"""Independent V3 request entry; primary planning is shared, repair is opt-in by version."""

import asyncio
from functools import partial
from time import monotonic

from langgraph.errors import NodeCancelledError

from backend.app.runtime.config_loader import load_runtime_config
from backend.app.schemas.planning import SystemVersion
from backend.app.services.tripworld_discovery import TripWorldDiscovery
from backend.app.tripworld.retrieval.runtime import RuntimeRetrieval
from backend.app.versions.v1.runner import run_tools_planner
from backend.app.versions.v3.graph import build_v3_graph
from backend.app.versions.v3.resources import DeadlinePort, RequestRetrieval
from backend.app.versions.v3.state import V3PlanningResult
from backend.app.versions.v3.wiring import project_result


async def run_v3(
    request,
    llm_client,
    places_provider,
    weather_provider,
    routes_provider,
    *,
    development_timeout_seconds=None,
    request_started_at=None,
    quantity_review_enabled=None,
    runtime_config_source=None,
    retrieval_factory=None,
    retrieval_runtime=None,
    **kwargs,
):
    """Injected clients remain caller-owned. Factory-created retrieval is request-owned.

    An explicit whole-request allowance is mandatory; CLI passes its earlier entry time
    so dependency setup cannot reset the allowance. Model/HTTP defaults are unchanged.
    """
    started = monotonic() if request_started_at is None else request_started_at
    if runtime_config_source is None:
        runtime_config_source = (
            "injected_runtime_config"
            if kwargs.get("runtime_config") is not None
            else "config/runtime.yaml"
        )
    config = kwargs.get("runtime_config") or load_runtime_config()
    if development_timeout_seconds is None or not (
        0 < development_timeout_seconds <= config.development_timeout_seconds
    ):
        raise ValueError("V3 requires an explicit bounded whole-request timeout")
    if retrieval_factory is not None and retrieval_runtime is not None:
        raise ValueError("Choose owned retrieval factory or externally owned runtime")
    if config.v3_repair is None:
        raise ValueError("V3 requires runtime.v3_repair configuration")
    review_source = "runtime.yaml" if quantity_review_enabled is None else "explicit_override"
    if quantity_review_enabled is None:
        quantity_review_enabled = config.v3_repair.quantity_review_enabled
    from backend.app.runtime.config_loader import runtime_config_snapshot

    base_config_hash = runtime_config_snapshot(config)[1]
    config = config.model_copy(
        update={
            "v3_repair": config.v3_repair.model_copy(
                update={"quantity_review_enabled": quantity_review_enabled}
            )
        }
    )
    deadline = started + development_timeout_seconds
    kwargs["runtime_config"] = config
    if kwargs.get("llm_config_identity") is None:
        kwargs["llm_config_identity"] = (
            f"{type(llm_client).__module__}.{type(llm_client).__qualname__}"
        )
    tracer = kwargs.get("tracer")
    if tracer is not None:
        tracer.event(
            "v3_request_policy",
            {
                "quantity_review_enabled": quantity_review_enabled,
                "review_policy_source": review_source,
                "runtime_config_source": runtime_config_source,
                "base_runtime_config_hash": base_config_hash,
                "effective_runtime_config_hash": runtime_config_snapshot(config)[1],
                "repair_policy": config.v3_repair.model_dump(mode="json"),
                "nearby_reserve_seconds": config.reference_discovery.deadline_seconds,
                "operation_policy": "v3_operations_1",
                "started_at_monotonic": started,
                "request_deadline_monotonic": deadline,
            },
        )
    for key in ("web_provider", "page_retriever", "official_reasoner"):
        if kwargs.get(key) is not None:
            kwargs[key] = DeadlinePort(kwargs[key], deadline)
    owner = RequestRetrieval(
        retrieval_factory or (lambda: RuntimeRetrieval(config.tripworld_discovery)),
        deadline,
        runtime=retrieval_runtime,
    )
    try:
        owner.check_time()
        async with asyncio.timeout_at(deadline):
            result = await run_tools_planner(
                request,
                DeadlinePort(llm_client, deadline),
                DeadlinePort(places_provider, deadline),
                DeadlinePort(weather_provider, deadline),
                DeadlinePort(routes_provider, deadline),
                system_version=SystemVersion.V3,
                graph_factory=partial(
                    build_v3_graph,
                    owner=owner,
                    request_deadline=deadline,
                    quantity_review_enabled=quantity_review_enabled,
                ),
                discovery_factory=partial(
                    TripWorldDiscovery,
                    config=config.tripworld_discovery,
                    runtime_factory=lambda: owner,
                ),
                result_factory=V3PlanningResult,
                result_projector=project_result,
                **kwargs,
            )
            owner.check_time()
    except NodeCancelledError as exc:
        # LangGraph translates cancellation raised by a dependency without task.cancel().
        # Preserve the caller-facing cancellation contract instead of reporting failure.
        raise asyncio.CancelledError() from exc
    finally:
        await owner.close()
        resources = owner.snapshot() | {
            "started_at_monotonic": started,
            "request_deadline_monotonic": deadline,
        }
        if tracer is not None:
            tracer.event("v3_resources_released", resources)
    return result.model_copy(update={"request_resources": resources})


def main(argv=None, **kwargs):
    """CLI deadline begins before local configuration and dependency construction."""
    import argparse
    import sys

    from dotenv import load_dotenv

    from backend.app.versions.v1.runner import main as tools_main

    started = monotonic()
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--rag-env-file")
    parser.add_argument("--runtime-config")
    parser.add_argument(
        "--repair-quantity-review", action=argparse.BooleanOptionalAction, default=None
    )
    args, remaining = parser.parse_known_args(argv)
    if args.runtime_config:
        remaining = ["--runtime-config", args.runtime_config, *remaining]
    from backend.app.runtime.configuration_paths import configuration_directory

    load_dotenv(args.rag_env_file or configuration_directory() / ".env", override=False)
    return tools_main(
        remaining,
        planner_runner=partial(
            run_v3,
            request_started_at=started,
            quantity_review_enabled=args.repair_quantity_review,
            runtime_config_source=args.runtime_config
            or (
                "injected_runtime_config"
                if kwargs.get("runtime_config") is not None
                else "config/runtime.yaml"
            ),
        ),
        system_version=SystemVersion.V3,
        loop_factory=asyncio.SelectorEventLoop if sys.platform == "win32" else None,
        **kwargs,
    )
