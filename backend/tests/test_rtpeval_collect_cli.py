"""Offline selected-material staging through the installed process boundary."""

import copy
import hashlib
import json

import pytest

from backend.tests import test_rtpeval_cli as cli_tests

pytest_plugins = ("backend.tests.evaluation.test_intake",)
installed_cli = cli_tests.installed_cli


@pytest.fixture
def collection(batch):
    manifest, _, write, _, root = batch
    write()
    group = copy.deepcopy(manifest["groups"][0])
    group.pop("completion_attested")
    group.pop("requirement_spec_ref")
    for version, run in group["selected_runs"].items():
        run["completion"] = {
            "declared_by": "fixture-producer",
            "declared_at": "2026-10-09T00:00:00Z",
            "policy_ref": "producer-policy-1",
            "workflow_status": "completed",
            "required_mechanisms": {
                "generation": "completed",
                **({"retrieval": "completed"} if version in ("v2", "v3") else {}),
                **({"validation": "completed", "repair": "completed"} if version == "v3" else {}),
            },
        }
    config = {
        "schema_version": "rtpeval_collection_1",
        "batch_id": "batch",
        "revision": "1",
        "created_at": "2026-10-09T00:00:00Z",
        "qualification_policy_ref": "producer-policy-1",
        "groups": [group],
    }
    path = root / "collection.json"

    def save():
        path.write_text(json.dumps(config), encoding="utf-8")
        return path

    return config, save, root


@pytest.fixture
def legacy_completion_collection(collection):
    config, save, root = collection

    def ref(path):
        return {
            "path": path.relative_to(root).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "media_type": "application/json",
            "availability": "available",
        }

    runs = config["groups"][0]["selected_runs"]
    capture = root / "prior/captures/v0"
    capture.mkdir(parents=True)
    result = root / runs["v0"]["result_ref"]["path"]
    (capture / "result.json").write_bytes(result.read_bytes())
    runs["v0"]["result_ref"] = ref(capture / "result.json")
    old_selection = root / "prior/old-selection.json"
    old_selection.write_text('{"evidence":"original-selection"}', encoding="utf-8")
    completion = copy.deepcopy(runs["v0"]["completion"])
    completion["operator_selection_ref"] = {
        **ref(old_selection),
        "path": "../../old-selection.json",
    }
    native = capture / "producer-completion.json"
    native.write_text(json.dumps(completion), encoding="utf-8")
    snapshot_config = copy.deepcopy(config)
    snapshot_config["groups"][0]["selected_runs"]["v0"]["completion"] = completion
    snapshot_config["groups"][0]["selected_runs"]["v3"] = {
        "run_id": runs["v3"]["run_id"],
        "capture_directory": "future",
    }
    snapshot = root / "replacement-selection.json"
    snapshot.write_text(json.dumps(snapshot_config), encoding="utf-8")
    current_completion = root / "current-completion.json"
    current_completion.write_text(
        json.dumps({"operator_selection_ref": ref(snapshot)}), encoding="utf-8"
    )
    provenance_path = root / runs["v3"]["provenance_ref"]["path"]
    provenance = json.loads(provenance_path.read_bytes())
    provenance["producer_completion_ref"] = ref(current_completion)
    provenance_path.write_text(json.dumps(provenance), encoding="utf-8")
    runs["v3"]["provenance_ref"]["sha256"] = hashlib.sha256(
        provenance_path.read_bytes()
    ).hexdigest()
    config["completion_origins"] = [
        {
            "selection_ref": ref(snapshot),
            "group_id": config["groups"][0]["group_id"],
            "version": "v0",
            "run_id": runs["v0"]["run_id"],
            "completion_ref": ref(native),
        }
    ]
    return config, save, root


def test_collect_recovers_bound_legacy_completion_without_rewriting_sources(
    legacy_completion_collection,
):
    from backend.cli.collection import collect, read_staging

    _, save, root = legacy_completion_collection
    path = save()
    originals = {p: p.read_bytes() for p in root.rglob("*.json")}
    output = root / "recovery"
    staging = collect(path, output)
    assert staging["status"] == "pending_review"
    assert all(r["completion_qualified"] for r in staging["groups"][0]["selected_runs"].values())
    assert not staging["qualified_four_version_batch"]
    assert read_staging(output / "staging.json") == staging
    assert {p: p.read_bytes() for p in originals} == originals
    assert (output / "sources/replacement-selection.json").read_bytes() == originals[
        root / "replacement-selection.json"
    ]


@pytest.mark.parametrize(
    "fault", ["missing", "duplicate", "hash", "mismatch", "owner", "escape", "unused"]
)
def test_completion_origin_faults_refuse_recovery_without_writes(
    legacy_completion_collection, fault
):
    from backend.cli.collection import CollectionError, collect

    config, save, root = legacy_completion_collection
    origin = config["completion_origins"][0]
    if fault == "missing":
        del config["completion_origins"]
    elif fault == "duplicate":
        config["completion_origins"].append(copy.deepcopy(origin))
    elif fault == "hash":
        origin["completion_ref"]["sha256"] = "0" * 64
    elif fault in ("mismatch", "owner"):
        source = root / origin["completion_ref"]["path"]
        value = json.loads(source.read_bytes())
        if fault == "mismatch":
            value["declared_at"] = "different"
        else:
            source = root / "wrong-owner.json"
            origin["completion_ref"]["path"] = source.name
        source.write_text(json.dumps(value), encoding="utf-8")
        origin["completion_ref"]["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    elif fault == "escape":
        origin["selection_ref"]["path"] = "../outside.json"
    else:
        origin["run_id"] = "wrong-run"
        # Avoid reaching the unrelated escape so the unused binding itself must be rejected.
        snapshot = root / origin["selection_ref"]["path"]
        value = json.loads(snapshot.read_bytes())
        value["groups"][0]["selected_runs"]["v0"]["completion"].pop("operator_selection_ref")
        snapshot.write_text(json.dumps(value), encoding="utf-8")
        origin["selection_ref"]["sha256"] = hashlib.sha256(snapshot.read_bytes()).hexdigest()
        current = root / "current-completion.json"
        wrapper = json.loads(current.read_bytes())
        wrapper["operator_selection_ref"]["sha256"] = origin["selection_ref"]["sha256"]
        current.write_text(json.dumps(wrapper), encoding="utf-8")
        run = config["groups"][0]["selected_runs"]["v3"]
        provenance = root / run["provenance_ref"]["path"]
        declaration = json.loads(provenance.read_bytes())
        declaration["producer_completion_ref"]["sha256"] = hashlib.sha256(
            current.read_bytes()
        ).hexdigest()
        provenance.write_text(json.dumps(declaration), encoding="utf-8")
        run["provenance_ref"]["sha256"] = hashlib.sha256(provenance.read_bytes()).hexdigest()
    path = save()
    originals = {p: p.read_bytes() for p in root.rglob("*.json")}
    output = root / "recovery"
    with pytest.raises(CollectionError):
        collect(path, output)
    assert not output.exists()
    assert {p: p.read_bytes() for p in originals} == originals


@pytest.mark.parametrize("bind_alias", [False, True])
def test_legacy_completion_context_is_bound_for_each_immutable_selection_alias(
    legacy_completion_collection, bind_alias
):
    from backend.cli.collection import CollectionError, collect, read_staging

    config, save, root = legacy_completion_collection
    origin = config["completion_origins"][0]
    snapshot = root / origin["selection_ref"]["path"]
    alias = root / "replacement-config.json"
    alias.write_bytes(snapshot.read_bytes())
    alias_origin = copy.deepcopy(origin)
    alias_origin["selection_ref"]["path"] = alias.name
    if bind_alias:
        config["completion_origins"].append(alias_origin)
    current = root / "current-completion.json"
    wrapper = json.loads(current.read_bytes())
    wrapper["operator_config_ref"] = alias_origin["selection_ref"]
    current.write_text(json.dumps(wrapper), encoding="utf-8")
    run = config["groups"][0]["selected_runs"]["v3"]
    provenance = root / run["provenance_ref"]["path"]
    declaration = json.loads(provenance.read_bytes())
    declaration["producer_completion_ref"]["sha256"] = hashlib.sha256(
        current.read_bytes()
    ).hexdigest()
    provenance.write_text(json.dumps(declaration), encoding="utf-8")
    run["provenance_ref"]["sha256"] = hashlib.sha256(provenance.read_bytes()).hexdigest()
    path = save()
    originals = {p: p.read_bytes() for p in root.rglob("*.json")}
    output = root / "recovery"
    if bind_alias:
        staging = collect(path, output)
        assert read_staging(output / "staging.json") == staging
        assert (output / "sources/replacement-config.json").read_bytes() == snapshot.read_bytes()
    else:
        with pytest.raises(CollectionError, match="escapes collection root"):
            collect(path, output)
        assert not output.exists()
    assert {p: p.read_bytes() for p in originals} == originals


@pytest.mark.parametrize("path_kind", ["escape", "absolute"])
def test_bound_native_completion_still_rejects_invalid_dependency_paths(
    legacy_completion_collection, path_kind
):
    from backend.cli.collection import CollectionError, collect

    config, save, root = legacy_completion_collection
    origin = config["completion_origins"][0]
    native_path = root / origin["completion_ref"]["path"]
    completion = json.loads(native_path.read_bytes())
    completion["operator_selection_ref"]["path"] = (
        "../../../../outside.json"
        if path_kind == "escape"
        else str(root / "prior/old-selection.json")
    )
    native_path.write_text(json.dumps(completion), encoding="utf-8")
    origin["completion_ref"]["sha256"] = hashlib.sha256(native_path.read_bytes()).hexdigest()
    snapshot = root / origin["selection_ref"]["path"]
    selection = json.loads(snapshot.read_bytes())
    selection["groups"][0]["selected_runs"]["v0"]["completion"] = completion
    snapshot.write_text(json.dumps(selection), encoding="utf-8")
    origin["selection_ref"]["sha256"] = hashlib.sha256(snapshot.read_bytes()).hexdigest()
    current = root / "current-completion.json"
    wrapper = json.loads(current.read_bytes())
    wrapper["operator_selection_ref"]["sha256"] = origin["selection_ref"]["sha256"]
    current.write_text(json.dumps(wrapper), encoding="utf-8")
    run = config["groups"][0]["selected_runs"]["v3"]
    provenance = root / run["provenance_ref"]["path"]
    declaration = json.loads(provenance.read_bytes())
    declaration["producer_completion_ref"]["sha256"] = hashlib.sha256(
        current.read_bytes()
    ).hexdigest()
    provenance.write_text(json.dumps(declaration), encoding="utf-8")
    run["provenance_ref"]["sha256"] = hashlib.sha256(provenance.read_bytes()).hexdigest()
    path = save()
    output = root / "recovery"
    with pytest.raises(CollectionError):
        collect(path, output)
    assert not output.exists()


def test_partial_collection_preserves_exact_bytes_and_pending_review(installed_cli, collection):
    config, save, root = collection
    del config["groups"][0]["selected_runs"]["v2"]
    path = save()
    originals = {p: p.read_bytes() for p in root.glob("*.json")}
    output = root / "staging"
    result = installed_cli("batch", "collect", path, "-o", output)
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["status"] == "incomplete"
    staging = json.loads((output / "staging.json").read_bytes())
    assert staging["schema_version"] == "rtpeval_staging_1"
    assert staging["qualified_four_version_batch"] is False
    assert staging["pending_requirement_review"] is True
    assert "v2" in staging["groups"][0]["missing_versions"]
    group = staging["groups"][0]
    for key in ("input_ref",):
        assert (output / group[key]["path"]).read_bytes() == originals[
            root / config["groups"][0][key]["path"]
        ]
    for version, run in group["selected_runs"].items():
        for key in ("result_ref", "usage_ref", "provenance_ref"):
            source = config["groups"][0]["selected_runs"][version][key]["path"]
            assert (output / run[key]["path"]).read_bytes() == originals[root / source]
    assert {p: p.read_bytes() for p in originals} == originals
    assert not (output / "manifest.json").exists()


@pytest.mark.parametrize(
    "fault,diagnostic",
    [
        ("duplicate_run", "Duplicate run"),
        ("wrong_hash", "hash mismatch"),
        ("escaping_path", "escapes"),
        ("absolute_path", "relative"),
        ("provenance_mismatch", "Provenance"),
        ("usage_mismatch", "Usage"),
        ("result_version", "Result version"),
        ("missing_provenance", "provenance"),
        ("source_drift", "hash mismatch"),
    ],
)
def test_invalid_selection_never_publishes_or_changes_sources(
    installed_cli, collection, fault, diagnostic
):
    config, save, root = collection
    runs = config["groups"][0]["selected_runs"]
    run = runs["v0"]
    if fault == "duplicate_run":
        runs["v1"]["run_id"] = run["run_id"]
    elif fault == "wrong_hash":
        run["result_ref"]["sha256"] = "0" * 64
    elif fault == "escaping_path":
        run["result_ref"]["path"] = "../outside.json"
    elif fault == "absolute_path":
        run["result_ref"]["path"] = str(root / "v0.json")
    elif fault == "missing_provenance":
        del run["provenance_ref"]
    else:
        key = "provenance_ref" if fault == "provenance_mismatch" else "usage_ref"
        if fault in ("result_version", "source_drift"):
            key = "result_ref"
        path = root / run[key]["path"]
        value = json.loads(path.read_bytes())
        value["run_id" if "mismatch" in fault else "system_version"] = "wrong"
        raw = json.dumps(value).encode()
        path.write_bytes(raw)
        if fault != "source_drift":
            import hashlib

            run[key]["sha256"] = hashlib.sha256(raw).hexdigest()
    path = save()
    originals = {p: p.read_bytes() for p in root.glob("*.json")}
    output = root / "staging"
    result = installed_cli("batch", "collect", path, "--directory", output)
    assert result.returncode == 2, result.stdout + result.stderr
    assert diagnostic.lower() in result.stdout.lower()
    assert not output.exists()
    assert {p: p.read_bytes() for p in originals} == originals


@pytest.mark.parametrize(
    "version,status,mechanism,expected",
    [
        ("v0", "cancelled", None, False),
        ("v1", "timed_out", None, False),
        ("v2", "completed", ("retrieval", "degraded"), False),
        ("v3", "failed", None, False),
        ("v3", "completed", ("repair", "not_applicable"), True),
        ("v3", "completed", ("repair", "completed"), True),
        ("v3", "completed", ("validation", "failed"), False),
        ("v0", "missing", None, False),
    ],
)
def test_completion_qualification_preserves_normal_and_blocked_attempts(
    installed_cli, collection, version, status, mechanism, expected
):
    config, save, root = collection
    run = config["groups"][0]["selected_runs"][version]
    if status == "missing":
        del run["completion"]
    else:
        run["completion"]["workflow_status"] = status
        if mechanism:
            run["completion"]["required_mechanisms"][mechanism[0]] = mechanism[1]
    path = save()
    result = installed_cli("batch", "collect", path, "--directory", root / "staging")
    assert result.returncode == 0, result.stdout + result.stderr
    stage = json.loads(result.stdout)
    selected = stage["groups"][0]["selected_runs"][version]
    assert selected["completion_qualified"] is expected
    assert stage["status"] == ("pending_review" if expected else "blocked")
    assert selected["completion"] == run.get("completion")
    assert selected["usage_ref"]["availability"] == "available"
    usage = json.loads((root / "staging" / selected["usage_ref"]["path"]).read_bytes())
    assert usage["collection_status"] == "unavailable"
    assert "model_calls" not in usage
    if not expected:
        assert selected["blocking_reasons"]


def test_traceable_producer_declaration_can_supply_missing_provenance(installed_cli, collection):
    config, save, root = collection
    run = config["groups"][0]["selected_runs"]["v0"]
    declaration = json.loads((root / run.pop("provenance_ref")["path"]).read_bytes())
    declaration.update(
        declared_by="original-producer",
        declared_at="2026-10-09T00:00:00Z",
        rationale="Historical original run explicitly linked by its producer",
    )
    run["producer_declaration"] = declaration
    result = installed_cli("batch", "collect", save(), "--directory", root / "staging")
    assert result.returncode == 0, result.stdout + result.stderr
    stage = json.loads(result.stdout)
    ref = stage["groups"][0]["selected_runs"]["v0"]["provenance_ref"]
    assert json.loads((root / "staging" / ref["path"]).read_bytes()) == declaration
    assert stage["status"] == "pending_review"


def test_collection_retains_explicit_provenance_dependencies_and_evidence_bytes(
    installed_cli, collection, batch
):
    config, save, root = collection
    _, _, _, artifact, _ = batch
    binary = b"\x00\xffunchanged-original"
    (root / "raw.bin").write_bytes(binary)
    import hashlib

    evidence = {
        "schema_version": "rtpeval_generation_evidence_1",
        "artifacts": [{"path": "raw.bin", "sha256": hashlib.sha256(binary).hexdigest()}],
    }
    evidence_ref = artifact("evidence-index.json", evidence, evidence["schema_version"])
    run = config["groups"][0]["selected_runs"]["v0"]
    provenance = json.loads((root / run["provenance_ref"]["path"]).read_bytes())
    provenance["configuration_ref"] = artifact("runtime-policy.json", {"configuration": {}})
    provenance["evidence_index_ref"] = evidence_ref
    run["provenance_ref"] = artifact("v0-provenance.json", provenance, provenance["schema_version"])
    result = installed_cli("batch", "collect", save(), "--directory", root / "staging")
    assert result.returncode == 0, result.stdout + result.stderr
    assert (root / "staging/sources/raw.bin").read_bytes() == binary
    assert (root / "staging/sources/runtime-policy.json").read_bytes() == (
        root / "runtime-policy.json"
    ).read_bytes()
    assert (root / "staging/sources/evidence-index.json").read_bytes() == (
        root / "evidence-index.json"
    ).read_bytes()


def test_interrupted_attempt_without_result_stays_visible(installed_cli, collection):
    config, save, root = collection
    run = config["groups"][0]["selected_runs"]["v2"]
    source = json.loads((root / run.pop("provenance_ref")["path"]).read_bytes())
    run.pop("result_ref")
    run.pop("usage_ref")
    source.update(
        result_sha256=None,
        declared_by="producer",
        declared_at="now",
        rationale="Interrupted attempt retained without an adopted output",
    )
    run["producer_declaration"] = source
    run["completion"]["workflow_status"] = "cancelled"
    result = installed_cli("batch", "collect", save(), "--directory", root / "staging")
    assert result.returncode == 0, result.stdout + result.stderr
    stage = json.loads(result.stdout)
    attempt = stage["groups"][0]["selected_runs"]["v2"]
    assert attempt["run_id"] == "run-v2"
    assert attempt["completion_qualified"] is False
    assert "missing_material:result_ref" in attempt["blocking_reasons"]
    assert "missing_material:usage_ref" in attempt["blocking_reasons"]
    assert stage["status"] == "blocked"


@pytest.mark.parametrize("fault", ["missing_usage", "invalid_final", "failed_usage"])
def test_failed_material_never_becomes_qualified(installed_cli, collection, batch, fault):
    config, save, root = collection
    _, _, _, artifact, _ = batch
    run = config["groups"][0]["selected_runs"]["v0"]
    if fault == "missing_usage":
        run.pop("usage_ref")
    elif fault == "invalid_final":
        result = json.loads((root / run["result_ref"]["path"]).read_bytes())
        result["itinerary"] = None
        run["result_ref"] = artifact("v0.json", result)
        for key in ("usage_ref", "provenance_ref"):
            value = json.loads((root / run[key]["path"]).read_bytes())
            value["result_sha256"] = run["result_ref"]["sha256"]
            run[key] = artifact(run[key]["path"], value, value["schema_version"])
    else:
        usage = json.loads((root / run["usage_ref"]["path"]).read_bytes())
        usage["outcome"] = "failed"
        run["usage_ref"] = artifact("v0-usage.json", usage, usage["schema_version"])
    result = installed_cli("batch", "collect", save(), "--directory", root / "staging")
    assert result.returncode == 0, result.stdout + result.stderr
    stage = json.loads(result.stdout)
    assert stage["status"] == "blocked"
    assert not stage["groups"][0]["completion_attested"]


@pytest.mark.parametrize("fault", ["original", "copied", "config", "completion"])
def test_verified_staging_rejects_source_or_declaration_drift(installed_cli, collection, fault):
    from backend.cli.collection import CollectionError, read_staging

    config, save, root = collection
    source = save()
    output = root / "staging"
    result = installed_cli("batch", "collect", source, "--directory", output)
    assert result.returncode == 0, result.stdout + result.stderr
    assert read_staging(output / "staging.json")["status"] == "pending_review"
    if fault == "original":
        (root / "v0.json").write_bytes(b"{}")
    elif fault == "copied":
        (output / "sources/v0.json").write_bytes(b"{}")
    elif fault == "config":
        config["qualification_policy_ref"] = "changed"
        save()
    else:
        stage = json.loads((output / "staging.json").read_bytes())
        stage["groups"][0]["selected_runs"]["v0"]["completion"]["declared_by"] = "forged"
        (output / "staging.json").write_text(json.dumps(stage), encoding="utf-8")
    with pytest.raises(CollectionError, match="drift|mismatch"):
        read_staging(output / "staging.json")


def test_collection_refuses_existing_or_finalized_destination(installed_cli, collection):
    _, save, root = collection
    output = root / "finalized"
    output.mkdir()
    finalized = output / "manifest.json"
    finalized.write_bytes(b'{"schema_version":"rtpeval_batch_1"}')
    result = installed_cli("batch", "collect", save(), "--directory", output)
    assert result.returncode == 2
    assert "fresh" in result.stdout.lower()
    assert finalized.read_bytes() == b'{"schema_version":"rtpeval_batch_1"}'


@pytest.mark.parametrize("arguments", [("batch", "--help"), ("batch", "collect", "--help")])
def test_collection_help_loads_no_intake_or_provider(installed_cli, arguments):
    result = installed_cli(*arguments, block_intake=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "offline" in result.stdout.lower()


@pytest.mark.parametrize(
    "fault", ["duplicate_key", "nonfinite", "dependency_escape", "dependency_hash", "policy"]
)
def test_strict_configuration_and_dependency_boundary(installed_cli, collection, batch, fault):
    config, save, root = collection
    _, _, _, artifact, _ = batch
    run = config["groups"][0]["selected_runs"]["v0"]
    if fault == "policy":
        run["completion"]["policy_ref"] = "wrong-policy"
    elif fault.startswith("dependency"):
        provenance = json.loads((root / run["provenance_ref"]["path"]).read_bytes())
        provenance["configuration_ref"] = {
            "path": "../outside.json" if fault == "dependency_escape" else "input.json",
            "sha256": "0" * 64,
        }
        run["provenance_ref"] = artifact(
            "v0-provenance.json", provenance, provenance["schema_version"]
        )
    path = save()
    if fault == "duplicate_key":
        path.write_text(
            '{"schema_version":"rtpeval_collection_1","schema_version":"rtpeval_collection_1"}',
            encoding="utf-8",
        )
    elif fault == "nonfinite":
        path.write_text(
            path.read_text(encoding="utf-8").replace('"revision": "1"', '"revision": NaN'),
            encoding="utf-8",
        )
    output = root / "staging"
    result = installed_cli("batch", "collect", path, "--directory", output)
    if fault == "policy":
        assert result.returncode == 0, result.stdout + result.stderr
        assert json.loads(result.stdout)["status"] == "blocked"
    else:
        assert result.returncode == 2, result.stdout + result.stderr
        assert not output.exists()
