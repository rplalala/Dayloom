"""Shared product coverage applicability; no semantic inference or provider access."""

MINIMUM_MISSING = "minimum_daily_coverage_missing"


def minimum_coverage(day, count, unclassified, *, same_day, contract=None, schedule=None):
    """Coverage measures concrete primary identity, not factual visit feasibility.

    An assessed empty protection list differs from historical/unassessed None.
    Fixed-interval exemption requires complete coverage of an existing planning
    window; no minimum visit duration or almost-full-day threshold is inferred.
    """
    protections = getattr(contract, "time_protections", None)
    from backend.app.policies.daily_visit_constraints import hard_exact_count

    if hard_exact_count(contract, day) == 0:
        return "exempt", "explicit_zero_sightseeing_count", (f"daily_visit_constraint:{day}",)
    relevant = [p for p in protections or () if not p.dates or day in p.dates]
    refs = tuple(p.model_dump_json() for p in relevant)
    if any(p.status == "fixed" and p.full_day is True for p in relevant):
        return "exempt", "explicit_full_day_user_commitment", refs
    if count:
        return "satisfied", "countable_primary_present_not_feasibility", ()
    if same_day or unclassified:
        return "unknown", "count_or_remaining_day_unassessable", ()
    if protections is None or any(p.status == "unresolved" for p in relevant):
        return "unknown", "coverage_applicability_unassessed", refs
    if schedule is not None:
        from backend.app.policies.itinerary_schedule import subtract

        if str(day) in schedule.unresolved_dates:
            return "unknown", "scoped_time_protection_unresolved", refs
        windows = [
            w for w in (*schedule.day_windows, *schedule.blank_windows) if w.start.date() == day
        ]
        if windows and all(
            not subtract(w.start, w.end, [(f.start, f.end) for f in schedule.fixed])
            for w in windows
        ):
            return "exempt", "fixed_commitments_cover_planning_window", refs
    return "missing", MINIMUM_MISSING, (f"generation_diagnostics:{day}",)
