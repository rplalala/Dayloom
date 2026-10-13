"""Read-only pace measurements and source-linked V3 Repair objectives."""

from backend.app.policies.visit_multiplicity import is_primary_visit
from backend.pace_policy import daily_penalty, zero_penalty_counts


def pace_coverage_floor(minimum, current_count, zero_counts=()):
    """Allow an assessed pace target to lower coverage without permitting an empty day."""
    return min(minimum, current_count, min((n for n in zero_counts if n >= 1), default=minimum))


def measure_pace(itinerary, contract, diagnostics, assessments=()):
    policies = {p.date: p for p in contract.daily_pace or ()}
    days = {d.date: d for d in itinerary.days}
    result = []
    for row in diagnostics.days:
        policy = policies.get(row.date, policies.get(None))
        activities = days[row.date].activities if row.date in days else ()
        primary = [a for a in activities if is_primary_visit(a, assessments)]
        # An ambiguous activity/role must never be counted as zero to improve pace.
        unknown = any(a.activity_kind == "unknown" for a in activities) or any(
            a.source_place_id == s.place_id and s.role == "unresolved"
            for a in activities
            for s in assessments
        )
        penalty = (
            None
            if policy is None or unknown
            else daily_penalty(len(primary), policy.profile, policy.exact_count)
        )
        result.append(
            {
                "date": row.date,
                "count": len(primary),
                "penalty": penalty,
                "zero_counts": zero_penalty_counts(policy.profile, policy.exact_count)
                if policy
                else (),
                "policy": policy.model_dump(mode="json") if policy else None,
                "activity_ids": tuple(a.activity_id for a in primary),
            }
        )
    return result


def pace_summary(before, after):
    def projection(report):
        rows = [f for f in report.findings if f.check == "soft_pace"]
        known = bool(rows) and all(f.magnitude is not None for f in rows)
        return {
            "mean_penalty": sum(f.magnitude for f in rows) / len(rows) if known else None,
            "days": [
                {"date": f.dates[0].isoformat(), "penalty": f.magnitude, "reason": f.reason}
                for f in rows
            ],
        }

    first, last = projection(before), projection(after)
    dates = [
        f.dates[0] for f in before.findings if f.check == "soft_pace" and f.magnitude is not None
    ]
    initial = {f.dates[0]: f.magnitude for f in before.findings if f.check == "soft_pace"}
    final = {f.dates[0]: f.magnitude for f in after.findings if f.check == "soft_pace"}
    comparable = {
        "dates": [str(d) for d in dates],
        "before_total": sum(initial[d] for d in dates) if dates else None,
        "after_total": sum(final[d] for d in dates)
        if dates and all(final.get(d) is not None for d in dates)
        else None,
    }
    return {
        "objective": "zero_soft_pace_deductions",
        "is_failure_constraint": False,
        "comparable": comparable,
        "before": first,
        "after": last,
        "target_state": "reached"
        if last["mean_penalty"] == 0
        else "unavailable"
        if last["mean_penalty"] is None
        else "residual",
    }
