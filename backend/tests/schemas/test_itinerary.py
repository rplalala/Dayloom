"""Tests for shared itinerary and planning result schemas."""

from datetime import date, datetime

import pytest
from pydantic import ValidationError

from backend.app.schemas.itinerary import Activity, Itinerary, ItineraryDay
from backend.app.schemas.planning import PlanningResult, SystemVersion
from backend.app.schemas.request import TravelRequirements


def make_activity(activity_id: str = "activity-1") -> Activity:
    return Activity(
        activity_id=activity_id,
        title="Visit Fushimi Inari Shrine",
        place_name="Fushimi Inari Taisha",
        location="Kyoto, Japan",
        start_time=datetime.fromisoformat("2026-10-01T09:00:00+09:00"),
        end_time=datetime.fromisoformat("2026-10-01T11:00:00+09:00"),
    )


def make_itinerary() -> Itinerary:
    return Itinerary(
        destination="Kyoto",
        start_date=date(2026, 10, 1),
        end_date=date(2026, 10, 1),
        days=[ItineraryDay(date=date(2026, 10, 1), activities=[make_activity()])],
    )


def test_planning_result_has_only_shared_output_fields() -> None:
    result = PlanningResult(
        system_version=SystemVersion.V0,
        requirements=TravelRequirements(
            destination="Kyoto",
            start_date=date(2026, 10, 1),
            end_date=date(2026, 10, 1),
            traveler_count=1,
        ),
        itinerary=make_itinerary(),
    )

    assert set(result.model_dump(mode="json")) == {
        "generation_diagnostics",
        "system_version",
        "requirements",
        "itinerary",
    }


def test_planning_result_rejects_version_specific_fields() -> None:
    with pytest.raises(ValidationError):
        PlanningResult(
            system_version=SystemVersion.V1,
            requirements=TravelRequirements(destination="Kyoto"),
            itinerary=make_itinerary(),
            evidence=[],
        )


def test_activity_rejects_non_positive_duration() -> None:
    with pytest.raises(ValidationError, match="end_time must be after start_time"):
        Activity(
            activity_id="activity-1",
            title="Invalid activity",
            start_time=datetime.fromisoformat("2026-10-01T11:00:00+09:00"),
            end_time=datetime.fromisoformat("2026-10-01T11:00:00+09:00"),
        )


def test_itinerary_rejects_duplicate_activity_ids() -> None:
    with pytest.raises(ValidationError, match="activity_id values must be unique"):
        Itinerary(
            destination="Kyoto",
            start_date=date(2026, 10, 1),
            end_date=date(2026, 10, 1),
            days=[
                ItineraryDay(
                    date=date(2026, 10, 1),
                    activities=[make_activity(), make_activity()],
                )
            ],
        )


def test_transport_declaration_round_trips_in_nested_itinerary_output() -> None:
    raw = make_activity().model_dump(mode="json")
    raw.update(
        activity_kind="transport",
        place_name=None,
        transport={"mode": "TRANSIT", "from_activity_id": "a", "to_activity_id": "b"},
    )
    itinerary = make_itinerary().model_copy(
        update={
            "days": [
                ItineraryDay(date=date(2026, 10, 1), activities=[Activity.model_validate(raw)])
            ]
        }
    )
    encoded = itinerary.model_dump(mode="json")
    assert encoded["days"][0]["activities"][0]["transport"] == raw["transport"]
    assert Itinerary.model_validate(encoded).model_dump(mode="json") == encoded


@pytest.mark.parametrize("explicit_null", [False, True])
def test_absent_transport_preserves_historical_activity_wire_shape(explicit_null) -> None:
    raw = make_activity().model_dump(mode="json")
    if explicit_null:
        raw["transport"] = None
    assert "transport" not in Activity.model_validate(raw).model_dump(mode="json")


@pytest.mark.parametrize(
    "declaration",
    [
        {"mode": "WALK", "from_activity_id": "", "to_activity_id": "b"},
        {"mode": "BICYCLE", "from_activity_id": "a", "to_activity_id": "b"},
        {"mode": "WALK", "from_activity_id": "a"},
    ],
)
def test_invalid_transport_declaration_is_rejected(declaration) -> None:
    raw = make_activity().model_dump(mode="json")
    raw.update(activity_kind="transport", transport=declaration)
    with pytest.raises(ValidationError):
        Activity.model_validate(raw)


def test_transport_declaration_cannot_reclassify_a_visit() -> None:
    raw = make_activity().model_dump(mode="json")
    raw.update(
        activity_kind="main_poi",
        transport={"mode": None, "from_activity_id": "a", "to_activity_id": "b"},
    )
    with pytest.raises(ValidationError, match="transport declarations require"):
        Activity.model_validate(raw)


def test_nested_planning_serialization_schema_keeps_activity_contract() -> None:
    schema = PlanningResult.model_json_schema(mode="serialization")["$defs"]["Activity"]
    assert set(schema["properties"]) == {
        "activity_id",
        "activity_kind",
        "time_use",
        "title",
        "place_name",
        "source_place_id",
        "location",
        "start_time",
        "end_time",
        "estimated_cost",
        "notes",
        "transport",
    }
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {"activity_id", "title", "start_time", "end_time"}
