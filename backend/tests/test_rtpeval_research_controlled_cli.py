"""Controlled inventory and preservation through offline research CLI."""

import json

import pytest

from backend.evaluation.controlled_report import build_controlled_report
from backend.tests import test_rtpeval_research_population_cli as population_tests
from backend.tests.evaluation.controlled_fixtures import expectations, material
from backend.tests.evaluation.test_controlled_replay import case, replay, scripted
from backend.tests.research_native_fixtures import file_ref
from backend.tests.versions.v3.test_b_targets import edit, visit
from backend.tests.versions.v3.test_validation import DAY

research_material = population_tests.research_material
save = population_tests.save
pytest_plugins = ("backend.tests.test_rtpeval_cli",)


def descriptor(root, value, execution, goals, package):
    report = build_controlled_report(
        value, execution, goals, **package, generated_at="2026-10-04T00:00:00Z"
    )
    assert report["status"] == "complete", report["diagnostics"]
    base = value["case_id"]
    options = {name: option for name, option in package.items() if name != "snapshot_directory"}
    return {
        "case_ref": save(root, base + "-case.json", value),
        "execution_ref": save(root, base + "-execution.json", execution),
        "expectations_ref": save(root, base + "-expectations.json", goals),
        "report_ref": save(root, base + "-report.json", report),
        "snapshot_ref": file_ref(root, package["snapshot_directory"] / "manifest.json"),
        **{
            name + "_ref": save(root, base + "-" + name + ".json", option)
            for name, option in options.items()
        },
    }


def controlled_entry(value, goals, sources):
    return {
        "case_id": value["case_id"],
        "revision": value["revision"],
        "role": value["role"],
        "expected_goal_ids": [goal["goal_id"] for goal in goals["targets"]],
        "expected_guard_ids": [goal["goal_id"] for goal in goals["guards"]],
        "expectations_sha256": sources["expectations_ref"]["sha256"],
        "descriptor": sources,
    }


def declared_controlled(research_material, *, uncertain=False, reviewed=False, regress=False):
    root, _, _, _, write = research_material
    value = case(
        [[visit("a", "a", start="10:00", end="11:00"), visit("b", "b", start="10:30", end="11:30")]]
    )
    value.update(case_id="target-case", role="target")
    value = scripted(
        value,
        {
            "edits": [
                edit(
                    "retime",
                    "b",
                    start="20:00" if regress else "11:30",
                    end="21:00" if regress else "12:30",
                )
            ]
        },
    )
    execution = replay(value)
    package = material(
        value,
        execution,
        root / "target-snapshot",
        hours={"regularOpeningHours": {}} if uncertain else None,
    )
    if regress:
        package = material(
            value,
            execution,
            root / "regression-snapshot",
            hours={
                "regularOpeningHours": {
                    "periods": [
                        {
                            "open": {"day": DAY.isoweekday() % 7, "hour": 8, "minute": 0},
                            "close": {"day": DAY.isoweekday() % 7, "hour": 18, "minute": 0},
                        }
                    ]
                }
            },
        )
    goals = expectations(
        value,
        execution,
        targets=[
            {
                "goal_id": "overlap",
                "basis": "confirmed_conflict",
                "detector": {"check": "overlap", "activity_ids": ["a", "b"]},
                "condition": {
                    "kind": "check",
                    "dimension": "conflicts",
                    "activity_ids": ["a", "b"],
                },
            },
            {
                "goal_id": "count",
                "basis": "review_opportunity",
                "detector": {"check": "missing-count-detector"},
                "condition": {"kind": "daily_count", "date": str(DAY), "minimum": 3},
            },
        ],
        guards=[
            {
                "goal_id": "hours",
                "basis": "product_policy",
                "condition": {"kind": "check", "dimension": "opening", "activity_ids": ["a"]},
            }
        ],
    )
    if reviewed:
        from copy import deepcopy

        from backend.tests.evaluation.test_controlled_report import opening_review

        facts = opening_review(value, execution)
        other = deepcopy(facts["opening"][0])
        other["canonical_place_id"] = "b"
        facts["opening"].append(other)
        package["factual_reviews"] = facts
    target = controlled_entry(value, goals, descriptor(root, value, execution, goals, package))
    control = case()
    control["case_id"] = "control-case"
    control_execution = replay(control)
    control_goals = expectations(control, control_execution)
    control_package = material(control, control_execution, root / "control-snapshot")
    control_row = controlled_entry(
        control,
        control_goals,
        descriptor(root, control, control_execution, control_goals, control_package),
    )
    missing = {
        "case_id": "missing-case",
        "revision": "1",
        "role": "target",
        "expected_goal_ids": ["missing"],
        "expected_guard_ids": [],
        "expectations_sha256": None,
        "descriptor": None,
    }
    study = {"study_id": "declared-study", "revision": "1", "cases": [target, missing, control_row]}
    declaration = write()
    value = json.loads(declaration.read_bytes())
    repair = {
        "schema_version": "rtpeval_research_repair_1",
        "population_id": "original-requests",
        "population_revision": "r1",
        "profile_id": "fixed-selection",
        "profile_revision": "p1",
        "controlled": study,
    }
    value["track_refs"]["repair"] = save(root, "repair-material.json", repair)
    save(root, "research.json", value)
    return declaration, study


@pytest.mark.parametrize("uncertain,preservation", [(False, "preserved"), (True, "unknown")])
def test_controlled_missing_and_multiple_targets_guard_uncertainty_are_separate(
    installed_cli, research_material, tmp_path, uncertain, preservation
):
    declaration, _ = declared_controlled(research_material, uncertain=uncertain)
    result = installed_cli(
        "research",
        "report",
        declaration,
        "--track",
        "repair",
        "--directory",
        tmp_path / "controlled-out",
        tools_offline=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads((tmp_path / "controlled-out" / "repair.json").read_text())
    controlled = report["controlled"]
    assert controlled["resolution"] == {
        "numerator": 1,
        "denominator": 3,
        "unit": "expected_targets",
        "fraction": 1 / 3,
    }
    assert controlled["verdict_coverage"]["available"] == 2
    assert controlled["verdict_coverage"]["expected"] == 3
    assert controlled["targets"][0]["preservation"] == preservation
    assert controlled["targets"][1]["native"]["detection"] == "missed"
    assert controlled["targets"][1]["native"]["independent_outcome"] == "residual"
    assert controlled["targets"][2]["native"] is None
    assert controlled["controls"][0]["native"]["control"]["outcome"] == "valid_no_change"
    assert controlled["case_joint_success"]["numerator"] == 0
    assert controlled["case_joint_success"]["denominator"] == 2
    assert report["same_run"]["summary"]["expected_slots"] == 20
    text = (tmp_path / "controlled-out" / "repair.md").read_text()
    assert "Independent target resolution: 1/3" in text
    assert "Joint target-case success: 0/2" in text
    channels = controlled["observational_channels"]
    assert channels["detection"]["denominator"] == 2
    assert channels["authorization"]["denominator"] == 1
    assert channels["model_attempt"]["denominator"] == 1
    assert channels["adoption"]["denominator"] == 1


@pytest.mark.parametrize(
    "fault", ["guard_inventory", "extra_target", "foreign_case", "forged_outcome", "snapshot"]
)
def test_invalid_controlled_source_or_undeclared_units_fail_atomically(
    installed_cli, research_material, tmp_path, fault
):
    from backend.evaluation.records import canonical_digest

    declaration, study = declared_controlled(research_material)
    root = declaration.parent
    entry = study["cases"][0]
    source = entry["descriptor"]
    if fault == "guard_inventory":
        entry["expected_guard_ids"] = []
    elif fault == "extra_target":
        entry["expected_goal_ids"].append("undeclared")
    elif fault == "foreign_case":
        entry["revision"] = "foreign"
    elif fault == "forged_outcome":
        report = json.loads((root / source["report_ref"]["path"]).read_bytes())
        report["targets"][1]["independent_outcome"] = "resolved"
        report["content_hash"] = canonical_digest(
            {k: v for k, v in report.items() if k not in {"generated_at", "content_hash"}}
        )
        source["report_ref"] = save(root, "forged-controlled.json", report)
    else:
        snapshot_path = root / source["snapshot_ref"]["path"]
        snapshot = json.loads(snapshot_path.read_bytes())
        raw = next(a["raw"] for row in snapshot["records"] for a in row["attempts"] if a["raw"])
        (snapshot_path.parent / raw["path"]).write_bytes(b"corrupt response")
    decl = json.loads(declaration.read_bytes())
    repair = json.loads((root / decl["track_refs"]["repair"]["path"]).read_bytes())
    repair["controlled"] = study
    decl["track_refs"]["repair"] = save(root, "repair-material.json", repair)
    save(root, "research.json", decl)
    output = tmp_path / "invalid-controlled-out"
    result = installed_cli(
        "research",
        "report",
        declaration,
        "--track",
        "repair",
        "--directory",
        output,
        tools_offline=True,
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert not output.exists()
    assert json.loads(result.stdout)["processing_status"] == "needs_material_correction"


def test_reviewed_continuity_can_preserve_resolution_while_raw_checks_remain_unknown(
    installed_cli, research_material, tmp_path
):
    declaration, _ = declared_controlled(research_material, uncertain=True, reviewed=True)
    result = installed_cli(
        "research",
        "report",
        declaration,
        "--track",
        "repair",
        "--directory",
        tmp_path / "reviewed-out",
        tools_offline=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads((tmp_path / "reviewed-out" / "repair.json").read_bytes())
    controlled = report["controlled"]
    assert controlled["targets"][0]["preservation"] == "preserved"
    native = controlled["cases"][0]["native"]
    assert (
        native["pair"]["stages"]["final_primary"]["primary_metrics"]["opening"]["checks"][0][
            "state"
        ]
        == "UNKNOWN"
    )
    assert (
        native["reviewed_checks"]["stages"]["final_primary"]["primary_metrics"]["opening"][
            "checks"
        ][0]["state"]
        == "PASS"
    )
    second = installed_cli(
        "research",
        "report",
        declaration,
        "--track",
        "repair",
        "--directory",
        tmp_path / "reviewed-again",
        tools_offline=True,
    )
    assert second.returncode == 0
    for name in ("repair.json", "repair.md"):
        assert (tmp_path / "reviewed-out" / name).read_bytes() == (
            tmp_path / "reviewed-again" / name
        ).read_bytes()


@pytest.mark.parametrize("outcome", ["lawful_change", "regressed", "unresolved"])
def test_native_control_outcomes_are_separate_from_generation_and_target_resolution(
    installed_cli, research_material, tmp_path, outcome
):
    from backend.tests.evaluation.test_controlled_report import addition_case

    root, _, _, _, write = research_material
    value = addition_case()
    execution = replay(value)
    fields = (
        {"b": {"regularOpeningHours": {"periods": []}}}
        if outcome == "regressed"
        else ({"b": {"regularOpeningHours": {}}} if outcome == "unresolved" else None)
    )
    package = material(value, execution, root / "control-only-snapshot", hours_by_place=fields)
    goals = expectations(value, execution)
    entry = controlled_entry(value, goals, descriptor(root, value, execution, goals, package))
    study = {"study_id": "controls-only", "revision": "1", "cases": [entry]}
    declaration = write()
    decl = json.loads(declaration.read_bytes())
    decl["track_refs"]["repair"] = save(
        root,
        "repair-material.json",
        {
            "schema_version": "rtpeval_research_repair_1",
            "population_id": "original-requests",
            "population_revision": "r1",
            "profile_id": "fixed-selection",
            "profile_revision": "p1",
            "controlled": study,
        },
    )
    save(root, "research.json", decl)
    result = installed_cli(
        "research",
        "report",
        declaration,
        "--track",
        "repair",
        "--directory",
        tmp_path / "control-only-out",
        tools_offline=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads((tmp_path / "control-only-out" / "repair.json").read_bytes())
    controlled = report["controlled"]
    assert controlled["control_outcomes"] == {outcome: 1}
    assert controlled["resolution"]["denominator"] == 0
    assert controlled["case_joint_success"]["denominator"] == 0
    assert report["same_run"]["summary"]["expected_slots"] == 20


def test_resolved_target_with_independent_regression_is_not_preserved(
    installed_cli, research_material, tmp_path
):
    declaration, _ = declared_controlled(research_material, regress=True)
    result = installed_cli(
        "research",
        "report",
        declaration,
        "--track",
        "repair",
        "--directory",
        tmp_path / "regression-out",
        tools_offline=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads((tmp_path / "regression-out" / "repair.json").read_bytes())
    controlled = report["controlled"]
    assert controlled["targets"][0]["independent_outcome"] == "resolved"
    assert controlled["targets"][0]["preservation"] == "violated"
    native = controlled["cases"][0]["native"]
    assert native["guards"][0]["after"]["state"] == "PASS"
    assert any(
        row["transition"] == "regression"
        for row in native["reviewed_checks"]["continuity"]["opening"]
    )
    assert controlled["preserved_resolution"]["numerator"] == 0
