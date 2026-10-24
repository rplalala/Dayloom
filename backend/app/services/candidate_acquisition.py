"""Shared candidate acquisition and evidence preparation for V1 and V2."""

from dataclasses import dataclass, replace

from backend.app.evidence.selection_models import (
    PlaceSearchIntent,
    PlaceSelectionInput,
    SearchIntentKind,
)
from backend.app.policies.interpreted_requirements import assess_requirements, require_resolved_hard
from backend.app.policies.poi_capacity import (
    EffectivePOICapacities,
)
from backend.app.policies.poi_funnel import (
    GENERIC_SEARCH_TERMS,
    NamedPlaceResolution,
    merge_search_observations,
)
from backend.app.policies.poi_selection import (
    POISelectionResult,
    SelectedPOI,
    evaluate_poi_eligibility,
)
from backend.app.runtime.budget import ToolBudgetKey
from backend.app.schemas.interpreted_requirements import ClarificationRequired
from backend.app.schemas.named_place_intent import NamedPlaceInclusion, NamedPlaceIntent
from backend.app.services.evidence_acquisition import SearchIntentExecution
from backend.app.services.review_selection import ReviewSelectionService

STRENGTH_ORDER = {"hard": 0, "high": 1, "medium": 2, "low": 3}


def allocate_review_order(contract, places, required, associations):
    """Allocate evidence opportunities only for explicitly registered dimensions."""
    requested = {e.requirement_id for e in contract.experience_evidence_requests}
    buckets = {}
    for req in contract.semantic_requirements:
        if req.requirement_id not in requested:
            continue
        relevant = sorted(
            p.candidate.place_id
            for p in places
            if req.requirement_id in associations.get(p.candidate.place_id, ())
        )
        # Evidence requirements can concern the whole pool without a discovery query.
        if not relevant:
            relevant = sorted(p.candidate.place_id for p in places)
        for subject in sorted(set(req.subject_refs)):
            buckets[(STRENGTH_ORDER[req.strength], subject, req.requirement_id)] = list(relevant)
    relevant_ids = {pid for bucket in buckets.values() for pid in bucket}
    chosen = sorted(set(required) & relevant_ids)
    for tier in range(4):
        keys = sorted(key for key in buckets if key[0] == tier)
        while any(buckets[key] for key in keys):
            for key in keys:
                while buckets[key] and buckets[key][0] in chosen:
                    buckets[key].pop(0)
                if buckets[key]:
                    chosen.append(buckets[key].pop(0))
    return tuple(chosen)


def selection_record(ids, places, required, trip_end, *, details):
    eligibility = tuple(
        evaluate_poi_eligibility(p, trip_end=trip_end, require_details=details) for p in places
    )
    by_id = {e.place_id: e for e in eligibility}
    return POISelectionResult(
        selected=tuple(
            SelectedPOI(
                place_id=i,
                must_visit=i in required,
                date_risk=by_id[i].date_risk,
                not_visitable_before=by_id[i].not_visitable_before,
            )
            for i in ids
        ),
        eligibility=eligibility,
        conflicts=(),
    )


@dataclass(frozen=True)
class CandidatePool:
    capacities: EffectivePOICapacities
    named_place_resolutions: tuple[NamedPlaceResolution, ...]
    search_intents: tuple[PlaceSearchIntent, ...]
    search_executions: tuple[SearchIntentExecution, ...]
    admitted_candidates: tuple[PlaceSelectionInput, ...]
    enriched_candidates: tuple[PlaceSelectionInput, ...]
    details_failures: tuple[tuple[str, str], ...]
    must_visit_place_ids: frozenset[str]
    excluded_place_ids: frozenset[str]


class CandidateAcquisition:
    """One request; acquisition adapter owns budgets/cache, selector owns no providers."""

    def __init__(self, acquisition, llm, tracer, llm_identity):
        self.acquisition = acquisition
        self.llm = llm
        self.tracer = tracer
        from backend.app.runtime.config_models import LandmarkNominationConfig
        from backend.app.services.landmark_discovery import LandmarkDiscovery
        from backend.app.services.landmark_nomination import LandmarkNominationService

        config = getattr(acquisition, "runtime_config", None)
        self.landmarks = LandmarkDiscovery(
            acquisition,
            LandmarkNominationService(
                llm,
                config.landmark_nomination if config else LandmarkNominationConfig(),
                config.main_generation.framing_tokens if config else 256,
                tracer=tracer,
                deadline=getattr(acquisition, "request_deadline", None),
            ),
        )
        if config and config.poi_semantics:
            from backend.app.services.poi_semantics import POISemanticsService

            acquisition.poi_semantics = POISemanticsService(
                llm,
                config.poi_semantics,
                config.main_generation.framing_tokens,
                tracer=tracer,
                deadline=getattr(acquisition, "request_deadline", None),
            )
        self.review = ReviewSelectionService(
            places_provider=acquisition._places,
            llm_client=llm,
            llm_config_identity=llm_identity,
            budget=acquisition._budget,
            cache=acquisition._cache,
            tracer=tracer,
        )

    async def run(self, contract, destination, window, *, supply):
        acq = self.acquisition
        r = contract.requirements
        assessments = assess_requirements(contract, category_visits=True)
        require_resolved_hard(assessments)
        capacities = supply.capacities(r, window)
        intents = []
        # The old identity resolver only interprets identities, not user preference text.
        # Exclusions use OPTIONAL for lookup only; the canonical requirement stays EXCLUDED.
        for n in sorted(
            contract.named_places,
            key=lambda n: (
                {"REQUIRED": 0, "EXCLUDED": 1, "OPTIONAL": 2}[n.inclusion],
                n.requirement_id,
            ),
        ):
            named = NamedPlaceIntent(
                place_text=n.place_text,
                inclusion=NamedPlaceInclusion.REQUIRED
                if n.inclusion == "REQUIRED"
                else NamedPlaceInclusion.OPTIONAL,
                source_text=n.source_refs[0].quote,
            )
            intents.append(
                PlaceSearchIntent(
                    intent_id=n.requirement_id,
                    term=n.place_text,
                    query=f"{n.place_text} in {r.destination}",
                    named_place_intent=named,
                    kind=SearchIntentKind.EXPLICIT_REQUIREMENT
                    if n.inclusion == "REQUIRED"
                    else SearchIntentKind.NORMAL_PREFERENCE,
                )
            )
        strengths = {s.requirement_id: s.strength for s in contract.semantic_requirements}
        positive = {
            r.requirement_id for r in contract.semantic_requirements if r.polarity == "favor"
        }
        links = {
            d.intent_id: tuple(r for r in d.requirement_refs if r in positive)
            for d in contract.discovery_intents
        }
        for named in contract.named_places:
            if named.inclusion != "EXCLUDED":
                links[named.requirement_id] = (named.requirement_id,)
                strengths[named.requirement_id] = (
                    "high" if named.inclusion == "REQUIRED" else "medium"
                )
        for d in sorted(
            contract.discovery_intents,
            key=lambda d: (
                min(STRENGTH_ORDER[strengths[key]] for key in d.requirement_refs),
                d.intent_id,
            ),
        ):
            intents.append(
                PlaceSearchIntent(
                    intent_id=d.intent_id,
                    term=d.query_text,
                    query=f"{d.query_text} in {r.destination}",
                    kind=SearchIntentKind.NORMAL_PREFERENCE,
                )
            )
        for i, term in enumerate(GENERIC_SEARCH_TERMS):
            if len(intents) >= 3:
                break
            intents.append(
                PlaceSearchIntent(
                    intent_id=f"default_{i}",
                    term=term,
                    query=f"{term} in {r.destination}",
                    kind=SearchIntentKind.FALLBACK,
                )
            )
        failures, executions = set(), []
        observations = await self.landmarks.search(
            contract, destination, intents, failures, executions
        )
        merged = merge_search_observations(observations)
        capture = getattr(acq, "candidate_capture", None)
        if capture is not None:
            capture.pre_google(merged.places)
        from backend.app.services.named_place_binding import (
            NamedPlaceBinding,
            NamedPlaceBindingError,
        )

        binding = NamedPlaceBinding(
            self.llm,
            config=acq.runtime_config.main_generation if acq.runtime_config else None,
            tracer=self.tracer,
            deadline=getattr(acq, "request_deadline", None),
        )
        resolutions = await binding.resolve(
            contract,
            merged.places,
            failures=frozenset(failures),
            not_attempted=frozenset(
                e.intent_id for e in executions if e.status == "budget_not_attempted"
            ),
        )
        required, excluded, optional = set(), set(), set()
        ordered_names = sorted(
            contract.named_places,
            key=lambda n: (
                {"REQUIRED": 0, "EXCLUDED": 1, "OPTIONAL": 2}[n.inclusion],
                n.requirement_id,
            ),
        )
        by_requirement = {b.search_intent_id: b for b in resolutions}
        resolutions = tuple(by_requirement[n.requirement_id] for n in ordered_names)
        for n, resolution in zip(ordered_names, resolutions, strict=True):
            if resolution.resolved_place_id is None and n.inclusion != "OPTIONAL":
                if resolution.status in {"search_failed", "search_not_issued_budget"}:
                    raise NamedPlaceBindingError(f"named_place_{resolution.status}")
                raise ClarificationRequired(
                    "unresolved_named_identity",
                    (n.requirement_id,),
                    conflicts=({"requirement_id": n.requirement_id, "reason": resolution.status},),
                )
            if resolution.resolved_place_id:
                if n.inclusion == "REQUIRED":
                    required.add(resolution.resolved_place_id)
                elif n.inclusion == "EXCLUDED":
                    excluded.add(resolution.resolved_place_id)
                else:
                    optional.add(resolution.resolved_place_id)
        if required & excluded:
            raise ClarificationRequired("required_excluded_conflict")
        if getattr(acq, "poi_semantics", None):
            acq.poi_semantics.named_bindings = {
                n.requirement_id: resolution.resolved_place_id
                for n, resolution in zip(ordered_names, resolutions, strict=True)
                if resolution.resolved_place_id
            }
        extension = getattr(supply, "discovery_extension", None)
        if extension is not None:
            merged = await extension.extend(contract, destination, merged, excluded)
            merged = replace(merged, places=tuple(self.landmarks.annotate(merged.places)))
        if capture is not None:
            status = (
                "partial"
                if extension is not None
                and extension.report.get("status") not in ("complete", "empty")
                else "complete"
            )
            reasons = [
                "search_" + execution.status
                for execution in executions
                if execution.status != "provider_success"
            ]
            if status == "partial":
                reasons.append("rag_" + extension.report.get("status", "unavailable"))
            capture.record("discovered", merged.places, status=status, reasons=reasons)
        eligible = [
            p
            for p in merged.places
            if evaluate_poi_eligibility(
                p,
                trip_end=r.end_date,
                excluded=p.candidate.place_id in excluded,
                require_details=False,
            ).eligible
        ]
        if not required <= {p.candidate.place_id for p in eligible}:
            raise ClarificationRequired("required_place_ineligible")
        capacities = supply.required_capacities(capacities, len(required))
        if not eligible:
            raise ClarificationRequired("no_eligible_candidates")
        associations = {
            p.candidate.place_id: tuple(
                sorted({ref for i in p.discovery_intent_ids for ref in links.get(i, ())})
            )
            for p in eligible
        }
        order = supply.acquisition_order(
            eligible, required, associations, strengths, contract, destination
        )
        by_id = {p.candidate.place_id: p for p in eligible}
        admitted = tuple(by_id[i] for i in order[: capacities.c_raw])
        if extension is not None:
            extension.record_admission(
                {p.candidate.place_id for p in eligible},
                {p.candidate.place_id for p in admitted},
            )
        self.tracer.event(
            "semantic_candidate_admission",
            {
                "admitted_ids": order[: capacities.c_raw],
                "omitted_ids": order[capacities.c_raw :],
                "omitted_associations": {i: associations[i] for i in order[capacities.c_raw :]},
                "raw_count": len(observations),
                "merged_count": len(merged.places),
            },
        )
        if capture is not None:
            capture.record("admitted", admitted)
            capture.omissions(
                [
                    {
                        "canonical_place_id": p.candidate.place_id,
                        "stage": "admitted",
                        "reason": "ineligible_or_excluded",
                    }
                    for p in merged.places
                    if p.candidate.place_id not in by_id
                ]
                + [
                    {"canonical_place_id": pid, "stage": "admitted", "reason": "admission_capacity"}
                    for pid in order[capacities.c_raw :]
                ]
            )
        acq._consume_new_candidates(p.candidate.place_id for p in admitted)
        from backend.app.services.candidate_details import acquire_candidate_details

        semantics = getattr(acq, "poi_semantics", None)

        async def adequate(items, deadline):
            rows = await semantics.prepare(
                [p.structured_evidence for p in items], contract, deadline=deadline
            )
            if (
                semantics.calls >= semantics.config.max_calls
                or semantics.elapsed >= semantics.config.total_seconds
            ):
                return True  # No assessment capacity for additional unassessed Details.
            qualified = {pid: row for pid, row in rows.items() if row.main_eligible}
            if len(qualified) < capacities.k_final:
                return False
            exclusive = any(
                r.experience_goal and r.experience_goal.trip_scope == "exclusive"
                for r in contract.semantic_requirements
            )
            if exclusive:
                return True
            from math import ceil

            favored = {
                r.requirement_id for r in contract.semantic_requirements if r.polarity == "favor"
            }
            general = sum(
                pid not in required
                and not any(
                    m.requirement_id in favored and m.relation == "supported" for m in row.matches
                )
                for pid, row in qualified.items()
            )
            reference = ceil(
                max(0, capacities.k_final - len(required)) * semantics.config.exploration_fraction
            )
            unprocessed = {p.candidate.place_id for p in admitted} - rows.keys()
            # Search origin is an opportunity lane, never proof of semantic suitability.
            pending_general = any(not associations.get(pid) for pid in unprocessed)
            return general >= reference or not pending_general

        rich, detail_failures, attempted = await acquire_candidate_details(
            acq,
            admitted,
            r.end_date,
            capacities.r_pool,
            adequate=adequate if semantics else None,
        )
        if capture is not None:
            capture.record(
                "enriched",
                rich,
                reasons=[getattr(acq, "details_report", {}).get("stop", "unknown")],
            )
            capture.omissions(
                [
                    {"canonical_place_id": pid, "stage": "enriched", "reason": reason}
                    for pid, reason in detail_failures
                ]
                + [
                    {
                        "canonical_place_id": pid,
                        "stage": "enriched",
                        "reason": "unprocessed_"
                        + getattr(acq, "details_report", {}).get("stop", "unknown"),
                    }
                    for pid in getattr(acq, "details_report", {}).get("unprocessed_ids", [])
                ]
            )
        if semantics:
            await semantics.prepare([p.structured_evidence for p in rich], contract)
        if not required <= {p.candidate.place_id for p in rich}:
            raise ClarificationRequired("required_place_details_unusable")
        if not rich:
            raise ClarificationRequired("no_eligible_details")
        profiles = {}
        review_order = allocate_review_order(contract, rich, required, associations)
        for place_id in review_order[: capacities.review_pool_cap]:
            profiles[place_id] = await self.review.acquire_profile(place_id)
        selection = await supply.select(
            contract,
            assessments,
            rich,
            required,
            excluded,
            capacities,
            destination,
            profiles,
            optional,
            associations,
            strengths,
        )
        policy_result = selection.policy_result
        final = selection_record(
            policy_result.selected_place_ids, rich, required, r.end_date, details=True
        )
        if capture is not None:
            supplied = set(final.selected_place_ids)
            capture.record("supplied", [p for p in rich if p.candidate.place_id in supplied])
            capture.omissions(
                [
                    {
                        "canonical_place_id": p.candidate.place_id,
                        "stage": "supplied",
                        "reason": "not_selected",
                    }
                    for p in rich
                    if p.candidate.place_id not in supplied
                ]
            )
        acq._budget.consume(ToolBudgetKey.FINAL_POIS, len(final.selected_place_ids))
        funnel = CandidatePool(
            capacities=capacities,
            named_place_resolutions=resolutions,
            search_intents=tuple(intents),
            search_executions=tuple(executions),
            admitted_candidates=admitted,
            enriched_candidates=tuple(rich),
            details_failures=tuple(detail_failures),
            must_visit_place_ids=frozenset(required),
            excluded_place_ids=frozenset(excluded),
        )
        self.tracer.event(
            supply.completion_event,
            {
                "selected_ids": final.selected_place_ids,
                "policy_result": policy_result.model_dump(mode="json"),
                "evaluator_calls": selection.evaluator_calls,
                "subset_enumerator_calls": selection.subset_enumerator_calls,
                "details_attempts": attempted,
                "details_failures": detail_failures,
                "review_place_ids": sorted(profiles),
                "tool_usage": acq._budget.summary(),
            },
        )
        return funnel, selection
