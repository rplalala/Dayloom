"""Tests for deterministic Microsoft Foundry DTO-to-domain mapping."""

import re
from datetime import date

import pytest
from pydantic import ValidationError

from backend.app.llm.azure_foundry.dto import (
    FoundryDateTimeDTO,
    FoundryItineraryDayDTO,
    FoundryItineraryDTO,
    FoundryMoneyDTO,
    FoundryV0ActivityDTO,
)
from backend.app.llm.azure_foundry.mapping import (
    FoundryMappingError,
    map_foundry_datetime,
    map_foundry_itinerary,
    map_foundry_money,
)


def make_datetime(
    *,
    date_value: str = "2026-10-01",
    time_value: str = "13:30:00",
    utc_offset: str = "+09:00",
) -> FoundryDateTimeDTO:
    return FoundryDateTimeDTO(
        date=date_value,
        time=time_value,
        utc_offset=utc_offset,
    )


def make_activity(
    *,
    start_time: FoundryDateTimeDTO | None = None,
    end_time: FoundryDateTimeDTO | None = None,
) -> FoundryV0ActivityDTO:
    return FoundryV0ActivityDTO(
        activity_kind="main_poi",
        time_use="scheduled",
        source_place_id=None,
        activity_id="activity-1",
        title="Visit Fushimi Inari Shrine",
        place_name="Fushimi Inari Taisha",
        location="Kyoto, Japan",
        start_time=start_time or make_datetime(time_value="09:00:00"),
        end_time=end_time or make_datetime(time_value="11:00:00"),
        estimated_cost=FoundryMoneyDTO(amount="0", currency="JPY"),
        notes=None,
        transport=None,
    )


def make_itinerary(*, activity: FoundryV0ActivityDTO | None = None) -> FoundryItineraryDTO:
    activities = [activity or make_activity()]
    if activity and activity.activity_kind == "transport":
        for aid, start, end in (
            ("origin", "07:00:00", "08:00:00"),
            ("destination", "12:00:00", "13:00:00"),
        ):
            activities.append(
                make_activity().model_copy(
                    update={
                        "activity_id": aid,
                        "start_time": make_datetime(time_value=start),
                        "end_time": make_datetime(time_value=end),
                    }
                )
            )
    return FoundryItineraryDTO(
        output_version="itinerary_3",
        reference_recommendations=[],
        destination="Kyoto",
        start_date="2026-10-01",
        end_date="2026-10-01",
        days=[
            FoundryItineraryDayDTO(
                date="2026-10-01",
                activities=activities,
            )
        ],
    )


def test_datetime_mapping_constructs_exact_aware_datetime() -> None:
    mapped = map_foundry_datetime(make_datetime(), field_path="activity.start_time")

    assert mapped.isoformat() == "2026-10-01T13:30:00+09:00"


@pytest.mark.parametrize(
    ("component", "value", "message"),
    [
        ("date", "2026/10/01", "must use exactly YYYY-MM-DD"),
        ("date", "2026-02-30", "is not a valid calendar date"),
        ("time", "13:30", "must use exactly HH:MM:SS"),
        ("time", "24:00:00", "must use exactly HH:MM:SS"),
        ("utc_offset", "JST", "must use exactly +HH:MM or -HH:MM"),
        ("utc_offset", "+9:00", "must use exactly +HH:MM or -HH:MM"),
    ],
)
def test_datetime_mapping_rejects_non_exact_components(
    component: str,
    value: str,
    message: str,
) -> None:
    values = {
        "date_value": "2026-10-01",
        "time_value": "13:30:00",
        "utc_offset": "+09:00",
    }
    argument_name = {
        "date": "date_value",
        "time": "time_value",
        "utc_offset": "utc_offset",
    }[component]
    values[argument_name] = value

    with pytest.raises(FoundryMappingError, match=re.escape(message)):
        map_foundry_datetime(
            make_datetime(**values),
            field_path="activity.start_time",
        )


def test_money_mapping_preserves_domain_validation() -> None:
    with pytest.raises(ValidationError):
        map_foundry_money(FoundryMoneyDTO(amount="-1", currency="jpy"))


def test_itinerary_mapping_returns_existing_domain_model() -> None:
    mapped = map_foundry_itinerary(make_itinerary())

    assert mapped.destination == "Kyoto"
    assert mapped.start_date == date(2026, 10, 1)
    assert mapped.days[0].activities[0].start_time.isoformat() == ("2026-10-01T09:00:00+09:00")


def test_itinerary_mapping_does_not_infer_missing_activity_date() -> None:
    payload = make_activity().model_dump()
    del payload["end_time"]["date"]

    with pytest.raises(ValidationError, match="Field required"):
        FoundryV0ActivityDTO.model_validate(payload)


@pytest.mark.parametrize("mode", ["WALK", "TRANSIT", "DRIVE", None])
def test_v0_mapping_preserves_transport_declaration_without_inventing_route_facts(mode):
    raw = make_activity().model_dump()
    raw.update(
        activity_kind="transport",
        place_name=None,
        transport={"mode": mode, "from_activity_id": "origin", "to_activity_id": "destination"},
    )
    mapped = map_foundry_itinerary(
        make_itinerary(activity=FoundryV0ActivityDTO.model_validate(raw))
    )
    assert (
        mapped.model_dump(mode="json")["days"][0]["activities"][0]["transport"] == raw["transport"]
    )
    assert mapped.transfers == []
    assert mapped.route_diagnostics == []


def test_itinerary_mapping_preserves_domain_time_range_validation() -> None:
    activity = make_activity(
        start_time=make_datetime(time_value="12:00:00"),
        end_time=make_datetime(time_value="11:00:00"),
    )

    with pytest.raises(ValidationError, match="end_time must be after start_time"):
        map_foundry_itinerary(make_itinerary(activity=activity))
