"""Product service diagnostics coexist with progress and the public presentation."""

import asyncio
import json
from datetime import date

import pytest

from backend.app.observability.product_logs import ProductLogs, log_context
from backend.app.observability.progress import ProgressObserver, progress_scope
from backend.app.schemas.request import PlanningRequest
from backend.app.services.planning import PlanningFailedError, PlanningService
from backend.tests.api.test_product_planning import make_product_payload
from backend.tests.fakes import FixedDateProvider, V0TestRuntime
from backend.tests.versions.v0.fakes import FakeStructuredLLMClient, make_itinerary


def test_product_run_retains_repair_reason_and_progress(tmp_path, monkeypatch):
    monkeypatch.setenv("PRODUCT_LOG_DIRECTORY", str(tmp_path))
    monkeypatch.setenv("PRODUCT_LOG_ENABLED", "true")

    class Runtime(V0TestRuntime):
        async def run(self, *args, tracer=None, **kwargs):
            tracer.event("v3_repair_decision", {"status": "REJECTED", "reason": "opening_conflict"})
            tracer.event(
                "v3_finalized",
                {
                    "reason": "model_call_limit",
                    "repair": {"status": "ACCEPTED_PARTIAL"},
                    "soft_pace": {"completion": {"status": "partial"}},
                },
            )
            return await super().run(*args, tracer=tracer, **kwargs)

    observer = ProgressObserver()
    service = PlanningService(
        Runtime(FakeStructuredLLMClient([make_itinerary()]), "v3"),
        FixedDateProvider(date(2026, 9, 11)),
    )

    async def run():
        with log_context(task_id="diagnostic-task"), progress_scope(observer):
            return await service.plan(PlanningRequest.model_validate(make_product_payload()))

    result = asyncio.run(run())
    assert result.itinerary.destination == "Kyoto"
    rows = ProductLogs().read(task_id="diagnostic-task")
    summary = next(row for row in rows if "collection_status" in row)
    assert summary["stop_reason"] == "model_call_limit"
    assert summary["repair_status"] == "ACCEPTED_PARTIAL"
    assert any(row.get("event") == "v3_repair_decision" for row in rows)
    assert observer.buffer


@pytest.mark.parametrize("failure", [RuntimeError("private value"), asyncio.CancelledError()])
def test_failed_or_cancelled_service_keeps_summary_and_original_error(
    tmp_path, monkeypatch, failure
):
    monkeypatch.setenv("PRODUCT_LOG_DIRECTORY", str(tmp_path))
    monkeypatch.setenv("PRODUCT_LOG_ENABLED", "true")

    class Runtime:
        async def run(self, *args, **kwargs):
            raise failure

    service = PlanningService(Runtime(), FixedDateProvider(date(2026, 9, 11)))
    with pytest.raises(
        asyncio.CancelledError
        if isinstance(failure, asyncio.CancelledError)
        else PlanningFailedError
    ):
        asyncio.run(service.plan(PlanningRequest.model_validate(make_product_payload())))
    summary = ProductLogs().read(summaries_only=True)[0]
    assert summary["status"] == (
        "cancelled" if isinstance(failure, asyncio.CancelledError) else "failed"
    )
    assert "private value" not in json.dumps(summary)


def test_usage_observation_records_real_callback_usage_and_restores_context(tmp_path, monkeypatch):
    from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
    from langchain_core.messages import AIMessage

    from backend.app.observability.usage import current_usage

    monkeypatch.setenv("PRODUCT_LOG_DIRECTORY", str(tmp_path))
    monkeypatch.setenv("PRODUCT_LOG_ENABLED", "true")
    model = FakeMessagesListChatModel(
        responses=[
            AIMessage(
                content="ok",
                usage_metadata={"input_tokens": 11, "output_tokens": 5, "total_tokens": 16},
            )
        ]
    )

    class Runtime(V0TestRuntime):
        async def run(self, *args, **kwargs):
            await model.ainvoke("private prompt")
            return await super().run(*args, **kwargs)

    service = PlanningService(
        Runtime(FakeStructuredLLMClient([make_itinerary()]), "v3"),
        FixedDateProvider(date(2026, 9, 11)),
    )
    asyncio.run(service.plan(PlanningRequest.model_validate(make_product_payload())))
    summary = ProductLogs().read(summaries_only=True)[0]
    assert summary["usage"]["reported"] == {
        "input_tokens": 11,
        "output_tokens": 5,
        "total_tokens": 16,
    }
    assert current_usage.get() is None
    assert "private prompt" not in json.dumps(ProductLogs().read())


def test_cancelled_real_v3_retains_consumed_primary_tool_budget(tmp_path, monkeypatch):
    from contextlib import asynccontextmanager

    from backend.app.services.planner_runtime import PlannerDependencies, RequestPlannerRuntime
    from backend.tests.request_fixtures import make_request
    from backend.tests.versions.v1.fakes import FakeRoutesProvider, FakeWeatherProvider
    from backend.tests.versions.v2.test_v2_runner import Places
    from backend.tests.versions.v3.test_wiring import Model, OwnedRetrieval

    monkeypatch.setenv("PRODUCT_LOG_DIRECTORY", str(tmp_path))
    monkeypatch.setenv("PRODUCT_LOG_ENABLED", "true")
    monkeypatch.setattr(
        "backend.app.versions.v3.runner.RuntimeRetrieval", lambda _: OwnedRetrieval()
    )

    entered = asyncio.Event()

    class WaitingModel(Model):
        async def generate_repair_structured(self, **kwargs):
            entered.set()
            await asyncio.Event().wait()

    @asynccontextmanager
    async def dependencies(*args):
        yield PlannerDependencies(
            WaitingModel(), Places(), FakeWeatherProvider(), FakeRoutesProvider()
        )

    service = PlanningService(
        RequestPlannerRuntime(dependency_factory=dependencies), FixedDateProvider(date(2026, 9, 11))
    )

    async def stop_running():
        task = asyncio.create_task(service.plan(make_request()))
        await asyncio.wait_for(entered.wait(), timeout=5)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(stop_running())
    budget = json.loads(next(tmp_path.glob("runs/*/budget.json")).read_text())
    assert any(row["used"] > 0 for row in budget["primary_tools"].values())
