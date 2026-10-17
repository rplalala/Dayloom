"""Tools timestamps retain civil clocks and obey sourced IANA transitions."""

from datetime import datetime

import pytest

from backend.app.policies.itinerary_output import validate_output_sources
from backend.app.schemas.itinerary import Activity, Itinerary, ItineraryDay
from backend.tests.candidate_fixtures import candidate_fixture


def paris_schedule(offset="+02:00"):
    place = (
        candidate_fixture(1, 0)
        .canonical_places[0]
        .structured_evidence.model_copy(update={"timezone_id": "Europe/Paris"})
    )
    activity = Activity(
        activity_id="a",
        activity_kind="main_poi",
        time_use="scheduled",
        title="Museum visit",
        source_place_id=place.place_id,
        place_name=place.name,
        start_time=f"2026-10-25T10:00:00{offset}",
        end_time=f"2026-10-25T11:00:00{offset}",
    )
    itinerary = Itinerary(
        output_version="itinerary_3",
        destination="Paris",
        start_date="2026-10-25",
        end_date="2026-10-25",
        days=[ItineraryDay(date="2026-10-25", activities=[activity])],
    )
    return itinerary, place


def test_known_offset_conflict_is_rejected_without_mutating_original():
    itinerary, place = paris_schedule()
    before = itinerary.model_dump_json()
    with pytest.raises(ValueError, match="timezone_offset_conflict"):
        validate_output_sources(itinerary, places=[place], supplied_ids=[place.place_id])
    assert itinerary.model_dump_json() == before


def test_correct_offset_is_preserved_at_tools_acceptance():
    itinerary, place = paris_schedule("+01:00")
    accepted = validate_output_sources(itinerary, places=[place], supplied_ids=[place.place_id])
    assert accepted.days[0].activities[0].start_time.isoformat() == "2026-10-25T10:00:00+01:00"


def test_local_wire_time_derives_offset_instead_of_copying_trip_wide_offset():
    from backend.app.policies.schedule_time import local_datetime

    assert (
        local_datetime("2026-10-24", "10:00:00", "Europe/Paris").isoformat()
        == "2026-10-24T10:00:00+02:00"
    )
    assert (
        local_datetime("2026-10-25", "10:00:00", "Europe/Paris").isoformat()
        == "2026-10-25T10:00:00+01:00"
    )


@pytest.mark.parametrize(
    "day,clock,reason",
    [
        ("2026-03-29", "02:30:00", "dst_gap"),
        ("2026-10-25", "02:30:00", "dst_fold"),
    ],
)
def test_local_gap_or_unselected_fold_is_not_guessed(day, clock, reason):
    from backend.app.policies.schedule_time import local_datetime

    with pytest.raises(ValueError, match=reason):
        local_datetime(day, clock, "Europe/Paris")


@pytest.mark.parametrize("offset", ["+01:00", "+02:00"])
def test_explicit_fold_choice_is_valid_when_it_names_a_real_instant(offset):
    from backend.app.policies.schedule_time import validate_endpoint

    validate_endpoint(datetime.fromisoformat(f"2026-10-25T02:30:00{offset}"), "Europe/Paris")


def test_transfer_elapsed_time_crosses_transition_with_new_arrival_offset():
    from backend.app.policies.schedule_time import elapsed_add, elapsed_seconds

    start = datetime.fromisoformat("2026-10-25T02:55:00+02:00")
    end = elapsed_add(start, 600, "Europe/Paris")
    assert end.isoformat() == "2026-10-25T02:05:00+01:00"
    assert elapsed_seconds(start, end) == 600


def test_missing_or_conflicting_zone_evidence_does_not_supply_a_guessed_zone():
    from backend.app.policies.schedule_time import ScheduleTimeContext, local_datetime

    with pytest.raises(ValueError, match="timezone_missing"):
        local_datetime("2026-10-25", "10:00:00", None)
    context = ScheduleTimeContext(
        [
            {"place_id": "p", "timezone_id": "Europe/Paris"},
            {"place_id": "p", "timezone_id": "Europe/London"},
        ]
    )
    with pytest.raises(ValueError, match="timezone_evidence_conflict"):
        context.zone_for("p")


def test_non_dst_zone_and_transition_crossing_interval_keep_real_elapsed_time():
    from backend.app.policies.schedule_time import elapsed_seconds, local_datetime

    assert (
        local_datetime("2026-10-25", "10:00:00", "Asia/Tokyo").isoformat()
        == "2026-10-25T10:00:00+09:00"
    )
    start = local_datetime("2026-10-25", "01:30:00", "Europe/Paris")
    end = local_datetime("2026-10-25", "03:30:00", "Europe/Paris")
    assert elapsed_seconds(start, end) == 10800


def test_elapsed_helpers_do_not_interpret_naive_clocks_in_the_host_timezone():
    from backend.app.policies.schedule_time import elapsed_add, elapsed_seconds

    naive = datetime(2026, 10, 25, 10)
    with pytest.raises(ValueError, match="timezone_offset_missing"):
        elapsed_add(naive, 600)
    with pytest.raises(ValueError, match="timezone_offset_missing"):
        elapsed_seconds(naive, naive)
