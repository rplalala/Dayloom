"""Best-effort JSON/JSONL tracing for an individual V1 run."""

import json
import logging
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import StrEnum
from pathlib import Path
from typing import Protocol, runtime_checkable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import UUID

from backend.app.observability.budget_summary import BudgetSummary
from backend.app.policies.trip_dates import TripDateWindow
from backend.app.schemas.request import PlanningRequest, TravelRequirements

LOGGER = logging.getLogger(__name__)
_SENSITIVE_KEY_PARTS = (
    "apikey",
    "authorization",
    "bearer",
    "credential",
    "cookie",
    "password",
    "secret",
    "token",
)
_BEARER_PATTERN = re.compile(r"(?i)\bBearer\s+[^\s,;]+")
_EMBEDDED_URL_PATTERN = re.compile(r"https?://[^\s\"'<>]+")
_SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\b(api[_-]?key|authorization|bearer|credential|password|secret|token)"
    r"\s*[:=]\s*([^\s,;]+)"
)


class TracePayloadMode(StrEnum):
    """Increasing levels of optional trace payload detail."""

    METADATA = "metadata"
    NORMALIZED = "normalized"
    RAW = "raw"


_PAYLOAD_LEVEL = {
    TracePayloadMode.METADATA: 0,
    TracePayloadMode.NORMALIZED: 1,
    TracePayloadMode.RAW: 2,
}


@dataclass(frozen=True)
class RunTraceContext:
    """Immutable metadata captured once when a V1 run starts."""

    run_id: UUID
    system_version: str
    reference_date: date
    date_window: TripDateWindow
    request: PlanningRequest
    started_at: datetime
    runtime_config: dict[str, object] | None = None
    runtime_config_sha256: str | None = None


@runtime_checkable
class RunTracer(Protocol):
    """Trace interface that graph, LLM, and integration layers can share."""

    @property
    def run_id(self) -> UUID:
        """Return the immutable run identifier."""

        ...

    def event(self, event_type: str, payload: object | None = None) -> None:
        """Append one ordered lifecycle event without raising."""

        ...

    def payload(
        self,
        category: str,
        name: str,
        value: object,
        *,
        minimum_mode: TracePayloadMode,
    ) -> None:
        """Write an optional redacted payload without raising."""

        ...

    def set_requirements(self, requirements: TravelRequirements) -> None:
        """Retain requested dates for final run metadata without raising."""

        ...

    def finish(
        self,
        *,
        status: str,
        requirements: TravelRequirements | None,
        tool_usage: dict[str, object],
        outcome: object | None,
        error: object | None = None,
    ) -> None:
        """Finalize run metadata without raising."""

        ...


def _normalized_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _is_sensitive_key(value: str) -> bool:
    normalized = _normalized_key(value)
    return normalized == "key" or any(part in normalized for part in _SENSITIVE_KEY_PARTS)


def _redact_url(value: str) -> str:
    try:
        parts = urlsplit(value)
    except ValueError:
        return value
    if not parts.scheme or not parts.netloc or not parts.query:
        return value
    query = [
        (
            key,
            "[REDACTED]" if _is_sensitive_key(key) else item,
        )
        for key, item in parse_qsl(parts.query, keep_blank_values=True)
    ]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def redact_secrets(value: object) -> object:
    """Recursively remove common credential fields and bearer values."""
    from .raw_capture import redact_known_credentials

    value = redact_known_credentials(value)

    if isinstance(value, dict):
        redacted: dict[str, object] = {}
        for key, item in value.items():
            if (
                str(key)
                in {
                    "max_output_tokens",
                    "input_tokens",
                    "output_tokens",
                    "total_tokens",
                    "reasoning_tokens",
                    "input_tokens_estimated",
                    "framing_tokens",
                    "total_query_tokens",
                    "system_tokens",
                    "user_tokens",
                    "schema_tokens",
                    "source_max_tokens",
                    "model_input_tokens_per_call",
                    "draft_output_tokens",
                    "cache_read",
                    "cached_tokens",
                    "cache_read_input_tokens",
                    "cache_write_input_tokens",
                    "cache_write_tokens",
                    "cache_creation_input_tokens",
                    "reasoning",
                }
                and type(item) is int
                and item >= 0
            ):
                redacted[str(key)] = item
            elif _is_sensitive_key(str(key)):
                redacted[str(key)] = "[REDACTED]"
            else:
                redacted[str(key)] = redact_secrets(item)
        return redacted
    if isinstance(value, (list, tuple, set)):
        return [redact_secrets(item) for item in value]
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, str):
        redacted = _SECRET_ASSIGNMENT_PATTERN.sub(r"\1=[REDACTED]", value)
        redacted = _EMBEDDED_URL_PATTERN.sub(lambda match: _redact_url(match.group(0)), redacted)
        return _BEARER_PATTERN.sub("Bearer [REDACTED]", redacted)
    if hasattr(value, "model_dump"):
        return redact_secrets(value.model_dump(mode="json"))
    return value


class NullRunTracer:
    """No-op tracer used by tests and disabled tracing configurations."""

    def __init__(self, run_id: UUID) -> None:
        self._run_id = run_id

    @property
    def run_id(self) -> UUID:
        return self._run_id

    def event(self, event_type: str, payload: object | None = None) -> None:
        return None

    def payload(
        self,
        category: str,
        name: str,
        value: object,
        *,
        minimum_mode: TracePayloadMode,
    ) -> None:
        return None

    def set_requirements(self, requirements: TravelRequirements) -> None:
        return None

    def finish(
        self,
        *,
        status: str,
        requirements: TravelRequirements | None,
        tool_usage: dict[str, object],
        outcome: object | None,
        error: object | None = None,
    ) -> None:
        return None


class FileRunTracer:
    """Best-effort local trace writer whose failures never escape to planning."""

    def __init__(
        self,
        context: RunTraceContext,
        *,
        root: Path,
        payload_mode: TracePayloadMode,
        max_payload_bytes: int = 1_000_000,
        capture_llm: bool = True,
        capture_tools: bool = True,
        capture_evidence: bool = True,
        raw_provider_payloads: bool = True,
    ) -> None:
        self._context = context
        self._run_id = context.run_id
        self._payload_mode = payload_mode
        self._max_payload_bytes = max_payload_bytes
        self._capture_categories = {
            "llm": capture_llm,
            "tools": capture_tools,
            "evidence": capture_evidence,
        }
        self._raw_provider_payloads = raw_provider_payloads
        timestamp = context.started_at.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
        self.run_directory = root / f"{timestamp}_{context.run_id}"
        self._events_path = self.run_directory / "events.jsonl"
        self._sequence = 0
        self._payload_sequence = 0
        self._failed = False
        self._requirements: TravelRequirements | None = None
        self._budget_summary = BudgetSummary(context)
        try:
            self.run_directory.mkdir(parents=True, exist_ok=False)
            for child in ("llm", "tools", "evidence"):
                (self.run_directory / child).mkdir()
            self._write_run_json(status="running")
        except Exception as exc:
            self._disable(exc)

    @property
    def run_id(self) -> UUID:
        return self._run_id

    def _disable(self, exc: Exception) -> None:
        if not self._failed:
            LOGGER.warning("Run tracing disabled after a local write failure: %s", exc)
        self._failed = True

    def _serialize(self, value: object) -> str:
        serialized = json.dumps(
            redact_secrets(value),
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
        encoded = serialized.encode("utf-8")
        if len(encoded) <= self._max_payload_bytes:
            return serialized
        marker = json.dumps(
            {
                "truncated": True,
                "original_bytes": len(encoded),
                "preview": encoded[: self._max_payload_bytes].decode("utf-8", errors="ignore"),
            },
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
        return marker

    def _run_metadata(self, *, status: str, **updates: object) -> dict[str, object]:
        value: dict[str, object] = {
            "run_id": str(self._context.run_id),
            "system_version": self._context.system_version,
            "system_stage": "v1-a",
            "runtime_reference_date": self._context.reference_date.isoformat(),
            "allowed_date_window": {
                "start": self._context.date_window.allowed_start.isoformat(),
                "end": self._context.date_window.allowed_end.isoformat(),
            },
            "requested_trip_dates": None,
            "started_at": self._context.started_at.isoformat(),
            "finished_at": None,
            "status": status,
            "input": self._context.request.model_dump(mode="json"),
            "tool_usage": {},
            "runtime_config": self._context.runtime_config,
            "runtime_config_sha256": self._context.runtime_config_sha256,
            "final_outcome": None,
        }
        value.update(updates)
        return value

    def _write_run_json(self, *, status: str, **updates: object) -> None:
        value = self._run_metadata(status=status, **updates)
        (self.run_directory / "run.json").write_text(self._serialize(value), encoding="utf-8")

    def event(self, event_type: str, payload: object | None = None) -> None:
        try:
            self._budget_summary.observe(event_type, payload)
        except Exception:
            self._budget_summary.incomplete = True
        if self._failed:
            return
        try:
            self._sequence += 1
            record = {
                "sequence": self._sequence,
                "recorded_at": datetime.now(UTC).isoformat(),
                "event": event_type,
                "payload": payload,
            }
            with self._events_path.open("a", encoding="utf-8") as stream:
                stream.write(
                    json.dumps(
                        redact_secrets(record),
                        ensure_ascii=True,
                        separators=(",", ":"),
                        sort_keys=True,
                    )
                )
                stream.write("\n")
        except Exception as exc:
            self._disable(exc)

    def payload(
        self,
        category: str,
        name: str,
        value: object,
        *,
        minimum_mode: TracePayloadMode,
    ) -> None:
        if (
            self._failed
            or not self._capture_categories.get(category, False)
            or (
                category == "tools"
                and minimum_mode is TracePayloadMode.RAW
                and not self._raw_provider_payloads
            )
            or _PAYLOAD_LEVEL[self._payload_mode] < _PAYLOAD_LEVEL[minimum_mode]
        ):
            return
        try:
            self._payload_sequence += 1
            safe_name = re.sub(r"[^a-zA-Z0-9_.-]", "_", name)
            path = self.run_directory / category / f"{self._payload_sequence:04d}_{safe_name}.json"
            path.write_text(self._serialize(value), encoding="utf-8")
        except Exception as exc:
            self._disable(exc)

    def set_requirements(self, requirements: TravelRequirements) -> None:
        if self._failed:
            return
        self._requirements = requirements

    def finish(
        self,
        *,
        status: str,
        requirements: TravelRequirements | None,
        tool_usage: dict[str, object],
        outcome: object | None,
        error: object | None = None,
    ) -> None:
        budget_status = self._write_budget_summary(status, tool_usage)
        if self._failed:
            return
        try:
            effective_requirements = requirements or self._requirements
            requested_dates = None
            if effective_requirements is not None:
                requested_dates = {
                    "start": effective_requirements.start_date,
                    "end": effective_requirements.end_date,
                }
            finished_at = datetime.now(UTC).isoformat()
            if error is not None:
                (self.run_directory / "error.json").write_text(
                    self._serialize(error), encoding="utf-8"
                )
            self._write_run_json(
                status=status,
                requested_trip_dates=requested_dates,
                finished_at=finished_at,
                tool_usage=tool_usage,
                final_outcome=outcome,
                budget_summary_status=budget_status,
            )
        except Exception as exc:
            self._disable(exc)

    def _write_budget_summary(self, status, tool_usage):
        try:
            value = self._budget_summary.finish(status, tool_usage)
            serialized = json.dumps(value, ensure_ascii=True, separators=(",", ":"))
            if len(serialized.encode("utf-8")) > 65536:
                serialized = json.dumps(
                    {
                        "schema_version": 1,
                        "run_id": str(self.run_id),
                        "status": value["status"],
                        "collection_status": "incomplete",
                        "reason": "summary_size_limit",
                        "primary_tools": {},
                        "stages": {},
                    }
                )
            pending = self.run_directory / "budget.json.tmp"
            pending.write_text(serialized, encoding="utf-8")
            pending.replace(self.run_directory / "budget.json")
            return "written"
        except Exception:
            LOGGER.warning("Budget summary unavailable after a local collection or write failure")
            return "unavailable"


def create_run_tracer(
    context: RunTraceContext,
    *,
    enabled: bool,
    root: Path,
    payload_mode: TracePayloadMode,
    max_payload_bytes: int = 1_000_000,
    capture_llm: bool = True,
    capture_tools: bool = True,
    capture_evidence: bool = True,
    raw_provider_payloads: bool = True,
) -> RunTracer:
    """Create a file tracer or a no-op tracer with the same immutable run ID."""

    if not enabled:
        return NullRunTracer(context.run_id)
    tracer = FileRunTracer(
        context,
        root=root,
        payload_mode=payload_mode,
        max_payload_bytes=max_payload_bytes,
        capture_llm=capture_llm,
        capture_tools=capture_tools,
        capture_evidence=capture_evidence,
        raw_provider_payloads=raw_provider_payloads,
    )
    if tracer._failed:
        return NullRunTracer(context.run_id)
    return tracer
