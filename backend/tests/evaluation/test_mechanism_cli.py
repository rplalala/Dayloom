"""Offline researcher workflow through persisted public CLI artifacts."""

import json

import pytest

from backend.evaluation.mechanism_cli import main
from backend.tests.evaluation.test_intake import batch as selected_batch

batch = selected_batch


def test_help_exposes_source_preparation_and_mechanism_reporting(capsys):
    with pytest.raises(SystemExit) as exited:
        main(["--help"])
    assert exited.value.code == 0
    assert "{prepare,report}" in capsys.readouterr().out


def test_public_four_version_workflow(batch, tmp_path):
    _, _, write, _, _ = batch
    prepared, report = [tmp_path / name for name in ("prepared.json", "report.json")]
    assert main(["prepare", "--manifest", str(write()), "--output", str(prepared)]) == 0
    assert main(["report", str(prepared), "--output", str(report)]) == 0
    assert len(json.loads(report.read_text())["runs"]) == 4


def test_genuine_ticket11_v3_only_selection_does_not_invent_other_versions(tmp_path):
    from backend.evaluation.controlled_preparation import prepare_controlled_case
    from backend.tests.evaluation.test_controlled_preparation import requirements
    from backend.tests.evaluation.test_controlled_replay import case, replay

    value = case()
    selection = prepare_controlled_case(value, replay(value), requirements(value)).to_dict()
    source, prepared, report = [
        tmp_path / name for name in ("selection.json", "prepared.json", "report.json")
    ]
    source.write_text(json.dumps(selection), encoding="utf-8")
    assert main(["prepare", "--selection", str(source), "--output", str(prepared)]) == 0
    assert main(["report", str(prepared), "--output", str(report)]) == 0
    runs = json.loads(report.read_text())["runs"]
    assert len(runs) == 1 and runs[0]["version"] == "v3"
    assert runs[0]["coverage"] == "available"
    assert runs[0]["triggered"] is False and runs[0]["model_attempts"] == 0
