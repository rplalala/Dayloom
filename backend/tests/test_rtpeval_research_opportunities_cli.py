"""Installed offline opportunity stages use canonical places and native source bindings."""

import json

import pytest

from backend.tests.test_rtpeval_research_population_cli import add_attempt, save

pytest_plugins = ("backend.tests.test_rtpeval_research_population_cli",)


def write_track(material, observations):
    root, _, _, _, write = material
    path = write()
    declaration = json.loads(path.read_text())
    declaration["track_refs"]["opportunities"] = save(
        root,
        "opportunities-input.json",
        {
            "schema_version": "rtpeval_research_opportunities_1",
            "observations": observations,
        },
    )
    save(root, path.name, declaration)
    return path


def report(installed_cli, material, observations, directory):
    result = installed_cli(
        "research",
        "report",
        write_track(material, observations),
        "--track",
        "opportunities",
        "--directory",
        directory,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads((directory / "opportunities.json").read_text())


def test_missing_history_retains_all_v1_v2_slots_without_reconstruction(
    installed_cli,
    research_material,
    tmp_path,
):
    value = report(installed_cli, research_material, [], tmp_path / "out")
    assert len(value["runs"]) == 40
    assert value["runs"][0]["stages"]["discovered"] == {
        "status": "unavailable",
        "canonical_ids": [],
        "observed_count": 0,
        "complete_count": None,
        "reasons": ["missing_historical_capture"],
        "origin_partitions": {"google_only": [], "rag_only": [], "mixed": []},
    }
    assert value["identity_unit"] == "canonical_place_id"
    assert value["runs"][0]["scheduled"]["complete_count"] is None


def observation(material, version="v2"):
    root, population, _, _, _ = material
    population["cases"] = population["cases"][:1]
    attempt = add_attempt(material, 0, version, "failed")
    google = {
        "intent_id": "interest-1",
        "source_query": "museums Sydney",
        "provider_rank": 0,
        "actual_result_count": 3,
    }
    rag = {
        "entity_id": "entity-1",
        "query": {
            "query_id": "q1",
            "text": "museums",
            "origin": "user",
            "version": "rag_query_plan_1",
            "intent_ids": ["interest-1"],
            "requirement_refs": ["r1"],
        },
        "rank": 1,
        "cosine": 0.9,
        "distance_km": 1,
        "artifact_hash": "a" * 64,
        "text_hash": "b" * 64,
        "space_id": "pinned",
        "policy_version": "p1",
        "resolution": "direct_id",
        "evidence_ref": "google_places:b",
    }
    places = [
        {"canonical_place_id": "a", "google_origins": [google], "rag_origins": []},
        {"canonical_place_id": "b", "google_origins": [google], "rag_origins": [rag]},
        {
            "canonical_place_id": "b",
            "google_origins": [],
            "rag_origins": [{**rag, "entity_id": "entity-2"}],
        },
        {
            "canonical_place_id": "c",
            "google_origins": [],
            "rag_origins": [{**rag, "evidence_ref": "google_places:c"}],
        },
    ]
    capture = {
        "schema_version": "rtpeval_candidate_capture_1",
        "version": version,
        "run_id": attempt["run_id"],
        "pre_rag_google_ids": ["a", "b"],
        "stages": {
            name: {"status": "complete", "places": places[:count], "reasons": []}
            for name, count in (
                ("discovered", 4),
                ("admitted", 4),
                ("enriched", 3),
                ("supplied", 2),
            )
        },
        "omissions": [{"canonical_place_id": "c", "stage": "enriched", "reason": "details_limit"}],
        "rag": {"queries": [rag["query"]], "omitted_queries": [], "status": "complete"},
    }
    entry = {
        key: attempt[key]
        for key in (
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
    entry.update(result_sha256=None, capture_ref=save(root, "capture.json", capture))
    return entry, capture


def test_canonical_duplicate_and_mixed_origins_keep_same_run_increment_separate(
    installed_cli,
    research_material,
    tmp_path,
):
    entry, _ = observation(research_material)
    value = report(installed_cli, research_material, [entry], tmp_path / "out")
    run = value["runs"][1]
    assert run["stages"]["discovered"]["canonical_ids"] == ["a", "b", "c"]
    assert run["stages"]["discovered"]["complete_count"] == 3
    assert run["stages"]["discovered"]["origin_partitions"] == {
        "google_only": ["a"],
        "mixed": ["b"],
        "rag_only": ["c"],
    }
    assert run["incremental_rag_ids"] == ["c"]
    assert run["stages"]["supplied"]["canonical_ids"] == ["a", "b"]
    assert run["omissions"] == [
        {"canonical_place_id": "c", "stage": "enriched", "reason": "details_limit"}
    ]
    assert len(run["places"]["b"]["rag_origins"]) == 2
    assert run["scheduled"]["status"] == "unavailable"


def test_partial_stages_preserve_observed_subtotals_and_reject_false_complete_lineage(
    installed_cli,
    research_material,
    tmp_path,
):
    root = research_material[0]
    entry, capture = observation(research_material)
    capture["stages"]["enriched"]["status"] = "partial"
    capture["stages"]["enriched"]["reasons"] = ["truncated_export"]
    entry["capture_ref"] = save(root, "capture.json", capture)
    value = report(installed_cli, research_material, [entry], tmp_path / "partial")
    assert value["runs"][1]["stages"]["enriched"]["observed_count"] == 2
    assert value["runs"][1]["stages"]["enriched"]["complete_count"] is None
    capture["stages"]["enriched"].update(status="complete", places=[])
    entry["capture_ref"] = save(root, "capture.json", capture)
    bad = installed_cli(
        "research", "validate", write_track(research_material, [entry]), "--track", "opportunities"
    )
    assert bad.returncode == 2
    assert "Stage lineage" in bad.stdout


def scheduled_material(material, batch, *, complete=False, extras=False):
    from backend.evaluation.identity import identity_references
    from backend.evaluation.intake import load_batch
    from backend.tests.evaluation.test_identity import details, evidence, plan, review_envelope

    root, population, _, census, _ = material
    entry, capture = observation(material)
    manifest, results, write, _, native_root = batch
    results["v2"]["itinerary"]["days"][0]["activities"][0]["source_place_id"] = "a"
    if complete:
        results["v2"]["itinerary"]["days"][0]["activities"][2]["source_place_id"] = "b"
    if extras:
        from backend.tests.evaluation.test_intake import activity

        results["v2"]["itinerary"]["days"][0]["activities"].append(
            activity("free", "Free time", "12:00", "13:00", "free_time")
        )
        results["v2"]["itinerary"]["reference_recommendations"] = [
            {"place_name": "Nearby C", "source_place_id": "c"}
        ]
        results["v2"]["rag_discovery"] = {"fate": {"scheduled": ["c"]}}
    native_path = write("v2")
    native_intake = load_batch(native_path)
    refs = identity_references(native_intake)
    ref = next(r for r in refs if r["version"] == "v2" and r["name"] == "Museum A")
    records = [details(ref, "Museum A", "a")]
    if complete:
        second = next(r for r in refs if r["version"] == "v2" and r["name"] == "Museum B")
        records.append(details(second, "Museum B", "b"))
    evidence_value = evidence(native_intake, records)
    for path in native_root.glob("*.json"):
        if path.parent == root:
            continue
        (root / path.name).write_bytes(path.read_bytes())
    population["cases"][0]["input_ref"] = manifest["groups"][0]["input_ref"]
    attempt = census["attempts"][0]
    attempt.update(
        input_sha256=population["cases"][0]["input_ref"]["sha256"],
        run_id="run-v2",
        group_id="g",
        result_ref=manifest["groups"][0]["selected_runs"]["v2"]["result_ref"],
    )
    entry.update(
        input_sha256=attempt["input_sha256"],
        run_id="run-v2",
        result_sha256=attempt["result_ref"]["sha256"],
    )
    capture["run_id"] = "run-v2"
    entry["capture_ref"] = save(root, "capture.json", capture)
    entry["identity_sources"] = {
        "mode": "legacy",
        "manifest_ref": save(root, "manifest.json", manifest),
        "evidence_ref": save(root, "identity-evidence.json", evidence_value),
        "audit_ref": save(root, "identity-audit.json", plan(native_intake, count=1)),
        "reviews_ref": save(
            root,
            "identity-reviews.json",
            review_envelope(native_intake, evidence_value["records"][0], ref["reference_id"], "a"),
        ),
    }
    if complete:
        reviews = review_envelope(native_intake, records[0], ref["reference_id"], "a")
        reviews["records"].extend(
            review_envelope(native_intake, records[1], second["reference_id"], "b")["records"]
        )
        entry["identity_sources"]["reviews_ref"] = save(root, "identity-reviews.json", reviews)
    return entry, capture


def test_scheduling_uses_rebuilt_native_identity_not_producer_claims_or_nearby(
    installed_cli,
    research_material,
    batch,
    tmp_path,
):
    entry, _ = scheduled_material(research_material, batch)
    value = report(installed_cli, research_material, [entry], tmp_path / "scheduled")
    row = value["runs"][1]
    assert row["scheduled"]["canonical_ids"] == ["a"]
    assert row["scheduled"]["observed_count"] == 1
    assert row["scheduled"]["complete_count"] is None  # Museum B remains independently unresolved.
    assert "unresolved_final_place_association" in row["scheduled"]["reasons"]
    assert row["scheduled"]["associations"][0]["canonical_place_id"] == "a"
    assert row["scheduled"]["associations"][0]["decision_route"] == "human_adjudication"


def test_cross_run_v1_v2_changes_are_separate_from_same_v2_rag_additions(
    installed_cli,
    research_material,
    tmp_path,
):
    root = research_material[0]
    entry2, capture2 = observation(research_material)
    attempt1 = add_attempt(research_material, 0, "v1", "failed")
    capture1 = {
        **capture2,
        "version": "v1",
        "run_id": attempt1["run_id"],
        "pre_rag_google_ids": ["a"],
        "omissions": [],
        "rag": None,
    }
    capture1["stages"] = {
        name: {
            "status": "complete",
            "places": [capture2["stages"][name]["places"][0]],
            "reasons": [],
        }
        for name in ("discovered", "admitted", "enriched", "supplied")
    }
    entry1 = {
        key: attempt1[key]
        for key in (
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
    entry1.update(result_sha256=None, capture_ref=save(root, "capture-v1.json", capture1))
    value = report(installed_cli, research_material, [entry1, entry2], tmp_path / "cross")
    assert value["cross_version"][0]["discovered"] == {
        "status": "complete",
        "v2_added_ids": ["b", "c"],
        "v1_only_ids": [],
    }
    assert value["runs"][1]["incremental_rag_ids"] == ["c"]


@pytest.mark.parametrize(
    "fault",
    [
        "foreign_attempt",
        "hash_drift",
        "invalid_rank",
        "unknown_stage",
        "false_google_pre_rag",
        "invalid_json",
        "foreign_native_result",
    ],
)
def test_malformed_or_foreign_sources_fail_validation_without_outputs(
    installed_cli,
    research_material,
    batch,
    tmp_path,
    fault,
):
    root = research_material[0]
    entry, capture = (
        scheduled_material(research_material, batch)
        if fault == "foreign_native_result"
        else observation(research_material)
    )
    if fault == "foreign_attempt":
        entry["attempt_id"] = "foreign"
    elif fault == "invalid_rank":
        capture["stages"]["discovered"]["places"][0]["google_origins"][0]["provider_rank"] = -1
    elif fault == "unknown_stage":
        capture["stages"]["fabricated"] = capture["stages"]["discovered"]
    elif fault == "false_google_pre_rag":
        capture["pre_rag_google_ids"] = ["c"]
    elif fault == "foreign_native_result":
        native = json.loads((root / "manifest.json").read_text())
        native["groups"][0]["selected_runs"]["v2"]["run_id"] = "foreign-native-run"
        entry["identity_sources"]["manifest_ref"] = save(root, "manifest.json", native)
    entry["capture_ref"] = save(root, "capture.json", capture)
    path = write_track(research_material, [entry])
    if fault == "hash_drift":
        (root / "capture.json").write_text("{}")
    elif fault == "invalid_json":
        entry["capture_ref"] = save(root, "capture.json", capture)
        raw = '{"schema_version":"rtpeval_candidate_capture_1","schema_version":"bad"}'
        (root / "capture.json").write_text(raw)
        import hashlib

        entry["capture_ref"]["sha256"] = hashlib.sha256(
            (root / "capture.json").read_bytes()
        ).hexdigest()
        path = write_track(research_material, [entry])
    result = installed_cli(
        "research", "report", path, "--track", "opportunities", "--directory", tmp_path / "invalid"
    )
    assert result.returncode == 2
    assert not (tmp_path / "invalid").exists()


def test_complete_schedule_excludes_nearby_and_generic_with_producer_fate_conflict(
    installed_cli,
    research_material,
    batch,
    tmp_path,
):
    entry, _ = scheduled_material(research_material, batch, complete=True, extras=True)
    value = report(installed_cli, research_material, [entry], tmp_path / "full-schedule")
    row = value["runs"][1]
    assert row["scheduled"]["canonical_ids"] == ["a", "b"]
    assert row["scheduled"]["complete_count"] == 2
    assert row["scheduled"]["status"] == "complete"
    assert "producer_scheduled_fate_conflicts_with_independent_associations" in row["diagnostics"]
    assert value["review_coverage"]["independent_association_slots"] == 1
    assert value["measurement_coverage"]["stages"]["scheduled"] == {
        "complete": 1,
        "partial": 0,
        "unavailable": 1,
    }
    assert value["diagnostics"] == [
        {
            **{
                key: row[key]
                for key in ("case_id", "case_revision", "version", "repetition_id", "attempt_id")
            },
            "reason": reason,
        }
        for reason in row["diagnostics"]
    ]
    assert all(
        "reference_recommendations" not in item["source"]["pointer"]
        for item in row["scheduled"]["associations"]
    )


def test_partial_rag_origin_is_invalid_material_and_markdown_has_full_source_links(
    installed_cli,
    research_material,
    tmp_path,
):
    root = research_material[0]
    entry, capture = observation(research_material)
    value = report(installed_cli, research_material, [entry], tmp_path / "valid")
    originals = {path: path.read_bytes() for path in root.glob("*.json")}
    second = report(installed_cli, research_material, [entry], tmp_path / "again")
    assert value["semantic_sha256"] == second["semantic_sha256"]
    assert originals == {path: path.read_bytes() for path in originals}
    rendered = (tmp_path / "valid" / "opportunities.md").read_text()
    assert "capture.json" in rendered
    assert entry["capture_ref"]["sha256"] in rendered
    assert "scheduled" in rendered
    capture["stages"]["discovered"]["places"][2]["rag_origins"][0]["rank"] = 0
    entry["capture_ref"] = save(root, "capture.json", capture)
    result = installed_cli(
        "research", "validate", write_track(research_material, [entry]), "--track", "opportunities"
    )
    assert result.returncode == 2


def test_final_semantic_binding_rejects_capture_for_different_output(
    installed_cli,
    research_material,
    batch,
    tmp_path,
):
    entry, capture = scheduled_material(research_material, batch)
    capture["result_semantic_sha256"] = "f" * 64
    entry["capture_ref"] = save(research_material[0], "capture.json", capture)
    result = installed_cli(
        "research", "validate", write_track(research_material, [entry]), "--track", "opportunities"
    )
    assert result.returncode == 2
    assert "Capture final semantic" in result.stdout


@pytest.mark.parametrize("applicable", [True, False])
def test_opportunity_report_envelope_describes_coverage_and_applicability(
    installed_cli, research_material, tmp_path, applicable
):
    import hashlib

    if not applicable:
        for case in research_material[1]["cases"]:
            case["planned_versions"] = ["v0", "v3"]
    value = report(installed_cli, research_material, [], tmp_path / "envelope")
    planned = 40 if applicable else 0
    assert value["processing_status"] == "completed"
    assert value["track"] == "opportunities"
    assert value["applicability"] == ("applicable" if applicable else "not_applicable")
    assert value["measurement_coverage"] == {
        "unit": "planned_v1_v2_slots",
        "planned_slots": planned,
        "captured_slots": 0,
        "stages": {
            stage: {"complete": 0, "partial": 0, "unavailable": planned}
            for stage in ("discovered", "admitted", "enriched", "supplied", "scheduled")
        },
    }
    assert value["review_coverage"] == {
        "unit": "planned_v1_v2_slots",
        "independent_association_slots": 0,
        "relevance_review": "not_performed",
    }
    expected_digest = hashlib.sha256(
        json.dumps(
            research_material[1], ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()
    assert value["population_digest"] == expected_digest
    assert value["diagnostics"] == []
    assert len(value["runs"]) == planned


def test_opportunity_envelope_counts_partial_capture_without_claiming_review(
    installed_cli, research_material, tmp_path
):
    entry, capture = observation(research_material)
    capture["stages"]["enriched"]["status"] = "partial"
    capture["stages"]["enriched"]["reasons"] = ["truncated_export"]
    entry["capture_ref"] = save(research_material[0], "capture.json", capture)
    value = report(installed_cli, research_material, [entry], tmp_path / "covered")
    assert value["measurement_coverage"]["planned_slots"] == 2
    assert value["measurement_coverage"]["captured_slots"] == 1
    assert value["measurement_coverage"]["stages"]["enriched"] == {
        "complete": 0,
        "partial": 1,
        "unavailable": 1,
    }
    assert value["measurement_coverage"]["stages"]["discovered"] == {
        "complete": 1,
        "partial": 0,
        "unavailable": 1,
    }
    assert value["review_coverage"]["independent_association_slots"] == 0
