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
from backend.tests.deployment.test_maintenance_cli import maintenance


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
        conn.execute("CREATE TYPE public.later_enum AS ENUM ('user-owned')")
    reused = run_cli("restore", release, "--dsn-env", "BASELINE_TARGET_TEST_URL")
    assert reused.returncode == 0, reused.stderr
    assert json.loads(reused.stdout)["status"] == "reused"
    with psycopg.connect(target) as conn:
        assert conn.execute("SELECT count(*) FROM app.users").fetchone()[0] == 2


def test_export_rejects_unrepresented_source_objects_without_writing_an_artifact(
    databases, tmp_path,
):
    with psycopg.connect(databases.source, autocommit=True) as conn:
        conn.execute("CREATE TYPE public.unrelated AS ENUM ('x')")
    release = tmp_path / "baseline"
    rejected = export_to(release, tmp_path)
    assert rejected.returncode == 2
    assert "custom type" in rejected.stderr
    assert not release.exists()
    with psycopg.connect(databases.source) as conn:
        assert conn.execute("SELECT 'x'::public.unrelated::text").fetchone() == ("x",)
        assert conn.execute("SELECT count(*) FROM app.users").fetchone() == (1,)


def test_private_backup_round_trip_retains_later_data_and_refuses_unknown_target(
    databases, tmp_path,
):
    release = tmp_path / "baseline"
    exported = export_to(release, tmp_path)
    assert exported.returncode == 0, exported.stderr
    baseline_id = json.loads(exported.stdout)["baseline_id"]
    assert run_cli("restore", release, "--dsn-env", "BASELINE_TARGET_TEST_URL").returncode == 0
    with psycopg.connect(databases.target, autocommit=True) as conn:
        conn.execute("INSERT INTO app.users VALUES ('later','later@example.test','later-hash')")
    config = tmp_path / "config"
    config.mkdir()
    for name in (".env", "product.yaml", ".config-access.json"):
        (config / name).write_text("controlled-test-configuration", encoding="utf-8")
    archive = tmp_path / "private-backup"
    backed_up = maintenance(
        "backup", archive, "--config", config, "--expect-id", baseline_id,
        "--dsn-env", "BASELINE_TARGET_TEST_URL",
    )
    assert backed_up.returncode == 0, backed_up.stderr
    # Only this fixture's own disposable source database is cleared for recovery.
    with psycopg.connect(databases.source, autocommit=True) as conn:
        conn.execute("DROP SCHEMA app CASCADE; DROP SCHEMA tripworld CASCADE")
        conn.execute("CREATE TYPE public.keep AS ENUM ('retained')")
    rejected = maintenance("restore", archive, "--dsn-env", "BASELINE_SOURCE_TEST_URL")
    assert rejected.returncode == 2
    assert "empty database" in rejected.stderr
    with psycopg.connect(databases.source, autocommit=True) as conn:
        assert conn.execute("SELECT 'retained'::public.keep::text").fetchone() == ("retained",)
        assert conn.execute("SELECT to_regclass('app.users')").fetchone()[0] is None
        conn.execute("DROP TYPE public.keep")
    restored = maintenance("restore", archive, "--dsn-env", "BASELINE_SOURCE_TEST_URL")
    assert restored.returncode == 0, restored.stderr
    assert json.loads(restored.stdout)["status"] == "restored"
    reused = run_cli("restore", release, "--dsn-env", "BASELINE_SOURCE_TEST_URL")
    assert reused.returncode == 0, reused.stderr
    assert json.loads(reused.stdout)["status"] == "reused"
    with psycopg.connect(databases.source) as conn:
        assert conn.execute("SELECT email FROM app.users ORDER BY id").fetchall() == [
            ("admin@admin.com",), ("later@example.test",),
        ]


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


@pytest.mark.parametrize(("change", "observation", "expected"), [
    ("CREATE TYPE public.unrelated AS ENUM ('x')", "SELECT 'x'::public.unrelated::text", "x"),
    ("CREATE DOMAIN public.unrelated AS text CHECK (VALUE <> '')",
     "SELECT 'x'::public.unrelated", "x"),
    ("CREATE TYPE public.unrelated AS RANGE (subtype=integer)",
     "SELECT '[1,3)'::public.unrelated::text", "[1,3)"),
    ("CREATE TYPE public.unrelated AS (value integer)",
     "SELECT ROW(7)::public.unrelated::text", "(7)"),
    ("CREATE SEQUENCE public.unrelated START 41",
     "SELECT last_value FROM public.unrelated", 41),
    ("CREATE AGGREGATE public.unrelated(integer) "
     "(sfunc=int4pl,stype=integer,initcond='0')",
     "SELECT public.unrelated(x) FROM (VALUES (7)) t(x)", 7),
    ("CREATE EVENT TRIGGER unrelated ON ddl_command_start "
     "EXECUTE FUNCTION app.event_observer()",
     "SELECT count(*) FROM pg_event_trigger WHERE evtname='unrelated'", 1),
    ("CREATE POLICY unrelated ON app.users USING (true)",
     "SELECT count(*) FROM pg_policy WHERE polname='unrelated'", 1),
    ("ALTER TABLE app.users ENABLE ROW LEVEL SECURITY",
     "SELECT relrowsecurity FROM pg_class WHERE oid='app.users'::regclass", True),
    ("ALTER TABLE app.users SET (fillfactor=80)",
     "SELECT reloptions[1] FROM pg_class WHERE oid='app.users'::regclass", "fillfactor=80"),
    ("ALTER TABLE app.users ALTER email TYPE text COLLATE \"C\"",
     "SELECT attcollation='\"C\"'::regcollation FROM pg_attribute "
     "WHERE attrelid='app.users'::regclass AND attname='email'", True),
    ("ALTER TABLE app.users DISABLE TRIGGER keep_enabled",
     "SELECT tgenabled::text FROM pg_trigger WHERE tgname='keep_enabled'", "D"),
    ("CREATE COLLATION public.unrelated FROM \"C\"",
     "SELECT count(*) FROM pg_collation WHERE collname='unrelated'", 1),
    ("CREATE RULE unrelated AS ON DELETE TO app.users DO INSTEAD NOTHING",
     "SELECT count(*) FROM pg_rewrite WHERE rulename='unrelated'", 1),
    ("ALTER VIEW app.user_view SET (security_barrier=true)",
     "SELECT reloptions[1] FROM pg_class WHERE oid='app.user_view'::regclass",
     "security_barrier=true"),
    ("CREATE CAST (integer AS uuid) WITH INOUT",
     "SELECT count(*) FROM pg_cast WHERE castsource='integer'::regtype "
     "AND casttarget='uuid'::regtype", 1),
    ("SELECT lo_create(0)", "SELECT count(*) FROM pg_largeobject_metadata", 1),
], ids=["enum", "domain", "range", "composite", "sequence", "aggregate", "event-trigger",
        "policy", "row-security", "table-settings", "column-collation", "disabled-trigger",
        "collation", "rule", "view-settings", "cast", "large-object"])
def test_registration_gap_rejects_unrepresented_state_without_relabeling(
    databases, tmp_path, change, observation, expected,
):
    with psycopg.connect(databases.source, autocommit=True) as conn:
        conn.execute("""CREATE VIEW app.user_view AS SELECT id FROM app.users;
            CREATE FUNCTION app.event_observer() RETURNS event_trigger
            LANGUAGE plpgsql AS 'BEGIN END';
            CREATE FUNCTION app.row_observer() RETURNS trigger
            LANGUAGE plpgsql AS 'BEGIN RETURN NEW; END';
            CREATE TRIGGER keep_enabled BEFORE INSERT ON app.users
                FOR EACH ROW EXECUTE FUNCTION app.row_observer()""")
    release = tmp_path / "baseline"
    assert export_to(release, tmp_path).returncode == 0
    assert run_cli("restore", release, "--dsn-env", "BASELINE_TARGET_TEST_URL").returncode == 0
    with psycopg.connect(databases.target, autocommit=True) as conn:
        conn.execute("DROP TABLE app.deployment_baseline")
        conn.execute(change)
    rejected = run_cli("restore", release, "--dsn-env", "BASELINE_TARGET_TEST_URL")
    assert rejected.returncode == 2, rejected.stdout + rejected.stderr
    assert "preserved" in rejected.stderr
    with psycopg.connect(databases.target) as conn:
        assert conn.execute("SELECT to_regclass('app.deployment_baseline')").fetchone()[0] is None
        assert conn.execute(observation).fetchone() == (expected,)
        assert conn.execute("SELECT email,password_hash FROM app.users").fetchall() == [
            ("admin@admin.com", "retained-test-hash"),
        ]


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


def test_registration_interruption_recovers_committed_restore(databases, tmp_path, monkeypatch):
    release = tmp_path / "baseline"
    assert export_to(release, tmp_path).returncode == 0
    # Delay the external client exit after its real restore transaction commits.
    # Killing the initializer here leaves the genuine registration gap, without
    # installing an unsupported event trigger in the snapshot under test.
    real_restore = shutil.which("pg_restore")
    wrapper_bin = tmp_path / "bin"
    wrapper_bin.mkdir()
    committed = tmp_path / "restore-committed"
    wrapper = wrapper_bin / "pg_restore"
    wrapper.write_text(
        f"#!{sys.executable}\n"
        "import os, subprocess, sys, time\n"
        "from pathlib import Path\n"
        f"result = subprocess.run([{real_restore!r}, *sys.argv[1:]])\n"
        "if result.returncode: sys.exit(result.returncode)\n"
        "parent = os.getppid()\n"
        f"Path({str(committed)!r}).touch()\n"
        "while os.getppid() == parent: time.sleep(0.05)\n",
        encoding="utf-8",
    )
    wrapper.chmod(0o700)
    monkeypatch.setenv("PATH", str(wrapper_bin) + os.pathsep + os.environ["PATH"])
    process = start_restore(release)
    try:
        deadline = time.monotonic() + 15
        while not committed.exists() and time.monotonic() < deadline:
            assert process.poll() is None, process.communicate()
            time.sleep(0.05)
        assert committed.exists(), "Real pg_restore did not reach the committed transaction gate"
        with psycopg.connect(databases.target) as observer:
            assert observer.execute("SELECT count(*) FROM app.users").fetchone() == (1,)
            assert observer.execute(
                "SELECT to_regclass('app.deployment_baseline')"
            ).fetchone()[0] is None
        process.kill()
        process.communicate(timeout=15)
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate(timeout=15)
    retry = run_cli("restore", release, "--dsn-env", "BASELINE_TARGET_TEST_URL")
    assert retry.returncode == 0, retry.stderr
    assert json.loads(retry.stdout)["status"] == "recovered"
