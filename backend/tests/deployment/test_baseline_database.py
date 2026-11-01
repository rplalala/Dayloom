"""Opt-in public CLI round trips use disposable databases and no providers."""

import json
import os
import shutil
from dataclasses import dataclass
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from backend.tests.deployment.test_baseline_cli import run_cli


@dataclass(repr=False)
class DatabasePair:
    source: str
    target: str

    def __repr__(self):
        return "<isolated baseline test databases>"


@pytest.fixture
def databases(monkeypatch):
    dsn = os.environ.get("DAYLOOM_BASELINE_TEST_URL")
    if not dsn or not shutil.which("pg_dump") or not shutil.which("pg_restore"):
        pytest.skip("Explicit isolated test connection and PostgreSQL 17 tools are required")
    params = conninfo_to_dict(dsn)
    if "test" not in params.get("dbname", "").lower():
        pytest.fail("Baseline acceptance requires an explicit isolated test database name")
    names = ["baseline_test_" + uuid4().hex for _ in range(2)]
    with psycopg.connect(**{**params, "dbname": "postgres"}, autocommit=True) as admin:
        for name in names:
            admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
        source, target = [make_conninfo(**{**params, "dbname": name}) for name in names]
        monkeypatch.setenv("BASELINE_SOURCE_TEST_URL", source)
        monkeypatch.setenv("BASELINE_TARGET_TEST_URL", target)
        try:
            with psycopg.connect(source, autocommit=True) as conn:
                conn.execute("CREATE SCHEMA app; CREATE SCHEMA tripworld")
                conn.execute("CREATE EXTENSION vector WITH SCHEMA tripworld")
                conn.execute("""CREATE TABLE app.users (
                    id text PRIMARY KEY, email text, password_hash text);
                    CREATE TABLE app.trips (id text PRIMARY KEY,
                        owner_id text REFERENCES app.users(id), media_cache jsonb);
                    CREATE TABLE app.planning_tasks (id text PRIMARY KEY, state text);
                    CREATE TABLE tripworld.entities (id text PRIMARY KEY, name text);
                    CREATE TABLE tripworld.embeddings (id text PRIMARY KEY,
                        embedding tripworld.vector(3));
                    CREATE TABLE tripworld.corpus_builds (artifact_hash text PRIMARY KEY,
                        manifest jsonb NOT NULL, row_count bigint);
                    INSERT INTO tripworld.corpus_builds VALUES ('fixture',
                        '{"output_sha256":"fixture","entity_count":1}',1);
                    INSERT INTO app.users VALUES ('admin','admin@admin.com','retained-test-hash');
                    INSERT INTO app.trips VALUES ('trip','admin',
                        '{"photo":{"revision":"retained","url":"https://lh3.googleusercontent.com/test"}}');
                    INSERT INTO app.planning_tasks VALUES ('task','completed');
                    INSERT INTO tripworld.entities VALUES ('entity','Test museum');
                    INSERT INTO tripworld.embeddings VALUES ('vector','[1,0,0]');
                """)
            yield DatabasePair(source, target)
        finally:
            for name in names:
                admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))


def export_to(root, tmp_path):
    runtime = tmp_path / "resources"
    for name, content in {
        "artifacts/retrieval_entities.parquet.manifest.json": {
            "output_sha256": "fixture", "entity_count": 1,
        },
        "reports/phase5_embedding_run.json": {"status": "complete"},
    }.items():
        target = runtime / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(content), encoding="utf-8")
    notice = tmp_path / "NOTICE.txt"
    notice.write_text("Controlled baseline test notice", encoding="utf-8")
    return run_cli("export", "--output", root, "--runtime-root", runtime,
                   "--source-revision", "1" * 40, "--notice", notice,
                   "--dsn-env", "BASELINE_SOURCE_TEST_URL")


def test_complete_round_trip_retains_admin_cache_and_later_destination_writes(databases, tmp_path):
    target = databases.target
    release = tmp_path / "baseline"
    exported = export_to(release, tmp_path)
    assert exported.returncode == 0, exported.stderr
    restored = run_cli("restore", release, "--dsn-env", "BASELINE_TARGET_TEST_URL")
    assert restored.returncode == 0, restored.stderr
    assert json.loads(restored.stdout)["status"] == "installed"
    with psycopg.connect(target, autocommit=True) as conn:
        assert conn.execute("SELECT email,password_hash FROM app.users").fetchone() == (
            "admin@admin.com", "retained-test-hash",
        )
        cache = conn.execute("SELECT media_cache FROM app.trips").fetchone()[0]
        assert cache["photo"]["revision"] == "retained"
        conn.execute("INSERT INTO app.users VALUES ('later','later@example.test','later-hash')")
    reused = run_cli("restore", release, "--dsn-env", "BASELINE_TARGET_TEST_URL")
    assert reused.returncode == 0, reused.stderr
    assert json.loads(reused.stdout)["status"] == "reused"
    with psycopg.connect(target) as conn:
        assert conn.execute("SELECT count(*) FROM app.users").fetchone()[0] == 2


def test_export_rejects_a_mismatched_runtime_manifest(databases, tmp_path):
    with psycopg.connect(databases.source, autocommit=True) as conn:
        conn.execute("UPDATE tripworld.corpus_builds SET row_count=2")
    result = export_to(tmp_path / "baseline", tmp_path)
    assert result.returncode == 2
    assert "retrieval" in result.stderr.lower()


def test_committed_restore_without_registration_is_recognized_exactly(databases, tmp_path):
    release = tmp_path / "baseline"
    assert export_to(release, tmp_path).returncode == 0
    assert run_cli("restore", release, "--dsn-env", "BASELINE_TARGET_TEST_URL").returncode == 0
    with psycopg.connect(databases.target, autocommit=True) as conn:
        conn.execute("DROP TABLE app.deployment_baseline")
    recovered = run_cli("restore", release, "--dsn-env", "BASELINE_TARGET_TEST_URL")
    assert recovered.returncode == 0, recovered.stderr
    assert json.loads(recovered.stdout)["status"] == "recovered"


def test_unknown_nonempty_target_is_not_overwritten(databases, tmp_path):
    release = tmp_path / "baseline"
    assert export_to(release, tmp_path).returncode == 0
    with psycopg.connect(databases.target, autocommit=True) as conn:
        conn.execute("CREATE TABLE public.keep (id integer PRIMARY KEY); "
                     "INSERT INTO keep VALUES (7)")
    rejected = run_cli("restore", release, "--dsn-env", "BASELINE_TARGET_TEST_URL")
    assert rejected.returncode == 2
    assert "preserved" in rejected.stderr
    with psycopg.connect(databases.target) as conn:
        assert conn.execute("SELECT id FROM public.keep").fetchall() == [(7,)]
        assert conn.execute("SELECT to_regclass('app.users')").fetchone()[0] is None


def test_active_planning_work_prevents_capture(databases, tmp_path):
    with psycopg.connect(databases.source, autocommit=True) as conn:
        conn.execute("UPDATE app.planning_tasks SET state='running'")
    result = export_to(tmp_path / "baseline", tmp_path)
    assert result.returncode == 2
    assert "active planning" in result.stderr
    assert not (tmp_path / "baseline").exists()


def test_corrupt_dump_is_rejected_before_target_changes(databases, tmp_path):
    release = tmp_path / "baseline"
    assert export_to(release, tmp_path).returncode == 0
    (release / "database.pgcustom").write_bytes(b"broken")
    result = run_cli("restore", release, "--dsn-env", "BASELINE_TARGET_TEST_URL")
    assert result.returncode == 2
    assert "checksum" in result.stderr.lower()
    with psycopg.connect(databases.target) as conn:
        assert conn.execute("SELECT to_regclass('app.users')").fetchone()[0] is None
