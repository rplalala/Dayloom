"""Deterministic conversion from Microsoft Foundry DTOs to domain models."""

import re
from datetime import date, datetime, time, timedelta, timezone

from backend.app.llm.azure_foundry.dto import (
    FoundryActivityDTO,
    FoundryDateTimeDTO,
    FoundryItineraryDayDTO,
    FoundryItineraryDTO,
    FoundryMoneyDTO,
    FoundryPrimaryItineraryDTO,
    FoundryV0ActivityDTO,
)
from backend.app.schemas.itinerary import Activity, Itinerary, ItineraryDay, TransportDeclaration
from backend.app.schemas.request import Money

_DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
_TIME_PATTERN = re.compile(r"(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d\Z")
_UTC_OFFSET_PATTERN = re.compile(r"([+-])([01]\d|2[0-3]):([0-5]\d)\Z")


class FoundryMappingError(ValueError):
    """Raised when a transport value cannot be mapped without guessing."""


def _map_iso_date(value: str, *, field_path: str) -> date:
    if _DATE_PATTERN.fullmatch(value) is None:
        raise FoundryMappingError(f"{field_path} must use exactly YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise FoundryMappingError(f"{field_path} is not a valid calendar date") from exc


def _map_optional_iso_date(value: str | None, *, field_path: str) -> date | None:
    if value is None:
        return None
    return _map_iso_date(value, field_path=field_path)


def map_foundry_datetime(value: FoundryDateTimeDTO, *, field_path: str) -> datetime:
    """Construct one aware datetime only from three complete, exact components."""

    mapped_date = _map_iso_date(value.date, field_path=f"{field_path}.date")
    if _TIME_PATTERN.fullmatch(value.time) is None:
        raise FoundryMappingError(f"{field_path}.time must use exactly HH:MM:SS")

    offset_match = _UTC_OFFSET_PATTERN.fullmatch(value.utc_offset)
    if offset_match is None:
        raise FoundryMappingError(f"{field_path}.utc_offset must use exactly +HH:MM or -HH:MM")

    hour, minute, second = (int(component) for component in value.time.split(":"))
    sign, offset_hour, offset_minute = offset_match.groups()
    offset_delta = timedelta(hours=int(offset_hour), minutes=int(offset_minute))
    if sign == "-":
        offset_delta = -offset_delta

    mapped_time = time(
        hour=hour,
        minute=minute,
        second=second,
        tzinfo=timezone(offset_delta),
    )
    return datetime.combine(mapped_date, mapped_time)


def map_foundry_money(value: FoundryMoneyDTO) -> Money:
    """Map money without altering its amount or currency text."""

    return Money(amount=value.amount, currency=value.currency)


def map_foundry_activity(value: FoundryActivityDTO, *, field_path: str) -> Activity:
    """Map one activity while preserving every provided value."""

    return Activity(
        activity_id=value.activity_id,
        activity_kind=value.activity_kind,
        atmosphere_theme=value.atmosphere_theme,
        time_use=value.time_use,
        source_place_id=value.source_place_id,
        title=value.title,
        place_name=value.place_name,
        location=value.location,
        start_time=map_foundry_datetime(
            value.start_time,
            field_path=f"{field_path}.start_time",
        ),
        end_time=map_foundry_datetime(
            value.end_time,
            field_path=f"{field_path}.end_time",
        ),
        estimated_cost=(
            map_foundry_money(value.estimated_cost) if value.estimated_cost is not None else None
        ),
        notes=value.notes,
        transport=(
            TransportDeclaration.model_validate(value.transport.model_dump())
            if isinstance(value, FoundryV0ActivityDTO) and value.transport is not None
            else None
        ),
    )


def map_foundry_itinerary_day(
    value: FoundryItineraryDayDTO,
    *,
    day_index: int,
) -> ItineraryDay:
    """Map one day without supplying activity datetime components from its date."""

    return ItineraryDay(
        date=_map_iso_date(value.date, field_path=f"days[{day_index}].date"),
        activities=[
            map_foundry_activity(
                activity,
                field_path=f"days[{day_index}].activities[{activity_index}]",
            )
            for activity_index, activity in enumerate(value.activities)
        ],
    )


def map_foundry_itinerary(value: FoundryPrimaryItineraryDTO) -> Itinerary:
    """Map a complete transport itinerary into the existing domain contract."""

    return Itinerary(
        output_version=value.output_version,
        reference_recommendations=[
            {
                **r.model_dump(exclude={"associated_day"}),
                "associated_day": _map_iso_date(
                    r.associated_day, field_path=f"reference_recommendations[{i}].associated_day"
                )
                if r.associated_day is not None
                else None,
            }
            for i, r in enumerate(
                value.reference_recommendations if isinstance(value, FoundryItineraryDTO) else []
            )
        ],
        destination=value.destination,
        start_date=_map_iso_date(value.start_date, field_path="start_date"),
        end_date=_map_iso_date(value.end_date, field_path="end_date"),
        days=[
            map_foundry_itinerary_day(day, day_index=day_index)
            for day_index, day in enumerate(value.days)
        ],
    )
