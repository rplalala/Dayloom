"""Public Product diagnostics: bounded storage, isolation and secret protection."""

import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest

from backend.app.observability.product_logs import ProductLogs, ProductLogSettings, log_context


@pytest.fixture(autouse=True)
def enable_diagnostics(monkeypatch):
    monkeypatch.setenv("PRODUCT_LOG_ENABLED", "true")


def test_product_operations_are_correlated_redacted_and_readable(tmp_path, monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "ambient-private-value")
    logs = ProductLogs(ProductLogSettings(directory=tmp_path, max_file_bytes=4096))
    with log_context(task_id="task-one", request_id="request-one"):
        logs.event("operation", {"password": "private-password", "detail": "ambient-private-value"})
    result = logs.read(task_id="task-one")
    assert result[0]["task_id"] == "task-one"
    assert result[0]["request_id"] == "request-one"
    text = json.dumps(result)
    assert "private-password" not in text
    assert "ambient-private-value" not in text


def test_missing_usage_remains_null_instead_of_a_secret_marker(tmp_path):
    logs = ProductLogs(ProductLogSettings(directory=tmp_path))
    logs.event(
        "usage", {"reported": {"input_tokens": None, "cached_input_tokens": 12}, "password": 123}
    )
    data = logs.read()[0]["data"]
    assert data["reported"] == {"input_tokens": None, "cached_input_tokens": 12}
    assert data["password"] == "[REDACTED]"


def test_product_rotation_retains_valid_json_and_other_resources(tmp_path):
    unrelated = tmp_path / "keep.txt"
    unrelated.write_text("unrelated")
    logs = ProductLogs(ProductLogSettings(directory=tmp_path, max_file_bytes=1024, backups=2))
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(
            pool.map(lambda i: logs.event("operation", {"index": i, "text": "x" * 200}), range(40))
        )
    assert len(list(tmp_path.glob("operations*.jsonl"))) <= 3
    assert logs.read()
    assert unrelated.read_text() == "unrelated"


def test_logging_off_and_failed_storage_do_not_break_operations(tmp_path, caplog):
    disabled = ProductLogs(ProductLogSettings(enabled=False, directory=tmp_path / "disabled"))
    disabled.event("ignored", {})
    assert not (tmp_path / "disabled").exists()
    blocked = tmp_path / "file"
    blocked.write_text("not a directory")
    logs = ProductLogs(ProductLogSettings(directory=blocked))
    logs.event("operation", {})
    assert "Product diagnostics" in caplog.text


def test_retention_only_removes_owned_finished_inactive_runs(tmp_path):
    logs = ProductLogs(ProductLogSettings(directory=tmp_path, retention_days=1))
    runs = tmp_path / "runs"
    for name in ("old-finished", "active", "unrelated"):
        path = runs / name
        path.mkdir(parents=True)
        if name != "unrelated":
            (path / "summary.json").write_text("{}")
        if name == "active":
            (path / ".active").touch()
        stamp = (datetime.now(UTC) - timedelta(days=3)).timestamp()
        os.utime(path, (stamp, stamp))
    logs.prune()
    assert not (runs / "old-finished").exists()
    assert (runs / "active").exists()
    assert (runs / "unrelated").exists()


def test_retention_rejects_a_namespace_resolving_outside_the_owned_root(tmp_path, monkeypatch):
    logs = ProductLogs(ProductLogSettings(directory=tmp_path / "owned", retention_days=1))
    namespace = logs.root / "runs"
    namespace.mkdir(parents=True)
    outside = tmp_path / "other" / "finished"
    outside.mkdir(parents=True)
    (outside / "summary.json").write_text("{}")
    stamp = (datetime.now(UTC) - timedelta(days=3)).timestamp()
    os.utime(outside, (stamp, stamp))
    from pathlib import Path

    original = Path.resolve
    monkeypatch.setattr(
        Path,
        "resolve",
        lambda path, *a, **kw: outside.parent if path == namespace else original(path, *a, **kw),
    )
    logs.prune()
    assert (outside / "summary.json").is_file()


def test_final_summary_survives_event_limits(tmp_path):
    from backend.app.observability.product_logs import ProductRunTracer
    from backend.app.runtime.config_loader import load_runtime_config
    from backend.tests.observability.test_run_trace import _context

    logs = ProductLogs(
        ProductLogSettings(directory=tmp_path, max_run_bytes=4096, max_event_bytes=512)
    )
    tracer = ProductRunTracer(_context(), logs=logs, trace=load_runtime_config().trace)
    for index in range(30):
        tracer.event("large_event", {"index": index, "text": "x" * 900})
    tracer.event(
        "v3_finalized",
        {
            "reason": "phase_or_request_deadline",
            "repair": {"status": "ACCEPTED_PARTIAL"},
            "soft_pace": {"completion": {"status": "partial"}},
        },
    )
    tracer.close("completed")
    summary = logs.read(summaries_only=True)[0]
    assert summary["stop_reason"] == "phase_or_request_deadline"
    assert summary["collection_status"] == "incomplete"
    assert summary["pace"]["completion"]["status"] == "partial"


def test_stage_timings_survive_detailed_event_truncation(tmp_path):
    from backend.app.observability.product_logs import ProductRunTracer
    from backend.app.runtime.config_loader import load_runtime_config
    from backend.tests.observability.test_run_trace import _context

    logs = ProductLogs(ProductLogSettings(directory=tmp_path, max_event_bytes=512))
    tracer = ProductRunTracer(_context(), logs=logs, trace=load_runtime_config().trace)
    tracer.event("product_stage", {"type": "stage", "stage": "requirements", "status": "started"})
    tracer.event(
        "product_stage",
        {"type": "stage", "stage": "requirements", "status": "completed", "duration_ms": 1250},
    )
    tracer.event("large_event", {"text": "x" * 2000})
    tracer.close("completed")
    assert logs.read(summaries_only=True)[0]["stages"]["requirements"]["elapsed_ms"] == 1250


def test_upstream_truncated_final_event_preserves_compact_completion(tmp_path):
    from backend.app.observability.product_logs import ProductRunTracer
    from backend.app.runtime.config_loader import load_runtime_config
    from backend.tests.observability.test_run_trace import _context

    logs = ProductLogs(ProductLogSettings(directory=tmp_path))
    tracer = ProductRunTracer(_context(), logs=logs, trace=load_runtime_config().trace)
    tracer.event(
        "v3_completion_summary",
        {
            "reason": "model_call_limit",
            "repair_status": "ACCEPTED_PARTIAL",
            "pace_completion": {"status": "partial"},
            "validation_counts": {"UNKNOWN": 2},
        },
    )
    tracer.event(
        "v3_finalized",
        {"truncated": True, "reason": "model_call_limit", "repair_status": "ACCEPTED_PARTIAL"},
    )
    tracer.close("completed")
    summary = logs.read(summaries_only=True)[0]
    assert summary["repair_status"] == "ACCEPTED_PARTIAL"
    assert summary["validation_counts"] == {"UNKNOWN": 2}
    assert summary["pace_completion"]["status"] == "partial"
    assert summary["upstream_details_truncated"]


def test_oversized_summary_keeps_stop_reason_within_its_separate_limit(tmp_path):
    from backend.app.observability.product_logs import ProductRunTracer
    from backend.app.runtime.config_loader import load_runtime_config
    from backend.tests.observability.test_run_trace import _context

    logs = ProductLogs(ProductLogSettings(directory=tmp_path))
    tracer = ProductRunTracer(_context(), logs=logs, trace=load_runtime_config().trace)
    tracer.event(
        "v3_completion_summary", {"reason": "model_call_limit", "repair_status": "ACCEPTED_PARTIAL"}
    )
    tracer.event(
        "product_presented",
        {"policy_completion": "incomplete", "required_experiences": ["x" * 100000]},
    )
    tracer.close("completed")
    path = next(tmp_path.glob("runs/*/summary.json"))
    summary = json.loads(path.read_text())
    assert path.stat().st_size <= 65536
    assert summary["stop_reason"] == "model_call_limit"
    assert summary["product_result"]["policy_completion"] == "incomplete"
    assert summary["summary_details_truncated"]


def test_failed_run_keeps_the_active_spending_bound(tmp_path):
    from decimal import Decimal

    from backend.app.integrations.spending import SpendingBudget, SpendingLimitError
    from backend.app.observability.product_logs import ProductRunTracer
    from backend.app.runtime.config_loader import load_runtime_config
    from backend.tests.observability.test_run_trace import _context

    logs = ProductLogs(ProductLogSettings(directory=tmp_path))
    tracer = ProductRunTracer(_context(), logs=logs, trace=load_runtime_config().trace)
    budget = SpendingBudget("2")
    with budget.activate():
        budget.reserve(Decimal("1"), "places")
        with pytest.raises(SpendingLimitError):
            budget.reserve(Decimal("2"), "places")
        tracer.close("failed")
    snapshot = logs.read(summaries_only=True)[0]["spending_upper_bound_not_invoice"]
    assert snapshot == {
        "limit_usd": "2",
        "charged_upper_usd": "1",
        "blocked": True,
        "event_count": 1,
    }
