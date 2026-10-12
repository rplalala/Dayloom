"""Source-bound census export at the installed, offline process seam."""

import copy
import json

import pytest

from backend.tests.test_rtpeval_cli import installed_cli as cli_fixture
from backend.tests.test_rtpeval_research_population_cli import add_attempt, save
from backend.tests.test_rtpeval_research_population_cli import (
    research_material as research_fixture,
)

installed_cli = cli_fixture
research_material = research_fixture


def inventory(material):
    root, _, _, census, write = material
    declaration = json.loads(write().read_bytes())
    entries = []
    for original in census["attempts"]:
        row = copy.deepcopy(original)
        metadata = {
            "schema_version": "rtpeval_planner_dispatch_1",
            "source_kind": "historical_import",
            "declared_by": "synthetic-operator",
            "recorded_at": "2026-10-03T00:00:00Z",
            "group_id": "synthetic-group",
            **{
                k: row.pop(k)
                for k in (
                    "dispatched",
                    "dispatched_at",
                    "input_sha256",
                    "configuration_sha256",
                    "execution_metadata",
                )
            },
            "run_id": row["run_id"],
            "version": row["version"],
        }
        metadata["planner_dispatches"] = int(metadata["dispatched"])
        metadata["evidence_refs"] = [
            save(
                root,
                row["attempt_id"] + "-trace.json",
                {
                    "run_id": row["run_id"],
                    "event": "explicit dispatch observation",
                },
            )
        ]
        row["group_id"] = metadata["group_id"]
        row["producer_metadata_ref"] = save(root, row["attempt_id"] + "-metadata.json", metadata)
        entries.append(row)
    request = {
        "schema_version": "rtpeval_research_census_export_1",
        "population_ref": declaration["population_ref"],
        "profile_ref": declaration["profile_ref"],
        "attempt_sources": entries,
    }
    save(root, "export-input.json", request)
    return root / "export-input.json", request


def test_installed_export_preserves_primary_retry_and_original_bytes(
    installed_cli, research_material, tmp_path
):
    root, population, profile, _, _ = research_material
    population["cases"] = population["cases"][:1]
    population["cases"][0]["planned_versions"] = ["v1", "v3"]
    profile["retry_rule"]["selection"] = "last_dispatched"
    failure = add_attempt(research_material, 0, "v1", "failed")
    retry = add_attempt(research_material, 0, "v1", "completed", order=2)
    add_attempt(research_material, 0, "v3", "cancelled")
    source, _ = inventory(research_material)
    originals = {path: path.read_bytes() for path in root.rglob("*") if path.is_file()}
    destination = tmp_path / "exported"
    exported = installed_cli("research", "export-census", source, "--directory", destination)
    assert exported.returncode == 0, exported.stdout + exported.stderr
    receipt = json.loads(exported.stdout)
    assert receipt["processing_status"] == "completed"
    declaration = destination / receipt["declaration_ref"]["path"]
    assert (
        installed_cli("research", "validate", declaration, "--track", "population").returncode == 0
    )
    report_dir = tmp_path / "report"
    report = installed_cli(
        "research", "report", declaration, "--track", "population", "--directory", report_dir
    )
    assert report.returncode == 0, report.stdout + report.stderr
    value = json.loads((report_dir / "population.json").read_bytes())
    assert value["population"]["planned_slots"] == 2
    assert value["summary"]["attempt_census"]["records"] == 3
    assert value["slots"][0]["primary_attempt"]["attempt_id"] == failure["attempt_id"]
    assert value["slots"][0]["retry_outcome"]["attempt_id"] == retry["attempt_id"]
    assert value["summary"]["status_counts"]["cancelled"] == 1
    assert originals == {path: path.read_bytes() for path in originals}
    for binding in receipt["source_bindings"]:
        assert (destination / "material" / binding["path"]).read_bytes() == (
            root / binding["path"]
        ).read_bytes()


def test_distinct_population_preserves_all_states_and_missing_slot(
    installed_cli, research_material, tmp_path
):
    root, population, _, _, _ = research_material
    population["population_id"] = "different-geography"
    population["revision"] = "population-7"
    profile = research_material[2]
    profile.update(
        population_id=population["population_id"], population_revision=population["revision"]
    )
    census = research_material[3]
    census.update(
        population_id=population["population_id"], population_revision=population["revision"]
    )
    population["cases"] = population["cases"][:2]
    first, second = population["cases"]
    first.update(
        case_id="harbor-request",
        revision="input-7",
        planned_versions=["v0", "v2", "v3"],
        repetition_ids=["weekday", "weekend"],
    )
    second.update(case_id="coastal-request", planned_versions=["v1"], repetition_ids=["solo"])
    second["input_ref"] = save(root, "different-request.json", {"destination": "Melbourne"})
    for version, status in zip(
        ["v0", "v2", "v3"], ["completed", "failed", "cancelled"], strict=True
    ):
        add_attempt(research_material, 0, version, status, repetition="weekday")
    for version, status in zip(
        ["v0", "v2", "v3"], ["clarification_required", "pending", "not_started"], strict=True
    ):
        add_attempt(
            research_material,
            0,
            version,
            status,
            repetition="weekend",
            dispatched=status != "not_started",
        )
    source, request = inventory(research_material)
    request["attempt_sources"][0]["result_ref"] = {
        "availability": "unavailable",
        "sha256": None,
        "reason": "not_adopted",
    }
    save(root, "export-input.json", request)
    destination = tmp_path / "other-export"
    exported = installed_cli("research", "export-census", source, "--directory", destination)
    assert exported.returncode == 0, exported.stdout + exported.stderr
    receipt = json.loads(exported.stdout)
    assert receipt["attempts"] == 6
    assert receipt["planned_slots"] == 7
    assert receipt["missing_slots"] == 1
    assert any(d["reason"] == "not_adopted" for d in receipt["diagnostics"])
    report_dir = tmp_path / "other-report"
    result = installed_cli(
        "research",
        "report",
        destination / receipt["declaration_ref"]["path"],
        "--track",
        "population",
        "--directory",
        report_dir,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    value = json.loads((report_dir / "population.json").read_bytes())
    assert value["summary"]["status_counts"] == {
        "completed": 1,
        "failed": 1,
        "cancelled": 1,
        "clarification_required": 1,
        "incomplete": 0,
        "unstarted": 1,
        "unknown_pending": 2,
    }
    assert value["summary"]["attempt_census"]["dispatched"] == 5
    assert value["slots"][-1]["attempts"] == []
    assert value["slots"][-1]["reason_type"] == "missing_census_record"
    assert value["all_four"]["completion"]["denominator"] == 0


@pytest.mark.parametrize(
    "fault",
    [
        "missing_metadata",
        "missing_dispatch_time",
        "duplicate_attempt",
        "duplicate_run",
        "order",
        "predecessor",
        "foreign_case",
        "foreign_revision",
        "foreign_repetition",
        "foreign_run",
        "foreign_group",
        "foreign_version",
        "input_binding",
        "config_binding",
        "recorded_before_dispatch",
        "completion_before_dispatch",
        "no_historical_evidence",
        "stale_source",
        "unsafe_path",
        "non_dispatch_time",
        "existing_destination",
    ],
)
def test_invalid_export_has_no_successful_bundle(installed_cli, research_material, tmp_path, fault):
    root, population, _, _, _ = research_material
    population["cases"] = population["cases"][:1]
    add_attempt(research_material, 0, "v0", "failed")
    add_attempt(research_material, 0, "v0", "completed", order=2)
    source, request = inventory(research_material)
    first, second = request["attempt_sources"]
    metadata_ref = first["producer_metadata_ref"]
    metadata = json.loads((root / metadata_ref["path"]).read_bytes())
    if fault == "missing_metadata":
        first.pop("producer_metadata_ref")
    elif fault == "duplicate_attempt":
        second["attempt_id"] = first["attempt_id"]
    elif fault == "duplicate_run":
        second["run_id"] = first["run_id"]
        ref = second["producer_metadata_ref"]
        value = json.loads((root / ref["path"]).read_bytes())
        value["run_id"] = first["run_id"]
        second["producer_metadata_ref"] = save(root, ref["path"], value)
    elif fault == "order":
        first["order"] = 2
    elif fault == "predecessor":
        second["prior_attempt_id"] = "missing-predecessor"
    elif fault in ("foreign_case", "foreign_revision", "foreign_repetition"):
        first[
            {
                "foreign_case": "case_id",
                "foreign_revision": "case_revision",
                "foreign_repetition": "repetition_id",
            }[fault]
        ] = "foreign"
    elif fault in ("foreign_run", "foreign_group", "foreign_version"):
        metadata[
            {"foreign_run": "run_id", "foreign_group": "group_id", "foreign_version": "version"}[
                fault
            ]
        ] = "foreign"
    elif fault in ("input_binding", "config_binding"):
        metadata["input_sha256" if fault == "input_binding" else "configuration_sha256"] = "0" * 64
    elif fault == "missing_dispatch_time":
        metadata["dispatched_at"] = None
    elif fault == "recorded_before_dispatch":
        metadata["recorded_at"] = "2026-10-01T00:00:00Z"
    elif fault == "non_dispatch_time":
        metadata.update(dispatched=False, planner_dispatches=0)
    elif fault == "no_historical_evidence":
        metadata["evidence_refs"] = []
    elif fault == "completion_before_dispatch":
        ref = first["completion_ref"]
        value = json.loads((root / ref["path"]).read_bytes())
        value["declared_at"] = "2026-10-01T00:00:00Z"
        first["completion_ref"] = save(root, ref["path"], value)
    elif fault == "unsafe_path":
        request["population_ref"]["path"] = "../escape.json"
    if fault not in ("missing_metadata", "stale_source"):
        first["producer_metadata_ref"] = save(root, metadata_ref["path"], metadata)
    save(root, "export-input.json", request)
    if fault == "stale_source":
        (root / metadata_ref["path"]).write_text("{}", encoding="utf-8")
    destination = tmp_path / "rejected"
    if fault == "existing_destination":
        destination.mkdir()
        (destination / "keep.txt").write_bytes(b"prior output")
    exported = installed_cli("research", "export-census", source, "--directory", destination)
    assert exported.returncode == 2, exported.stdout + exported.stderr
    assert json.loads(exported.stdout)["processing_status"] == "needs_material_correction"
    assert json.loads(exported.stdout)["diagnostics"]
    assert not (destination / "export.json").exists()
    assert not (destination / "material/research-export.json").exists()
    if fault == "existing_destination":
        assert (destination / "keep.txt").read_bytes() == b"prior output"
    else:
        assert not destination.exists()


@pytest.mark.parametrize(
    "execute,outcome", [(False, None), (True, "cancelled"), (True, "completed")]
)
def test_future_native_dispatch_evidence_exports_without_metadata_inference(
    installed_cli, research_material, tmp_path, execute, outcome
):
    from backend.tests.test_rtpeval_generate_cancellation import BOOTSTRAP, source_ref
    from backend.tests.test_rtpeval_generate_cli import arguments, registration

    root, population, profile, _, write = research_material
    args = arguments(root, execute=execute)
    generated = installed_cli(
        "generate",
        *args,
        *(registration(root) if execute else []),
        tools_offline=True,
        bootstrap=BOOTSTRAP.replace("InterruptedRuntime", "Runtime")
        if outcome == "completed"
        else BOOTSTRAP,
    )
    assert generated.returncode == int(outcome == "cancelled"), generated.stdout + generated.stderr
    population["cases"] = population["cases"][:1]
    case = population["cases"][0]
    case.update(
        case_id="actual-native-request", planned_versions=["v0"], repetition_ids=["native-repeat"]
    )
    case["input_ref"] = source_ref(root, root / "input.json")
    profile["configurations"]["v0"] = source_ref(root, root / "capture/runtime-policy.json")
    declaration = json.loads(write().read_bytes())
    entry = {
        "case_id": case["case_id"],
        "case_revision": case["revision"],
        "version": "v0",
        "repetition_id": "native-repeat",
        "attempt_id": "native-attempt",
        "order": 1,
        "prior_attempt_id": None,
        "run_id": "r",
        "group_id": "g",
        "reason_type": "native_observation",
        "producer_metadata_ref": source_ref(root, root / "capture/planner-dispatch.json"),
    }
    if execute:
        entry["completion_ref"] = source_ref(root, root / "capture/producer-completion.json")
        entry["usage_ref"] = source_ref(root, root / "capture/usage.json")
        if outcome == "completed":
            entry["result_ref"] = source_ref(root, root / "capture/result.json")
            entry["provenance_ref"] = source_ref(root, root / "capture/provenance.json")
    request = {
        "schema_version": "rtpeval_research_census_export_1",
        "population_ref": declaration["population_ref"],
        "profile_ref": declaration["profile_ref"],
        "attempt_sources": [entry],
    }
    source = root / "native-export.json"
    save(root, source.name, request)
    result = installed_cli(
        "research", "export-census", source, "--directory", tmp_path / "native-bundle"
    )
    assert result.returncode == 0, result.stdout + result.stderr
    census = json.loads((tmp_path / "native-bundle/material/census-export.json").read_bytes())
    if execute:
        completion = json.loads((root / "capture/producer-completion.json").read_bytes())
        for field in ("operator_selection_ref", "operator_config_ref"):
            ref = completion[field]
            original = (root / "capture" / ref["path"]).resolve()
            copied = tmp_path / "native-bundle/material" / original.relative_to(root)
            assert copied.read_bytes() == original.read_bytes()
    row = census["attempts"][0]
    metadata = json.loads((root / "capture/planner-dispatch.json").read_bytes())
    assert row["dispatched_at"] == metadata["dispatched_at"]
    assert row["dispatched"] is execute
    report_dir = tmp_path / "native-report"
    declaration_path = tmp_path / "native-bundle/material/research-export.json"
    report = installed_cli(
        "research", "report", declaration_path, "--track", "population", "--directory", report_dir
    )
    assert report.returncode == 0, report.stdout + report.stderr
    population_report = json.loads((report_dir / "population.json").read_bytes())
    assert (
        population_report["summary"]["status_counts"][outcome if execute else "unknown_pending"]
        == 1
    )
    assert population_report["summary"]["attempt_census"]["dispatched"] == int(execute)


def test_export_help_is_offline_and_explains_historical_requirements(installed_cli):
    result = installed_cli("research", "export-census", "--help")
    assert result.returncode == 0
    for text in (
        "inventory",
        "--directory",
        "fresh",
        "Historical",
        "dispatch metadata",
        "no Planner/evaluator",
    ):
        assert text in result.stdout


@pytest.mark.parametrize("kind", ["cases", "configurations", "history"])
def test_malformed_source_structures_return_correction_diagnostics(
    installed_cli, research_material, tmp_path, kind
):
    root, population, profile, _, _ = research_material
    source, _ = inventory(research_material)
    if kind == "cases":
        population["cases"] = ["invalid-case"]
        save(root, "population.json", population)
    elif kind == "configurations":
        profile["configurations"] = []
        save(root, "profile.json", profile)
    else:
        profile["previous_profile_ref"] = []
        save(root, "profile.json", profile)
    request = json.loads(source.read_bytes())
    request["population_ref"] = save(root, "population.json", population)
    request["profile_ref"] = save(root, "profile.json", profile)
    save(root, source.name, request)
    result = installed_cli(
        "research", "export-census", source, "--directory", tmp_path / "bad-shape"
    )
    assert result.returncode == 2
    assert json.loads(result.stdout)["diagnostics"]
    assert not (tmp_path / "bad-shape").exists()


def test_fresh_export_succeeds_when_directory_rename_is_unavailable(
    installed_cli, research_material, tmp_path
):
    source, _ = inventory(research_material)
    result = installed_cli(
        "research",
        "export-census",
        source,
        "--directory",
        tmp_path / "rename-denied",
        bootstrap="""
from pathlib import Path
def unavailable_rename(*args, **kwargs):
    raise PermissionError('Synthetic directory rename denied')
Path.rename = unavailable_rename
""",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)["processing_status"] == "completed"


def test_failed_publication_never_has_a_completed_receipt(
    installed_cli, research_material, tmp_path
):
    source, _ = inventory(research_material)
    destination = tmp_path / "interrupted-publication"
    result = installed_cli(
        "research",
        "export-census",
        source,
        "--directory",
        destination,
        bootstrap="""
from pathlib import Path
original_write = Path.write_bytes
def interrupted_write(path, data):
    if path.name == 'export.json':
        original_write(path, b'{"processing_status":')
        raise OSError('Synthetic interrupted receipt write')
    return original_write(path, data)
Path.write_bytes = interrupted_write
""",
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert json.loads(result.stdout)["processing_status"] == "needs_material_correction"
    receipt = destination / "export.json"
    if receipt.exists():
        with pytest.raises(json.JSONDecodeError):
            json.loads(receipt.read_bytes())
