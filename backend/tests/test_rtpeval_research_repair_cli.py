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


def test_native_paired_access_replays_through_installed_research(
    installed_cli, pair_case, batch, tmp_path
):
    from backend.evaluation.opening_judgment import prepare_packet
    from backend.evaluation.v3_correspondence import read_v3_result_sources
    from backend.evaluation.v3_pair_report import build_v3_pair_report
    from backend.tests.evaluation.test_opening_judgment import material
    from backend.tests.evaluation.test_pair_opening import missing_hours

    prepare_namespaced_usage(batch)
    case = pair_case(details_payload=missing_hours)
    root = batch[-1]
    descriptor = native_descriptor(root, case, "pair")
    density = json.loads((root / descriptor["density_reviews_ref"]["path"]).read_bytes())
    packet = prepare_packet(
        case[0],
        case[1],
        case[2],
        case[3],
        model="fixture-model",
        paired=True,
        pair_only=True,
        expected_plan=case[6],
    )
    access = material(packet)
    report = build_v3_pair_report(
        case[0],
        case[1],
        case[2],
        case[3],
        route_reviews=case[4],
        coordinate_evidence=case[5],
        expected_plan=case[6],
        density_reviews=density,
        opening_judgment=access,
        generated_at=native_pairs.STAMP,
        result_sources=read_v3_result_sources(case[0], root / "manifest.json"),
    ).to_dict()
    assert report["status"] == "complete"
    descriptor["report_ref"] = save(root, "pair-assisted-report.json", report)
    descriptor["opening_judgment_ref"] = save(root, "pair-access.json", access)
    declaration = declare_native(root, batch[0], pairs=[descriptor])
    result = installed_cli(
        "research",
        "report",
        declaration,
        "--track",
        "repair",
        "--directory",
        tmp_path / "assisted-research",
        evaluation_offline=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    derived = json.loads((tmp_path / "assisted-research/repair.json").read_bytes())
    assert derived["same_run"]["summary"]["unchanged"] == 1


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


@pytest.mark.parametrize("fault", ["groups", "runs"])
def test_malformed_native_manifest_is_public_material_correction(
    installed_cli, pair_case, batch, tmp_path, fault
):
    prepare_namespaced_usage(batch)
    case = pair_case()
    root = batch[-1]
    descriptor = native_descriptor(root, final_case(case), "quality")
    declaration = declare_native(root, batch[0], quality=[descriptor])
    manifest = json.loads((root / descriptor["manifest_ref"]["path"]).read_bytes())
    if fault == "groups":
        manifest["groups"] = [None]
    else:
        manifest["groups"][0]["selected_runs"] = []
    descriptor["manifest_ref"] = save(root, "malformed-native.json", manifest)
    material = json.loads((root / "repair-material.json").read_bytes())
    material["quality_reports"] = [descriptor]
    decl = json.loads(declaration.read_bytes())
    decl["track_refs"]["repair"] = save(root, "repair-material.json", material)
    save(root, "research.json", decl)
    output = tmp_path / "malformed-out"
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


@pytest.mark.parametrize(
    "state,attempted", [("no_repair", False), ("SKIPPED", False), ("REJECTED", True)]
)
def test_unchanged_no_repair_skipped_and_rejected_runs_remain_in_generation_cohort(
    installed_cli, pair_case, batch, tmp_path, state, attempted
):
    import copy

    from backend.evaluation.mechanism_preparation import read_batch_sources
    from backend.evaluation.mechanism_report import report_mechanism
    from backend.tests.evaluation.test_routes import no_departure
    from backend.tests.research_native_fixtures import file_ref

    prepare_namespaced_usage(batch)

    def change(results):
        no_departure(results)
        draft = copy.deepcopy(results["v3"]["itinerary"])
        repair = (
            None
            if state == "no_repair"
            else {
                "status": state,
                "model_attempted": attempted,
                "rounds": [],
                "components": [],
                "target_progress": [],
                "counters": {"model": int(attempted)},
                "usage": {},
            }
        )
        results["v3"]["v3"] = {
            "draft": draft,
            "final_primary": copy.deepcopy(draft),
            "original_report": {
                "findings": [] if state == "no_repair" else [{"finding_id": "f"}],
                "improvement_targets": [] if state == "no_repair" else [{"finding_id": "f"}],
            },
            "scope": None if state == "no_repair" else {"target_ids": ["f"]},
            "repair": repair,
        }

    case = pair_case(source_change=change)
    root = batch[-1]
    pair = native_descriptor(root, case, "pair")
    manifest = root / "manifest.json"
    mechanism = report_mechanism(read_batch_sources(manifest))
    assert mechanism["status"] == "complete", mechanism
    descriptor = {
        "manifest_ref": file_ref(root, manifest),
        "report_ref": save(root, "mechanism.json", mechanism),
    }
    declaration = declare_native(root, batch[0], pairs=[pair], mechanisms=[descriptor])
    result = installed_cli(
        "research",
        "report",
        declaration,
        "--track",
        "repair",
        "--directory",
        tmp_path / "states-out",
        evaluation_offline=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads((tmp_path / "states-out" / "repair.json").read_bytes())
    assert report["same_run"]["summary"]["unchanged"] == 1
    assert report["same_run"]["rows"][0]["repair_attempted"] is attempted
    conditional = report["same_run"]["conditional_attempted_repair"]
    assert conditional["summary"]["expected_slots"] == int(attempted)
    assert conditional["summary"]["unchanged"] == int(attempted)


@pytest.mark.parametrize("operation", ["delete", "replace"])
def test_native_deletion_and_replacement_keep_loss_and_identity_continuity(
    installed_cli, pair_case, batch, tmp_path, operation
):
    prepare_namespaced_usage(batch)

    def after(itinerary):
        if operation == "delete":
            itinerary["days"][0]["activities"] = itinerary["days"][0]["activities"][1:]
            itinerary["transfers"] = []
        else:
            itinerary["days"][0]["activities"][0].update(
                place_name="Gallery C", title="Gallery C", source_place_id="canonical-Gallery C"
            )

    proposal = native_pairs.edit(
        operation,
        place_id="canonical-Gallery C" if operation == "replace" else None,
        start_time="2020-01-01T09:00:00+00:00" if operation == "replace" else None,
        end_time="2020-01-01T10:00:00+00:00" if operation == "replace" else None,
    )
    case = pair_case(after=after, edits=[proposal])
    root = batch[-1]
    pair = native_descriptor(root, case, "pair")
    declaration = declare_native(root, batch[0], pairs=[pair])
    result = installed_cli(
        "research",
        "report",
        declaration,
        "--track",
        "repair",
        "--directory",
        tmp_path / "structure-out",
        evaluation_offline=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads((tmp_path / "structure-out" / "repair.json").read_bytes())
    native = report["same_run"]["rows"][0]["native"]
    relation = next(
        row for row in native["correspondence"]["relations"] if operation in row["operations"]
    )
    assert relation["relation"] == ("removed" if operation == "delete" else "replaced")
    assert native["visit_changes"]["removed_count"] == (1 if operation == "delete" else 0)
    if operation == "replace":
        assert relation["identity_change"] == "changed_canonical_venue"
    assert "repair_success" not in native


def test_native_density_improvement_keeps_literal_overall_and_auxiliary_deltas(
    installed_cli, pair_case, batch, tmp_path
):
    import copy

    prepare_namespaced_usage(batch)

    def before(itinerary):
        itinerary["days"][0]["activities"] = itinerary["days"][0]["activities"][:1]
        itinerary["transfers"] = []

    def after(itinerary):
        extra = copy.deepcopy(itinerary["days"][0]["activities"][0])
        extra.update(
            activity_id="extra",
            title="Museum B",
            place_name="Museum B",
            start_time="2020-01-01T12:00:00Z",
            end_time="2020-01-01T13:00:00Z",
        )
        itinerary["days"][0]["activities"].append(extra)

    case = pair_case(before=before, after=after)
    root = batch[-1]
    pair = native_descriptor(root, case, "pair")
    declaration = declare_native(root, batch[0], pairs=[pair])
    result = installed_cli(
        "research",
        "report",
        declaration,
        "--track",
        "repair",
        "--directory",
        tmp_path / "density-out",
        evaluation_offline=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads((tmp_path / "density-out" / "repair.json").read_bytes())
    assert report["same_run"]["summary"]["improved"] == 1
    native = report["same_run"]["rows"][0]["native"]
    assert native["deltas"]["overall_total"]["percentage_points"] == 20
    assert native["deltas"]["auxiliary_total"]["percentage_points"] == 0


def test_native_lost_verification_remains_explicit_in_continuity(
    installed_cli, pair_case, batch, tmp_path
):
    prepare_namespaced_usage(batch)

    def after(itinerary):
        itinerary["days"][0]["activities"][0].update(start_time=None, end_time=None)

    def payload(request):
        return {
            "id": request["parameters"]["place_id"],
            "timeZone": {"id": "Etc/UTC"},
            "regularOpeningHours": {"periods": [{"open": {"day": 0, "hour": 0, "minute": 0}}]},
        }

    case = pair_case(after=after, details_payload=payload)
    root = batch[-1]
    pair = native_descriptor(root, case, "pair")
    declaration = declare_native(root, batch[0], pairs=[pair])
    result = installed_cli(
        "research",
        "report",
        declaration,
        "--track",
        "repair",
        "--directory",
        tmp_path / "lost-out",
        evaluation_offline=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads((tmp_path / "lost-out" / "repair.json").read_bytes())
    row = report["same_run"]["rows"][0]
    assert row["continuity"]["transitions"]["lost_verification"] >= 1
    assert row["classification"] == "unavailable"


def test_native_missing_optional_stages_remain_unavailable_without_substituting_itinerary(
    installed_cli, route_case, batch, tmp_path
):
    prepare_namespaced_usage(batch)
    original = route_case()
    case = (original[0], original[1], None, None, None, None, None)
    root = batch[-1]
    pair = native_descriptor(root, case, "pair")
    declaration = declare_native(root, batch[0], pairs=[pair])
    result = installed_cli(
        "research",
        "report",
        declaration,
        "--track",
        "repair",
        "--directory",
        tmp_path / "missing-native-out",
        evaluation_offline=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads((tmp_path / "missing-native-out" / "repair.json").read_bytes())
    row = report["same_run"]["rows"][0]
    assert row["native"]["pair_status"] == "pair_unavailable"
    assert row["native"]["available_stages"] == {"draft": False, "final_primary": False}
    assert row["classification"] == "unavailable"
    assert report["same_run"]["summary"]["expected_slots"] == 1
    assert report["same_run"]["summary"]["unavailable"] == 1
