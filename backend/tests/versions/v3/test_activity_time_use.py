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
