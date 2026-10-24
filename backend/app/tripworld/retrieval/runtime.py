"""Cancellable query-only runtime; no corpus mutation, retry or checkpoint write."""

import asyncio
import json
import os
from pathlib import Path
from uuid import uuid4

import numpy as np
import psycopg
from openai import AsyncOpenAI
from pgvector.psycopg import register_vector_async
from psycopg.rows import dict_row

from backend.app.integrations.spending import install_spend_hooks
from backend.app.observability.usage import install_http_hooks, observe_sdk
from backend.app.runtime.database import DatabaseSettings
from backend.app.tripworld.database.policy import POLICY_VERSION
from backend.app.tripworld.database.search import search_query
from backend.app.tripworld.database.vectors import SPACE, SPACE_ID
from backend.app.tripworld.retrieval.diagnostics import (
    capture_vectors,
    current_vector_capture_directory,
    measure,
)
from backend.app.tripworld.retrieval.embedding import validate_vectors

ROOT = Path(__file__).resolve().parents[4] / "data/tripworld"


class RuntimeRetrieval:
    def __init__(
        self,
        config,
        *,
        root=ROOT,
        connect=None,
        embedding_client_factory=None,
        capture_directory=None,
    ):
        self.config, self.root = config, root
        self.connect = connect or psycopg.AsyncConnection.connect
        self.embedding_client_factory = embedding_client_factory or AsyncOpenAI
        self.conn = self.client = None
        self.usage = {}
        self.embedding_sends = 0
        self.capture_directory = (
            capture_directory
            if capture_directory is not None
            else current_vector_capture_directory.get()
        )
        self.diagnostics = []
        self.http_attempts = []
        self._http_hooks = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        try:
            if self.client is not None:
                if self._http_hooks is not None:
                    http, request_hook, response_hook = self._http_hooks
                    http.event_hooks["request"].remove(request_hook)
                    http.event_hooks["response"].remove(response_hook)
                await self.client.close()
        finally:
            if self.conn is not None:
                await self.conn.close()

    async def prepare(self):
        with measure(self.diagnostics, "prepare"):
            return await self._prepare()

    async def _prepare(self):
        manifest = json.loads(
            (self.root / "artifacts/retrieval_entities.parquet.manifest.json").read_text("utf-8")
        )
        build = json.loads((self.root / "reports/phase5_embedding_run.json").read_text("utf-8"))
        if build.get("status") != "complete":
            raise ValueError("A completed corpus embedding build is required")
        self.artifact_hash = manifest["output_sha256"]
        parameters = DatabaseSettings().connection_parameters()
        parameters.update(
            autocommit=True, row_factory=dict_row,
            options=(parameters.get("options", "") + " -c default_transaction_read_only=on "
                     f"-c statement_timeout={max(1, int(self.config.sql_timeout * 1000))}"),
        )
        with measure(self.diagnostics, "connection"):
            async with asyncio.timeout(self.config.connect_timeout):
                self.conn = await self.connect(**parameters)
        with measure(self.diagnostics, "compatibility"):
            async with asyncio.timeout(self.config.sql_timeout):
                await register_vector_async(self.conn)
                cursor = await self.conn.execute(
                    "SELECT configuration FROM tripworld.embedding_spaces WHERE space_id=%s",
                    (SPACE_ID,),
                )
                row = await cursor.fetchone()
                if row is None or row["configuration"] != SPACE:
                    raise ValueError("Embedding space compatibility mismatch")
                cursor = await self.conn.execute(
                    "SELECT manifest,row_count FROM tripworld.corpus_builds WHERE artifact_hash=%s",
                    (self.artifact_hash,),
                )
                row = await cursor.fetchone()
                if (
                    row is None
                    or row["manifest"] != manifest
                    or row["row_count"] != manifest["entity_count"]
                ):
                    raise ValueError("Corpus manifest compatibility mismatch")
                cursor = await self.conn.execute(
                    "SELECT artifact_hash,policy_version FROM tripworld.entities LIMIT 1"
                )
                row = await cursor.fetchone()
                if not row or row != {
                    "artifact_hash": self.artifact_hash,
                    "policy_version": POLICY_VERSION,
                }:
                    raise ValueError("Corpus policy compatibility mismatch")

    async def embed(self, texts):
        with measure(self.diagnostics, "embedding"):
            return await self._embed(texts)

    async def _embed(self, texts):
        if not os.environ.get("OPENAI_API_KEY"):
            raise ValueError("Embedding credentials unavailable")
        if self.client is None:
            self.client = self.embedding_client_factory(
                api_key=os.environ["OPENAI_API_KEY"],
                base_url="https://api.openai.com/v1",
                timeout=self.config.embedding_timeout,
                max_retries=0,
            )
            # Attach to this owned SDK client's actual transport (httpx2 in the installed stack).
            http = self.client._client
            install_spend_hooks(http)
            install_http_hooks(http, "openai", "embedding")
            active = {}

            async def request_hook(request):
                row = {"attempt_id": uuid4().hex, "status_code": None, "request_id": None}
                self.http_attempts.append(row)
                active[id(request)] = row

            async def response_hook(response):
                row = active.pop(id(response.request), None)
                if row is not None:
                    row.update(
                        status_code=response.status_code,
                        request_id=response.headers.get("x-request-id"),
                    )

            http.event_hooks["request"].append(request_hook)
            http.event_hooks["response"].append(response_hook)
            self._http_hooks = (http, request_hook, response_hook)
        async with asyncio.timeout(self.config.embedding_timeout):
            self.embedding_sends += 1
            response = await observe_sdk(
                self.client.embeddings.create,
                usage_operation="embedding",
                usage_provider="openai",
                model=SPACE["model"],
                input=texts,
                encoding_format="float",
            )
        self.usage = response.usage.model_dump() if response.usage is not None else None
        if response.model != SPACE["model"]:
            raise ValueError("Query embedding model mismatch")
        items = sorted(response.data, key=lambda x: x.index)
        if [r.index for r in items] != list(range(len(texts))):
            raise ValueError("Query embedding index mismatch")
        vectors = np.asarray([r.embedding for r in items], dtype=np.float32)
        if vectors.shape != (len(texts), 1536) or not np.isfinite(vectors).all():
            raise ValueError("Invalid query vectors")
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        if (norms <= 0).any():
            raise ValueError("Empty query vector")
        vectors /= norms
        validate_vectors(vectors, len(texts), 1536)
        if self.capture_directory is not None:
            try:
                filename = capture_vectors(
                    self.capture_directory, texts, vectors, getattr(self, "artifact_hash", None)
                )
                self.diagnostics.append(
                    {"stage": "development_capture", "status": "completed", "file": filename}
                )
            except Exception as exc:
                self.diagnostics.append(
                    {
                        "stage": "development_capture",
                        "status": "failed",
                        "exception_type": type(exc).__name__,
                    }
                )
        return vectors

    async def search(self, vector, scope, top_k):
        sql, params = search_query(scope, vector, top_k)
        sql = sql.replace(
            "WHERE discovery_allowed AND",
            "WHERE discovery_allowed AND policy_version=%(runtime_policy)s "
            "AND artifact_hash=%(runtime_artifact)s AND",
        )
        params.update(runtime_policy=POLICY_VERSION, runtime_artifact=self.artifact_hash)
        timer = asyncio.timeout(self.config.sql_timeout)
        try:
            with measure(self.diagnostics, "sql") as record:
                async with timer:
                    with measure(self.diagnostics, "execute"):
                        cursor = await self.conn.execute(sql, params)
                    with measure(self.diagnostics, "fetch_decode"):
                        rows = await cursor.fetchall()
        finally:
            record["sql_timeout_expired"] = timer.expired()
        if any(r["retrieval_entity_artifact_hash"] != self.artifact_hash for r in rows):
            raise ValueError("Returned corpus artifact mismatch")
        return [{"rank": i, **r} for i, r in enumerate(rows, 1)]
