"""Literal independent labels and pinned coverage through the installed offline CLI."""

import copy
import json

import pytest

from backend.tests.test_rtpeval_research_population_cli import add_attempt, save

pytest_plugins = ("backend.tests.test_rtpeval_research_population_cli",)


def write_relevance(
    material, observations=(), *, inventories=(), reviews=(), coverage=(), profile=None
):
    root, population, selection, _, write = material
    path = write()
    declaration = json.loads(path.read_text(encoding="utf-8"))
    declaration["track_refs"]["opportunities"] = save(
        root,
        "opportunities.json",
        {
            "schema_version": "rtpeval_research_opportunities_1",
            "observations": list(observations),
        },
    )
    declaration["track_refs"]["relevance"] = save(
        root,
        "relevance-material.json",
        {
            "schema_version": "rtpeval_research_relevance_1",
            "population_id": population["population_id"],
            "population_revision": population["revision"],
            "profile_id": selection["profile_id"],
            "profile_revision": selection["revision"],
            "interest_inventory_refs": list(inventories),
            "review_refs": list(reviews),
            "coverage_refs": list(coverage),
            "coverage_profile_ref": profile,
        },
    )
    save(root, path.name, declaration)
    return path


def get_report(installed_cli, declaration, directory):
    result = installed_cli(
        "research", "report", declaration, "--track", "relevance", "--directory", directory
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads((directory / "relevance.json").read_text(encoding="utf-8"))


def test_absent_independent_material_does_not_turn_queries_into_relevance(
    installed_cli, research_material, tmp_path
):
    population = research_material[1]
    population["cases"] = population["cases"][:1]
    declaration = write_relevance(research_material)
    report = get_report(installed_cli, declaration, tmp_path / "absent")
    assert report["processing_status"] == "completed"
    assert len(report["runs"]) == 2
    assert report["runs"][0]["relevance_status"] == "unavailable"
    assert report["runs"][0]["stages"]["discovered"]["complete_count"] is None
    assert report["comparisons"][0]["end_to_end"]["delta"] is None
    assert report["coverage"][0]["eligible_entity_count"] is None
    assert report["coverage"][0]["status"] == "unavailable"


def interest_inventory(material, *, interests=("architecture", "museums"), use_existing=False):
    root, population, _, _, _ = material
    population["cases"] = population["cases"][:1]
    case = population["cases"][0]
    if not use_existing:
        case["input_ref"] = save(
            root,
            "original.json",
            {
                "destination": "Sydney",
                "additional_preferences": "Architecture and museums"
                if interests
                else "No POI interests requested",
            },
        )
    source_text = json.loads((root / case["input_ref"]["path"]).read_text())[
        "additional_preferences"
    ]
    spec = {
        "schema_version": "rtpeval_requirements_1",
        "spec_id": "independent-spec",
        "revision": "s1",
        "group_id": "review-case-1",
        "input_sha256": case["input_ref"]["sha256"],
        "review": {
            "status": "reviewed",
            "reviewer_ref": "independent-human",
            "reviewed_at": "2026-10-01T00:00:00Z",
        },
        "subjects": [],
        "obligations": [],
        "unresolved_items": [],
        "soft_preferences": [
            {"preference_id": interest, "kind": "poi_interest"} for interest in interests
        ],
    }
    spec_ref = save(root, "reviewed-requirements.json", spec)
    inventory = {
        "schema_version": "rtpeval_research_interests_1",
        "case_id": case["case_id"],
        "case_revision": case["revision"],
        "input_sha256": case["input_ref"]["sha256"],
        "requirement_spec_ref": spec_ref,
        "revision": "i1",
        "reviewer_ref": "independent-human",
        "reviewer_kind": "human",
        "reviewed_at": "2026-10-01T00:00:00Z",
        "rationale": "Independent original preference inventory",
        "interests": [
            {
                "interest_id": interest,
                "source_pointer": "/additional_preferences",
                "source_text": source_text,
                "requirement_pointer": f"/soft_preferences/{index}",
            }
            for index, interest in enumerate(interests)
        ],
    }
    return save(root, "interests.json", inventory), inventory


def labels(material, inventory_ref, inventory, verdicts):
    root = material[0]
    records = []
    for interest_id, place_id, verdict in verdicts:
        records.append(
            {
                "review_id": interest_id + "-" + place_id,
                "revision": "review-r1",
                "case_id": inventory["case_id"],
                "case_revision": inventory["case_revision"],
                "input_sha256": inventory["input_sha256"],
                "interest_inventory_sha256": inventory_ref["sha256"],
                "requirement_spec_sha256": inventory["requirement_spec_ref"]["sha256"],
                "interest_id": interest_id,
                "source_pointer": "/additional_preferences",
                "canonical_place_id": place_id,
                "unresolved_subject_id": None,
                "venue_evidence_refs": [
                    save(
                        root,
                        "venue-" + place_id + ".json",
                        {
                            "source_kind": "independent_reviewed_description",
                            "canonical_place_id": place_id,
                            "description": "Saved independent venue material for synthetic review",
                        },
                    )
                ],
                "reviewer_ref": "independent-human",
                "reviewer_kind": "human",
                "reviewed_at": "2026-10-02T00:00:00Z",
                "rationale": "Literal fixture verdict",
                "verdict": verdict,
            }
        )
    return save(
        root,
        "relevance-reviews.json",
        {"schema_version": "rtpeval_research_relevance_reviews_1", "records": records},
    )


def discovery(material, version="v2"):
    from backend.tests.test_rtpeval_research_opportunities_cli import observation

    entry, capture = observation(material, version)
    entry["capture_ref"] = save(material[0], "capture-" + version + ".json", capture)
    return entry, capture


def test_independent_labels_deduplicate_places_over_interests_and_stage_entities(
    installed_cli, research_material, tmp_path
):
    inventory_ref, inventory = interest_inventory(research_material)
    entry, _ = discovery(research_material)
    reviews = labels(
        research_material,
        inventory_ref,
        inventory,
        [
            ("architecture", "a", "relevant"),
            ("architecture", "b", "not_relevant"),
            ("architecture", "c", "relevant"),
            ("museums", "a", "relevant"),
            ("museums", "b", "relevant"),
            ("museums", "c", "not_relevant"),
        ],
    )
    declaration = write_relevance(
        research_material, [entry], inventories=[inventory_ref], reviews=[reviews]
    )
    report = get_report(installed_cli, declaration, tmp_path / "labeled")
    assert report["review_coverage"] == {
        "unit": "original_requests",
        "planned_cases": 1,
        "interest_inventory_cases": 1,
        "relevance_review_cases": 1,
        "relevance_review_records": 6,
    }
    assert report["measurement_coverage"]["opportunities"]["captured_slots"] == 1
    run = report["runs"][1]
    assert run["stages"]["discovered"]["canonical_ids"] == ["a", "b", "c"]
    assert run["stages"]["discovered"]["complete_count"] == 3
    assert run["stages"]["discovered"]["review_coverage"]["judged_subjects"] == 3
    assert run["stages"]["discovered"]["review_coverage"]["inventoried_subjects"] == 3
    assert run["per_interest"][0]["stages"]["discovered"]["complete_count"] == 2
    assert run["per_interest"][1]["stages"]["discovered"]["complete_count"] == 2
    assert run["stages"]["supplied"]["complete_count"] == 2
    assert run["end_to_end"]["complete_count"] is None
    assert run["stages"]["discovered"]["origin_partitions"]["mixed"] == ["b"]
    assert run["stages"]["discovered"]["origin_partitions"] == {
        "google_only": ["a"],
        "rag_only": ["c"],
        "mixed": ["b"],
    }


def native_pair(material, batch):
    from backend.evaluation.identity import identity_references
    from backend.evaluation.intake import load_batch
    from backend.tests.evaluation.test_identity import details, evidence, plan, review_envelope

    root, population, _, census, _ = material
    entry2, capture2 = discovery(material)
    manifest, results, write, _, native_root = batch
    for version in ("v1", "v2"):
        activities = results[version]["itinerary"]["days"][0]["activities"]
        activities[0]["source_place_id"] = "a"
        activities[2]["source_place_id"] = "d" if version == "v1" else "b"
        if version == "v1":
            activities[2].update(title="Museum D", place_name="Museum D")
        write(version)
    native = load_batch(write())
    refs = identity_references(native)
    records, reviews = [], None
    for version, name, pid in (
        ("v1", "Museum A", "a"),
        ("v1", "Museum D", "d"),
        ("v2", "Museum A", "a"),
        ("v2", "Museum B", "b"),
    ):
        reference = next(r for r in refs if r["version"] == version and r["name"] == name)
        record = details(reference, name, pid)
        records.append(record)
        reviewed = review_envelope(native, record, reference["reference_id"], pid)
        if reviews is None:
            reviews = reviewed
        else:
            reviews["records"].extend(reviewed["records"])
    for path in native_root.glob("*.json"):
        (root / path.name).write_bytes(path.read_bytes())
    population["cases"][0]["input_ref"] = manifest["groups"][0]["input_ref"]
    attempt2 = census["attempts"][0]
    attempt2.update(
        input_sha256=population["cases"][0]["input_ref"]["sha256"],
        run_id="run-v2",
        group_id="g",
        result_ref=manifest["groups"][0]["selected_runs"]["v2"]["result_ref"],
    )
    completion = json.loads((root / attempt2["completion_ref"]["path"]).read_text())
    completion.update(
        workflow_status="completed",
        required_mechanisms={"generation": "completed", "retrieval": "completed"},
    )
    attempt2["completion_ref"] = save(root, attempt2["completion_ref"]["path"], completion)
    attempt1 = add_attempt(material, 0, "v1", "completed")
    attempt1.update(
        run_id="run-v1",
        group_id="g",
        result_ref=manifest["groups"][0]["selected_runs"]["v1"]["result_ref"],
    )
    identity_sources = {
        "mode": "legacy",
        "manifest_ref": save(root, "manifest.json", manifest),
        "evidence_ref": save(root, "identity-evidence.json", evidence(native, records)),
        "audit_ref": save(root, "identity-audit.json", plan(native, count=1)),
        "reviews_ref": save(root, "identity-reviews.json", reviews),
    }
    capture1 = copy.deepcopy(capture2)
    source_a = copy.deepcopy(capture2["stages"]["discovered"]["places"][0])
    source_d = {**copy.deepcopy(source_a), "canonical_place_id": "d"}
    capture1.update(
        version="v1", run_id="run-v1", pre_rag_google_ids=["a", "d"], omissions=[], rag=None
    )
    capture1["stages"] = {
        name: {"status": "complete", "places": [source_a, source_d], "reasons": []}
        for name in ("discovered", "admitted", "enriched", "supplied")
    }
    capture2["run_id"] = "run-v2"
    entries = []
    for attempt, capture in ((attempt1, capture1), (attempt2, capture2)):
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
        entry.update(
            result_sha256=attempt["result_ref"]["sha256"],
            capture_ref=save(root, "capture-" + attempt["version"] + ".json", capture),
            identity_sources=identity_sources,
        )
        entries.append(entry)
    return entries, (capture1, capture2)


def test_complete_pairs_preserve_chain_intersection_and_signed_composition_changes(
    installed_cli, research_material, batch, tmp_path
):
    entries, _ = native_pair(research_material, batch)
    inventory_ref, inventory = interest_inventory(
        research_material, interests=("architecture",), use_existing=True
    )
    reviews = labels(
        research_material,
        inventory_ref,
        inventory,
        [("architecture", pid, "relevant") for pid in ("a", "b", "c", "d")],
    )
    declaration = write_relevance(
        research_material, entries, inventories=[inventory_ref], reviews=[reviews]
    )
    report = get_report(installed_cli, declaration, tmp_path / "paired")
    assert report["runs"][0]["end_to_end"]["canonical_ids"] == ["a", "d"]
    assert report["runs"][1]["end_to_end"]["canonical_ids"] == ["a", "b"]
    assert report["runs"][1]["stages"]["scheduled"]["origin_partitions"] == {
        "google_only": ["a"],
        "rag_only": [],
        "mixed": ["b"],
    }
    paired = report["comparisons"][0]
    assert paired["end_to_end"] == {
        "status": "complete",
        "delta": 0,
        "v1_count": 2,
        "v2_count": 2,
        "gained_ids": ["b"],
        "lost_ids": ["d"],
        "retained_ids": ["a"],
        "reasons": [],
    }
    assert paired["stages"]["discovered"]["delta"] == 1
    assert report["runs"][1]["conversions"]["admitted_to_supplied"]["numerator"] == 2
    assert report["runs"][1]["conversions"]["admitted_to_supplied"]["denominator"] == 3
    assert report["runs"][1]["conversions"]["supplied_to_scheduled"]["fraction"] == 1.0


def corpus_coverage(material, *, count=0, status="complete", timing="prospective"):
    from backend.evaluation.research.sources import digest

    root, population, _, _, _ = material
    population["cases"] = population["cases"][:1]
    case = population["cases"][0]
    snapshot = save(
        root,
        "pinned-corpus.json",
        {"artifact_sha256": "a" * 64, "policy_version": "policy-1", "space_id": "space-1"},
    )
    scope = {"kind": "radius", "latitude": -33.86, "longitude": 151.21, "radius_m": 5000}
    identity = {
        "snapshot_ref": snapshot,
        "artifact_sha256": "a" * 64,
        "policy_version": "policy-1",
        "space_id": "space-1",
        "identity_pointers": {
            "artifact_sha256": "/artifact_sha256",
            "policy_version": "/policy_version",
            "space_id": "/space_id",
        },
    }
    binding = {
        "case_id": case["case_id"],
        "case_revision": case["revision"],
        "input_sha256": case["input_ref"]["sha256"],
        "scope": scope,
        "scope_sha256": digest(scope),
    }
    coverage = {
        "schema_version": "rtpeval_research_corpus_coverage_1",
        **binding,
        "snapshot_identity": identity,
        "measurement_method": "Exact offline eligible entity census",
        "measured_at": "2026-10-02T00:00:00Z",
        "declared_at": "2026-10-01T00:00:00Z",
        "timing_basis": timing,
        "count_status": status,
        "eligible_entity_count": count if status == "complete" else None,
        "observed_subtotal": count,
        "reasons": [] if status == "complete" else ["limited_processing"],
    }
    profile = {
        "schema_version": "rtpeval_research_coverage_profile_1",
        "coverage_profile_id": "fixed-strata",
        "revision": "r1",
        "population_id": population["population_id"],
        "population_revision": population["revision"],
        "declared_at": "2026-10-01T00:00:00Z",
        "timing_basis": timing,
        "snapshot_identity": identity,
        "cases": [binding],
        "metric": "eligible_entity_count",
        "strata": [
            {"stratum_id": "empty", "min_inclusive": 0, "max_exclusive": 1},
            {"stratum_id": "available", "min_inclusive": 1, "max_exclusive": None},
        ],
    }
    return coverage, profile


def test_valid_zero_pinned_corpus_retains_exact_scope_and_retrospective_stratum(
    installed_cli, research_material, tmp_path
):
    coverage, profile = corpus_coverage(research_material, timing="retrospective")
    declaration = write_relevance(
        research_material,
        coverage=[save(research_material[0], "coverage.json", coverage)],
        profile=save(research_material[0], "coverage-profile.json", profile),
    )
    report = get_report(installed_cli, declaration, tmp_path / "coverage")
    assert report["measurement_coverage"]["corpus"] == {
        "unit": "original_requests",
        "planned_cases": 1,
        "complete": 1,
        "partial": 0,
        "unavailable": 0,
    }
    row = report["coverage"][0]
    assert row["status"] == "complete"
    assert row["eligible_entity_count"] == 0
    assert row["observed_subtotal"] == 0
    assert row["stratum_id"] == "empty"
    assert row["timing_basis"] == "retrospective"
    assert row["snapshot_identity"]["policy_version"] == "policy-1"
    assert report["coverage_summary"]["strata"][0]["available_pairs"] == 0
    assert report["coverage_summary"]["strata"][0]["omitted_pairs"] == 1
    assert report["coverage_summary"]["strata"][0]["delta_median"] is None


def interest_coverage(material, inventory_ref, coverage, *, unknown=("entity-c",)):
    root = material[0]
    binding = {
        key: coverage[key] for key in ("case_id", "case_revision", "input_sha256", "scope_sha256")
    }
    binding["snapshot_sha256"] = coverage["snapshot_identity"]["snapshot_ref"]["sha256"]
    taxonomy = save(
        root,
        "taxonomy.json",
        {
            "schema_version": "rtpeval_research_interest_taxonomy_1",
            "interest_ids": ["architecture"],
        },
    )
    sample = save(
        root,
        "sample.json",
        {
            "schema_version": "rtpeval_research_corpus_sample_1",
            **binding,
            "entity_ids": ["entity-a", "entity-b", "entity-c"],
        },
    )
    evidence = save(
        root,
        "coding-evidence.json",
        {
            "source_kind": "independent_reviewed_description",
            **binding,
            "entity_ids": ["entity-a", "entity-b", "entity-c"],
            "description": "Offline corpus sample descriptions",
        },
    )
    coding = save(
        root,
        "coding.json",
        {
            "schema_version": "rtpeval_research_corpus_coding_1",
            **binding,
            "taxonomy_sha256": taxonomy["sha256"],
            "sample_sha256": sample["sha256"],
            "interest_inventory_sha256": inventory_ref["sha256"],
            "revision": "coding-r1",
            "reviewer_ref": "independent-human",
            "reviewer_kind": "human",
            "reviewed_at": "2026-10-02T00:00:00Z",
            "rationale": "Independent reviewed entity coding",
            "relevant_entity_ids": ["entity-a", "entity-b"],
            "unknown_entity_ids": list(unknown),
            "evidence_refs": [evidence],
        },
    )
    return save(
        root,
        "interest-coverage.json",
        {
            "schema_version": "rtpeval_research_interest_coverage_1",
            **binding,
            "interest_inventory_sha256": inventory_ref["sha256"],
            "taxonomy_ref": taxonomy,
            "sample_ref": sample,
            "coding_review_ref": coding,
            "numerator": 2,
            "denominator": 3,
            "measurement_method": "Reviewed synthetic sample",
            "uncertainty": "Descriptive finite sample; no population extrapolation",
        },
    )


def test_reviewed_sample_coverage_keeps_unknown_coding_bounds_and_denominator(
    installed_cli, research_material, tmp_path
):
    inventory_ref, _ = interest_inventory(research_material, interests=("architecture",))
    coverage, profile = corpus_coverage(research_material, count=4)
    coverage["interest_coverage_ref"] = interest_coverage(
        research_material, inventory_ref, coverage
    )
    profile["metric"] = "interest_coverage_fraction"
    declaration = write_relevance(
        research_material,
        inventories=[inventory_ref],
        coverage=[save(research_material[0], "coverage.json", coverage)],
        profile=save(research_material[0], "coverage-profile.json", profile),
    )
    report = get_report(installed_cli, declaration, tmp_path / "sampled")
    measured = report["coverage"][0]["interest_coverage"]
    assert measured["status"] == "partial"
    assert measured["numerator"] == 2
    assert measured["denominator"] == 3
    assert measured["fraction"] is None
    assert measured["lower_bound"] == 2 / 3
    assert measured["upper_bound"] == 1.0
    assert measured["unknown_entity_ids"] == ["entity-c"]
    assert report["coverage"][0]["stratum_id"] is None


def test_unknown_absent_and_unresolved_reviews_remain_separate_from_negative(
    installed_cli, research_material, tmp_path
):
    inventory_ref, inventory = interest_inventory(research_material, interests=("architecture",))
    entry, _ = discovery(research_material)
    review_ref = labels(
        research_material,
        inventory_ref,
        inventory,
        [("architecture", "a", "unknown"), ("architecture", "b", "not_relevant")],
    )
    value = json.loads((research_material[0] / review_ref["path"]).read_text())
    unresolved = copy.deepcopy(value["records"][0])
    unresolved.update(
        review_id="unresolved-1",
        canonical_place_id=None,
        unresolved_subject_id="unresolved-museum",
        venue_evidence_refs=[],
    )
    value["records"].append(unresolved)
    review_ref = save(research_material[0], review_ref["path"], value)
    declaration = write_relevance(
        research_material, [entry], inventories=[inventory_ref], reviews=[review_ref]
    )
    report = get_report(installed_cli, declaration, tmp_path / "unknown")
    stage = report["runs"][1]["stages"]["discovered"]
    assert stage["status"] == "partial"
    assert stage["observed_count"] == 0
    assert stage["complete_count"] is None
    assert stage["review_coverage"]["unknown_subjects"] == 1
    assert stage["review_coverage"]["negative_subjects"] == 1
    assert stage["review_coverage"]["absent_review_subjects"] == 1
    assert stage["review_coverage"]["fraction"] == 2 / 3
    assert report["independent_reviews"][2]["unresolved_subject_id"] == "unresolved-museum"
    assert report["independent_reviews"][0]["reviewer_kind"] == "human"


def test_one_planned_version_cannot_fabricate_a_pair(installed_cli, research_material, tmp_path):
    research_material[1]["cases"] = research_material[1]["cases"][:1]
    research_material[1]["cases"][0]["planned_versions"] = ["v2"]
    declaration = write_relevance(research_material)
    report = get_report(installed_cli, declaration, tmp_path / "one-version")
    assert len(report["runs"]) == 1
    assert report["comparisons"][0]["end_to_end"]["delta"] is None
    assert report["comparisons"][0]["end_to_end"]["reasons"] == ["missing_planned_version"]


@pytest.mark.parametrize(
    "field,bad", [("latitude", 91), ("longitude", -181), ("radius_m", -1), ("radius_m", True)]
)
def test_invalid_geographic_scope_is_a_material_error(installed_cli, research_material, field, bad):
    from backend.evaluation.research.sources import digest

    coverage, profile = corpus_coverage(research_material)
    coverage["scope"][field] = bad
    coverage["scope_sha256"] = digest(coverage["scope"])
    profile["cases"][0]["scope_sha256"] = coverage["scope_sha256"]
    declaration = write_relevance(
        research_material,
        coverage=[save(research_material[0], "coverage.json", coverage)],
        profile=save(research_material[0], "coverage-profile.json", profile),
    )
    result = installed_cli("research", "validate", declaration, "--track", "relevance")
    assert result.returncode == 2
    assert "geographic" in result.stdout.lower()


def test_corpus_snapshot_must_match_selected_rag_origins(installed_cli, research_material):
    entry, _ = discovery(research_material)
    coverage, profile = corpus_coverage(research_material, count=4)
    declaration = write_relevance(
        research_material,
        [entry],
        coverage=[save(research_material[0], "coverage.json", coverage)],
        profile=save(research_material[0], "coverage-profile.json", profile),
    )
    result = installed_cli("research", "validate", declaration, "--track", "relevance")
    assert result.returncode == 2
    assert "RAG" in result.stdout


def test_compatible_coverage_strata_emit_case_rows_and_descriptive_median_with_markdown(
    installed_cli, research_material, batch, tmp_path
):
    entries, _ = native_pair(research_material, batch)
    inventory_ref, inventory = interest_inventory(
        research_material, interests=("architecture",), use_existing=True
    )
    reviews = labels(
        research_material,
        inventory_ref,
        inventory,
        [("architecture", pid, "relevant") for pid in ("a", "b", "c", "d")],
    )
    coverage, profile = corpus_coverage(research_material, count=7)
    snapshot = coverage["snapshot_identity"]
    snapshot.update(policy_version="p1", space_id="pinned")
    snapshot["snapshot_ref"] = save(
        research_material[0],
        "pinned-corpus.json",
        {"artifact_sha256": "a" * 64, "policy_version": "p1", "space_id": "pinned"},
    )
    declaration = write_relevance(
        research_material,
        entries,
        inventories=[inventory_ref],
        reviews=[reviews],
        coverage=[save(research_material[0], "coverage.json", coverage)],
        profile=save(research_material[0], "coverage-profile.json", profile),
    )
    report = get_report(installed_cli, declaration, tmp_path / "descriptive")
    stratum = report["coverage_summary"]["strata"][1]
    assert stratum["case_ids"] == ["case-1"]
    assert stratum["available_pairs"] == 1
    assert stratum["omitted_pairs"] == 0
    assert stratum["delta_median"] == 0
    assert report["coverage"][0]["timing_basis"] == "prospective"
    duplicate = get_report(installed_cli, declaration, tmp_path / "again")
    assert report == duplicate
    rendered = (tmp_path / "descriptive" / "relevance.md").read_text()
    for expected in (
        "admitted",
        "supplied",
        "scheduled",
        "architecture",
        "7",
        "available",
        "numerator",
        "denominator",
        "unknown",
        "Source digest",
        "Semantic digest",
        "Descriptive",
    ):
        assert expected in rendered


@pytest.mark.parametrize(
    "mutation",
    [
        "input",
        "inventory",
        "spec",
        "pointer",
        "reviewer",
        "venue",
        "evidence",
        "query_truth",
        "contradiction",
        "interest_pointer",
        "duplicate_interest",
    ],
)
def test_rejected_relevance_source_bindings(installed_cli, research_material, mutation):
    inventory_ref, inventory = interest_inventory(research_material, interests=("architecture",))
    entry, _ = discovery(research_material)
    review_ref = labels(
        research_material, inventory_ref, inventory, [("architecture", "a", "relevant")]
    )
    root = research_material[0]
    value = json.loads((root / review_ref["path"]).read_text())
    record = value["records"][0]
    if mutation in ("input", "inventory", "spec"):
        field = {
            "input": "input_sha256",
            "inventory": "interest_inventory_sha256",
            "spec": "requirement_spec_sha256",
        }[mutation]
        record[field] = "0" * 64
    elif mutation == "pointer":
        record["source_pointer"] = "/foreign"
    elif mutation == "reviewer":
        record["reviewer_kind"] = "planner"
    elif mutation == "venue":
        record["canonical_place_id"] = "foreign-venue"
    elif mutation == "evidence":
        record["venue_evidence_refs"] = []
    elif mutation == "query_truth":
        record["venue_evidence_refs"] = [
            save(
                root,
                "query-evidence.json",
                {"source_kind": "planner_query", "canonical_place_id": "a"},
            )
        ]
    elif mutation == "contradiction":
        value["records"].append({**record, "review_id": "contradictory", "verdict": "not_relevant"})
    elif mutation == "interest_pointer":
        inventory["interests"][0]["requirement_pointer"] = "/soft_preferences/10"
        inventory_ref = save(root, "interests.json", inventory)
        record["interest_inventory_sha256"] = inventory_ref["sha256"]
    elif mutation == "duplicate_interest":
        inventory["interests"].append(copy.deepcopy(inventory["interests"][0]))
        inventory_ref = save(root, "interests.json", inventory)
        record["interest_inventory_sha256"] = inventory_ref["sha256"]
    review_ref = save(root, review_ref["path"], value)
    declaration = write_relevance(
        research_material, [entry], inventories=[inventory_ref], reviews=[review_ref]
    )
    result = installed_cli("research", "validate", declaration, "--track", "relevance")
    assert result.returncode == 2, result.stdout + result.stderr
    assert "needs_material_correction" in result.stdout
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize(
    "mutation",
    ["snapshot", "scope", "count", "false_zero", "threshold", "late", "foreign_case", "duplicate"],
)
def test_rejected_pinned_coverage_material(installed_cli, research_material, mutation):
    from backend.evaluation.research.sources import digest

    root = research_material[0]
    coverage, profile = corpus_coverage(research_material, count=2)
    if mutation == "snapshot":
        coverage["snapshot_identity"] = {
            **coverage["snapshot_identity"],
            "policy_version": "foreign-policy",
        }
    elif mutation == "scope":
        coverage["scope"] = {**coverage["scope"], "radius_m": 1000}
        coverage["scope_sha256"] = digest(coverage["scope"])
    elif mutation == "count":
        coverage["eligible_entity_count"] = True
    elif mutation == "false_zero":
        coverage.update(
            count_status="partial",
            eligible_entity_count=0,
            observed_subtotal=0,
            reasons=["sql_timeout"],
        )
    elif mutation == "threshold":
        profile["strata"][1]["min_inclusive"] = 0
    elif mutation == "late":
        add_attempt(research_material, 0, "v2", "failed")
        profile["declared_at"] = "2026-10-03T00:00:00Z"
    elif mutation == "foreign_case":
        coverage["input_sha256"] = "f" * 64
    refs = [save(root, "coverage.json", coverage)]
    if mutation == "duplicate":
        refs.append(refs[0])
    declaration = write_relevance(
        research_material, coverage=refs, profile=save(root, "coverage-profile.json", profile)
    )
    result = installed_cli("research", "validate", declaration, "--track", "relevance")
    assert result.returncode == 2, result.stdout + result.stderr
    assert "needs_material_correction" in result.stdout


@pytest.mark.parametrize(
    "status,reason", [("partial", "limited_processing"), ("unavailable", "sql_timeout")]
)
def test_incomplete_corpus_subtotals_never_become_exact_zero_or_stratum(
    installed_cli, research_material, tmp_path, status, reason
):
    coverage, profile = corpus_coverage(research_material, status=status)
    coverage["reasons"] = [reason]
    declaration = write_relevance(
        research_material,
        coverage=[save(research_material[0], "coverage.json", coverage)],
        profile=save(research_material[0], "coverage-profile.json", profile),
    )
    report = get_report(installed_cli, declaration, tmp_path / "incomplete")
    assert report["coverage"][0]["eligible_entity_count"] is None
    assert report["coverage"][0]["observed_subtotal"] == 0
    assert report["coverage"][0]["stratum_id"] is None
    assert report["coverage"][0]["status"] == status
    assert report["coverage"][0]["reasons"] == [reason]
    assert report["coverage_summary"]["unstratified_pairs"] == 1


def test_independently_reviewed_no_poi_interest_is_not_applicable(
    installed_cli, research_material, tmp_path
):
    inventory_ref, _ = interest_inventory(research_material, interests=())
    declaration = write_relevance(research_material, inventories=[inventory_ref])
    report = get_report(installed_cli, declaration, tmp_path / "no-interest")
    assert report["applicability"] == "not_applicable"
    assert report["runs"][0]["relevance_status"] == "not_applicable"
    assert report["runs"][0]["stages"]["discovered"]["status"] == "not_applicable"
    assert report["runs"][0]["end_to_end"]["status"] == "not_applicable"
    assert report["comparisons"][0]["end_to_end"]["delta"] is None


def test_sample_cannot_exceed_complete_eligible_corpus(installed_cli, research_material):
    inventory_ref, _ = interest_inventory(research_material, interests=("architecture",))
    coverage, profile = corpus_coverage(research_material, count=2)
    coverage["interest_coverage_ref"] = interest_coverage(
        research_material, inventory_ref, coverage
    )
    declaration = write_relevance(
        research_material,
        inventories=[inventory_ref],
        coverage=[save(research_material[0], "coverage.json", coverage)],
        profile=save(research_material[0], "coverage-profile.json", profile),
    )
    result = installed_cli("research", "validate", declaration, "--track", "relevance")
    assert result.returncode == 2
    assert "eligible" in result.stdout


def test_per_interest_principal_follows_reviewed_inventory(
    installed_cli, research_material, batch, tmp_path
):
    entries, _ = native_pair(research_material, batch)
    inventory_ref, inventory = interest_inventory(
        research_material, interests=("architecture",), use_existing=True
    )
    reviews = labels(
        research_material,
        inventory_ref,
        inventory,
        [("architecture", pid, "relevant") for pid in ("a", "b", "c", "d")],
    )
    declaration = write_relevance(
        research_material, entries, inventories=[inventory_ref], reviews=[reviews]
    )
    report = get_report(installed_cli, declaration, tmp_path / "per-interest")
    assert report["runs"][1]["per_interest"][0]["end_to_end"]["complete_count"] == 2
    assert (
        report["runs"][1]["per_interest"][0]["conversions"]["admitted_to_supplied"]["fraction"]
        == 2 / 3
    )
    assert report["comparisons"][0]["per_interest"][0]["end_to_end"]["delta"] == 0


@pytest.mark.parametrize("reviewed_at", ["not-a-timestamp", "2026-10-01T00:00:00"])
def test_malformed_requirement_review_time_is_rejected(
    installed_cli, research_material, reviewed_at
):
    root = research_material[0]
    inventory_ref, inventory = interest_inventory(research_material, interests=("architecture",))
    spec = json.loads((root / inventory["requirement_spec_ref"]["path"]).read_text())
    spec["review"]["reviewed_at"] = reviewed_at
    inventory["requirement_spec_ref"] = save(root, "reviewed-requirements.json", spec)
    inventory_ref = save(root, "interests.json", inventory)
    declaration = write_relevance(research_material, inventories=[inventory_ref])
    result = installed_cli("research", "validate", declaration, "--track", "relevance")
    assert result.returncode == 2
    assert "needs_material_correction" in result.stdout


@pytest.mark.parametrize("applicable", [True, False])
def test_relevance_report_envelope_covers_unavailable_material_and_unplanned_slots(
    installed_cli, research_material, tmp_path, applicable
):
    import hashlib

    if not applicable:
        for case in research_material[1]["cases"]:
            case["planned_versions"] = ["v0", "v3"]
    declaration = write_relevance(research_material)
    value = get_report(installed_cli, declaration, tmp_path / "envelope")
    planned = 40 if applicable else 0
    assert value["applicability"] == ("unavailable" if applicable else "not_applicable")
    assert value["measurement_coverage"]["opportunities"]["planned_slots"] == planned
    assert value["measurement_coverage"]["opportunities"]["captured_slots"] == 0
    assert value["measurement_coverage"]["corpus"] == {
        "unit": "original_requests",
        "planned_cases": 20,
        "complete": 0,
        "partial": 0,
        "unavailable": 20,
    }
    assert value["review_coverage"] == {
        "unit": "original_requests",
        "planned_cases": 20,
        "interest_inventory_cases": 0,
        "relevance_review_cases": 0,
        "relevance_review_records": 0,
    }
    expected_digest = hashlib.sha256(
        json.dumps(
            research_material[1], ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()
    assert value["population_digest"] == expected_digest
    assert value["diagnostics"] == []


def test_relevance_envelope_preserves_source_bound_opportunity_conflicts(
    installed_cli, research_material, batch, tmp_path
):
    from backend.tests.test_rtpeval_research_opportunities_cli import scheduled_material

    entry, _ = scheduled_material(research_material, batch, complete=True, extras=True)
    declaration = write_relevance(research_material, [entry])
    value = get_report(installed_cli, declaration, tmp_path / "conflict")
    conflicts = value["diagnostics"]
    assert any(
        row["reason"] == "producer_scheduled_fate_conflicts_with_independent_associations"
        for row in conflicts
    )
    assert all(
        row["case_id"] == entry["case_id"] and row["attempt_id"] == entry["attempt_id"]
        for row in conflicts
    )
