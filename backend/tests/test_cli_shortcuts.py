"""Short commands preserve native capture and explicit execution boundaries."""

import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

from backend.cli.rtpeval import main


@pytest.mark.parametrize("version", ["v0", "v1", "v2", "v3"])
def test_short_generation_prepares_fresh_runs_without_credentials(
    tmp_path, monkeypatch, capsys, version
):
    monkeypatch.chdir(tmp_path)
    request = tmp_path / "trip.json"
    original = json.dumps(
        {
            "input_version": "planning_request_2",
            "destination": "Sydney, Australia",
            "start_date": "2026-11-05",
            "end_date": "2026-11-06",
            "traveler_count": 2,
            "budget": {"amount": "1600", "currency": "AUD"},
        }
    ).encode()
    request.write_bytes(original)
    reference = SimpleNamespace(today=lambda: date(2026, 11, 1))
    outputs = []
    for _ in range(2):
        assert main(["generate", version, str(request)], date_provider=reference) == 0
        report = json.loads(capsys.readouterr().out)
        assert report["status"] == "prepared"
        assert report["provider_sends"] == 0
        output = Path(report["output_directory"])
        outputs.append(output)
        assert (output / "input.json").read_bytes() == original
        manifest = json.loads((output / "manifest.json").read_bytes())
        assert manifest["version"] == version
        assert manifest["group_id"] == "trip"
        assert manifest["run_id"]
        assert not manifest["execution_requested"]
        assert not (output / "result.json").exists()
    assert outputs[0] != outputs[1]


def test_published_cases_have_one_offline_verification_command(monkeypatch, capsys):
    import socket

    def blocked(*args, **kwargs):
        raise AssertionError("Published-result verification must not contact providers")

    monkeypatch.setattr(socket, "create_connection", blocked)
    assert main(["verify"]) == 0
    output = capsys.readouterr().out
    assert "12 cases" in output
    assert "48 finals" in output
    assert "24 confirmed answers" in output


def test_short_generation_refuses_existing_output(tmp_path):
    from backend.tests.test_rtpeval_generate_cli import REFERENCE, arguments

    native = arguments(tmp_path)
    source = native[native.index("--input-json") + 1]
    output = tmp_path / "capture"
    output.mkdir()
    marker = output / "keep.txt"
    marker.write_text("keep")
    with pytest.raises(FileExistsError):
        main(["generate", "v0", source, "-o", str(output)], date_provider=REFERENCE)
    assert marker.read_text() == "keep"


def test_short_generation_executes_once_with_explicit_identities(tmp_path, capsys):
    from backend.tests.test_rtpeval_generate_cli import REFERENCE, Runtime, arguments

    native = arguments(tmp_path)
    source = native[native.index("--input-json") + 1]
    output = tmp_path / "capture"
    assert main([
        "generate", "v0", source, "-o", str(output), "--group-id", "chosen-group",
        "--run-id", "chosen-run", "--execute",
    ], runtime=Runtime(), date_provider=REFERENCE) == 0
    capsys.readouterr()
    manifest = json.loads((output / "manifest.json").read_bytes())
    assert manifest["group_id"] == "chosen-group"
    assert manifest["run_id"] == "chosen-run"
    dispatch = json.loads((output / "planner-dispatch.json").read_bytes())
    assert dispatch["planner_dispatches"] == 1
    assert (output / "result.json").is_file()
