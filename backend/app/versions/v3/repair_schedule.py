"""Repair-only time authorization over the shared occupancy view."""

from datetime import datetime

from backend.app.policies.itinerary_schedule import (
    ScheduleState as ScheduleState,
)
from backend.app.policies.itinerary_schedule import (
    TimeWindow as TimeWindow,
)
from backend.app.policies.itinerary_schedule import (
    available_intervals,
    ordered_activities,
    primary_journey_allowed,
    subtract,
)
from backend.app.policies.itinerary_schedule import (
    available_minutes as available_minutes,
)
from backend.app.policies.itinerary_schedule import (
    build_schedule as build_schedule,
)
from backend.app.policies.schedule_time import ScheduleTimeContext, elapsed_add, elapsed_seconds


def window_projection(itinerary, schedule, roots):
    if schedule is None:
        return []
    windows = {w.root_activity_id: w for w in schedule.windows}
    rows = []
    for day in itinerary.days:
        occupied = [
            (a.start_time, a.end_time)
            for a in day.activities
            if a.activity_id not in schedule.lineage
        ]
        occupied += [(w.start, w.end) for w in schedule.fixed]
        for a in day.activities:
            root = schedule.lineage.get(a.activity_id)
            if root not in roots:
                continue
            w = windows[root]
            for start, end in subtract(
                max(a.start_time, w.start), min(a.end_time, w.end), occupied
            ):
                rows.append(
                    dict(
                        root_activity_id=root,
                        fragment_id=a.activity_id,
                        start=start.isoformat(),
                        end=end.isoformat(),
                        source=w.source,
                    )
                )
    for w in schedule.blank_windows:
        occupied = [(a.start_time, a.end_time) for d in itinerary.days for a in d.activities]
        occupied.extend((f.start, f.end) for f in schedule.fixed)
        occupied.extend(
            (datetime.fromisoformat(t["start"]), datetime.fromisoformat(t["end"]))
            for t in schedule.occupied_transfers
        )
        for start, end in subtract(w.start, w.end, occupied):
            rows.append(
                dict(
                    root_activity_id=w.root_activity_id,
                    fragment_id=None,
                    start=start.isoformat(),
                    end=end.isoformat(),
                    source=w.source,
                )
            )
    return rows


def retained_transfers(original, proposed, schedule):
    """Keep only reservations whose endpoints and adjacency are unchanged.

    Superseded reservations remain in prior round audit, not as simultaneous travel.
    Removing a reservation does not recreate or enlarge a free-time fragment.
    """
    if schedule is None:
        return ()
    old = {a.activity_id: a for d in original.days for a in d.activities}
    new = {a.activity_id: a for d in proposed.days for a in d.activities}
    pairs = {
        (a.activity_id, b.activity_id)
        for d in proposed.days
        for ordered in [ordered_activities(d, schedule)]
        for a, b in zip(ordered, ordered[1:], strict=False)
        if primary_journey_allowed(a, b)
    }
    return tuple(
        t
        for t in schedule.occupied_transfers
        if (t["from_activity_id"], t["to_activity_id"]) in pairs
        and all(new.get(t[k]) == old.get(t[k]) for k in ("from_activity_id", "to_activity_id"))
    )


def check_time_permissions(original, proposed, schedule):
    if schedule is None:
        return
    old = {a.activity_id: a for d in original.days for a in d.activities}
    new = {a.activity_id: a for d in proposed.days for a in d.activities}
    for a in old.values():
        if (
            a.activity_kind not in {"generic_activity", "unknown", "transport"}
            or new.get(a.activity_id) == a
        ):
            continue
        if str(a.start_time.date()) in schedule.unresolved_dates or any(
            a.start_time.utcoffset() is not None
            and max(a.start_time, w.start) < min(a.end_time, w.end)
            for w in schedule.fixed
        ):
            raise ValueError("Existing activity in protected user time has no safe change binding")
    for day in proposed.days:
        for a in day.activities:
            if a.activity_id in schedule.lineage or a == old.get(a.activity_id):
                continue
            if str(day.date) in schedule.unresolved_dates:
                raise ValueError("Changed arrangement intersects unresolved time requirement scope")
            for transfer in retained_transfers(original, proposed, schedule):
                start, end = (
                    datetime.fromisoformat(transfer["start"]),
                    datetime.fromisoformat(transfer["end"]),
                )
                if max(a.start_time, start) < min(a.end_time, end):
                    raise ValueError("Changed arrangement overlaps adopted transfer reservation")
            for w in schedule.fixed:
                if a.start_time.utcoffset() is None:
                    raise ValueError("Cannot compare fixed time with unknown activity timezone")
                if max(a.start_time, w.start) < min(a.end_time, w.end):
                    raise ValueError("Changed arrangement overlaps fixed user time")


def consume_windows(original, proposed, scope, schedule, places, evidence, policy, *, prefix):
    """Atomic derived edits after patch authorization; reserve only actual affected transfers."""
    if schedule is None or not scope.window_roots:
        return proposed, schedule, ()
    windows = {w.root_activity_id: w for w in schedule.windows}
    if len(set(scope.window_roots)) != len(scope.window_roots) or any(
        root not in windows or windows[root].start.date() not in scope.dates
        for root in scope.window_roots
    ):
        raise ValueError("Invalid elastic window scope")
    from backend.app.schemas.itinerary import Activity
    from backend.app.versions.v3.repair_spatial import layout_measure

    check_time_permissions(original, proposed, schedule)
    old = {a.activity_id: a for d in original.days for a in d.activities}
    result = proposed.model_copy(deep=True)
    lineage = dict(schedule.lineage)
    transfers, audit = [], []
    time_context = ScheduleTimeContext(places.values() if isinstance(places, dict) else places)
    occupied = [
        (a.start_time, a.end_time)
        for d in proposed.days
        for a in d.activities
        if a.activity_id not in schedule.lineage and a != old.get(a.activity_id)
    ]
    for day in proposed.days:
        ordered = ordered_activities(day, schedule)
        for left, right in zip(ordered, ordered[1:], strict=False):
            if not primary_journey_allowed(left, right):
                continue
            if left == old.get(left.activity_id) and right == old.get(right.activity_id):
                continue
            if not left.source_place_id or not right.source_place_id:
                continue  # Unknown real activities remain barriers in route/spatial checks.
            minutes, basis, refs = layout_measure(
                left,
                right,
                scope.travel_mode or "WALK",
                evidence,
                scope.routing_preference,
                schedule,
            )
            from backend.app.versions.v3.repair_transport import saved_transfer

            transfer = saved_transfer(proposed, left, right)
            if transfer and transfer.provider_duration_seconds is not None:
                minutes = (transfer.provider_duration_seconds + transfer.reserve_seconds) / 60
                basis, refs = transfer.calculation_basis, transfer.evidence_refs
            if minutes is None:
                minutes, basis = policy.fallback_reserve_minutes, "policy_reserve_route_unknown"
            seconds = minutes * 60
            interval = next(
                (
                    (a, elapsed_add(a, seconds, time_context.zone_for(right.source_place_id)))
                    for a, b in available_intervals(left, right, schedule)
                    if elapsed_seconds(a, b) >= seconds
                    and (
                        basis != "time_applicable"
                        or a == (transfer.departure_time if transfer else left.end_time)
                    )
                ),
                None,
            )
            if interval is None:
                raise ValueError("Insufficient unoccupied transfer window")
            occupied.append(interval)
            transfers.append(
                dict(
                    from_activity_id=left.activity_id,
                    to_activity_id=right.activity_id,
                    start=interval[0].isoformat(),
                    end=interval[1].isoformat(),
                    basis=basis,
                    evidence_refs=list(refs),
                )
            )
    windows = {w.root_activity_id: w for w in schedule.windows}
    for day in result.days:
        updated = []
        for a in day.activities:
            root = lineage.get(a.activity_id)
            if root not in scope.window_roots:
                updated.append(a)
                continue
            w = windows[root]
            if not w.start <= a.start_time < a.end_time <= w.end or (
                a.activity_kind != "free_time" and a.time_use != "free_window"
            ):
                raise ValueError("Placeholder exceeds original authorization")
            cuts = [
                (max(left, a.start_time), min(right, a.end_time))
                for left, right in occupied
                if max(left, a.start_time) < min(right, a.end_time)
            ]
            # Fixed user time is never consumed, including by transfer reservations.
            for left, right in cuts:
                if any(
                    max(left, f.start, a.start_time) < min(right, f.end, a.end_time)
                    for f in schedule.fixed
                ):
                    raise ValueError("Placeholder consumption overlaps fixed user time")
            if not cuts:
                updated.append(a)
                continue
            pieces = subtract(a.start_time, a.end_time, cuts)
            ids = []
            for index, (start, end) in enumerate(pieces):
                aid = f"{prefix}_window_{len(audit)}_{index}"
                if (
                    aid in old
                    or aid in lineage
                    or any(aid == x.activity_id for d in proposed.days for x in d.activities)
                ):
                    raise ValueError("Window fragment ID collision")
                fragment = Activity.model_validate(
                    {
                        **a.model_dump(),
                        "activity_id": aid,
                        "start_time": start,
                        "end_time": end,
                    }
                )
                updated.append(fragment)
                lineage[aid] = root
                ids.append(aid)
            audit.append(
                dict(
                    root_activity_id=root,
                    previous_fragment_id=a.activity_id,
                    fragment_ids=ids,
                    authorized_start=w.start.isoformat(),
                    authorized_end=w.end.isoformat(),
                    source=w.source,
                    consumed=[(left.isoformat(), right.isoformat()) for left, right in cuts],
                )
            )
        day.activities = updated
    # Null/unknown cost projections are not financial obligations. Remove stale paths for
    # consumed placeholders; immutable originals retain their observations.
    if hasattr(result, "set_cost_projections"):
        paths = {
            f"days[{di}].activities[{ai}].estimated_cost": a.activity_id
            for di, d in enumerate(proposed.days)
            for ai, a in enumerate(d.activities)
        }
        new = {
            a.activity_id: f"days[{di}].activities[{ai}].estimated_cost"
            for di, d in enumerate(result.days)
            for ai, a in enumerate(d.activities)
        }
        from dataclasses import replace

        result.set_cost_projections(
            tuple(
                replace(p, field_path=new[paths[p.field_path]])
                for p in proposed.cost_projections
                if paths.get(p.field_path) in new
            )
        )
    type(result).model_validate(result.model_dump())
    return (
        result,
        schedule.model_copy(
            update={
                "lineage": lineage,
                "occupied_transfers": (
                    *retained_transfers(original, proposed, schedule),
                    *transfers,
                ),
            }
        ),
        tuple(audit),
    )
