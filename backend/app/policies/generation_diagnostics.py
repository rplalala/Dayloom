"""Observe declared activity roles without text interpretation, mutation or tools."""

import unicodedata
from collections import Counter
from datetime import timedelta

from backend.app.policies.visit_multiplicity import is_primary_visit
from backend.app.schemas.generation_diagnostics import (
    DayGenerationDiagnostics,
    GenerationDiagnostics,
)


def observe_generation(
    itinerary,
    requirements,
    *,
    reference_date,
    supplied_ids=None,
    related_requirement_ids=(),
    contract=None,
    schedule=None,
    places=(),
    blank_policy=None,
    semantic_assessments=(),
    named_resolutions=(),
):
    """Count only main visits; canonical mode requires the validated supply ledger.

    Missing roles and unresolved main identities are explicitly unassessable. Default
    misses are observations, even when user pace or evidence justifies fewer visits.
    V0 name equality is a proxy, never canonical identity or semantic deduplication.
    """
    from backend.app.policies.minimum_coverage import minimum_coverage

    if schedule is None and contract is not None:
        from backend.app.policies.itinerary_schedule import build_schedule

        schedule = build_schedule(itinerary, contract, places)
        from types import SimpleNamespace

        from backend.app.policies.itinerary_schedule import prepare_blank_windows
        from backend.app.runtime.config_loader import load_runtime_config

        schedule = prepare_blank_windows(
            itinerary,
            SimpleNamespace(
                schedule=schedule,
                contract=contract,
                places=places,
            ),
            blank_policy or load_runtime_config().v3_repair,
        )
    canonical = supplied_ids is not None
    semantic_rows = {r.place_id: r for r in semantic_assessments}
    supplied = set(supplied_ids or ())
    by_date = {day.date: day for day in itinerary.days}
    rows, seen = [], set()
    cross_day = 0
    day_date = requirements.start_date
    while day_date <= requirements.end_date:
        day = by_date.get(day_date)
        activities = day.activities if day else ()
        roles = Counter(a.activity_kind for a in activities)
        keys = []
        unclassified = sum(
            a.activity_kind == "unknown" and not is_primary_visit(a, semantic_assessments)
            for a in activities
        )
        for activity in activities:
            if not is_primary_visit(activity, semantic_assessments):
                continue
            if canonical:
                key = activity.source_place_id if activity.source_place_id in supplied else None
                if key in semantic_rows and semantic_rows[key].role == "non_main":
                    continue  # A known non-main object is not an unknown visit identity.
                if semantic_rows and (
                    key not in semantic_rows or not semantic_rows[key].main_eligible
                ):
                    key = None
            else:
                name = unicodedata.normalize("NFKC", activity.place_name or "")
                key = " ".join(name.split()).casefold() or None
            if key is None:
                unclassified += 1
            else:
                keys.append(key)
        unique = set(keys)
        cross_day += len(unique & seen)
        seen.update(unique)
        same_day = day_date == reference_date
        count = len(unique)
        status = (
            "not_assessable"
            if same_day or unclassified
            else "below_target"
            if count < 2
            else "above_target"
            if count > 5
            else "within_target"
        )
        minimum, minimum_reason, minimum_refs = minimum_coverage(
            day_date, count, unclassified, same_day=same_day, contract=contract, schedule=schedule
        )
        rows.append(
            DayGenerationDiagnostics(
                date=day_date,
                day_present=day is not None,
                applicability="same_day_remaining_hours_unsupported"
                if same_day
                else "default_full_day",
                count_basis="canonical_id" if canonical else "name_proxy",
                main_activity_count=len(keys),
                distinct_main_poi_count=count,
                repeated_main_poi_count=len(keys) - count,
                generic_activity_count=roles["generic_activity"],
                transport_activity_count=roles["transport"],
                free_time_activity_count=roles["free_time"],
                unclassified_activity_count=unclassified,
                target_status=status,
                empty_day=not activities,
                minimum_coverage=minimum,
                minimum_coverage_reason=minimum_reason,
                minimum_coverage_evidence=minimum_refs,
            )
        )
        day_date += timedelta(days=1)
    statuses = Counter(row.target_status for row in rows)
    from backend.app.policies.poi_semantic_output import goal_progress, semantic_policy_issues

    issues = (
        semantic_policy_issues(itinerary, contract, semantic_assessments, named_resolutions)
        if contract
        else ()
    )
    issues += tuple(
        {"reason": "minimum_daily_coverage_missing", "date": str(r.date)}
        for r in rows
        if r.minimum_coverage == "missing"
    )
    from backend.app.policies.daily_visit_constraints import assess_daily_visits

    daily_counts = (
        assess_daily_visits(itinerary, contract, semantic_assessments) if contract else ()
    )
    issues += tuple(
        {
            "reason": "daily_visit_count_unmet",
            "date": str(r.date),
            "requirement_ids": r.requirement_ids,
            "status": r.status,
        }
        for r in daily_counts
        if r.strength == "hard" and r.status != "PASS"
    )
    return GenerationDiagnostics(
        daily_visit_counts=daily_counts
        if contract and contract.daily_visit_constraints is not None
        else None,
        goal_progress=goal_progress(itinerary, contract, semantic_assessments)
        if contract and canonical
        else (),
        policy_completion="incomplete"
        if issues or any(r.minimum_coverage == "missing" for r in rows)
        else "complete"
        if semantic_rows
        and contract
        and contract.contract_version
        in (
            "interpreted_requirements_4",
            "interpreted_requirements_5",
            "interpreted_requirements_6",
        )
        and contract.visit_requirements is not None
        else "unassessed",
        policy_issues=issues,
        days=tuple(rows),
        days_meeting_default_target=statuses["within_target"],
        days_below_target=statuses["below_target"],
        days_above_target=statuses["above_target"],
        days_unassessable=statuses["not_assessable"],
        empty_days=sum(d.empty_day for d in rows),
        days_with_zero_main_pois=sum(d.distinct_main_poi_count == 0 for d in rows),
        scheduled_unique_supply=len(seen) if canonical else None,
        unused_supply=len(supplied - seen) if canonical else None,
        cross_day_repeated_visits=cross_day,
        related_requirement_ids=tuple(related_requirement_ids),
    )
