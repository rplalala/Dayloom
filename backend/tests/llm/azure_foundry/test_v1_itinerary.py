"""V1-only optional-cost projection without relaxing shared itinerary validation."""

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from backend.app.llm.azure_foundry.dto import (
    FoundryDateTimeDTO,
    FoundryMoneyDTO,
    FoundryPrimaryActivityDTO,
    FoundryPrimaryItineraryDayDTO,
    FoundryPrimaryItineraryDTO,
)
from backend.app.llm.azure_foundry.itinerary_cost_projection import map_foundry_v1_itinerary
from backend.app.llm.azure_foundry.mapping import FoundryMappingError, map_foundry_itinerary


def _datetime(time: str) -> FoundryDateTimeDTO:
    return FoundryDateTimeDTO(date="2026-09-18", time=time, utc_offset="+08:00")


def _itinerary(
    *costs: FoundryMoneyDTO | None,
    end_time: str = "11:00:00",
    notes: str | None = None,
    start_date: str = "2026-09-18",
) -> FoundryPrimaryItineraryDTO:
    return FoundryPrimaryItineraryDTO(
        output_version="itinerary_3",
        destination="Singapore",
        start_date=start_date,
        end_date="2026-09-18",
        days=[
            FoundryPrimaryItineraryDayDTO(
                date="2026-09-18",
                activities=[
                    FoundryPrimaryActivityDTO(
                        activity_kind="main_poi",
                        atmosphere_theme=None,
                        time_use="scheduled",
                        source_place_id=None,
                        activity_id=f"activity-{index}",
                        title=f"Visit place {index}",
                        place_name=f"Place {index}",
                        location="Singapore",
                        start_time=_datetime("09:00:00"),
                        end_time=_datetime(end_time),
                        estimated_cost=cost,
                        notes=notes,
                    )
                    for index, cost in enumerate(costs)
                ],
            )
        ],
    )


def _project(cost: FoundryMoneyDTO | None):
    result = map_foundry_v1_itinerary(_itinerary(cost))
    return result.days[0].activities[0].estimated_cost, result.cost_projections[0]


def test_v1_point_amount_is_preserved_without_midpoint() -> None:
    source = _itinerary(FoundryMoneyDTO(amount="10.00", currency="SGD"))
    projected = map_foundry_v1_itinerary(source)
    cost = projected.days[0].activities[0].estimated_cost

    assert cost is not None
    assert cost.amount == Decimal("10.00")
    assert cost.currency == "SGD"
    assert projected.cost_projections[0].projection == "exact_point"
    assert projected.model_dump() == map_foundry_itinerary(source).model_dump()


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        ("1.00-10.00", Decimal("5.50")),
        ("10-20", Decimal("15")),
        ("0-10", Decimal("5")),
        ("1.00 - 10.00", Decimal("5.50")),
    ],
)
def test_v1_bounded_range_uses_exact_decimal_midpoint(amount: str, expected: Decimal) -> None:
    cost, diagnostic = _project(FoundryMoneyDTO(amount=amount, currency="SGD"))

    assert cost is not None
    assert cost.amount == expected
    assert cost.currency == "SGD"
    assert diagnostic.projection == "midpoint_from_range"
    assert diagnostic.lower_bound is not None
    assert diagnostic.upper_bound is not None
    assert diagnostic.midpoint == str(expected)
    assert diagnostic.field_path == "days[0].activities[0].estimated_cost"


@pytest.mark.parametrize(
    "amount",
    [
        "from 10",
        "10+",
        "up to 20",
        "under 20",
        "around 10",
        "20-10",
        "-5-10",
        "1-",
        "-10",
        "1-10-20",
        "abc",
        "NaN",
        "Infinity",
        "10 USD-20 SGD",
    ],
)
def test_v1_unsupported_optional_amount_becomes_null(amount: str) -> None:
    cost, diagnostic = _project(FoundryMoneyDTO(amount=amount, currency="SGD"))

    assert cost is None
    assert diagnostic.projection == "invalid_set_null"
    assert diagnostic.error_category == "unsupported_amount"


@pytest.mark.parametrize("currency", ["S$", "sgd", "SGD/USD", ""])
def test_v1_invalid_optional_currency_becomes_null(currency: str) -> None:
    cost, diagnostic = _project(FoundryMoneyDTO(amount="1-10", currency=currency))

    assert cost is None
    assert diagnostic.projection == "invalid_set_null"
    assert diagnostic.error_category == "invalid_currency"


def test_v1_explicit_null_is_not_invalid_cost_degradation() -> None:
    cost, diagnostic = _project(None)

    assert cost is None
    assert diagnostic.projection == "explicit_null"


def test_v1_multiple_activity_costs_are_projected_independently() -> None:
    result = map_foundry_v1_itinerary(
        _itinerary(
            FoundryMoneyDTO(amount="10", currency="SGD"),
            FoundryMoneyDTO(amount="1-10", currency="SGD"),
            FoundryMoneyDTO(amount="from 20", currency="SGD"),
            None,
            notes="Keep the existing note.",
        )
    )

    assert [
        activity.estimated_cost.amount if activity.estimated_cost else None
        for activity in result.days[0].activities
    ] == [Decimal("10"), Decimal("5.5"), None, None]
    assert [item.projection for item in result.cost_projections] == [
        "exact_point",
        "midpoint_from_range",
        "invalid_set_null",
        "explicit_null",
    ]
    assert all(
        activity.notes == "Keep the existing note." for activity in result.days[0].activities
    )


def test_v1_cost_degradation_does_not_hide_invalid_non_cost_field() -> None:
    source = _itinerary(FoundryMoneyDTO(amount="abc", currency="SGD"), end_time="11:00")

    with pytest.raises(FoundryMappingError, match="must use exactly HH:MM:SS"):
        map_foundry_v1_itinerary(source)


def test_v1_invalid_date_and_missing_structure_still_fail() -> None:
    with pytest.raises(FoundryMappingError, match="start_date must use exactly YYYY-MM-DD"):
        map_foundry_v1_itinerary(_itinerary(None, start_date="2026/09/18"))
    with pytest.raises(ValidationError, match="Field required"):
        FoundryPrimaryItineraryDTO.model_validate(
            {"destination": "Singapore", "start_date": "2026-09-18", "end_date": "2026-09-18"}
        )


def test_v1_projection_keeps_shared_itinerary_date_and_activity_contract() -> None:
    result = map_foundry_v1_itinerary(
        _itinerary(FoundryMoneyDTO(amount="1.00-10.00", currency="SGD"))
    )

    assert result.start_date == date(2026, 9, 18)
    assert result.end_date == date(2026, 9, 18)
    assert result.days[0].activities[0].activity_id == "activity-0"
    assert result.days[0].activities[0].start_time.isoformat() == ("2026-09-18T09:00:00+08:00")
    assert "_cost_projections" not in result.model_dump()


def test_v0_shared_mapping_still_rejects_range_cost() -> None:
    with pytest.raises(ValidationError):
        map_foundry_itinerary(_itinerary(FoundryMoneyDTO(amount="1.00-10.00", currency="SGD")))
