"""Streaming contracts, preflight rejection and producer cancellation."""

import asyncio
import json
from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel

from backend.app.api.dependencies import get_developer_planning_service, get_planning_service
from backend.app.api.streaming import planning_events, planning_stream
from backend.app.main import app
from backend.app.observability.progress import ProgressObserver, observed
from backend.app.schemas.planning import PlanningResult
from backend.app.services.planning import DeveloperPlanningService, PlanningService
from backend.tests.fakes import FixedDateProvider
from backend.tests.request_fixtures import make_request
from backend.tests.versions.v0.fakes import make_itinerary


class Runtime:
    def __init__(self):
        self.calls = []

    @observed("generation")
    async def run(self, version, request, *, reference_date, tracer=None):
        self.calls.append(version)
        return PlanningResult(
            system_version=version,
            requirements=request.trip_requirements(),
            itinerary=make_itinerary(),
        )


def post_stream(developer=False, invalid=False):
    runtime = Runtime()
    provider = FixedDateProvider(date(2026, 9, 11))
    service = (
        DeveloperPlanningService(runtime, provider)
        if developer
        else PlanningService(runtime, provider)
    )
    dependency = get_developer_planning_service if developer else get_planning_service
    request = make_request().model_dump(mode="json")
    if invalid:
        request.update(start_date="2027-01-01", end_date="2027-01-03")
    body = {"version": "v3", "request": request} if developer else request

    async def send():
        app.dependency_overrides[dependency] = lambda: service
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                return await c.post(
                    "/api/dev/planning/stream" if developer else "/api/planning/stream", json=body
                )
        finally:
            app.dependency_overrides.pop(dependency, None)

    return asyncio.run(send()), runtime


@pytest.mark.parametrize("developer", [True])
def test_stream_final_result_and_ordered_events(developer):
    response, runtime = post_stream(developer)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = [
        json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")
    ]
    assert [e["sequence"] for e in events] == list(range(1, len(events) + 1))
    assert events[0]["type"] == "started" and events[-1]["type"] == "result"
    assert len({e["run_id"] for e in events}) == 1
    assert runtime.calls == ["v3"]
    if developer:
        assert events[-1]["result"]["system_version"] == "v3"
    else:
        assert events[-1]["result"]["status"] == "completed"
        assert "system_version" not in response.text and '"version"' not in response.text


@pytest.mark.parametrize("developer", [True])
def test_invalid_stream_request_is_http_422_before_execution(developer):
    response, runtime = post_stream(developer, invalid=True)
    assert response.status_code == 422
    assert not runtime.calls
    assert response.headers["content-type"].startswith("application/json")


def test_error_after_stream_start_is_terminal_event_without_private_message():
    async def fail():
        raise RuntimeError("PRIVATE")

    async def consume():
        return [e async for e in planning_events(fail, ProgressObserver())]

    output = "".join(asyncio.run(consume()))
    assert "event: error" in output and "event: result" not in output
    assert "PRIVATE" not in output


def test_iterator_close_waits_for_producer_cleanup():
    async def scenario():
        started, closed = asyncio.Event(), asyncio.Event()

        async def run():
            try:
                started.set()
                await asyncio.Event().wait()
            finally:
                await asyncio.sleep(0)
                closed.set()

        stream = planning_events(run, ProgressObserver())
        await anext(stream)
        await started.wait()
        await stream.aclose()
        assert closed.is_set()

    asyncio.run(scenario())


def test_asgi_disconnect_cancels_producer_and_waits_for_cleanup():
    async def scenario():
        started, closed = asyncio.Event(), asyncio.Event()

        async def run():
            try:
                started.set()
                await asyncio.Event().wait()
            finally:
                await asyncio.sleep(0.01)
                closed.set()

        async def receive():
            await started.wait()
            return {"type": "http.disconnect"}

        async def send(message):
            pass

        response = planning_stream(run)
        await response({"type": "http", "asgi": {"spec_version": "2.0"}}, receive, send)
        assert closed.is_set()

    asyncio.run(asyncio.wait_for(scenario(), 2))


def test_idle_stream_sends_heartbeat_not_fake_progress():
    class Result(BaseModel):
        status: str = "completed"

    async def scenario():
        release = asyncio.Event()
        produced = asyncio.Event()

        async def run():
            await release.wait()
            produced.set()
            return Result()

        stream = planning_events(run, ProgressObserver(), heartbeat_seconds=0.01)
        await anext(stream)
        assert await anext(stream) == ": keep-alive\n\n"
        release.set()
        await produced.wait()
        assert "event: result" in await anext(stream)
        await stream.aclose()

    asyncio.run(scenario())


def test_send_failure_also_closes_generator_and_owned_producer():
    from starlette.requests import ClientDisconnect

    async def scenario():
        entered, closed = asyncio.Event(), asyncio.Event()

        async def run():
            try:
                entered.set()
                await asyncio.Event().wait()
            finally:
                await asyncio.sleep(0)
                closed.set()

        async def send(message):
            if message["type"] == "http.response.body":
                await entered.wait()
                raise OSError("Disconnected")

        async def receive():
            await asyncio.Event().wait()

        with pytest.raises(ClientDisconnect):
            await planning_stream(run)(
                {"type": "http", "asgi": {"spec_version": "2.4"}}, receive, send
            )
        assert closed.is_set()

    asyncio.run(asyncio.wait_for(scenario(), 2))
