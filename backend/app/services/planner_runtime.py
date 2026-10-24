"""Request-owned programmatic research execution for application/API callers."""

import asyncio
import logging
from collections.abc import AsyncIterator, Callable
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from time import monotonic
from typing import Protocol
from uuid import uuid4

import anyio
from openai import DefaultAsyncHttpxClient, DefaultHttpxClient

from backend.app.integrations.azure_foundry.evidence_reasoner import AzureFoundryEvidenceReasoner
from backend.app.integrations.azure_foundry.web_search import AzureFoundryWebEvidenceProvider
from backend.app.integrations.google import GooglePlacesProvider, GoogleRoutesProvider
from backend.app.integrations.http import HttpxJSONTransport
from backend.app.integrations.open_meteo import OpenMeteoWeatherProvider
from backend.app.integrations.openai_search import OpenAIWebEvidenceProvider, SearchSettings
from backend.app.integrations.spending import (
    SpendingBudget,
    SpendingLimitError,
    current_spending_budget,
)
from backend.app.integrations.web.http_page_retriever import SafeHTMLPageRetriever
from backend.app.llm.azure_foundry.client import AzureFoundryStructuredLLMClient
from backend.app.llm.client import StructuredLLMClient
from backend.app.observability.progress import ObservedV0Client, ProgressTracer, current_progress
from backend.app.observability.run_trace import NullRunTracer, RunTracer
from backend.app.runtime.config_loader import load_runtime_config
from backend.app.runtime.config_models import RuntimeConfig
from backend.app.schemas.planning import PlanningResult, SystemVersion
from backend.app.schemas.request import PlanningRequest
from backend.app.services.preference_interpretation import validate_planning_request
from backend.app.versions.v0.config import V0Settings
from backend.app.versions.v0.runner import run_v0
from backend.app.versions.v1.config import V1Settings
from backend.app.versions.v1.runner import run_v1
from backend.app.versions.v2.runner import run_v2
from backend.app.versions.v3.runner import run_v3

LOGGER = logging.getLogger(__name__)


class PlannerRuntime(Protocol):
    async def run(
        self,
        version: SystemVersion,
        request: PlanningRequest,
        *,
        reference_date: date,
        tracer: RunTracer | None = None,
        opportunity_capture_path: Path | None = None,
        opportunity_capture_run_id: str | None = None,
    ) -> PlanningResult:
        """Run one version; callers never invoke a CLI or parse its output."""
        ...


@dataclass(frozen=True)
class PlannerDependencies:
    llm: StructuredLLMClient
    places: object = None
    weather: object = None
    routes: object = None
    web: object = None
    pages: object = None
    reasoner: object = None
    llm_identity: str | None = None


async def _await_cleanup(operation) -> None:
    """Finish same-loop cleanup even if the caller is cancelled again while waiting."""
    task = asyncio.create_task(operation)
    interrupted = False
    with anyio.CancelScope(shield=True):
        while not task.done():
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError:
                if task.done() and task.cancelled():
                    raise
                interrupted = True
        task.result()
    if interrupted:
        raise asyncio.CancelledError()


async def _close_client(client) -> None:
    """Attempt every owned close without replacing the execution exception."""
    try:
        await _await_cleanup(client.aclose())
    except Exception:
        # Do not log provider exception messages, which may contain credentials/payloads.
        LOGGER.warning("An application-owned planning client could not be closed")


@asynccontextmanager
async def create_planner_dependencies(
    version: SystemVersion, config: RuntimeConfig, tracer: RunTracer
) -> AsyncIterator[PlannerDependencies]:
    """Construct separate mutable clients for every run, including partial setup cleanup."""
    async with AsyncExitStack() as stack:

        def own(client):
            if hasattr(client, "aclose"):
                stack.push_async_callback(_close_client, client)
            return client

        settings = V0Settings() if version == SystemVersion.V0 else V1Settings()
        # LangChain's default transports are cached across adapters. Explicit clients
        # prevent one request's cleanup from closing another request's connections.
        http_client = DefaultHttpxClient()
        stack.callback(http_client.close)
        http_async_client = own(DefaultAsyncHttpxClient())
        llm = own(AzureFoundryStructuredLLMClient(
            endpoint=str(settings.azure_openai_endpoint),
            deployment=settings.azure_openai_deployment,
            api_key=settings.azure_openai_api_key.get_secret_value(),
            http_client=http_client,
            http_async_client=http_async_client,
            auxiliary_limits=config.auxiliary_model_limits,
        ))
        if version == SystemVersion.V0:
            yield PlannerDependencies(llm=llm)
            return

        transport = HttpxJSONTransport()
        # The transport/page retriever own HTTP clients inside each operation.
        google_key = settings.google_maps_api_key.get_secret_value()
        foundry = {
            "endpoint": str(settings.azure_openai_endpoint),
            "deployment": settings.azure_openai_deployment,
            "api_key": settings.azure_openai_api_key.get_secret_value(),
            "config": config.web_evidence,
            "auxiliary_limits": config.auxiliary_model_limits,
        }
        yield PlannerDependencies(
            llm=llm,
            places=GooglePlacesProvider(api_key=google_key, transport=transport, tracer=tracer),
            weather=OpenMeteoWeatherProvider(transport=transport, tracer=tracer),
            routes=GoogleRoutesProvider(api_key=google_key, transport=transport, tracer=tracer),
            web=own(
                OpenAIWebEvidenceProvider(
                    api_key=SearchSettings().openai_api_key.get_secret_value(),
                    config=config.web_evidence, auxiliary_limits=config.auxiliary_model_limits,
                ) if config.web_evidence.provider == "openai"
                else AzureFoundryWebEvidenceProvider(**foundry)
            ),
            pages=own(SafeHTMLPageRetriever(config.web_evidence.page_retrieval)),
            reasoner=own(AzureFoundryEvidenceReasoner(**foundry)),
            llm_identity=settings.azure_openai_deployment,
        )


class RequestPlannerRuntime:
    """Stateless dispatcher: no shared clients, budgets, cache or current-run metadata."""

    def __init__(
        self,
        *,
        config: RuntimeConfig | None = None,
        dependency_factory: Callable = create_planner_dependencies,
    ) -> None:
        self._config = config
        self._dependency_factory = dependency_factory

    async def run(
        self, version, request, **kwargs,
    ):
        config = self._config or load_runtime_config()
        existing = current_spending_budget()
        if existing is not None or config.generation_spend_usd is None:
            result = await self._run(version, request, **kwargs)
            if existing is not None and existing.blocked:
                raise SpendingLimitError("generation_spending_limit: incomplete generation")
            return result
        budget = SpendingBudget(config.generation_spend_usd)
        with budget.activate():
            result = await self._run(version, request, **kwargs)
            if budget.blocked:
                raise SpendingLimitError("generation_spending_limit: incomplete generation")
            return result

    async def _run(
        self,
        version: SystemVersion,
        request: PlanningRequest,
        *,
        reference_date: date,
        tracer: RunTracer | None = None,
        opportunity_capture_path: Path | None = None,
        opportunity_capture_run_id: str | None = None,
    ) -> PlanningResult:
        started = monotonic()
        version = SystemVersion(version)
        if opportunity_capture_path is not None and version not in (
            SystemVersion.V1,
            SystemVersion.V2,
        ):
            raise ValueError("Opportunity capture only supports V1/V2")
        request = validate_planning_request(request, reference_date)
        config = self._config or load_runtime_config()
        observer = current_progress()
        effective_tracer = tracer or (
            ProgressTracer(observer) if observer else NullRunTracer(uuid4())
        )
        allowance = config.development_timeout_seconds
        effective_tracer.event("application_request_deadline", {"deadline": started + allowance})
        # Explicit API policy; no change to independent CLI timeout activation.
        stack = AsyncExitStack()
        try:
            async with asyncio.timeout_at(started + allowance):
                deps = await stack.enter_async_context(
                    self._dependency_factory(version, config, effective_tracer)
                )
                if version == SystemVersion.V0:
                    client = ObservedV0Client(deps.llm) if observer else deps.llm
                    return await run_v0(request, client, reference_date=reference_date)
                runner = {
                    SystemVersion.V1: run_v1,
                    SystemVersion.V2: run_v2,
                    SystemVersion.V3: run_v3,
                }[version]
                options = {}
                if opportunity_capture_path is not None:
                    options.update(
                        opportunity_capture_path=opportunity_capture_path,
                        opportunity_capture_run_id=opportunity_capture_run_id,
                    )
                if version == SystemVersion.V3:
                    options["request_started_at"] = started
                return await runner(
                    request,
                    deps.llm,
                    deps.places,
                    deps.weather,
                    deps.routes,
                    reference_date=reference_date,
                    runtime_config=config,
                    development_timeout_seconds=allowance,
                    tracer=effective_tracer,
                    llm_config_identity=deps.llm_identity,
                    web_provider=deps.web,
                    page_retriever=deps.pages,
                    official_reasoner=deps.reasoner,
                    **options,
                )
        finally:
            # Provider release is not planning work and must outlive its execution deadline.
            await _await_cleanup(stack.aclose())
