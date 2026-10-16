"""Actual production nodes/SDK over MockTransport; matrix owns one shared HTTP client."""

import asyncio
import json

import httpx2 as httpx
import pytest

from backend.tests.request_fixtures import make_request
from backend.tests.versions.v1.fakes import (
    FakePlacesProvider,
    FakeRoutesProvider,
    FakeWeatherProvider,
)
from tools.validation.requirement_acceptance import freeze_matrix, run_matrix
from tools.validation.runtime_acceptance import AcceptanceSession


def response(payload, number):
    return {
        "id": f"resp_{number}",
        "created_at": 0,
        "object": "response",
        "status": "completed",
        "error": None,
        "incomplete_details": None,
        "model": "fixture-model",
        "output": [
            {
                "id": f"msg_{number}",
                "type": "message",
                "role": "assistant",
                "status": "completed",
                "content": [{"type": "output_text", "text": payload, "annotations": []}],
            }
        ],
        "parallel_tool_calls": True,
        "tool_choice": "auto",
        "tools": [],
        "temperature": 1,
        "top_p": 1,
        "usage": {
            "input_tokens": 30,
            "output_tokens": 10,
            "total_tokens": 40,
            "input_tokens_details": {"cached_tokens": 0},
            "output_tokens_details": {"reasoning_tokens": 0},
        },
    }


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    import socket

    def forbidden(*args, **kwargs):
        raise AssertionError("Real network access forbidden in acceptance tests")

    original_pair, original_connect = socket.socketpair, socket.socket.connect
    creating_wakeup_pair = False

    def pair(*args, **kwargs):
        nonlocal creating_wakeup_pair
        creating_wakeup_pair = True
        try:
            return original_pair(*args, **kwargs)
        finally:
            creating_wakeup_pair = False

    def connect(sock, address):
        if creating_wakeup_pair:
            return original_connect(sock, address)
        return forbidden()

    monkeypatch.setattr(socket, "socketpair", pair)
    monkeypatch.setattr(socket.socket, "connect", connect)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setenv("LANGSMITH_TRACING", "false")


def settings():
    from backend.app.versions.v0.config import V0Settings

    return V0Settings(
        _env_file=None,
        azure_openai_endpoint="https://fixture.invalid/openai/v1",
        azure_openai_api_key="fixture-secret",
        azure_openai_deployment="fixture-model",
    )


def itinerary(engine="v0"):
    value = {
        "destination": "Sydney",
        "start_date": "2026-09-12",
        "end_date": "2026-09-13",
        "output_version": "itinerary_3",
        "reference_recommendations": [],
        "days": [
            {"date": "2026-09-12", "activities": []},
            {"date": "2026-09-13", "activities": []},
        ],
    }

    if engine == "v1":
        value.pop("reference_recommendations")
    return value


def scenarios():
    return {
        "reference_date": "2026-09-12",
        "cases": [
            {
                "case_id": name,
                "engine": engine,
                "request": make_request(text).model_dump(mode="json"),
                "expected_outcome": expected,
                "checks": ["DO_NOT_SEND_CHECKS"],
            }
            for name, engine, text, expected in [
                ("V0_E", "v0", "", "completed"),
                ("V1_E", "v1", "", "completed"),
                ("V0_P", "v0", "Prefer local places", "completed"),
                ("V1_P", "v1", "Prefer local places", "completed"),
                ("HARD", "shared", "Absolutely no stairs.", "clarification"),
            ]
        ],
    }


def payloads():
    from backend.tests.versions.v1.test_interpreted_requirements import draft_for

    pref = draft_for().model_dump(mode="json")
    hard = draft_for("Absolutely no stairs.").model_dump(mode="json")
    hard["semantic_requirements"][0]["strength"] = "hard"
    return [itinerary(), itinerary("v1"), pref, itinerary(), pref, itinerary("v1"), hard]


class ModelTransport(httpx.MockTransport):
    def __init__(self, values=None, missing_usage=False):
        self.requests, self.close_calls = [], 0
        self.values = values or payloads()
        self.missing_usage = missing_usage
        self.ordinary_index = 0
        super().__init__(self.respond)

    def respond(self, request):
        self.requests.append(json.loads(request.content))
        assert "DO_NOT_SEND_CHECKS" not in request.content.decode()
        data = json.loads(request.content)
        if "FoundrySemanticAssessmentBatch" in request.content.decode():
            content = data["input"][-1]["content"]
            payload = json.loads(content if isinstance(content, str) else content[0]["text"])
            value = {
                "assessments": [
                    dict(
                        candidate_ref=p["candidate_ref"],
                        visit_object=p["name"],
                        role="attraction",
                        categories=["fixture"],
                        reason="Synthetic fixture evidence",
                        evidence_refs=[p["source_ref"]],
                        matches=[],
                        exception_requirement_ids=[],
                    )
                    for p in payload["places"]
                ]
            }
        else:
            value = self.values[self.ordinary_index]
            self.ordinary_index += 1
        from backend.tests.llm.azure_foundry.requirement_fixtures import current_response

        value = current_response(value, request)
        raw = response(value if isinstance(value, str) else json.dumps(value), len(self.requests))
        if self.missing_usage:
            raw.pop("usage")
        else:
            raw["usage"]["output_tokens_details"]["reasoning_tokens"] = 4
            raw["usage"]["input_tokens_details"]["cached_tokens"] = 5
        return httpx.Response(200, json=raw, headers={"x-request-id": f"req-{len(self.requests)}"})

    async def aclose(self):
        self.close_calls += 1
        await super().aclose()


def providers():
    return {
        "places_provider": FakePlacesProvider(),
        "weather_provider": FakeWeatherProvider(),
        "routes_provider": FakeRoutesProvider(),
    }


async def matrix(path, *, capture=True, transport=None):
    transport = transport or ModelTransport()
    supplied = providers()
    async with AcceptanceSession(
        settings=settings(), transport=transport, directory=path, capture=capture
    ) as session:
        manifest = freeze_matrix(scenarios(), path, session.client)
        results = await run_matrix(manifest, path, session=session, providers=supplied)
        assert not session.http.is_closed
    assert session.http.is_closed and session.close_count == transport.close_calls == 1
    assert session.http.event_hooks["request"] == []
    return results, session, transport, supplied


@pytest.mark.parametrize("repeat", range(3))
def test_real_five_case_matrix_and_two_successive_sessions(tmp_path, repeat):
    async def exercise():
        sessions = []
        for i in range(2):
            results, session, transport, supplied = await matrix(tmp_path / str(i))
            assert [r["outcome"] for r in results] == ["completed"] * 4 + ["clarification"]
            assert results[-1]["code"] == "unsupported_hard_requirements"
            assert [r["client_invocations"] for r in results] == [1, 2, 2, 3, 1]
            assert [r["value"]["system_version"] for r in results[:4]] == ["v0", "v1", "v0", "v1"]
            assert len(session.calls) == len(transport.requests) == 9
            assert all(c["http_sends"] == len(c["responses"]) == 1 for c in session.calls.values())
            assert (
                sum(c["responses"][0]["usage"]["total_tokens"] for c in session.calls.values())
                == 360
            )
            assert sum(e["layer"] == "langchain_response" for e in session.events) == 9
            assert not session.broken and not session.capture_errors
            assert supplied["places_provider"].details_requests
            assert not supplied["places_provider"].reviews_requests
            sessions.append(session)
        assert sessions[0].http is not sessions[1].http

    asyncio.run(exercise())


def test_json_observer_preserves_installed_sdk_and_client_ownership(tmp_path):
    import httpx as legacy_httpx

    from backend.app.integrations.http import HttpxJSONTransport

    async def exercise():
        original_class = legacy_httpx.AsyncClient
        google_requests = []

        def respond(request):
            google_requests.append(request)
            return legacy_httpx.Response(200, json={"places": []})

        model = ModelTransport()
        async with AcceptanceSession(
            settings=settings(), transport=model, directory=tmp_path
        ) as session:
            manifest = freeze_matrix(scenarios(), tmp_path, session.client)
            with session.observe_json_transport(transport=legacy_httpx.MockTransport(respond)):
                assert legacy_httpx.AsyncClient is original_class
                result = await HttpxJSONTransport().request_json(
                    "POST",
                    "https://places.googleapis.com/v1/places:searchText",
                    headers={"X-Goog-Api-Key": "fixture-secret", "X-Goog-FieldMask": "places.id"},
                    json_body={"textQuery": "fixture"},
                )
                assert result == {"places": []}
                rows = await run_matrix(manifest, tmp_path, session=session, providers=providers())
                assert [r["outcome"] for r in rows] == ["completed"] * 4 + ["clarification"]
                assert all(c["http_sends"] == 1 for c in session.calls.values())
                assert len(model.requests) == 9
            assert legacy_httpx.AsyncClient is original_class
            assert not session.http.is_closed
            sends = [e for e in session.events if e["layer"] == "external_http_send"]
            assert len(sends) == len(google_requests) == 1
            assert sends[0]["payload"]["field_mask"] == "places.id"
            assert "fixture-secret" not in json.dumps(sends)
            assert (
                sum(c["responses"][0]["usage"]["total_tokens"] for c in session.calls.values())
                == 360
            )
            assert not session.capture_errors
        assert model.close_calls == session.close_count == 1

    asyncio.run(exercise())


def test_wrapped_type_error_stops_remaining_acceptance_cases(tmp_path, monkeypatch):
    async def exercise():
        model = ModelTransport()
        async with AcceptanceSession(settings=settings(), transport=model) as session:
            source = scenarios()
            manifest = freeze_matrix(source, tmp_path, session.client)

            async def fail(**kwargs):
                try:
                    raise TypeError("Invalid client type")
                except TypeError as exc:
                    raise RuntimeError("Wrapped dispatch failure") from exc

            monkeypatch.setattr(session.client, "generate_structured", fail)
            rows = await run_matrix(manifest, tmp_path, session=session, providers=providers())
            assert rows[0]["outcome"] == "shared_dependency_failure"
            assert all(r["outcome"] == "unexecuted" for r in rows[1:])
            assert not model.requests

    asyncio.run(exercise())


def test_capture_non_interference(tmp_path):
    async def exercise():
        enabled, _, a, pa = await matrix(tmp_path / "on")
        disabled, _, b, pb = await matrix(tmp_path / "off", capture=False)
        assert a.requests == b.requests

        def stable(value):
            if isinstance(value, dict):
                return {
                    k: stable(v)
                    for k, v in value.items()
                    if k not in ("elapsed_seconds", "cpu_seconds", "run_id", "call_id")
                }
            if isinstance(value, list):
                return [stable(v) for v in value]
            return value

        assert stable([r.get("value") for r in enabled]) == stable(
            [r.get("value") for r in disabled]
        )
        assert [r["outcome"] for r in enabled] == [r["outcome"] for r in disabled]
        assert pa["places_provider"].search_requests == pb["places_provider"].search_requests
        assert pa["places_provider"].details_requests == pb["places_provider"].details_requests
        assert pa["routes_provider"].requests == pb["routes_provider"].requests

    asyncio.run(exercise())


def test_closed_client_stops_before_any_v1_acquisition(tmp_path):
    async def exercise():
        transport = ModelTransport()
        async with AcceptanceSession(settings=settings(), transport=transport) as session:
            source = scenarios()
            source["cases"] = source["cases"][1:]
            manifest = freeze_matrix(source, tmp_path, session.client)
            await session.http.aclose()
            supplied = providers()
            rows = await run_matrix(manifest, tmp_path, session=session, providers=supplied)
            assert rows[0]["outcome"] == "shared_dependency_failure"
            assert all(r["outcome"] == "unexecuted" for r in rows[1:])
            assert not supplied["places_provider"].search_requests and not transport.requests
        assert transport.close_calls == 1

    asyncio.run(exercise())


@pytest.mark.parametrize("missing", [False, True])
def test_parse_failure_retains_sdk_usage_and_next_case_can_continue(tmp_path, missing):
    async def exercise():
        transport = ModelTransport(["{", itinerary("v1")], missing_usage=missing)
        async with AcceptanceSession(
            settings=settings(), transport=transport, directory=tmp_path
        ) as s:
            source = scenarios()
            source["cases"] = source["cases"][:2]
            manifest = freeze_matrix(source, tmp_path, s.client)
            rows = await run_matrix(manifest, tmp_path, session=s, providers=providers())
            assert rows[0]["outcome"] == "content_or_business_failure"
            assert rows[1]["outcome"] == "completed"
            calls = list(s.calls.values())
            assert not calls[0]["mapped"] and calls[1]["mapped"]
            assert len(calls[0]["responses"]) == 1
            usage = calls[0]["responses"][0]["usage"]
            assert (usage is None) if missing else usage["total_tokens"] == 40
            assert (
                calls[0]["responses"][0]["raw_response"]["output"][0]["content"][0]["text"] == "{"
            )

    asyncio.run(exercise())


@pytest.mark.parametrize("write_failure", ["none", "exception"])
def test_capture_write_failure_preserves_result_and_stops_next_case(
    tmp_path, monkeypatch, write_failure
):
    async def exercise():
        transport = ModelTransport()
        async with AcceptanceSession(
            settings=settings(), transport=transport, directory=tmp_path
        ) as s:
            manifest = freeze_matrix(scenarios(), tmp_path, s.client)

            def fail_write(*args, **kwargs):
                if write_failure == "exception":
                    raise OSError("Fixture disk failure")
                return None

            monkeypatch.setattr(s.capture, "record", fail_write)
            rows = await run_matrix(manifest, tmp_path, session=s, providers=providers())
            assert rows[0]["outcome"] == "completed"
            assert all(r["outcome"] == "unexecuted" for r in rows[1:])
            assert len(transport.requests) == 1 and s.capture_errors

    asyncio.run(exercise())


@pytest.mark.parametrize("mode", ["exception", "cancel"])
def test_final_cleanup_on_exception_and_cancellation(mode):
    async def exercise():
        transport = ModelTransport()
        s = AcceptanceSession(settings=settings(), transport=transport)

        async def work():
            async with s:
                if mode == "exception":
                    raise ValueError("fixture")
                asyncio.current_task().cancel()
                await asyncio.sleep(0)

        with pytest.raises(ValueError if mode == "exception" else asyncio.CancelledError):
            await work()
        assert s.http.is_closed and s.sync_http.is_closed and transport.close_calls == 1

    asyncio.run(exercise())


def test_borrowed_client_is_not_closed_and_hooks_are_preserved():
    async def exercise():
        transport = ModelTransport()
        async with AcceptanceSession(settings=settings(), transport=transport) as owner:
            original = list(owner.http.event_hooks["request"])
            async with AcceptanceSession(client=owner.client) as borrower:
                borrower.begin_case("borrowed")
            assert not owner.http.is_closed
            assert owner.http.event_hooks["request"] == original
        assert transport.close_calls == 1

    asyncio.run(exercise())


def test_original_factory_cached_client_failure_reproduced():
    from uuid import uuid4

    from backend.app.versions.v0.runner import create_foundry_client

    async def exercise():
        config = settings().model_copy(
            update={"azure_openai_endpoint": f"https://{uuid4().hex}.invalid/v1"}
        )
        a, b = create_foundry_client(config), create_foundry_client(config)
        assert a._chat_model.root_async_client._client is b._chat_model.root_async_client._client
        await a._chat_model.root_async_client.close()
        assert b._chat_model.root_async_client.is_closed()
        from openai import APIConnectionError

        with pytest.raises(APIConnectionError):
            await b._chat_model.root_async_client.responses.create(model="fixture", input="unused")
        a._chat_model.root_client.close()

    asyncio.run(exercise())


@pytest.mark.parametrize("http_family", ["httpx", "httpx2"])
def test_provider_observer_uses_injected_family_and_borrows_transport(http_family):
    import importlib

    family = importlib.import_module(http_family)

    async def exercise():
        async with AcceptanceSession(settings=settings(), transport=ModelTransport()) as s:
            async with family.AsyncClient(
                transport=family.MockTransport(
                    lambda request: family.Response(200, json={"normal": True})
                )
            ) as http:
                with s.observe_provider_http(http, "fixture-provider"):
                    response_value = await http.get("https://fixture.invalid/data")
                    assert response_value.json() == {"normal": True}
                assert not http.is_closed
                assert not http.event_hooks["request"] and not http.event_hooks["response"]
        assert [e["layer"] for e in s.events] == ["provider_send", "provider_response"]
        assert s.events[0]["payload"]["attempt_id"] == s.events[1]["payload"]["attempt_id"]

    asyncio.run(exercise())


def test_requirement_only_workflow_uses_same_session(tmp_path):
    async def exercise():
        values = payloads()
        async with AcceptanceSession(
            settings=settings(), transport=ModelTransport([values[2], values[-1], values[2]])
        ) as s:
            source = scenarios()
            source["cases"] = [
                source["cases"][2],
                source["cases"][-1],
                {**source["cases"][2], "case_id": "after_hard"},
            ]
            for case in source["cases"]:
                case["engine"] = "shared"
            manifest = freeze_matrix(source, tmp_path, s.client)
            rows = await run_matrix(manifest, tmp_path, session=s)
            assert [r["outcome"] for r in rows] == ["completed", "clarification", "completed"]
            assert not s.broken and len(s.calls) == 3

    asyncio.run(exercise())


def test_valid_dto_then_domain_failure_preserves_usage(tmp_path):
    async def exercise():
        invalid = {**itinerary(), "destination": ""}
        async with AcceptanceSession(
            settings=settings(), transport=ModelTransport([invalid, itinerary("v1")])
        ) as s:
            source = scenarios()
            source["cases"] = source["cases"][:2]
            manifest = freeze_matrix(source, tmp_path, s.client)
            rows = await run_matrix(manifest, tmp_path, session=s, providers=providers())
            assert [r["outcome"] for r in rows] == ["content_or_business_failure", "completed"]
            first = next(iter(s.calls.values()))
            assert not first["mapped"] and first["responses"][0]["usage"]["total_tokens"] == 40
            assert sum(e["layer"] == "langchain_response" for e in s.events) == 3

    asyncio.run(exercise())


@pytest.mark.parametrize("status", [401, 503])
def test_wrapped_provider_failure_stops_without_retry(tmp_path, status):
    async def exercise():
        sends = []

        def handler(request):
            sends.append(1)
            return httpx.Response(status, json={"error": {"message": "fixture", "type": "fixture"}})

        async with AcceptanceSession(
            settings=settings(), transport=httpx.MockTransport(handler)
        ) as s:
            manifest = freeze_matrix(scenarios(), tmp_path, s.client)
            supplied = providers()
            rows = await run_matrix(manifest, tmp_path, session=s, providers=supplied)
            assert rows[0]["outcome"] == (
                "shared_dependency_failure" if status == 401 else "provider_failure"
            )
            assert all(r["outcome"] == "unexecuted" for r in rows[1:])
            assert len(sends) == 1 and not supplied["places_provider"].search_requests

    asyncio.run(exercise())


def test_cross_loop_borrow_is_rejected_without_network():
    from tools.validation.runtime_acceptance import SharedDependencyFailure

    s = AcceptanceSession(settings=settings(), transport=ModelTransport())
    first, second = asyncio.new_event_loop(), asyncio.new_event_loop()

    async def check():
        with pytest.raises(SharedDependencyFailure, match="event loop"):
            s.ready()

    try:
        first.run_until_complete(s.__aenter__())
        second.run_until_complete(check())
    finally:
        first.run_until_complete(s.__aexit__(None, None, None))
        first.close()
        second.close()
    assert s.http.is_closed


def test_duplicate_layers_do_not_duplicate_usage_but_distinct_attempts_remain():
    async def exercise():
        async with AcceptanceSession(settings=settings(), transport=ModelTransport()) as s:
            s.calls["fixture"] = {"http_sends": 1, "responses": []}
            token = s.call.set("fixture")
            try:
                payload = {"response_id": "r", "usage": {"total_tokens": 0}}
                s.record("sdk_response", dict(payload))
                s.record("sdk_response", dict(payload))
                s.record("langchain_response", dict(payload))
                assert len(s.calls["fixture"]["responses"]) == 1
                assert s.calls["fixture"]["responses"][0]["usage"]["total_tokens"] == 0
                s.calls["fixture"]["http_sends"] = 2
                s.record("sdk_response", dict(payload))
                assert len(s.calls["fixture"]["responses"]) == 2
            finally:
                s.call.reset(token)

    asyncio.run(exercise())


@pytest.mark.parametrize("state", ["incomplete", "refusal"])
def test_unsuccessful_model_content_preserves_response_state_and_usage(tmp_path, state):
    async def exercise():
        def handler(request):
            raw = response(json.dumps(itinerary()), 1)
            if state == "incomplete":
                raw["status"] = "incomplete"
                raw["incomplete_details"] = {"reason": "max_output_tokens"}
            else:
                raw["output"][0]["content"] = [{"type": "refusal", "refusal": "Fixture refusal"}]
            return httpx.Response(200, json=raw)

        async with AcceptanceSession(
            settings=settings(), transport=httpx.MockTransport(handler)
        ) as s:
            source = scenarios()
            source["cases"] = source["cases"][:1]
            manifest = freeze_matrix(source, tmp_path, s.client)
            await run_matrix(manifest, tmp_path, session=s)
            call = next(iter(s.calls.values()))
            assert len(call["http_responses"]) == len(call["responses"]) == 1
            assert call["responses"][0]["usage"]["total_tokens"] == 40
            raw = call["responses"][0]["raw_response"]
            assert raw["status"] == ("incomplete" if state == "incomplete" else "completed")
            if state == "refusal":
                assert raw["output"][0]["content"][0]["type"] == "refusal"

    asyncio.run(exercise())


def test_spent_matrix_and_unique_artifacts(tmp_path):
    async def exercise():
        async with AcceptanceSession(
            settings=settings(), transport=ModelTransport(), directory=tmp_path
        ) as s:
            source = scenarios()
            source["cases"] = source["cases"][:2]
            manifest = freeze_matrix(source, tmp_path, s.client)
            await run_matrix(manifest, tmp_path, session=s, providers=providers())
            before = {p: p.read_bytes() for p in (tmp_path / s.session_id).glob("*.json")}
            with pytest.raises(FileExistsError):
                await run_matrix(manifest, tmp_path, session=s, providers=providers())
            assert all(p.read_bytes() == raw for p, raw in before.items())
            assert not s.http.is_closed and len(s.calls) == 3
            records = [json.loads(raw) for raw in before.values()]
            received = [r for r in records if r["layer"] == "sdk_response"]
            assert len(received) == len({r["call_id"] for r in received}) == 3
            assert {r["case_id"] for r in received} == {"V0_E", "V1_E"}

    asyncio.run(exercise())
