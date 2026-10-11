"""Offline external study integration at the installed suite command boundary."""

import hashlib
import json

import pytest

from backend.evaluation.human_report import build_human_report
from backend.evaluation.human_tasks import build_human_package, prepare_human_material
from backend.tests import test_rtpeval_suite_cli as suite_tests
from backend.tests.evaluation.test_human_answers import answer, bundle
from backend.tests.evaluation.test_human_tasks import config, review

installed_cli = suite_tests.installed_cli
suite_material = suite_tests.suite_material

pytest_plugins = ("backend.tests.evaluation.test_intake",)
STAMP = "2026-10-11T00:00:00Z"


def save(root, name, value):
    path = root / name
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")
    return {
        "path": name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "schema_version": value["schema_version"],
    }


def human(root, revision=1, *, missing=False):
    manifest = root / "first/manifest.json"
    cfg = config()
    package = build_human_package(manifest, cfg, review(prepare_human_material(manifest, cfg)))
    public, private = package["public"], package["private"]
    answers = [] if missing else [bundle(answer(public, revision=revision))]
    report = build_human_report(public, private, answers, generated_at=STAMP)
    prefix = f"human-{revision}"
    return {
        "report": save(root, prefix + "-report.json", report),
        "presentation": save(root, prefix + "-presentation.json", public),
        "mapping": save(root, prefix + "-mapping.json", private),
        "answers": [save(root, prefix + "-answers.json", answers[0])] if answers else [],
        "source_context": {
            "case_ids": ["first"],
            "rater_ref": public["rater_ref"],
            "source_hashes": private["preparation"]["source_hashes"],
        },
    }


def test_human_attachment_verifies_native_presentation_and_keeps_rater_population(
    suite_material, installed_cli
):
    source, directory, declaration = suite_material
    declaration["tracks"] = {"human": [human(source.parent)]}
    source.write_text(json.dumps(declaration), encoding="utf-8")
    result = installed_cli(
        "suite", "prepare", source, "--directory", directory, evaluation_offline=True
    )
    assert result.returncode == 0, result.stdout + result.stderr
    preparation = json.loads((directory / "preparation.json").read_bytes())
    study = preparation["track_configuration"]["external"]["human"][0]
    assert study["rater_ref"] == "3" * 32
    assert study["main_task_count"] == 1
    assert study["effective_revisions"][0]["answer_revision"] == 1
    assert study["evidence_status"] == "available"
    original = source.parent / declaration["tracks"]["human"][0]["report"]["path"]
    assert (directory / study["report"]).read_bytes() == original.read_bytes()


@pytest.mark.parametrize("fault", ["rater", "foreign_source", "stale_answers", "timestamp"])
def test_human_attachment_rejects_foreign_or_stale_bindings_before_outputs(
    suite_material, installed_cli, fault
):
    source, directory, declaration = suite_material
    attachment = human(source.parent)
    if fault == "rater":
        attachment["source_context"]["rater_ref"] = "foreign-rater"
    elif fault == "foreign_source":
        attachment["source_context"]["source_hashes"]["manifest"] = "0" * 64
    elif fault == "stale_answers":
        public = json.loads((source.parent / attachment["presentation"]["path"]).read_bytes())
        attachment["answers"] = [
            save(source.parent, "stale-answers.json", bundle(answer(public, revision=2)))
        ]
    else:
        report = json.loads((source.parent / attachment["report"]["path"]).read_bytes())
        report["generated_at"] = "2026-10-12T00:00:00Z"
        attachment["report"] = save(source.parent, "changed-timestamp.json", report)
    declaration["tracks"] = {"human": [attachment]}
    source.write_text(json.dumps(declaration), encoding="utf-8")
    result = installed_cli(
        "suite", "prepare", source, "--directory", directory, evaluation_offline=True
    )
    assert result.returncode == 2
    assert "Human" in json.loads(result.stdout)["reason"]
    assert not directory.exists()


def controlled_missing(root):
    from backend.evaluation.controlled_batch import build_controlled_batch

    manifest = {
        "schema_version": "rtpeval_controlled_batch_1",
        "batch_id": "study-independent",
        "revision": "1",
        "cases": [
            {
                "case_id": "experiment-target",
                "role": "target",
                "expected_goal_ids": ["goal-a"],
                "report": {
                    "path": "not-collected.json",
                    "sha256": "0" * 64,
                    "schema_version": "rtpeval_controlled_report_1",
                    "media_type": "application/json",
                    "availability": "unavailable",
                },
            }
        ],
    }
    report = build_controlled_batch(manifest, root, generated_at=STAMP)
    return {
        "report": save(root, "controlled-missing-report.json", report),
        "manifest": save(root, "controlled-missing-manifest.json", manifest),
        "source_context": {
            "population_id": "controlled-study-a",
            "batch_id": "study-independent",
            "revision": "1",
            "cases": [
                {
                    "case_id": "experiment-target",
                    "role": "target",
                    "expected_goal_ids": ["goal-a"],
                    "preparation_sha256": None,
                    "expectations_sha256": None,
                }
            ],
        },
    }


def test_missing_study_keeps_native_denominators_separate_from_primary_selection(
    suite_material, installed_cli
):
    source, directory, declaration = suite_material
    declaration["tracks"] = {
        "human": [human(source.parent, missing=True)],
        "controlled_repair": [controlled_missing(source.parent)],
    }
    source.write_text(json.dumps(declaration), encoding="utf-8")
    result = installed_cli(
        "suite", "prepare", source, "--directory", directory, evaluation_offline=True
    )
    assert result.returncode == 0, result.stdout + result.stderr
    prepared = json.loads((directory / "preparation.json").read_bytes())
    studies = prepared["track_configuration"]["external"]
    assert studies["human"][0]["missingness"]["preference"]["missing"] == 1
    assert studies["controlled_repair"][0]["counts"]["expected_cases"] == 1
    assert studies["controlled_repair"][0]["counts"]["expected_targets"] == 1
    assert studies["controlled_repair"][0]["counts"]["unavailable_cases"] == 1
    assert len(prepared["cases"]) == 3


def execute_fixture(source, directory, monkeypatch, capsys):
    import asyncio

    import httpx

    from backend.cli.rtpeval import main
    from backend.tests.evaluation.test_evaluation_run import mock_provider

    assert main(["suite", "prepare", str(source), "--directory", str(directory)]) == 0
    prepared = json.loads(capsys.readouterr().out)
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "synthetic-google")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "synthetic-model")
    client = httpx.AsyncClient(transport=httpx.MockTransport(mock_provider))
    try:
        assert (
            main(
                [
                    "suite",
                    "execute",
                    str(directory),
                    "--approved-sha256",
                    prepared["preparation_sha256"],
                ],
                http_client=client,
            )
            == 0
        )
    finally:
        asyncio.run(client.aclose())
    return json.loads(capsys.readouterr().out)


def test_later_human_revision_refresh_preserves_execution_and_replays_closed_lineage(
    suite_material, installed_cli, monkeypatch, capsys
):
    source, directory, declaration = suite_material
    declaration["tracks"] = {"human": [human(source.parent)]}
    source.write_text(json.dumps(declaration), encoding="utf-8")
    original = execute_fixture(source, directory, monkeypatch, capsys)
    preserved = {path: path.read_bytes() for path in directory.rglob("*") if path.is_file()}
    attachments = {
        "schema_version": "rtpeval_suite_attachments_1",
        "suite_id": "synthetic",
        "tracks": {"human": [human(source.parent, revision=2)]},
    }
    update = source.parent / "attachments.json"
    update.write_text(json.dumps(attachments), encoding="utf-8")
    result = installed_cli(
        "suite", "report", directory, "--attachments", update, evaluation_offline=True
    )
    assert result.returncode == 0, result.stdout + result.stderr
    refreshed = json.loads(result.stdout)
    assert refreshed["cases"] == original["cases"]
    assert (
        refreshed["tracks"]["human"]["studies"][0]["effective_revisions"][0]["answer_revision"] == 2
    )
    assert {path: path.read_bytes() for path in preserved} == preserved
    first_revision = {
        path: path.read_bytes()
        for path in (directory / "reports/0001").rglob("*")
        if path.is_file()
    }
    repeated = installed_cli("suite", "report", directory, evaluation_offline=True)
    assert repeated.returncode == 0, repeated.stdout + repeated.stderr
    assert json.loads(repeated.stdout)["tracks"] == refreshed["tracks"]
    assert {path: path.read_bytes() for path in first_revision} == first_revision
    replay = installed_cli("suite", "replay", directory, evaluation_offline=True)
    assert replay.returncode == 0, replay.stdout + replay.stderr
    assert json.loads(replay.stdout)["tracks"] == refreshed["tracks"]
    # A new report with a dishonest binding must leave every prior artifact intact.
    before_invalid = {path: path.read_bytes() for path in directory.rglob("*") if path.is_file()}
    attachments["tracks"]["human"][0]["source_context"]["rater_ref"] = "other"
    invalid = source.parent / "invalid-attachments.json"
    invalid.write_text(json.dumps(attachments), encoding="utf-8")
    denied = installed_cli(
        "suite", "report", directory, "--attachments", invalid, evaluation_offline=True
    )
    assert denied.returncode == 2
    assert {
        path: path.read_bytes() for path in directory.rglob("*") if path.is_file()
    } == before_invalid
    # Corrupt closed refresh dependency bytes cannot be hidden by a valid execution receipt.
    copied = directory / refreshed["tracks"]["human"]["studies"][0]["report"]
    copied.write_bytes(copied.read_bytes() + b" ")
    corrupted = installed_cli("suite", "replay", directory, evaluation_offline=True)
    assert corrupted.returncode == 2
    assert json.loads(corrupted.stdout)["processing_status"] == "needs_material_correction"


@pytest.fixture
def refresh_cli(installed_cli, tmp_path):
    # Import denial is a process boundary guard: refresh must not even load
    # primary scoring or independently executed controlled-study code.
    guard = tmp_path / "guard/sitecustomize.py"
    with guard.open("a", encoding="utf-8") as stream:
        stream.write(
            '\nforbidden += ("backend.evaluation.quality_report", '
            '"backend.evaluation.controlled_replay", '
            '"backend.evaluation.controlled_report")\n'
        )
    return installed_cli


def test_refresh_with_no_new_attachment_never_loads_primary_or_controlled_scoring(
    suite_material, refresh_cli, monkeypatch, capsys
):
    source, directory, _ = suite_material
    original = execute_fixture(source, directory, monkeypatch, capsys)
    result = refresh_cli("suite", "report", directory, evaluation_offline=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout) == original


@pytest.mark.parametrize("fault", ["inventory", "population", "corrupt_case"])
def test_controlled_attachment_rejects_supplied_foreign_or_corrupt_population(
    suite_material, installed_cli, fault
):
    source, directory, declaration = suite_material
    attachment = controlled_missing(source.parent)
    if fault == "inventory":
        attachment["source_context"]["cases"][0]["expected_goal_ids"] = ["other-goal"]
    elif fault == "population":
        attachment["source_context"]["batch_id"] = "other-study"
    else:
        manifest = json.loads((source.parent / attachment["manifest"]["path"]).read_bytes())
        ref = manifest["cases"][0]["report"]
        ref["availability"] = "available"
        ref["path"] = "corrupt-controlled.json"
        (source.parent / ref["path"]).write_text("{}", encoding="utf-8")
        attachment["manifest"] = save(source.parent, "corrupt-manifest.json", manifest)
    declaration["tracks"] = {"controlled_repair": [attachment]}
    source.write_text(json.dumps(declaration), encoding="utf-8")
    result = installed_cli(
        "suite", "prepare", source, "--directory", directory, evaluation_offline=True
    )
    assert result.returncode == 2
    assert not directory.exists()


def test_refresh_receipt_cannot_hide_forged_parent_lineage(
    suite_material, installed_cli, monkeypatch, capsys
):
    source, directory, _ = suite_material
    execute_fixture(source, directory, monkeypatch, capsys)
    result = installed_cli("suite", "report", directory, evaluation_offline=True)
    assert result.returncode == 0
    revision = directory / "reports/0001"
    lineage = json.loads((revision / "lineage.json").read_bytes())
    lineage["parent_summary_sha256"] = "0" * 64
    (revision / "lineage.json").write_text(json.dumps(lineage), encoding="utf-8")
    receipt = json.loads((revision / "receipt.json").read_bytes())
    receipt["files"]["lineage.json"] = hashlib.sha256(
        (revision / "lineage.json").read_bytes()
    ).hexdigest()
    (revision / "receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
    replay = installed_cli("suite", "replay", directory, evaluation_offline=True)
    assert replay.returncode == 2
    assert "lineage mismatch" in json.loads(replay.stdout)["reason"]


def controlled_complete(root):
    """Create a separately completed native synthetic study before suite operations."""
    from backend.evaluation.controlled_batch import build_controlled_batch
    from backend.evaluation.controlled_preparation import prepare_controlled_case
    from backend.evaluation.controlled_report import build_controlled_report
    from backend.evaluation.records import canonical_digest
    from backend.tests.evaluation.controlled_fixtures import expectations, material
    from backend.tests.evaluation.test_controlled_replay import case, replay

    value = case()
    execution = replay(value)
    native = material(value, execution, root / "controlled-snapshot")
    goals = expectations(value, execution)
    prepared = prepare_controlled_case(value, execution, native["requirement_spec"]).to_dict()
    individual = build_controlled_report(value, execution, goals, **native, generated_at=STAMP)
    assert individual["status"] == "complete", individual["diagnostics"]
    individual_ref = save(root, "controlled-individual.json", individual)
    individual_ref.update(media_type="application/json", availability="available")
    manifest = {
        "schema_version": "rtpeval_controlled_batch_1",
        "batch_id": "complete-study",
        "revision": "1",
        "cases": [
            {
                "case_id": value["case_id"],
                "role": "control",
                "expected_goal_ids": [],
                "report": individual_ref,
            }
        ],
    }
    report = build_controlled_batch(manifest, root, generated_at=STAMP)
    return {
        "report": save(root, "controlled-complete-report.json", report),
        "manifest": save(root, "controlled-complete-manifest.json", manifest),
        "source_context": {
            "population_id": "controlled-study-b",
            "batch_id": "complete-study",
            "revision": "1",
            "cases": [
                {
                    "case_id": value["case_id"],
                    "role": "control",
                    "expected_goal_ids": [],
                    "preparation_sha256": canonical_digest(prepared),
                    "expectations_sha256": canonical_digest(goals),
                    "preparation": save(root, "controlled-preparation.json", prepared),
                    "expectations": save(root, "controlled-expectations.json", goals),
                }
            ],
        },
    }


def test_valid_controlled_report_keeps_independent_case_preparation_and_goals(
    suite_material, installed_cli
):
    source, directory, declaration = suite_material
    declaration["tracks"] = {"controlled_repair": [controlled_complete(source.parent)]}
    source.write_text(json.dumps(declaration), encoding="utf-8")
    result = installed_cli(
        "suite", "prepare", source, "--directory", directory, evaluation_offline=True
    )
    assert result.returncode == 0, result.stdout + result.stderr
    prepared = json.loads((directory / "preparation.json").read_bytes())
    study = prepared["track_configuration"]["external"]["controlled_repair"][0]
    assert study["evidence_status"] == "available"
    assert study["counts"]["expected_cases"] == 1
    assert study["counts"]["control_cases"] == 1
    assert study["counts"]["unavailable_cases"] == 0
    assert study["case_inventory"][0]["case_id"] == "synthetic-control"
    assert len(prepared["cases"]) == 3


def test_controlled_report_rejects_self_consistent_foreign_preparation(
    suite_material, installed_cli
):
    from backend.evaluation.records import canonical_digest

    source, directory, declaration = suite_material
    attachment = controlled_complete(source.parent)
    row = attachment["source_context"]["cases"][0]
    preparation = json.loads((source.parent / row["preparation"]["path"]).read_bytes())
    preparation["source_hashes"]["case"] = "0" * 64
    row["preparation"] = save(source.parent, "foreign-controlled-preparation.json", preparation)
    row["preparation_sha256"] = canonical_digest(preparation)
    declaration["tracks"] = {"controlled_repair": [attachment]}
    source.write_text(json.dumps(declaration), encoding="utf-8")
    result = installed_cli(
        "suite", "prepare", source, "--directory", directory, evaluation_offline=True
    )
    assert result.returncode == 2
    assert "preparation source binding" in json.loads(result.stdout)["reason"]
    assert not directory.exists()


def test_human_attachment_refresh_runs_with_primary_and_study_execution_imports_denied(
    suite_material, refresh_cli, monkeypatch, capsys
):
    source, directory, _ = suite_material
    original = execute_fixture(source, directory, monkeypatch, capsys)
    update = source.parent / "guarded-attachments.json"
    update.write_text(
        json.dumps(
            {
                "schema_version": "rtpeval_suite_attachments_1",
                "suite_id": "synthetic",
                "tracks": {"human": [human(source.parent)]},
            }
        ),
        encoding="utf-8",
    )
    result = refresh_cli(
        "suite", "report", directory, "--attachments", update, evaluation_offline=True
    )
    assert result.returncode == 0, result.stdout + result.stderr
    refreshed = json.loads(result.stdout)
    assert refreshed["cases"] == original["cases"]
    assert refreshed["tracks"]["human"]["studies"][0]["rater_ref"] == "3" * 32


@pytest.mark.parametrize("kind", ["human_mapping", "controlled_inventory"])
def test_malformed_attachment_structure_is_actionable_material_correction(
    suite_material, installed_cli, kind
):
    source, directory, declaration = suite_material
    if kind == "human_mapping":
        attachment = human(source.parent)
        mapping = json.loads((source.parent / attachment["mapping"]["path"]).read_bytes())
        mapping["preparation"] = []
        attachment["mapping"] = save(source.parent, "malformed-mapping.json", mapping)
        declaration["tracks"] = {"human": [attachment]}
    else:
        attachment = controlled_missing(source.parent)
        manifest = json.loads((source.parent / attachment["manifest"]["path"]).read_bytes())
        manifest["cases"] = ["invalid-case"]
        attachment["manifest"] = save(source.parent, "malformed-controlled-manifest.json", manifest)
        declaration["tracks"] = {"controlled_repair": [attachment]}
    source.write_text(json.dumps(declaration), encoding="utf-8")
    result = installed_cli(
        "suite", "prepare", source, "--directory", directory, evaluation_offline=True
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert json.loads(result.stdout)["processing_status"] == "needs_material_correction"
    assert not directory.exists()
