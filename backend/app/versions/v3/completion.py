"""Final Rich completion, distinct from accepted edits and a finished invocation."""

from datetime import timedelta


def rich_completion(after, contract, *, review_enabled, changed):
    rows = {f.dates[0]: f for f in after.findings if f.check == "soft_pace"}
    policies = {p.date: p.model_dump(mode="json") for p in contract.daily_pace or ()}
    default = policies.get(None, {})
    request = contract.requirements
    dates = (
        request.start_date + timedelta(days=index)
        for index in range((request.end_date - request.start_date).days + 1)
    )
    days = []
    for day in dates:
        finding = rows.get(day)
        evidence = finding.adopted_evidence if finding else {}
        policy = policies.get(day, default)
        if policy.get("profile") != "rich" and not (
            default.get("profile") == "rich" and policy.get("profile") == "unresolved"
        ):
            continue
        count = evidence.get("count") if finding and finding.magnitude is not None else None
        projection = evidence.get("hard_count_projection") or {}
        override = (
            "full_day_protection"
            if evidence.get("time_protection_projection")
            else "explicit_count"
            if policy.get("exact_count") is not None
            else "hard_count"
            if projection.get("minimum_count", 0) > 3
            else None
        )
        targets = evidence.get("zero_counts", ())
        if count is None:
            state = "unavailable"
        elif override:
            state = "source_overridden" if finding.magnitude == 0 else "residual"
        else:
            state = "satisfied" if count == 3 else "residual"
        days.append(
            {
                "date": str(day),
                "count": count,
                "target_count": min(targets) if override and targets else 3,
                "override": override,
                "state": state,
            }
        )
    if not days:
        return None

    # These are explicitly unverified capabilities, not executable return checks.
    # The original validation report retains their limitations even on completion.
    unverified = [
        f
        for f in after.findings
        if f.status == "UNKNOWN"
        and f.check not in {"budget", "visitor_suitability"}
        and f.reason != "open_semantics_not_executable_predicates"
    ]
    failures = [f for f in after.findings if f.status == "CONFIRMED"]
    states = {day["state"] for day in days}
    if not review_enabled:
        status = "not_attempted"
    elif failures or "residual" in states:
        status = "partial"
    elif unverified or "unavailable" in states:
        status = "unavailable"
    elif states == {"source_overridden"}:
        status = "source_overridden"
    else:
        status = "complete" if changed else "already_satisfied"
    return {
        "status": status,
        "days": days,
        "blocking_findings": [f.finding_id for f in (*failures, *unverified)],
        "unverified_checks": sorted({f.check for f in unverified}),
    }
