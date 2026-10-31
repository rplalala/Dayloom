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
