"""Research Repair acceptance through the installed offline CLI."""

import json

import pytest

from backend.evaluation.quality_report import quality_content_hash
from backend.tests import test_rtpeval_research_population_cli as population_tests
from backend.tests.evaluation import test_v3_pair_report as native_pairs
from backend.tests.research_native_fixtures import (
    declare_native,
    final_case,
    native_descriptor,
    prepare_namespaced_usage,
)
from backend.tests.test_rtpeval_research_population_cli import save

research_material = population_tests.research_material


pytest_plugins = ("backend.tests.test_rtpeval_cli",)


def test_missing_repair_material_retains_every_planned_v3_slot(
    installed_cli, research_material, tmp_path
):
    result = installed_cli(
        "research",
        "report",
        research_material[-1](),
        "--track",
        "repair",
        "--directory",
        tmp_path / "repair-out",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads((tmp_path / "repair-out" / "repair.json").read_text())
    assert len(report["same_run"]["rows"]) == 20
    assert report["same_run"]["summary"] == {
        "expected_slots": 20,
        "comparable": 0,
        "improved": 0,
        "unchanged": 0,
        "worse": 0,
        "unavailable": 20,
    }
    assert report["controlled"]["applicability"] == "not_declared"
    assert report["four_final"]["summary"]["comparable"] == 0


pair_case = native_pairs.pair_case
route_case = native_pairs.route_case
prepared_scenario = native_pairs.prepared_scenario


def test_real_native_unchanged_pairs_and_finals_keep_separate_masks(
    installed_cli, pair_case, batch, tmp_path
):
    prepare_namespaced_usage(batch)
    case = pair_case()
    root = batch[-1]
    pair = native_descriptor(root, case, "pair")
    quality = native_descriptor(root, final_case(case), "quality")
    declaration = declare_native(root, batch[0], quality=[quality], pairs=[pair])
    result = installed_cli(
        "research",
        "report",
        declaration,
        "--track",
        "repair",
        "--directory",
        tmp_path / "real-out",
        evaluation_offline=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads((tmp_path / "real-out" / "repair.json").read_text())
    assert report["same_run"]["summary"]["unchanged"] == 1
    assert report["same_run"]["rows"][0]["native"]["deltas"]["overall_total"] == {
        "percentage_points": 0.0,
        "exact_fraction": {"numerator": 0, "denominator": 1},
    }
    row = report["four_final"]["rows"][0]
    assert row["deltas"]["overall_total"]["percentage_points"] == 0.0
    assert row["native_group"]["versions"]["v3"]["auxiliary_total"]["score_0_100"] == 50.0


@pytest.mark.parametrize("fault", ["metrics", "rules", "run", "snapshot"])
def test_rehashed_foreign_or_changed_native_material_is_rejected(
    installed_cli, pair_case, batch, tmp_path, fault
):
    prepare_namespaced_usage(batch)
    case = pair_case()
    root = batch[-1]
    descriptor = native_descriptor(root, final_case(case), "quality")
    saved = json.loads((root / descriptor["report_ref"]["path"]).read_bytes())
    if fault == "metrics":
        saved["groups"][0]["versions"]["v3"]["overall_total"]["score_0_100"] = 99
    elif fault == "rules":
        saved["rules_profile"]["profile_id"] = "invented-score"
    elif fault == "run":
        saved["groups"][0]["versions"]["v3"]["run_id"] = "foreign-run"
    else:
        directory = root / descriptor["snapshot_ref"]["path"]
        snapshot = json.loads(directory.read_bytes())
        raw = next(a["raw"] for r in snapshot["records"] for a in r["attempts"] if a["raw"])
        (directory.parent / raw["path"]).write_bytes(b"changed saved response")
    if fault != "snapshot":
        saved["content_hash"] = quality_content_hash(saved)
        descriptor["report_ref"] = save(root, "quality-report.json", saved)
    declaration = declare_native(root, batch[0], quality=[descriptor])
    output = tmp_path / "invalid-out"
    result = installed_cli(
        "research",
        "report",
        declaration,
        "--track",
        "repair",
        "--directory",
        output,
        evaluation_offline=True,
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert not output.exists()
    assert json.loads(result.stdout)["processing_status"] == "needs_material_correction"
