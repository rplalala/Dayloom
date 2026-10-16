"""Directed transition checks and bounded route acquisition for repair only."""

from backend.app.evidence.normalization import normalize_routes
from backend.app.integrations.google.routes import ROUTE_MATRIX_FIELD_MASK
from backend.app.integrations.models import LatLng, RouteMatrixRequest, RouteWaypoint
from backend.app.policies.itinerary_schedule import primary_journey_allowed
from backend.app.policies.route_options import route_rows, transfer_time_check
from backend.app.services.evidence_acquisition import V1EvidenceAcquisitionService
from backend.app.versions.v3.repair_models import TransitionBinding
from backend.app.versions.v3.repair_schedule import ordered_activities


def bind_transitions(itinerary, mode, routing_preference=None, schedule=None):
    if mode is None:
        return ()
    bindings = []
    saved = {(t.from_activity_id, t.to_activity_id): t for t in itinerary.transfers}
    for day in itinerary.days:
        ordered = ordered_activities(day, schedule)
        for left, right in zip(ordered, ordered[1:], strict=False):
            if not primary_journey_allowed(left, right):
                continue
            if (
                left.source_place_id
                and right.source_place_id
                and left.source_place_id != right.source_place_id
                and left.end_time.utcoffset() is not None
            ):
                transfer = saved.get((left.activity_id, right.activity_id))
                if transfer and (
                    transfer.origin_place_id != left.source_place_id
                    or transfer.destination_place_id != right.source_place_id
                    or transfer.departure_time < left.end_time
                    or transfer.departure_time > right.start_time
                ):
                    transfer = None
                bindings.append(
                    TransitionBinding(
                        from_activity_id=left.activity_id,
                        to_activity_id=right.activity_id,
                        travel_mode=transfer.mode if transfer else mode,
                        departure_time=transfer.departure_time if transfer else left.end_time,
                        routing_preference=transfer.routing_preference
                        if transfer
                        else routing_preference,
                        application_reserve_seconds=transfer.reserve_seconds if transfer else 0,
                        mode_source=transfer.mode_source if transfer else "USER_EXPLICIT",
                    )
                )
    return tuple(bindings)


def applicable_elements(left, right, binding, evidence):
    if binding.departure_time.utcoffset() is None or binding.departure_time < left.end_time:
        return []
    return [
        (r["duration_seconds"], r["source_ref"])
        for r in route_rows(
            left.source_place_id,
            right.source_place_id,
            binding.travel_mode,
            binding.routing_preference,
            binding.departure_time,
            evidence,
        )
    ]


def check_transitions(itinerary, bindings, evidence, schedule=None):
    items = {a.activity_id: a for d in itinerary.days for a in d.activities}
    adjacent = {
        (a.activity_id, b.activity_id)
        for d in itinerary.days
        for ordered in [ordered_activities(d, schedule)]
        for a, b in zip(ordered, ordered[1:], strict=False)
    }
    bound = {(b.from_activity_id, b.to_activity_id) for b in bindings}
    for pair in sorted(adjacent - bound):
        yield dict(status="UNKNOWN", reason="transition_binding_missing", activity_ids=pair)
    for binding in bindings:
        pair = (binding.from_activity_id, binding.to_activity_id)
        row = dict(
            status="UNKNOWN", reason="route_scope_or_evidence_unavailable", activity_ids=pair
        )
        if pair not in adjacent or any(i not in items for i in pair):
            yield row
            continue
        left, right = (items[i] for i in pair)
        row["adopted_evidence"] = {
            "considered_routes": [
                {
                    "source_ref": r.source_ref,
                    "travel_mode": r.travel_mode,
                    "routing_preference": r.routing_preference,
                    "departure_time": r.representative_departure_time.isoformat()
                    if r.representative_departure_time
                    else None,
                    "retrieved_at": r.retrieved_at.isoformat(),
                    "element": e.model_dump(mode="json"),
                }
                for r in evidence
                for e in r.elements
                if e.origin_place_id == left.source_place_id
                and e.destination_place_id == right.source_place_id
            ]
        }
        matches = applicable_elements(left, right, binding, evidence)
        if not matches or len({duration for duration, _ in matches}) != 1:
            yield row
            continue
        try:
            selected = route_rows(
                left.source_place_id,
                right.source_place_id,
                binding.travel_mode,
                binding.routing_preference,
                binding.departure_time,
                evidence,
            )
            comparison = transfer_time_check(
                left,
                right,
                selected,
                schedule,
                binding.departure_time,
                binding.application_reserve_seconds,
            )
            if comparison is None:
                yield row
                continue
            gap, deficit = comparison
        except TypeError:
            yield row
            continue
        row.pop("adopted_evidence", None)
        yield dict(
            **{
                **row,
                "status": "CONFIRMED" if deficit else "PASS",
                "reason": "minimum_transfer_deficit" if deficit else "minimum_transfer_only",
            },
            adopted_evidence={
                "available_seconds": gap,
                "application_reserve_seconds": binding.application_reserve_seconds,
                "selected_routes": route_rows(
                    left.source_place_id,
                    right.source_place_id,
                    binding.travel_mode,
                    binding.routing_preference,
                    binding.departure_time,
                    evidence,
                ),
            },
            magnitude=deficit,
            evidence_refs=tuple(sorted({ref for _, ref in matches})),
        )


async def acquire_transitions(
    itinerary, bindings, evidence, places, provider, budget, schedule=None
):
    """Only necessary directed one-by-one matrices; all calls share the phase ledger."""
    acquired = []
    if provider is None:
        return ()
    items = {a.activity_id: a for d in itinerary.days for a in d.activities}
    places = {p.place_id: p for p in places}
    adjacent = {
        (a.activity_id, b.activity_id)
        for d in itinerary.days
        for ordered in [ordered_activities(d, schedule)]
        for a, b in zip(ordered, ordered[1:], strict=False)
    }
    for binding in bindings:
        if (binding.from_activity_id, binding.to_activity_id) not in adjacent:
            continue
        left, right = items[binding.from_activity_id], items[binding.to_activity_id]
        if applicable_elements(left, right, binding, (*evidence, *acquired)):
            continue
        if left.source_place_id not in places or right.source_place_id not in places:
            continue

        if any(
            places[pid].latitude is None or places[pid].longitude is None
            for pid in (left.source_place_id, right.source_place_id)
        ):
            budget.stops.append("route_coordinates_unavailable")
            continue

        def waypoint(pid):
            p = places[pid]
            return RouteWaypoint(
                place_id=pid, location=LatLng(latitude=p.latitude, longitude=p.longitude)
            )

        if binding.travel_mode == "WALK":
            from backend.app.versions.v3.repair_spatial import walk_measurements

            if walk_measurements(left, right, (*evidence, *acquired)):
                continue
        request = RouteMatrixRequest(
            origins=[waypoint(left.source_place_id)],
            destinations=[waypoint(right.source_place_id)],
            travel_mode=binding.travel_mode,
            departure_time=None if binding.travel_mode == "WALK" else binding.departure_time,
            routing_preference=binding.routing_preference,
            field_mask=ROUTE_MATRIX_FIELD_MASK,
        )
        value = await budget.call(
            V1EvidenceAcquisitionService._route_cache_key(request),
            lambda request=request: provider.compute_route_matrix(request),
            charges={"routes": 1, "elements": len(request.origins) * len(request.destinations)},
            observed=getattr(provider, "observes_send_boundary", False),
            unwrap=True,
        )
        if value is not None:
            acquired.append(
                normalize_routes(value, request=request, mode_reason="repair_bound_leg")
            )
    return tuple(acquired)
