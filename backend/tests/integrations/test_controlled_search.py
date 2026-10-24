import asyncio
import json

import httpx

from backend.app.integrations.openai_search import OpenAIWebEvidenceProvider
from backend.app.integrations.spending import SpendingBudget
from backend.app.runtime.config_loader import load_runtime_profile
from backend.tests.integrations.azure_foundry.test_web_search import _request


def test_search_preserves_task_domains_and_reserves_before_real_sdk_send():
    sent = []
    budget = SpendingBudget("2")

    def respond(request):
        assert budget.reserved_usd > 0
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
        client = OpenAIWebEvidenceProvider(
            api_key="fixture",
            config=load_runtime_profile("acceptance").web_evidence,
            http_client=httpx.AsyncClient(transport=httpx.MockTransport(respond)),
        )
        try:
            with budget.activate():
                return await client.search(_request())
        finally:
            await client.aclose()

    result = asyncio.run(run())
    assert sent[0]["input"] == _request().task_instruction
    assert sent[0]["max_tool_calls"] == 2
    assert sent[0]["tools"][0]["filters"]["allowed_domains"] == ["example.org"]
    assert [hit.allowed_domain for hit in result.hits] == [True, False]
    assert budget.reserved_usd < 1
    assert len(sent) == 1
