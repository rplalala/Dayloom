"""Budget metadata survives large-payload truncation without changing planning."""

import json

from backend.app.observability.run_trace import FileRunTracer, TracePayloadMode
from backend.tests.observability.test_run_trace import _context


def test_budget_summary_survives_truncated_final_outcome(tmp_path):
    tracer = FileRunTracer(
        _context(), root=tmp_path, payload_mode=TracePayloadMode.METADATA, max_payload_bytes=100
    )
    tracer.finish(
        status="completed",
        requirements=None,
        tool_usage={"weather_calls": {"used": 1, "limit": 2}},
        outcome={"large": "x" * 5000},
    )
    assert json.loads((tracer.run_directory / "run.json").read_text())["truncated"]
    summary = json.loads((tracer.run_directory / "budget.json").read_text())
    assert summary["status"] == "completed"
    assert summary["primary_tools"]["weather_calls"] == {"used": 1, "limit": 2}
    assert summary["stages"]["primary_generation"]["usage_status"] == "missing"
    assert "large" not in json.dumps(summary)


def test_stage_snapshots_are_not_summed_and_usage_is_deduplicated(tmp_path):
    from dataclasses import replace

    from backend.app.runtime.config_loader import load_runtime_config, runtime_config_snapshot

    snapshot, digest = runtime_config_snapshot(load_runtime_config())
    tracer = FileRunTracer(
        replace(_context(), runtime_config=snapshot, runtime_config_sha256=digest),
        root=tmp_path,
        payload_mode=TracePayloadMode.METADATA,
    )
    semantic = dict(
        call_id="call-1",
        status="accepted",
        elapsed_seconds=2,
        engineering_tokens=300,
        usage={"model": {"input_tokens": 100, "output_tokens": 20, "total_tokens": 120}},
    )
    for _ in range(2):
        tracer.event("poi_semantic_assessment", semantic)
        tracer.event(
            "rag_final_fate",
            dict(
                details_sends=26,
                fallback_sends=4,
                embedding_sends=1,
                embedding_usage={"total_tokens": 7},
            ),
        )
        tracer.event(
            "v3_repair_round",
            dict(
                round_index=1,
                cumulative_counters={"routes": 12, "elements": 12, "model": 1},
                usage={"model": {"input_tokens": 200, "output_tokens": 30, "total_tokens": 230}},
            ),
        )
    tracer.finish(status="completed", requirements=None, tool_usage={}, outcome=None)
    stages = json.loads((tracer.run_directory / "budget.json").read_text())["stages"]
    assert stages["semantics"]["calls"][0]["usage"]["output_tokens"] == 20
    assert len(stages["semantics"]["calls"]) == 1
    assert stages["semantics"]["limits"]["max_calls"] == 6
    assert stages["rag"]["observed"]["details_sends"] == 26
    assert stages["rag"]["limits"]["fallback_calls"] == 4
    assert stages["repair"]["observed"]["routes"] == 12
    assert len(stages["repair"]["calls"]) == 1
    assert stages["repair"]["calls"][0]["usage"]["output_tokens"] == 30
    assert stages["requirements"]["usage_status"] == "missing"


def test_budget_write_failure_does_not_prevent_final_trace(tmp_path, monkeypatch):
    from pathlib import Path

    tracer = FileRunTracer(_context(), root=tmp_path, payload_mode=TracePayloadMode.METADATA)
    original = Path.write_text

    def fail_budget(path, *args, **kwargs):
        if path.name == "budget.json.tmp":
            raise OSError("Disk failure")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", fail_budget)
    tracer.finish(status="failed", requirements=None, tool_usage={}, outcome=None)
    final = json.loads((tracer.run_directory / "run.json").read_text())
    assert final["status"] == "failed"
    assert final["budget_summary_status"] == "unavailable"


def test_semantic_timeout_metadata_survives_failed_trace_finalization(tmp_path):
    tracer = FileRunTracer(_context(), root=tmp_path, payload_mode=TracePayloadMode.METADATA)
    tracer.event(
        "poi_semantic_assessment",
        dict(
            call_id="timeout-call",
            status="failed",
            error_type="TimeoutError",
            usage={},
            timeout_seconds=13.5,
            limiting_deadline="caller",
            remaining_seconds={"call": 45, "total": 76.9, "caller": 13.5, "request": 460},
        ),
    )
    tracer.finish(status="failed", requirements=None, tool_usage={}, outcome=None)
    summary = json.loads((tracer.run_directory / "budget.json").read_text())
    call = summary["stages"]["semantics"]["calls"][0]
    assert call["timeout_seconds"] == 13.5 and call["limiting_deadline"] == "caller"
    assert call["remaining_seconds"] == {
        "call": 45,
        "total": 76.9,
        "caller": 13.5,
        "request": 460,
    }
    assert call["error_type"] == "TimeoutError" and call["usage_status"] == "missing"


def test_call_cap_is_explicit_and_secrets_never_enter_budget_file(tmp_path):
    tracer = FileRunTracer(_context(), root=tmp_path, payload_mode=TracePayloadMode.RAW)
    for i in range(40):
        tracer.event(
            "poi_semantic_assessment",
            dict(
                call_id=f"call-{i}",
                secret="Bearer sensitive-value",
                assessments=["secret-place"],
                usage={
                    "credential-secret": {
                        "input_tokens": 10,
                        "output_tokens": 5,
                        "total_tokens": 15,
                    }
                },
            ),
        )
    tracer.finish(
        status="completed",
        requirements=None,
        tool_usage={"secret-key": {"used": 1, "limit": 2}},
        outcome={"secret": "private-itinerary"},
    )
    path = tracer.run_directory / "budget.json"
    text = path.read_text()
    summary = json.loads(text)
    assert len(text.encode()) <= 65536
    assert summary["collection_status"] == "incomplete"
    assert len(summary["stages"]["semantics"]["calls"]) == 32
    assert "secret" not in text and "sensitive-value" not in text


def test_actual_v3_flow_writes_final_separate_budget_pools(tmp_path):
    import asyncio
    from dataclasses import replace

    from backend.app.runtime.config_loader import load_runtime_config, runtime_config_snapshot
    from backend.tests.versions.v3.test_wiring import execute

    snapshot, digest = runtime_config_snapshot(load_runtime_config())
    tracer = FileRunTracer(
        replace(
            _context(), system_version="v3", runtime_config=snapshot, runtime_config_sha256=digest
        ),
        root=tmp_path,
        payload_mode=TracePayloadMode.METADATA,
        max_payload_bytes=300,
    )
    result, _, _, _ = asyncio.run(execute(tracer=tracer))
    summary = json.loads((tracer.run_directory / "budget.json").read_text())
    assert summary["status"] == "completed"
    assert summary["stages"]["repair"]["observed"]["model"] == result.v3.repair.counters["model"]
    assert len(summary["stages"]["semantics"]["calls"]) == result.semantic_assessment["calls"]
    assert summary["primary_tools"]["weather_calls"]["used"] == 1
    assert json.loads((tracer.run_directory / "run.json").read_text())["truncated"]


def test_cancelled_rag_retains_recorded_work_without_inventing_usage(tmp_path):
    tracer = FileRunTracer(_context(), root=tmp_path, payload_mode=TracePayloadMode.METADATA)
    tracer.event(
        "rag_cancelled",
        {
            "resolution_attempts": 3,
            "details_sends": 2,
            "fallback_sends": 1,
            "retrieval_queries": 1,
            "embedding_sends": 1,
        },
    )
    tracer.finish(status="cancelled", requirements=None, tool_usage={}, outcome=None)
    summary = json.loads((tracer.run_directory / "budget.json").read_text())
    assert summary["stages"]["rag"]["observed"]["resolution_attempts"] == 3
    assert summary["stages"]["rag"]["observed"]["details_sends"] == 2
    assert summary["stages"]["rag"]["usage_status"] == "missing"


def test_nomination_accounting_is_separate_and_does_not_include_names(tmp_path):
    tracer = FileRunTracer(_context(), root=tmp_path, payload_mode=TracePayloadMode.METADATA)
    tracer.event(
        "landmark_nomination",
        dict(
            calls=1,
            call_id="landmark-1",
            elapsed_seconds=0.2,
            engineering_tokens=600,
            nominated=2,
            names=["PRIVATE"],
            usage={},
        ),
    )
    tracer.event(
        "landmark_discovery",
        dict(
            resolved=1,
            unresolved=1,
            supplementary_sends=1,
            candidate_search_sends=4,
            general_status="provider_success",
        ),
    )
    tracer.finish(status="completed", requirements=None, tool_usage={}, outcome=None)
    data = json.loads((tracer.run_directory / "budget.json").read_text())
    row = data["stages"]["landmark_nomination"]
    assert row["observed"]["resolved"] == 1
    assert row["observed"]["calls"] == 1
    assert row["calls"][0]["usage_status"] == "missing"
    assert data["stages"]["semantics"]["calls"] == []
    assert "PRIVATE" not in json.dumps(data)
