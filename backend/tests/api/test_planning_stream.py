"""Streaming contracts, preflight rejection and producer cancellation."""

import asyncio
import json
from datetime import date

import pytest
from pydantic import BaseModel

from backend.app.api.streaming import planning_events, planning_stream
from backend.app.observability.progress import ProgressObserver, observed
from backend.app.schemas.planning import PlanningResult
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


def test_stream_final_result_and_ordered_events():
    runtime = Runtime()

    async def consume():
        observer = ProgressObserver(developer=True, version="v3")
        return [event async for event in planning_events(
            lambda: runtime.run("v3", make_request(), reference_date=date(2026, 9, 11)),
            observer,
        )]

    events = [
        json.loads(line[6:])
        for chunk in asyncio.run(consume()) for line in chunk.splitlines()
        if line.startswith("data: ")
    ]
    assert [event["sequence"] for event in events] == list(range(1, len(events) + 1))
    assert events[0]["type"] == "started" and events[-1]["type"] == "result"
    assert len({event["run_id"] for event in events}) == 1
    assert runtime.calls == ["v3"]
    assert events[-1]["result"]["system_version"] == "v3"


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
