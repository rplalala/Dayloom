"""Public tools runner passive-capture parity with synthetic borrowed providers."""

import asyncio
import json
from datetime import date

from backend.app.versions.v1.runner import run_v1
from backend.app.versions.v2.runner import run_v2
from backend.tests.request_fixtures import make_request
from backend.tests.services.test_tripworld_discovery import Retrieval, hit
from backend.tests.versions.v0.fakes import FakeStructuredLLMClient
from backend.tests.versions.v1.fakes import FakeRoutesProvider, FakeWeatherProvider, make_itinerary
from backend.tests.versions.v2.test_v2_runner import Places

pytest_plugins = ("backend.tests.versions.v2.test_v2_runner",)


def stable(value):
    if isinstance(value, dict):
        return {
            key: stable(item)
            for key, item in value.items()
            if key
            not in (
                "elapsed_seconds",
                "cpu_seconds",
                "phase_seconds",
                "call_id",
                "remaining_seconds",
            )
        }
    if isinstance(value, list):
        return [stable(item) for item in value]
    return value


def test_passive_export_has_identical_calls_payloads_and_planning_output(tmp_path):
    async def scenario(runner, path):
        places, llm, weather, routes = (
            Places(),
            FakeStructuredLLMClient([make_itinerary()]),
            FakeWeatherProvider(),
            FakeRoutesProvider(),
        )
        kwargs = (
            {"retrieval_factory": lambda: Retrieval([hit("aaa-rag")])} if runner == run_v2 else {}
        )
        result = await runner(
            make_request(),
            llm,
            places,
            weather,
            routes,
            reference_date=date(2026, 9, 11),
            opportunity_capture_path=path,
            **kwargs,
        )
        return result, llm.calls, places.search_requests, places.details_requests, places.nearby

    for runner in (run_v1, run_v2):
        plain = asyncio.run(scenario(runner, None))
        path = tmp_path / (runner.__name__ + ".json")
        enabled = asyncio.run(scenario(runner, path))
        assert plain[0].itinerary == enabled[0].itinerary
        assert stable(plain[0].model_dump(mode="json")) == stable(
            enabled[0].model_dump(mode="json")
        )
        assert plain[1:] == enabled[1:]
        captured = json.loads(path.read_text())
        assert captured["schema_version"] == "rtpeval_candidate_capture_1"
        assert captured["stages"]["discovered"]["status"] == "complete"
        assert len(captured["stages"]["supplied"]["places"]) == (9 if runner == run_v1 else 10)
        failed_write = asyncio.run(scenario(runner, tmp_path))
        assert plain[0].itinerary == failed_write[0].itinerary
        assert plain[1:] == failed_write[1:]


def test_failure_and_cancellation_preserve_original_outcome_and_partial_export(tmp_path):
    import pytest

    class FailingLLM(FakeStructuredLLMClient):
        async def generate_structured(self, **kwargs):
            raise self.responses[0]

    class BlockingLLM(FakeStructuredLLMClient):
        def __init__(self, started):
            super().__init__([])
            self.started = started

        async def generate_structured(self, **kwargs):
            self.started.set()
            await asyncio.Event().wait()

    async def failing(cancel, path):
        started = asyncio.Event()
        llm = BlockingLLM(started) if cancel else FailingLLM([RuntimeError("synthetic-failure")])
        task = asyncio.create_task(
            run_v1(
                make_request(),
                llm,
                Places(),
                FakeWeatherProvider(),
                FakeRoutesProvider(),
                reference_date=date(2026, 9, 11),
                opportunity_capture_path=path,
            )
        )
        if cancel:
            await asyncio.wait_for(started.wait(), timeout=10)
            task.cancel()
        return await task

    for cancel in (False, True):
        exception = asyncio.CancelledError if cancel else RuntimeError
        with pytest.raises(exception) as plain:
            asyncio.run(failing(cancel, None))
        path = tmp_path / ("cancel.json" if cancel else "failure.json")
        with pytest.raises(exception) as captured_error:
            asyncio.run(failing(cancel, path))
        assert type(plain.value) is type(captured_error.value)
        captured = json.loads(path.read_text())
        assert captured["outcome"] == "failed"
        assert captured["failure_type"] == type(captured_error.value).__name__
        assert captured["result_semantic_sha256"] is None
        assert captured["stages"]["discovered"]["places"]


def test_tools_cli_exposes_default_off_capture_path(tmp_path, capsys):
    from backend.app.versions.v1.runner import main

    request = tmp_path / "request.json"
    request.write_text(make_request().model_dump_json())
    capture = tmp_path / "opportunities.json"
    code = main(
        [
            "--input-json",
            str(request),
            "--reference-date",
            "2026-09-11",
            "--opportunity-capture",
            str(capture),
        ],
        llm_client=FakeStructuredLLMClient([make_itinerary()]),
        places_provider=Places(),
        weather_provider=FakeWeatherProvider(),
        routes_provider=FakeRoutesProvider(),
    )
    assert code == 0
    assert json.loads(capsys.readouterr().out)["system_version"] == "v1"
    assert json.loads(capture.read_text())["version"] == "v1"
