"""Offline pilot guard and observation checks; no external provider requests."""

import asyncio
import subprocess
from types import SimpleNamespace

import pytest

from tools.validation import landmark_pilot as pilot


def prepared(tmp_path, monkeypatch):
    monkeypatch.setattr(pilot, "OUTPUT", tmp_path / "pilot")
    monkeypatch.setattr(pilot, "local_dependencies", lambda: None)
    monkeypatch.setattr(pilot, "source_hashes", lambda: {"fixture.py": "frozen"})
    monkeypatch.setattr(pilot, "today_and_validate", lambda: "2026-09-28")
    pilot.prepare()
    return pilot.OUTPUT


def test_prepare_and_preflight_reject_drift_order_and_repeated_attempts(tmp_path, monkeypatch):
    output = prepared(tmp_path, monkeypatch)
    assert pilot.preflight(pilot.CASES[0]) == "2026-09-28"
    with pytest.raises(FileNotFoundError):
        pilot.preflight(pilot.CASES[1])
    monkeypatch.setattr(pilot, "source_hashes", lambda: {"fixture.py": "changed"})
    with pytest.raises(ValueError, match="source/input"):
        pilot.preflight(pilot.CASES[0])
    monkeypatch.setattr(pilot, "source_hashes", lambda: {"fixture.py": "frozen"})
    pilot.write(output / f"{pilot.CASES[0]}.started.json", {})
    with pytest.raises(FileExistsError):
        pilot.preflight(pilot.CASES[0])


@pytest.mark.parametrize("timeout", [False, True])
def test_failed_process_or_timeout_consumes_attempt_and_stops_batch(tmp_path, monkeypatch, timeout):
    output = prepared(tmp_path, monkeypatch)

    def launch(*args, **kwargs):
        assert kwargs["timeout"] == 660
        if timeout:
            raise subprocess.TimeoutExpired("fake", 660)
        return SimpleNamespace(returncode=1)

    head = pilot.read(output / "manifest.json")["git_head"]
    monkeypatch.setattr(pilot.subprocess, "check_output", lambda *a, **kw: head)
    (tmp_path / ".env").touch()
    monkeypatch.setattr(pilot, "ROOT", tmp_path)
    monkeypatch.setattr(pilot.subprocess, "run", launch)
    assert pilot.execute(pilot.CASES[0]) == 1
    assert not pilot.read(output / f"{pilot.CASES[0]}.finished.json")["continue_allowed"]
    with pytest.raises(FileExistsError):
        pilot.execute(pilot.CASES[0])
    with pytest.raises(ValueError, match="stopped"):
        pilot.preflight(pilot.CASES[1])


def test_capture_observes_actual_v3_entry_without_adding_model_calls(tmp_path):
    from backend.tests.versions.v3.test_wiring import Model, execute

    class Nomination(Model):
        nominations = 0

        async def generate_landmark_nomination_structured(self, **kwargs):
            self.nominations += 1
            return {"names": ["Place poi-0-0"]}

    capture = pilot.PilotCapture(tmp_path)
    with capture.observe():
        result, model, _, runtime = asyncio.run(execute(Nomination()))
    assert model.nominations == 1 and model.repair_calls >= 1
    assert runtime.closes == 1 and result.request_resources["closed"]
    assert {"initial", "initial_validation", "nomination", "resolution"} <= set(capture.stages)
    assert not capture.errors
    records = [pilot.read(p) for p in tmp_path.glob("*.json")]
    initial = next(r for r in records if r["validation_stage"] == "initial")
    assert initial["itinerary"] == result.v3.draft.model_dump(mode="json")
    assert initial["supply"]["landmarks"]["poi-0-0"]["rank"] == 1


def test_capture_failure_is_observed_without_changing_nomination(tmp_path, monkeypatch):
    from backend.app.runtime.config_models import LandmarkNominationConfig
    from backend.app.services.landmark_nomination import LandmarkNominationService

    class Model:
        async def generate_landmark_nomination_structured(self, **kwargs):
            return {"names": ["Landmark"]}

    capture = pilot.PilotCapture(tmp_path)
    monkeypatch.setattr(capture.capture, "record", lambda *a, **kw: None)
    with capture.observe():
        assert asyncio.run(
            LandmarkNominationService(Model(), LandmarkNominationConfig(), 2048).nominate(
                {"name": "City"}
            )
        ) == ("Landmark",)
    assert capture.errors == ["nomination:OSError"]


def test_capture_redacts_and_bounds_artifacts(tmp_path):
    capture = pilot.PilotCapture(tmp_path, ("fixture-secret",))
    capture.save("small", {"name": "fixture-secret"})
    assert "fixture-secret" not in next(tmp_path.glob("*.json")).read_text()
    capture.save("oversize", {"name": "a" * 1100000})
    assert capture.errors == ["oversize:OverflowError"]


def test_capture_initialization_and_payload_failures_are_isolated(tmp_path, monkeypatch):
    def fail(*args, **kwargs):
        raise OSError("fixture")

    capture = pilot.PilotCapture(tmp_path / "payload")
    capture.save("payload", fail)
    assert capture.errors == ["payload:OSError"]
    monkeypatch.setattr(pilot, "DevelopmentRequirementCapture", fail)
    capture = pilot.PilotCapture(tmp_path / "init")
    capture.save("value", {})
    assert capture.errors == ["initialization:OSError", "value:OSError"]


def test_case_capture_limit_uses_actual_written_bytes(tmp_path):
    capture = pilot.PilotCapture(tmp_path)
    for i in range(10):
        capture.save(str(i), {"values": ["a" * 70] * 10000})
    assert capture.errors
    assert sum(p.stat().st_size for p in tmp_path.glob("*.json")) <= 4 * 1024 * 1024


@pytest.mark.parametrize("cancel", [False, True])
def test_initial_evidence_survives_no_target_or_later_cancellation(tmp_path, cancel):
    from backend.tests.versions.v3.test_wiring import Model, execute, primary

    model = Model(primary(cancel), "cancel" if cancel else "complete")
    capture = pilot.PilotCapture(tmp_path)
    with capture.observe():
        if cancel:
            with pytest.raises(asyncio.CancelledError):
                asyncio.run(execute(model))
        else:
            result, _, _, _ = asyncio.run(execute(model))
            assert result.v3.repair is None and model.repair_calls == 0
    assert {"initial", "initial_validation"} <= set(capture.stages)
    assert not capture.errors
