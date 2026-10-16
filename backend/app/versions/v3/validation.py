"""Pure V3 checks over an existing snapshot. No acquisition, model or repair calls."""

from collections import defaultdict
from itertools import combinations

from backend.app.evidence.effective_models import EffectivePlaceEvidence
from backend.app.evidence.models import PlaceEvidence, RouteEvidenceBundle
from backend.app.policies.generation_diagnostics import observe_generation
from backend.app.policies.itinerary_output import validate_output_sources
from backend.app.policies.poi_funnel import NamedPlaceResolution
from backend.app.policies.trip_dates import TripDateWindow, validate_itinerary_dates
from backend.app.policies.visit_multiplicity import is_primary_visit
from backend.app.schemas.interpreted_requirements import InterpretedTripRequirements
from backend.app.schemas.itinerary import Itinerary
from backend.app.versions.v3.models import (
    Finding,
    ImprovementTarget,
    PlaceUseObservation,
    ValidationPolicy,
    ValidationReport,
)


def validate_draft(
    itinerary: Itinerary,
    contract: InterpretedTripRequirements,
    *,
    window: TripDateWindow,
    supplied_ids: tuple[str, ...],
    places: tuple[PlaceEvidence, ...],
    named_resolutions: tuple[NamedPlaceResolution, ...] = (),
    effective_places: tuple[EffectivePlaceEvidence, ...] = (),
    routes: RouteEvidenceBundle | None = None,
    policy: ValidationPolicy | None = None,
    route_evidence: tuple = (),
    transitions: tuple = (),
    original_supply_ids: tuple[str, ...] | None = None,
    schedule=None,
    visit_bindings=(),
    semantic_assessments=(),
) -> ValidationReport:
    """Validate already accepted application inputs, without changing even array order.

    Shared schema/source/date errors still raise at the shared boundary. Nearby is
    ignored, never promoted to primary supply. Effective facts must be outputs of the
    existing official evidence resolver, not model-authored or TripWorld priors.
    """
    policy = policy or ValidationPolicy()
    # Reuse shared checks on a detached primary-only copy; discard normalization.
    primary = itinerary.model_copy(deep=True, update={"reference_recommendations": []})
    validate_output_sources(primary, places=places, supplied_ids=supplied_ids)
    from backend.app.policies.transport_constraints import validate_restricted_transport

    validate_restricted_transport(primary, contract.transport_constraint)
    validate_itinerary_dates(contract.requirements, primary, window)
    by_id = {p.place_id: p for p in places}
    effective = {p.place_id: p for p in effective_places}
    if len(by_id) != len(places) or len(effective) != len(effective_places):
        raise ValueError("Duplicate evidence identity")
    if not set(effective) <= set(by_id):
        raise ValueError("Effective evidence must belong to supplied Details snapshot")
    diagnostics = observe_generation(
        itinerary,
        contract.requirements,
        reference_date=window.reference_date,
        contract=contract,
        schedule=schedule,
        places=places,
        semantic_assessments=semantic_assessments,
        named_resolutions=named_resolutions,
        supplied_ids=supplied_ids,
        related_requirement_ids=tuple(r.requirement_id for r in contract.semantic_requirements),
    )
    if original_supply_ids is not None:
        scheduled = {
            a.source_place_id
            for d in itinerary.days
            for a in d.activities
            if a.activity_kind == "main_poi" and a.source_place_id
        }
        original_ids = set(original_supply_ids)
        diagnostics = diagnostics.model_copy(
            update={
                "unused_supply": len(original_ids - scheduled),
                "scheduled_unique_supply": len(original_ids & scheduled),
            }
        )
    findings = []

    def add(check, status, reason, **kwargs):
        findings.append(
            Finding(
                finding_id=f"finding_{len(findings) + 1}",
                check=check,
                status=status,
                reason=reason,
                is_violation=status == "CONFIRMED",
                **kwargs,
            )
        )

    judgments = {r.place_id: r for r in semantic_assessments}
    for issue in diagnostics.policy_issues:
        if issue["reason"] == "experience_goal_count_unmet":
            add(
                "semantic_requirements",
                "CONFIRMED",
                issue["reason"],
                requirement_ids=(issue["requirement_id"],),
                magnitude=issue["shortfall"],
                evidence_refs=(f"requirements:{issue['requirement_id']}",),
                adopted_evidence={"basis": "supported_visit_count_not_operating_fact"},
            )
            continue
        if issue["reason"] not in {
            "primary_role_unqualified",
            "primary_exception_allowance_exceeded",
            "experience_goal_count_exceeded",
            "experience_goal_dates_unmet",
        }:
            continue
        rid = issue.get("requirement_id")
        affected = [
            (d.date, a)
            for d in itinerary.days
            for a in d.activities
            if is_primary_visit(a, semantic_assessments)
            and (
                a.activity_id == issue.get("activity_id")
                or (
                    rid
                    and a.source_place_id in judgments
                    and (
                        rid in judgments[a.source_place_id].exception_requirement_ids
                        or (
                            issue["reason"]
                            in {"experience_goal_count_exceeded", "experience_goal_dates_unmet"}
                            and any(
                                m.requirement_id == rid and m.relation == "supported"
                                for m in judgments[a.source_place_id].matches
                            )
                        )
                    )
                )
            )
        ]
        if not affected:
            continue
        known = all(
            a.source_place_id in judgments and judgments[a.source_place_id].role != "unresolved"
            for _, a in affected
        )
        add(
            "primary_policy",
            "CONFIRMED" if known else "UNKNOWN",
            issue["reason"],
            dates=tuple(sorted({d for d, _ in affected})),
            activity_ids=tuple(a.activity_id for _, a in affected),
            place_ids=tuple(sorted({a.source_place_id for _, a in affected if a.source_place_id})),
            requirement_ids=(rid,) if rid else (),
            magnitude=issue.get("excess", issue.get("shortfall", 1)),
            evidence_refs=("application:primary_role_policy_1",),
            adopted_evidence={"basis": "semantic_judgment_and_product_policy_not_operating_fact"},
        )
    from backend.app.policies.daily_visit_constraints import assess_daily_visits, hard_exact_count

    for count in assess_daily_visits(itinerary, contract, semantic_assessments):
        status = count["status"]
        add(
            "daily_visit_count",
            "CONFIRMED"
            if status == "FAIL" and count["strength"] == "hard"
            else "NEEDS_REVIEW"
            if status == "FAIL"
            else status,
            "daily_visit_count",
            dates=(count["date"],),
            activity_ids=(*count["activity_ids"], *count["potential_activity_ids"]),
            requirement_ids=count["requirement_ids"],
            evidence_refs=count["source_refs"],
            magnitude=max(
                0,
                count["count"] - count["upper"],
                count["lower"] - count["count"] if count["mode"] == "exact" else 0,
            )
            if status != "UNKNOWN"
            else None,
            adopted_evidence={
                "constraint_id": count["constraint_id"],
                "count": count["count"],
                "mode": count["mode"],
                "lower": count["lower"],
                "upper": count["upper"],
                "strength": count["strength"],
            },
        )
    for row in diagnostics.days:
        count = row.distinct_main_poi_count
        if row.minimum_coverage == "missing":
            add(
                "coverage",
                "CONFIRMED",
                "minimum_daily_coverage_missing",
                dates=(row.date,),
                magnitude=1,
                evidence_refs=row.minimum_coverage_evidence,
                adopted_evidence={"rule": "minimum_daily_coverage_1", "required_count": 1},
            )
            continue
        if row.minimum_coverage == "exempt":
            continue
        if hard_exact_count(contract, row.date) is not None:
            continue  # The sourced daily count supersedes a default quantity review.
        if row.minimum_coverage == "unknown" and count == 0:
            add("coverage", "UNKNOWN", row.minimum_coverage_reason, dates=(row.date,))
            continue
        if (
            row.target_status == "not_assessable"
            or count < policy.daily_main_min
            or count > policy.daily_main_max
        ):
            add(
                "overfull"
                if count > policy.daily_main_max and row.target_status != "not_assessable"
                else "coverage",
                "UNKNOWN" if row.target_status == "not_assessable" else "NEEDS_REVIEW",
                "default_target_observation_without_executable_exception_contract",
                dates=(row.date,),
                evidence_refs=(f"generation_diagnostics:{row.date}",),
            )

    if schedule is not None:
        for day in itinerary.days:
            if str(day.date) in schedule.unresolved_dates:
                add(
                    "semantic_requirements",
                    "UNKNOWN",
                    "scoped_time_protection_unresolved",
                    dates=(day.date,),
                )
            for a in day.activities:
                if a.activity_kind == "free_time" or a.time_use == "free_window":
                    continue  # Rest placeholders may cover fixed rest; visits may not.
                for fixed in schedule.fixed:
                    if a.start_time.utcoffset() is None:
                        continue  # Existing overlap checks preserve timezone uncertainty.
                    overlap = (
                        min(a.end_time, fixed.end) - max(a.start_time, fixed.start)
                    ).total_seconds()
                    if overlap > 0:
                        add(
                            "semantic_requirements",
                            "CONFIRMED"
                            if a.activity_kind == "main_poi" or a.time_use == "scheduled"
                            else "UNKNOWN",
                            "fixed_user_time_overlap"
                            if a.activity_kind == "main_poi" or a.time_use == "scheduled"
                            else "activity_time_protection_relationship_unbound",
                            dates=(day.date,),
                            activity_ids=(a.activity_id,),
                            requirement_ids=(fixed.root_activity_id,),
                            magnitude=overlap,
                            evidence_refs=(fixed.source,),
                        )

    activities = [a for day in itinerary.days for a in day.activities]
    scheduled = {a.source_place_id for a in activities if a.source_place_id}
    visits = defaultdict(list)
    for a in activities:
        if is_primary_visit(a, semantic_assessments) and a.source_place_id:
            visits[a.source_place_id].append(a)
    for pid, items in visits.items():
        if len(items) > 1:
            from backend.app.policies.visit_multiplicity import excess_visits

            excess = excess_visits(items, contract, named_resolutions, pid)
            if excess == 0:
                continue
            add(
                "repetition",
                "CONFIRMED" if excess is not None else "UNKNOWN",
                "unauthorized_repeat_product_policy"
                if excess is not None
                else "visit_multiplicity_unassessed",
                evidence_refs=("product_policy:canonical_visit_multiplicity_1",),
                adopted_evidence={"basis": "product_policy_not_provider_fact"},
                magnitude=excess,
                place_ids=(pid,),
                activity_ids=tuple(a.activity_id for a in items),
                dates=tuple(sorted({a.start_time.date() for a in items})),
            )

    # Compare every pair, including nested and cross-day intervals. Mixed awareness
    # cannot be compared safely; wall-clock or prose assumptions are not introduced.
    for left, right in combinations([a for a in activities if a.time_use != "free_window"], 2):
        fields = dict(
            activity_ids=(left.activity_id, right.activity_id),
            dates=tuple(sorted({left.start_time.date(), right.start_time.date()})),
        )
        if (left.start_time.utcoffset() is None) != (right.start_time.utcoffset() is None):
            add("overlap", "UNKNOWN", "mixed_timezone_awareness", **fields)
        elif max(left.start_time, right.start_time) < min(left.end_time, right.end_time):
            add(
                "overlap",
                "CONFIRMED",
                "scheduled_intervals_overlap",
                evidence_refs=(
                    f"draft:activity:{left.activity_id}",
                    f"draft:activity:{right.activity_id}",
                ),
                **fields,
            )

    bindings = defaultdict(list)
    for resolution in named_resolutions:
        bindings[resolution.search_intent_id].append(resolution)
    known_requirements = {r.requirement_id for r in contract.named_places}
    if not set(bindings) <= known_requirements:
        raise ValueError("Named resolution has no canonical requirement provenance")
    for requirement in contract.named_places:
        if requirement.inclusion == "OPTIONAL" and not any(
            v.requirement_id == requirement.requirement_id
            for v in contract.visit_requirements or ()
        ):
            continue
        matches = bindings.get(requirement.requirement_id, [])
        resolution = matches[0] if len(matches) == 1 else None
        valid = (
            resolution is not None
            and resolution.status == "resolved"
            and resolution.resolved_place_id is not None
            and resolution.matching_place_ids == (resolution.resolved_place_id,)
            and resolution.named_place_intent.place_text == requirement.place_text
            and resolution.named_place_intent.source_text
            in {source.quote for source in requirement.source_refs}
        )
        if not valid:
            add(
                "named_requirement",
                "UNKNOWN",
                "missing_or_inconsistent_identity_binding",
                requirement_ids=(requirement.requirement_id,),
            )
            continue
        pid = resolution.resolved_place_id
        present = (
            any(
                a.source_place_id == pid and is_primary_visit(a, semantic_assessments)
                for a in activities
            )
            if requirement.inclusion == "REQUIRED"
            else pid in scheduled
        )
        conflict = (requirement.inclusion == "REQUIRED" and not present) or (
            requirement.inclusion == "EXCLUDED" and present
        )
        visit_specs = [
            v
            for v in contract.visit_requirements or ()
            if v.requirement_id == requirement.requirement_id
        ]
        executable = [v for v in visit_specs if v.status == "executable"]
        actual = [
            a
            for a in activities
            if is_primary_visit(a, semantic_assessments) and a.source_place_id == pid
        ]
        obligation_unmet = any(
            len(actual) < v.minimum_visits
            or (v.exact_visits is not None and len(actual) != v.exact_visits)
            or (v.distinct_dates and len({a.start_time.date() for a in actual}) < v.minimum_visits)
            or not set(v.dates) <= {a.start_time.date() for a in actual}
            for v in executable
        )
        from backend.app.versions.v3.repair_obligations import visit_binding

        mode_unverified = False
        for spec in executable:
            if not spec.access_mode:
                continue
            applicable = [
                a
                for a in actual
                if (binding := visit_binding(a, visit_bindings))
                and binding.mode == spec.access_mode
            ]
            if len(applicable) < spec.minimum_visits or not set(spec.dates) <= {
                a.start_time.date() for a in applicable
            }:
                mode_unverified = True
        conflict = conflict or obligation_unmet
        add(
            "named_requirement",
            "CONFIRMED"
            if conflict
            else "UNKNOWN"
            if mode_unverified or any(v.status == "unresolved" for v in visit_specs)
            else "PASS",
            "visit_requirement_unresolved"
            if not conflict
            and (mode_unverified or any(v.status == "unresolved" for v in visit_specs))
            else "required_visit_obligation_unmet"
            if obligation_unmet
            else "required_identity_omitted"
            if conflict and not present
            else "excluded_identity_scheduled"
            if conflict
            else "identity_inclusion_only",
            requirement_ids=(requirement.requirement_id,),
            place_ids=(pid,),
            evidence_refs=(
                f"requirements:{requirement.requirement_id}",
                f"named_resolution:{requirement.requirement_id}",
            ),
        )

    for activity in activities:
        if (
            not activity.source_place_id
            or activity.activity_kind in {"transport", "free_time"}
            or activity.time_use == "free_window"
        ):
            continue
        from backend.app.evidence.opening_hours import with_context_timezone

        place = with_context_timezone(
            by_id[activity.source_place_id],
            [
                by_id[a.source_place_id]
                for d in itinerary.days
                if d.date == activity.start_time.date()
                for a in d.activities
                if a.source_place_id in by_id
            ],
        )
        evidence = effective.get(place.place_id)
        from backend.app.versions.v3.repair_obligations import visit_binding

        binding = visit_binding(activity, visit_bindings)
        from backend.app.evidence.opening_hours import assess_opening

        status, reason, refs, magnitude, audit = assess_opening(activity, place, evidence, binding)
        fields = dict(
            activity_ids=(activity.activity_id,),
            place_ids=(place.place_id,),
            dates=(activity.start_time.date(),),
        )
        add(
            "opening",
            status,
            reason,
            evidence_refs=refs,
            magnitude=magnitude,
            adopted_evidence=audit,
            **fields,
        )
        add(
            "visitor_suitability",
            "UNKNOWN",
            "admission_reservation_and_special_area_unverified",
            adopted_evidence={
                "scheduling_policy": audit["policy"],
                "access_mode": audit["access_mode"],
                "reported_conditions": [
                    f.model_dump(mode="json")
                    for f in evidence.facts
                    if f.dimension
                    in {
                        "admission_policy",
                        "reservation_requirement",
                        "ticket_requirement",
                        "advance_ticket_purchase_requirement",
                    }
                    and f.source_refs
                    and (
                        not f.applicable_start_date
                        or f.applicable_start_date <= activity.start_time.date()
                    )
                    and (
                        not f.applicable_end_date
                        or f.applicable_end_date >= activity.start_time.date()
                    )
                ]
                if evidence
                else [],
                "unverified": [
                    "admission_eligibility",
                    "reservation_completion",
                    "ticket_possession",
                    "special_area_access",
                ],
            },
            evidence_refs=(place.source_ref,),
            **fields,
        )

    # Current Activity has no per-leg travel mode or departure applicability binding.
    # Even direct provider observations cannot certify the planned transition.
    route_refs = (
        ()
        if routes is None
        else tuple(r.source_ref for r in (routes.baseline, *routes.alternatives))
    )
    if transitions:
        from backend.app.versions.v3.repair_routes import check_transitions

        available_routes = (
            *route_evidence,
            *((routes.baseline, *routes.alternatives) if routes else ()),
        )
        for assessment in check_transitions(itinerary, transitions, available_routes, schedule):
            add("route", **assessment)
    else:
        add(
            "route",
            "UNKNOWN",
            "per_leg_mode_and_departure_binding_not_supported",
            evidence_refs=route_refs,
        )
    add("budget", "UNKNOWN", "verified_party_currency_cost_coverage_not_supported")
    daily_refs = {
        ref for rule in contract.daily_visit_constraints or () for ref in rule.requirement_refs
    }
    open_semantics = [
        r for r in contract.semantic_requirements if r.requirement_id not in daily_refs
    ]
    if open_semantics:
        add(
            "semantic_requirements",
            "UNKNOWN",
            "open_semantics_not_executable_predicates",
            requirement_ids=tuple(r.requirement_id for r in open_semantics),
        )
    from backend.app.versions.v3.soft_pace import measure_pace

    pace_rows = measure_pace(itinerary, contract, diagnostics, semantic_assessments)
    for row in pace_rows:
        penalty = row["penalty"]
        add(
            "soft_pace",
            "UNKNOWN" if penalty is None else "PASS" if penalty == 0 else "NEEDS_REVIEW",
            "soft_pace_unavailable" if penalty is None else "soft_pace_objective",
            dates=(row["date"],),
            activity_ids=row["activity_ids"],
            magnitude=penalty,
            evidence_refs=("policy:rtpeval_daily_density_2",),
            adopted_evidence={
                "count": row["count"],
                "zero_counts": row["zero_counts"],
                "policy": row["policy"],
                "is_failure_constraint": False,
            },
        )
    targets = tuple(
        ImprovementTarget(
            finding_id=f.finding_id,
            basis="confirmed_conflict" if f.status == "CONFIRMED" else "review_policy",
        )
        for f in findings
        if f.status == "CONFIRMED"
        or (
            f.status == "NEEDS_REVIEW"
            and f.check in policy.review_targets
            and not (
                f.check == "coverage"
                and "soft_pace" in policy.review_targets
                and any(row["date"] in f.dates and row["penalty"] is not None for row in pace_rows)
            )
        )
    )
    return ValidationReport(
        diagnostics=diagnostics,
        findings=tuple(findings),
        place_use_observations=tuple(
            PlaceUseObservation(
                place_id=pid, primary_type=by_id[pid].primary_type, source_ref=by_id[pid].source_ref
            )
            for pid in sorted(scheduled)
        ),
        improvement_targets=targets,
    )


def _opening(activity, place, evidence, binding=None):
    from backend.app.evidence.opening_hours import assess_opening

    return assess_opening(activity, place, evidence, binding)[:3]


def _opening_magnitude(activity, place, evidence):
    from backend.app.evidence.opening_hours import assess_opening

    return assess_opening(activity, place, evidence)[3]
