"""Initial Product supply budgets follow sourced demand without rewriting requirements."""

import asyncio
from datetime import date, timedelta

import pytest

from backend.app.policies.trip_dates import create_trip_date_window
from backend.app.runtime.config_loader import load_runtime_profile, tool_limits
from backend.app.services.preference_interpretation import (
    empty_preference_draft,
    interpret_preferences,
)
from backend.tests.request_fixtures import make_request
from backend.tests.versions.v0.fakes import FakeStructuredLLMClient


def contract(days, profile="rich"):
    text = f"Travel pace: {profile}."
    request = make_request(text).model_copy(
        update={"end_date": date(2026, 9, 12) + timedelta(days=days - 1)}
    )
    data = empty_preference_draft().model_dump()
    data["daily_pace"] = [
        {
            "date": None,
            "profile": profile,
            "exact_count": None,
            "source_refs": [{"quote": text, "occurrence": 0}],
        }
    ]
    draft = type(empty_preference_draft()).model_validate(data)
    return asyncio.run(
        interpret_preferences(
            request,
            date(2026, 9, 11),
            FakeStructuredLLMClient([draft]),
            category_visits=True,
        )
    )


@pytest.mark.parametrize("days,expected", [(1, 9), (9, 36), (10, 40)])
def test_rich_initial_supply_includes_the_pace_target_and_alternatives(days, expected):
    from backend.app.policies.poi_capacity import acceptance_capacities

    original = contract(days)
    before = original.model_dump()
    capacities = acceptance_capacities(
        original,
        create_trip_date_window(date(2026, 9, 11)),
        tool_limits(load_runtime_profile("acceptance")),
    )
    assert capacities.k_final == expected
    assert capacities.r_pool >= expected
    assert capacities.c_raw <= 256
    assert original.model_dump() == before


def test_seventeen_required_identities_do_not_hit_the_development_gate():
    from backend.app.policies.poi_capacity import acceptance_capacities

    capacities = acceptance_capacities(
        contract(2),
        create_trip_date_window(date(2026, 9, 11)),
        tool_limits(load_runtime_profile("acceptance")),
        required=17,
    )
    assert capacities.k_final >= 17


def test_long_acceptance_trip_uses_the_larger_review_allowance():
    from backend.app.policies.poi_capacity import acceptance_capacities

    original = contract(9)
    before = original.model_dump()
    capacities = acceptance_capacities(
        original, create_trip_date_window(date(2026, 9, 11)),
        tool_limits(load_runtime_profile("acceptance")),
    )
    assert capacities.review_pool_cap == 18
    assert capacities.k_final == 36
    assert original.model_dump() == before


def test_named_required_places_and_category_obligations_reserve_independent_capacity():
    from backend.app.policies.poi_capacity import acceptance_capacities
    from backend.tests.services.test_required_categories import category_draft

    text = "Visit at least 10 gardens."
    original = asyncio.run(
        interpret_preferences(
            make_request(text, end_date="2026-09-16"),
            date(2026, 9, 11),
            FakeStructuredLLMClient([category_draft(text, frequency="minimum", count=10)]),
            category_visits=True,
        )
    )
    before = original.model_dump()
    result = acceptance_capacities(
        original,
        create_trip_date_window(date(2026, 9, 11)),
        tool_limits(load_runtime_profile("acceptance")),
        required=10,
    )
    # Ten resolved named places may all be outside the ten required category visits.
    assert result.k_final == 27
    assert original.model_dump() == before


def test_explicit_daily_count_and_protected_day_override_soft_pace_demand():
    from backend.app.policies.poi_capacity import acceptance_capacities
    from backend.app.schemas.interpreted_requirements import InterpretationDraft
    from backend.tests.services.test_daily_visit_constraints import TEXT, counted_draft
    from backend.tests.services.test_time_protection import protected_draft

    text = TEXT + " Private time Travel pace: rich."
    data = counted_draft().model_dump()
    data["daily_pace"] = [
        {
            "date": None,
            "profile": "rich",
            "exact_count": None,
            "source_refs": [{"quote": "Travel pace: rich.", "occurrence": 0}],
        }
    ]
    data["time_protections"] = protected_draft(
        dates=["2026-09-13"],
        full_day=True,
        start_time=None,
        end_time=None,
    ).model_dump()["time_protections"]
    request = make_request(text, end_date="2026-09-20")
    original = asyncio.run(
        interpret_preferences(
            request,
            date(2026, 9, 11),
            FakeStructuredLLMClient([InterpretationDraft.model_validate(data)]),
            category_visits=True,
        )
    )
    before = original.model_dump()
    result = acceptance_capacities(
        original,
        create_trip_date_window(date(2026, 9, 11)),
        tool_limits(load_runtime_profile("acceptance")),
    )
    assert result.k_final == 30  # 1 exact + 0 protected + 7*3 Rich visits, plus 8 alternatives.
    assert original.model_dump() == before


def test_independent_hard_category_obligations_raise_supply_without_weakening_them():
    from backend.app.policies.poi_capacity import acceptance_capacities
    from backend.app.schemas.interpreted_requirements import InterpretationDraft
    from backend.tests.services.test_required_categories import category_draft

    first, second = "Visit at least 10 gardens.", "Visit at least 10 science centres."
    data = category_draft(first, frequency="minimum", count=10).model_dump()
    other = category_draft(second, frequency="minimum", count=10).model_dump()
    other["semantic_requirements"][0]["local_key"] = "second"
    other["discovery_intents"][0]["requirement_refs"] = ["second"]
    data["semantic_requirements"] += other["semantic_requirements"]
    data["discovery_intents"] += other["discovery_intents"]
    original = asyncio.run(
        interpret_preferences(
            make_request(first + " " + second, end_date="2026-09-20"),
            date(2026, 9, 11),
            FakeStructuredLLMClient([InterpretationDraft.model_validate(data)]),
            category_visits=True,
        )
    )
    before = original.model_dump()
    result = acceptance_capacities(
        original,
        create_trip_date_window(date(2026, 9, 11)),
        tool_limits(load_runtime_profile("acceptance")),
    )
    assert result.k_final == 27  # 20 category obligations and 7 alternatives.
    assert original.model_dump() == before
