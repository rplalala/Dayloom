"""Pinned corpus production and export through guarded installed commands."""

import json

import pytest

from backend.app.tripworld.database.policy import POLICY_VERSION, text_hash
from backend.app.tripworld.database.vectors import SPACE, SPACE_ID
from backend.app.tripworld.retrieval.entities import ENTITY_VERSION, TEXT_VERSION
from backend.evaluation.research.sources import digest
from backend.tests.test_rtpeval_cli import installed_cli as cli_fixture
from backend.tests.test_rtpeval_research_population_cli import (
    research_material as research_fixture,
)
from backend.tests.test_rtpeval_research_population_cli import save

installed_cli = cli_fixture
research_material = research_fixture


def entity(identity, latitude=10, longitude=20, **changes):
    return {
        "retrieval_entity_id": identity,
        "google_place_id": "shared-venue",
        "source_fsq_place_ids": [identity],
        "preferred_name": identity,
        "aliases": [],
        "latitude": latitude,
        "longitude": longitude,
        "localities": [],
        "regions": [],
        "country": "ZZ",
        "countries": ["ZZ"],
        "fsq_categories": [],
        "google_categories": [],
        "direct_semantics": [],
        "inferred_semantics": [],
        "semantic_rule_ids": [],
        "source_eligibility_hints": [],
        "eligibility_hint": "eligible",
        "retrieval_description": "",
        "raw_retrieval_text": identity,
        "retrieval_text": identity,
        "coordinate_spread_km": 0,
        "location_flags": [],
        "source_row_count": 1,
        "tripworld_revision": "synthetic-revision",
        "semantic_mapping_version": "synthetic-mapping",
        "retrieval_entity_builder_version": ENTITY_VERSION,
        "retrieval_text_template_version": TEXT_VERSION,
        "content_hash": digest(identity),
        **changes,
    }


def request(material, entities=None, scope=None):
    root, population, _, _, write = material
    population["cases"] = population["cases"][:1]
    case = population["cases"][0]
    rows = entities if entities is not None else [entity("one"), entity("two", longitude=20.01)]
    dataset = save(
        root, "entities.json", {"schema_version": "rtpeval_corpus_entities_1", "entities": rows}
    )
    manifest = {
        "output_sha256": dataset["sha256"],
        "entity_count": len(rows),
        "inputs": {
            key: rows[0][key] if rows else value
            for key, value in (
                ("retrieval_entity_builder_version", ENTITY_VERSION),
                ("retrieval_text_template_version", TEXT_VERSION),
                ("tripworld_revision", "synthetic-revision"),
                ("semantic_mapping_version", "synthetic-mapping"),
            )
        },
    }
    snapshot = save(
        root,
        "snapshot.json",
        {"corpus": manifest, "policy_version": POLICY_VERSION, "space_id": SPACE_ID},
    )
    index = save(
        root,
        "embedding-index.json",
        {
            "schema_version": "rtpeval_corpus_embedding_index_1",
            "artifact_sha256": dataset["sha256"],
            "space_id": SPACE_ID,
            "configuration": SPACE,
            "text_hashes": [text_hash(row["retrieval_text"]) for row in rows],
        },
    )
    scope = scope or {"kind": "radius", "latitude": 10, "longitude": 20, "radius_m": 2000}
    value = {
        "schema_version": "rtpeval_corpus_request_1",
        "declaration_ref": save(root, "research.json", json.loads(write().read_bytes())),
        "case_id": case["case_id"],
        "case_revision": case["revision"],
        "input_sha256": case["input_ref"]["sha256"],
        "scope": scope,
        "scope_sha256": digest(scope),
        "snapshot_identity": {
            "snapshot_ref": snapshot,
            "artifact_sha256": dataset["sha256"],
            "policy_version": POLICY_VERSION,
            "space_id": SPACE_ID,
            "identity_pointers": {
                "artifact_sha256": "/corpus/output_sha256",
                "policy_version": "/policy_version",
                "space_id": "/space_id",
            },
        },
        "declared_at": "2026-10-01T00:00:00Z",
        "timing_basis": "unverified",
        "measurement_configuration": {
            "max_entities": 100,
            "max_source_bytes": 1000000,
            "timeout_seconds": 5,
            "statement_timeout_ms": 1000,
            "connect_timeout_seconds": 2,
            "batch_size": 10,
        },
        "source": {
            "kind": "saved_dataset",
            "dataset_ref": dataset,
            "embedding_index_ref": index,
            "manifest_pointer": "/corpus",
        },
        "coverage_profile_ref": None,
    }
    save(root, "corpus-request.json", value)
    return root / "corpus-request.json", value


def run(installed_cli, *args, **kwargs):
    return installed_cli("research", "corpus", *args, evaluation_offline=True, **kwargs)


def test_prepare_is_offline_fresh_and_preserves_exact_sources(
    installed_cli, research_material, tmp_path
):
    source, _ = request(research_material)
    originals = {p: p.read_bytes() for p in research_material[0].glob("*.json")}
    destination = tmp_path / "prepared"
    result = run(installed_cli, "prepare", source, "--directory", destination)
    assert result.returncode == 0, result.stdout + result.stderr
    receipt = json.loads(result.stdout)
    assert receipt["processing_status"] == "prepared"
    assert receipt["database_connections"] == 0
    assert not (destination / "material/corpus-sidecar.json").exists()
    for binding in receipt["source_bindings"]:
        assert (destination / "material" / binding["path"]).read_bytes() == (
            research_material[0] / binding["path"]
        ).read_bytes()
    assert {p: p.read_bytes() for p in originals} == originals
    repeated = run(installed_cli, "prepare", source, "--directory", destination)
    assert repeated.returncode == 2


def test_measure_counts_entities_instead_of_shared_venues_and_reports_coverage(
    installed_cli, research_material, tmp_path
):
    rows = [
        entity("one"),
        entity("two", longitude=20.01),
        entity("outside", longitude=25),
        entity("ineligible", eligibility_hint="ineligible"),
        entity("empty", retrieval_text=""),
        entity("spread", coordinate_spread_km=11),
        entity("conflict", location_flags=["country_conflict"]),
        entity("no-vector"),
    ]
    source, value = request(research_material, rows)
    root = research_material[0]
    index = json.loads((root / "embedding-index.json").read_bytes())
    index["text_hashes"].remove(text_hash("no-vector"))
    value["source"]["embedding_index_ref"] = save(root, "embedding-index.json", index)
    save(root, source.name, value)
    prepared, measured = tmp_path / "prepared", tmp_path / "measured"
    assert run(installed_cli, "prepare", source, "--directory", prepared).returncode == 0
    result = run(installed_cli, "measure", prepared / "receipt.json", "--directory", measured)
    assert result.returncode == 0, result.stdout + result.stderr
    receipt = json.loads(result.stdout)
    sidecar = json.loads((measured / receipt["sidecar_ref"]["path"]).read_bytes())
    assert sidecar["eligible_entity_count"] == sidecar["observed_subtotal"] == 2
    assert sidecar["count_status"] == "complete"
    assert sidecar["declared_at"] == value["declared_at"]
    assert sidecar["measurement_method"] == "saved_dataset_full_entity_scan_1"
    declaration = measured / receipt["declaration_ref"]["path"]
    validated = installed_cli("research", "validate", declaration, "--track", "relevance")
    assert validated.returncode == 0, validated.stdout + validated.stderr
    reported = installed_cli(
        "research",
        "report",
        declaration,
        "--track",
        "relevance",
        "--directory",
        tmp_path / "report",
    )
    assert reported.returncode == 0, reported.stdout + reported.stderr
    report = json.loads((tmp_path / "report/relevance.json").read_bytes())
    assert report["coverage"][0]["eligible_entity_count"] == 2
    assert report["coverage"][0]["timing_basis"] == "unverified"


def test_saved_export_replays_evidence_without_changing_originals_or_times(
    installed_cli, research_material, tmp_path
):
    source, _ = request(research_material)
    prepared, measured, exported = (
        tmp_path / name for name in ("prepared", "measured", "exported")
    )
    assert run(installed_cli, "prepare", source, "--directory", prepared).returncode == 0
    assert (
        run(installed_cli, "measure", prepared / "receipt.json", "--directory", measured).returncode
        == 0
    )
    originals = {
        p.relative_to(measured): p.read_bytes() for p in measured.rglob("*") if p.is_file()
    }
    result = run(installed_cli, "export", measured / "receipt.json", "--directory", exported)
    assert result.returncode == 0, result.stdout + result.stderr
    receipt = json.loads(result.stdout)
    assert receipt["database_connections"] == 0
    for name, raw in originals.items():
        assert (measured / name).read_bytes() == raw
        if name.parts[0] == "material":
            assert (exported / name).read_bytes() == raw
    declaration = exported / receipt["declaration_ref"]["path"]
    assert (
        installed_cli("research", "validate", declaration, "--track", "relevance").returncode == 0
    )


DATABASE_BOOTSTRAP = """
import json
import os
import psycopg
from pathlib import Path
payload = json.loads(Path(os.environ['CORPUS_DB_FIXTURE']).read_bytes())
os.environ['CORPUS_TEST_DSN'] = 'postgresql://reader:secret-fixture@invalid/corpus'
class Cursor:
    def __init__(self, rows): self.rows, self.calls = iter(rows), 0
    def fetchone(self): return next(self.rows, None)
    def fetchmany(self, count):
        self.calls += 1
        if payload.get('fault') in ('timeout', 'failure') and self.calls > 1:
            if payload['fault'] == 'timeout': raise TimeoutError('secret-fixture-timeout')
            raise OSError('secret-fixture-failure')
        if payload.get('fault') in ('timeout', 'failure'): count = 1
        rows = []
        for _ in range(count):
            row = next(self.rows, None)
            if row is None: break
            rows.append(row)
        return rows
    def execute(self, sql, params=None):
        assert sql.strip().startswith('SELECT') and 'LIMIT' in sql
        return self
    def close(self): pass
class Connection:
    def execute(self, sql, params=None):
        assert sql.strip().split()[0] in ('SELECT', 'BEGIN', 'ROLLBACK', 'SHOW')
        if sql.startswith('BEGIN'):
            assert 'REPEATABLE READ' in sql and 'READ ONLY' in sql
            return Cursor([])
        if 'transaction_read_only' in sql: return Cursor([{'transaction_read_only': 'on'}])
        if 'transaction_isolation' in sql:
            return Cursor([{'transaction_isolation': 'repeatable read'}])
        if 'txid_current_snapshot' in sql: return Cursor([{'snapshot_id': '1:2:'}])
        if 'corpus_builds' in sql: return Cursor([payload['build']])
        if 'embedding_spaces' in sql: return Cursor([{'configuration': payload['space']}])
        if 'count(*)' in sql: return Cursor([payload['counts']])
        return Cursor([])
    def cursor(self, **kwargs): return Cursor(payload['rows'])
    def close(self): pass
def connect(dsn, **kwargs):
    if payload.get('fault') == 'connection_failure': raise OSError('secret-fixture-dsn')
    assert dsn.endswith('/corpus')
    assert kwargs['autocommit'] is True and kwargs['connect_timeout'] == 2
    assert 'default_transaction_read_only=on' in kwargs['options']
    assert 'statement_timeout=1000' in kwargs['options']
    return Connection()
psycopg.connect = connect
"""


def database_fixture(material, tmp_path):
    source, value = request(material)
    root = material[0]
    manifest = json.loads((root / "snapshot.json").read_bytes())["corpus"]
    rows = json.loads((root / "entities.json").read_bytes())["entities"]
    payload = {
        "build": {"manifest": manifest, "row_count": len(rows)},
        "space": SPACE,
        "counts": {"entity_count": len(rows), "foreign_entity_count": 0},
        "rows": [
            {
                "entity": row,
                "artifact_hash": value["snapshot_identity"]["artifact_sha256"],
                "policy_version": POLICY_VERSION,
                "text_hash": text_hash(row["retrieval_text"]),
                "discovery_allowed": True,
                "has_embedding": True,
            }
            for row in rows
        ],
    }
    fixture_path = tmp_path / "db.json"
    fixture_path.write_text(json.dumps(payload))
    value["source"] = {"kind": "database", "manifest_pointer": "/corpus"}
    save(root, source.name, value)
    bootstrap = (
        f"import os\nos.environ['CORPUS_DB_FIXTURE'] = {str(fixture_path)!r}\n" + DATABASE_BOOTSTRAP
    )
    return source, value, payload, fixture_path, bootstrap


def test_database_measurement_is_read_only_consistent_and_secret_free(
    installed_cli, research_material, tmp_path
):
    source, _, _, _, bootstrap = database_fixture(research_material, tmp_path)
    prepared, measured = tmp_path / "prepared", tmp_path / "database"
    assert run(installed_cli, "prepare", source, "--directory", prepared).returncode == 0
    result = run(
        installed_cli,
        "measure",
        prepared / "receipt.json",
        "--directory",
        measured,
        "--database",
        "--dsn-env",
        "CORPUS_TEST_DSN",
        bootstrap=bootstrap,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    receipt = json.loads(result.stdout)
    sidecar = json.loads((measured / receipt["sidecar_ref"]["path"]).read_bytes())
    assert sidecar["eligible_entity_count"] == 2
    evidence = json.loads((measured / receipt["measurement_ref"]["path"]).read_bytes())
    assert evidence["source_identity"]["transaction"]["read_only"] is True
    assert evidence["source_identity"]["transaction"]["snapshot_id"] == "1:2:"
    for artifact in measured.rglob("*.json"):
        assert b"secret-fixture" not in artifact.read_bytes()
    exported = run(
        installed_cli, "export", measured / "receipt.json", "--directory", tmp_path / "db-export"
    )
    assert exported.returncode == 0, exported.stdout + exported.stderr


def test_database_deadline_includes_identity_checks_before_scan(
    installed_cli, research_material, tmp_path
):
    source, _, _, _, bootstrap = database_fixture(research_material, tmp_path)
    prepared, measured = tmp_path / "prepared", tmp_path / "deadline"
    assert run(installed_cli, "prepare", source, "--directory", prepared).returncode == 0
    bootstrap += "\nimport time\nticks = iter([0, 10])\ntime.monotonic = lambda: next(ticks, 10)\n"
    result = run(
        installed_cli,
        "measure",
        prepared / "receipt.json",
        "--directory",
        measured,
        "--database",
        "--dsn-env",
        "CORPUS_TEST_DSN",
        bootstrap=bootstrap,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    sidecar = json.loads((measured / "material/_corpus-sidecar.json").read_bytes())
    assert sidecar["count_status"] == "unavailable"
    assert sidecar["observed_subtotal"] is None
    assert sidecar["reasons"] == ["timeout"]


def test_database_observation_byte_budget_cannot_produce_exact_zero(
    installed_cli, research_material, tmp_path
):
    source, _, payload, fixture_path, bootstrap = database_fixture(research_material, tmp_path)
    payload["rows"][0]["entity"]["aliases"] = ["x" * 1100000]
    fixture_path.write_text(json.dumps(payload))
    prepared, measured = tmp_path / "prepared", tmp_path / "byte-limit"
    assert run(installed_cli, "prepare", source, "--directory", prepared).returncode == 0
    result = run(
        installed_cli,
        "measure",
        prepared / "receipt.json",
        "--directory",
        measured,
        "--database",
        "--dsn-env",
        "CORPUS_TEST_DSN",
        bootstrap=bootstrap,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    sidecar = json.loads((measured / "material/_corpus-sidecar.json").read_bytes())
    assert sidecar["eligible_entity_count"] is None
    assert sidecar["observed_subtotal"] == 0
    assert sidecar["reasons"] == ["observation_byte_limit"]


@pytest.mark.parametrize("fault", ["timeout", "failure", "connection_failure", "truncated", "cap"])
def test_incomplete_database_scan_retains_subtotals_without_exact_count(
    installed_cli, research_material, tmp_path, fault
):
    source, value, payload, fixture_path, bootstrap = database_fixture(research_material, tmp_path)
    payload["fault"] = fault
    if fault == "truncated":
        payload["rows"] = payload["rows"][:1]
    if fault == "cap":
        value["measurement_configuration"].update(max_entities=1, batch_size=1)
        save(research_material[0], source.name, value)
    fixture_path.write_text(json.dumps(payload))
    prepared, measured = tmp_path / "prepared", tmp_path / "partial"
    assert run(installed_cli, "prepare", source, "--directory", prepared).returncode == 0
    result = run(
        installed_cli,
        "measure",
        prepared / "receipt.json",
        "--directory",
        measured,
        "--database",
        "--dsn-env",
        "CORPUS_TEST_DSN",
        bootstrap=bootstrap,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    receipt = json.loads(result.stdout)
    sidecar = json.loads((measured / receipt["sidecar_ref"]["path"]).read_bytes())
    assert sidecar["eligible_entity_count"] is None
    assert sidecar["count_status"] == (
        "unavailable" if fault == "connection_failure" else "partial"
    )
    assert sidecar["observed_subtotal"] == (None if fault == "connection_failure" else 1)
    assert sidecar["reasons"] == [
        {
            "timeout": "timeout",
            "failure": "retrieval_failure",
            "connection_failure": "retrieval_failure",
            "truncated": "truncated_scan",
            "cap": "scan_limit",
        }[fault]
    ]
    result = run(
        installed_cli, "export", measured / "receipt.json", "--directory", tmp_path / "export"
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("fault", ["build", "space", "count", "policy", "row", "not_authorized"])
def test_database_drift_and_implicit_network_access_are_rejected(
    installed_cli, research_material, tmp_path, fault
):
    source, _, payload, fixture_path, bootstrap = database_fixture(research_material, tmp_path)
    if fault == "build":
        payload["build"]["row_count"] += 1
    if fault == "space":
        payload["space"] = {**SPACE, "version": "foreign"}
    if fault == "count":
        payload["counts"]["entity_count"] += 1
    if fault == "policy":
        payload["counts"]["foreign_entity_count"] = 1
    if fault == "row":
        payload["rows"][0]["artifact_hash"] = "f" * 64
    fixture_path.write_text(json.dumps(payload))
    prepared, rejected = tmp_path / "prepared", tmp_path / "rejected"
    assert run(installed_cli, "prepare", source, "--directory", prepared).returncode == 0
    result = run(
        installed_cli,
        "measure",
        prepared / "receipt.json",
        "--directory",
        rejected,
        *([] if fault == "not_authorized" else ["--database", "--dsn-env", "CORPUS_TEST_DSN"]),
        bootstrap=bootstrap,
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert not rejected.exists()


@pytest.mark.parametrize(
    "scope,rows,expected",
    [
        (
            {"kind": "bounding_box", "south": -11, "north": -10, "west": 30, "east": 31},
            [entity("edge", -11, 30), entity("inside", -10.5, 30.5), entity("outside", -9, 30)],
            2,
        ),
        ({"kind": "radius", "latitude": 70, "longitude": -40, "radius_m": 1000}, [], 0),
        (
            {"kind": "radius", "latitude": 0, "longitude": 179.99, "radius_m": 5000},
            [entity("across", 0.01, -179.99), entity("far", 0.01, -170)],
            1,
        ),
    ],
)
def test_distinct_inputs_snapshots_and_geographies_include_exact_zero(
    installed_cli, research_material, tmp_path, scope, rows, expected
):
    root, population, selection, census, _ = research_material
    population.update(population_id="different-inputs", revision="population-7")
    selection.update(
        population_id=population["population_id"], population_revision=population["revision"]
    )
    census.update(
        population_id=population["population_id"], population_revision=population["revision"]
    )
    case = population["cases"][0]
    case.update(
        case_id="coastal-request",
        revision="input-8",
        planned_versions=["v2"],
        repetition_ids=["solo"],
    )
    case["input_ref"] = save(
        root, "different-input.json", {"destination": "Different request", "coordinate": scope}
    )
    source, _ = request(research_material, rows, scope)
    prepared, measured = tmp_path / "prepared", tmp_path / "measured"
    assert run(installed_cli, "prepare", source, "--directory", prepared).returncode == 0
    result = run(installed_cli, "measure", prepared / "receipt.json", "--directory", measured)
    assert result.returncode == 0, result.stdout + result.stderr
    sidecar = json.loads((measured / json.loads(result.stdout)["sidecar_ref"]["path"]).read_bytes())
    assert sidecar["eligible_entity_count"] == sidecar["observed_subtotal"] == expected
    assert sidecar["case_id"] == "coastal-request"
    assert sidecar["scope"] == scope


@pytest.mark.parametrize(
    "fault",
    [
        "policy",
        "space",
        "text_policy",
        "input",
        "case",
        "scope_hash",
        "latitude",
        "box",
        "snapshot",
        "unsafe",
        "source_hash",
        "limit",
        "secrets",
    ],
)
def test_prepare_rejects_incompatible_or_unbounded_sources(
    installed_cli, research_material, tmp_path, fault
):
    source, value = request(research_material)
    root = research_material[0]
    if fault in ("policy", "space"):
        value["snapshot_identity"]["policy_version" if fault == "policy" else "space_id"] = (
            "foreign"
        )
    elif fault == "text_policy":
        snapshot = json.loads((root / "snapshot.json").read_bytes())
        snapshot["corpus"]["inputs"]["retrieval_text_template_version"] = "foreign"
        value["snapshot_identity"]["snapshot_ref"] = save(root, "snapshot.json", snapshot)
    elif fault == "input":
        value["input_sha256"] = "f" * 64
    elif fault == "case":
        value["case_revision"] = "foreign"
    elif fault == "scope_hash":
        value["scope_sha256"] = "f" * 64
    elif fault == "latitude":
        value["scope"]["latitude"] = 91
    elif fault == "box":
        value["scope"] = {
            "kind": "bounding_box",
            "south": 10,
            "north": 11,
            "west": 170,
            "east": -170,
        }
    elif fault == "snapshot":
        value["snapshot_identity"]["artifact_sha256"] = "f" * 64
    elif fault == "unsafe":
        value["source"]["dataset_ref"]["path"] = "../outside.json"
    elif fault == "source_hash":
        (root / "entities.json").write_bytes(b"{}")
    elif fault == "limit":
        value["measurement_configuration"]["max_source_bytes"] = 100
    else:
        value["source"]["password"] = "secret-fixture"
    save(root, source.name, value)
    result = run(installed_cli, "prepare", source, "--directory", tmp_path / "rejected")
    assert result.returncode == 2, result.stdout + result.stderr
    assert not (tmp_path / "rejected").exists()


@pytest.mark.parametrize(
    "basis,late", [("prospective", False), ("retrospective", True), ("prospective", True)]
)
@pytest.mark.parametrize("profile_source", ["request", "declaration"])
def test_profile_thresholds_and_dispatch_timing_remain_caller_owned(
    installed_cli, research_material, tmp_path, basis, late, profile_source
):
    from backend.tests.test_rtpeval_research_population_cli import add_attempt

    add_attempt(research_material, 0, "v2", "failed")
    source, value = request(research_material)
    root, population, _, _, _ = research_material
    declared = "2026-10-03T00:00:00Z" if late else "2026-10-01T00:00:00Z"
    value.update(declared_at=declared, timing_basis=basis)
    profile = {
        "schema_version": "rtpeval_research_coverage_profile_1",
        "coverage_profile_id": "operator-strata",
        "revision": "p7",
        "population_id": population["population_id"],
        "population_revision": population["revision"],
        "declared_at": declared,
        "timing_basis": basis,
        "snapshot_identity": value["snapshot_identity"],
        "cases": [
            {
                k: value[k]
                for k in ("case_id", "case_revision", "input_sha256", "scope", "scope_sha256")
            }
        ],
        "metric": "eligible_entity_count",
        "strata": [
            {"stratum_id": "sparse", "min_inclusive": 0, "max_exclusive": 5},
            {"stratum_id": "dense", "min_inclusive": 5, "max_exclusive": None},
        ],
    }
    value["coverage_profile_ref"] = save(root, "coverage-profile.json", profile)
    if profile_source == "declaration":
        relevance_ref = save(
            root,
            "relevance.json",
            {
                "schema_version": "rtpeval_research_relevance_1",
                "population_id": population["population_id"],
                "population_revision": population["revision"],
                "profile_id": research_material[2]["profile_id"],
                "profile_revision": research_material[2]["revision"],
                "interest_inventory_refs": [],
                "review_refs": [],
                "coverage_refs": [],
                "coverage_profile_ref": value.pop("coverage_profile_ref"),
            },
        )
        declaration = json.loads((root / "research.json").read_bytes())
        declaration["track_refs"]["relevance"] = relevance_ref
        value["declaration_ref"] = save(root, "research.json", declaration)
    original = (root / "coverage-profile.json").read_bytes()
    save(root, source.name, value)
    prepared, measured = tmp_path / "prepared", tmp_path / "measured"
    result = run(installed_cli, "prepare", source, "--directory", prepared)
    if late and basis == "prospective":
        assert result.returncode == 2
        assert not prepared.exists()
        return
    assert result.returncode == 0, result.stdout + result.stderr
    result = run(installed_cli, "measure", prepared / "receipt.json", "--directory", measured)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (measured / "material/coverage-profile.json").read_bytes() == original
    declared_path = measured / json.loads(result.stdout)["declaration_ref"]["path"]
    result = installed_cli(
        "research",
        "report",
        declared_path,
        "--track",
        "relevance",
        "--directory",
        tmp_path / "report",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads((tmp_path / "report/relevance.json").read_bytes())
    assert report["coverage"][0]["timing_basis"] == basis
    assert report["coverage"][0]["stratum_id"] == "sparse"
    assert report["coverage_profile"]["strata"] == profile["strata"]
    exported = run(
        installed_cli, "export", measured / "receipt.json", "--directory", tmp_path / "export"
    )
    assert exported.returncode == 0, exported.stdout + exported.stderr


@pytest.mark.parametrize("combined", [False, True])
def test_source_budget_is_checked_before_first_dependency_read(
    installed_cli, research_material, tmp_path, combined
):
    source, value = request(research_material)
    root, population, _, _, write = research_material
    size = 999000 if combined else 1001000
    population["cases"][0]["input_ref"] = save(root, "input-0.json", {"request": "x" * size})
    value["input_sha256"] = population["cases"][0]["input_ref"]["sha256"]
    value["declaration_ref"] = save(root, "research.json", json.loads(write().read_bytes()))
    save(root, source.name, value)
    result = run(
        installed_cli,
        "prepare",
        source,
        "--directory",
        tmp_path / "rejected",
        bootstrap="""
from pathlib import Path
original_read = Path.read_bytes
def guarded_read(path):
    if path.name == 'input-0.json':
        raise AssertionError('Over-budget dependency was read before resource check')
    return original_read(path)
Path.read_bytes = guarded_read
""",
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert "byte limit" in result.stdout
    assert not (tmp_path / "rejected").exists()


@pytest.mark.parametrize("empty", [False, True])
def test_end_of_saved_scan_deadline_cannot_produce_exact_count(
    installed_cli, research_material, tmp_path, empty
):
    source, _ = request(research_material, [] if empty else [entity("one")])
    prepared, measured = tmp_path / "prepared", tmp_path / "timed"
    assert run(installed_cli, "prepare", source, "--directory", prepared).returncode == 0
    ticks = [0, 10] if empty else [0, 0, 10]
    result = run(
        installed_cli,
        "measure",
        prepared / "receipt.json",
        "--directory",
        measured,
        bootstrap=f"import time\nticks = iter({ticks!r})\n"
        "time.monotonic = lambda: next(ticks, 10)\n",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    sidecar = json.loads((measured / "material/_corpus-sidecar.json").read_bytes())
    assert sidecar["eligible_entity_count"] is None
    assert sidecar["count_status"] == ("unavailable" if empty else "partial")
    assert sidecar["observed_subtotal"] == (0 if empty else 1)
    assert sidecar["reasons"] == ["timeout"]
    result = run(
        installed_cli, "export", measured / "receipt.json", "--directory", tmp_path / "export"
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("format", ["json", "parquet"])
def test_saved_scan_caps_and_timeouts_never_claim_complete_census(
    installed_cli, research_material, tmp_path, format
):
    source, value = request(research_material)
    root = research_material[0]
    if format == "parquet":
        import hashlib

        import pyarrow as pa
        import pyarrow.parquet as pq

        pq.write_table(
            pa.Table.from_pylist([entity("one"), entity("two", longitude=20.01)]),
            root / "entities.parquet",
        )
        raw = (root / "entities.parquet").read_bytes()
        artifact = hashlib.sha256(raw).hexdigest()
        value["source"]["dataset_ref"] = {
            "path": "entities.parquet",
            "sha256": artifact,
            "media_type": "application/vnd.apache.parquet",
            "availability": "available",
        }
        value["snapshot_identity"]["artifact_sha256"] = artifact
        snapshot = json.loads((root / "snapshot.json").read_bytes())
        snapshot["corpus"]["output_sha256"] = artifact
        value["snapshot_identity"]["snapshot_ref"] = save(root, "snapshot.json", snapshot)
        index = json.loads((root / "embedding-index.json").read_bytes())
        index["artifact_sha256"] = artifact
        value["source"]["embedding_index_ref"] = save(root, "embedding-index.json", index)
    value["measurement_configuration"].update(max_entities=1, batch_size=1)
    save(root, source.name, value)
    prepared, measured = tmp_path / "prepared", tmp_path / "capped"
    assert run(installed_cli, "prepare", source, "--directory", prepared).returncode == 0
    result = run(installed_cli, "measure", prepared / "receipt.json", "--directory", measured)
    assert result.returncode == 0, result.stdout + result.stderr
    sidecar = json.loads((measured / "material/_corpus-sidecar.json").read_bytes())
    assert sidecar["count_status"] == "partial" and sidecar["eligible_entity_count"] is None
    assert sidecar["observed_subtotal"] == 1 and sidecar["reasons"] == ["scan_limit"]
    timed = tmp_path / "timed"
    result = run(
        installed_cli,
        "measure",
        prepared / "receipt.json",
        "--directory",
        timed,
        bootstrap="import time\nticks = iter([0, 0, 10])\n"
        "time.monotonic = lambda: next(ticks, 10)\n",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    sidecar = json.loads((timed / "material/_corpus-sidecar.json").read_bytes())
    assert sidecar["eligible_entity_count"] is None and sidecar["reasons"] == ["timeout"]
    result = run(
        installed_cli, "export", timed / "receipt.json", "--directory", tmp_path / "export"
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("fault", ["count", "observation", "missing", "clock", "identity"])
def test_saved_measurement_forgery_or_missing_evidence_is_rejected(
    installed_cli, research_material, tmp_path, fault
):
    source, _ = request(research_material)
    prepared, measured = tmp_path / "prepared", tmp_path / "measured"
    assert run(installed_cli, "prepare", source, "--directory", prepared).returncode == 0
    assert (
        run(installed_cli, "measure", prepared / "receipt.json", "--directory", measured).returncode
        == 0
    )
    receipt = json.loads((measured / "receipt.json").read_bytes())
    evidence = json.loads((measured / receipt["measurement_ref"]["path"]).read_bytes())
    if fault == "count":
        sidecar = json.loads((measured / receipt["sidecar_ref"]["path"]).read_bytes())
        sidecar.update(eligible_entity_count=999, observed_subtotal=999)
        receipt["sidecar_ref"] = save(measured, receipt["sidecar_ref"]["path"], sidecar)
    elif fault == "observation":
        evidence["observations"][0]["has_embedding"] = False
    elif fault == "clock":
        evidence["finished_at"] = "2026-01-01T00:00:00Z"
    elif fault == "identity":
        evidence["source_identity"]["artifact_sha256"] = "f" * 64
    if fault == "missing":
        (measured / receipt["measurement_ref"]["path"]).unlink()
    else:
        receipt["measurement_ref"] = save(measured, receipt["measurement_ref"]["path"], evidence)
    save(measured, "receipt.json", receipt)
    result = run(
        installed_cli, "export", measured / "receipt.json", "--directory", tmp_path / "rejected"
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert not (tmp_path / "rejected").exists()


def test_source_drift_and_interrupted_publication_do_not_produce_success_receipts(
    installed_cli, research_material, tmp_path
):
    source, _ = request(research_material)
    prepared = tmp_path / "prepared"
    assert run(installed_cli, "prepare", source, "--directory", prepared).returncode == 0
    blocked = tmp_path / "interrupted"
    result = run(
        installed_cli,
        "measure",
        prepared / "receipt.json",
        "--directory",
        blocked,
        bootstrap="""
from pathlib import Path
original_write = Path.write_bytes
def interrupted_write(path, raw):
    if path.name == 'receipt.json':
        original_write(path, b'{"processing_status":')
        raise OSError('Synthetic interrupted publication')
    return original_write(path, raw)
Path.write_bytes = interrupted_write
""",
    )
    assert result.returncode == 2
    with pytest.raises(json.JSONDecodeError):
        json.loads((blocked / "receipt.json").read_bytes())
    rejected = installed_cli(
        "research", "validate", blocked / "material/_corpus-research.json", "--track", "relevance"
    )
    assert rejected.returncode == 2, rejected.stdout + rejected.stderr
    (prepared / "material/entities.json").write_bytes(b"{}")
    result = run(
        installed_cli, "measure", prepared / "receipt.json", "--directory", tmp_path / "drift"
    )
    assert result.returncode == 2 and not (tmp_path / "drift").exists()


def test_final_completion_interruption_is_rejected_even_with_a_saved_root_receipt(
    installed_cli, research_material, tmp_path
):
    source, _ = request(research_material)
    prepared, interrupted = tmp_path / "prepared", tmp_path / "unsealed"
    assert run(installed_cli, "prepare", source, "--directory", prepared).returncode == 0
    result = run(
        installed_cli,
        "measure",
        prepared / "receipt.json",
        "--directory",
        interrupted,
        bootstrap="""
from pathlib import Path
original_write = Path.write_bytes
def interrupted_write(path, raw):
    if path.name == '_corpus-completion.json' and 'unsealed' in path.parts:
        original_write(path, b'{"processing_status":')
        raise OSError('Synthetic interrupted final completion')
    return original_write(path, raw)
Path.write_bytes = interrupted_write
""",
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert (
        json.loads((interrupted / "receipt.json").read_bytes())["processing_status"] == "completed"
    )
    rejected = installed_cli(
        "research",
        "validate",
        interrupted / "material/_corpus-research.json",
        "--track",
        "relevance",
    )
    assert rejected.returncode == 2, rejected.stdout + rejected.stderr
    rejected = run(
        installed_cli, "export", interrupted / "receipt.json", "--directory", tmp_path / "export"
    )
    assert rejected.returncode == 2 and not (tmp_path / "export").exists()


@pytest.mark.parametrize("operation", [None, "prepare", "measure", "export"])
def test_corpus_help_is_offline_discoverable_and_separates_operations(installed_cli, operation):
    result = installed_cli(
        "research", "corpus", *([] if operation is None else [operation]), "--help"
    )
    assert result.returncode == 0
    if operation is None:
        assert all(name in result.stdout for name in ("prepare", "measure", "export"))
    else:
        assert "Fresh" in result.stdout
    if operation == "measure":
        assert "--database" in result.stdout and "--dsn-env" in result.stdout


@pytest.mark.parametrize("compatible", [True, False])
def test_selected_rag_snapshot_is_checked_before_corpus_measurement(
    installed_cli, research_material, tmp_path, compatible
):
    from backend.tests.test_rtpeval_research_relevance_cli import discovery, write_relevance

    entry, capture = discovery(research_material)
    source, value = request(research_material)
    root = research_material[0]
    if compatible:
        for stage in capture["stages"].values():
            for place in stage["places"]:
                for origin in place["rag_origins"]:
                    origin.update(
                        artifact_hash=value["snapshot_identity"]["artifact_sha256"],
                        policy_version=POLICY_VERSION,
                        space_id=SPACE_ID,
                    )
        entry["capture_ref"] = save(root, "capture-v2.json", capture)
    declaration = write_relevance(research_material, [entry])
    value["declaration_ref"] = save(root, declaration.name, json.loads(declaration.read_bytes()))
    save(root, source.name, value)
    prepared = tmp_path / "prepared"
    result = run(installed_cli, "prepare", source, "--directory", prepared)
    if not compatible:
        assert result.returncode == 2, result.stdout + result.stderr
        assert not prepared.exists()
        return
    assert result.returncode == 0, result.stdout + result.stderr
    result = run(
        installed_cli, "measure", prepared / "receipt.json", "--directory", tmp_path / "measured"
    )
    assert result.returncode == 0, result.stdout + result.stderr
    receipt = json.loads(result.stdout)
    declared = tmp_path / "measured" / receipt["declaration_ref"]["path"]
    assert installed_cli("research", "validate", declared, "--track", "relevance").returncode == 0


def test_preparation_and_saved_export_never_load_database_driver_or_credentials(
    installed_cli, research_material, tmp_path
):
    source, _ = request(research_material)
    deny_database = "forbidden += ('psycopg', 'backend.app.tripworld.retrieval.runtime')\n"
    prepared, measured = tmp_path / "prepared", tmp_path / "measured"
    result = run(installed_cli, "prepare", source, "--directory", prepared, bootstrap=deny_database)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (
        run(
            installed_cli,
            "measure",
            prepared / "receipt.json",
            "--directory",
            measured,
            bootstrap=deny_database,
        ).returncode
        == 0
    )
    result = run(
        installed_cli,
        "export",
        measured / "receipt.json",
        "--directory",
        tmp_path / "export",
        bootstrap=deny_database,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_one_scope_can_be_measured_inside_a_larger_declared_population(
    installed_cli, research_material, tmp_path
):
    root, population, _, _, write = research_material
    second = population["cases"][1]
    source, value = request(research_material)
    population["cases"].append(second)
    value["declaration_ref"] = save(root, "research.json", json.loads(write().read_bytes()))
    save(root, source.name, value)
    prepared = tmp_path / "prepared"
    result = run(installed_cli, "prepare", source, "--directory", prepared)
    assert result.returncode == 0, result.stdout + result.stderr
    result = run(
        installed_cli, "measure", prepared / "receipt.json", "--directory", tmp_path / "measured"
    )
    assert result.returncode == 0, result.stdout + result.stderr
    first_material = tmp_path / "measured/material"
    second_value = json.loads((first_material / source.name).read_bytes())
    second_value.update(
        case_id=second["case_id"],
        case_revision=second["revision"],
        input_sha256=second["input_ref"]["sha256"],
    )
    second_value["declaration_ref"] = save(
        first_material,
        "_corpus-research.json",
        json.loads((first_material / "_corpus-research.json").read_bytes()),
    )
    second_source = first_material / "second-request.json"
    save(first_material, second_source.name, second_value)
    second_prepared = tmp_path / "second-prepared"
    result = run(installed_cli, "prepare", second_source, "--directory", second_prepared)
    assert result.returncode == 0, result.stdout + result.stderr
    second_measured = tmp_path / "second-measured"
    result = run(
        installed_cli, "measure", second_prepared / "receipt.json", "--directory", second_measured
    )
    assert result.returncode == 0, result.stdout + result.stderr
    receipt = json.loads(result.stdout)
    reported = installed_cli(
        "research",
        "report",
        second_measured / receipt["declaration_ref"]["path"],
        "--track",
        "relevance",
        "--directory",
        tmp_path / "report",
    )
    assert reported.returncode == 0, reported.stdout + reported.stderr
    coverage = json.loads((tmp_path / "report/relevance.json").read_bytes())["coverage"]
    assert [row["eligible_entity_count"] for row in coverage] == [2, 2]
    exported = run(
        installed_cli,
        "export",
        second_measured / "receipt.json",
        "--directory",
        tmp_path / "export",
    )
    assert exported.returncode == 0, exported.stdout + exported.stderr
