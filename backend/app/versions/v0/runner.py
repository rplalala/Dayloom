"""Public runner and command-line behavior for V0."""

import argparse
import asyncio
import json
import sys
from collections.abc import Sequence
from datetime import date

from pydantic import ValidationError

from backend.app.llm.azure_foundry import AzureFoundryStructuredLLMClient
from backend.app.llm.client import StructuredLLMClient
from backend.app.policies.generation_diagnostics import observe_generation
from backend.app.policies.trip_dates import (
    DateProvider,
    SystemDateProvider,
    TripDatePolicyError,
    create_trip_date_window,
    validate_itinerary_dates,
)
from backend.app.runtime.config_loader import load_runtime_config
from backend.app.runtime.logging_config import configure_logging
from backend.app.runtime.settings import RuntimeSettings
from backend.app.schemas.interpreted_requirements import ClarificationRequired
from backend.app.schemas.planning import PlanningResult, SystemVersion
from backend.app.schemas.request import PlanningRequest
from backend.app.schemas.requirement_boundary import RequirementBoundaryError
from backend.app.services.preference_interpretation import (
    read_planning_request,
    validate_planning_request,
)
from backend.app.versions.v0.config import V0Settings
from backend.app.versions.v0.graph import (
    V0StageError,
    build_v0_graph,
)


async def run_v0(
    request: PlanningRequest,
    llm_client: StructuredLLMClient,
    *,
    reference_date: date | None = None,
    date_provider: DateProvider | None = None,
) -> PlanningResult:
    """Run V0 and return its stable shared result contract."""

    if reference_date is not None and date_provider is not None:
        raise ValueError("reference_date and date_provider cannot both be supplied")

    effective_reference_date = reference_date or (date_provider or SystemDateProvider()).today()
    request = validate_planning_request(request, effective_reference_date)
    date_window = create_trip_date_window(effective_reference_date)
    graph = build_v0_graph(llm_client)
    final_state = await graph.ainvoke(
        {
            "request": request,
            "reference_date": effective_reference_date,
        }
    )

    requirements = final_state.get("requirements")
    itinerary = final_state.get("itinerary")
    if requirements is None or itinerary is None:
        raise RuntimeError("V0 graph completed without a planning result")

    validate_itinerary_dates(requirements, itinerary, date_window)

    return PlanningResult(
        generation_diagnostics=observe_generation(
            itinerary,
            requirements,
            reference_date=effective_reference_date,
            contract=final_state["interpreted_requirements"],
            related_requirement_ids=tuple(
                r.requirement_id
                for r in final_state["interpreted_requirements"].semantic_requirements
            ),
        ),
        system_version=SystemVersion.V0,
        requirements=requirements,
        itinerary=itinerary,
    )


def create_foundry_client(
    settings: V0Settings, *, auxiliary_limits=None
) -> AzureFoundryStructuredLLMClient:
    """Create the default provider client from explicit V0 settings."""

    return AzureFoundryStructuredLLMClient(
        endpoint=str(settings.azure_openai_endpoint),
        deployment=settings.azure_openai_deployment,
        api_key=settings.azure_openai_api_key.get_secret_value(),
        auxiliary_limits=auxiliary_limits,
    )


def parse_reference_date(value: str) -> date:
    """Parse an ISO 8601 date for argparse."""

    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("reference date must use YYYY-MM-DD") from exc


def build_argument_parser() -> argparse.ArgumentParser:
    """Build the independent V0 command-line parser."""

    parser = argparse.ArgumentParser(description="Run the V0 plain-LLM travel planner.")
    parser.add_argument(
        "--input-json", required=True, help="Path to a shared PlanningRequest JSON file."
    )
    parser.add_argument(
        "--reference-date",
        type=parse_reference_date,
        help="Reference date for relative dates, in YYYY-MM-DD format.",
    )
    return parser


def serialize_planning_result(result: PlanningResult) -> str:
    """Serialize CLI JSON using ASCII escapes for encoding-independent output."""

    return result.model_dump_json(indent=2, ensure_ascii=True)


def main(
    argv: Sequence[str] | None = None,
    *,
    llm_client: StructuredLLMClient | None = None,
) -> int:
    """Execute the V0 CLI and return a process exit code."""

    args = build_argument_parser().parse_args(argv)

    try:
        request = read_planning_request(args.input_json)
        configure_logging(load_runtime_config().logging)
        settings = V0Settings() if llm_client is None else RuntimeSettings()
        effective_date = args.reference_date or SystemDateProvider(settings.app_time_zone).today()
        request = validate_planning_request(request, effective_date)
        client = llm_client or create_foundry_client(settings)
        result = asyncio.run(
            run_v0(
                request,
                client,
                reference_date=effective_date,
            )
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
    except V0StageError as exc:
        cause = exc.__cause__
        error = {
            "error": "v0_stage_failed",
            "stage": exc.stage,
            "message": str(cause) if cause is not None else str(exc),
        }
        print(json.dumps(error), file=sys.stderr)
        return 1
    except Exception as exc:
        error = {
            "error": "v0_execution_failed",
            "message": str(exc),
        }
        print(json.dumps(error), file=sys.stderr)
        return 1

    print(serialize_planning_result(result))
    return 0
