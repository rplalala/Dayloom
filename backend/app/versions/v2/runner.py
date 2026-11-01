"""Independent V2 dispatch over the shared tools planner."""

from functools import partial

from backend.app.runtime.config_loader import load_runtime_config
from backend.app.schemas.planning import SystemVersion
from backend.app.services.tripworld_discovery import TripWorldDiscovery
from backend.app.versions.v1.runner import run_tools_planner
from backend.app.versions.v2.graph import build_v2_graph
from backend.app.versions.v2.state import V2PlanningResult


async def run_v2(
    request,
    llm_client,
    places_provider,
    weather_provider,
    routes_provider,
    *,
    rag_config=None,
    retrieval_factory=None,
    **kwargs,
):
    config = kwargs.get("runtime_config") or load_runtime_config()
    if (
        config.acquisition.policy_id == "quality_first_1"
        and rag_config is not None
        and rag_config != config.tripworld_discovery
    ):
        raise ValueError("Historical RAG override cannot replace quality-first policy")
    return await run_tools_planner(
        request,
        llm_client,
        places_provider,
        weather_provider,
        routes_provider,
        system_version=SystemVersion.V2,
        graph_factory=build_v2_graph,
        discovery_factory=partial(
            TripWorldDiscovery,
            config=rag_config or config.tripworld_discovery,
            runtime_factory=retrieval_factory,
        ),
        result_factory=V2PlanningResult,
        **kwargs,
    )


def main(argv=None, **kwargs):
    """Reuse CLI dependency ownership with explicit version and runner dispatch."""
    import argparse
    import asyncio
    import sys

    from dotenv import load_dotenv

    from backend.app.versions.v1.runner import main as tools_main

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--rag-env-file", help="Optional local V2 DB/embedding environment file")
    args, remaining = parser.parse_known_args(argv)
    from backend.app.runtime.configuration_paths import configuration_directory

    load_dotenv(args.rag_env_file or configuration_directory() / ".env", override=False)
    return tools_main(
        remaining,
        planner_runner=run_v2,
        system_version=SystemVersion.V2,
        loop_factory=asyncio.SelectorEventLoop if sys.platform == "win32" else None,
        **kwargs,
    )
