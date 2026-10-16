"""New wire declarations and immutable legacy serialization at the schema seam."""

import pytest
from pydantic import ValidationError

from backend.app.schemas.itinerary import Itinerary


def itinerary(kind="generic_activity", time_use="scheduled", **activity):
    return {
        "output_version": "itinerary_3",
        "destination": "Paris",
        "start_date": "2026-10-15",
        "end_date": "2026-10-15",
        "days": [
            {
                "date": "2026-10-15",
                "activities": [
                    {
                        "activity_id": "walk",
                        "activity_kind": kind,
                        "time_use": time_use,
                        "title": "Movable architecture walk",
                        "place_name": None,
                        "start_time": "2026-10-15T11:00:00+02:00",
                        "end_time": "2026-10-15T12:00:00+02:00",
                        **activity,
                    }
                ],
            }
        ],
    }


def test_new_wire_preserves_scheduled_movable_walk_without_booking():
    result = Itinerary.model_validate(itinerary()).model_dump(mode="json")
    assert result["days"][0]["activities"][0]["time_use"] == "scheduled"


@pytest.mark.parametrize(
    "kind,time_use",
    [
        ("main_poi", "free_window"),
        ("free_time", "scheduled"),
        ("unknown", "scheduled"),
        ("generic_activity", None),
    ],
)
def test_new_wire_rejects_missing_or_contradictory_meaning(kind, time_use):
    with pytest.raises(ValidationError):
        Itinerary.model_validate(itinerary(kind, time_use))


def test_legacy_reader_does_not_add_a_time_use_declaration():
    raw = itinerary()
    raw["output_version"] = "itinerary_2"
    del raw["days"][0]["activities"][0]["time_use"]
    result = Itinerary.model_validate(raw).model_dump(mode="json")
    assert "time_use" not in result["days"][0]["activities"][0]


def test_provider_contract_requires_time_use_and_mapping_preserves_it():
    from backend.app.llm.azure_foundry.dto import FoundryPrimaryItineraryDTO
    from backend.app.llm.azure_foundry.mapping import map_foundry_itinerary

    raw = itinerary()
    activity = raw["days"][0]["activities"][0]
    activity.update(source_place_id=None, location=None, notes=None, estimated_cost=None)
    for key, clock in (("start_time", "11:00:00"), ("end_time", "12:00:00")):
        activity[key] = {"date": "2026-10-15", "time": clock, "utc_offset": "+02:00"}
    result = map_foundry_itinerary(FoundryPrimaryItineraryDTO.model_validate(raw))
    assert result.days[0].activities[0].time_use == "scheduled"
    del activity["time_use"]
    with pytest.raises(ValidationError):
        FoundryPrimaryItineraryDTO.model_validate(raw)


@pytest.mark.parametrize("time_use,available", [("scheduled", False), ("free_window", True)])
def test_schedule_uses_declared_availability_even_for_named_suggestions(time_use, available):
    from backend.app.policies.itinerary_schedule import build_schedule, ordered_activities
    from backend.tests.versions.v3.test_repair import context

    plan = Itinerary.model_validate(itinerary(time_use=time_use, place_name="Left Bank"))
    contract = context().contract.model_copy(update={"time_protections": ()})
    state = build_schedule(plan, contract, primary_generated=True)
    assert bool(state.windows) is available
    assert bool(ordered_activities(plan.days[0], state)) is not available


def test_explicit_nonprimary_claim_is_not_promoted_by_a_place_assessment():
    from types import SimpleNamespace

    from backend.app.policies.visit_multiplicity import is_primary_visit

    plan = Itinerary.model_validate(itinerary(source_place_id="park", place_name="Park"))
    assessment = SimpleNamespace(place_id="park", main_eligible=True)
    assert not is_primary_visit(plan.days[0].activities[0], [assessment])


@pytest.mark.parametrize(
    "bad",
    [
        {"start_time": "2026-10-16T11:00:00+02:00", "end_time": "2026-10-16T12:00:00+02:00"},
        {"start_time": "2026-10-15T11:00:00", "end_time": "2026-10-15T12:00:00"},
    ],
)
def test_new_wire_rejects_unattributable_activity_dates(bad):
    with pytest.raises(ValidationError):
        Itinerary.model_validate(itinerary(**bad))


def test_transport_requires_consecutive_occurrences_without_chronology_repair():
    raw = itinerary("main_poi", place_name="Park")
    first = raw["days"][0]["activities"][0]
    second = {
        **first,
        "activity_id": "other",
        "start_time": "2026-10-15T11:30:00+02:00",
        "end_time": "2026-10-15T12:30:00+02:00",
    }
    # Overlap is a quality failure; it must not erase the declared directed pair.
    transport = {
        **first,
        "activity_id": "journey",
        "activity_kind": "transport",
        "place_name": None,
        "transport": {"mode": None, "from_activity_id": "walk", "to_activity_id": "other"},
    }
    raw["days"][0]["activities"] = [first, transport, second]
    assert Itinerary.model_validate(raw).days[0].activities[1].transport.mode is None
    raw["days"][0]["activities"].append({**transport, "activity_id": "duplicate"})
    with pytest.raises(ValidationError, match="consecutive pair"):
        Itinerary.model_validate(raw)


def test_new_nonprimary_locations_are_not_selected_as_primary_journey_endpoints():
    from backend.app.versions.v3.repair_routes import bind_transitions

    raw = itinerary("main_poi", place_name="Museum A", source_place_id="a")
    first = raw["days"][0]["activities"][0]
    middle = {
        **first,
        "activity_id": "rest",
        "activity_kind": "generic_activity",
        "place_name": "Cafe",
        "source_place_id": "cafe",
    }
    last = {**first, "activity_id": "museum-b", "source_place_id": "b", "place_name": "Museum B"}
    raw["days"][0]["activities"] = [first, middle, last]
    assert bind_transitions(Itinerary.model_validate(raw), "WALK") == ()
