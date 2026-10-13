"""Affected-day arrangement strategy over immutable application permissions."""

from backend.app.versions.v3.repair_schedule import ordered_activities

REPLAN_INSTRUCTION = """Replan the affected date group as one coherent visit arrangement.
Local editing did not advance these targets. Reconsider the order and placement of all
authorized visits in affected_day_replan.days together, including linked move endpoints.
Use fixed and unpermitted visits as anchors. Preserve unaffected dates exactly.
Reuse qualified candidates and applicable observations first. Never invent identities or
grant an operation merely because a visit appears in the date group. Original source_date
and move_dates remain binding after every step. Produce structured edits, never a replacement
itinerary. Joint dependent edits must leave feasible neighboring transfers, coverage and
occupancy; the application verifies these and owns all transport.\n"""


def replan_scope(itinerary, localized, original_scope):
    """Allow originally authorized retiming of peers in the causal date closure.

    Localized dates already include active finding dates, permitted move destinations
    and coverage dependencies. Peer retiming cannot grant deferred removal authority
    or extend that date closure to unrelated originally authorized work.
    """
    dates = set(localized.dates)
    current_dates = {a.activity_id: d.date for d in itinerary.days for a in d.activities}
    permissions = {p.activity_id: p for p in localized.permissions}
    for permission in original_scope.permissions:
        if (
            permission.activity_id not in permissions
            and current_dates.get(permission.activity_id) in dates
            and "retime" in permission.operations
        ):
            permissions[permission.activity_id] = permission.model_copy(
                update={"operations": frozenset({"retime"})}
            )
    return localized.model_copy(update={"permissions": tuple(permissions.values())})


def arrangement_context(itinerary, scope, context):
    """Project the authorized date group without granting new edit authority."""
    activities = {a.activity_id: d.date for d in itinerary.days for a in d.activities}
    return {
        "affected_dates": [str(d) for d in scope.dates],
        "unaffected_dates": [str(d.date) for d in itinerary.days if d.date not in scope.dates],
        "days": [
            {
                "date": str(day.date),
                "activities": [
                    a.model_dump(mode="json") for a in ordered_activities(day, context.schedule)
                ],
            }
            for day in itinerary.days
            if day.date in scope.dates
        ],
        "date_dependencies": [
            {
                "reason": "authorized_move",
                "activity_id": p.activity_id,
                "source_date": str(p.source_date or activities[p.activity_id]),
                "destination_dates": [str(d) for d in p.move_dates if d in scope.dates],
            }
            for p in scope.permissions
            if "move" in p.operations
        ]
        + [
            {
                "reason": "coverage_compensation",
                "date": str(p.date),
                "trigger_activity_ids": list(p.trigger_activity_ids),
            }
            for p in scope.coverage_permissions
        ],
    }
