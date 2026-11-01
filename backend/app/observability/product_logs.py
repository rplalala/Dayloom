"""Local Product diagnostics with bounded files and request/task correlation."""

import asyncio
import json
import logging
import math
import os
import re
import shutil
import threading
from collections import Counter
from contextlib import contextmanager, nullcontext
from contextvars import ContextVar
from datetime import UTC, datetime
from pathlib import Path
from time import time
from uuid import uuid4

from pydantic import Field
from pydantic_settings import SettingsConfigDict

from backend.app.observability.run_trace import (
    FileRunTracer,
    NullRunTracer,
    RunTraceContext,
    redact_secrets,
)
from backend.app.runtime.configuration_paths import InstanceSettings
from backend.app.runtime.database import PROJECT_ROOT

LOGGER = logging.getLogger(__name__)
_context = ContextVar("product_log_context", default=None)
_locks = {}
_locks_guard = threading.Lock()
_SECRET = re.compile(r"key|password|secret|credential|cookie|authorization|db_url", re.I)
_USAGE_FIELDS = {
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "cached_input_tokens",
    "cache_write_input_tokens",
    "reasoning_tokens",
    "system_tokens",
    "user_tokens",
    "schema_tokens",
    "framing_tokens",
    "context_tokens",
    "candidate_tokens",
    "evidence_tokens",
    "requirements_findings_tokens",
    "engineering_tokens",
    "total_query_tokens",
}


def _restore_numeric_usage(original, redacted):
    if isinstance(original, dict) and isinstance(redacted, dict):
        for key, value in original.items():
            if key in _USAGE_FIELDS and (value is None or (type(value) is int and value >= 0)):
                redacted[key] = value
            elif key in redacted:
                _restore_numeric_usage(value, redacted[key])
    elif isinstance(original, (list, tuple)) and isinstance(redacted, list):
        for source, target in zip(original, redacted, strict=False):
            _restore_numeric_usage(source, target)


class ProductLogSettings(InstanceSettings):
    model_config = SettingsConfigDict(
        env_prefix="PRODUCT_LOG_",
        env_file=PROJECT_ROOT / ".env",
        extra="ignore",
        hide_input_in_errors=True,
    )
    enabled: bool = True
    directory: Path = PROJECT_ROOT / "logs" / "product"
    max_file_bytes: int = Field(default=5_000_000, ge=1024)
    backups: int = Field(default=5, ge=1, le=50)
    max_event_bytes: int = Field(default=128_000, ge=512)
    max_run_bytes: int = Field(default=50_000_000, ge=4096)
    max_storage_bytes: int = Field(default=500_000_000, ge=4096)
    retention_days: int = Field(default=30, ge=1, le=3650)


@contextmanager
def log_context(*, reset=False, **fields):
    token = _context.set(
        {
            **({} if reset else (_context.get() or {})),
            **{k: str(v) for k, v in fields.items() if v is not None},
        }
    )
    try:
        yield
    finally:
        _context.reset(token)


def context_fields():
    return dict(_context.get() or {})


def safe_error(error):
    """Keep exception types and code locations, never exception text or locals."""
    chain, seen = [], set()
    while error is not None and id(error) not in seen and len(chain) < 8:
        seen.add(id(error))
        frames, tb = [], error.__traceback__
        while tb is not None:
            frames.append(
                {
                    "file": Path(tb.tb_frame.f_code.co_filename).name,
                    "function": tb.tb_frame.f_code.co_name,
                    "line": tb.tb_lineno,
                }
            )
            tb = tb.tb_next
        chain.append({"type": type(error).__name__, "frames": frames[-12:]})
        error = error.__cause__ or error.__context__
    return chain


class ProductLogs:
    def __init__(self, settings=None):
        self.settings = settings or ProductLogSettings()
        directory = self.settings.directory
        self.root = (directory if directory.is_absolute() else PROJECT_ROOT / directory).resolve()
        self.failed = False
        self._last_warning = 0
        from dotenv import dotenv_values

        values = {**dotenv_values(PROJECT_ROOT / ".env"), **os.environ}
        self._secrets = sorted(
            {v for k, v in values.items() if _SECRET.search(k) and v and len(v) >= 8},
            key=len,
            reverse=True,
        )

    def sanitize(self, value):
        redacted = redact_secrets(value)
        _restore_numeric_usage(value, redacted)
        encoded = json.dumps(redacted, ensure_ascii=True, default=str)
        for secret in self._secrets:
            encoded = encoded.replace(json.dumps(secret)[1:-1], "[REDACTED]")
        # URLs with userinfo can contain database passwords without a labelled field.
        encoded = re.sub(
            r"(?<![a-z0-9+.-])([a-z][a-z0-9+.-]*://)[^/\s\"@]+@",
            r"\1[REDACTED]@", encoded, flags=re.I,
        )
        return json.loads(encoded)

    @property
    def runs_root(self):
        namespace = self.root / "runs"
        if (
            namespace.is_symlink()
            or namespace.is_junction()
            or namespace.resolve().parent != self.root
        ):
            raise OSError("Product run namespace is outside the configured root")
        return namespace

    def warning(self):
        self.failed = True
        if time() - self._last_warning > 60:
            LOGGER.warning("Product diagnostics incomplete after a storage or collection failure")
            self._last_warning = time()

    @contextmanager
    def storage(self):
        with _locks_guard:
            lock = _locks.setdefault(str(self.root), threading.RLock())
        with lock:
            self.root.mkdir(parents=True, exist_ok=True)
            with (self.root / ".writer.lock").open("a+b") as stream:
                if stream.tell() == 0:
                    stream.write(b"0")
                    stream.flush()
                stream.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                try:
                    yield
                finally:
                    stream.seek(0)
                    if os.name == "nt":
                        msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                    else:
                        fcntl.flock(stream.fileno(), fcntl.LOCK_UN)

    def bounded(self, value, limit=None):
        value = self.sanitize(value)
        encoded = json.dumps(value, ensure_ascii=True, separators=(",", ":"))
        if len(encoded.encode()) > (limit or self.settings.max_event_bytes):
            return {"truncated": True, "original_bytes": len(encoded.encode())}
        return value

    def event(self, name, data=None):
        if not self.settings.enabled:
            return
        try:
            row = {
                "schema_version": 1,
                "recorded_at": datetime.now(UTC).isoformat(),
                **context_fields(),
                "event": name,
                "data": self.bounded(
                    data, min(self.settings.max_event_bytes, self.settings.max_file_bytes // 2)
                ),
            }
            encoded = json.dumps(row, ensure_ascii=True, separators=(",", ":")) + "\n"
            with self.storage():
                path = self.root / "operations.jsonl"
                if (
                    path.exists()
                    and path.stat().st_size + len(encoded.encode()) > self.settings.max_file_bytes
                ):
                    for index in range(self.settings.backups, 0, -1):
                        source = self.root / (
                            f"operations.{index - 1}.jsonl" if index > 1 else "operations.jsonl"
                        )
                        if source.exists():
                            source.replace(self.root / f"operations.{index}.jsonl")
                with path.open("a", encoding="utf-8") as stream:
                    stream.write(encoded)
        except Exception:
            self.warning()

    def read(self, *, task_id=None, run_id=None, summaries_only=False):
        """Read local diagnostics; never exposed as an unauthenticated HTTP API."""
        rows = []
        if not self.root.is_dir():
            return rows
        paths = [] if summaries_only else list(self.root.glob("operations*.jsonl"))
        for directory in self.runs_root.glob("*"):
            if directory.is_dir() and not directory.is_symlink() and not directory.is_junction():
                summary = directory / "summary.json"
                if summary.exists():
                    identity = json.loads(summary.read_text(encoding="utf-8"))
                    if task_id is not None and identity.get("task_id") != task_id:
                        continue
                    if run_id is not None and identity.get("run_id") != run_id:
                        continue
                if not summaries_only:
                    paths.extend(directory.glob("*.jsonl"))
                paths.extend(directory.glob("summary.json"))
        for path in sorted(paths):
            with path.open(encoding="utf-8") as stream:
                for line in stream:
                    try:
                        row = json.loads(line)
                    except ValueError:
                        continue
                    data = row.get("data") if isinstance(row.get("data"), dict) else {}
                    if task_id is not None and row.get("task_id", data.get("task_id")) != task_id:
                        continue
                    if run_id is not None and row.get("run_id") != run_id:
                        continue
                    rows.append(row)
        return sorted(rows, key=lambda row: row.get("recorded_at", row.get("started_at", "")))

    def prune(self):
        """Only delete expired/over-quota finished runs in this owned namespace."""
        if not self.settings.enabled:
            return
        try:
            with self.storage():
                runs = self.runs_root
                candidates = []
                for path in runs.glob("*"):
                    if (
                        path.is_symlink()
                        or path.is_junction()
                        or not path.is_dir()
                        or path.resolve().parent != runs
                    ):
                        continue
                    if not (path / "summary.json").is_file():
                        continue
                    active = path / ".active"
                    if active.exists() and time() - active.stat().st_mtime < 86400:
                        continue
                    size = sum(
                        p.stat().st_size
                        for p in path.rglob("*")
                        if p.is_file() and not p.is_symlink()
                    )
                    candidates.append((path.stat().st_mtime, path, size))
                total = sum(size for _, _, size in candidates)
                for stamp, path, size in sorted(candidates):
                    if (
                        time() - stamp > self.settings.retention_days * 86400
                        or total > self.settings.max_storage_bytes
                    ):
                        shutil.rmtree(path)
                        total -= size
        except Exception:
            self.warning()


class ProductRunTracer(FileRunTracer):
    """Reuse planner tracing, with independent final diagnostics and per-run bounds."""

    def __init__(self, context, *, logs, trace):
        self.logs, self.correlation = logs, context_fields()
        self.summary = {
            **self.correlation,
            "run_id": str(context.run_id),
            "schema_version": 1,
            "started_at": context.started_at.isoformat(),
            "status": "running",
        }
        self.bytes_written = 0
        self.incomplete = False
        self._closed = False
        logs.prune()
        super().__init__(
            context,
            root=logs.runs_root,
            payload_mode=trace.payload_level,
            max_payload_bytes=min(trace.max_payload_bytes, logs.settings.max_event_bytes),
            capture_llm=trace.capture_llm,
            capture_tools=trace.capture_tools,
            capture_evidence=trace.capture_evidence,
            raw_provider_payloads=trace.raw_provider_payloads,
        )
        if not self._failed:
            try:
                (self.run_directory / ".active").touch()
                self.summary["collection_status"] = "in_progress"
                self._save_summary()
            except OSError:
                self._disable(None)

    def _serialize(self, value):
        encoded = json.dumps(self.logs.sanitize(value), ensure_ascii=True, default=str)
        if len(encoded.encode()) > self._max_payload_bytes:
            self.incomplete = True
            return json.dumps({"truncated": True, "original_bytes": len(encoded.encode())})
        return encoded

    def _write_run_json(self, *, status, **updates):
        value = self._run_metadata(
            status=status, **{**updates, **self.correlation, "system_stage": "product-v3"}
        )
        # Metadata has its own allowance; a large outcome must not erase identity,
        # configuration or completion timestamps when detailed events are bounded.
        value = self.logs.sanitize(value)
        for key, limit in (
            ("input", 16_384), ("runtime_config", 24_576),
            ("tool_usage", 8_192), ("final_outcome", 8_192),
        ):
            bounded = self.logs.bounded(value[key], limit)
            if bounded != value[key]:
                self.incomplete = True
                if key == "final_outcome":
                    bounded.update(summary_file="summary.json", event_file="events.jsonl")
            value[key] = bounded
        pending = self.run_directory / "run.json.tmp"
        pending.write_text(json.dumps(value, ensure_ascii=True, default=str), encoding="utf-8")
        pending.replace(self.run_directory / "run.json")

    def _disable(self, exc):
        self.logs.warning()
        self.incomplete = True
        self._failed = True

    def event(self, event_type, payload=None):
        try:
            self._budget_summary.observe(event_type, payload)
            if event_type == "v3_repair_input_sizing" and isinstance(payload, dict):
                from backend.app.observability.budget_summary import REPAIR_INPUT_KEYS, select

                self.summary["repair_input_sizing"] = select(payload, REPAIR_INPUT_KEYS)
            if event_type == "product_stage" and isinstance(payload, dict):
                self._observe_stage(payload)
            if event_type == "v3_completion_summary" and isinstance(payload, dict):
                self.summary.update(
                    {key: value for key, value in payload.items() if key != "reason"}
                )
                self.summary["stop_reason"] = payload.get("reason")
            if (
                event_type == "v3_finalized"
                and isinstance(payload, dict)
                and payload.get("truncated")
            ):
                self.incomplete = True
                self.summary["upstream_details_truncated"] = True
                self.summary.setdefault("stop_reason", payload.get("reason"))
                self.summary.setdefault("repair_status", payload.get("repair_status"))
            elif event_type == "v3_finalized" and isinstance(payload, dict):
                from backend.app.observability.run_trace import TracePayloadMode

                for key in ("draft", "original_report", "final_primary", "final_report"):
                    if key in payload:
                        self.payload(
                            "evidence", key, payload[key], minimum_mode=TracePayloadMode.METADATA
                        )
                repair = payload.get("repair") or {}
                report = payload.get("final_report") or {}
                findings = report.get("findings", [])
                self.summary.update(
                    stop_reason=payload.get("reason"),
                    repair_status=repair.get("status"),
                    selected_round_index=repair.get("selected_round_index"),
                    pace=payload.get("soft_pace"),
                    validation_counts=dict(Counter(row.get("status") for row in findings)),
                    validation=[
                        {
                            k: row.get(k)
                            for k in ("finding_id", "check", "status", "reason", "dates")
                        }
                        for row in findings[:50]
                    ],
                    validation_details_truncated=len(findings) > 50,
                )
            if event_type == "v3_repair_decision":
                self.summary["last_repair_decision"] = payload
            if event_type == "product_presented":
                self.summary["product_result"] = payload
            bounded = self.logs.bounded(payload)
            if bounded != self.logs.sanitize(payload):
                self.incomplete = True
            cost = len(json.dumps(bounded, default=str).encode())
            if self.bytes_written + cost > self.logs.settings.max_run_bytes:
                self.incomplete = True
                return
            self.bytes_written += cost
            if self._failed:
                return
            self._sequence += 1
            row = {
                **self.correlation,
                "run_id": str(self.run_id),
                "sequence": self._sequence,
                "recorded_at": datetime.now(UTC).isoformat(),
                "event": event_type,
                "payload": bounded,
            }
            with self._events_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(row, ensure_ascii=True, separators=(",", ":")) + "\n")
        except Exception:
            self.logs.warning()
            self.incomplete = True

    def _observe_stage(self, payload):
        stage, status = payload.get("stage"), payload.get("status")
        if not isinstance(stage, str) or not re.fullmatch(r"[a-z_]{1,60}", stage):
            return
        if status not in {"started", "completed", "failed", "cancelled", "skipped"}:
            return
        stages = self.summary.setdefault("stages", {})
        if stage not in stages and len(stages) >= 64:
            self.incomplete = True
            return
        row = stages.setdefault(
            stage, {"elapsed_ms": None, "timed_occurrences": 0, "scope": "inclusive_not_additive"}
        )
        row[status] = row.get(status, 0) + 1
        row["last_status"] = status
        duration = payload.get("duration_ms")
        if type(duration) in (int, float) and math.isfinite(duration) and duration >= 0:
            row["elapsed_ms"] = (row["elapsed_ms"] or 0) + duration
            row["timed_occurrences"] += 1

    def payload(self, category, name, value, *, minimum_mode):
        try:
            cost = min(
                len(json.dumps(self.logs.sanitize(value), default=str).encode()),
                self._max_payload_bytes,
            )
            if self.bytes_written + cost > self.logs.settings.max_run_bytes:
                self.incomplete = True
                return
            self.bytes_written += cost
            super().payload(category, name, self.logs.sanitize(value), minimum_mode=minimum_mode)
        except Exception:
            self.logs.warning()
            self.incomplete = True

    def finish(self, **kwargs):
        self.summary["planner_status"] = kwargs["status"]
        self._final_tool_usage = kwargs["tool_usage"]
        super().finish(**kwargs)

    def _save_summary(self):
        value = self.logs.sanitize(self.summary)
        if len(json.dumps(value).encode()) > 65536:
            retained = {
                key: self.logs.bounded(value[key], 1024)
                for key in (
                    "schema_version",
                    "task_id",
                    "execution_id",
                    "run_id",
                    "request_id",
                    "owner_id",
                    "fence",
                    "started_at",
                    "finished_at",
                    "status",
                    "stop_reason",
                    "repair_status",
                    "selected_round_index",
                    "primary_tool_usage_status",
                    "repair_input_sizing",
                    "policy_completion",
                )
                if key in value
            }
            retained.update(collection_status="incomplete", summary_details_truncated=True)
            for key in (
                "pace_completion",
                "spending_upper_bound_not_invoice",
                "stages",
                "usage",
                "validation_counts",
                "product_result",
                "error",
            ):
                if key not in value:
                    continue
                item = value[key]
                if key == "product_result" and isinstance(item, dict):
                    item = {
                        name: item[name]
                        for name in ("pace_review", "policy_completion", "policy_reasons")
                        if name in item
                    }
                candidate = self.logs.bounded(item, 16000)
                if len(json.dumps({**retained, key: candidate}).encode()) <= 65536:
                    retained[key] = candidate
            value = retained
        pending = self.run_directory / "summary.json.tmp"
        pending.write_text(json.dumps(value, separators=(",", ":")), encoding="utf-8")
        pending.replace(self.run_directory / "summary.json")

    def close(self, status, *, result=None, error=None):
        if self._closed:
            return
        self._closed = True
        try:
            from backend.app.integrations.spending import current_spending_budget

            budget = current_spending_budget()
            if budget:
                snapshot = budget.snapshot()
                self.summary["spending_upper_bound_not_invoice"] = {
                    key: value for key, value in snapshot.items() if key != "events"
                }
                self.summary["spending_upper_bound_not_invoice"]["event_count"] = len(
                    snapshot["events"]
                )
            if not hasattr(self, "_final_tool_usage"):
                self._budget_summary.incomplete = True
                self.incomplete = True
                self.summary["primary_tool_usage_status"] = "unavailable"
            else:
                self.summary["primary_tool_usage_status"] = "recorded"
            self.summary.update(
                status=status,
                finished_at=datetime.now(UTC).isoformat(),
                collection_status="incomplete" if self.incomplete or self._failed else "complete",
            )
            if result is not None:
                self.summary["completion"] = (
                    result.completion.model_dump(mode="json")
                    if hasattr(result, "completion") and result.completion
                    else None
                )
            if error is not None:
                self.summary["error"] = safe_error(error)
            budget_status = self._write_budget_summary(
                status, getattr(self, "_final_tool_usage", {})
            )
            if budget_status != "written":
                self.summary["collection_status"] = "incomplete"
            if len(json.dumps(self.logs.sanitize(self.summary), default=str).encode()) > 65536:
                self.summary["validation"] = []
                self.summary["pace"] = {
                    "completion": (self.summary.get("pace") or {}).get("completion")
                }
                self.summary["collection_status"] = "incomplete"
                self.summary["summary_details_truncated"] = True
            self._save_summary()
            (self.run_directory / ".active").unlink(missing_ok=True)
        except Exception:
            self.logs.warning()

    def record_usage(self, data):
        from backend.app.observability.run_trace import TracePayloadMode

        models = data.get("model_calls", [])
        self.summary["usage"] = {
            "scope": "instrumented_adapters_only_not_invoice",
            "model_calls": len(models),
            "provider_events": len(data.get("provider_events", [])),
            "missing_fields": data.get("missing_fields", []),
            "usage_status": "reported"
            if models and all(row.get("total_tokens") is not None for row in models)
            else "missing_or_partial",
            "reported": {
                key: sum(row[key] for row in models)
                if models and all(type(row.get(key)) is int for row in models)
                else None
                for key in ("input_tokens", "output_tokens", "total_tokens")
            },
        }
        timings = {}
        for row in data.get("stage_summaries", []):
            stage, elapsed = row.get("stage"), row.get("elapsed_seconds")
            if not isinstance(stage, str) or not re.fullmatch(r"[a-z_]{1,60}", stage):
                continue
            if stage not in timings and len(timings) >= 64:
                self.incomplete = True
                break
            observed = timings.setdefault(
                stage,
                {"elapsed_seconds": None, "observations": 0, "scope": "inclusive_not_additive"},
            )
            if type(elapsed) in (int, float) and math.isfinite(elapsed) and elapsed >= 0:
                observed["elapsed_seconds"] = (observed["elapsed_seconds"] or 0) + elapsed
                observed["observations"] += 1
        self.summary["usage"]["stage_timings"] = timings
        self.payload("llm", "usage", data, minimum_mode=TracePayloadMode.METADATA)


def operation(name, data=None):
    """Best-effort audit hook, including when Product settings are unavailable."""
    try:
        ProductLogs().event(name, data)
    except Exception:
        LOGGER.warning("Product diagnostics unavailable: invalid logging configuration")


class ProductTracer:
    """Fan out diagnostics and public progress without replacing either observer."""

    def __init__(self, file_tracer, progress):
        self.file_tracer, self.progress = file_tracer, progress

    def __getattr__(self, name):
        return getattr(self.file_tracer, name)

    def event(self, name, payload=None):
        self.file_tracer.event(name, payload)
        if self.progress:
            self.progress.event(name, payload)

    def payload(self, *args, **kwargs):
        self.file_tracer.payload(*args, **kwargs)


@contextmanager
def planning_diagnostics(request, reference_date, *, config=None):
    from backend.app.observability.model_usage import observe_usage
    from backend.app.observability.progress import ProgressTracer, current_progress
    from backend.app.policies.trip_dates import create_trip_date_window
    from backend.app.runtime.config_loader import (
        load_product_runtime_config,
        runtime_config_snapshot,
    )

    observer = current_progress()
    run_id = observer.run_id if observer else uuid4()
    file = None
    try:
        logs = ProductLogs()
        config = config or load_product_runtime_config()
        if logs.settings.enabled and config.trace.enabled:
            snapshot, digest = runtime_config_snapshot(config)
            context = RunTraceContext(
                run_id=run_id,
                system_version="v3",
                reference_date=reference_date,
                date_window=create_trip_date_window(reference_date),
                request=request,
                started_at=datetime.now(UTC),
                runtime_config=snapshot,
                runtime_config_sha256=digest,
            )
            file = ProductRunTracer(context, logs=logs, trace=config.trace)
    except Exception:
        LOGGER.warning("Product diagnostics unavailable during run setup")
    tracer = ProductTracer(
        file or NullRunTracer(run_id), ProgressTracer(observer) if observer else None
    )
    previous_sink = observer.diagnostic_sink if observer else None
    if observer:
        observer.diagnostic_sink = lambda event: tracer.event("product_stage", event)
    try:
        with (
            log_context(run_id=run_id),
            observe_usage(file.record_usage) if file else nullcontext(),
        ):
            yield tracer
    except BaseException as error:
        if file:
            file.close(
                "cancelled" if isinstance(error, asyncio.CancelledError) else "failed", error=error
            )
        raise
    else:
        if file:
            file.close("completed")
    finally:
        if observer:
            observer.diagnostic_sink = previous_sink
