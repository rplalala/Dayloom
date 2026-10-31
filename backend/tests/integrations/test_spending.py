"""Dollar admission is enforced before the HTTP transport, including failures."""

import asyncio
from decimal import Decimal

import httpx
import pytest

from backend.app.integrations.spending import (
    SpendingBudget,
    SpendingLimitError,
    install_spend_hooks,
)


def test_concurrent_requests_cannot_spend_the_same_remaining_allowance():
    sent = []

    async def run():
        budget = SpendingBudget("0.04")
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: sent.append(request) or httpx.Response(500)
            )
        ) as client:
            install_spend_hooks(client)
            with budget.activate():
                results = await asyncio.gather(
                    *[
                        client.post("https://places.googleapis.com/v1/places:searchText", json={})
                        for _ in range(2)
                    ],
                    return_exceptions=True,
                )
        assert sum(isinstance(r, SpendingLimitError) for r in results) == 1
        assert budget.reserved_usd == Decimal("0.04")
        assert budget.blocked

    asyncio.run(run())
    assert len(sent) == 1


@pytest.mark.parametrize("usage", [None, {"input_tokens": 100, "output_tokens": 20}])
def test_model_reservation_uses_full_context_and_only_refunds_reported_usage(usage):
    async def run():
        budget = SpendingBudget("2")
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(200, json={"status": "completed", "usage": usage})
            )
        ) as client:
            install_spend_hooks(client)
            with budget.activate():
                await client.post(
                    "https://fixture.openai.azure.com/openai/v1/responses",
                    json={
                        "model": "gpt-6-luna",
                        "max_output_tokens": 16384,
                        "input": "Keep every hard requirement.",
                    },
                )
        assert budget.events[0]["reserved_usd"] == "1.082768"
        assert budget.reserved_usd == Decimal("0.00014" if usage else "1.082768")

    asyncio.run(run())


def test_larger_foundry_output_is_admitted_without_bypassing_shared_spending():
    sent = []

    async def run():
        budget = SpendingBudget("1.5")
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: sent.append(request) or httpx.Response(500)
            )
        ) as client:
            install_spend_hooks(client)
            with budget.activate():
                results = await asyncio.gather(
                    *[
                        client.post(
                            "https://fixture.openai.azure.com/openai/v1/responses",
                            json={
                                "model": "gpt-6-luna",
                                "max_output_tokens": 32768,
                                "input": "Keep every requirement and a finite charge ceiling.",
                            },
                        )
                        for _ in range(2)
                    ],
                    return_exceptions=True,
                )
        assert len(sent) == 1
        assert sum(isinstance(result, SpendingLimitError) for result in results) == 1
        assert budget.blocked
        assert budget.reserved_usd == Decimal("1.115536")

    asyncio.run(run())


@pytest.mark.parametrize(
    "body",
    [
        {"model": "unpriced", "max_output_tokens": 100},
        {"model": "gpt-6-luna", "max_output_tokens": 100, "tools": [{"type": "function"}]},
        {
            "model": "gpt-6-luna",
            "max_output_tokens": 100,
            "tools": [{"type": "web_search"}, {"type": "function"}],
        },
        {"model": "gpt-6-luna", "max_output_tokens": 100, "stream": True},
        {"model": "gpt-6-luna", "max_output_tokens": 128001},
    ],
)
def test_unknown_charges_never_reach_transport(body):
    async def run():
        budget = SpendingBudget("25")
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda _: pytest.fail("Unpriced request was sent"))
        ) as client:
            install_spend_hooks(client)
            with budget.activate(), pytest.raises(SpendingLimitError):
                await client.post("https://fixture.openai.azure.com/openai/v1/responses", json=body)
        assert budget.reserved_usd == 0
        assert budget.blocked

    asyncio.run(run())


@pytest.mark.parametrize(
    "endpoint,model",
    [
        ("https://fixture.services.ai.azure.com/openai/v1/responses", "gpt-6-luna"),
        ("https://api.openai.com/v1/responses", "gpt-4.1-mini-2025-04-14"),
    ],
)
def test_search_is_excluded_from_dollar_admission_without_disabling_other_limits(endpoint, model):
    sent = []

    async def run():
        budget = SpendingBudget("0.04")
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: sent.append(request) or httpx.Response(500)
            )
        ) as client:
            install_spend_hooks(client)
            with budget.activate():
                await client.post("https://places.googleapis.com/v1/places:searchText", json={})
                await client.post(
                    endpoint,
                    json={
                        "model": model,
                        "max_output_tokens": 512,
                        "tools": [{"type": "web_search"}],
                        "max_tool_calls": 1,
                    },
                )
                assert budget.blocked is False
                assert budget.snapshot()["excluded_operations"] == ["web_search"]
                assert budget.reserved_usd == Decimal("0.04")
                assert [event["operation"] for event in budget.events] == ["places"]
                with pytest.raises(SpendingLimitError):
                    await client.post("https://places.googleapis.com/v1/places:searchText", json={})
        assert budget.blocked

    asyncio.run(run())
    assert len(sent) == 2
