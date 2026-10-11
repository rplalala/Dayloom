"""Optional source-bound research integration through the installed suite CLI."""

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from backend.tests import test_rtpeval_research_population_cli as population_tests
from backend.tests import test_rtpeval_research_repair_cli as repair_tests
from backend.tests import test_rtpeval_suite_cli as suite_tests

installed_cli = suite_tests.installed_cli
suite_material = suite_tests.suite_material
research_material = population_tests.research_material
pytest_plugins = ("backend.tests.evaluation.test_intake",)


def research_attachment(material, root, tracks):
    declaration = material[-1]()
    destination = root / "research"
    shutil.copytree(declaration.parent, destination)
    raw = (destination / declaration.name).read_bytes()
    return {
        "schema_version": "rtpeval_suite_research_1",
        "declaration_ref": {
            "path": "research/" + declaration.name,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "schema_version": "rtpeval_research_declaration_1",
            "media_type": "application/json",
            "availability": "available",
        },
        "selected_tracks": tracks,
    }


def test_prepare_retains_failed_research_slots_outside_native_quality_selection(
    suite_material, research_material, installed_cli
):
    source, directory, declaration = suite_material
    research_material[1]["cases"] = research_material[1]["cases"][:2]
    population_tests.add_attempt(research_material, 0, "v0", "completed")
    population_tests.add_attempt(research_material, 0, "v1", "failed")
    declaration["tracks"] = {
        "research": research_attachment(research_material, source.parent, ["population"])
    }
    source.write_text(json.dumps(declaration), encoding="utf-8")
    result = installed_cli(
        "suite", "prepare", source, "--directory", directory, evaluation_offline=True
    )
    assert result.returncode == 0, result.stdout + result.stderr
    prepared = json.loads((directory / "preparation.json").read_bytes())
    assert len(prepared["cases"]) == 3
    assert prepared["reserved_cost_usd"] == "30"
    bound_modules = [name.replace("\\", "/") for name in prepared["implementation_hashes"]]
    assert any(name.endswith("/evaluation/suite_research.py") for name in bound_modules)
    assert any(name.endswith("/evaluation/research/links.py") for name in bound_modules)
    research = prepared["track_configuration"]["research"]
    assert research["selected_tracks"] == ["population"]
    assert research["tracks"]["relevance"]["processing_status"] == "not_requested"
    entry = research["tracks"]["population"]
    report = json.loads((directory / entry["json"]["path"]).read_bytes())
    assert report["population"]["unique_requests"] == 2
    assert len(report["slots"]) == 8
    assert report["summary"]["planned_completion"]["numerator"] == 1
    assert report["summary"]["planned_completion"]["denominator"] == 8
    assert report["summary"]["conditional_completion"]["denominator"] == 2
    assert report["summary"]["status_counts"]["failed"] == 1
    assert report["summary"]["status_counts"]["unknown_pending"] == 6
    assert report["all_four"]["completion"]["denominator"] == 2
    assert entry["semantic_sha256"] == report["semantic_sha256"]
    assert entry["source_digest"] == report["source_digest"]
    assert entry["measurement_coverage"] == report["measurement_coverage"]
    frozen = directory / research["source_root"]
    assert (frozen / "research.json").read_bytes() == (
        source.parent / "research/research.json"
    ).read_bytes()
    assert not list(directory.rglob("started.json"))


def test_offline_refresh_indexes_all_questions_without_claiming_missing_measurements(
    suite_material, research_material, installed_cli, monkeypatch, capsys
):
    from backend.tests.test_rtpeval_suite_external_cli import execute_fixture

    source, directory, _ = suite_material
    original = execute_fixture(source, directory, monkeypatch, capsys)
    preserved = {path: path.read_bytes() for path in directory.rglob("*") if path.is_file()}
    research_material[1]["cases"] = research_material[1]["cases"][:2]
    population_tests.add_attempt(research_material, 0, "v1", "failed")
    selected = ["tradeoffs", "relevance", "population", "repair", "opportunities"]
    attachment = research_attachment(research_material, source.parent, selected)
    update = source.parent / "attachments.json"
    update.write_text(
        json.dumps(
            {
                "schema_version": "rtpeval_suite_attachments_1",
                "suite_id": "synthetic",
                "tracks": {"research": attachment},
            }
        ),
        encoding="utf-8",
    )
    result = installed_cli(
        "suite", "report", directory, "--attachments", update, evaluation_offline=True
    )
    assert result.returncode == 0, result.stdout + result.stderr
    refreshed = json.loads(result.stdout)
    assert refreshed["cases"] == original["cases"]
    assert refreshed["processing_status"] == "complete"
    research = refreshed["tracks"]["research"]
    assert research["population"]["planned_slots"] == 8
    assert research["population"]["unique_requests"] == 2
    for name in selected:
        entry = research["tracks"][name]
        assert entry["processing_status"] == "completed"
        path = directory / entry["json"]["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["json"]["sha256"]
        report = json.loads(path.read_bytes())
        standalone = installed_cli(
            "research",
            "report",
            source.parent / attachment["declaration_ref"]["path"],
            "--track",
            name,
            "--directory",
            source.parent / ("alone-" + name),
            evaluation_offline=True,
        )
        assert standalone.returncode == 0, standalone.stdout + standalone.stderr
        assert report == json.loads(
            (source.parent / ("alone-" + name) / (name + ".json")).read_bytes()
        )
    relevance = json.loads(
        (directory / research["tracks"]["relevance"]["json"]["path"]).read_bytes()
    )
    assert len(relevance["runs"]) == 4
    assert relevance["comparisons"][0]["end_to_end"]["delta"] is None
    resources = json.loads(
        (directory / research["tracks"]["tradeoffs"]["json"]["path"]).read_bytes()
    )
    assert resources["all_attempts"]["missing_usage_attempts"] == 1
    assert resources["all_attempts"]["ledger_complete"] is False
    assert {path: path.read_bytes() for path in preserved} == preserved
    lineage = json.loads((directory / "reports/0001/lineage.json").read_bytes())
    assert (
        lineage["parent_summary_sha256"]
        == hashlib.sha256(preserved[directory / "summary.json"]).hexdigest()
    )
    replay = installed_cli("suite", "replay", directory, evaluation_offline=True)
    assert replay.returncode == 0, replay.stdout + replay.stderr
    assert json.loads(replay.stdout) == refreshed


def native_research_material(batch, pair_case, *, tokens_missing=False):
    import copy

    from backend.evaluation.identity import identity_references
    from backend.tests import test_rtpeval_research_relevance_cli as relevance_tests
    from backend.tests import test_rtpeval_research_tradeoffs_cli as tradeoff_tests
    from backend.tests.evaluation.test_identity import evidence, plan, review_envelope, search
    from backend.tests.research_native_fixtures import declare_native, final_case, native_descriptor
    from backend.tests.test_rtpeval_research_opportunities_cli import observation

    root = batch[-1]
    tradeoff_tests.native_usage(batch)
    if tokens_missing:
        for run in batch[0]["groups"][0]["selected_runs"].values():
            usage = json.loads((root / run["usage_ref"]["path"]).read_bytes())
            usage["model_calls"][0].pop("total_tokens")
            run["usage_ref"] = batch[3](run["usage_ref"]["path"], usage, usage["schema_version"])
        batch[2]()
    case = pair_case()
    pair = native_descriptor(root, case, "pair")
    quality = native_descriptor(root, final_case(case), "quality")
    path = declare_native(root, batch[0], quality=[quality], pairs=[pair])
    declaration = json.loads(path.read_bytes())
    population = json.loads((root / "population.json").read_bytes())
    profile = json.loads((root / "profile.json").read_bytes())
    census = json.loads((root / "census.json").read_bytes())

    def write():
        for field, name, value in (
            ("population_ref", "population.json", population),
            ("profile_ref", "profile.json", profile),
            ("census_ref", "census.json", census),
        ):
            declaration[field] = population_tests.save(root, name, value)
        population_tests.save(root, "research.json", declaration)
        return path

    material = root, population, profile, census, write
    observations, reviews = [], []
    for reference in identity_references(case[0]):
        pid = "canonical-" + reference["name"]
        row = search(reference, reference["name"], place_id=pid)
        observations.append(row)
        reviews.extend(review_envelope(case[0], row, reference["reference_id"], pid)["records"])
    identity_sources = {
        "mode": "legacy",
        "manifest_ref": quality["manifest_ref"],
        "evidence_ref": population_tests.save(
            root, "rag-identity-evidence.json", evidence(case[0], observations)
        ),
        "audit_ref": population_tests.save(root, "rag-identity-audit.json", plan(case[0])),
        "reviews_ref": population_tests.save(
            root,
            "rag-identity-reviews.json",
            {
                "schema_version": "rtpeval_identity_reviews_1",
                "batch_id": "batch",
                "batch_revision": "1",
                "records": reviews,
            },
        ),
    }
    entries = []
    for version in ("v1", "v2"):
        scratch_material = root, copy.deepcopy(population), profile, {"attempts": []}, write
        _, capture = observation(scratch_material, version)
        ids = {"a": "canonical-Museum A", "b": "canonical-Museum B", "c": "canonical-Museum C"}
        capture["pre_rag_google_ids"] = [ids[pid] for pid in capture["pre_rag_google_ids"]]
        for stage in capture["stages"].values():
            for place in stage["places"]:
                place["canonical_place_id"] = ids.get(
                    place["canonical_place_id"], place["canonical_place_id"]
                )
                for origin in place["rag_origins"]:
                    origin["evidence_ref"] = "google_places:" + place["canonical_place_id"]
                    origin.update(space_id="space-1", policy_version="policy-1")
        for omission in capture["omissions"]:
            omission["canonical_place_id"] = ids[omission["canonical_place_id"]]
        if version == "v1":
            places = copy.deepcopy(capture["stages"]["supplied"]["places"])
            for place in places:
                place["rag_origins"] = []
            capture.update(rag=None, omissions=[])
            capture["stages"] = {
                name: {"status": "complete", "places": places, "reasons": []}
                for name in capture["stages"]
            }
        attempt = next(a for a in census["attempts"] if a["version"] == version)
        capture["run_id"] = attempt["run_id"]
        entry = {
            field: attempt[field]
            for field in (
                "case_id",
                "case_revision",
                "version",
                "repetition_id",
                "attempt_id",
                "run_id",
                "input_sha256",
                "configuration_sha256",
            )
        }
        entry.update(
            result_sha256=attempt["result_ref"]["sha256"],
            capture_ref=population_tests.save(root, version + "-capture.json", capture),
            identity_sources=identity_sources,
        )
        entries.append(entry)
    inventory_ref, inventory = relevance_tests.interest_inventory(
        material, interests=("architecture",), use_existing=True
    )
    labels = relevance_tests.labels(
        material,
        inventory_ref,
        inventory,
        [
            ("architecture", pid, "relevant")
            for pid in ("canonical-Museum A", "canonical-Museum B", "canonical-Museum C")
        ],
    )
    coverage, coverage_profile = relevance_tests.corpus_coverage(material)
    path = relevance_tests.write_relevance(
        material,
        entries,
        inventories=[inventory_ref],
        reviews=[labels],
        coverage=[population_tests.save(root, "coverage.json", coverage)],
        profile=population_tests.save(root, "coverage-profile.json", coverage_profile),
    )
    declaration.update(json.loads(path.read_bytes()))
    declaration["track_refs"]["tradeoffs"] = population_tests.save(
        root,
        "tradeoffs-material.json",
        {
            "schema_version": "rtpeval_research_tradeoffs_1",
            "quality_reports": [quality],
            "cost_ledgers": [],
        },
    )
    write()
    return material


pair_case = repair_tests.pair_case
route_case = repair_tests.route_case
prepared_scenario = repair_tests.prepared_scenario


def test_all_three_questions_link_only_source_compatible_selected_attempts(
    suite_material, installed_cli, batch, pair_case, monkeypatch, capsys
):
    from backend.tests.test_rtpeval_suite_external_cli import execute_fixture

    source, directory, declaration = suite_material
    material = native_research_material(batch, pair_case)
    path = material[-1]()
    ref = population_tests.save(source.parent, path.name, json.loads(path.read_bytes()))
    declaration["tracks"] = {
        "research": {
            "schema_version": "rtpeval_suite_research_1",
            "declaration_ref": ref,
            "selected_tracks": ["population", "opportunities", "relevance", "repair", "tradeoffs"],
        }
    }
    source.write_text(json.dumps(declaration), encoding="utf-8")
    report = execute_fixture(source, directory, monkeypatch, capsys)
    assert report["processing_status"] == "complete"
    research = report["tracks"]["research"]
    outputs = {
        name: json.loads((directory / entry["json"]["path"]).read_bytes())
        for name, entry in research["tracks"].items()
    }
    assert outputs["population"]["summary"]["planned_completion"]["numerator"] == 4
    assert outputs["population"]["summary"]["planned_completion"]["denominator"] == 4
    rag = outputs["relevance"]["comparisons"][0]
    assert rag["end_to_end"]["delta"] == 0
    assert rag["stages"]["discovered"]["delta"] == 1
    assert outputs["relevance"]["coverage"][0]["eligible_entity_count"] == 0
    assert outputs["repair"]["same_run"]["summary"]["unchanged"] == 1
    assert outputs["repair"]["four_final"]["summary"]["unchanged"] == 1
    assert (
        outputs["repair"]["same_run"]["rows"][0]["native"]["stages"]["draft"]["label"] == "V3 draft"
    )
    assert (
        outputs["tradeoffs"]["paired_comparisons"][0]["rows"][0]["resources"]["total_tokens"][
            "difference"
        ]
        == 50
    )
    links = research["benefit_resource_links"]
    assert [row["kind"] for row in links] == [
        "rag_v2_minus_v1",
        "repair_v3_minus_v2_finals",
        "repair_same_run_v3",
    ]
    assert all(row["status"] == "matched" for row in links)
    assert [member["version"] for member in links[2]["selected_attempts"]] == ["v3"]
    assert links[2]["resource_view"] == "selected_v3_invocation"
    assert links[0]["selected_attempts"][0]["attempt_id"] == "a-v1"
    assert (
        links[0]["selected_attempts"][1]["usage_sha256"]
        == material[3]["attempts"][2]["usage_ref"]["sha256"]
    )
    assert links[0]["benefit"]["semantic_sha256"] == outputs["relevance"]["semantic_sha256"]
    assert links[0]["resources"]["semantic_sha256"] == outputs["tradeoffs"]["semantic_sha256"]
    replay = installed_cli("suite", "replay", directory, evaluation_offline=True)
    assert replay.returncode == 0, replay.stdout + replay.stderr
    assert json.loads(replay.stdout) == report
    raws = [path for path in research["tracks"]["repair"]["source_dependencies"] if "/raw/" in path]
    assert raws, "Native research snapshots must freeze raw responses"
    for path in raws:
        original = source.parent / Path(path).relative_to("tracks/research/sources")
        assert (directory / path).read_bytes() == original.read_bytes()
    raw = directory / raws[0]
    raw.write_bytes(raw.read_bytes() + b" corrupted")
    rejected = installed_cli("suite", "replay", directory, evaluation_offline=True)
    assert rejected.returncode == 2, rejected.stderr
    assert json.loads(rejected.stdout)["processing_status"] == "needs_material_correction"
    rejected_report = installed_cli("suite", "report", directory, evaluation_offline=True)
    assert rejected_report.returncode == 2, rejected_report.stderr
    assert not (directory / "reports/0001").exists()


def test_later_independent_review_refresh_and_inherited_refresh_keep_closed_sources(
    suite_material, installed_cli, batch, pair_case, monkeypatch, capsys
):
    import re
    from urllib.parse import unquote

    from backend.tests.test_rtpeval_suite_external_cli import execute_fixture

    source, directory, declaration = suite_material
    material = native_research_material(batch, pair_case)
    path = material[-1]()
    attachment = {
        "schema_version": "rtpeval_suite_research_1",
        "declaration_ref": population_tests.save(
            source.parent, path.name, json.loads(path.read_bytes())
        ),
        "selected_tracks": ["relevance", "tradeoffs", "repair"],
    }
    declaration["tracks"] = {"research": attachment}
    source.write_text(json.dumps(declaration), encoding="utf-8")
    original = execute_fixture(source, directory, monkeypatch, capsys)
    initial = {p: p.read_bytes() for p in directory.rglob("*") if p.is_file()}
    research = original["tracks"]["research"]
    old_relevance = research["tracks"]["relevance"]["semantic_sha256"]
    later = source.parent / "later review"
    shutil.copytree(directory / research["source_prefix"], later)
    reviews = json.loads((later / "relevance-reviews.json").read_bytes())
    for row in reviews["records"]:
        row.update(revision="review-r2", reviewed_at="2026-10-03T00:00:00Z")
        if row["canonical_place_id"] == "canonical-Museum C":
            row["verdict"] = "not_relevant"
    changed = population_tests.save(later, "relevance-reviews.json", reviews)
    native_declaration = json.loads((later / "research.json").read_bytes())
    relevance_material = json.loads((later / "relevance-material.json").read_bytes())
    relevance_material["review_refs"] = [changed]
    native_declaration["track_refs"]["relevance"] = population_tests.save(
        later, "relevance-material.json", relevance_material
    )
    attachment["declaration_ref"] = population_tests.save(
        later, "research.json", native_declaration
    )
    update = later / "attachments.json"
    update.write_text(
        json.dumps(
            {
                "schema_version": "rtpeval_suite_attachments_1",
                "suite_id": "synthetic",
                "tracks": {"research": attachment},
            }
        ),
        encoding="utf-8",
    )
    result = installed_cli(
        "suite", "report", directory, "--attachments", update, evaluation_offline=True
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["cases"] == original["cases"]
    revised = report["tracks"]["research"]
    assert revised["tracks"]["relevance"]["semantic_sha256"] != old_relevance
    assert (
        revised["tracks"]["tradeoffs"]["semantic_sha256"]
        != research["tracks"]["tradeoffs"]["semantic_sha256"]
    )  # Declaration bytes are a source dependency.
    rel = json.loads((directory / revised["tracks"]["relevance"]["json"]["path"]).read_bytes())
    assert rel["comparisons"][0]["stages"]["discovered"]["delta"] == 0
    assert rel["review_coverage"]["relevance_review_records"] == 3
    assert {p: p.read_bytes() for p in initial} == initial
    first = {p: p.read_bytes() for p in (directory / "reports/0001").rglob("*") if p.is_file()}
    shutil.rmtree(later)  # Revision replay uses only its frozen dependencies.
    inherited = installed_cli("suite", "report", directory, evaluation_offline=True)
    assert inherited.returncode == 0, inherited.stdout + inherited.stderr
    inherited_report = json.loads(inherited.stdout)
    inherited_index = inherited_report["tracks"]["research"]
    assert (
        inherited_index["tracks"]["relevance"]["json"]["path"]
        == "reports/0002/tracks/research/reports/relevance.json"
    )
    assert (
        inherited_index["tracks"]["relevance"]["semantic_sha256"]
        == revised["tracks"]["relevance"]["semantic_sha256"]
    )
    assert {p: p.read_bytes() for p in first} == first
    assert {p: p.read_bytes() for p in initial} == initial
    for index in (revised, inherited_index):
        for entry in index["tracks"].values():
            if entry["processing_status"] == "not_requested":
                continue
            markdown = directory / entry["markdown"]["path"]
            for target in re.findall(r"\]\(([^)]+)\)", markdown.read_text(encoding="utf-8")):
                assert (markdown.parent / unquote(target)).resolve().is_file()
            assert hashlib.sha256(markdown.read_bytes()).hexdigest() == entry["markdown"]["sha256"]
    receipt = json.loads((directory / "reports/0002/receipt.json").read_bytes())
    assert "sources/research.json" in receipt["files"]
    assert "tracks/research/reports/relevance.md" in receipt["files"]
    replay = installed_cli("suite", "replay", directory, evaluation_offline=True)
    assert replay.returncode == 0, replay.stdout + replay.stderr
    assert json.loads(replay.stdout) == inherited_report


@pytest.mark.parametrize("fault", ["declaration_hash", "escape", "missing", "stale", "malformed"])
def test_invalid_research_refresh_diagnoses_track_before_mutating_prior_outputs(
    suite_material, research_material, installed_cli, monkeypatch, capsys, fault
):
    from backend.tests.test_rtpeval_suite_external_cli import execute_fixture

    source, directory, _ = suite_material
    execute_fixture(source, directory, monkeypatch, capsys)
    preserved = {p: p.read_bytes() for p in directory.rglob("*") if p.is_file()}
    research_material[1]["cases"] = research_material[1]["cases"][:1]
    if fault == "stale":
        research_material[3]["profile_revision"] = "old-profile"
    attachment = research_attachment(
        research_material, source.parent, ["population", "opportunities"]
    )
    nested = source.parent / "research"
    if fault == "declaration_hash":
        attachment["declaration_ref"]["sha256"] = "0" * 64
    elif fault == "escape":
        attachment["declaration_ref"]["path"] = "../research.json"
    elif fault == "missing":
        (nested / "input-0.json").unlink()
    elif fault == "malformed":
        declared = json.loads((nested / "research.json").read_bytes())
        declared["track_refs"]["opportunities"] = population_tests.save(
            nested,
            "bad-opportunities.json",
            {"schema_version": "rtpeval_research_opportunities_1", "observations": "bad-array"},
        )
        attachment["declaration_ref"] = {
            **population_tests.save(nested, "research.json", declared),
            "path": "research/research.json",
        }
    update = source.parent / "attachments.json"
    update.write_text(
        json.dumps(
            {
                "schema_version": "rtpeval_suite_attachments_1",
                "suite_id": "synthetic",
                "tracks": {"research": attachment},
            }
        ),
        encoding="utf-8",
    )
    result = installed_cli(
        "suite", "report", directory, "--attachments", update, evaluation_offline=True
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert "Research" in json.loads(result.stdout)["reason"]
    assert "opportunities" in json.loads(result.stdout)["reason"] if fault == "malformed" else True
    assert {p: p.read_bytes() for p in preserved} == preserved
    assert not (directory / "reports").exists()


@pytest.mark.parametrize("fault", ["report", "markdown", "source", "missing", "escape", "parent"])
def test_frozen_research_refresh_integrity_rejects_corrupt_missing_and_escaped_material(
    suite_material, research_material, installed_cli, monkeypatch, capsys, fault
):
    from backend.tests.test_rtpeval_suite_external_cli import execute_fixture

    source, directory, _ = suite_material
    execute_fixture(source, directory, monkeypatch, capsys)
    research_material[1]["cases"] = research_material[1]["cases"][:1]
    attachment = research_attachment(research_material, source.parent, ["population"])
    update = source.parent / "attachments.json"
    update.write_text(
        json.dumps(
            {
                "schema_version": "rtpeval_suite_attachments_1",
                "suite_id": "synthetic",
                "tracks": {"research": attachment},
            }
        ),
        encoding="utf-8",
    )
    refreshed = installed_cli(
        "suite", "report", directory, "--attachments", update, evaluation_offline=True
    )
    assert refreshed.returncode == 0, refreshed.stdout + refreshed.stderr
    revision = directory / "reports/0001"
    target = (
        revision
        / {
            "report": "tracks/research/reports/population.json",
            "markdown": "tracks/research/reports/population.md",
            "source": "sources/research/input-0.json",
            "missing": "sources/research/input-0.json",
            "escape": "attachments.json",
            "parent": "lineage.json",
        }[fault]
    )
    if fault == "missing":
        target.unlink()
    elif fault in ("escape", "parent"):
        value = json.loads(target.read_bytes())
        if fault == "escape":
            value["tracks"]["research"]["declaration_ref"]["path"] = "../research.json"
        else:
            value["parent_summary_sha256"] = "0" * 64
        target.write_text(json.dumps(value), encoding="utf-8")
        # Keep the local receipt self-consistent; source bounds/lineage must still reject it.
        if fault == "escape":
            lineage = json.loads((revision / "lineage.json").read_bytes())
            lineage["attachments_sha256"] = hashlib.sha256(target.read_bytes()).hexdigest()
            (revision / "lineage.json").write_text(json.dumps(lineage), encoding="utf-8")
        reclose_revision(revision)
    else:
        target.write_bytes(target.read_bytes() + b" changed")
    prior = {p: p.read_bytes() for p in directory.rglob("*") if p.is_file()}
    replay = installed_cli("suite", "replay", directory, evaluation_offline=True)
    assert replay.returncode == 2, replay.stdout + replay.stderr
    assert json.loads(replay.stdout)["processing_status"] == "needs_material_correction"
    assert {p: p.read_bytes() for p in prior} == prior
    report = installed_cli("suite", "report", directory, evaluation_offline=True)
    assert report.returncode == 2, report.stdout + report.stderr
    assert not (directory / "reports/0002").exists()


def reclose_revision(revision):
    receipt = json.loads((revision / "receipt.json").read_bytes())
    receipt["files"] = {
        p.relative_to(revision).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in revision.rglob("*")
        if p.is_file() and p != revision / "receipt.json"
    }
    (revision / "receipt.json").write_text(json.dumps(receipt), encoding="utf-8")


def test_unselected_track_material_is_not_read_and_missing_links_retain_units(
    suite_material, research_material, installed_cli
):
    source, directory, declaration = suite_material
    research_material[1]["cases"] = research_material[1]["cases"][:1]
    attachment = research_attachment(research_material, source.parent, ["population"])
    research_path = source.parent / "research/research.json"
    value = json.loads(research_path.read_bytes())
    value["track_refs"]["relevance"] = {"path": "missing-malformed.json", "sha256": "0" * 64}
    attachment["declaration_ref"] = {
        **population_tests.save(research_path.parent, research_path.name, value),
        "path": "research/research.json",
    }
    declaration["tracks"] = {"research": attachment}
    source.write_text(json.dumps(declaration), encoding="utf-8")
    prepared = installed_cli(
        "suite", "prepare", source, "--directory", directory, evaluation_offline=True
    )
    assert prepared.returncode == 0, prepared.stdout + prepared.stderr
    index = json.loads((directory / "tracks/research/index.json").read_bytes())
    assert index["tracks"]["relevance"] == {
        "processing_status": "not_requested",
        "reason": "track_not_selected",
    }
    assert len(index["benefit_resource_links"]) == 3
    assert all(row["status"] == "unavailable" for row in index["benefit_resource_links"])
    assert all(row["selected_attempts"] for row in index["benefit_resource_links"])
    assert "missing-malformed.json" not in json.dumps(index)


def test_research_source_drift_stops_native_execution_and_only_invalidates_affected_track(
    suite_material, installed_cli, batch, pair_case, monkeypatch, capsys
):
    import asyncio

    import httpx

    from backend.cli.rtpeval import main
    from backend.tests.evaluation.test_evaluation_run import mock_provider

    source, directory, declaration = suite_material
    material = native_research_material(batch, pair_case)
    path = material[-1]()
    declaration["tracks"] = {
        "research": {
            "schema_version": "rtpeval_suite_research_1",
            "declaration_ref": population_tests.save(
                source.parent, path.name, json.loads(path.read_bytes())
            ),
            "selected_tracks": ["population", "relevance", "repair", "tradeoffs"],
        }
    }
    source.write_text(json.dumps(declaration), encoding="utf-8")
    prepared = installed_cli(
        "suite", "prepare", source, "--directory", directory, evaluation_offline=True
    )
    assert prepared.returncode == 0, prepared.stdout + prepared.stderr
    target = source.parent / "relevance-reviews.json"
    raw = target.read_bytes()
    calls = []

    def respond(request):
        calls.append(request)
        response = mock_provider(request)
        if len(calls) == 6:
            target.write_bytes(raw + b" ")
        return response

    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "synthetic-google")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "synthetic-model")
    client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    try:
        assert (
            main(
                [
                    "suite",
                    "execute",
                    str(directory),
                    "--approved-sha256",
                    json.loads(prepared.stdout)["preparation_sha256"],
                ],
                http_client=client,
            )
            == 2
        )
    finally:
        asyncio.run(client.aclose())
    report = json.loads(capsys.readouterr().out)
    assert len(calls) == 6
    assert [row["processing_status"] for row in report["cases"]] == [
        "complete",
        "stopped",
        "unstarted",
    ]
    research = report["tracks"]["research"]
    assert research["processing_status"] == "needs_material_correction"
    assert research["tracks"]["relevance"]["processing_status"] == "needs_material_correction"
    assert research["tracks"]["repair"]["processing_status"] == "completed"
    assert research["tracks"]["tradeoffs"]["processing_status"] == "completed"
    assert research["benefit_resource_links"][0]["status"] == "unavailable"
    assert "research_material_correction" in research["benefit_resource_links"][0]["reasons"]
    target.write_bytes(raw)
    replay = installed_cli("suite", "replay", directory, evaluation_offline=True)
    assert replay.returncode == 2, replay.stdout + replay.stderr
    assert json.loads(replay.stdout) == report


def test_replay_rebuilds_saved_semantics_even_when_all_refresh_checksums_are_rehashed(
    suite_material, research_material, installed_cli, monkeypatch, capsys
):
    import base64

    from backend.tests.test_rtpeval_suite_external_cli import execute_fixture

    source, directory, _ = suite_material
    execute_fixture(source, directory, monkeypatch, capsys)
    research_material[1]["cases"] = research_material[1]["cases"][:1]
    attachment = research_attachment(research_material, source.parent, ["population"])
    update = source.parent / "attachments.json"
    update.write_text(
        json.dumps(
            {
                "schema_version": "rtpeval_suite_attachments_1",
                "suite_id": "synthetic",
                "tracks": {"research": attachment},
            }
        ),
        encoding="utf-8",
    )
    result = installed_cli(
        "suite", "report", directory, "--attachments", update, evaluation_offline=True
    )
    assert result.returncode == 0, result.stdout + result.stderr
    revision = directory / "reports/0001"
    report_path = revision / "tracks/research/reports/population.json"
    forged = json.loads(report_path.read_bytes())
    forged["summary"]["planned_completion"]["numerator"] = 1
    forged["semantic_sha256"] = hashlib.sha256(
        json.dumps(
            {k: v for k, v in forged.items() if k != "semantic_sha256"},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    report_path.write_text(json.dumps(forged), encoding="utf-8")
    index_path = revision / "tracks/research/index.json"
    index = json.loads(index_path.read_bytes())
    index["tracks"]["population"].update(semantic_sha256=forged["semantic_sha256"])
    index["tracks"]["population"]["json"]["sha256"] = hashlib.sha256(
        report_path.read_bytes()
    ).hexdigest()
    index_path.write_text(json.dumps(index, sort_keys=True), encoding="utf-8")
    configuration_path = revision / "configuration.json"
    config = json.loads(configuration_path.read_bytes())
    config["research"] = index
    for path in (report_path, index_path):
        config["raw_artifacts"][path.relative_to(revision).as_posix()] = base64.b64encode(
            path.read_bytes()
        ).decode("ascii")
    configuration_path.write_text(json.dumps(config), encoding="utf-8")
    summary_path = revision / "summary.json"
    summary = json.loads(summary_path.read_bytes())
    summary["tracks"]["research"]["tracks"]["population"].update(
        semantic_sha256=forged["semantic_sha256"]
    )
    summary["tracks"]["research"]["tracks"]["population"]["json"]["sha256"] = hashlib.sha256(
        report_path.read_bytes()
    ).hexdigest()
    summary["tracks"]["research"]["index"]["sha256"] = hashlib.sha256(
        index_path.read_bytes()
    ).hexdigest()
    summary_path.write_text(json.dumps(summary), encoding="utf-8")
    lineage_path = revision / "lineage.json"
    lineage = json.loads(lineage_path.read_bytes())
    lineage["summary_sha256"] = hashlib.sha256(summary_path.read_bytes()).hexdigest()
    lineage_path.write_text(json.dumps(lineage), encoding="utf-8")
    reclose_revision(revision)
    replay = installed_cli("suite", "replay", directory, evaluation_offline=True)
    assert replay.returncode == 2, replay.stdout + replay.stderr
    assert "replay differs" in json.loads(replay.stdout)["reason"]


def test_opportunity_subset_links_observed_benefits_without_loading_relevance(
    suite_material, installed_cli, batch, pair_case
):
    source, directory, declaration = suite_material
    material = native_research_material(batch, pair_case)
    path = material[-1]()
    declaration["tracks"] = {
        "research": {
            "schema_version": "rtpeval_suite_research_1",
            "declaration_ref": population_tests.save(
                source.parent, path.name, json.loads(path.read_bytes())
            ),
            "selected_tracks": ["opportunities", "tradeoffs"],
        }
    }
    source.write_text(json.dumps(declaration), encoding="utf-8")
    result = installed_cli(
        "suite", "prepare", source, "--directory", directory, evaluation_offline=True
    )
    assert result.returncode == 0, result.stdout + result.stderr
    index = json.loads((directory / "tracks/research/index.json").read_bytes())
    assert index["tracks"]["relevance"]["processing_status"] == "not_requested"
    rag = index["benefit_resource_links"][0]
    assert rag["status"] == "matched"
    assert rag["benefit"]["track"] == "opportunities"
    assert rag["benefit"]["pointer"] == "/cross_version/0"
    assert rag["resources"]["pointer"] == "/paired_comparisons/0/rows/0"
    assert index["benefit_resource_links"][1]["status"] == "unavailable"


def test_missing_selected_usage_retains_partial_benefit_links_and_native_quality(
    suite_material, installed_cli, batch, pair_case
):
    source, directory, declaration = suite_material
    material = native_research_material(batch, pair_case)
    next(a for a in material[3]["attempts"] if a["version"] == "v2").pop("usage_ref")
    path = material[-1]()
    declaration["tracks"] = {
        "research": {
            "schema_version": "rtpeval_suite_research_1",
            "declaration_ref": population_tests.save(
                source.parent, path.name, json.loads(path.read_bytes())
            ),
            "selected_tracks": ["relevance", "tradeoffs", "repair"],
        }
    }
    source.write_text(json.dumps(declaration), encoding="utf-8")
    result = installed_cli(
        "suite", "prepare", source, "--directory", directory, evaluation_offline=True
    )
    assert result.returncode == 0, result.stdout + result.stderr
    prepared = json.loads((directory / "preparation.json").read_bytes())
    assert len(prepared["cases"]) == 3
    index = prepared["track_configuration"]["research"]
    assert index["tracks"]["tradeoffs"]["measurement_coverage"]["missing_usage_attempts"] == 1
    assert [r["status"] for r in index["benefit_resource_links"]] == [
        "partial",
        "partial",
        "matched",
    ]
    assert index["benefit_resource_links"][0]["selected_attempts"][1]["usage_sha256"] is None
    resources = json.loads((directory / index["tracks"]["tradeoffs"]["json"]["path"]).read_bytes())
    assert resources["all_attempts"]["ledger_complete"] is False
    assert resources["all_attempts"]["totals"]["total_tokens"]["total"] is None
    assert resources["all_attempts"]["totals"]["total_tokens"]["observed_subtotal"] == 300
    assert resources["paired_comparisons"][0]["native_quality_pairs"] == 1


def test_research_controlled_targets_keep_expected_inventory_separate_from_generation(
    suite_material, research_material, installed_cli
):
    from backend.tests.test_rtpeval_research_controlled_cli import declared_controlled

    source, directory, declaration = suite_material
    research_material[1]["cases"] = research_material[1]["cases"][:1]
    path, _ = declared_controlled(research_material)
    nested = source.parent / "research"
    shutil.copytree(path.parent, nested)
    declaration["tracks"] = {
        "research": {
            "schema_version": "rtpeval_suite_research_1",
            "declaration_ref": {
                **population_tests.save(nested, "research.json", json.loads(path.read_bytes())),
                "path": "research/research.json",
            },
            "selected_tracks": ["population", "repair", "tradeoffs"],
        }
    }
    source.write_text(json.dumps(declaration), encoding="utf-8")
    result = installed_cli(
        "suite",
        "prepare",
        source,
        "--directory",
        directory,
        evaluation_offline=True,
        tools_offline=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    prepared = json.loads((directory / "preparation.json").read_bytes())
    index = prepared["track_configuration"]["research"]
    controlled = json.loads((directory / index["tracks"]["repair"]["json"]["path"]).read_bytes())[
        "controlled"
    ]
    assert (controlled["resolution"]["numerator"], controlled["resolution"]["denominator"]) == (
        1,
        3,
    )
    assert (
        controlled["verdict_coverage"]["available"],
        controlled["verdict_coverage"]["expected"],
    ) == (2, 3)
    assert (
        controlled["case_joint_success"]["numerator"],
        controlled["case_joint_success"]["denominator"],
    ) == (0, 2)
    assert index["population"]["planned_slots"] == 4
    assert index["controlled_resource_link"]["applicability"] == "not_applicable"
    tradeoffs = json.loads((directory / index["tracks"]["tradeoffs"]["json"]["path"]).read_bytes())
    assert tradeoffs["all_attempts"]["dispatched_attempts"] == 0
    assert tradeoffs["all_attempts"]["ledger_complete"] is False
    snapshot_raws = [p for p in index["tracks"]["repair"]["source_dependencies"] if "/raw/" in p]
    assert snapshot_raws
    assert all((directory / p).read_bytes() for p in snapshot_raws)


def test_report_rejects_rehashed_initial_research_summary_before_fresh_revision(
    suite_material, research_material, installed_cli, monkeypatch, capsys
):
    from backend.tests.test_rtpeval_suite_external_cli import execute_fixture

    source, directory, declaration = suite_material
    research_material[1]["cases"] = research_material[1]["cases"][:1]
    declaration["tracks"] = {
        "research": research_attachment(research_material, source.parent, ["population"])
    }
    source.write_text(json.dumps(declaration), encoding="utf-8")
    execute_fixture(source, directory, monkeypatch, capsys)
    summary = json.loads((directory / "summary.json").read_bytes())
    summary["tracks"]["research"]["tracks"]["population"]["measurement_coverage"][
        "planned_slots"
    ] = 99
    (directory / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    reclose_revision(directory)
    preserved = {p: p.read_bytes() for p in directory.rglob("*") if p.is_file()}
    result = installed_cli("suite", "report", directory, evaluation_offline=True)
    assert result.returncode == 2, result.stdout + result.stderr
    assert "research" in json.loads(result.stdout)["reason"].lower()
    assert {p: p.read_bytes() for p in preserved} == preserved
    assert not (directory / "reports").exists()


@pytest.mark.parametrize("with_cost", [False, True, "zero"])
def test_missing_tokens_preserves_known_elapsed_calls_and_http_in_partial_links(
    suite_material, installed_cli, batch, pair_case, with_cost
):
    source, directory, declaration = suite_material
    material = native_research_material(batch, pair_case, tokens_missing=True)
    path = material[-1]()
    if with_cost:
        from backend.tests.test_rtpeval_research_tradeoffs_cli import cost_track

        value = json.loads(path.read_bytes())
        track = json.loads((material[0] / value["track_refs"]["tradeoffs"]["path"]).read_bytes())
        track["cost_ledgers"] = cost_track(material, material[3]["attempts"])["cost_ledgers"]
        if with_cost == "zero":
            ledger = track["cost_ledgers"][0]
            prices = json.loads((material[0] / ledger["prices_ref"]["path"]).read_bytes())
            for row in prices["rows"]:
                row["rates"] = {key: "0" for key in row["rates"]}
            ledger["prices_ref"] = population_tests.save(material[0], "prices-USD.json", prices)
        value["track_refs"]["tradeoffs"] = population_tests.save(
            material[0], "tradeoffs-material.json", track
        )
        population_tests.save(material[0], path.name, value)
    declaration["tracks"] = {
        "research": {
            "schema_version": "rtpeval_suite_research_1",
            "declaration_ref": population_tests.save(
                source.parent, path.name, json.loads(path.read_bytes())
            ),
            "selected_tracks": ["relevance", "tradeoffs", "repair"],
        }
    }
    source.write_text(json.dumps(declaration), encoding="utf-8")
    result = installed_cli(
        "suite", "prepare", source, "--directory", directory, evaluation_offline=True
    )
    assert result.returncode == 0, result.stderr
    index = json.loads((directory / "preparation.json").read_bytes())["track_configuration"][
        "research"
    ]
    resources = json.loads((directory / index["tracks"]["tradeoffs"]["json"]["path"]).read_bytes())
    for resource in resources["all_attempts"]["rows"]:
        assert resource["metrics"]["elapsed_seconds"] == 10
        assert resource["metrics"]["model_calls"] == 1
        assert resource["metrics"]["http_sends"] == 0
        assert resource["metrics"]["total_tokens"] is None
    for link in index["benefit_resource_links"]:
        assert link["source_compatible"] is True
        assert link["status"] == "partial"
        assert link["resource_status"] == "partial"
        coverage = link["resource_measurement_coverage"]
        assert coverage["total_tokens"]["missing_attempts"] == len(link["selected_attempts"])
        assert coverage["elapsed_seconds"]["known_attempts"] == len(link["selected_attempts"])
        if with_cost:
            assert coverage["cost"]["observed_attempts"] == len(link["selected_attempts"])
            assert coverage["cost"]["missing_attempts"] == 0
            assert coverage["cost"]["by_mode"]["actual"]["known_total_attempts"] == 0
            assert coverage["cost"]["by_mode"]["actual"]["missing_total_attempts"] == len(
                link["selected_attempts"]
            )
            assert coverage["cost"]["by_mode"]["estimated"]["known_total_attempts"] == len(
                link["selected_attempts"]
            )
    if with_cost:
        assert [
            r["cost"]["native"]["estimated_total"] for r in resources["all_attempts"]["rows"]
        ] == (
            ["0", "0", "0", "0"]
            if with_cost == "zero"
            else ["0.00024", "0.00024", "0.00034", "0.00024"]
        )
