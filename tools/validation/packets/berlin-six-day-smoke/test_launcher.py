"""Offline process-boundary checks; no providers or network are constructed."""

import importlib.util
import json
import subprocess
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

spec = importlib.util.spec_from_file_location(
    "berlin_packet", Path(__file__).with_name("run_one.py")
)
packet = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packet)


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    output = tmp_path / "evidence"
    request = tmp_path / "request.json"
    packet.write_json(request, packet.EXPECTED_REQUEST)
    runtime = tmp_path / "runtime-source.yaml"
    policy = yaml.safe_load(packet.RUNTIME.read_text(encoding="utf-8"))
    # The historical launcher retains its original five-send guard.
    policy["v3_repair"]["max_model_calls"] = 5
    runtime.write_text(yaml.safe_dump(policy), encoding="utf-8")
    for name, value in {
        "OUTPUT": output,
        "REQUEST": request,
        "RUNTIME": runtime,
        "MANIFEST": output / "manifest.json",
        "COPIED_RUNTIME": output / "runtime.yaml",
        "local_dependencies": lambda: None,
        "credentials": lambda version: (),
        "all_secrets": lambda: (),
        "git_head": lambda: "frozen",
        "environment_hash": lambda: "environment",
        "source_hashes": lambda: {"input": packet.sha256(request)},
        "current_date_and_validate": lambda trip: date(2026, 9, 28),
    }.items():
        monkeypatch.setattr(packet, name, value)
    packet.prepare()
    return output


def result(version):
    return {
        "system_version": version,
        "itinerary": {
            "start_date": "2026-10-03",
            "end_date": "2026-10-08",
            "days": [
                {
                    "date": (date(2026, 10, 3) + timedelta(days=i)).isoformat(),
                    "activities": [{"title": "Example visit"}],
                }
                for i in range(6)
            ],
        },
    }


def fake_process(command, **kwargs):
    assert kwargs["timeout"] == 660
    version = (
        command[command.index("--version") + 1]
        if "--version" in command
        else Path(command[1]).stem.removeprefix("run_")
    )
    output = packet.OUTPUT / version
    if version in {"v1", "v3"}:
        output.mkdir()
    if version != "v0":
        trace = (
            (packet.OUTPUT / "trace" / version) if version == "v2" else output / "trace" / version
        )
        trace.mkdir(parents=True)
        packet.write_json(
            trace / "budget.json",
            {
                "collection_status": "complete",
                "primary_tools": {"calls": {"used": 1, "limit": 2}},
            },
        )
        packet.write_json(trace / "run.json", {"truncated": False})
    encoded = json.dumps(result(version)).encode()
    if version in {"v1", "v3"}:
        packet.write_json(output / "result.json", result(version))
        packet.write_json(
            output / "execution.json",
            {
                "application_exit_code": 0,
                "trace_status": "available",
                "trace_directories": [str(trace)],
                "capture_status": "complete",
                "semantic_capture_status": "complete",
                "repair_capture_errors": [],
            },
        )
    return SimpleNamespace(stdout=encoded, stderr=b"", returncode=0)


def test_four_complete_cases_enable_blind_review_once(prepared, monkeypatch):
    monkeypatch.setattr(packet.subprocess, "run", fake_process)
    for version in packet.CASES:
        packet.run(version)
        batch = json.loads(packet.MANIFEST.read_text())
        assert batch["blind_review_eligible"] == (version == "v3")
    with pytest.raises(ValueError):
        packet.run("v0")


def test_source_drift_blocks_before_process(prepared, monkeypatch):
    monkeypatch.setattr(packet, "source_hashes", lambda: {"changed": "hash"})
    with pytest.raises(ValueError, match="changed"):
        packet.run("v0")
    assert not (prepared / "v0.attempt.lock").exists()


def test_timeout_consumes_attempt_and_stops_batch(prepared, monkeypatch):
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], 660)

    monkeypatch.setattr(packet.subprocess, "run", timeout)
    packet.run("v0")
    assert json.loads(packet.MANIFEST.read_text())["status"] == "stopped_timeout"
    assert (prepared / "v0.attempt.lock").is_file()
    with pytest.raises(ValueError, match="stopped"):
        packet.run("v1")


def test_incomplete_day_disables_blind_review(prepared, monkeypatch):
    def incomplete(command, **kwargs):
        outcome = fake_process(command, **kwargs)
        if "run_v0.py" in command[1]:
            payload = json.loads(outcome.stdout)
            payload["itinerary"]["days"][2]["activities"] = []
            outcome.stdout = json.dumps(payload).encode()
        return outcome

    monkeypatch.setattr(packet.subprocess, "run", incomplete)
    for version in packet.CASES:
        packet.run(version)
    assert not json.loads(packet.MANIFEST.read_text())["blind_review_eligible"]


def test_budget_overrun_stops_following_case(prepared, monkeypatch):
    def overrun(command, **kwargs):
        outcome = fake_process(command, **kwargs)
        if "--version" in command:
            packet.write_json(
                prepared / "v1/trace/v1/budget.json",
                {
                    "collection_status": "complete",
                    "primary_tools": {"calls": {"used": 3, "limit": 2}},
                },
            )
        return outcome

    monkeypatch.setattr(packet.subprocess, "run", overrun)
    packet.run("v0")
    packet.run("v1")
    assert json.loads(packet.MANIFEST.read_text())["status"] == "stopped_budget_evidence"
    with pytest.raises(ValueError, match="stopped"):
        packet.run("v2")


def test_version_commands_preserve_independent_paths():
    actual = json.loads(Path(__file__).with_name("request.json").read_text(encoding="utf-8"))
    assert actual == packet.EXPECTED_REQUEST
    assert actual["destination"] == "Berlin, Germany"
    commands = {v: packet.command_for(v, "2026-09-28", Path("example")) for v in packet.CASES}
    assert commands["v0"][1].endswith("run_v0.py")
    assert "--runtime-config" not in commands["v0"]
    assert commands["v2"][1].endswith("run_v2.py")
    assert "--rag-env-file" in commands["v2"]
    assert "--capture-repair" in commands["v3"]
    assert "--rag-env-file" not in commands["v1"]
