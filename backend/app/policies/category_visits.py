"""Bounded category visit obligations; matching remains evidence-based semantic judgment."""


def required_category_visit(requirement):
    """Recognize an executable shape, without interpreting words or certifying a venue."""
    goal = requirement.experience_goal
    return bool(
        goal
        and requirement.strength == "hard"
        and requirement.polarity == "favor"
        and requirement.scope in {"individual_poi", "selected_poi_set", "whole_trip"}
        and requirement.subject_refs == ("party",)
        and goal.target == "category"
        and goal.frequency in {"one_off", "minimum", "exact"}
        and goal.trip_scope == "ordinary"
    )


def category_visit_target(requirement):
    """Explicit count goals and required one-off visits share the existing supply/Repair path."""
    goal = requirement.experience_goal
    if not goal or requirement.polarity != "favor" or goal.target != "category":
        return None
    if goal.frequency in {"exact", "minimum"}:
        return goal.count
    return 1 if required_category_visit(requirement) else None


def required_category_progress(requirement, assessments, *, count, uncertain, satisfied):
    """Explain observed coverage without inferring feasibility from a search shortfall."""
    goal = requirement.experience_goal
    target = goal.count or 1
    confirmed_excess = goal.frequency == "exact" and count > target
    status = (
        "satisfied"
        if satisfied
        else "unverified"
        if uncertain and not confirmed_excess
        else "unmet"
    )
    supported = any(
        row.main_eligible
        and any(
            m.requirement_id == requirement.requirement_id and m.relation == "supported"
            for m in row.matches
        )
        for row in assessments
    )
    unavailable = not assessments or any(
        row.role == "unresolved"
        or not any(
            m.requirement_id == requirement.requirement_id and m.relation != "unresolved"
            for m in row.matches
        )
        for row in assessments
    )
    if satisfied:
        reason = "supported_visit_coverage"
    elif status == "unverified":
        reason = "matching_evidence_incomplete"
    elif supported:
        reason = "required_visits_not_scheduled"
    else:
        reason = "matching_evidence_incomplete" if unavailable else "no_confirmed_match"
    return dict(
        required=True,
        requirement=requirement.normalized_text,
        source_quotes=[s.quote for s in requirement.source_refs],
        frequency=goal.frequency,
        status=status,
        reason=reason,
    )


def protect_required_categories(original, proposed, contract, assessments):
    """Protect attained hard obligations during local edits, deletion and day replanning."""
    from backend.app.policies.poi_semantic_output import goal_progress

    before = {r["requirement_id"]: r for r in goal_progress(original, contract, assessments)}
    requirements = {r.requirement_id: r for r in contract.semantic_requirements}
    for row in goal_progress(proposed, contract, assessments):
        if not row.get("required"):
            continue
        previous = before[row["requirement_id"]]
        if (
            min(row["matched"], row["expected"]) < min(previous["matched"], previous["expected"])
            or previous["satisfied"]
            and not row["satisfied"]
            or min(row["matched_dates"], row["expected"])
            < min(previous["matched_dates"], previous["expected"])
            and requirements[row["requirement_id"]].experience_goal.distinct_dates
        ):
            raise ValueError("Required category visit satisfaction decreased")
