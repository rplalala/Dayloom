"""Repair validation must consume the same explicit occupancy as generation/intake."""

import pytest

from backend.app.policies.itinerary_schedule import ScheduleState, TimeWindow
from backend.tests.versions.v3.test_validation import activity, draft, run


@pytest.mark.parametrize("time_use,occupied", [("free_window", False), ("scheduled", True)])
def test_validation_checks_scheduled_generic_activities_but_not_free_suggestions(
    time_use, occupied
):
    visit = activity(time_use="scheduled")
    suggestion = activity("suggestion", "b", activity_kind="generic_activity", time_use=time_use)
    plan = draft([visit, suggestion]).model_copy(update={"output_version": "itinerary_3"})
    type(plan).model_validate(plan.model_dump())
    schedule = ScheduleState(
        fixed=(
            TimeWindow(
                root_activity_id="user-appointment",
                start=visit.start_time,
                end=visit.end_time,
                source="original-request:fixed-time",
            ),
        )
    )
    result = run(itinerary=plan, schedule=schedule)
    overlap = [f for f in result.findings if f.check == "overlap"]
    assert bool(overlap) is occupied
    opening = [
        f for f in result.findings if f.check == "opening" and "suggestion" in f.activity_ids
    ]
    assert bool(opening) is occupied
    protection = [
        f
        for f in result.findings
        if f.check == "semantic_requirements" and "suggestion" in f.activity_ids
    ]
    assert bool(protection) is occupied
    if occupied:
        assert all(f.status == "CONFIRMED" for f in protection)


@pytest.mark.parametrize(
    "wire,kind,reserves_journey",
    [
        ("itinerary_3", "generic_activity", False),
        ("itinerary_3", "main_poi", True),
        ("itinerary_2", "generic_activity", True),
    ],
)
def test_window_consumption_reserves_only_the_adopted_journey_population(
    wire, kind, reserves_journey
):
    from backend.app.versions.v3.repair_models import RepairScope
    from backend.app.versions.v3.repair_schedule import build_schedule, consume_windows
    from backend.tests.versions.v3.test_repair import context, exploring_budget

    time_use = "scheduled" if wire == "itinerary_3" else None
    original = draft(
        [
            activity(start="09:00", end="10:00", time_use=time_use),
            activity("support", "b", "10:00", "11:00", activity_kind=kind, time_use=time_use),
            activity(
                "free",
                None,
                "11:00",
                "17:00",
                activity_kind="free_time",
                time_use="free_window" if time_use else None,
                place_name=None,
                location=None,
            ),
        ]
    )
    original.output_version = wire
    ctx = context()
    schedule = build_schedule(
        original,
        ctx.contract.model_copy(update={"time_protections": ()}),
        ctx.places,
        primary_generated=True,
    )
    scope = RepairScope(
        dates=(original.start_date,),
        permissions=(),
        target_ids=("synthetic-authorized-addition",),
        window_roots=tuple(w.root_activity_id for w in schedule.windows),
        travel_mode="WALK",
    )
    proposed = original.model_copy(deep=True)
    proposed.days[0].activities.append(activity("added", "c", "12:00", "13:00", time_use=time_use))
    type(proposed).model_validate(proposed.model_dump())
    saved = original.model_dump()
    final, schedule, _ = consume_windows(
        original,
        proposed,
        scope,
        schedule,
        ctx.places,
        ctx.route_evidence,
        exploring_budget().policy.spatial,
        prefix="contract",
    )
    assert original.model_dump() == saved
    assert bool(schedule.occupied_transfers) is reserves_journey
    if reserves_journey:
        assert {
            (row["from_activity_id"], row["to_activity_id"]) for row in schedule.occupied_transfers
        } == {("support", "added")}
    else:
        assert any(
            a.time_use == "free_window" and a.start_time.hour == 11 and a.end_time.hour == 12
            for a in final.days[0].activities
        )


@pytest.mark.parametrize(
    "wire,kind,retains_journey",
    [
        ("itinerary_3", "generic_activity", False),
        ("itinerary_3", "main_poi", True),
        ("itinerary_2", "generic_activity", True),
    ],
)
def test_retained_reservations_follow_the_same_journey_population(wire, kind, retains_journey):
    from backend.app.versions.v3.repair_schedule import retained_transfers

    time_use = "scheduled" if wire == "itinerary_3" else None
    left = activity(start="09:00", end="10:00", time_use=time_use)
    right = activity("support", "b", "11:00", "12:00", activity_kind=kind, time_use=time_use)
    plan = draft([left, right]).model_copy(update={"output_version": wire})
    type(plan).model_validate(plan.model_dump())
    schedule = ScheduleState(
        occupied_transfers=(
            {
                "from_activity_id": left.activity_id,
                "to_activity_id": right.activity_id,
                "start": left.end_time.isoformat(),
                "end": right.start_time.isoformat(),
            },
        )
    )
    assert bool(retained_transfers(plan, plan, schedule)) is retains_journey
