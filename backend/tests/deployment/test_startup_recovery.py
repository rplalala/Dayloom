"""Every-start installation checks use an isolated database through the public CLI."""

import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from backend.tests.deployment.test_launch_cli import ROOT, launch


@dataclass(repr=False)
class StartupDatabase:
    dsn: str

    def __repr__(self):
        return "<isolated startup test database>"


@pytest.fixture
def startup_database():
    supplied = os.environ.get("DAYLOOM_STARTUP_TEST_URL")
    if not supplied:
        pytest.skip("Explicit isolated startup test database is required")
    parameters = conninfo_to_dict(supplied)
    if "test" not in parameters.get("dbname", "").lower():
        pytest.fail("Startup acceptance requires an isolated test database name")
    name = "startup_test_" + uuid4().hex
    with psycopg.connect(**{**parameters, "dbname": "postgres"}, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
        try:
            yield StartupDatabase(make_conninfo(**{**parameters, "dbname": name}))
        finally:
            admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))


def instance_at(tmp_path, database):
    directory = tmp_path / "instance"
    result = launch("bootstrap", "--directory", str(directory))
    assert result.returncode == 0, result.stderr
    with (directory / ".env").open("a", encoding="utf-8") as stream:
        stream.write("\nDAYLOOM_DB_URL=" + json.dumps(database.dsn) + "\n")
    return directory


def installed_receipt(database):
    with psycopg.connect(database.dsn, autocommit=True) as connection:
        connection.execute("CREATE SCHEMA app")
        connection.execute("CREATE TABLE app.deployment_baseline (singleton boolean, "
                           "format_version integer, baseline_id text)")
        connection.execute("INSERT INTO app.deployment_baseline VALUES (true,1,%s)", ("b" * 64,))


def check(directory, timeout="2"):
    return launch("check-installation", "--baseline-id", "b" * 64,
                  "--startup-timeout", timeout, instance=directory)


def test_startup_refuses_unknown_migrations_and_preserves_installed_rows(
    startup_database, tmp_path,
):
    directory = instance_at(tmp_path, startup_database)
    installed_receipt(startup_database)
    assert check(directory).returncode == 0
    with psycopg.connect(startup_database.dsn, autocommit=True) as connection:
        connection.execute("INSERT INTO app.schema_migrations(name,sha256) "
                           "VALUES ('9999_future.sql','future-checksum')")
    result = check(directory)
    assert result.returncode == 2
    assert "newer application" in result.stderr.lower()
    with psycopg.connect(startup_database.dsn) as connection:
        assert connection.execute("SELECT sha256 FROM app.schema_migrations "
                                  "WHERE name='9999_future.sql'").fetchone() == ("future-checksum",)


def test_startup_waits_for_installation_then_migrates_without_factory_restore(
    startup_database, tmp_path,
):
    directory = instance_at(tmp_path, startup_database)
    environment = {**os.environ, "PYTHONPATH": str(ROOT), "DAYLOOM_CONFIG_DIR": str(directory)}
    # Ambient runtime/provider settings must never choose this controlled process's database.
    excluded = ("DAYLOOM_DB_", "PRODUCT_", "OPENAI_", "GOOGLE_", "AZURE_")
    environment = {key: value for key, value in environment.items()
                   if not key.startswith(excluded)}
    process = subprocess.Popen(
        [sys.executable, "-m", "deploy.docker.app_entrypoint", "check-installation",
         "--baseline-id", "b" * 64, "--startup-timeout", "8"],
        cwd=ROOT, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    try:
        time.sleep(1)
        assert process.poll() is None
        installed_receipt(startup_database)
        stdout, stderr = process.communicate(timeout=12)
        assert process.returncode == 0, stderr
        assert json.loads(stdout) == {"installed": True}
        with psycopg.connect(startup_database.dsn) as connection:
            count = connection.execute("SELECT count(*) FROM app.schema_migrations").fetchone()
            assert count == (10,)
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate()


def test_missing_installation_never_creates_application_schema(startup_database, tmp_path):
    directory = instance_at(tmp_path, startup_database)
    result = check(directory, "0.2")
    assert result.returncode == 2
    assert "did not become ready" in result.stderr.lower()
    with psycopg.connect(startup_database.dsn) as connection:
        assert connection.execute("SELECT to_regnamespace('app')").fetchone()[0] is None


def test_migration_checksum_failure_is_nonready_and_does_not_rewrite_history(
    startup_database, tmp_path,
):
    directory = instance_at(tmp_path, startup_database)
    installed_receipt(startup_database)
    assert check(directory).returncode == 0
    with psycopg.connect(startup_database.dsn, autocommit=True) as connection:
        connection.execute("UPDATE app.schema_migrations SET sha256='incompatible' "
                           "WHERE name='001_accounts.sql'")
    result = check(directory)
    assert result.returncode == 2
    assert "migration checksum" in result.stderr.lower()
    assert "controlled-test-only" not in result.stdout + result.stderr
