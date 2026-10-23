"""Async query adapter uses bounded, read-only DB and mocked embedding HTTP."""

import asyncio
import json

import httpx
import numpy as np
import pytest
from openai import AsyncOpenAI, InternalServerError

from backend.app.tripworld.database.policy import POLICY_VERSION
from backend.app.tripworld.database.vectors import SPACE
from backend.app.tripworld.retrieval.geography import GeographicScope
from backend.app.tripworld.retrieval.runtime import RuntimeRetrieval
from backend.app.versions.v2.config import RAGConfig


class Cursor:
    def __init__(self, rows):
        self.rows = rows

    async def fetchone(self):
        return self.rows[0] if self.rows else None

    async def fetchall(self):
        return self.rows


class Connection:
    def __init__(self, manifest):
        self.manifest, self.closed, self.calls = manifest, False, []

    async def execute(self, sql, params=None):
        self.calls.append((sql, params))
        if "SELECT configuration" in sql:
            return Cursor([{"configuration": SPACE}])
        if "SELECT manifest" in sql:
            return Cursor([{"manifest": self.manifest, "row_count": 1}])
        if "SELECT artifact_hash,policy_version" in sql:
            return Cursor([{"artifact_hash": "artifact", "policy_version": POLICY_VERSION}])
        return Cursor([])

    async def close(self):
        self.closed = True


def configured(tmp_path, monkeypatch, handler):
    manifest = {"output_sha256": "artifact", "entity_count": 1}
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "reports").mkdir()
    (tmp_path / "artifacts/retrieval_entities.parquet.manifest.json").write_text(
        json.dumps(manifest)
    )
    (tmp_path / "reports/phase5_embedding_run.json").write_text('{"status":"complete"}')
    conn = Connection(manifest)
    captured = {}

    async def connect(**kwargs):
        captured.update(kwargs)
        return conn

    async def register(_):
        pass

    def client(**kwargs):
        return AsyncOpenAI(
            **kwargs, http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
        )

    monkeypatch.setenv("DAYLOOM_DB_PASSWORD", "fake-unit-password")
    monkeypatch.setenv("OPENAI_API_KEY", "fake-unit-key")
    monkeypatch.setattr("backend.app.tripworld.retrieval.runtime.register_vector_async", register)
    runtime = RuntimeRetrieval(
        RAGConfig(), root=tmp_path, connect=connect, embedding_client_factory=client
    )
    return runtime, conn, captured


def test_adapter_prepares_readonly_uses_existing_sql_and_one_batch(tmp_path, monkeypatch):
    requests = []

    def handler(request):
        requests.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "object": "list",
                "model": SPACE["model"],
                "data": [
                    {"object": "embedding", "index": i, "embedding": [1.0] + [0.0] * 1535}
                    for i in range(2)
                ],
                "usage": {"prompt_tokens": 5, "total_tokens": 5},
            },
        )

    runtime, conn, captured = configured(tmp_path, monkeypatch, handler)

    async def scenario():
        async with runtime:
            await runtime.prepare()
            vectors = await runtime.embed(["museums", "parks"])
            assert vectors.shape == (2, 1536)
            assert np.linalg.norm(vectors[0]) == 1
            assert (
                await runtime.search(
                    vectors[0], GeographicScope(latitude=-37.81, longitude=144.96, radius_km=15), 10
                )
                == []
            )

    asyncio.run(scenario())
    assert conn.closed and "default_transaction_read_only=on" in captured["options"]
    assert len(requests) == runtime.embedding_sends == 1
    assert requests[0]["input"] == ["museums", "parks"]
    assert runtime.usage["total_tokens"] == 5
    sql, params = conn.calls[-1]
    assert "MATERIALIZED" in sql and params["runtime_artifact"] == "artifact"
    assert params["k"] == 10 and params["runtime_policy"] == POLICY_VERSION
    assert all(
        not sql.startswith(("INSERT", "CREATE", "UPDATE", "DELETE")) for sql, _ in conn.calls
    )


def test_embedding_http_failure_has_no_sdk_retry_and_closes(tmp_path, monkeypatch):
    sends = []

    def handler(request):
        sends.append(request)
        return httpx.Response(500, json={"error": {"message": "synthetic failure"}})

    runtime, conn, _ = configured(tmp_path, monkeypatch, handler)

    async def scenario():
        async with runtime:
            await runtime.prepare()
            await runtime.embed(["museum"])

    with pytest.raises(InternalServerError):
        asyncio.run(scenario())
    assert len(sends) == runtime.embedding_sends == 1 and conn.closed


def test_compatibility_failure_precedes_embedding(tmp_path, monkeypatch):
    runtime, conn, _ = configured(tmp_path, monkeypatch, lambda _: pytest.fail("Unexpected HTTP"))
    conn.manifest = {"incompatible": True}

    async def scenario():
        async with runtime:
            await runtime.prepare()

    with pytest.raises(ValueError, match="manifest"):
        asyncio.run(scenario())
    assert runtime.embedding_sends == 0 and conn.closed


@pytest.mark.parametrize("historical", [False, True])
def test_runtime_timeout_reaches_real_adapter_session(tmp_path, monkeypatch, historical):
    from backend.app.runtime.config_loader import load_runtime_config
    from backend.app.versions.v2.config import RAGConfig

    runtime, conn, captured = configured(tmp_path, monkeypatch, lambda _: pytest.fail("No HTTP"))
    runtime.config = (
        RAGConfig(sql_timeout=60, deadline_seconds=180)
        if historical else load_runtime_config().tripworld_discovery
    )

    async def run():
        async with runtime:
            await runtime.prepare()

    asyncio.run(run())
    assert "statement_timeout=60000" in captured["options"]
    assert runtime.config.sql_timeout == 60
    assert runtime.config.deadline_seconds == (180 if historical else 360)
    assert conn.closed


@pytest.mark.parametrize("capture", [False, True])
def test_httpx2_attempts_usage_and_opt_in_vectors(tmp_path, monkeypatch, capture):
    import hashlib

    import httpx2
    from openai import DefaultAsyncHttpxClient

    requests = []

    def handler(request):
        requests.append(json.loads(request.content))
        return httpx2.Response(
            200,
            headers={"x-request-id": "mock-id"},
            json={
                "object": "list",
                "model": SPACE["model"],
                "data": [{"object": "embedding", "index": 0, "embedding": [1.0] + [0.0] * 1535}],
                "usage": {"prompt_tokens": 2, "total_tokens": 2},
            },
        )

    runtime, _, _ = configured(tmp_path, monkeypatch, lambda _: None)
    runtime.embedding_client_factory = lambda **kw: AsyncOpenAI(
        **kw, http_client=DefaultAsyncHttpxClient(transport=httpx2.MockTransport(handler))
    )
    capture_path = tmp_path / "captured"
    runtime.capture_directory = capture_path if capture else None

    async def run():
        async with runtime:
            await runtime.prepare()
            result = await runtime.embed(["private query"])
            assert result[0, 0] == 1 and result.shape == (1, 1536)

    asyncio.run(run())
    assert runtime.usage == {"prompt_tokens": 2, "total_tokens": 2}
    assert runtime.embedding_sends == len(runtime.http_attempts) == 1
    assert runtime.http_attempts[0]["request_id"] == "mock-id"
    assert requests == [
        {"input": ["private query"], "model": SPACE["model"], "encoding_format": "float"}
    ]
    assert runtime.client.is_closed()
    assert "private query" not in json.dumps(runtime.diagnostics)
    if capture:
        with np.load(next(capture_path.glob("*.npz")), allow_pickle=False) as archive:
            metadata = json.loads(str(archive["metadata"]))
            assert (
                metadata["vectors_sha256"]
                == hashlib.sha256(archive["vectors"].tobytes()).hexdigest()
            )
            assert metadata["text_sha256"] == [hashlib.sha256(b"private query").hexdigest()]
            assert metadata["space"] == SPACE
    else:
        assert not capture_path.exists()


def test_invalid_embedding_keeps_usage_and_http_metadata(tmp_path, monkeypatch):
    def handler(_):
        return httpx.Response(
            200,
            headers={"x-request-id": "invalid"},
            json={
                "object": "list",
                "model": "wrong-model",
                "data": [],
                "usage": {"prompt_tokens": 3, "total_tokens": 3},
            },
        )

    runtime, _, _ = configured(tmp_path, monkeypatch, handler)

    async def run():
        async with runtime:
            await runtime.embed(["museum"])

    with pytest.raises(ValueError, match="model mismatch"):
        asyncio.run(run())
    assert runtime.usage["total_tokens"] == 3
    assert runtime.http_attempts[0]["request_id"] == "invalid"


@pytest.mark.parametrize("cancel", [False, True])
def test_sql_timeout_and_caller_cancellation_are_distinct(tmp_path, monkeypatch, cancel):
    runtime, conn, _ = configured(tmp_path, monkeypatch, lambda _: pytest.fail("No HTTP"))
    runtime.config = runtime.config.model_copy(update={"sql_timeout": 0.02})

    async def run():
        async with runtime:
            await runtime.prepare()
            entered = asyncio.Event()

            async def slow(*_):
                entered.set()
                await asyncio.sleep(60)

            conn.execute = slow
            task = asyncio.create_task(
                runtime.search(
                    np.array([1.0] + [0.0] * 1535, dtype=np.float32),
                    GeographicScope(latitude=0, longitude=0, radius_km=15),
                    10,
                )
            )
            await entered.wait()
            if cancel:
                task.cancel()
            with pytest.raises(asyncio.CancelledError if cancel else TimeoutError):
                await task

    asyncio.run(run())
    sql = next(row for row in runtime.diagnostics if row["stage"] == "sql")
    assert sql["sql_timeout_expired"] is (not cancel)
    assert not any(row["stage"] == "fetch_decode" for row in runtime.diagnostics)
    assert conn.closed


@pytest.mark.parametrize("failure", ["rate_limit", "invalid_json"])
def test_httpx2_failure_metadata_without_retry(tmp_path, monkeypatch, failure):
    import httpx2
    from openai import DefaultAsyncHttpxClient, RateLimitError

    def handler(_):
        if failure == "rate_limit":
            return httpx2.Response(
                429,
                headers={"x-request-id": "failed-response"},
                json={"error": {"message": "offline synthetic limit"}},
            )
        return httpx2.Response(
            200,
            headers={"x-request-id": "failed-response", "content-type": "application/json"},
            content=b"invalid json",
        )

    runtime, _, _ = configured(tmp_path, monkeypatch, lambda _: None)
    runtime.embedding_client_factory = lambda **kw: AsyncOpenAI(
        **kw, http_client=DefaultAsyncHttpxClient(transport=httpx2.MockTransport(handler))
    )

    async def run():
        async with runtime:
            await runtime.embed(["museum"])

    with pytest.raises(RateLimitError if failure == "rate_limit" else json.JSONDecodeError):
        asyncio.run(run())
    assert runtime.embedding_sends == len(runtime.http_attempts) == 1
    assert runtime.http_attempts[0]["request_id"] == "failed-response"
    assert runtime.client.is_closed()


def test_failed_development_capture_preserves_success(tmp_path, monkeypatch):
    def handler(_):
        return httpx.Response(
            200,
            json={
                "object": "list",
                "model": SPACE["model"],
                "data": [{"object": "embedding", "index": 0, "embedding": [1.0] + [0.0] * 1535}],
                "usage": {"prompt_tokens": 1, "total_tokens": 1},
            },
        )

    runtime, _, _ = configured(tmp_path, monkeypatch, handler)
    runtime.capture_directory = tmp_path / "not-a-directory"
    runtime.capture_directory.write_text("occupied", encoding="utf-8")

    async def run():
        async with runtime:
            result = await runtime.embed(["museum"])
            assert result[0, 0] == 1

    asyncio.run(run())
    capture = next(row for row in runtime.diagnostics if row["stage"] == "development_capture")
    assert capture["status"] == "failed"


@pytest.mark.parametrize("cancel", [False, True])
def test_httpx2_embedding_timeout_and_cancel_close_owned_client(tmp_path, monkeypatch, cancel):
    import httpx2
    from openai import DefaultAsyncHttpxClient

    entered = asyncio.Event()

    async def handler(_):
        entered.set()
        await asyncio.sleep(60)

    runtime, _, _ = configured(tmp_path, monkeypatch, lambda _: None)
    runtime.config = runtime.config.model_copy(update={"embedding_timeout": 5})
    runtime.embedding_client_factory = lambda **kw: AsyncOpenAI(
        **kw, http_client=DefaultAsyncHttpxClient(transport=httpx2.MockTransport(handler))
    )

    async def run():
        async with runtime:
            task = asyncio.create_task(runtime.embed(["museum"]))
            try:
                if cancel:
                    await asyncio.wait_for(entered.wait(), timeout=3)
                    task.cancel()
                with pytest.raises(asyncio.CancelledError if cancel else TimeoutError):
                    await task
            finally:
                if not task.done():
                    task.cancel()
                await asyncio.gather(task, return_exceptions=True)

    asyncio.run(asyncio.wait_for(run(), timeout=10))
    assert runtime.embedding_sends == len(runtime.http_attempts) == 1
    assert runtime.http_attempts[0]["status_code"] is None
    assert runtime.client.is_closed()
    assert runtime.diagnostics[0]["status"] == ("cancelled" if cancel else "failed")


def test_connection_tolerance_uses_effective_config_without_changing_sql(tmp_path, monkeypatch):
    from contextlib import asynccontextmanager
    from pathlib import Path

    from backend.app.runtime.config_loader import load_runtime_config_file

    runtime, conn, captured = configured(tmp_path, monkeypatch, lambda _: None)
    runtime.config = load_runtime_config_file(Path("config/runtime.yaml")).tripworld_discovery
    observed = []

    @asynccontextmanager
    async def timeout(seconds):
        observed.append(seconds)
        yield

    monkeypatch.setattr("backend.app.tripworld.retrieval.runtime.asyncio.timeout", timeout)

    async def scenario():
        async with runtime:
            await runtime.prepare()

    asyncio.run(scenario())
    assert observed == [10, 60]
    assert "statement_timeout=60000" in captured["options"]
    assert runtime.config.deadline_seconds == 360
    assert conn.closed
