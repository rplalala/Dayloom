"""Active V1 acquisition adapter for deterministic planning candidate supply."""

from dataclasses import dataclass, replace

from backend.app.policies.planning_supply import (
    PlanningSupplyResult,
    SupplyCandidate,
    nomination_allowed,
    select_planning_supply,
)
from backend.app.policies.poi_capacity import apply_poi_operating_budgets, derive_poi_capacities
from backend.app.policies.poi_selection import POISelectionResult
from backend.app.schemas.interpreted_requirements import ClarificationRequired
from backend.app.services.candidate_acquisition import CandidateAcquisition, selection_record


@dataclass(frozen=True)
class PlanningSupplySelection:
    final_selection: POISelectionResult
    policy_result: PlanningSupplyResult
    profiles: tuple
    semantic_assessments: tuple = ()

    evaluator_calls = 0
    subset_enumerator_calls = 0

    @property
    def selected_place_ids(self):
        return self.policy_result.selected_place_ids


class PlanningCandidateSupplyPipeline:
    """Reuse bounded acquisition; never construct or call the historical evaluator."""

    completion_event = "planning_supply_completed"

    def __init__(self, acquisition, llm, tracer, llm_identity):
        self.acquisition = acquisition
        self.tracer = tracer
        self.candidate_acquisition = CandidateAcquisition(acquisition, llm, tracer, llm_identity)

    async def run(self, contract, destination, window):
        return await self.candidate_acquisition.run(contract, destination, window, supply=self)

    def capacities(self, requirements, window, *, contract=None):
        self._requirements, self._window = requirements, window
        self._contract = contract
        config = getattr(self.acquisition, "runtime_config", None)
        if config and config.resource_profile == "acceptance":
            from backend.app.policies.poi_capacity import acceptance_capacities

            if contract is None:
                raise ValueError("Acceptance supply requires the interpreted contract")
            return acceptance_capacities(contract, window, self.acquisition._budget.limits)
        if (
            getattr(self.acquisition, "runtime_config", None)
            and self.acquisition.runtime_config.acquisition.policy_id == "quality_first_1"
        ):
            from backend.app.policies.poi_capacity import quality_capacities

            return quality_capacities(requirements.start_date, requirements.end_date, window)
        return apply_poi_operating_budgets(
            derive_poi_capacities(requirements.start_date, requirements.end_date, window),
            self.acquisition._budget.limits,
        )

    def acquisition_order(self, places, required, associations, strengths, contract, destination):
        from backend.app.policies.acquisition_opportunities import opportunity_order

        config = getattr(self.acquisition, "runtime_config", None)
        return opportunity_order(
            places,
            required,
            contract,
            destination,
            exploration_fraction=config.poi_semantics.exploration_fraction
            if config and config.poi_semantics
            else 0,
        )

    def required_capacities(self, capacities, count):
        limits = self.acquisition._budget.limits
        config = getattr(self.acquisition, "runtime_config", None)
        if config and config.resource_profile == "acceptance":
            from backend.app.policies.poi_capacity import acceptance_capacities

            values = acceptance_capacities(self._contract, self._window, limits, count)
            self._normal_supply_capacity = values.k_final
            self.tracer.event("effective_acquisition_policy", {
                "policy_id": config.acquisition.policy_id,
                "resource_profile": config.resource_profile,
                "days": values.algorithmic.trip_days, "required": count,
                "capacity": values.c_raw, "new_success_target": values.r_pool,
                "supply_target": values.k_final, "review_cap": values.review_pool_cap,
                "limiting_budgets": values.limiting_budgets,
            })
            return values
        if config and config.acquisition.policy_id == "quality_first_1":
            from backend.app.policies.poi_capacity import quality_capacities

            self._normal_supply_capacity = capacities.k_final
            values = quality_capacities(
                self._requirements.start_date, self._requirements.end_date, self._window, count
            )
            effective = limits.model_copy(
                update={
                    "max_candidates": values.c_raw,
                    "max_place_detail_calls": config.budget.places.detail_calls,
                    "max_review_detail_calls": values.review_pool_cap,
                    "max_review_enriched_places": values.review_pool_cap,
                    "max_experience_profile_llm_calls": values.review_pool_cap,
                }
            )
            self.acquisition._budget.set_limits(effective)
            self.tracer.event(
                "effective_acquisition_policy",
                {
                    "policy_id": config.acquisition.policy_id,
                    "days": values.algorithmic.trip_days,
                    "required": count,
                    "normal_capacity": capacities.c_raw,
                    "normal_new_success_target": capacities.r_pool,
                    "normal_supply_target": capacities.k_final,
                    "normal_review_cap": capacities.review_pool_cap,
                    "capacity": values.c_raw,
                    "new_success_target": values.r_pool,
                    "send_cap": values.r_pool + 8,
                    "supply_target": values.k_final,
                    "review_cap": values.review_pool_cap,
                },
            )
            return values
        if count > min(limits.max_candidates, limits.max_place_detail_calls, limits.max_final_pois):
            raise ClarificationRequired("required_capacity_conflict")
        # Normal final capacity stays visible; only acquisition expands for required identities.
        return replace(
            capacities, c_raw=max(capacities.c_raw, count), r_pool=max(capacities.r_pool, count)
        )

    async def select(
        self,
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
    ):
        service = getattr(self.acquisition, "poi_semantics", None)
        judgments = service.ledger if service else None

        candidates = tuple(
            SupplyCandidate(
                place_id=p.candidate.place_id,
                primary_type=(
                    judgments[p.candidate.place_id].categories[0]
                    if judgments and judgments[p.candidate.place_id].categories
                    else p.structured_evidence.primary_type
                ),
                rating=p.rating,
                latitude=p.structured_evidence.latitude,
                longitude=p.structured_evidence.longitude,
                intent_ids=p.discovery_intent_ids,
                landmark_nomination=p.landmark_nomination,
            )
            for p in rich
            if (
                judgments is None
                or (
                    p.candidate.place_id in judgments
                    and judgments[p.candidate.place_id].main_eligible
                )
            )
            and nomination_allowed(
                p, contract, judgments.get(p.candidate.place_id) if judgments else None, required
            )
        )
        if judgments is not None and not set(required) <= {c.place_id for c in candidates}:
            from backend.app.schemas.poi_semantics import SemanticPreparationLimit

            raise SemanticPreparationLimit("required_primary_role_not_qualified")
        result = select_planning_supply(
            candidates,
            contract,
            required_ids=required,
            excluded_ids=excluded,
            capacity=getattr(self, "_normal_supply_capacity", capacities.k_final),
            hard_capacity=self.acquisition._budget.limits.max_final_pois,
            destination_coordinates=(destination.latitude, destination.longitude),
            profiles=profiles,
            semantic_assessments=judgments,
            semantic_config=service.config if service else None,
        )
        landmark_report = dict(getattr(self.acquisition, "landmark_diagnostics", {}))
        qualified_landmarks = {p.candidate.place_id for p in rich if p.landmark_nomination}
        qualified_landmarks &= {c.place_id for c in candidates}
        landmark_report.update(
            qualified=len(qualified_landmarks),
            selected=len(qualified_landmarks & set(result.selected_place_ids)),
        )
        if landmark_report and not qualified_landmarks:
            landmark_report["status"] = "degraded"
        self.tracer.event("landmark_discovery", landmark_report)
        result = result.model_copy(
            update={
                "acquisition_diagnostics": getattr(self.acquisition, "details_report", {}),
                "nomination_diagnostics": landmark_report,
                "landmarks": {
                    p.candidate.place_id: p.landmark_nomination
                    for p in rich
                    if p.landmark_nomination and p.candidate.place_id in result.selected_place_ids
                },
            }
        )
        final = selection_record(
            result.selected_place_ids,
            rich,
            required,
            contract.requirements.end_date,
            details=True,
        )
        return PlanningSupplySelection(
            final,
            result,
            tuple(profiles.values()),
            tuple(judgments[pid] for pid in result.selected_place_ids) if judgments else (),
        )


def planner_supply_projection(selection, contract):
    """The planner sees options, explicit must-visits, and evidence uncertainty."""
    result = selection.policy_result
    return {
        "contract_version": "planning_supply_1",
        "landmarks": {pid: row.model_dump() for pid, row in result.landmarks.items()},
        "poi_semantics": [r.model_dump(mode="json") for r in selection.semantic_assessments],
        "required_canonical_ids": result.required_canonical_ids,
        "optional_canonical_ids": result.optional_canonical_ids,
        "planning_supply_count": len(result.selected_place_ids),
        "supply_shortfall": result.shortfall,
        "semantics": [
            r.model_dump(exclude={"source_refs"}) for r in contract.semantic_requirements
        ],
        "subjects": [
            {"subject_id": "party", "label": "Travel party"},
            *[s.model_dump(exclude={"source_refs"}) for s in contract.subjects],
        ],
        "daily_visit_constraints": [
            r.model_dump(mode="json", exclude={"source_refs"})
            for r in contract.daily_visit_constraints or ()
        ],
        "review_evidence_relations": {
            pid: [r.model_dump() for r in result.profile_relations[pid]]
            for pid in result.selected_place_ids
        },
        "instructions": (
            "Use each canonical identity once unless a sourced visit requirement explicitly "
            "authorizes revisits. Exact counts and distinct dates must be respected. "
            "Dated daily_visit_constraints count all scheduled primary occurrences, including "
            "separate authorized visits to one place. Hard exact totals override default "
            "coverage and soft pace. Supporting meals, transport and references do not count. "
            "Satisfy one-off category goals, then prefer other unrepresented suitable experiences; "
            "continuing preferences are not quotas or a requirement for every visit. "
            "Use soft_coverage for distinct final scheduled coverage, not candidate counts. "
            "One/two targets saturate preference priority, never cap categories; "
            "Candidate opportunity limits retain replacements and are not fulfilled coverage. "
            "Landmark rank is model-origin soft guidance, not evidence of feasible dates, "
            "routes, opening, admission or costs. A landmark may match an already covered "
            "interest; do not remove its independent value or invent a fixed category ratio. "
            "retain alternatives "
            "and independent landmark value. Feasible soft gaps are allowed and must be disclosed. "
            "Semantic role judgments authorize primary choices, not operating facts. "
            "Exception alternatives share one request-level visit allowance. One Michelin meal "
            "does not authorize other ordinary restaurants. Indoor climbing is not mountain "
            "climbing; related alternatives do not prove exact requirement satisfaction. "
            "REQUIRED IDs are explicit user must-visits; preserve their canonical identities. "
            "OPTIONAL candidates are planning options: use a suitable subset, not every option. "
            "Attempt a coherent trip and preference alignment; soft trade-offs are allowed. "
            "UNKNOWN is neither failure nor satisfaction. Review relations are uncertain, "
            "review-supported judgments, not official facts or verified hard compliance. "
            "Do not assert unsupported local authenticity, quietness or family suitability. "
            "Supply size is not a mandatory visit count. An optional candidate may be scheduled "
            "or unused. Do not allocate references from this supply; the application handles "
            "nearby discovery after primary generation. "
            "Schedule feasibility is not validated."
        ),
    }
