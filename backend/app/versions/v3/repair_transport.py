"""Application-owned per-leg options; provider facts and policy reserves stay separate."""

from datetime import datetime

from backend.app.policies.itinerary_schedule import primary_journey_allowed
from backend.app.policies.route_options import route_option
from backend.app.policies.schedule_time import ScheduleTimeContext, elapsed_add, elapsed_seconds
from backend.app.schemas.itinerary import Transfer
from backend.app.versions.v3.repair_models import TransitionBinding
from backend.app.versions.v3.repair_routes import acquire_transitions, route_rows
from backend.app.versions.v3.repair_schedule import available_intervals, ordered_activities


def allowed_modes(scope):
    if scope.allowed_transport_modes is not None:
        return scope.allowed_transport_modes
    if scope.unsupported_explicit_mode:
        return ()
    explicit = scope.mode_source and (
        scope.mode_source.startswith("explicit") or scope.mode_source == "USER_EXPLICIT"
    )
    # A supplied non-WALK mode remains restrictive for historical typed contexts.
    if explicit or scope.travel_mode not in (None, "WALK"):
        return (scope.travel_mode,) if scope.travel_mode else ()
    return ("WALK", "TRANSIT", "DRIVE")


async def resolve_transfers(
    original, proposed, scope, evidence, places, provider, budget, schedule=None
):
    """Change only affected legs; reuse every allowed mode before acquiring alternatives."""
    modes = allowed_modes(scope)
    time_context = ScheduleTimeContext(places.values() if isinstance(places, dict) else places)
    old = {a.activity_id: a for d in original.days for a in d.activities}
    old_pairs = {
        (a.activity_id, b.activity_id)
        for d in original.days
        for seq in [ordered_activities(d, schedule)]
        for a, b in zip(seq, seq[1:], strict=False)
    }
    saved = {(t.from_activity_id, t.to_activity_id): t for t in original.transfers}
    selected, acquired = [], []
    for day in proposed.days:
        seq = ordered_activities(day, schedule)
        for left, right in zip(seq, seq[1:], strict=False):
            if not primary_journey_allowed(left, right):
                continue
            if not left.source_place_id or not right.source_place_id or not modes:
                continue
            pair = (left.activity_id, right.activity_id)
            changed = (
                pair not in old_pairs
                or left != old.get(left.activity_id)
                or right != old.get(right.activity_id)
                or pair in saved
                and saved[pair].mode not in modes
            )
            if not changed:
                if pair in saved:
                    selected.append(saved[pair])
                continue
            option = next(
                (
                    v
                    for mode in modes
                    if (
                        v := route_option(
                            left,
                            right,
                            mode,
                            (*evidence, *acquired),
                            budget.policy.spatial,
                            schedule,
                            scope.routing_preference if len(modes) == 1 else None,
                            time_context=time_context,
                        )
                    )
                ),
                None,
            )
            if option is None:
                for mode in modes:
                    intervals = available_intervals(left, right, schedule)
                    if not intervals:
                        break
                    departure = intervals[0][0]
                    binding = TransitionBinding(
                        from_activity_id=left.activity_id,
                        to_activity_id=right.activity_id,
                        travel_mode=mode,
                        departure_time=departure,
                        routing_preference=(scope.routing_preference or "TRAFFIC_UNAWARE")
                        if mode == "DRIVE" and len(modes) == 1
                        else "TRAFFIC_UNAWARE"
                        if mode == "DRIVE"
                        else None,
                    )
                    extra = await acquire_transitions(
                        proposed,
                        (binding,),
                        (*evidence, *acquired),
                        places,
                        provider,
                        budget,
                        schedule,
                    )
                    acquired.extend(extra)
                    option = route_option(
                        left,
                        right,
                        mode,
                        (*evidence, *acquired),
                        budget.policy.spatial,
                        schedule,
                        scope.routing_preference if len(modes) == 1 else None,
                        time_context=time_context,
                    )
                    if option:
                        break
            if option is None and modes == ("DRIVE",):
                # Retain the explicit attempted binding even when reserve makes it infeasible.
                # Formal validation must see that deficit, not silently fall back to zero reserve.
                preference = scope.routing_preference or "TRAFFIC_UNAWARE"
                rows = route_rows(
                    left.source_place_id,
                    right.source_place_id,
                    "DRIVE",
                    preference,
                    left.end_time,
                    (*evidence, *acquired),
                )
                if rows and len({r["duration_seconds"] for r in rows}) == 1:
                    row = rows[0]
                    reserve = budget.policy.spatial.drive_reserve_minutes * 60
                    arrival = elapsed_add(
                        left.end_time,
                        row["duration_seconds"] + reserve,
                        time_context.zone_for(right.source_place_id),
                    )
                    option = Transfer(
                        from_activity_id=left.activity_id,
                        to_activity_id=right.activity_id,
                        origin_place_id=left.source_place_id,
                        destination_place_id=right.source_place_id,
                        mode="DRIVE",
                        mode_source="USER_EXPLICIT",
                        departure_time=left.end_time,
                        arrival_time=arrival,
                        provider_duration_seconds=row["duration_seconds"],
                        distance_meters=row["element"].get("distance_meters"),
                        reserve_seconds=reserve,
                        routing_preference=preference,
                        evidence_refs=tuple(r["source_ref"] for r in rows),
                        calculation_basis=row["basis"],
                        validation_state="CONFIRMED" if arrival > right.start_time else "UNKNOWN",
                    )
            if option:
                if len(modes) == 1:
                    option = option.model_copy(update={"mode_source": "USER_EXPLICIT"})
                selected.append(option)
    return proposed.model_copy(update={"transfers": selected}), tuple(acquired)


def saved_transfer(itinerary, left, right):
    return next(
        (
            t
            for t in itinerary.transfers
            if t.from_activity_id == left.activity_id
            and t.to_activity_id == right.activity_id
            and t.origin_place_id == left.source_place_id
            and t.destination_place_id == right.source_place_id
            and t.departure_time >= left.end_time
            and t.departure_time <= right.start_time
        ),
        None,
    )


def present_transfers(
    itinerary,
    bindings,
    evidence,
    schedule=None,
    default_source="APPLICATION_DEFAULT_WALK",
    *,
    places=(),
):
    """Final output uses the same bindings and checks as formal route validation."""
    from backend.app.versions.v3.repair_routes import check_transitions

    time_context = ScheduleTimeContext(places)

    checks = {
        tuple(r["activity_ids"]): r
        for r in check_transitions(itinerary, bindings, evidence, schedule)
    }
    items = {a.activity_id: a for d in itinerary.days for a in d.activities}
    transfers = []
    for b in bindings:
        left, right = items[b.from_activity_id], items[b.to_activity_id]
        if not primary_journey_allowed(left, right):
            continue
        rows = route_rows(
            left.source_place_id,
            right.source_place_id,
            b.travel_mode,
            b.routing_preference,
            b.departure_time,
            evidence,
        )
        row = rows[0] if rows and len({r["duration_seconds"] for r in rows}) == 1 else None
        existing = saved_transfer(itinerary, left, right)
        source = existing.mode_source if existing else default_source
        seconds = row["duration_seconds"] if row else None
        reservation = (
            next(
                (
                    r
                    for r in schedule.occupied_transfers
                    if r["from_activity_id"] == left.activity_id
                    and r["to_activity_id"] == right.activity_id
                    and r["basis"] == "policy_reserve_route_unknown"
                ),
                None,
            )
            if schedule and row is None
            else None
        )
        reserve = b.application_reserve_seconds
        if reservation:
            reserve = elapsed_seconds(
                datetime.fromisoformat(reservation["start"]),
                datetime.fromisoformat(reservation["end"]),
            )
        transfers.append(
            Transfer(
                from_activity_id=left.activity_id,
                to_activity_id=right.activity_id,
                origin_place_id=left.source_place_id,
                destination_place_id=right.source_place_id,
                mode=b.travel_mode,
                mode_source=source,
                departure_time=b.departure_time,
                arrival_time=elapsed_add(
                    b.departure_time,
                    seconds + b.application_reserve_seconds,
                    time_context.zone_for(right.source_place_id),
                )
                if seconds is not None
                else None,
                provider_duration_seconds=seconds,
                distance_meters=row["element"].get("distance_meters") if row else None,
                reserve_seconds=reserve,
                routing_preference=b.routing_preference,
                evidence_refs=tuple(sorted({r["source_ref"] for r in rows})),
                calculation_basis=row["basis"]
                if row
                else "policy_reserve_route_unknown"
                if reservation
                else "route_unknown",
                validation_state=checks.get((left.activity_id, right.activity_id), {}).get(
                    "status", "UNKNOWN"
                ),
                unknowns=("Car transport must be arranged; cost and availability not verified.",)
                if b.travel_mode == "DRIVE"
                else ("Applicable route estimate unavailable.",)
                if row is None
                else (),
            )
        )
    return itinerary.model_copy(update={"transfers": transfers})


async def prepare_options(
    original, preparation, scope, context, evidence, provider, budget, report
):
    """Round-robin target opportunities; options inform choices, not visit feasibility."""
    from backend.app.evidence.normalization import normalize_routes
    from backend.app.integrations.google.routes import ROUTE_MATRIX_FIELD_MASK
    from backend.app.integrations.models import LatLng, RouteMatrixRequest, RouteWaypoint
    from backend.app.services.evidence_acquisition import V1EvidenceAcquisitionService

    places = {c.place.place_id: c.place for c in preparation.ledger}
    queues = {}
    active_additions = {
        f.finding_id
        for f in report.findings
        if f.finding_id in scope.target_ids and f.check == "coverage"
    }
    for auth in preparation.authorizations:
        if auth.operation != "add" or auth.target_id not in active_additions:
            continue
        queues.setdefault((auth.target_id, auth.date), []).append(auth)
    ordered = []
    while any(queues.values()):
        for key in sorted(queues):
            if queues[key]:
                ordered.append(queues[key].pop(0))
    options, acquired, seen = [], [], set()
    for auth in ordered:
        anchors = [
            a
            for d in original.days
            if d.date == auth.date
            for a in ordered_activities(d, context.schedule)
            if a.source_place_id in places
        ]
        # One nearest real anchor per opportunity, not every candidate/anchor/mode matrix.
        from backend.app.versions.v3.repair_spatial import distance_km

        anchors.sort(
            key=lambda a: (
                distance_km(places.get(auth.place_id), places.get(a.source_place_id)) or 0,
                a.activity_id,
            )
        )
        for anchor in anchors[:1]:
            for origin, destination in (
                (anchor.source_place_id, auth.place_id),
                (auth.place_id, anchor.source_place_id),
            ):
                departure = anchor.end_time
                if origin == destination or (origin, destination, departure) in seen:
                    continue
                seen.add((origin, destination, departure))
                modes = allowed_modes(scope)

                def usable(
                    mode, origin=origin, destination=destination, departure=departure, modes=modes
                ):
                    pref = (
                        (
                            (scope.routing_preference or "TRAFFIC_UNAWARE")
                            if len(modes) == 1
                            else "TRAFFIC_UNAWARE"
                        )
                        if mode == "DRIVE"
                        else None
                    )
                    rows = route_rows(
                        origin, destination, mode, pref, departure, (*evidence, *acquired)
                    )
                    limit = (
                        budget.policy.spatial.max_leg_minutes
                        if mode == "WALK"
                        else budget.policy.spatial.transit_max_minutes
                        if mode == "TRANSIT"
                        else budget.policy.spatial.drive_max_minutes
                    )
                    return [
                        r
                        for r in rows
                        if r["duration_seconds"] <= limit * 60
                        and (
                            mode != "WALK"
                            or r["element"].get("distance_meters") is not None
                            and r["element"]["distance_meters"]
                            <= budget.policy.spatial.walk_route_max_km * 1000
                        )
                    ]

                chosen = next(((m, rows) for m in modes if (rows := usable(m))), None)
                if chosen is None and provider is not None:
                    for mode in modes:
                        if (
                            budget.used["routes"] >= budget.limits["routes"]
                            or budget.used["preparation_routes"]
                            >= budget.limits["preparation_routes"]
                            or budget.used["elements"] >= budget.limits["elements"]
                            or budget.clock() >= budget.io_deadline
                        ):
                            break
                        pref = (
                            (
                                (scope.routing_preference or "TRAFFIC_UNAWARE")
                                if len(modes) == 1
                                else "TRAFFIC_UNAWARE"
                            )
                            if mode == "DRIVE"
                            else None
                        )
                        # An existing usable fact that exceeds policy is not fetched again.
                        if route_rows(
                            origin, destination, mode, pref, departure, (*evidence, *acquired)
                        ):
                            continue
                        if any(
                            pid not in places
                            or places[pid].latitude is None
                            or places[pid].longitude is None
                            for pid in (origin, destination)
                        ):
                            break

                        def waypoint(pid):
                            p = places[pid]
                            return RouteWaypoint(
                                place_id=pid,
                                location=LatLng(latitude=p.latitude, longitude=p.longitude),
                            )

                        request = RouteMatrixRequest(
                            origins=[waypoint(origin)],
                            destinations=[waypoint(destination)],
                            travel_mode=mode,
                            departure_time=departure if mode == "TRANSIT" else None,
                            routing_preference=pref,
                            field_mask=ROUTE_MATRIX_FIELD_MASK,
                        )
                        value = await budget.call(
                            V1EvidenceAcquisitionService._route_cache_key(request),
                            lambda request=request: provider.compute_route_matrix(request),
                            charges={"routes": 1, "elements": 1},
                            observed=getattr(provider, "observes_send_boundary", False),
                            unwrap=True,
                            audit={
                                "target_id": auth.target_id,
                                "date": str(auth.date),
                                "mode": mode,
                            },
                        )
                        if value is not None:
                            acquired.append(
                                normalize_routes(
                                    value, request=request, mode_reason="target_transport_option"
                                )
                            )
                        if rows := usable(mode):
                            chosen = mode, rows
                            break
                        if budget.clock() >= budget.io_deadline or budget.remaining() <= 0:
                            break
                if chosen:
                    mode, rows = chosen
                    row = rows[0]
                    options.append(
                        dict(
                            target_id=auth.target_id,
                            date=str(auth.date),
                            origin=origin,
                            destination=destination,
                            mode=mode,
                            reference_departure=departure.isoformat(),
                            duration_seconds=row["duration_seconds"],
                            distance_meters=row["element"].get("distance_meters"),
                            reserve_seconds=budget.policy.spatial.drive_reserve_minutes * 60
                            if mode == "DRIVE"
                            else 0,
                            basis=row["basis"],
                            source_ref=row["source_ref"],
                            qualification=(
                                "Provider option only; final adjacency, departure "
                                "and continuous window must be rechecked."
                            ),
                        )
                    )
    return tuple(options), tuple(acquired)
