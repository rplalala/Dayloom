"""Shared provider applicability and adopted transfer construction; no Repair authority."""

from backend.app.policies.itinerary_schedule import available_intervals
from backend.app.policies.schedule_time import elapsed_add, elapsed_seconds
from backend.app.schemas.itinerary import Transfer


def route_rows(origin, destination, mode, routing_preference, departure, evidence):
    """One selector for provider estimates; sensitive modes retain exact-time scope."""
    rows = []
    obstacle = False
    for route in evidence:
        if route.travel_mode != mode:
            continue
        actual_preference, required_preference = route.routing_preference, routing_preference
        if mode == "DRIVE":
            actual_preference = actual_preference or "TRAFFIC_UNAWARE"
            required_preference = required_preference or "TRAFFIC_UNAWARE"
        if actual_preference != required_preference:
            continue
        for element in route.elements:
            if not (
                element.origin_place_id == origin
                and element.destination_place_id == destination
                and element.evidence_type == "provider_observed"
                and (
                    element.status_state == "success"
                    or element.status_state == "legacy"
                    and element.status in {"OK", "0"}
                )
            ):
                continue
            fallback = element.fallback_info or {}
            calculation = fallback.get("routingMode")
            basic_drive = mode == "DRIVE" and (
                calculation == "FALLBACK_TRAFFIC_UNAWARE"
                or not calculation
                and routing_preference
                in (None, "TRAFFIC_UNAWARE", "ROUTING_PREFERENCE_UNSPECIFIED")
            )
            stable = mode == "WALK" or basic_drive
            if not stable and (
                departure is None or route.representative_departure_time != departure
            ):
                continue
            if element.condition == "ROUTE_NOT_FOUND":
                obstacle = True
                continue
            if (
                route.availability == "unavailable"
                or element.availability != "available"
                or element.condition != "ROUTE_EXISTS"
                or element.duration_seconds is None
            ):
                continue
            rows.append(
                dict(
                    duration_seconds=element.duration_seconds,
                    source_ref=route.source_ref,
                    travel_mode=mode,
                    routing_preference=route.routing_preference,
                    departure_time=route.representative_departure_time.isoformat()
                    if route.representative_departure_time
                    else None,
                    requested_at=(element.requested_at or route.requested_at).isoformat()
                    if element.requested_at or route.requested_at
                    else None,
                    retrieved_at=(element.retrieved_at or route.retrieved_at).isoformat(),
                    basis="walk_provider_estimate"
                    if mode == "WALK"
                    else "basic_drive_estimate"
                    if basic_drive
                    else "time_applicable",
                    element=element.model_dump(mode="json"),
                )
            )
    return [] if obstacle else rows


def route_option(
    left,
    right,
    mode,
    evidence,
    policy,
    schedule=None,
    routing_preference=None,
    *,
    time_context=None,
):
    """An option is tied to one continuous interval, never a sum of free fragments."""
    preference = (routing_preference or "TRAFFIC_UNAWARE") if mode == "DRIVE" else None
    reserve = policy.drive_reserve_minutes * 60 if mode == "DRIVE" else 0
    for start, end in available_intervals(left, right, schedule):
        rows = route_rows(
            left.source_place_id, right.source_place_id, mode, preference, start, evidence
        )
        if not rows or len({r["duration_seconds"] for r in rows}) != 1:
            continue
        row = rows[0]
        seconds = row["duration_seconds"]
        distance = row["element"].get("distance_meters")
        limit = (
            policy.max_leg_minutes
            if mode == "WALK"
            else policy.transit_max_minutes
            if mode == "TRANSIT"
            else policy.drive_max_minutes
        )
        if seconds > limit * 60 or seconds + reserve > elapsed_seconds(start, end):
            continue
        if mode == "WALK" and (distance is None or distance > policy.walk_route_max_km * 1000):
            continue
        return Transfer(
            from_activity_id=left.activity_id,
            to_activity_id=right.activity_id,
            origin_place_id=left.source_place_id,
            destination_place_id=right.source_place_id,
            mode=mode,
            mode_source="APPLICATION_DEFAULT_WALK"
            if mode == "WALK"
            else "APPLICATION_TRANSIT_FALLBACK"
            if mode == "TRANSIT"
            else "APPLICATION_CAR_FALLBACK",
            departure_time=start,
            arrival_time=elapsed_add(
                start,
                seconds + reserve,
                time_context.zone_for(right.source_place_id) if time_context else None,
            ),
            provider_duration_seconds=seconds,
            distance_meters=distance,
            reserve_seconds=reserve,
            routing_preference=preference,
            evidence_refs=tuple(sorted({r["source_ref"] for r in rows})),
            calculation_basis=row["basis"],
            validation_state="PASS",
            unknowns=("Car transport must be arranged; cost and availability not verified.",)
            if mode == "DRIVE"
            else (),
        )
    return None


def transfer_time_check(left, right, rows, schedule, departure, reserve=0):
    """One shared continuous-window comparison for diagnostics and formal validation."""
    # Time-independent provider estimates still require a continuous itinerary slot
    # at the actual bound departure; a later free interval cannot validate this leg.
    if any(t.utcoffset() is None for t in (left.end_time, right.start_time, departure)):
        return None
    try:
        minutes = next(
            (
                elapsed_seconds(departure, end) / 60
                for start, end in available_intervals(left, right, schedule)
                if start <= departure < end
            ),
            0,
        )
    except TypeError:
        return None
    gap = minutes * 60
    return gap, max(0, rows[0]["duration_seconds"] + reserve - gap)
