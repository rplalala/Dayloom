"""Application addition policy; measurements never imply future route verification."""

from math import asin, cos, radians, sin, sqrt

from backend.app.versions.v3.repair_schedule import available_intervals, ordered_activities


def distance_km(a, b):
    if (
        a is None
        or b is None
        or any(v is None for v in (a.latitude, a.longitude, b.latitude, b.longitude))
    ):
        return None
    lat1, lat2 = radians(a.latitude), radians(b.latitude)
    dlat, dlon = lat2 - lat1, radians(b.longitude - a.longitude)
    return (
        6371
        * 2
        * asin(min(1, sqrt(sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2)))
    )


def walk_measurements(left, right, evidence):
    from backend.app.versions.v3.repair_routes import route_rows

    return [
        (r["duration_seconds"], r["source_ref"])
        for r in route_rows(
            left.source_place_id, right.source_place_id, "WALK", None, None, evidence
        )
    ]


def layout_measure(left, right, mode, evidence, routing_preference=None, schedule=None):
    from backend.app.versions.v3.repair_routes import route_rows

    rows = route_rows(
        left.source_place_id,
        right.source_place_id,
        mode,
        routing_preference,
        left.end_time,
        evidence,
    )
    if rows and len({r["duration_seconds"] for r in rows}) == 1:
        return (
            rows[0]["duration_seconds"] / 60,
            rows[0]["basis"],
            tuple(r["source_ref"] for r in rows),
        )
    return None, "route_unknown", ()


def bind_transitions_for_pair(left, right, mode, routing_preference=None):
    from backend.app.versions.v3.repair_models import TransitionBinding

    if left.end_time.utcoffset() is None:
        return None
    return TransitionBinding(
        from_activity_id=left.activity_id,
        to_activity_id=right.activity_id,
        travel_mode=mode,
        departure_time=left.end_time,
        routing_preference=routing_preference,
    )


def check_addition_layout(
    stage_original,
    proposed,
    places,
    evidence,
    mode,
    policy,
    required=(),
    routing_preference=None,
    schedule=None,
    check_rearrangements=False,
):
    """Recompute stage-added burden against the immutable baseline on every proposal.

    Missing comparable baseline durations earn no credit. Conservative gross added load
    is explicitly labeled; UNKNOWN baseline travel is never reported as zero duration.
    """
    places = {p.place_id: p for p in places}
    original_days = {d.date: d for d in stage_original.days}
    old_items = {a.activity_id: a for d in stage_original.days for a in d.activities}
    effective_mode = mode or "WALK"
    radius = policy.walk_radius_km if effective_mode == "WALK" else policy.motor_radius_km
    rows, failures, totals = [], [], []
    for day in proposed.days:
        ordered = ordered_activities(day, schedule)
        added = {
            a.activity_id
            for a in ordered
            if a.activity_id not in old_items
            or a.source_place_id != old_items[a.activity_id].source_place_id
            or a.start_time.date() != old_items[a.activity_id].start_time.date()
        }
        automatic = {
            a.activity_id
            for a in ordered
            if a.activity_id in added and a.source_place_id not in required
        }
        old_order = (
            ordered_activities(original_days[day.date], schedule)
            if day.date in original_days
            else []
        )
        old_pairs = {
            (a.activity_id, b.activity_id): (a, b)
            for a, b in zip(old_order, old_order[1:], strict=False)
        }
        new_pairs = {
            (a.activity_id, b.activity_id) for a, b in zip(ordered, ordered[1:], strict=False)
        }
        removed = {a.activity_id for a in old_order} - {a.activity_id for a in ordered}
        changed_edges = {pair for pair in new_pairs - old_pairs.keys() if removed}
        if check_rearrangements:
            changed_edges.update(
                (a.activity_id, b.activity_id)
                for a, b in zip(ordered, ordered[1:], strict=False)
                if (a.activity_id, b.activity_id) not in old_pairs
                or any(
                    item.activity_id not in old_items
                    or any(
                        getattr(item, field) != getattr(old_items[item.activity_id], field)
                        for field in ("source_place_id", "start_time", "end_time")
                    )
                    for item in (a, b)
                )
            )
        if not automatic and not changed_edges:
            continue
        daily = 0.0
        bases = set()
        affected_pairs = []
        for a, b in zip(ordered, ordered[1:], strict=False):
            if (
                not ({a.activity_id, b.activity_id} & automatic)
                and (a.activity_id, b.activity_id) not in changed_edges
            ):
                continue
            affected_pairs.append((a, b))
            distance = distance_km(places.get(a.source_place_id), places.get(b.source_place_id))
            from backend.app.versions.v3.repair_transport import saved_transfer

            transfer = saved_transfer(proposed, a, b)
            leg_mode = transfer.mode if transfer else effective_mode
            leg_preference = transfer.routing_preference if transfer else routing_preference
            minutes, basis, refs = layout_measure(
                a, b, leg_mode, evidence, leg_preference, schedule
            )
            if transfer and transfer.provider_duration_seconds is not None:
                minutes = (transfer.provider_duration_seconds + transfer.reserve_seconds) / 60
                basis, refs = transfer.calculation_basis, transfer.evidence_refs
            try:
                gap = max(
                    (
                        (end - start).total_seconds() / 60
                        for start, end in available_intervals(a, b, schedule)
                    ),
                    default=0,
                )
            except TypeError:
                gap = None
            errors = []
            if distance is None and minutes is None:
                errors.append("coordinates_required_for_automatic_addition")
            elif minutes is None and distance is not None and distance > radius:
                errors.append("automatic_geographic_range")
            # Explicit no-route observations cannot be masked by conservative fallback.
            if any(
                r.travel_mode == leg_mode
                and r.routing_preference == leg_preference
                and (
                    r.representative_departure_time == a.end_time
                    or (leg_mode == "WALK" and r.representative_departure_time is None)
                )
                and any(
                    e.origin_place_id == a.source_place_id
                    and e.destination_place_id == b.source_place_id
                    and e.evidence_type == "provider_observed"
                    and e.condition == "ROUTE_NOT_FOUND"
                    and (
                        e.status_state == "success"
                        or e.status_state == "legacy"
                        and e.status in {"OK", "0"}
                    )
                    for e in r.elements
                )
                for r in evidence
            ):
                errors.append("observed_route_obstacle")
            if minutes is None:
                minutes = policy.fallback_reserve_minutes
                basis = "policy_reserve_route_unknown"
                if distance is None or distance > policy.fallback_distance_km:
                    errors.append("no_route_fallback_distance")
                if leg_mode != "WALK":
                    errors.append("explicit_motor_mode_requires_route_evidence")
            from backend.app.versions.v3.repair_routes import route_rows

            measured_rows = route_rows(
                a.source_place_id,
                b.source_place_id,
                leg_mode,
                leg_preference,
                transfer.departure_time if transfer else a.end_time,
                evidence,
            )
            provider_minutes = (
                transfer.provider_duration_seconds / 60
                if transfer and transfer.provider_duration_seconds is not None
                else minutes
            )
            limit = (
                policy.max_leg_minutes
                if leg_mode == "WALK"
                else policy.transit_max_minutes
                if leg_mode == "TRANSIT"
                else policy.drive_max_minutes
            )
            if (
                leg_mode == "WALK"
                and measured_rows
                and any(
                    r["element"].get("distance_meters") is not None
                    and r["element"]["distance_meters"] > policy.walk_route_max_km * 1000
                    for r in measured_rows
                )
            ):
                errors.append("automatic_walk_route_distance")
            if leg_mode == "DRIVE" and not transfer and basis != "policy_reserve_route_unknown":
                minutes += policy.drive_reserve_minutes
            if provider_minutes > limit:
                errors.append("automatic_leg_burden")
            if gap is None or gap < minutes:
                errors.append("insufficient_layout_transfer_window")
            daily += minutes
            bases.add(basis)
            rows.append(
                dict(
                    date=str(day.date),
                    mode=leg_mode,
                    from_activity_id=a.activity_id,
                    to_activity_id=b.activity_id,
                    distance_km=distance,
                    minutes=minutes,
                    basis=basis,
                    evidence_refs=refs,
                    gap_minutes=gap,
                    time_verified=basis == "time_applicable",
                    policy_satisfied=not errors,
                    reasons=errors,
                )
            )
            failures.extend(errors)
        # Blank-day groups must be coherent as a whole, not a long chain of short hops.
        if not any(a.source_place_id for a in old_order):
            group = [a for a in ordered if a.activity_id in automatic]
            for index, a in enumerate(group):
                for b in group[index + 1 :]:
                    distance = distance_km(
                        places.get(a.source_place_id), places.get(b.source_place_id)
                    )
                    measured, _, _ = layout_measure(
                        a, b, effective_mode, evidence, routing_preference
                    )
                    transfer = saved_transfer(proposed, a, b)
                    if transfer and transfer.validation_state == "PASS":
                        measured = transfer.provider_duration_seconds / 60
                    if measured is None and (distance is None or distance > radius):
                        failures.append("blank_day_group_range")
            if not affected_pairs and group:
                if places.get(group[0].source_place_id) is None:
                    failures.append("coordinates_required_for_automatic_addition")
        # Compare each insertion chain against its original retained adjacent anchors.
        credits = []
        for pair, (a, b) in old_pairs.items():
            if pair in new_pairs and all(
                next(x for x in ordered if x.activity_id == old.activity_id).source_place_id
                == old.source_place_id
                for old in (a, b)
            ):
                continue
            indices = {x.activity_id: i for i, x in enumerate(ordered)}
            if a.activity_id not in indices or b.activity_id not in indices:
                continue
            lo, hi = indices[a.activity_id], indices[b.activity_id]
            chain = ordered[lo : hi + 1]
            if hi <= lo or not any(x.activity_id in automatic for x in chain):
                continue
            base_distance = distance_km(
                places.get(a.source_place_id), places.get(b.source_place_id)
            )
            legs = [
                distance_km(places.get(x.source_place_id), places.get(y.source_place_id))
                for x, y in zip(chain, chain[1:], strict=False)
            ]
            if base_distance is not None and all(v is not None for v in legs):
                if sum(legs) - base_distance > max(
                    policy.detour_floor_km, policy.detour_ratio * base_distance
                ):
                    failures.append("automatic_insertion_detour")
            base_minutes, base_basis, refs = layout_measure(
                a, b, effective_mode, evidence, routing_preference, schedule
            )
            # Only uniform measured bases are comparable. Never credit an unknown baseline.
            credit = base_minutes if base_minutes is not None and bases == {base_basis} else None
            if credit is not None:
                daily -= credit
            credits.append(
                dict(
                    pair=pair,
                    minutes=credit,
                    basis=base_basis,
                    evidence_refs=refs,
                    status="comparable_credit" if credit is not None else "no_comparable_credit",
                )
            )
        daily = max(0, daily)
        if daily > policy.daily_added_minutes:
            failures.append("stage_cumulative_daily_added_burden")
        totals.append(
            dict(
                date=str(day.date),
                added_minutes=daily,
                baseline_credits=credits,
                basis="measured_increment_or_conservative_gross",
                stage_cumulative=True,
            )
        )
    return dict(
        accepted=not failures,
        reasons=list(dict.fromkeys(failures)),
        legs=rows,
        daily=totals,
        mode=effective_mode,
        mode_basis="structured" if mode else "application_nearby_default",
    )
