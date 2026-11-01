"""Opt-in public CLI round trips use disposable databases and no providers."""

import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
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


def test_unknown_public_function_target_is_not_modified(databases, tmp_path):
    release = tmp_path / "baseline"
    assert export_to(release, tmp_path).returncode == 0
    with psycopg.connect(databases.target, autocommit=True) as conn:
        conn.execute("CREATE FUNCTION public.keep() RETURNS integer LANGUAGE sql AS 'SELECT 7'")
    rejected = run_cli("restore", release, "--dsn-env", "BASELINE_TARGET_TEST_URL")
    assert rejected.returncode == 2
    with psycopg.connect(databases.target) as conn:
        assert conn.execute("SELECT public.keep()").fetchone() == (7,)
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


def start_restore(release):
    return subprocess.Popen(
        [sys.executable, "-m", "deploy.release.baseline", "restore", str(release),
         "--dsn-env", "BASELINE_TARGET_TEST_URL"],
        cwd=Path(__file__).resolve().parents[3], env=os.environ.copy(),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )


def wait_for_gate(connection, process, *, application="pg_restore"):
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        row = connection.execute(
            "SELECT pid FROM pg_stat_activity WHERE datname=current_database() "
            "AND wait_event='advisory' AND application_name=%s", (application,),
        ).fetchone()
        if row:
            return row[0]
        assert process.poll() is None, process.communicate()
        time.sleep(0.05)
    pytest.fail("Controlled initializer did not reach the external database fault gate")


def add_restore_gate(source):
    with psycopg.connect(source, autocommit=True) as conn:
        conn.execute("""CREATE FUNCTION app.restore_gate(integer) RETURNS boolean AS $$
            BEGIN
                IF current_setting('application_name') = 'pg_restore' THEN
                    PERFORM pg_advisory_xact_lock(252005);
                END IF;
                RETURN true;
            END $$ LANGUAGE plpgsql;
            CREATE TABLE app.restore_gate_rows (
                id integer PRIMARY KEY CHECK (app.restore_gate(id)));
            INSERT INTO app.restore_gate_rows VALUES (1)""")


def test_interrupted_restore_rolls_back_and_retry_installs_once(databases, tmp_path):
    add_restore_gate(databases.source)
    release = tmp_path / "baseline"
    assert export_to(release, tmp_path).returncode == 0
    with psycopg.connect(databases.target, autocommit=True) as observer:
        observer.execute("SELECT pg_advisory_lock(252005)")
        process = start_restore(release)
        try:
            backend = wait_for_gate(observer, process)
            observer.execute("SELECT pg_terminate_backend(%s)", (backend,))
            stdout, stderr = process.communicate(timeout=15)
            assert process.returncode == 2, stdout + stderr
            assert observer.execute("SELECT to_regclass('app.users')").fetchone()[0] is None
            assert observer.execute(
                "SELECT to_regclass('app.deployment_baseline')"
            ).fetchone()[0] is None
        finally:
            observer.execute("SELECT pg_advisory_unlock(252005)")
            if process.poll() is None:
                process.kill()
                process.communicate()
    retry = run_cli("restore", release, "--dsn-env", "BASELINE_TARGET_TEST_URL")
    assert retry.returncode == 0, retry.stderr
    assert json.loads(retry.stdout)["status"] == "installed"


def test_concurrent_initializers_serialize_and_preserve_later_writes(databases, tmp_path):
    add_restore_gate(databases.source)
    release = tmp_path / "baseline"
    assert export_to(release, tmp_path).returncode == 0
    with psycopg.connect(databases.target, autocommit=True) as observer:
        observer.execute("SELECT pg_advisory_lock(252005)")
        first = start_restore(release)
        second = None
        try:
            wait_for_gate(observer, first)
            second = start_restore(release)
            wait_for_gate(observer, second, application="")
            observer.execute("SELECT pg_advisory_unlock(252005)")
            outcomes = [process.communicate(timeout=15) for process in (first, second)]
            assert all(process.returncode == 0 for process in (first, second)), outcomes
            assert sorted(json.loads(out[0])["status"] for out in outcomes) == [
                "installed", "reused",
            ]
            observer.execute("INSERT INTO app.users VALUES ('later','later@example.test','hash')")
            receipt = observer.execute("SELECT * FROM app.deployment_baseline").fetchall()
            retry = run_cli("restore", release, "--dsn-env", "BASELINE_TARGET_TEST_URL")
            assert retry.returncode == 0, retry.stderr
            assert json.loads(retry.stdout)["status"] == "reused"
            assert observer.execute("SELECT count(*) FROM app.users").fetchone() == (2,)
            assert observer.execute("SELECT * FROM app.deployment_baseline").fetchall() == receipt
        finally:
            observer.execute("SELECT pg_advisory_unlock_all()")
            for process in (first, second):
                if process and process.poll() is None:
                    process.kill()
                    process.communicate()


def test_registration_interruption_recovers_committed_restore(databases, tmp_path):
    with psycopg.connect(databases.source, autocommit=True) as conn:
        conn.execute("""CREATE FUNCTION app.registration_gate() RETURNS event_trigger AS $$
            BEGIN
                IF current_query() LIKE '%CREATE TABLE app.deployment_baseline%' THEN
                    PERFORM pg_advisory_xact_lock(252006);
                END IF;
            END $$ LANGUAGE plpgsql;
            CREATE EVENT TRIGGER registration_gate ON ddl_command_start
                WHEN TAG IN ('CREATE TABLE') EXECUTE FUNCTION app.registration_gate()""")
    release = tmp_path / "baseline"
    assert export_to(release, tmp_path).returncode == 0
    with psycopg.connect(databases.target, autocommit=True) as observer:
        observer.execute("SELECT pg_advisory_lock(252006)")
        process = start_restore(release)
        try:
            backend = wait_for_gate(observer, process, application="")
            assert observer.execute("SELECT count(*) FROM app.users").fetchone() == (1,)
            assert observer.execute(
                "SELECT to_regclass('app.deployment_baseline')"
            ).fetchone()[0] is None
            observer.execute("SELECT pg_terminate_backend(%s)", (backend,))
            process.communicate(timeout=15)
            assert process.returncode == 2
        finally:
            observer.execute("SELECT pg_advisory_unlock(252006)")
            if process.poll() is None:
                process.kill()
                process.communicate()
    retry = run_cli("restore", release, "--dsn-env", "BASELINE_TARGET_TEST_URL")
    assert retry.returncode == 0, retry.stderr
    assert json.loads(retry.stdout)["status"] == "recovered"
