import asyncio
import json

import httpx
import pytest

from backend.app.integrations.azure_foundry import web_search as azure_search
from backend.app.integrations.openai_search import OpenAIWebEvidenceProvider
from backend.app.integrations.spending import SpendingBudget
from backend.app.runtime.config_loader import load_runtime_profile
from backend.tests.integrations.azure_foundry.test_web_search import _request


@pytest.mark.parametrize("large_auxiliary", [False, True])
@pytest.mark.parametrize("provider", ["azure_foundry", "openai"])
def test_search_preserves_task_bounds_without_dollar_admission(
    large_auxiliary, provider, monkeypatch
):
    sent = []
    budget = SpendingBudget("0.000001")

    def respond(request):
        assert budget.reserved_usd == 0
        sent.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "id": "resp-offline",
                "status": "completed",
                "object": "response",
                "output": [
                    {
                        "type": "web_search_call",
                        "id": "search-1",
                        "status": "completed",
                        "action": {
                            "type": "search",
                            "sources": [
                                {"url": "https://example.org/notice"},
                                {"url": "https://untrusted.test/notice"},
                            ],
                        },
                    }
                ],
                "usage": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
            },
        )

    async def run():
        config = load_runtime_profile("acceptance")
        limits = (
            config.auxiliary_model_limits.model_copy(update={"output_tokens": 128000})
            if large_auxiliary
            else None
        )
        transport = httpx.AsyncClient(transport=httpx.MockTransport(respond))
        if provider == "azure_foundry":
            from openai import AsyncOpenAI

            monkeypatch.setattr(
                azure_search,
                "AsyncOpenAI",
                lambda **kwargs: AsyncOpenAI(
                    **kwargs,
                    http_client=transport,
                ),
            )
            client = azure_search.AzureFoundryWebEvidenceProvider(
                endpoint="https://fixture.services.ai.azure.com/openai/v1",
                deployment="gpt-6-luna",
                api_key="fixture",
                config=config.web_evidence,
                auxiliary_limits=limits,
            )
        else:
            client = OpenAIWebEvidenceProvider(
                api_key="fixture",
                config=config.web_evidence,
                auxiliary_limits=limits,
                http_client=transport,
            )
        try:
            with budget.activate():
                return await client.search(_request())
        finally:
            await client.aclose()

    result = asyncio.run(run())
    assert sent[0]["input"] == _request().task_instruction
    assert sent[0]["max_tool_calls"] == 2
    if provider == "openai":
        assert sent[0]["max_output_tokens"] == (32768 if large_auxiliary else 16384)
    elif large_auxiliary:
        assert sent[0]["max_output_tokens"] == 128000
    assert sent[0]["tools"][0]["filters"]["allowed_domains"] == ["example.org"]
    assert [hit.allowed_domain for hit in result.hits] == [True, False]
    assert budget.reserved_usd == 0
    assert budget.blocked is False
    assert budget.snapshot()["excluded_operations"] == ["web_search"]
    assert len(sent) == 1
