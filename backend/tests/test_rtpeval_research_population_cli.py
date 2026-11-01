"""Offline installed research CLI acceptance with source-bound synthetic populations."""

import hashlib
import json

import pytest

pytest_plugins = ("backend.tests.test_rtpeval_cli",)


def save(root, name, value):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    return {
        "path": name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "media_type": "application/json",
        "availability": "available",
        **({"schema_version": value["schema_version"]} if "schema_version" in value else {}),
    }


@pytest.fixture
def research_material(tmp_path):
    root = tmp_path / "material"
    root.mkdir()
    population = {
        "schema_version": "rtpeval_research_population_1",
        "population_id": "original-requests",
        "revision": "r1",
        "cases": [
            {
                "case_id": f"case-{index + 1}",
                "revision": "input-r1",
                "input_ref": save(root, f"input-{index}.json", {"destination": "Sydney"}),
                "metadata": {"tags": ["synthetic"]},
                "planned_versions": ["v0", "v1", "v2", "v3"],
                "repetition_ids": ["rep-1"],
            }
            for index in range(20)
        ],
    }
    profile = {
        "schema_version": "rtpeval_research_profile_1",
        "profile_id": "fixed-selection",
        "revision": "p1",
        "population_id": "original-requests",
        "population_revision": "r1",
        "source_revision": "synthetic-source",
        "declared_at": "2026-10-01T00:00:00Z",
        "timing_basis": "prospective",
        "first_attempt_rule": "first_dispatched",
        "retry_rule": {"selection": "none", "scope": "slot"},
        "completion_policy_ref": "selected_workflow_1",
        "completion_mapping": {
            "completed": "completed",
            "clarification_required": "clarification_required",
            "failed": "failed",
            "cancelled": "cancelled",
            "incomplete": "incomplete",
            "not_started": "unstarted",
            "pending": "unknown_pending",
            "required_mechanism_failed": "failed",
        },
        "configurations": {
            version: save(root, f"config-{version}.json", {"version": version})
            for version in ("v0", "v1", "v2", "v3")
        },
    }
    census = {
        "schema_version": "rtpeval_research_census_1",
        "population_id": "original-requests",
        "population_revision": "r1",
        "profile_id": "fixed-selection",
        "profile_revision": "p1",
        "attempts": [],
    }

    def write(include_census=True):
        declaration = {
            "schema_version": "rtpeval_research_declaration_1",
            "population_ref": save(root, "population.json", population),
            "profile_ref": save(root, "profile.json", profile),
            "census_ref": save(root, "census.json", census) if include_census else None,
            "track_refs": {},
        }
        save(root, "research.json", declaration)
        return root / "research.json"

    return root, population, profile, census, write


def test_original_inputs_without_census_retain_80_planned_unknown_slots(
    installed_cli, research_material, tmp_path
):
    root, _, _, _, write = research_material
    declaration = write(include_census=False)
    originals = {path: path.read_bytes() for path in root.glob("*.json")}
    valid = installed_cli("research", "validate", declaration, "--track", "population")
    assert valid.returncode == 0, valid.stdout + valid.stderr
    result = installed_cli(
        "research", "report", declaration, "-t", "population", "-o", tmp_path / "out"
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads((tmp_path / "out" / "population.json").read_text(encoding="utf-8"))
    assert report["population"]["unique_requests"] == 20
    assert report["summary"]["planned_completion"] == {
        "numerator": 0,
        "denominator": 80,
        "unit": "planned_slots",
        "confirmed_fraction": 0.0,
        "fraction": None,
        "lower_bound": 0.0,
        "upper_bound": 1.0,
        "unresolved": 80,
        "availability": "bounded",
    }
    assert report["summary"]["conditional_completion"]["availability"] == "unavailable"
    assert report["summary"]["conditional_completion"]["denominator"] == 0
    assert report["summary"]["status_counts"]["unknown_pending"] == 80
    assert report["all_four"]["completion"]["denominator"] == 20
    assert len(report["slots"]) == 80
    assert report["by_request"][0]["metadata"] == {"tags": ["synthetic"]}
    assert report["by_request"][0]["input_ref"]["path"] == "input-0.json"
    assert report["measurement_coverage"]["census_slots"] == 0
    assert report["measurement_coverage"]["planned_slots"] == 80
    assert report["review_coverage"]["applicability"] == "not_applicable"
    assert "80" in (tmp_path / "out" / "population.md").read_text(encoding="utf-8")
    assert originals == {path: path.read_bytes() for path in originals}


def add_attempt(
    material, case_index, version, native_status, *, order=1, dispatched=True, repetition=None
):
    root, population, profile, census, _ = material
    case = population["cases"][case_index]
    repetition = repetition or case["repetition_ids"][0]
    attempt_id = f"{case['case_id']}-{repetition}-{version}-attempt-{order}"
    previous = [
        a
        for a in census["attempts"]
        if a["case_id"] == case["case_id"]
        and a["version"] == version
        and a["repetition_id"] == repetition
    ]
    mechanisms = {"generation": "completed" if native_status == "completed" else native_status}
    if native_status == "completed":
        if version in ("v2", "v3"):
            mechanisms["retrieval"] = "completed"
        if version == "v3":
            mechanisms.update(validation="completed", repair="not_applicable")
    completion = {
        "declared_by": "synthetic-producer",
        "declared_at": f"2026-10-02T00:0{order}:00Z",
        "policy_ref": "selected_workflow_1",
        "workflow_status": native_status,
        "required_mechanisms": mechanisms,
    }
    attempt = {
        "case_id": case["case_id"],
        "case_revision": case["revision"],
        "version": version,
        "repetition_id": repetition,
        "attempt_id": attempt_id,
        "order": order,
        "run_id": attempt_id + "-run",
        "prior_attempt_id": previous[-1]["attempt_id"] if previous else None,
        "dispatched": dispatched,
        "dispatched_at": f"2026-10-02T00:0{order}:00Z" if dispatched else None,
        "input_sha256": case["input_ref"]["sha256"],
        "configuration_sha256": profile["configurations"][version]["sha256"],
        "reason_type": "producer_" + native_status,
        "execution_metadata": {"cache": "cold", "concurrency": 1, "order": case_index},
        "completion_ref": save(root, attempt_id + "-completion.json", completion),
    }
    census["attempts"].append(attempt)
    return attempt


def read_report(installed_cli, material, directory):
    result = installed_cli(
        "research", "report", material[-1](), "--track", "population", "--directory", directory
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads((directory / "population.json").read_text(encoding="utf-8"))


def test_first_dispatch_and_retries_keep_distinct_completion_denominators(
    installed_cli, research_material, tmp_path
):
    _, population, profile, _, _ = research_material
    population["cases"] = population["cases"][:2]
    profile["retry_rule"]["selection"] = "last_dispatched"
    add_attempt(research_material, 0, "v0", "completed")
    failure = add_attempt(research_material, 0, "v1", "failed")
    retry = add_attempt(research_material, 0, "v1", "completed", order=2)
    add_attempt(research_material, 0, "v2", "clarification_required")
    add_attempt(research_material, 0, "v3", "cancelled")
    add_attempt(research_material, 1, "v0", "incomplete")
    add_attempt(research_material, 1, "v1", "not_started", dispatched=False)
    add_attempt(research_material, 1, "v2", "pending")
    report = read_report(installed_cli, research_material, tmp_path / "mixed")
    assert report["summary"]["planned_completion"] == {
        "numerator": 1,
        "denominator": 8,
        "unit": "planned_slots",
        "confirmed_fraction": 0.125,
        "fraction": None,
        "lower_bound": 0.125,
        "upper_bound": 0.375,
        "unresolved": 2,
        "availability": "bounded",
    }
    assert report["summary"]["conditional_completion"]["numerator"] == 1
    assert report["summary"]["conditional_completion"]["denominator"] == 6
    assert report["summary"]["conditional_completion"]["unresolved"] == 1
    assert report["summary"]["status_counts"] == {
        "completed": 1,
        "clarification_required": 1,
        "failed": 1,
        "cancelled": 1,
        "incomplete": 1,
        "unstarted": 1,
        "unknown_pending": 2,
    }
    failed_slot = report["slots"][1]
    assert failed_slot["primary_attempt"]["attempt_id"] == failure["attempt_id"]
    assert failed_slot["retry_outcome"]["attempt_id"] == retry["attempt_id"]
    assert failed_slot["retry_outcome"]["status"] == "completed"
    assert len(failed_slot["attempts"]) == 2
    assert report["all_four"]["completion"]["numerator"] == 0
    assert report["all_four"]["completion"]["denominator"] == 2
    assert report["all_four"]["completion"]["upper_bound"] == 0.0


def test_repetitions_remain_grouped_and_unstarted_records_are_not_first_dispatches(
    installed_cli, research_material, tmp_path
):
    _, population, _, _, _ = research_material
    population["cases"] = population["cases"][:1]
    population["cases"][0]["repetition_ids"] = ["rep-1", "rep-2"]
    add_attempt(research_material, 0, "v0", "not_started", dispatched=False)
    actual_first = add_attempt(research_material, 0, "v0", "completed", order=2)
    for version in ("v1", "v2", "v3"):
        add_attempt(research_material, 0, version, "completed")
    for version in ("v0", "v1", "v2", "v3"):
        add_attempt(
            research_material,
            0,
            version,
            "failed" if version == "v0" else "completed",
            repetition="rep-2",
        )
    report = read_report(installed_cli, research_material, tmp_path / "repeated")
    assert report["population"]["unique_requests"] == 1
    assert report["summary"]["planned_completion"]["fraction"] == 0.875
    assert report["summary"]["conditional_completion"]["denominator"] == 8
    assert report["all_four"]["completion"]["fraction"] == 0.5
    assert report["summary"]["attempt_census"] == {
        "records": 9,
        "dispatched": 8,
        "retry_dispatches": 0,
    }
    assert report["slots"][0]["primary_attempt"]["attempt_id"] == actual_first["attempt_id"]
    assert report["by_version_repetition"][0]["summary"]["planned_completion"]["numerator"] == 1
    assert report["by_request"][0]["repetition_ids"] == ["rep-1", "rep-2"]
    assert report["quality_candidate_material"] == {
        "completed_selected_attempts": 7,
        "with_result_refs": 0,
        "missing_result_refs": 7,
        "non_completed_or_unresolved_slots": 1,
        "native_qualification": "not_performed",
    }


def attach_native_material(material, attempt, *, result=True):
    root = material[0]
    attempt["group_id"] = "native-" + attempt["case_id"] + "-" + attempt["repetition_id"]
    if result:
        attempt["result_ref"] = save(
            root,
            attempt["attempt_id"] + "-result.json",
            {
                "system_version": attempt["version"],
                "itinerary": {"days": []},
                "quality_pass": True,
            },
        )
    result_sha = attempt.get("result_ref", {}).get("sha256")
    identity = {
        "group_id": attempt["group_id"],
        "run_id": attempt["run_id"],
        "version": attempt["version"],
        "result_sha256": result_sha,
    }
    attempt["usage_ref"] = save(
        root,
        attempt["attempt_id"] + "-usage.json",
        {
            "schema_version": "rtpeval_usage_1",
            **identity,
            "namespace": "planner",
            "collection_status": "partial",
            "model_calls": [],
            "provider_events": [],
            "cache_events": [],
            "outcome": "completed" if result else "failed",
        },
    )
    attempt["provenance_ref"] = save(
        root,
        attempt["attempt_id"] + "-provenance.json",
        {
            "schema_version": "rtpeval_provenance_1",
            **identity,
            "input_sha256": attempt["input_sha256"],
        },
    )


def test_native_refs_remain_source_bound_and_results_never_imply_completion(
    installed_cli, research_material, tmp_path
):
    _, population, _, _, _ = research_material
    population["cases"] = population["cases"][:1]
    unknown = add_attempt(research_material, 0, "v0", "completed")
    attach_native_material(research_material, unknown)
    unknown.pop("completion_ref")
    failed = add_attempt(research_material, 0, "v1", "failed")
    attach_native_material(research_material, failed, result=False)
    report = read_report(installed_cli, research_material, tmp_path / "native")
    assert report["summary"]["planned_completion"]["numerator"] == 0
    assert report["summary"]["planned_completion"]["unresolved"] == 3
    bound_paths = {row["path"] for row in report["source_bindings"]}
    assert unknown["result_ref"]["path"] in bound_paths
    assert failed["usage_ref"]["path"] in bound_paths
    assert failed["provenance_ref"]["path"] in bound_paths
    assert report["slots"][1]["primary_attempt"]["status"] == "failed"


@pytest.mark.parametrize(
    "artifact,field",
    [
        ("provenance_ref", "input_sha256"),
        ("provenance_ref", "run_id"),
        ("provenance_ref", "group_id"),
        ("provenance_ref", "version"),
        ("provenance_ref", "result_sha256"),
        ("usage_ref", "result_sha256"),
        ("usage_ref", "run_id"),
        ("usage_ref", "group_id"),
        ("usage_ref", "version"),
        ("usage_ref", "namespace"),
        ("result_ref", "system_version"),
    ],
)
def test_foreign_native_artifact_binding_requires_material_correction(
    installed_cli, research_material, tmp_path, artifact, field
):
    root, population, _, _, write = research_material
    population["cases"] = population["cases"][:1]
    attempt = add_attempt(research_material, 0, "v0", "completed")
    attach_native_material(research_material, attempt)
    ref = attempt[artifact]
    native = json.loads((root / ref["path"]).read_text(encoding="utf-8"))
    native[field] = "foreign"
    attempt[artifact] = save(root, ref["path"], native)
    destination = tmp_path / "rejected"
    result = installed_cli(
        "research", "report", write(), "--track", "population", "--directory", destination
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert json.loads(result.stdout)["processing_status"] == "needs_material_correction"
    assert not destination.exists()


def test_configuration_bytes_and_declared_input_schema_are_verified(
    installed_cli, research_material, tmp_path
):
    root, population, profile, _, _ = research_material
    population["cases"] = population["cases"][:1]
    path = root / "runtime.yaml"
    path.write_text("generation:\n  model: synthetic\n", encoding="utf-8")
    profile["configurations"]["v0"] = {
        "path": "runtime.yaml",
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "media_type": "application/yaml",
        "availability": "available",
    }
    report = read_report(installed_cli, research_material, tmp_path / "yaml")
    assert "runtime.yaml" in {source["path"] for source in report["source_bindings"]}
    population["cases"][0]["input_ref"]["schema_version"] = "planning_request_foreign"
    result = installed_cli("research", "validate", research_material[-1](), "--track", "population")
    assert result.returncode == 2


def test_profile_cannot_relabel_native_completed_as_failed(installed_cli, research_material):
    research_material[2]["completion_mapping"]["completed"] = "failed"
    result = installed_cli("research", "validate", research_material[-1](), "--track", "population")
    assert result.returncode == 2
    assert "mapping" in result.stdout.lower()


def test_missing_census_also_bounds_unknown_conditional_dispatch_denominator(
    installed_cli, research_material, tmp_path
):
    research_material[1]["cases"] = research_material[1]["cases"][:1]
    add_attempt(research_material, 0, "v0", "completed")
    report = read_report(installed_cli, research_material, tmp_path / "dispatch-unknown")
    conditional = report["summary"]["conditional_completion"]
    assert conditional["numerator"] == 1
    assert conditional["denominator"] == 1
    assert conditional["fraction"] is None
    assert conditional["availability"] == "bounded"
    assert conditional["unknown_dispatch_slots"] == 3
    assert conditional["denominator_lower_bound"] == 1
    assert conditional["denominator_upper_bound"] == 4
    assert conditional["lower_bound"] == 0.25
    assert conditional["upper_bound"] == 1.0


@pytest.mark.parametrize(
    "mutation", ["missing_mechanisms", "malformed_mechanisms", "foreign_producer_policy"]
)
def test_malformed_native_completion_declarations_are_material_errors(
    installed_cli, research_material, mutation
):
    root, _, _, _, write = research_material
    attempt = add_attempt(research_material, 0, "v0", "failed")
    ref = attempt["completion_ref"]
    completion = json.loads((root / ref["path"]).read_text(encoding="utf-8"))
    if mutation == "missing_mechanisms":
        completion.pop("required_mechanisms")
    elif mutation == "malformed_mechanisms":
        completion["required_mechanisms"] = []
    else:
        completion["producer_policy_ref"] = "foreign"
    attempt["completion_ref"] = save(root, ref["path"], completion)
    result = installed_cli("research", "validate", write(), "--track", "population")
    assert result.returncode == 2


def test_reports_are_deterministic_fresh_and_explain_bounds_in_markdown(
    installed_cli, research_material, tmp_path
):
    research_material[1]["cases"] = research_material[1]["cases"][:1]
    add_attempt(research_material, 0, "v0", "completed")
    first = read_report(installed_cli, research_material, tmp_path / "first")
    second = read_report(installed_cli, research_material, tmp_path / "second")
    assert first == second
    for name in ("population.json", "population.md"):
        assert (tmp_path / "first" / name).read_bytes() == (tmp_path / "second" / name).read_bytes()
    payload = {key: value for key, value in first.items() if key != "semantic_sha256"}
    assert (
        first["semantic_sha256"]
        == hashlib.sha256(
            json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        ).hexdigest()
    )
    view = (tmp_path / "first" / "population.md").read_text(encoding="utf-8")
    assert "Conditional completion" in view
    assert "All-four completion" in view
    assert "0.25" in view
    assert "upper" in view.lower()
    originals = {p: p.read_bytes() for p in (tmp_path / "first").iterdir()}
    rejected = installed_cli(
        "research",
        "report",
        research_material[-1](),
        "--track",
        "population",
        "--directory",
        tmp_path / "first",
    )
    assert rejected.returncode == 2
    assert originals == {p: p.read_bytes() for p in originals}


def test_profile_revisions_retain_linked_sources_and_reject_foreign_history(
    installed_cli, research_material, tmp_path
):
    root, _, profile, _, write = research_material
    previous = dict(profile, revision="p0", declared_at="2026-09-01T00:00:00Z")
    profile["previous_profile_ref"] = save(root, "profile-p0.json", previous)
    report = read_report(installed_cli, research_material, tmp_path / "history")
    assert "profile-p0.json" in {row["path"] for row in report["source_bindings"]}
    previous["profile_id"] = "foreign"
    profile["previous_profile_ref"] = save(root, "profile-p0.json", previous)
    result = installed_cli("research", "validate", write(), "--track", "population")
    assert result.returncode == 2


@pytest.mark.parametrize(
    "mutation",
    [
        "duplicate_case",
        "stale_profile",
        "stale_census",
        "input_hash",
        "configuration_hash",
        "case_revision",
        "foreign_slot",
        "duplicate_run",
        "order",
        "prior_link",
        "dispatch_timestamp",
        "undispatched_completed",
        "dispatched_unstarted",
        "incomplete_required_mechanism",
        "stale_bytes",
        "escaping_path",
        "absolute_path",
        "duplicate_json_key",
        "nonfinite_json",
        "schema_ref",
        "prospective_after_dispatch",
        "malformed_configuration_ref",
    ],
)
def test_malformed_population_census_or_sources_never_emit_partial_cohorts(
    installed_cli, research_material, tmp_path, mutation
):
    root, population, profile, census, write = research_material
    first = add_attempt(research_material, 0, "v0", "completed")
    if mutation == "duplicate_case":
        population["cases"].append(population["cases"][0])
    elif mutation == "stale_profile":
        profile["population_revision"] = "old"
    elif mutation == "stale_census":
        census["profile_revision"] = "old"
    elif mutation in ("input_hash", "configuration_hash"):
        first["input_sha256" if mutation == "input_hash" else "configuration_sha256"] = "0" * 64
    elif mutation == "case_revision":
        first["case_revision"] = "old"
    elif mutation == "foreign_slot":
        first["repetition_id"] = "undeclared"
    elif mutation == "duplicate_run":
        second = add_attempt(research_material, 0, "v1", "failed")
        second["run_id"] = first["run_id"]
    elif mutation == "order":
        first["order"] = 2
    elif mutation == "prior_link":
        first["prior_attempt_id"] = "foreign-attempt"
    elif mutation == "dispatch_timestamp":
        first["dispatched_at"] = "2026-10-03T00:00:00Z"
    elif mutation == "undispatched_completed":
        first.update(dispatched=False, dispatched_at=None)
    elif mutation == "dispatched_unstarted":
        add_attempt(research_material, 0, "v1", "not_started")
    elif mutation == "incomplete_required_mechanism":
        ref = first["completion_ref"]
        completion = json.loads((root / ref["path"]).read_text(encoding="utf-8"))
        completion["required_mechanisms"]["generation"] = "failed"
        first["completion_ref"] = save(root, ref["path"], completion)
    elif mutation == "stale_bytes":
        (root / population["cases"][0]["input_ref"]["path"]).write_text("{}", encoding="utf-8")
    elif mutation in ("escaping_path", "absolute_path"):
        (root.parent / "foreign.json").write_text("{}", encoding="utf-8")
        population["cases"][0]["input_ref"]["path"] = (
            "../foreign.json" if mutation == "escaping_path" else str(root.parent / "foreign.json")
        )
    elif mutation in ("duplicate_json_key", "nonfinite_json"):
        ref = population["cases"][0]["input_ref"]
        path = root / ref["path"]
        path.write_text(
            '{"destination":"A","destination":"B"}'
            if mutation == "duplicate_json_key"
            else '{"value":NaN}',
            encoding="utf-8",
        )
        ref["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    elif mutation == "malformed_configuration_ref":
        profile["configurations"]["v0"] = None
    elif mutation == "schema_ref":
        population["cases"][0]["input_ref"]["schema_version"] = "foreign"
    else:
        profile["declared_at"] = "2026-10-03T00:00:00Z"
    destination = tmp_path / "invalid"
    result = installed_cli(
        "research", "report", write(), "--track", "population", "--directory", destination
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert json.loads(result.stdout)["processing_status"] == "needs_material_correction"
    assert not destination.exists()


def test_partial_versions_and_explicit_zero_dispatch_keep_applicability(
    installed_cli, research_material, tmp_path
):
    population = research_material[1]
    population["cases"] = population["cases"][:1]
    population["cases"][0]["planned_versions"] = ["v0", "v2"]
    add_attempt(research_material, 0, "v0", "not_started", dispatched=False)
    add_attempt(research_material, 0, "v2", "not_started", dispatched=False)
    report = read_report(installed_cli, research_material, tmp_path / "zero")
    assert report["summary"]["planned_completion"]["fraction"] == 0.0
    assert report["summary"]["planned_completion"]["denominator"] == 2
    assert report["summary"]["conditional_completion"]["fraction"] is None
    assert report["summary"]["conditional_completion"]["denominator"] == 0
    assert report["all_four"]["completion"]["denominator"] == 0
    assert report["all_four"]["excluded_not_all_four"] == 1


def test_retrospective_profiles_preserve_timing_basis(installed_cli, research_material, tmp_path):
    research_material[2].update(timing_basis="retrospective", declared_at="2026-10-03T00:00:00Z")
    add_attempt(research_material, 0, "v0", "completed")
    report = read_report(installed_cli, research_material, tmp_path / "retrospective")
    assert report["selection_profile"]["timing_basis"] == "retrospective"


def test_linked_source_cannot_escape_via_symlink(installed_cli, research_material):
    root, population, _, _, write = research_material
    outside = root.parent / "outside"
    outside.mkdir()
    (outside / "input.json").write_text("{}", encoding="utf-8")
    try:
        (root / "linked").symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"Host symlink privilege unavailable: {exc}")
    population["cases"][0]["input_ref"]["path"] = "linked/input.json"
    result = installed_cli("research", "validate", write(), "--track", "population")
    assert result.returncode == 2
