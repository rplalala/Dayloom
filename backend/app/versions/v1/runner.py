"""Public runner and command-line behavior for V1."""

import argparse
import asyncio
import json
import sys
from collections.abc import Sequence
from datetime import UTC, date, datetime
from pathlib import Path
from time import monotonic
from uuid import uuid4

from pydantic import ValidationError

from backend.app.integrations.azure_foundry.evidence_reasoner import AzureFoundryEvidenceReasoner
from backend.app.integrations.azure_foundry.web_search import AzureFoundryWebEvidenceProvider
from backend.app.integrations.google import (
    GooglePlacesProvider,
    GoogleRoutesProvider,
)
from backend.app.integrations.http import HttpxJSONTransport
from backend.app.integrations.open_meteo import OpenMeteoWeatherProvider
from backend.app.integrations.protocols import (
    NearbyPlacesProvider,
    PlacesProvider,
    RoutesProvider,
    WeatherProvider,
)
from backend.app.integrations.web.extraction_protocols import OfficialEvidenceReasoner
from backend.app.integrations.web.http_page_retriever import SafeHTMLPageRetriever
from backend.app.integrations.web.protocols import PageRetriever, WebEvidenceProvider
from backend.app.llm.client import StructuredLLMClient
from backend.app.observability.run_trace import (
    NullRunTracer,
    RunTraceContext,
    RunTracer,
    create_run_tracer,
)
from backend.app.policies.itinerary_output import output_role_summary
from backend.app.policies.trip_dates import (
    DateProvider,
    SystemDateProvider,
    TripDatePolicyError,
    create_trip_date_window,
)
from backend.app.runtime.budget import ToolBudget, ToolBudgetLimits
from backend.app.runtime.cache import RequestCache
from backend.app.runtime.config_loader import (
    load_runtime_config,
    load_runtime_config_file,
    resolve_trace_directory,
    runtime_config_snapshot,
    tool_limits,
)
from backend.app.runtime.config_models import ReferenceDiscoveryConfig, WebEvidenceConfig
from backend.app.runtime.logging_config import configure_logging
from backend.app.schemas.interpreted_requirements import ClarificationRequired
from backend.app.schemas.planning import PlanningResult, SystemVersion
from backend.app.schemas.planning_supply_result import PlanningSupplyPlanningResult
from backend.app.schemas.request import PlanningRequest
from backend.app.schemas.requirement_boundary import RequirementBoundaryError
from backend.app.services.evidence_acquisition import (
    NoViableCandidatesError,
    V1EvidenceAcquisitionService,
)
from backend.app.services.official_web_grounding import OfficialWebGroundingService
from backend.app.services.official_web_integration import OfficialWebIntegrationService
from backend.app.services.preference_interpretation import (
    read_planning_request,
    validate_planning_request,
)
from backend.app.services.reference_discovery import ReferenceDiscoveryService
from backend.app.services.web_evidence_acquisition import WebEvidenceAcquisitionService
from backend.app.versions.v0.runner import create_foundry_client, parse_reference_date
from backend.app.versions.v1.config import V1Settings
from backend.app.versions.v1.graph import V1StageError, build_v1_graph


async def run_tools_planner(
    request: PlanningRequest,
    llm_client: StructuredLLMClient,
    places_provider: PlacesProvider,
    weather_provider: WeatherProvider,
    routes_provider: RoutesProvider,
    *,
    reference_date: date | None = None,
    date_provider: DateProvider | None = None,
    budget_limits: ToolBudgetLimits | None = None,
    tracer: RunTracer | None = None,
    llm_config_identity: str | None = None,
    web_provider: WebEvidenceProvider | None = None,
    page_retriever: PageRetriever | None = None,
    official_reasoner: OfficialEvidenceReasoner | None = None,
    web_evidence_config: WebEvidenceConfig | None = None,
    reference_discovery_config: ReferenceDiscoveryConfig | None = None,
    runtime_config=None,
    runtime_config_path=None,
    development_timeout_seconds=None,
    system_version=SystemVersion.V1,
    graph_factory=None,
    discovery_factory=None,
    result_factory=PlanningSupplyPlanningResult,
    result_projector=None,
    opportunity_capture_path=None,
) -> PlanningResult:
    """Run V1 with one fixed date, shared budget, cache, tracer, and explicit graph."""

    request_started = monotonic()
    if reference_date is not None and date_provider is not None:
        raise ValueError("reference_date and date_provider cannot both be supplied")

    runtime_config = runtime_config or load_runtime_config()
    if runtime_config.acquisition.policy_id == "quality_first_1":
        if (
            web_evidence_config is not None and web_evidence_config != runtime_config.web_evidence
        ) or (
            reference_discovery_config is not None
            and reference_discovery_config != runtime_config.reference_discovery
        ):
            raise ValueError("Conflicting quality-first component configuration")
    effective_reference_date = (
        reference_date
        or (date_provider or SystemDateProvider(runtime_config.app.time_zone)).today()
    )
    request = validate_planning_request(request, effective_reference_date)
    date_window = create_trip_date_window(effective_reference_date)
    effective_tracer = tracer or NullRunTracer(uuid4())
    if (
        runtime_config.acquisition.policy_id == "quality_first_1"
        and budget_limits is not None
        and budget_limits != tool_limits(runtime_config)
    ):
        raise ValueError("Conflicting explicit quality-first budget override")
    budget = ToolBudget(budget_limits or tool_limits(runtime_config))
    cache = RequestCache()
    evidence_service = V1EvidenceAcquisitionService(
        places_provider=places_provider,
        weather_provider=weather_provider,
        routes_provider=routes_provider,
        budget=budget,
        cache=cache,
        tracer=effective_tracer,
        runtime_config=runtime_config,
    )
    evidence_service.request_deadline = (
        request_started + development_timeout_seconds
        if development_timeout_seconds is not None
        else getattr(routes_provider, "deadline", None)
    )
    web_dependencies = (web_provider, page_retriever, official_reasoner)
    if any(item is not None for item in web_dependencies) and not all(
        item is not None for item in web_dependencies
    ):
        raise ValueError(
            "Official-Web provider, page retriever, and reasoner must be supplied together"
        )
    official_web_service = None
    if web_provider is not None and page_retriever is not None and official_reasoner is not None:
        web_config = web_evidence_config or runtime_config.web_evidence
        official_web_service = OfficialWebIntegrationService(
            acquisition=WebEvidenceAcquisitionService(
                provider=web_provider,
                budget=budget,
                cache=cache,
                tracer=effective_tracer,
                config=web_config,
            ),
            grounding=OfficialWebGroundingService(
                page_retriever=page_retriever,
                reasoner=official_reasoner,
                budget=budget,
                tracer=effective_tracer,
                config=web_config,
            ),
            budget=budget,
            tracer=effective_tracer,
        )
    capture = None
    if opportunity_capture_path is not None and system_version in (
        SystemVersion.V1,
        SystemVersion.V2,
    ):
        from backend.app.services.candidate_capture import CandidateCapture

        capture = CandidateCapture(
            opportunity_capture_path, system_version.value, effective_tracer.run_id
        )
        evidence_service.candidate_capture = capture
    extension = discovery_factory(evidence_service) if discovery_factory else None
    graph_kwargs = {"discovery_extension": extension} if extension is not None else {}
    graph = (graph_factory or build_v1_graph)(
        llm_client,
        evidence_service,
        effective_tracer,
        llm_config_identity=(
            llm_config_identity or f"{type(llm_client).__module__}.{type(llm_client).__qualname__}"
        ),
        **graph_kwargs,
        runtime_config=runtime_config,
        official_web_service=official_web_service,
        reference_service=ReferenceDiscoveryService(
            places_provider if isinstance(places_provider, NearbyPlacesProvider) else None,
            cache,
            reference_discovery_config or runtime_config.reference_discovery,
        ),
    )
    effective_tracer.event(
        "run_started",
        {
            "runtime_config": runtime_config_snapshot(runtime_config)[0],
            "runtime_config_hash": runtime_config_snapshot(runtime_config)[1],
            "runtime_config_path": str(runtime_config_path) if runtime_config_path else None,
            "run_id": effective_tracer.run_id,
            "system_version": system_version.value,
            "request": request,
            "runtime_reference_date": effective_reference_date,
            "allowed_date_window": {
                "start": date_window.allowed_start,
                "end": date_window.allowed_end,
            },
        },
    )
    try:
        if development_timeout_seconds is not None:
            if not 0 < development_timeout_seconds <= runtime_config.development_timeout_seconds:
                raise ValueError("Invalid development whole-request timeout")
            async with asyncio.timeout_at(request_started + development_timeout_seconds):
                final_state = await graph.ainvoke(
                    {"request": request, "reference_date": effective_reference_date}
                )
        else:
            final_state = await graph.ainvoke(
                {"request": request, "reference_date": effective_reference_date}
            )
        requirements = final_state.get("requirements")
        itinerary = final_state.get("itinerary")
        if requirements is None or itinerary is None:
            raise RuntimeError("V1 graph completed without a planning result")
        selection = final_state["review_selection"]
        extra = {"rag_discovery": extension.finalize(final_state)} if extension else {}
        if result_projector is not None:
            extra.update(result_projector(final_state))
        result = result_factory(
            **extra,
            semantic_assessment=evidence_service.poi_semantics.snapshot()
            if getattr(evidence_service, "poi_semantics", None)
            else None,
            generation_diagnostics=final_state["generation_diagnostics"],
            system_version=system_version,
            requirements=requirements,
            itinerary=itinerary,
            interpreted_requirements=final_state["interpreted_requirements"],
            selection_status="degraded_selection"
            if selection.policy_result.shortfall
            else "selected",
            planning_supply=selection.policy_result,
            output_role_summary=output_role_summary(itinerary, selection.policy_result),
        )
    except asyncio.CancelledError as exc:
        if capture is not None:
            capture.finish(rag=extension.report if extension else None, failure=exc)
        raise
    except Exception as exc:
        if capture is not None:
            capture.finish(rag=extension.report if extension else None, failure=exc)
        effective_tracer.event(
            "run_failed",
            {"error": type(exc).__name__},
        )
        effective_tracer.finish(
            status="failed",
            requirements=None,
            tool_usage=budget.summary(),
            outcome=None,
            error={"error": type(exc).__name__},
        )
        raise

    if capture is not None:
        capture.finish(result=result, rag=extra.get("rag_discovery"))
    effective_tracer.event("run_completed")
    effective_tracer.finish(
        status="completed",
        requirements=result.requirements,
        tool_usage=budget.summary(),
        outcome=result,
    )
    return result


async def run_v1(request, llm_client, places_provider, weather_provider, routes_provider, **kwargs):
    """Independent Google-only entry; no retrieval clients or database initialization."""
    if {"system_version", "graph_factory", "discovery_factory", "result_factory"} & kwargs.keys():
        raise ValueError("Version dependencies belong to the explicit version runner")
    return await run_tools_planner(
        request, llm_client, places_provider, weather_provider, routes_provider, **kwargs
    )


def build_argument_parser() -> argparse.ArgumentParser:
    """Build the independent V1 command-line parser."""

    parser = argparse.ArgumentParser(description="Run the V1-A evidence-informed travel planner.")
    parser.add_argument(
        "--input-json", required=True, help="Path to a shared PlanningRequest JSON file."
    )
    parser.add_argument(
        "--reference-date",
        type=parse_reference_date,
        help="Trusted research reference date in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--runtime-config", type=Path, help="Explicit immutable runtime YAML policy"
    )
    parser.add_argument(
        "--opportunity-capture",
        type=Path,
        help="Optional exclusive best-effort local candidate stage export (V1/V2)",
    )
    parser.add_argument(
        "--development-timeout-seconds",
        type=float,
        help="Explicit bounded whole-run development wait",
    )
    return parser


def serialize_planning_result(result: PlanningResult) -> str:
    """Serialize CLI JSON using ASCII escapes for encoding-independent output."""

    return result.model_dump_json(indent=2, ensure_ascii=True)


def _create_tool_providers(
    settings: V1Settings,
    tracer: RunTracer,
) -> tuple[PlacesProvider, WeatherProvider, RoutesProvider]:
    api_key = settings.google_maps_api_key.get_secret_value()
    transport = HttpxJSONTransport()
    return (
        GooglePlacesProvider(api_key=api_key, transport=transport, tracer=tracer),
        OpenMeteoWeatherProvider(transport=transport, tracer=tracer),
        GoogleRoutesProvider(api_key=api_key, transport=transport, tracer=tracer),
    )


def _create_official_web_providers(
    settings: V1Settings,
    config: WebEvidenceConfig,
    *,
    existing=(None, None, None),
    owned_clients=None,
) -> tuple[WebEvidenceProvider, PageRetriever, OfficialEvidenceReasoner]:
    endpoint = str(settings.azure_openai_endpoint)
    deployment = settings.azure_openai_deployment
    api_key = settings.azure_openai_api_key.get_secret_value()
    factories = (
        lambda: AzureFoundryWebEvidenceProvider(
            endpoint=endpoint, deployment=deployment, api_key=api_key, config=config
        ),
        lambda: SafeHTMLPageRetriever(config.page_retrieval),
        lambda: AzureFoundryEvidenceReasoner(
            endpoint=endpoint, deployment=deployment, api_key=api_key, config=config
        ),
    )
    result = []
    for supplied, factory in zip(existing, factories, strict=True):
        value = supplied if supplied is not None else factory()
        if supplied is None and owned_clients is not None and hasattr(value, "aclose"):
            owned_clients.append(value)
        result.append(value)
    return tuple(result)


def main(
    argv: Sequence[str] | None = None,
    *,
    llm_client: StructuredLLMClient | None = None,
    places_provider: PlacesProvider | None = None,
    weather_provider: WeatherProvider | None = None,
    routes_provider: RoutesProvider | None = None,
    tracer: RunTracer | None = None,
    budget_limits: ToolBudgetLimits | None = None,
    date_provider: DateProvider | None = None,
    web_provider: WebEvidenceProvider | None = None,
    page_retriever: PageRetriever | None = None,
    official_reasoner: OfficialEvidenceReasoner | None = None,
    planner_runner=None,
    system_version=SystemVersion.V1,
    loop_factory=None,
) -> int:
    """Execute the V1 CLI and return a process exit code."""

    parser = build_argument_parser()
    parser.description = f"Run the {system_version.value.upper()} tools travel planner."
    args = parser.parse_args(argv)
    all_clients_injected = all(
        item is not None
        for item in (llm_client, places_provider, weather_provider, routes_provider)
    )
    settings: V1Settings | None = None
    owned_clients = []
    cleanup_delegated = False
    try:
        request = read_planning_request(args.input_json)
        runtime_config = (
            load_runtime_config_file(args.runtime_config)
            if args.runtime_config
            else load_runtime_config()
        )
        configure_logging(runtime_config.logging)
        if not all_clients_injected:
            settings = V1Settings()
        budget_limits = budget_limits or (tool_limits(runtime_config))

        if args.reference_date is not None and date_provider is not None:
            raise ValueError("reference_date and date_provider cannot both be supplied")
        effective_reference_date = (
            args.reference_date
            or (date_provider or SystemDateProvider(runtime_config.app.time_zone)).today()
        )
        request = validate_planning_request(request, effective_reference_date)
        run_id = uuid4()
        started_at = datetime.now(UTC)
        config_snapshot, config_hash = runtime_config_snapshot(
            runtime_config,
            effective_budget={
                **{key.value: value for key, value in budget_limits.as_key_limits().items()},
                "baseline_route_matrix_elements_per_request": (
                    budget_limits.max_baseline_route_matrix_elements_per_request
                ),
            },
        )
        context = RunTraceContext(
            run_id=run_id,
            system_version=system_version.value,
            reference_date=effective_reference_date,
            date_window=create_trip_date_window(effective_reference_date),
            request=request,
            started_at=started_at,
            runtime_config=config_snapshot,
            runtime_config_sha256=config_hash,
        )
        if tracer is None:
            if settings is None:
                effective_tracer: RunTracer = NullRunTracer(run_id)
            else:
                effective_tracer = create_run_tracer(
                    context,
                    enabled=runtime_config.trace.enabled,
                    root=resolve_trace_directory(runtime_config.trace.directory),
                    payload_mode=runtime_config.trace.payload_level,
                    max_payload_bytes=runtime_config.trace.max_payload_bytes,
                    capture_llm=runtime_config.trace.capture_llm,
                    capture_tools=runtime_config.trace.capture_tools,
                    capture_evidence=runtime_config.trace.capture_evidence,
                    raw_provider_payloads=runtime_config.trace.raw_provider_payloads,
                )
        else:
            effective_tracer = tracer

        if settings is not None:
            default_places, default_weather, default_routes = _create_tool_providers(
                settings, effective_tracer
            )
            if llm_client is None:
                llm_client = create_foundry_client(settings)
                owned_clients.append(llm_client)
            places_provider = places_provider or default_places
            weather_provider = weather_provider or default_weather
            routes_provider = routes_provider or default_routes
            if not all(p is not None for p in (web_provider, page_retriever, official_reasoner)):
                web_provider, page_retriever, official_reasoner = _create_official_web_providers(
                    settings,
                    runtime_config.web_evidence,
                    existing=(web_provider, page_retriever, official_reasoner),
                    owned_clients=owned_clients,
                )

        if (
            llm_client is None
            or places_provider is None
            or weather_provider is None
            or routes_provider is None
        ):
            raise RuntimeError("V1 providers were not configured")

        cleanup_delegated = True
        result = asyncio.run(
            _run_with_owned_clients(
                (planner_runner or run_v1)(
                    request,
                    llm_client,
                    places_provider,
                    weather_provider,
                    routes_provider,
                    reference_date=effective_reference_date,
                    budget_limits=budget_limits,
                    tracer=effective_tracer,
                    llm_config_identity=(
                        settings.azure_openai_deployment if settings is not None else None
                    ),
                    web_provider=web_provider,
                    page_retriever=page_retriever,
                    official_reasoner=official_reasoner,
                    web_evidence_config=runtime_config.web_evidence,
                    runtime_config=runtime_config,
                    runtime_config_path=args.runtime_config,
                    development_timeout_seconds=args.development_timeout_seconds,
                    **(
                        {"opportunity_capture_path": args.opportunity_capture}
                        if args.opportunity_capture is not None
                        else {}
                    ),
                ),
                owned_clients,
            ),
            loop_factory=loop_factory,
        )
    except RequirementBoundaryError as exc:
        print(json.dumps(exc.as_dict()), file=sys.stderr)
        return 1
    except ClarificationRequired as exc:
        print(json.dumps(exc.as_dict()), file=sys.stderr)
        return 2
    except (ValidationError, OSError) as exc:
        print(json.dumps({"error": "invalid_planning_input", "message": str(exc)}), file=sys.stderr)
        return 2
    except TripDatePolicyError as exc:
        print(json.dumps(exc.as_detail()), file=sys.stderr)
        return 2
    except NoViableCandidatesError as exc:
        print(
            json.dumps({"error": "no_viable_candidates", "message": str(exc)}),
            file=sys.stderr,
        )
        return 2
    except V1StageError as exc:
        cause = exc.__cause__
        error = {
            "error": f"{system_version.value}_stage_failed",
            "stage": exc.stage,
            "message": str(cause) if cause is not None else str(exc),
        }
        print(json.dumps(error), file=sys.stderr)
        return 1
    except Exception as exc:
        error = {"error": f"{system_version.value}_execution_failed", "message": str(exc)}
        print(json.dumps(error), file=sys.stderr)
        return 1
    finally:
        if not cleanup_delegated and owned_clients:
            # Assembly can fail before there is a running event loop or any request I/O.
            asyncio.run(_close_owned_clients(owned_clients), loop_factory=loop_factory)

    print(serialize_planning_result(result))
    return 0


async def _run_with_owned_clients(operation, owned_clients):
    """CLI-created adapters close on the same loop; injected collaborators are borrowed."""
    try:
        return await operation
    finally:
        await _close_owned_clients(owned_clients)


async def _close_owned_clients(owned_clients):
    results = await asyncio.gather(
        *(client.aclose() for client in reversed(owned_clients) if hasattr(client, "aclose")),
        return_exceptions=True,
    )
    # Cleanup failure must not mask the original planning failure/cancellation.
    for result in results:
        if isinstance(result, BaseException):
            import logging

            logging.getLogger(__name__).warning(
                "Owned client cleanup failed: %s", type(result).__name__
            )
