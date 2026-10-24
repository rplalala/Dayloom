"""Observable product-policy progress; semantic judgments stay separate from facts."""

from collections import Counter, defaultdict

from backend.app.policies.category_visits import (
    category_visit_target,
    required_category_progress,
    required_category_visit,
)
from backend.app.policies.visit_multiplicity import (
    excess_visits,
    is_primary_visit,
    named_visit_issues,
)
from backend.app.schemas.interpreted_requirements import SoftCoverageTarget, soft_coverage_eligible


def goal_progress(itinerary, contract, assessments):
    rows = {r.place_id: r for r in assessments}
    visits = [
        (d.date, a)
        for d in itinerary.days
        for a in d.activities
        if is_primary_visit(a, assessments)
    ]
    progress = []
    for req in contract.semantic_requirements:
        goal = req.experience_goal
        soft = (req.soft_coverage or SoftCoverageTarget()) if soft_coverage_eligible(req) else None
        if not goal or req.polarity != "favor" or (goal.frequency == "continuing" and not soft):
            continue
        required = required_category_visit(req)
        if not rows and not soft and not required:
            continue
        expected = soft.target if soft else goal.count or 1
        matched = [
            (d, a)
            for d, a in visits
            if a.source_place_id in rows
            and rows[a.source_place_id].main_eligible
            and any(
                m.requirement_id == req.requirement_id and m.relation == "supported"
                for m in rows[a.source_place_id].matches
            )
        ]
        count = (
            len({a.source_place_id for _, a in matched})
            if goal.target == "category"
            else len(matched)
        )
        matched_dates = len({d for d, _ in matched})
        uncertain = not rows or any(
            a.source_place_id not in rows
            or rows[a.source_place_id].role == "unresolved"
            or not any(
                m.requirement_id == req.requirement_id for m in rows[a.source_place_id].matches
            )
            or any(
                m.requirement_id == req.requirement_id and m.relation == "unresolved"
                for m in rows[a.source_place_id].matches
            )
            for _, a in visits
        )
        satisfied = (
            count >= expected
            if soft
            else (count == goal.count if goal.frequency == "exact" else count >= expected)
            and (not goal.distinct_dates or matched_dates >= expected)
        )
        if required and goal.frequency == "exact" and uncertain:
            satisfied = False
        progress.append(
            dict(
                requirement_id=req.requirement_id,
                expected=expected,
                matched=count,
                matched_dates=matched_dates,
                satisfied=satisfied,
                **(
                    required_category_progress(
                        req, assessments, count=count, uncertain=uncertain, satisfied=satisfied,
                    )
                    if required else {}
                ),
                **(
                    dict(
                        soft=True,
                        preference=req.normalized_text,
                        target_origin=soft.origin,
                        focus_source=soft.focus_source.model_dump() if soft.focus_source else None,
                        remaining=max(0, expected - count),
                        coverage_status="covered"
                        if satisfied
                        else "unassessed"
                        if uncertain
                        else "gap",
                    )
                    if soft
                    else {}
                ),
                basis="model_semantic_judgment_not_operating_fact",
            )
        )
    return tuple(progress)


def semantic_policy_issues(itinerary, contract, assessments=(), resolutions=()):
    rows = {r.place_id: r for r in assessments}
    visits = defaultdict(list)
    exceptions = Counter()
    issues = []
    for day in itinerary.days:
        for activity in day.activities:
            if not is_primary_visit(activity, assessments):
                continue
            pid = activity.source_place_id
            if pid:
                visits[pid].append(activity)
            if not rows:
                continue
            row = rows.get(pid)
            if row is None or not row.main_eligible:
                issues.append(
                    {"reason": "primary_role_unqualified", "activity_id": activity.activity_id}
                )
            elif row.role == "exception_only":
                # One visit can fulfill multiple supported exceptions, but is one identity.
                exceptions.update(row.exception_requirement_ids)
    for pid, items in visits.items():
        excess = excess_visits(items, contract, resolutions, pid)
        if len(items) > 1 and (excess is None or excess > 0):
            issues.append(
                {
                    "reason": "visit_multiplicity_unassessed"
                    if excess is None
                    else "unauthorized_repeat",
                    "place_id": pid,
                    "excess": excess,
                }
            )
    progress = {r["requirement_id"]: r for r in goal_progress(itinerary, contract, assessments)}
    for req in contract.semantic_requirements:
        goal = req.experience_goal
        row = progress.get(req.requirement_id)
        target = category_visit_target(req)
        if row and row.get("required") and row["status"] == "unverified":
            issues.append({
                "reason": "required_category_unverified", "requirement_id": req.requirement_id,
            })
            continue
        if (
            target is not None
            and row
            and row["matched"] < target
        ):
            issues.append(
                {
                    "reason": "experience_goal_count_unmet",
                    "requirement_id": req.requirement_id,
                    "shortfall": target - row["matched"],
                }
            )
        if (
            goal
            and goal.target == "category"
            and goal.frequency == "exact"
            and row
            and row["matched"] > goal.count
        ):
            issues.append(
                {
                    "reason": "experience_goal_count_exceeded",
                    "requirement_id": req.requirement_id,
                    "excess": row["matched"] - goal.count,
                }
            )
        if (
            goal
            and goal.target == "category"
            and goal.distinct_dates
            and goal.frequency in {"exact", "minimum"}
            and row
            and row["matched"] >= goal.count
            and row["matched_dates"] < goal.count
        ):
            issues.append(
                {
                    "reason": "experience_goal_dates_unmet",
                    "requirement_id": req.requirement_id,
                    "shortfall": goal.count - row["matched_dates"],
                }
            )
        if goal and goal.explicit_primary_exception and goal.frequency != "minimum":
            if exceptions[req.requirement_id] > (goal.count or 1):
                issues.append(
                    {
                        "reason": "primary_exception_allowance_exceeded",
                        "requirement_id": req.requirement_id,
                    }
                )
    named = {n.requirement_id for n in contract.named_places}
    for ref, count in exceptions.items():
        if ref in named:
            specs = [v for v in contract.visit_requirements or () if v.requirement_id == ref]
            exact = [v.exact_visits for v in specs if v.exact_visits is not None]
            if not exact and any(v.minimum_visits > 1 for v in specs):
                continue
            if count > (min(exact) if exact else 1):
                issues.append(
                    {"reason": "primary_exception_allowance_exceeded", "requirement_id": ref}
                )
    if rows or resolutions:
        issues.extend(named_visit_issues(itinerary, contract, resolutions, assessments))
    return tuple(issues)
