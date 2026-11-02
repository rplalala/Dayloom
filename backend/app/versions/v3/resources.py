"""One lazy request owner, with borrowed phase views and persistent failure state."""

import asyncio
from copy import deepcopy
from hashlib import sha256
from time import monotonic


class DeadlinePort:
    """Borrow a client with pre-send request guards; keep its provider defaults intact."""

    def __init__(self, client, deadline):
        self.client, self.deadline = client, deadline
        for name in (
            "search_text",
            "get_place_details",
            "get_place_reviews",
            "search_nearby",
            "get_daily_forecast",
            "compute_route_matrix",
            "generate_structured",
            "generate_primary_structured",
            "generate_repair_structured",
            "search",
            "retrieve",
            "fetch",
            "reason",
        ):
            if hasattr(client, name):
                setattr(self, name, self.guarded(getattr(client, name)))

    def __getattr__(self, name):
        return getattr(self.client, name)

    def guarded(self, operation):
        async def invoke(*args, **kwargs):
            if monotonic() >= self.deadline:
                raise TimeoutError("Whole-request deadline exhausted before external operation")
            async with asyncio.timeout_at(self.deadline):
                return await operation(*args, **kwargs)

        return invoke


class RequestRetrieval:
    """Own factory-created resources only; no phase deadlines live on the raw runtime.

    Failed query work remains blocked even if a later phase changes Top-K. The
    operation ledger records attempts, not invented HTTP sends; raw send diagnostics
    remain authoritative. Successful values use the common request cache.
    """

    def __init__(self, factory, deadline, *, runtime=None, enabled=True):
        self.factory, self.deadline = factory, deadline
        self.enabled = enabled
        self.runtime = runtime
        self.owned = runtime is None
        self.entered = False
        self.entry_failed = False
        self.prepared = False
        self.prepare_attempted = False
        self.closed = False
        self.failed_embeddings = set()
        self.failed_searches = set()
        self.operations = []
        self.phase = "primary_discovery"

    def check_time(self):
        if monotonic() >= self.deadline:
            raise TimeoutError("Whole-request deadline exhausted")

    async def __aenter__(self):
        if not self.enabled:
            raise RuntimeError("Retrieval disabled_by_deployment")
        self.check_time()
        if self.entry_failed or self.closed:
            raise RuntimeError("Request retrieval resource unavailable")
        try:
            if self.runtime is None:
                self.runtime = self.factory()
            if self.owned and not self.entered:
                self.entered = True
                await self.runtime.__aenter__()
        except BaseException:
            self.entry_failed = True
            raise
        return self

    async def __aexit__(self, *_):
        # Discovery borrows the runtime; only the request owner releases it.
        return False

    def __getattr__(self, name):
        if self.runtime is None:
            if name in {"diagnostics", "http_attempts"}:
                return []
            raise AttributeError(name)
        return getattr(self.runtime, name)

    async def prepare(self):
        self.check_time()
        if self.prepared:
            return
        if self.prepare_attempted:
            raise RuntimeError("Request retrieval initialization already failed")
        self.prepare_attempted = True
        await self.__aenter__()
        await self.runtime.prepare()
        self.prepared = True

    def allows_embedding(self, texts):
        return (
            self.enabled
            and not self.closed
            and not self.entry_failed
            and not (set(texts) & self.failed_embeddings)
            and (self.prepared or not self.prepare_attempted)
        )

    @staticmethod
    def search_key(vector, scope):
        # Top-K cannot disguise a retry of the same failed query and region.
        values = vector.tolist() if hasattr(vector, "tolist") else list(vector)
        return sha256(repr(values).encode()).hexdigest(), scope.model_dump_json()

    def allows_search(self, vector, scope):
        return self.enabled and self.search_key(vector, scope) not in self.failed_searches

    async def embed(self, texts):
        self.check_time()
        if not self.allows_embedding(texts):
            raise RuntimeError("Previous request embedding or initialization failure")
        record = {
            "operation": "embedding",
            "query_count": len(texts),
            "status": "attempted",
            "phase": self.phase,
        }
        self.operations.append(record)
        try:
            await self.prepare()
            value = await self.runtime.embed(texts)
        except BaseException:
            self.failed_embeddings.update(texts)
            record["status"] = "incomplete_or_failed"
            raise
        record["status"] = "succeeded"
        return value

    async def search(self, vector, scope, top_k):
        self.check_time()
        key = self.search_key(vector, scope)
        if not self.allows_search(vector, scope):
            raise RuntimeError("Previous request retrieval failure")
        record = {
            "operation": "retrieval",
            "top_k": top_k,
            "status": "attempted",
            "phase": self.phase,
        }
        self.operations.append(record)
        try:
            await self.prepare()
            value = await self.runtime.search(vector, scope, top_k)
        except BaseException:
            self.failed_searches.add(key)
            record["status"] = "incomplete_or_failed"
            raise
        record["status"] = "succeeded"
        return value

    def snapshot(self):
        return deepcopy(
            {
                "prepared": self.prepared,
                "rag_enabled": self.enabled,
                "initialization_attempted": self.prepare_attempted,
                "owned": self.owned,
                "closed": self.closed,
                "operations": self.operations,
                "runtime_diagnostics": getattr(self, "diagnostics", []),
                "http_attempts": getattr(self, "http_attempts", []),
            }
        )

    async def close(self):
        if self.closed:
            return
        self.closed = True
        if self.owned and self.runtime is not None:
            # Shield cleanup from the cancellation that ended planning, but await it.
            async def release():
                try:
                    await self.runtime.__aexit__(None, None, None)
                except Exception as exc:
                    self.operations.append(
                        {"operation": "close", "status": "failed", "error": type(exc).__name__}
                    )

            task = asyncio.create_task(release())
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError:
                await task
                raise
