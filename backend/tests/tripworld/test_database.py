"""Production policy unit tests and opt-in real PostgreSQL contract tests, no live APIs."""

import os
from pathlib import Path

import numpy as np
import psycopg
import pyarrow.parquet as pq
import pytest
from psycopg.types.json import Jsonb

from backend.app.tripworld.artifacts import load_json_object
from backend.app.tripworld.database.policy import exclusion_reasons, normalized_name, text_hash
from backend.app.tripworld.database.search import PostgresSearch, geographic_sql, search_query
from backend.app.tripworld.database.vectors import SPACE_ID
from backend.app.tripworld.hashing import sha256_file
from backend.app.tripworld.retrieval.geography import GeographicScope
from backend.tests.product.database_safety import require_test_database
from backend.tests.tripworld.test_retrieval_foundation import source_row
from tools.data.tripworld.artifact_persistence import write_json_if_changed
from tools.data.tripworld.corpus import build_corpus
from tools.data.tripworld.database_connection import TripWorldDatabaseError, connection, migrate
from tools.data.tripworld.database_ingestion import ingest, validate_artifact
from tools.data.tripworld.entity_builder import build_entities, merge_entity
from tools.data.tripworld.preprocessing import project_source
from tools.data.tripworld.vector_store import prepare_space, store_vectors


def test_production_policy_keeps_unknown_and_exact_threshold(tiny_manifest):
    entity = merge_entity([source_row("a", semantic_eligibility_hints=[])], tiny_manifest)
    assert not exclusion_reasons(entity)
    assert not exclusion_reasons(entity.model_copy(update={"coordinate_spread_km": 10.0}))
    assert exclusion_reasons(entity.model_copy(update={"coordinate_spread_km": 10.001})) == [
        "coordinate_spread_over_10km"
    ]
    excluded = entity.model_copy(
        update={
            "eligibility_hint": "ineligible",
            "retrieval_text": "",
            "latitude": None,
            "location_flags": ("country_conflict",),
        }
    )
    assert exclusion_reasons(excluded) == [
        "ineligible",
        "empty_text",
        "invalid_coordinates",
        "country_conflict",
    ]


def test_name_normalization_and_text_hash_are_deliberately_different():
    assert normalized_name("  Ｍuseum  CAFÉ ") == "museum café"
    assert text_hash("Museum") != text_hash("museum")


@pytest.mark.parametrize("longitude", [179.9, -179.9])
def test_sql_geo_wrap_parameters(longitude):
    where, params = geographic_sql(GeographicScope(latitude=0, longitude=longitude, radius_km=50))
    assert " OR " in where
    assert params["left"] > params["right"]


def test_bad_vector_and_k_rejected_before_database():
    scope = GeographicScope(latitude=0, longitude=0, radius_km=1)
    with pytest.raises(ValueError):
        search_query(scope, np.zeros(1536, dtype=np.float32), 10)
    with pytest.raises(ValueError):
        search_query(scope, np.ones(1536, dtype=np.float32), 0)


def test_database_errors_sanitized(monkeypatch):
    monkeypatch.setenv("DAYLOOM_DB_PASSWORD", "secret-for-test")

    def fail(**kwargs):
        raise psycopg.OperationalError("secret-for-test")

    monkeypatch.setattr(psycopg, "connect", fail)
    with pytest.raises(TripWorldDatabaseError) as error:
        with connection():
            pass
    assert "secret-for-test" not in str(error.value)


def test_locked_progress_report_does_not_abort_paid_build(monkeypatch, tmp_path):
    from tools.data.tripworld import database_build as production

    def locked(*args):
        raise PermissionError("report is being read")

    monkeypatch.setattr(production, "write_json_if_changed", locked)
    monkeypatch.setattr(production.time, "sleep", lambda _: None)
    production.write_progress(tmp_path / "report.json", {"status": "running"})


@pytest.fixture
def entity_artifact(tmp_path, tiny_source, tiny_manifest, semantic_mapping):
    selected, corpus, entities = [
        tmp_path / name for name in ("selected.parquet", "corpus.parquet", "entities.parquet")
    ]
    project_source(tiny_source, selected, tiny_manifest)
    build_corpus(selected, corpus, tiny_manifest, semantic_mapping)
    build_entities(corpus, entities, tiny_manifest)
    return entities


def test_ingestion_rejects_hash_and_version_before_writes(entity_artifact):
    meta_path = entity_artifact.with_suffix(".parquet.manifest.json")
    meta = load_json_object(meta_path)
    meta["inputs"]["retrieval_entity_builder_version"] = "unsupported"
    write_json_if_changed(meta_path, meta)
    with pytest.raises(ValueError, match="version"):
        validate_artifact(entity_artifact)
    entity_artifact.write_bytes(entity_artifact.read_bytes() + b"corrupt")
    with pytest.raises(ValueError, match="hash"):
        validate_artifact(entity_artifact)


@pytest.fixture
def db(monkeypatch):
    if os.environ.get("DAYLOOM_DB_TESTS") != "1":
        pytest.skip("Set DAYLOOM_DB_TESTS=1 for isolated local PostgreSQL tests")
    dsn = os.environ.get("DAYLOOM_DB_TEST_URL", "")
    require_test_database(dsn)
    monkeypatch.setenv("DAYLOOM_DB_URL", dsn)
    with connection() as conn:
        assert "test" in conn.info.dbname.lower()
        conn.execute("DROP SCHEMA IF EXISTS tripworld CASCADE")
        conn.commit()
        migrate(conn)
        conn.commit()
        yield conn


def test_real_migrations_extension_and_checksum(db, tmp_path):
    assert db.execute("SELECT extversion FROM pg_extension WHERE extname='vector'").fetchone()
    assert migrate(db) == []
    path = Path(__file__).parents[3] / "tools/data/tripworld/migrations/001_retrieval.sql"
    (tmp_path / path.name).write_text(path.read_text() + "\n-- changed", encoding="utf-8")
    with pytest.raises(ValueError, match="checksum"):
        migrate(db, tmp_path)


def test_real_ingestion_idempotence_text_change_and_vector_invalidation(db, entity_artifact):
    first = ingest(db, entity_artifact)
    assert first["rows"] == 5 and first["changed"] == 5
    assert ingest(db, entity_artifact)["changed"] == 0
    prepare_space(db)
    row = db.execute("SELECT * FROM tripworld.entities WHERE discovery_allowed LIMIT 1").fetchone()
    v = np.zeros((1, 1536), dtype=np.float32)
    v[0, 0] = 1
    assert store_vectors(db, [row["text_hash"]], v, {"fake": True}) == 1
    assert store_vectors(db, [row["text_hash"]], v, {"fake": True}) == 0
    table = pq.read_table(entity_artifact)
    records = table.to_pylist()
    for record in records:
        if record["retrieval_entity_id"] == row["retrieval_entity_id"]:
            record["retrieval_text"] += " changed"
            record["content_hash"] = text_hash(record["retrieval_text"])
    import pyarrow as pa

    pq.write_table(pa.Table.from_pylist(records, schema=table.schema), entity_artifact)
    meta = load_json_object(entity_artifact.with_suffix(".parquet.manifest.json"))
    meta["output_sha256"] = sha256_file(entity_artifact)
    write_json_if_changed(entity_artifact.with_suffix(".parquet.manifest.json"), meta)
    ingest(db, entity_artifact)
    assert not db.execute("SELECT * FROM tripworld.entity_embeddings").fetchall()
    assert db.execute("SELECT count(*) AS n FROM tripworld.embeddings").fetchone()["n"] == 1


def test_real_exact_geo_alias_policy_and_ties(db, entity_artifact):
    ingest(db, entity_artifact)
    prepare_space(db)
    rows = db.execute(
        "SELECT retrieval_entity_id,text_hash FROM tripworld.entities ORDER BY retrieval_entity_id"
    ).fetchall()
    vectors = np.zeros((len(rows), 1536), dtype=np.float32)
    vectors[:, 0] = 1
    store_vectors(db, [r["text_hash"] for r in rows], vectors, {"fake": True})
    db.execute(
        "UPDATE tripworld.entities SET latitude=0,longitude=179.95,country='JP', "
        "discovery_allowed=true,exclusion_reasons='{}',normalized_names=ARRAY['museum','alias']"
    )
    db.execute(
        "UPDATE tripworld.entities SET discovery_allowed=false,"
        "exclusion_reasons=ARRAY['ineligible'] WHERE retrieval_entity_id=%s",
        (rows[-1]["retrieval_entity_id"],),
    )
    db.commit()
    search = PostgresSearch(db)
    scope = GeographicScope(latitude=0, longitude=-179.95, radius_km=30, country="jp")
    hits = search.search(vectors[0], scope, 2)
    assert [h["retrieval_entity_id"] for h in hits] == [r["retrieval_entity_id"] for r in rows[:2]]
    assert all(abs(h["similarity_score"] - 1) < 1e-6 for h in hits)
    assert len(search.lexical("  ALIAS ", scope)) == 4
    assert not search.lexical("missing", scope)
    assert not search.search(vectors[0], scope.model_copy(update={"radius_km": 1}), 10)
    assert search.counts(scope) == {"geographic_count": 5, "post_policy_count": 4}
    assert not search.search(vectors[0], scope.model_copy(update={"country": "US"}), 10)


def test_real_incompatible_space_rejected(db):
    db.execute(
        "INSERT INTO tripworld.embedding_spaces VALUES (%s,%s)",
        (SPACE_ID, Jsonb({"model": "wrong"})),
    )
    db.commit()
    with pytest.raises(ValueError, match="compatibility"):
        prepare_space(db)


def test_real_stale_policy_rejected(db, entity_artifact):
    ingest(db, entity_artifact)
    db.execute("UPDATE tripworld.entities SET policy_version='superseded'")
    db.commit()
    with pytest.raises(ValueError, match="policy version mismatch"):
        PostgresSearch(db)


def test_real_readonly_search_and_missing_space_before_api(db, entity_artifact, tmp_path):
    from tools.diagnostics.retrieval_service import RetrievalService

    ingest(db, entity_artifact)
    scope = GeographicScope(latitude=0, longitude=0, radius_km=10)

    def forbidden_provider(config):
        raise AssertionError("No paid request before compatibility validation")

    service = RetrievalService(db, tmp_path, provider_factory=forbidden_provider)
    with pytest.raises(ValueError, match="compatibility"):
        service.retrieve("museum", scope)
    assert db.execute("SELECT count(*) AS n FROM tripworld.embedding_spaces").fetchone()["n"] == 0
    prepare_space(db)
    db.execute("SET TRANSACTION READ ONLY")
    vector = np.zeros(1536, dtype=np.float32)
    vector[0] = 1
    assert PostgresSearch(db).search(vector, scope) == []
    db.rollback()


def test_real_bad_snapshot_rolls_back_without_losing_entities(db, entity_artifact):
    ingest(db, entity_artifact)
    sidecar = entity_artifact.with_suffix(".parquet.manifest.json")
    meta = load_json_object(sidecar)
    meta["entity_count"] += 1
    write_json_if_changed(sidecar, meta)
    with pytest.raises(ValueError, match="count mismatch"):
        ingest(db, entity_artifact)
    assert db.execute("SELECT count(*) AS n FROM tripworld.entities").fetchone()["n"] == 5


def test_real_geo_pole_and_box_corner(db, entity_artifact):
    ingest(db, entity_artifact)
    search = PostgresSearch(db)
    db.execute("UPDATE tripworld.entities SET country=NULL,latitude=89.9,longitude=180")
    assert (
        search.counts(GeographicScope(latitude=89.9, longitude=0, radius_km=30))["geographic_count"]
        == 5
    )
    db.execute("UPDATE tripworld.entities SET latitude=0.8,longitude=0.8")
    assert (
        search.counts(GeographicScope(latitude=0, longitude=0, radius_km=100))["geographic_count"]
        == 0
    )


def test_real_build_resume_and_no_api_for_unchanged_text(
    db, entity_artifact, tmp_path, monkeypatch
):
    from types import SimpleNamespace

    from tools.data.tripworld import database_build as production
    from tools.data.tripworld.embedding_config import EmbeddingConfig, EncodedBatch

    ingest(db, entity_artifact)
    monkeypatch.setattr(
        production,
        "tokenizer",
        lambda: SimpleNamespace(encode_ordinary=lambda text: list(text.encode("utf-8"))),
    )
    monkeypatch.setattr(
        production, "production_config", lambda: EmbeddingConfig(max_batch_inputs=1, max_run_usd=5)
    )
    production.preflight(db, tmp_path)

    class FakeProvider:
        calls = 0
        fail = True

        def __init__(self, config):
            self.config = config

        def encode(self, texts, **kwargs):
            FakeProvider.calls += 1
            if FakeProvider.fail and FakeProvider.calls == 2:
                raise RuntimeError("simulated interruption")
            vectors = np.zeros((len(texts), 1536), dtype=np.float32)
            vectors[:, 0] = 1
            return EncodedBatch(vectors, 10, 10, self.config.model_name)

        def close(self):
            pass

    with pytest.raises(RuntimeError, match="interruption"):
        production.build(db, tmp_path, workers=1, provider_factory=FakeProvider)
    assert db.execute("SELECT count(*) AS n FROM tripworld.embeddings").fetchone()["n"] == 1
    FakeProvider.fail = False
    production.build(db, tmp_path, workers=1, provider_factory=FakeProvider)
    calls = FakeProvider.calls
    result = production.build(db, tmp_path, workers=1, provider_factory=FakeProvider)
    assert FakeProvider.calls == calls
    assert result["current_run"].get("new_usage_tokens", 0) == 0
