"""Hard mode acceptance; no provider calls or inference from transport prose."""

from backend.app.schemas.requirement_boundary import RequirementBoundaryError


def validate_restricted_transport(itinerary, constraint, *, plain=False):
    if constraint is None:
        return

    def reject(path, code="disallowed_transport_mode"):
        raise RequirementBoundaryError(
            code, stage="output_transport", errors=({"loc": path, "type": code},)
        )

    allowed = set(constraint.allowed_modes)
    if not plain:
        for i, transfer in enumerate(itinerary.transfers):
            if transfer.mode not in allowed:
                reject(("transfers", i, "mode"))
        return
    for di, day in enumerate(itinerary.days):
        declared = set()
        for ai, activity in enumerate(day.activities):
            if activity.activity_kind != "transport":
                continue
            claim = activity.transport
            if claim is None or claim.mode is None:
                reject(("days", di, "activities", ai, "transport"), "transport_mode_unresolved")
            if claim.mode not in allowed:
                reject(("days", di, "activities", ai, "transport", "mode"))
            declared.add((claim.from_activity_id, claim.to_activity_id))
        visits = sorted(
            (
                a
                for a in day.activities
                if a.place_name and a.activity_kind not in ("transport", "free_time")
            ),
            key=lambda a: a.start_time,
        )
        for left, right in zip(visits, visits[1:], strict=False):
            if (
                left.place_name != right.place_name
                and (left.activity_id, right.activity_id) not in declared
            ):
                reject(("days", di, "activities"), "transport_mode_unresolved")
