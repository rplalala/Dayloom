"""IANA civil boundaries survive calendar protection and derived Repair fragments."""

from datetime import date, datetime

import pytest

from backend.app.policies.itinerary_schedule import build_schedule
from backend.app.policies.schedule_time import elapsed_seconds, validate_endpoint
from backend.app.runtime.config_loader import load_runtime_config
from backend.app.schemas.interpreted_requirements import TimeProtection
from backend.app.schemas.itinerary import Activity, Itinerary, Transfer
from backend.app.versions.v3.repair_models import RepairScope
from backend.app.versions.v3.repair_schedule import consume_windows
from backend.tests.policies.test_tools_schedule_time import paris_schedule
from backend.tests.versions.v3.test_validation import contract


@pytest.mark.parametrize(
    "day,offset,seconds", [("2026-10-25", "+01:00", 90000), ("2026-03-29", "+02:00", 82800)]
)
def test_calendar_and_full_day_protection_use_two_real_midnights(day, offset, seconds):
    itinerary, place = paris_schedule("+01:00")
    itinerary = Itinerary.model_validate_json(
        itinerary.model_dump_json().replace("2026-10-25", day).replace("+01:00", offset)
    )
    protection = TimeProtection(
        dates=(date.fromisoformat(day),),
        full_day=True,
        start_time=None,
        end_time=None,
        status="fixed",
        reason=None,
        source_refs=({"quote": "rest", "start": 0, "end": 4, "occurrence": 0},),
    )
    state = build_schedule(
        itinerary, contract().model_copy(update={"time_protections": (protection,)}), (place,)
    )
    for window in (state.day_windows[0], state.fixed[0]):
        assert elapsed_seconds(window.start, window.end) == seconds
        assert (window.end - window.start).total_seconds() == seconds
        for endpoint in (window.start, window.end):
            validate_endpoint(endpoint, "Europe/Paris")


def test_transfer_reservation_and_free_fragments_change_offset_at_fall_back():
    itinerary, place = paris_schedule("+01:00")
    pid = place.place_id

    def visit(aid, start, end, *, free=False):
        return Activity(
            activity_id=aid,
            activity_kind="free_time" if free else "main_poi",
            time_use="free_window" if free else "scheduled",
            title="Synthetic window" if free else "Visit",
            source_place_id=None if free else pid,
            place_name=None if free else place.name,
            start_time=f"2026-10-25T{start}",
            end_time=f"2026-10-25T{end}",
        )

    left = visit("a", "02:00:00+02:00", "02:55:00+02:00")
    free = visit("free", "02:55:00+02:00", "03:30:00+01:00", free=True)
    right = visit("b", "03:30:00+01:00", "04:30:00+01:00")
    other = place.model_copy(update={"place_id": "other"})
    right.source_place_id = other.place_id
    original = itinerary.model_copy(
        update={"days": [itinerary.days[0].model_copy(update={"activities": [left, free, right]})]}
    )
    schedule = build_schedule(
        original,
        contract().model_copy(update={"time_protections": ()}),
        (place, other),
        primary_generated=True,
    )
    proposed = original.model_copy(deep=True)
    proposed.days[0].activities[0].start_time = datetime.fromisoformat("2026-10-25T02:05:00+02:00")
    proposed.transfers = [
        Transfer(
            from_activity_id="a",
            to_activity_id="b",
            origin_place_id=pid,
            destination_place_id=other.place_id,
            mode="WALK",
            mode_source="synthetic",
            departure_time=left.end_time,
            arrival_time="2026-10-25T02:05:00+01:00",
            provider_duration_seconds=600,
            calculation_basis="walk_provider_estimate",
            validation_state="PASS",
        )
    ]
    scope = RepairScope(
        dates=(itinerary.start_date,),
        permissions=(),
        window_roots=("free",),
        target_ids=("synthetic",),
    )
    final, state, _ = consume_windows(
        original,
        proposed,
        scope,
        schedule,
        {pid: place, other.place_id: other},
        (),
        load_runtime_config().v3_repair,
        prefix="dst",
    )
    assert state.occupied_transfers[0]["end"] == "2026-10-25T02:05:00+01:00"
    for activity in final.days[0].activities:
        for endpoint in (activity.start_time, activity.end_time):
            validate_endpoint(endpoint, "Europe/Paris")


@pytest.mark.parametrize("day", ["2026-10-25", "2026-03-29"])
def test_ambiguous_or_missing_protection_clock_stays_unresolved(day):
    itinerary, place = paris_schedule("+01:00")
    itinerary = Itinerary.model_validate_json(
        itinerary.model_dump_json().replace("2026-10-25", day)
    )
    protection = TimeProtection(
        dates=(date.fromisoformat(day),),
        full_day=False,
        start_time="02:15",
        end_time="03:30",
        status="fixed",
        reason=None,
        source_refs=({"quote": "rest", "start": 0, "end": 4, "occurrence": 0},),
    )
    state = build_schedule(
        itinerary, contract().model_copy(update={"time_protections": (protection,)}), (place,)
    )
    assert state.fixed == ()
    assert state.unresolved_dates == (day,)


def test_final_transfer_formats_arrival_in_the_adopted_destinations_zone():
    from backend.app.versions.v3.repair_routes import bind_transitions
    from backend.app.versions.v3.repair_transport import present_transfers
    from backend.tests.versions.v3.test_mixed_transport import measured

    itinerary, place = paris_schedule("+01:00")
    left = (
        itinerary.days[0]
        .activities[0]
        .model_copy(
            update={
                "source_place_id": "a",
                "start_time": datetime.fromisoformat("2026-10-25T10:00:00+11:00"),
                "end_time": datetime.fromisoformat("2026-10-25T11:00:00+11:00"),
            }
        )
    )
    right = left.model_copy(
        update={
            "activity_id": "b",
            "source_place_id": "b",
            "start_time": datetime.fromisoformat("2026-10-25T11:00:00+10:00"),
            "end_time": datetime.fromisoformat("2026-10-25T12:00:00+10:00"),
        }
    )
    itinerary.days[0].activities = [left, right]
    zones = (
        place.model_copy(update={"place_id": "a", "timezone_id": "Australia/Sydney"}),
        place.model_copy(update={"place_id": "b", "timezone_id": "Australia/Brisbane"}),
    )
    final = present_transfers(
        itinerary,
        bind_transitions(itinerary, "WALK"),
        (measured("WALK", 600, distance=500),),
        places=zones,
    )
    transfer = final.transfers[0]
    assert transfer.arrival_time.isoformat() == "2026-10-25T10:10:00+10:00"
    assert elapsed_seconds(transfer.departure_time, transfer.arrival_time) == 600
    validate_endpoint(transfer.arrival_time, "Australia/Brisbane")
