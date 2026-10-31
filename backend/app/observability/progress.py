"""Opt-in, request-local execution observations, independent of persisted traces."""

import asyncio
from collections import Counter, deque
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from inspect import iscoroutinefunction
from time import monotonic
from uuid import uuid4

from backend.app.observability.run_trace import NullRunTracer
from backend.app.observability.usage import usage_stage

_current = ContextVar("planning_progress", default=None)
_parent = ContextVar("planning_progress_parent", default=None)

MESSAGES = {
    "introductions": "Preparing place introductions",
    "requirements": "Understanding your trip preferences",
    "destination": "Finding your destination",
    "candidates": "Finding places for your trip",
    "retrieval": "Finding places for your trip",
    "weather": "Checking the weather",
    "routes": "Checking travel times",
    "official_information": "Checking place information",
    "generation": "Planning your days",
    "date_validation": "Checking your trip dates",
    "transfers": "Checking travel times",
    "validation": "Checking your itinerary",
    "repair": "Adjusting your itinerary",
    "repair_round": "Adjusting your itinerary",
    "repair_preparation": "Adjusting your itinerary",
    "repair_model": "Adjusting your itinerary",
    "repair_reason_compression": "Adjusting your itinerary",
    "revalidation": "Checking the updated itinerary",
    "nearby": "Finding nearby suggestions",
}


def current_progress():
    return _current.get()


def skipped(stage):
    observer = current_progress()
    if observer is not None:
        observer.occurrences[stage] += 1
        observer.stage(stage, observer.occurrences[stage], "skipped")


def progress_details(name, details):
    """Accept explicit, safe metadata from the mechanism that owns its meaning."""
    observer = current_progress()
    if observer is not None:
        observer.detail(name, details)


@contextmanager
def progress_scope(observer):
    token = _current.set(observer)
    parent_token = _parent.set(None)
    try:
        yield
    finally:
        _parent.reset(parent_token)
        _current.reset(token)


class ProgressObserver:
    """Bounded per-request buffer; a slow reader receives an explicit loss notice."""

    def __init__(
        self, *, developer=False, version=None, clock=monotonic, capacity=256, run_id=None
    ):
        self.run_id = run_id or uuid4()
        self.diagnostic_sink = None
        self.developer, self.version, self.clock = developer, version, clock
        self.started = clock()
        self.sequence = 0
        self.occurrences = Counter()
        self.buffer = deque(maxlen=capacity)
        self.ready = asyncio.Event()
        self.dropped = 0

    def emit(self, kind, **fields):
        self.sequence += 1
        event = {
            "run_id": str(self.run_id),
            "sequence": self.sequence,
            "type": kind,
            "elapsed_ms": max(0, (self.clock() - self.started) * 1000),
            **fields,
        }
        if self.developer:
            event["version"] = self.version
        if self.diagnostic_sink is not None:
            try:
                self.diagnostic_sink(event)
            except Exception:
                pass  # Diagnostics never take ownership of planning/progress.
        if len(self.buffer) == self.buffer.maxlen:
            self.buffer.popleft()
            self.dropped += 1
        self.buffer.append(event)
        self.ready.set()

    async def next(self):
        while not self.buffer:
            self.ready.clear()
            await self.ready.wait()
        event = self.buffer.popleft()
        if self.dropped:
            event = {**event, "dropped_events": self.dropped}
            self.dropped = 0
        return event

    def begin(self, stage, **details):
        self.occurrences[stage] += 1
        occurrence = self.occurrences[stage]
        started = self.clock()
        self.stage(stage, occurrence, "started", details=details)
        return occurrence, started

    def stage(self, stage, occurrence, status, *, duration=None, details=None):
        fields = {
            "stage": stage,
            "occurrence": occurrence,
            "status": status,
            "stage_id": f"{stage}:{occurrence}",
            "parent_id": _parent.get(),
            "message": MESSAGES.get(stage, "Preparing your itinerary"),
        }
        if duration is not None and status != "skipped":
            fields["duration_ms"] = max(0, duration * 1000)
        if self.developer and details:
            fields["details"] = details
        self.emit("stage", **fields)

    def detail(self, name, details):
        if self.developer:
            self.emit("detail", name=name, stage_id=_parent.get(), details=details)


def _summary(result):
    """Explicit counters only, never prompts, model reasoning or intermediate drafts."""
    if hasattr(result, "findings"):
        return {
            "finding_counts": dict(Counter(f.status for f in result.findings)),
            "findings": [
                {"id": f.finding_id, "check": f.check, "status": f.status} for f in result.findings
            ],
        }
    if hasattr(result, "target_progress"):
        return {
            "repair_status": result.status,
            "reason": result.reason,
            "model_attempted": result.model_attempted,
            "target_outcomes": [
                {"id": t.finding_id, "outcome": t.outcome} for t in result.target_progress
            ],
        }
    return {}


def observed(stage):
    """Observe an existing function without changing its arguments/result/exception."""

    def decorate(function):
        def start():
            observer = current_progress()
            if observer is None:
                return None
            occurrence, started = observer.begin(stage)
            token = _parent.set(f"{stage}:{occurrence}")
            return observer, occurrence, started, token

        def finish(context, result=None, error=None):
            if context is None:
                return
            observer, occurrence, started, token = context
            _parent.reset(token)
            status = "completed"
            if error is not None:
                status = "cancelled" if isinstance(error, asyncio.CancelledError) else "failed"
            observer.stage(
                stage,
                occurrence,
                status,
                duration=observer.clock() - started,
                details=_summary(result) if error is None else None,
            )

        @wraps(function)
        async def asynchronous(*args, **kwargs):
            context = start()
            try:
                with usage_stage(stage, kwargs.get("round_index")):
                    result = await function(*args, **kwargs)
            except BaseException as exc:
                finish(context, error=exc)
                raise
            finish(context, result=result)
            return result

        @wraps(function)
        def synchronous(*args, **kwargs):
            context = start()
            try:
                with usage_stage(stage, kwargs.get("round_index")):
                    result = function(*args, **kwargs)
            except BaseException as exc:
                finish(context, error=exc)
                raise
            finish(context, result=result)
            return result

        return asynchronous if iscoroutinefunction(function) else synchronous

    return decorate


class ProgressTracer(NullRunTracer):
    """Translate selected existing structured counters; discard trace payloads entirely."""

    def __init__(self, observer):
        super().__init__(observer.run_id)
        self.observer = observer

    def event(self, event_type, payload=None):
        if event_type == "semantic_candidate_admission" and isinstance(payload, dict):
            self.observer.detail(
                "candidate_admission",
                {
                    "raw_count": payload.get("raw_count"),
                    "merged_count": payload.get("merged_count"),
                    "admitted_count": len(payload.get("admitted_ids", ())),
                    "omitted_count": len(payload.get("omitted_ids", ())),
                },
            )
        elif event_type == "planning_supply_completed" and isinstance(payload, dict):
            self.observer.detail(
                "planning_supply",
                {
                    "selected_count": len(payload.get("selected_ids", ())),
                    "details_attempts": payload.get("details_attempts"),
                    "reviewed_count": len(payload.get("review_place_ids", ())),
                },
            )
        elif event_type == "opening_hours_planning_views_created" and isinstance(payload, dict):
            self.observer.detail(
                "generation_input",
                {
                    "place_count": len(payload.get("places", ())),
                },
            )


class ObservedV0Client:
    """Observe V0's generation call without editing its graph, prompts or runner."""

    def __init__(self, client):
        self.client = client

    def __getattr__(self, name):
        return getattr(self.client, name)

    async def generate_structured(self, **kwargs):
        from backend.app.schemas.itinerary import Itinerary

        call = self.client.generate_structured
        if kwargs.get("response_schema") is Itinerary:
            call = observed("generation")(call)
        return await call(**kwargs)
