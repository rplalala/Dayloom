"""Qualified reuse first, then individually bounded optional discovery and Details."""

import unicodedata
from types import SimpleNamespace

from backend.app.evidence.selection_normalization import (
    normalize_place_details_for_selection,
    normalize_place_search_hit,
)
from backend.app.integrations.google.places import (
    PLACES_CANDIDATE_FIELD_MASK,
    PLACES_DETAILS_FIELD_MASK,
)
from backend.app.integrations.models import LatLng, PlaceDetailsRequest, PlaceSearchRequest
from backend.app.policies.poi_funnel import opening_dates_compatible
from backend.app.policies.poi_selection import evaluate_poi_eligibility
from backend.app.schemas.tripworld_discovery import RetrievalQuery
from backend.app.services.evidence_acquisition import V1EvidenceAcquisitionService, _ProviderResult
from backend.app.services.tripworld_discovery import TripWorldDiscovery
from backend.app.tripworld.database.policy import POLICY_VERSION
from backend.app.tripworld.database.vectors import SPACE_ID
from backend.app.tripworld.retrieval.entities import RetrievalEntity
from backend.app.versions.v3.repair_acceptance import inclusion_ids
from backend.app.versions.v3.repair_budget import RepairLimit
from backend.app.versions.v3.repair_feedback import digest, opportunity
from backend.app.versions.v3.repair_models import (
    CandidateDecision,
    CandidatePreparation,
    RepairCandidate,
)
from backend.app.versions.v3.repair_transport import allowed_modes


def qualify(item, trip_end, excluded):
    if item.structured_evidence is None or item.structured_evidence.availability == "unavailable":
        return False
    return evaluate_poi_eligibility(
        item, trip_end=trip_end, excluded=item.candidate.place_id in excluded
    ).eligible


def merge_details(item, dto):
    enriched = normalize_place_details_for_selection(item, dto)
    if enriched.details_opening_date and any(
        not opening_dates_compatible(enriched.details_opening_date, d)
        for d in enriched.search_opening_date_observations
    ):
        enriched = enriched.model_copy(update={"opening_date_conflict": True})
    return enriched


class RepairResolver(TripWorldDiscovery):
    """Reuse exact V2 Google-backed identity resolution, with a repair-only ledger.

    Never invoke extend(), its query planner, initial supply budgets or runtime factory.
    """

    def __init__(self, provider, budget, geographic_scope, blocked):
        self.acq = SimpleNamespace(
            _places=provider,
            _place_details_cache_key=V1EvidenceAcquisitionService._place_details_cache_key,
        )
        self.blocked = blocked
        self.budget, self.scope = budget, geographic_scope
        self.config = SimpleNamespace(identity_radius_km=budget.rag_config.identity_radius_km)

    async def provider(self, key, kind, factory):
        if kind == "details" and self.blocked(key[1]):
            return _ProviderResult(value=None)
        value = await self.budget.call(
            key,
            factory,
            charges={"details": 1} if kind == "details" else {"google": 1, "fallback": 1},
            observed=getattr(self.acq._places, "observes_send_boundary", False),
            unwrap=True,
        )
        if kind == "fallback" and value is not None:
            value = value.model_copy(
                update={"candidates": [c for c in value.candidates if not self.blocked(c.place_id)]}
            )
        return _ProviderResult(value=value)


def candidate_targets(original, context, scope):
    """Preserve all date associations; matching, not assignment, measures supply."""
    from backend.app.versions.v3.repair_acceptance import assess

    report = assess(original, context)
    from backend.app.versions.v3.repair_targets import affected_activity_ids

    targets = []
    days = {d.date: d for d in report.diagnostics.days}
    for finding in report.findings:
        if finding.finding_id not in scope.target_ids:
            continue
        if finding.check not in {
            "coverage",
            "soft_pace",
            "daily_visit_count",
        } and finding.reason not in {
            "required_identity_omitted",
            "required_visit_obligation_unmet",
            "experience_goal_count_unmet",
        }:
            continue
        for day in scope.add_dates:
            if scope.direct_add_dates is not None and day not in scope.direct_add_dates:
                continue
            if finding.dates and day not in finding.dates:
                continue
            if finding.check == "coverage" and not finding.dates:
                continue
            gap = (
                max(
                    0,
                    min(finding.adopted_evidence.get("zero_counts", (0,)))
                    - finding.adopted_evidence.get("count", 0),
                )
                if finding.check == "soft_pace"
                else max(
                    0,
                    (
                        1
                        if finding.reason == "minimum_daily_coverage_missing"
                        else scope.daily_main_min
                    )
                    - days[day].distinct_main_poi_count,
                )
                if finding.check == "coverage"
                else int(finding.magnitude or 1)
            )
            if gap:
                targets.append((finding.finding_id, day, "add", gap))
    for permission in scope.coverage_permissions:
        if permission.date in scope.add_dates and (
            (
                permission.parent_id in scope.target_ids
                and any(
                    p.activity_id in permission.trigger_activity_ids
                    and p.operations & {"replace", "delete", "move"}
                    for p in scope.permissions
                )
            )
            or permission.target_id in scope.target_ids
            or any(
                r.permission.target_id == permission.target_id and r.status != "resolved"
                for r in scope.active_related
            )
        ):
            targets.append(
                (permission.target_id, permission.date, "add", max(1, permission.minimum_count))
            )
    for permission in scope.permissions:
        if "replace" in permission.operations:
            day = next(
                d.date
                for d in original.days
                for a in d.activities
                if a.activity_id == permission.activity_id
            )
            parents = [
                f.finding_id
                for f in report.findings
                if f.finding_id in scope.target_ids
                and permission.activity_id in affected_activity_ids(original, f)
            ]
            for target in parents:
                targets.append((target, day, "replace", 1))
    return tuple(dict.fromkeys(targets))


def date_hours(place, day):
    from backend.app.evidence.opening_hours import selected_hours

    return selected_hours(place, day)["known"]


def matched_capacity(decisions, targets, multiplier=2):
    """Bipartite matching counts each identity once without removing associations."""
    matched = {}
    slots = [
        (target, day, operation)
        for target, day, operation, gap in targets
        for _ in range(multiplier * gap)
    ]
    choices = [
        {
            d.place_id
            for d in decisions
            if d.target_id == target
            and d.date == day
            and d.operation == operation
            and d.disposition == "eligible"
            and d.opportunity_status != "BLOCKED"
        }
        for target, day, operation in slots
    ]

    def augment(slot, seen):
        for pid in sorted(choices[slot] - seen):
            seen.add(pid)
            if pid not in matched or augment(matched[pid], seen):
                matched[pid] = slot
                return True
        return False

    return sum(augment(i, set()) for i in range(len(slots)))


async def prepare_candidates(
    context,
    scope,
    budget,
    *,
    original,
    pool=(),
    provider=None,
    intent_ids=(),
    rag=None,
    geographic_scope=None,
    semantic_service=None,
):
    """rag is an already prepared RuntimeRetrieval-compatible port; no instance assembly."""
    policy = budget.policy
    capacity = policy.input.identity_capacity
    alternatives = policy.alternatives_per_gap
    required, excluded = inclusion_ids(context)
    scheduled = {
        a.source_place_id for d in original.days for a in d.activities if a.source_place_id
    }
    if len(scheduled) > capacity:
        raise ValueError("repair_identity_union_ceiling")
    targets = candidate_targets(original, context, scope)
    from backend.app.versions.v3.repair_acceptance import assess

    goal_targets = {
        f.finding_id: f.requirement_ids
        for f in assess(original, context).findings
        if f.reason == "experience_goal_count_unmet"
    }
    from backend.app.versions.v3.repair_targets import insertion_windows

    available_dates = {
        str(w["start"])[:10] for w in insertion_windows(original, context.schedule, scope)
    }
    acquisition_dates = {
        day
        for _, day, operation, _ in targets
        if context.schedule is None
        or operation == "replace"
        or scope.coverage_permissions
        or str(day) in context.schedule.unresolved_dates
        or str(day) in available_dates
    }
    ledger = {
        p.place_id: RepairCandidate(place=p, origin="original_supply", provenance=(p.source_ref,))
        for p in context.places
        if p.place_id in context.original_supply_ids
    }
    ledger.update({c.place.place_id: c for c in context.identity_ledger})
    if semantic_service:
        initial_places = {pid: c.place for pid, c in ledger.items()}
        initial_places.update(
            {
                p.candidate.place_id: p.structured_evidence
                for p in pool
                if qualify(p, context.contract.requirements.end_date, excluded)
            }
        )
        await semantic_service.prepare(
            list(initial_places.values()), context.contract, deadline=budget.io_deadline
        )
    items = {item.candidate.place_id: item for item in pool}
    decisions = []
    eligible = {}
    seen = set()
    newly_qualified = set()
    revisit = {(r.place_id, r.date) for r in scope.revisits}
    slots = capacity - len(scheduled)
    reference = sum(alternatives * gap for _, _, _, gap in targets)
    base_geographic_scope = geographic_scope
    opportunity_records = []
    history = getattr(budget, "presentation_history", ())
    presented = {row["signature"] for row in history}
    feedback_adjustment = getattr(budget, "feedback_kind", None) in {
        "no_op_patch",
        "no_measurable_improvement",
        "candidate_specific_conflict",
    }
    local_stops = []
    reserve = 0

    def discovery_scope():
        from backend.app.tripworld.retrieval.geography import GeographicScope

        seen_dates = getattr(budget, "discovery_dates", set())
        days = sorted(acquisition_dates)
        if not days:
            return None, base_geographic_scope

        def priority(day):
            count = len({r.place_id for r in eligible.values() if r.date == day})
            novel = len(
                {
                    r.place_id
                    for r in eligible.values()
                    if r.date == day and r.opportunity_signature not in presented
                }
            )
            need = max((alternatives * gap for _, d, _, gap in targets if d == day), default=0)
            return (
                novel > 0 if feedback_adjustment else count >= need,
                day in seen_dates,
                count - need,
                day,
            )

        day = min(days, key=priority)
        anchors = [
            ledger[a.source_place_id].place
            for d in original.days
            if d.date == day
            for a in d.activities
            if a.source_place_id in ledger
        ]
        anchors = [p for p in anchors if p.latitude is not None and p.longitude is not None]
        selected = base_geographic_scope
        if anchors:
            p = anchors[0]
            selected = GeographicScope(
                latitude=p.latitude,
                longitude=p.longitude,
                radius_km=policy.spatial.walk_radius_km
                if allowed_modes(scope) == ("WALK",)
                else policy.spatial.motor_radius_km,
            )
        return day, selected

    def record_opportunity(day, selected, kind):
        budget.discovery_dates = getattr(budget, "discovery_dates", set()) | {day}
        opportunity_records.append(
            dict(
                date=str(day),
                kind=kind,
                scope=selected.model_dump(mode="json") if selected else None,
                reason="target_alternatives_or_feedback",
                status="attempted_or_cached",
            )
        )

    intents = {i.intent_id: i for i in context.contract.discovery_intents}
    if (
        len(intent_ids) > max(policy.acquisition.google, policy.acquisition.retrieval)
        or len(set(intent_ids)) != len(intent_ids)
        or not set(intent_ids) <= intents.keys()
    ):
        raise ValueError("Discovery intents must fit configured acquisition capacity")

    def has_existing_route(pid, day):
        from backend.app.versions.v3.repair_routes import route_rows

        for d in original.days:
            if d.date != day:
                continue
            for a in d.activities:
                if not a.source_place_id:
                    continue
                # Preparation grants an option, not a final time/adjacency certification.
                for origin, destination, mode in (
                    (o, d, m)
                    for o, d in ((a.source_place_id, pid), (pid, a.source_place_id))
                    for m in allowed_modes(scope)
                ):
                    if route_rows(
                        origin,
                        destination,
                        mode,
                        "TRAFFIC_UNAWARE" if mode == "DRIVE" else None,
                        a.end_time,
                        context.route_evidence,
                    ):
                        return True
        return False

    def associations(candidate, item=None):
        assessment = next(
            (r for r in context.semantic_assessments if r.place_id == candidate.place.place_id),
            None,
        )
        if semantic_service:
            assessment = semantic_service.ledger.get(candidate.place.place_id)
            # Newly acquired identities await the bounded batch in finish(). These
            # provisional associations never authorize model input before assessment.
            if assessment is not None and not assessment.main_eligible:
                return []
        rows = []
        for target, day, operation, _ in targets:
            if target in goal_targets:
                if assessment is not None and not any(
                    m.requirement_id in goal_targets[target] and m.relation == "supported"
                    for m in assessment.matches
                ):
                    continue
                if assessment is None and not semantic_service:
                    continue
            pid, place = candidate.place.place_id, candidate.place
            disposition, reason = "eligible", "qualified_option_not_date_verified"
            refs = candidate.provenance
            if pid in excluded:
                disposition, reason = "excluded", "explicitly_excluded"
            elif operation == "add" and pid in scheduled and (pid, day) not in revisit:
                disposition, reason = "scheduled_context", "revisit_not_authorized"
            elif (
                place.availability == "unavailable" or place.business_status == "CLOSED_PERMANENTLY"
            ):
                disposition, reason = "fact_ineligible", "unavailable_or_permanently_closed"
            elif item is not None:
                gate = evaluate_poi_eligibility(item, trip_end=day, excluded=False)
                if not gate.eligible:
                    disposition = (
                        "excluded"
                        if gate.reason == "opening_definitely_after_trip"
                        else "fact_ineligible"
                    )
                    reason = gate.reason
                    # A future-opening exclusion is bounded to this target date.
                    refs = candidate.provenance
            if disposition == "eligible" and pid not in required and operation == "add":
                from backend.app.versions.v3.repair_spatial import distance_km

                anchors = [
                    ledger[a.source_place_id].place
                    for d in original.days
                    if d.date == day
                    for a in d.activities
                    if a.source_place_id in ledger
                ]
                radius = (
                    policy.spatial.walk_radius_km
                    if allowed_modes(scope) == ("WALK",)
                    else policy.spatial.motor_radius_km
                )
                distances = [distance_km(place, anchor) for anchor in anchors]
                if (
                    distances
                    and all(v is not None and v > radius for v in distances)
                    and not has_existing_route(pid, day)
                ):
                    disposition, reason = "excluded", "target_geographic_policy"
            from backend.app.evidence.opening_hours import selected_hours, with_context_timezone

            scoped_place = with_context_timezone(
                place,
                [
                    ledger[a.source_place_id].place
                    for d in original.days
                    if d.date == day
                    for a in d.activities
                    if a.source_place_id in ledger
                ],
            )
            view = selected_hours(
                scoped_place,
                day,
                next((e for e in context.effective_places if e.place_id == pid), None),
            )
            hours = view["known"]
            if disposition == "eligible" and hours and not view["intervals"]:
                disposition, reason = "excluded", "adopted_date_closed"
                refs = tuple(view["evidence_refs"])
            state, opportunity_reason, windows = opportunity(
                scoped_place,
                day,
                operation,
                view,
                original,
                context,
                scope,
                policy.spatial,
                pid in required,
            )
            if disposition != "eligible":
                state, opportunity_reason = "BLOCKED", reason
            elif state == "BLOCKED":
                disposition, reason = "excluded", opportunity_reason
                if opportunity_reason == "leg_policy_excludes_all_authorized_windows":
                    refs = tuple(
                        sorted(
                            set(refs)
                            | {
                                r.source_ref
                                for r in context.route_evidence
                                if any(
                                    pid in (e.origin_place_id, e.destination_place_id)
                                    for e in r.elements
                                )
                            }
                        )
                    )
            anchors = [
                a.model_dump(mode="json")
                for d in original.days
                if d.date == day
                for a in d.activities
            ]
            signature = digest(
                dict(
                    place_id=pid,
                    date=str(day),
                    operation=operation,
                    target=getattr(budget, "target_keys", {}).get(target, target),
                    windows=windows,
                    hours=view,
                    anchors=anchors,
                    mode=scope.travel_mode,
                    routing_preference=scope.routing_preference,
                    failed_combinations=[
                        r
                        for r in getattr(budget, "conflict_records", ())
                        if r["place_id"] == pid and r["date"] == str(day)
                    ],
                    routes=[
                        r.model_dump(mode="json")
                        | {
                            "elements": [
                                e.model_dump(mode="json")
                                for e in r.elements
                                if pid in (e.origin_place_id, e.destination_place_id)
                            ]
                        }
                        for r in context.route_evidence
                        if any(
                            pid in (e.origin_place_id, e.destination_place_id) for e in r.elements
                        )
                    ],
                )
            )
            rows.append(
                CandidateDecision(
                    opportunity_status=state,
                    opportunity_reason=opportunity_reason,
                    opportunity_windows=windows,
                    opportunity_signature=signature,
                    place_id=pid,
                    target_id=target,
                    date=day,
                    operation=operation,
                    disposition=disposition,
                    reason=reason,
                    evidence_refs=refs,
                    has_date_hours=hours,
                    related_intent_ids=tuple(sorted(set(item.discovery_intent_ids) & set(intents)))
                    if item is not None
                    else (),
                    unknowns=(() if hours else ("target_date_hours_missing",))
                    + (
                        "admission_reservation_and_special_area_unverified",
                        "verified_cost_not_supported",
                    ),
                )
            )
        return rows

    def admit(item, origin):
        pid = item.candidate.place_id
        if pid in seen:
            budget.used["duplicate_hits"] += 1
            return
        seen.add(pid)
        if not qualify(item, context.contract.requirements.end_date, excluded):
            # Record normal fact-gate failures, never relabel missing Details as unsuitable.
            gate = evaluate_poi_eligibility(
                item, trip_end=context.contract.requirements.end_date, excluded=pid in excluded
            )
            for target, day, operation, _ in targets:
                decisions.append(
                    CandidateDecision(
                        place_id=pid,
                        target_id=target,
                        date=day,
                        operation=operation,
                        disposition="fact_ineligible",
                        reason=gate.reason or "details_unavailable",
                        evidence_refs=(item.candidate.source_ref,)
                        if hasattr(item.candidate, "source_ref")
                        else (),
                    )
                )
            return
        refs = tuple(h.intent_id for h in item.query_hits) + tuple(
            o.evidence_ref for o in item.discovery_origins
        )
        candidate = RepairCandidate(
            place=item.structured_evidence,
            origin=origin,
            provenance=(*refs, item.structured_evidence.source_ref),
        )
        ledger[pid] = candidate
        rows = associations(candidate, item)
        decisions.extend(rows)
        eligible.update(
            {
                (r.place_id, r.target_id, r.date, r.operation): r
                for r in rows
                if r.disposition == "eligible"
            }
        )
        if origin in {"google", "rag"}:
            newly_qualified.add(pid)

    for pid, candidate in tuple(ledger.items()):
        # Original supply is already through the shared gate; pool adds dated facts where available.
        rows = associations(candidate, items.get(pid))
        decisions.extend(rows)
        eligible.update(
            {
                (r.place_id, r.target_id, r.date, r.operation): r
                for r in rows
                if r.disposition == "eligible"
            }
        )
        seen.add(pid)
    pending = []
    for item in pool:
        if item.candidate.place_id in seen:
            budget.used["duplicate_hits"] += 1
        elif item.structured_evidence is not None:
            admit(item, "comparison_pool")
            budget.used["qualified_reuse"] += int(item.candidate.place_id in ledger)
        else:
            pending.append((item, "discovered"))
            for target, day, operation, _ in targets:
                decisions.append(
                    CandidateDecision(
                        place_id=item.candidate.place_id,
                        target_id=target,
                        date=day,
                        operation=operation,
                        disposition="details_pending",
                        reason="details_not_acquired",
                    )
                )

    def rank(pid):
        rows = [r for r in eligible.values() if r.place_id == pid]
        from backend.app.versions.v3.repair_spatial import distance_km

        anchors = [
            ledger[a.source_place_id].place
            for d in original.days
            if d.date in scope.add_dates
            for a in d.activities
            if a.source_place_id in ledger
        ]
        distances = [distance_km(ledger[pid].place, a) for a in anchors]
        proximity = min((v for v in distances if v is not None), default=0)
        return (
            proximity,
            -sum(r.has_date_hours for r in rows),
            -len({iid for r in rows for iid in r.related_intent_ids}),
            -len(rows),
            pid,
        )

    def select_ids():
        pinned = (required & {r.place_id for r in eligible.values()}) - scheduled
        if len(scheduled | pinned) > capacity:
            raise ValueError("repair_identity_union_ceiling")
        all_ids = {r.place_id for r in eligible.values()}
        chosen = set(pinned) | (all_ids & scheduled)
        # One round-wide exploration opportunity, not a score bonus or per-day reserve.
        fresh = sorted(newly_qualified & all_ids - scheduled - chosen, key=rank)[
            : min(reserve, capacity - len(scheduled | chosen))
        ]
        chosen.update(fresh)
        while all_ids - chosen and len(scheduled | chosen) < capacity:
            # Prefer filling distinct target opportunity slots, without assigning an ID
            # permanently to a date or rewarding a discovery source.
            def opportunity(pid):
                rows = [r for r in eligible.values() if r.place_id in chosen | {pid}]
                novel = [r for r in rows if r.opportunity_signature not in presented]
                return (
                    -matched_capacity(novel, targets, alternatives) if feedback_adjustment else 0,
                    -matched_capacity(rows, targets, alternatives),
                    *rank(pid),
                )

            chosen.add(min(all_ids - chosen, key=opportunity))
        return chosen

    def insufficient(rows):
        return matched_capacity(rows, targets, alternatives) < reference

    def material_reasons():
        rows = list(eligible.values())
        result = []
        if insufficient(rows):
            result.append("distinct_target_alternatives_shortfall")
        # Missing generic facts do not make candidates ineligible or cause universal exploration.
        novel = any(
            r.opportunity_signature not in presented for r in rows if r.place_id in select_ids()
        )
        if feedback_adjustment and not novel:
            result.append("no_progress_requires_new_opportunity")
        elif getattr(budget, "explore_feedback", False) and not getattr(
            budget, "feedback_explored", False
        ):
            result.append("previous_arrangement_requires_other_options")
        return result

    reasons = material_reasons()
    pinned = required - scheduled
    reserve = min(policy.exploration_positions, max(0, slots - len(pinned))) if reasons else 0
    baseline_ids = {r.place_id for r in eligible.values()}
    preparing_old = True

    def stop(reason):
        if reason not in local_stops:
            local_stops.append(reason)
        if reason not in budget.stops:
            budget.stops.append(reason)
        return False

    def can_acquire():
        if semantic_service and (
            semantic_service.calls >= semantic_service.config.max_calls
            or semantic_service.elapsed >= semantic_service.config.total_seconds
        ):
            return stop("semantic_assessment_preparation_limit")
        if not targets:
            return stop("no_candidate_operation")
        if not acquisition_dates:
            return stop("no_authorized_insertion_window")
        if not (material_reasons() if preparing_old else reasons):
            return stop("preparation_reference_met")
        if feedback_adjustment and any(
            r.opportunity_signature not in presented
            for r in eligible.values()
            if r.place_id in select_ids()
        ):
            return stop("novel_existing_opportunity_available")
        if budget.io_deadline <= budget.clock() or budget.remaining() <= 0:
            return stop("preparation_deadline")
        if (
            reserve == 0
            and not preparing_old
            and len(scheduled | {r.place_id for r in eligible.values()}) >= capacity
        ):
            return stop("no_discovery_presentation_opportunity")
        if slots <= len(pinned):
            return stop("input_positions_unavailable")
        if (
            budget.used["canonical"] >= budget.limits["canonical"]
            or budget.used["details"] >= budget.limits["details"]
        ):
            reason = (
                "canonical_budget_exhausted"
                if budget.used["canonical"] >= budget.limits["canonical"]
                else "details_budget_exhausted"
            )
            if reason not in budget.stops:
                budget.stops.append(reason)
            return False
        fresh = newly_qualified - baseline_ids
        # Stop as soon as the reserved opportunity and preparation target are served.
        option_ids = {r.place_id for r in eligible.values()}
        if (
            not preparing_old
            and len(fresh) >= reserve
            and (
                not insufficient(list(eligible.values())) or len(scheduled | option_ids) >= capacity
            )
        ):
            return stop("bounded_exploration_complete")
        return budget.remaining() > 0

    def blocked(pid):
        if pid in excluded:
            for target, day, operation, _ in targets:
                decisions.append(
                    CandidateDecision(
                        place_id=pid,
                        target_id=target,
                        date=day,
                        operation=operation,
                        disposition="excluded",
                        reason="explicitly_excluded",
                        evidence_refs=tuple(
                            f"named_requirement:{n.requirement_id}"
                            for n in context.contract.named_places
                            if n.inclusion == "EXCLUDED"
                        ),
                    )
                )
            return True
        if pid in scheduled and not any(
            (pid, day) in revisit or operation == "replace" for _, day, operation, _ in targets
        ):
            for target, day, operation, _ in targets:
                decisions.append(
                    CandidateDecision(
                        place_id=pid,
                        target_id=target,
                        date=day,
                        operation=operation,
                        disposition="scheduled_context",
                        reason="revisit_not_authorized",
                    )
                )
            return True
        item = items.get(pid)
        if item is not None:
            return all(
                not evaluate_poi_eligibility(item, trip_end=day, require_details=False).eligible
                for _, day, _, _ in targets
            )
        return False

    async def finish():
        judgments = {r.place_id: r for r in context.semantic_assessments}
        if semantic_service:
            judgments = await semantic_service.prepare(
                [c.place for c in ledger.values()], context.contract, deadline=budget.io_deadline
            )
            for key in list(eligible):
                if key[0] not in judgments or not judgments[key[0]].main_eligible:
                    del eligible[key]
        for key, option in list(eligible.items()):
            if option.target_id in goal_targets and (
                option.place_id not in judgments
                or not judgments[option.place_id].main_eligible
                or not any(
                    m.requirement_id in goal_targets[option.target_id] and m.relation == "supported"
                    for m in judgments[option.place_id].matches
                )
            ):
                del eligible[key]
        chosen = select_ids()
        auth = tuple(
            r.model_copy(
                update={
                    "disposition": "selected",
                    "reason": "exploration_opportunity"
                    if r.place_id in newly_qualified
                    else "retained_qualified_option",
                }
            )
            for r in eligible.values()
            if r.place_id in chosen
        )
        omitted = tuple(
            r.model_copy(
                update={"disposition": "capacity_omitted", "reason": "input_identity_capacity"}
            )
            for r in eligible.values()
            if r.place_id not in chosen
        )
        budget.used["input_identity_union"] = len(scheduled | chosen)
        spatial_options = spatial_candidate_options(
            chosen, scheduled, auth, ledger, policy, scope.travel_mode
        )
        from backend.app.versions.v3.repair_targets import insertion_windows

        def operation_audit(target, day, operation):
            rows = [
                r
                for r in eligible.values()
                if (r.target_id, r.date, r.operation) == (target, day, operation)
            ]
            blocked = {
                r.place_id
                for r in decisions
                if (r.target_id, r.date, r.operation) == (target, day, operation)
                and r.opportunity_status == "BLOCKED"
            }
            return dict(
                target_id=target,
                date=str(day),
                operation=operation,
                association_edges=len(rows),
                unique_candidate_identities=len({r.place_id for r in rows}),
                input_candidate_identities=len({r.place_id for r in rows if r.place_id in chosen}),
                tryable=len({r.place_id for r in rows if r.opportunity_status == "TRYABLE"}),
                unresolved=len({r.place_id for r in rows if r.opportunity_status == "UNRESOLVED"}),
                blocked=len(blocked),
                presented=len({r.place_id for r in rows if r.opportunity_signature in presented}),
                unpresented=len(
                    {r.place_id for r in rows if r.opportunity_signature not in presented}
                ),
                preparation_reference_met=(
                    matched_capacity(
                        rows,
                        [
                            (target, day, operation, gap)
                            for t, d, op, gap in targets
                            if (t, d, op) == (target, day, operation)
                        ],
                        alternatives,
                    )
                    >= sum(
                        alternatives * gap
                        for t, d, op, gap in targets
                        if (t, d, op) == (target, day, operation)
                    )
                ),
                acquisition_stops=list(local_stops),
            )

        return CandidatePreparation(
            identity_capacity_summary=dict(
                scope="all_active_candidate_operations",
                independent_identity_capacity=matched_capacity(
                    list(eligible.values()), targets, alternatives
                ),
                input_independent_identity_capacity=matched_capacity(
                    [r for r in eligible.values() if r.place_id in chosen], targets, alternatives
                ),
                unique_candidate_identities=len({r.place_id for r in eligible.values()}),
                association_edges=len(eligible),
                preparation_reference=reference,
                preparation_reference_met=not insufficient(list(eligible.values())),
            ),
            identity_free_operations=tuple(
                dict(
                    activity_id=p.activity_id,
                    operation=op,
                    candidate_identities_required=False,
                    source_date=str(
                        next(
                            d.date
                            for d in original.days
                            for a in d.activities
                            if a.activity_id == p.activity_id
                        )
                    ),
                    destination_dates=[str(d) for d in p.move_dates] if op == "move" else [],
                )
                for p in scope.permissions
                for op in sorted(p.operations)
                if op in {"retime", "move", "delete"}
            ),
            target_opportunities=tuple(operation_audit(t, d, op) for t, d, op, _ in targets),
            elastic_windows=tuple(insertion_windows(original, context.schedule, scope)),
            spatial_options=tuple(spatial_options),
            discovery_opportunities=tuple(opportunity_records)
            + tuple(
                dict(
                    date=str(day),
                    status="not_attempted",
                    reason=local_stops[-1]
                    if local_stops
                    else "no_targeted_query"
                    if not intent_ids
                    else "provider_unavailable"
                    if provider is None
                    else "no_new_result",
                )
                for day in sorted({d for _, d, _, _ in targets})
                if not any(r["date"] == str(day) for r in opportunity_records)
            ),
            ledger=tuple(ledger.values()),
            input_candidates=tuple(ledger[pid] for pid in sorted(chosen)),
            authorizations=auth,
            decisions=tuple(dict.fromkeys((*decisions, *omitted, *auth))),
            scheduled_ids=tuple(sorted(scheduled)),
            exploration_reasons=tuple(reasons),
            exploration_slots=reserve,
            preparation_reference=reference,
        )

    async def details(item, origin):
        from backend.app.versions.v3.repair_spatial import distance_km

        if item.candidate.place_id not in required and targets:
            outside = []
            for _target, day, operation, _ in targets:
                anchors_for_day = [
                    ledger[a.source_place_id].place
                    for d in original.days
                    if d.date == day
                    for a in d.activities
                    if a.source_place_id in ledger
                ]
                radius = (
                    policy.spatial.walk_radius_km
                    if allowed_modes(scope) == ("WALK",)
                    else policy.spatial.motor_radius_km
                )
                distances = [distance_km(item.candidate, a) for a in anchors_for_day]
                outside.append(
                    operation == "add"
                    and not has_existing_route(item.candidate.place_id, day)
                    and bool(distances)
                    and all(v is not None and v > radius for v in distances)
                )
            if all(outside):
                for target, day, operation, _ in targets:
                    decisions.append(
                        CandidateDecision(
                            place_id=item.candidate.place_id,
                            target_id=target,
                            date=day,
                            operation=operation,
                            disposition="excluded",
                            reason="target_geographic_policy_before_details",
                        )
                    )
                return
        if blocked(item.candidate.place_id) or not can_acquire():
            return
        if item.candidate.place_id in seen:
            budget.used["duplicate_hits"] += 1
            return
        try:
            processed = getattr(budget, "canonical_processed", set())
            if item.candidate.place_id in processed:
                budget.stops.append("canonical_already_attempted")
                return
            budget.canonical_processed = processed | {item.candidate.place_id}
            budget.charge(canonical=1)
        except RepairLimit:
            budget.stops.append("canonical_budget_exhausted")
            return
        if provider is None or item.candidate.place_id in excluded:
            return
        req = PlaceDetailsRequest(
            place_id=item.candidate.place_id, field_mask=PLACES_DETAILS_FIELD_MASK
        )
        dto = await budget.call(
            V1EvidenceAcquisitionService._place_details_cache_key(req),
            lambda: provider.get_place_details(req),
            charges={"details": 1},
            observed=getattr(provider, "observes_send_boundary", False),
            unwrap=True,
        )
        if dto is not None:
            try:
                admit(merge_details(item, dto), origin)
            except ValueError:
                budget.stops.append("invalid_details")

    old_attempt_start = budget.used["canonical"]
    # When discovery is available, retain up to two existing canonical/Details
    # attempts for it; reserve both remaining attempts and sends, never add budget.
    old_attempt_limit = (
        max(
            0,
            min(
                budget.limits["canonical"] - budget.used["canonical"],
                budget.limits["details"] - budget.used["details"],
            )
            - reserve,
        )
        if provider is not None and intent_ids
        else budget.limits["canonical"]
    )
    for item, origin in pending:
        if budget.used["canonical"] - old_attempt_start >= old_attempt_limit:
            budget.stops.append("old_details_discovery_reserve")
            break
        if not can_acquire():
            break
        await details(item, origin)
    preparing_old = False
    reasons = material_reasons()
    reserve = min(policy.exploration_positions, max(0, slots - len(pinned))) if reasons else 0
    baseline_ids = {r.place_id for r in eligible.values()}
    if reasons:
        budget.feedback_explored = True
    if provider is not None:
        for index in range(
            min(
                budget.limits["ordinary_google"],
                len({d for _, d, _, _ in targets}) * len(intent_ids),
            )
        ):
            iid = intent_ids[index % len(intent_ids)]
            if not can_acquire():
                break
            intent = intents[iid]
            target_day, geographic_scope = discovery_scope()
            record_opportunity(target_day, geographic_scope, "google")
            req = PlaceSearchRequest(
                text_query=f"{intent.query_text} in {context.contract.requirements.destination}",
                page_size=policy.acquisition.top_k,
                field_mask=PLACES_CANDIDATE_FIELD_MASK,
                location_bias=None
                if geographic_scope is None
                else LatLng(
                    latitude=geographic_scope.latitude, longitude=geographic_scope.longitude
                ),
            )
            bias = (
                None
                if req.location_bias is None
                else (req.location_bias.latitude, req.location_bias.longitude)
            )
            key = (
                "places_search",
                req.text_query.casefold(),
                req.page_size,
                req.field_mask,
                req.include_future_opening_businesses,
                bias,
                req.language_code,
            )
            response = await budget.call(
                key,
                lambda req=req: provider.search_text(req),
                charges={"google": 1},
                audit={"date": str(target_day), "intent_id": iid},
                timeout=budget.rag_config.google_timeout,
                observed=getattr(provider, "observes_send_boundary", False),
                unwrap=True,
            )
            if response is None:
                continue
            budget.used["raw_discovery_hits"] += len(response.candidates)
            for dto in response.candidates[: policy.acquisition.top_k]:
                item = normalize_place_search_hit(
                    dto,
                    intent_id=iid,
                    source_query=req.text_query,
                    actual_result_count=response.actual_result_count,
                )
                await details(item, "google")
    target_day, geographic_scope = discovery_scope()
    # One optional RAG query; its failure leaves all qualified candidates intact.
    if (
        can_acquire()
        and rag is not None
        and geographic_scope is not None
        and intent_ids
        and provider is not None
    ):
        intent = intents[intent_ids[0]]
        record_opportunity(target_day, geographic_scope, "rag")
        query = RetrievalQuery(
            query_id="repair_query_1",
            text=" ".join(unicodedata.normalize("NFKC", intent.query_text).split()),
            origin="user",
            intent_ids=(intent.intent_id,),
            requirement_refs=intent.requirement_refs,
        )
        if hasattr(rag, "allows_embedding") and not rag.allows_embedding([query.text]):
            budget.stops.append("previous_rag_failure")
            return await finish()
        vector = await budget.call(
            ("rag_embedding", SPACE_ID, query.text),
            lambda: _embed_one(rag, query.text),
            charges={"embedding": 1},
            timeout=budget.rag_config.embedding_timeout,
        )
        if vector is not None:
            if hasattr(rag, "allows_search") and not rag.allows_search(vector, geographic_scope):
                budget.stops.append("previous_rag_failure")
                return await finish()
            rows = await budget.call(
                (
                    "rag_retrieval",
                    SPACE_ID,
                    rag.artifact_hash,
                    POLICY_VERSION,
                    geographic_scope.model_dump_json(),
                    policy.acquisition.top_k,
                    query.text,
                ),
                lambda: rag.search(vector, geographic_scope, policy.acquisition.top_k),
                charges={"retrieval": 1},
                timeout=budget.rag_config.sql_timeout,
            )
            resolver = RepairResolver(provider, budget, geographic_scope, blocked)
            for row in (rows or ())[: policy.acquisition.top_k]:
                try:
                    if not can_acquire():
                        break
                    entity = RetrievalEntity.model_validate(row["entity"])
                    if entity.google_place_id and blocked(entity.google_place_id):
                        continue
                    processed = getattr(budget, "canonical_processed", set())
                    entity_key = entity.google_place_id or entity.model_dump_json()
                    if entity_key in processed:
                        continue
                    budget.canonical_processed = processed | {entity_key}
                    budget.charge(canonical=1)
                    if (
                        entity.latitude is None
                        or entity.longitude is None
                        or entity.eligibility_hint == "ineligible"
                    ):
                        continue
                    if entity.google_place_id in excluded:
                        continue
                    value, method = await resolver.resolve(entity)
                    if value is None:
                        continue
                    items = {}
                    resolver.attach(items, value.place_id, entity, [(query, row)], method, value)
                    admit(merge_details(items[value.place_id], value), "rag")
                except RepairLimit:
                    budget.stops.append("canonical_budget_exhausted")
                    break
                except (ValueError, KeyError, TypeError):
                    budget.stops.append("invalid_rag_candidate")
    return await finish()


async def _embed_one(rag, text):
    values = await rag.embed([text])
    if len(values) != 1:
        raise ValueError("Expected one query vector")
    return values[0]


def spatial_candidate_options(chosen, scheduled, auth, ledger, policy, mode):
    """Bounded pair associations from actual projected identities, not verified routes."""
    from backend.app.versions.v3.repair_spatial import distance_km

    spatial_options = []
    ordered_ids = sorted(chosen - scheduled)
    for index, left in enumerate(ordered_ids):
        for right in ordered_ids[index + 1 :]:
            dates = sorted(
                {r.date for r in auth if r.place_id == left}
                & {r.date for r in auth if r.place_id == right}
            )
            distance = distance_km(ledger[left].place, ledger[right].place)
            radius = (
                policy.spatial.walk_radius_km
                if mode in (None, "WALK")
                else policy.spatial.motor_radius_km
            )
            if dates and distance is not None and distance <= radius:
                spatial_options.append(
                    {
                        "place_ids": [left, right],
                        "dates": [str(d) for d in dates],
                        "distance_km": round(distance, 3),
                        "basis": "coordinate_prefilter_not_route",
                    }
                )
    return tuple(spatial_options)
