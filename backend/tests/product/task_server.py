"""Real browser acceptance app; only external providers use controlled substitutes."""

import asyncio
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

from backend.app.api.dependencies import get_date_provider, get_planning_service
from backend.app.runtime.config_loader import load_runtime_config
from backend.app.services.planner_runtime import PlannerDependencies, RequestPlannerRuntime
from backend.app.services.planning import PlanningService
from backend.app.services.product_introductions import IntroductionBatch, ProductIntroductions
from backend.tests.fakes import FixedDateProvider
from backend.tests.product.editor_server import create_editor_app
from backend.tests.versions.v1.fakes import FakeRoutesProvider, FakeWeatherProvider
from backend.tests.versions.v2.test_v2_runner import Places
from backend.tests.versions.v3.test_wiring import Model, OwnedRetrieval

CONTROL = Path(__file__).resolve().parents[3] / ".scratch/task-browser/signals"


def create_task_app():
    from backend.app.versions.v3 import runner

    application = create_editor_app()
    CONTROL.mkdir(parents=True, exist_ok=True)

    class Retrieval(OwnedRetrieval):
        async def __aenter__(self):
            (CONTROL / "retrieval-entered").touch()
            return await super().__aenter__()

        async def __aexit__(self, *args):
            await super().__aexit__(*args)
            (CONTROL / "retrieval-closed").touch()

    runner.RuntimeRetrieval = lambda config: Retrieval()

    class GatedModel(Model):
        async def generate_structured(self, **kwargs):
            (CONTROL / "model-entered").touch()
            # Poll an explicit external completion signal, never a simulated completion timer.
            async with asyncio.timeout(120):
                while not (CONTROL / "model-release").exists():
                    await asyncio.sleep(0.025)
            outcome = (
                (CONTROL / "model-outcome").read_text()
                if (CONTROL / "model-outcome").exists()
                else ""
            )
            if outcome:
                from backend.app.schemas.requirement_boundary import RequirementBoundaryError
                from backend.tests.services.test_preference_input_gate import draft, issue

                source = "<b>Keep a private travel preference.</b>"
                if outcome == "needs_clarification":
                    return draft(issue(text=source))
                if outcome == "safety_blocked":
                    return draft(
                        issue("safety_self_harm", text=source, related_field=None),
                        disposition="VALID",
                        safety="SAFETY_BLOCK",
                    )
                if outcome == "provider_blocked":
                    raise RequirementBoundaryError(
                        "PRIVATE provider failure",
                        category="provider_request_rejected",
                        provider_diagnostics={
                            "provider_error_code": "content_filter",
                            "private": source,
                        },
                    )
                if outcome == "interrupted":
                    raise asyncio.CancelledError()
                raise RuntimeError("PRIVATE external failure")
            return await super().generate_structured(**kwargs)

    @asynccontextmanager
    async def dependencies(*args):
        with (CONTROL / "executions").open("a") as output:
            output.write("one\n")
        yield PlannerDependencies(
            GatedModel(behavior="empty"), Places(), FakeWeatherProvider(), FakeRoutesProvider()
        )

    class Introductions:
        async def generate(self, places):
            return IntroductionBatch(introductions=[])

    @asynccontextmanager
    async def introductions():
        yield Introductions()

    base_config = load_runtime_config()
    config = base_config.model_copy(
        update={
            "trace": base_config.trace.model_copy(update={"directory": CONTROL.parent / "traces"})
        }
    )
    provider = FixedDateProvider(date(2026, 9, 11))
    service = PlanningService(
        RequestPlannerRuntime(config=config, dependency_factory=dependencies),
        provider,
        introductions=ProductIntroductions(introductions),
    )
    application.dependency_overrides[get_planning_service] = lambda: service
    application.dependency_overrides[get_date_provider] = lambda: provider
    return application


if __name__ == "__main__":
    import argparse

    import uvicorn

    from scripts.run_api import create_api_loop

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    arguments = parser.parse_args()
    server = uvicorn.Server(
        uvicorn.Config(create_task_app(), host="127.0.0.1", port=arguments.port)
    )
    asyncio.run(server.serve(), loop_factory=create_api_loop)
