"""Actual Planner invocation clocks and explicitly non-dispatched preparation."""

import json
from datetime import UTC, datetime

import pytest

from backend.tests.test_rtpeval_generate_cli import REFERENCE, Runtime, arguments, registration


@pytest.mark.parametrize("execute", [False, True])
def test_public_generation_records_only_observed_dispatch(tmp_path, execute):
    from backend.cli.rtpeval import main

    times = iter(
        [
            datetime(2026, 10, 12, 1, tzinfo=UTC),
            datetime(2026, 10, 12, 2, tzinfo=UTC),
            datetime(2026, 10, 12, 3, tzinfo=UTC),
        ]
    )
    args = arguments(tmp_path, execute=execute)
    assert (
        main(
            ["generate", *args],
            runtime=Runtime(),
            date_provider=REFERENCE,
            clock=lambda: next(times),
        )
        == 0
    )
    metadata = json.loads((tmp_path / "capture/planner-dispatch.json").read_bytes())
    assert metadata["planner_dispatches"] == int(execute)
    assert metadata["dispatched"] is execute
    assert metadata["dispatched_at"] == ("2026-10-12T02:00:00+00:00" if execute else None)
    assert metadata["recorded_at"] == (
        "2026-10-12T03:00:00+00:00" if execute else "2026-10-12T01:00:00+00:00"
    )
    assert metadata["execution_metadata"] == (
        {"dispatch_mode": "awaited_single_invocation"} if execute else {}
    )
    assert metadata["run_id"] == "r"
    assert metadata["group_id"] == "g"
    assert metadata["version"] == "v0"
    import hashlib

    assert (
        metadata["input_sha256"]
        == hashlib.sha256((tmp_path / "input.json").read_bytes()).hexdigest()
    )
    assert (
        metadata["configuration_sha256"]
        == hashlib.sha256((tmp_path / "capture/runtime-policy.json").read_bytes()).hexdigest()
    )


def test_invalid_registration_reports_zero_dispatch_without_reading_clock(tmp_path, capsys):
    from backend.cli.rtpeval import main

    args = arguments(tmp_path, execute=True)
    selection = registration(tmp_path)
    (tmp_path / "staging").mkdir()
    assert (
        main(["generate", *args, *selection], clock=lambda: pytest.fail("clock reached dispatch"))
        == 2
    )
    value = json.loads(capsys.readouterr().out)
    assert value["planner"]["planner_dispatches"] == 0
    assert not (tmp_path / "capture").exists()
