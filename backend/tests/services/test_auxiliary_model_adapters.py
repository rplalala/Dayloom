"""Every auxiliary provider boundary checks input before sending paid work."""

import asyncio
import json
from types import SimpleNamespace

import httpx
import pytest
from openai import BadRequestError

from backend.app.evidence.experience_models import ExperienceProfileDraft
from backend.app.integrations.azure_foundry.evidence_reasoner import AzureFoundryEvidenceReasoner
from backend.app.integrations.azure_foundry.web_search import AzureFoundryWebEvidenceProvider
from backend.app.llm.azure_foundry.client import AzureFoundryStructuredLLMClient
from backend.app.runtime.config_loader import load_runtime_profile
from backend.app.runtime.config_models import AuxiliaryModelLimits
from backend.app.schemas.interpreted_requirements import InterpretationDraft
from backend.app.schemas.requirement_boundary import RequirementBoundaryError
from backend.app.services.generation_resources import GenerationResourceError
from backend.app.services.product_introductions import IntroductionClient
from backend.tests.integrations.azure_foundry.test_evidence_reasoner import _place, _source, _task
from backend.tests.integrations.azure_foundry.test_web_search import _request

TEXT = "Must include a botanical garden. Absolutely no stairs."


class ProviderReached(RuntimeError):
    pass


async def invoke(kind, limits, calls):
    class Responses:
        async def create(self, **kwargs):
            calls.append(kwargs)
            raise ProviderReached()

    responses = Responses()
    if kind in ("interpretation", "reviews"):
        async def send(request):
            calls.append(json.loads(request.content))
            return httpx.Response(400, json={"error": {"message": "offline rejection"}})

        http = httpx.AsyncClient(transport=httpx.MockTransport(send))
        sync = httpx.Client(transport=httpx.MockTransport(lambda _: pytest.fail("sync send")))
        client = AzureFoundryStructuredLLMClient(
            endpoint="https://example.invalid/openai/v1", deployment="fixture", api_key="fixture",
            http_async_client=http, http_client=sync, auxiliary_limits=limits,
        )
        try:
            await client.generate_structured(
                system_prompt="Preserve all supplied requirements.",
                user_prompt=TEXT if kind == "interpretation" else json.dumps({
                    "place_id": "alpha", "reviews": [{"review_id": "r1", "text": TEXT}],
                }),
                response_schema=InterpretationDraft
                if kind == "interpretation" else ExperienceProfileDraft,
            )
        finally:
            await client.aclose()
        return
    if kind == "introductions":
        client = IntroductionClient(
            SimpleNamespace(responses=responses), "fixture", auxiliary_limits=limits
        )
        await client.generate([{"activity_id": "a", "summary": TEXT}])
        return
    kwargs = {
        "endpoint": "https://example.invalid/openai/v1", "deployment": "fixture",
        "api_key": "fixture", "config": load_runtime_profile("acceptance").web_evidence,
        "responses_client": responses, "auxiliary_limits": limits,
    }
    if kind == "web":
        await AzureFoundryWebEvidenceProvider(**kwargs).search(
            _request().model_copy(update={"task_instruction": TEXT})
        )
    else:
        await AzureFoundryEvidenceReasoner(**kwargs).reason(_task(), (_source(TEXT),), _place())


@pytest.mark.parametrize("kind,output", [
    ("interpretation", 16384), ("reviews", 16384), ("web", 16384),
    ("evidence", 1200), ("introductions", 8192),
])
def test_provider_receives_output_cap_and_complete_source(kind, output):
    calls = []
    with pytest.raises((ProviderReached, BadRequestError, RequirementBoundaryError)):
        asyncio.run(invoke(kind, AuxiliaryModelLimits(), calls))
    assert len(calls) == 1
    assert calls[0]["max_output_tokens"] == output
    assert TEXT in json.dumps(calls[0])


@pytest.mark.parametrize("kind", ["interpretation", "reviews", "web", "evidence", "introductions"])
def test_oversized_input_never_reaches_provider(kind):
    calls = []
    with pytest.raises(GenerationResourceError, match="auxiliary_input_resource_overflow"):
        asyncio.run(invoke(kind, AuxiliaryModelLimits(input_tokens=1, framing_tokens=0), calls))
    assert calls == []


@pytest.mark.parametrize("profile", ["development", "acceptance"])
def test_planner_factory_applies_selected_policy_to_all_auxiliary_clients(monkeypatch, profile):
    from pydantic import SecretStr

    from backend.app.services import planner_runtime as runtime

    received = []

    class Client:
        def __init__(self, **kwargs):
            received.append(kwargs["auxiliary_limits"])

        async def aclose(self):
            pass

    monkeypatch.setattr(runtime, "V1Settings", lambda: SimpleNamespace(
        azure_openai_endpoint="https://example.invalid", azure_openai_deployment="fixture",
        azure_openai_api_key=SecretStr("fixture"), google_maps_api_key=SecretStr("fixture"),
    ))
    for name in (
        "AzureFoundryStructuredLLMClient", "AzureFoundryWebEvidenceProvider",
        "AzureFoundryEvidenceReasoner",
    ):
        monkeypatch.setattr(runtime, name, Client)

    async def run():
        async with runtime.create_planner_dependencies(
            "v3", load_runtime_profile(profile), None
        ):
            pass

    asyncio.run(run())
    expected = None if profile == "development" else AuxiliaryModelLimits()
    assert received == [expected, expected, expected]


def test_product_introduction_factory_applies_product_policy(monkeypatch):
    from pydantic import SecretStr

    from backend.app.runtime import config_loader
    from backend.app.services import product_introductions as introductions

    calls = []

    class Client:
        def __init__(self, **kwargs):
            self.responses = self

        async def create(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(output_text='{"introductions": []}')

        async def close(self):
            pass

    config = load_runtime_profile("acceptance").model_copy(update={
        "auxiliary_model_limits": AuxiliaryModelLimits(input_tokens=1, framing_tokens=0),
    })
    monkeypatch.setattr(config_loader, "load_product_runtime_config", lambda: config)
    monkeypatch.setattr(introductions, "AsyncOpenAI", Client)
    monkeypatch.setattr(introductions, "V0Settings", lambda: SimpleNamespace(
        azure_openai_endpoint="https://example.invalid", azure_openai_deployment="fixture",
        azure_openai_api_key=SecretStr("fixture"),
    ))

    async def run():
        async with introductions.create_introduction_client() as client:
            await client.generate([{"activity_id": "a", "summary": TEXT}])

    with pytest.raises(GenerationResourceError):
        asyncio.run(run())
    assert calls == []
