"""Structured product/service migration; old prose extraction is intentionally replaced."""

import asyncio
from datetime import date
from decimal import Decimal

import pytest

from backend.app.services.planning import (
    DeveloperPlanningService,
    PlanningFailedError,
    PlanningNeedsClarificationError,
    PlanningService,
)
from backend.app.services.preference_interpretation import empty_preference_draft
from backend.tests.fakes import FixedDateProvider, V0TestRuntime
from backend.tests.request_fixtures import make_request
from backend.tests.versions.v0.fakes import (
    FakeStructuredLLMClient,
    make_itinerary,
    make_requirements,
)


def test_product_selects_v3_and_preserves_total_budget_at_shared_boundary():
    request = make_request(
        requirements=make_requirements(), budget={"amount": "1234.50", "currency": "NZD"}
    )
    client = FakeStructuredLLMClient([make_itinerary()])
    result = asyncio.run(
        PlanningService(V0TestRuntime(client, "v3"), FixedDateProvider(date(2026, 9, 11))).plan(
            request
        )
    )
    assert "system_version" not in result.model_dump()
    assert result.requirements.budget.amount == Decimal("1234.50")
    assert result.requirements.budget.currency == "NZD"
    assert len(client.calls) == 1
    assert "1234.50" in client.calls[0].user_prompt


def test_product_service_hides_provider_failure():
    client = FakeStructuredLLMClient([RuntimeError("provider secret")])
    with pytest.raises(PlanningFailedError) as exc:
        asyncio.run(
            PlanningService(V0TestRuntime(client, "v3"), FixedDateProvider(date(2026, 9, 11))).plan(
                make_request()
            )
        )
    assert "provider secret" not in str(exc.value)


def test_product_generation_and_introductions_share_one_allowance():
    from backend.app.integrations.spending import current_spending_budget

    observed = []
    base = V0TestRuntime(FakeStructuredLLMClient([make_itinerary()]), "v3")

    class Runtime:
        async def run(self, *args, **kwargs):
            budget = current_spending_budget()
            observed.append(budget)
            budget.reserve(Decimal(".02"), "fixture_planner")
            return await base.run(*args, **kwargs)

    class Introductions:
        async def generate(self, *args):
            budget = current_spending_budget()
            observed.append(budget)
            budget.reserve(Decimal(".01"), "fixture_introductions")
            return {}

    service = PlanningService(
        Runtime(), FixedDateProvider(date(2026, 9, 11)),
        introductions=Introductions(), spend_limit_usd=".04",
    )
    asyncio.run(service.plan(make_request(requirements=make_requirements())))
    assert observed[0] is observed[1]
    assert observed[0].reserved_usd == Decimal(".03")
    assert current_spending_budget() is None


def test_product_service_preserves_form_on_semantic_issue():
    request = make_request("Unclear preference")
    draft = empty_preference_draft().model_copy(update={"extraction_issues": ("ambiguous",)})
    client = FakeStructuredLLMClient([draft])
    with pytest.raises(PlanningNeedsClarificationError) as exc:
        asyncio.run(
            PlanningService(V0TestRuntime(client, "v3"), FixedDateProvider(date(2026, 9, 11))).plan(
                request
            )
        )
    assert exc.value.requirements == request.trip_requirements()
    assert exc.value.issues["code"] == "extraction_ambiguity"
    assert len(client.calls) == 1


def test_developer_service_reuses_shared_v0_contract():
    request = make_request(requirements=make_requirements())
    client = FakeStructuredLLMClient([make_itinerary()])
    result = asyncio.run(
        DeveloperPlanningService(V0TestRuntime(client)).plan(
            "v0", request, reference_date=date(2026, 9, 11)
        )
    )
    assert result.requirements == request.trip_requirements()
    assert len(client.calls) == 1


def test_product_service_rejects_future_dates_before_model():
    request = make_request(start_date="2027-01-01", end_date="2027-01-03")
    client = FakeStructuredLLMClient([])
    with pytest.raises(ValueError, match="end_date must be on or before"):
        asyncio.run(
            PlanningService(V0TestRuntime(client, "v3"), FixedDateProvider(date(2026, 9, 11))).plan(
                request
            )
        )
    assert not client.calls
