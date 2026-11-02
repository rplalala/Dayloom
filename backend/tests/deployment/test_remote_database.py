"""Remote database startup is read-only and remains configurable until ready."""

import hashlib
from pathlib import Path
from unittest.mock import patch

import pytest
from dotenv import dotenv_values

from backend.app.product import database
from backend.tests.deployment.test_launch_cli import launch


def test_remote_bootstrap_has_no_baseline_or_fabricated_database_credentials(tmp_path):
    result = launch(
        "prepare-remote",
        "--directory",
        str(tmp_path),
        "--origin",
        "http://localhost:5199",
        "--app-image",
        "dayloom-app:controlled",
        "--uid",
        "1000",
        "--gid",
        "1000",
        "--project",
        "dayloom-light-test",
    )
    assert result.returncode == 0, result.stderr
    values = dotenv_values(tmp_path / ".env")
    assert values["DAYLOOM_DEPLOYMENT_MODE"] == "remote"
    assert values["DAYLOOM_DB_PASSWORD"] == ""
    assert values["DAYLOOM_DB_HOST"] == "unconfigured.invalid"
    assert "DAYLOOM_BASELINE_IMAGE" not in values
    assert "DAYLOOM_BASELINE_ID" not in values
    assert len(values["PRODUCT_JWT_SECRET"]) >= 32
    assert (
        launch(
            "prepare",
            "--directory",
            str(tmp_path),
            "--origin",
            "http://localhost:5199",
            "--app-image",
            "dayloom-app:controlled",
            "--baseline-image",
            "baseline:controlled",
            "--baseline-id",
            "b" * 64,
            "--uid",
            "1000",
            "--gid",
            "1000",
            "--project",
            "test",
        ).returncode
        == 2
    )


@pytest.mark.parametrize("change", [None, "crlf", "missing", "newer", "checksum"])
def test_remote_migration_audit_rejects_incompatible_history_without_writes(
    tmp_path,
    monkeypatch,
    change,
):
    import psycopg

    migration = tmp_path / "001_example.sql"
    migration.write_bytes(b"CREATE TABLE example(id int);\n")
    rows = [(migration.name, hashlib.sha256(migration.read_bytes()).hexdigest())]
    if change == "crlf":
        rows[0] = (
            migration.name,
            hashlib.sha256(migration.read_bytes().replace(b"\n", b"\r\n")).hexdigest(),
        )
    if change == "missing":
        rows = []
    elif change == "newer":
        rows.append(("999_future.sql", "a" * 64))
    elif change == "checksum":
        rows[0] = (migration.name, "a" * 64)
    queries = []

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def execute(self, sql):
            queries.append(sql)
            assert sql.startswith("SELECT ")
            return self

        def fetchall(self):
            return rows

    def connect(**parameters):
        assert parameters["sslmode"] == "verify-full"
        assert "default_transaction_read_only=on" in parameters["options"]
        assert parameters["connect_timeout"] <= 5
        return Connection()

    monkeypatch.setattr(psycopg, "connect", connect)
    parameters = {"host": "db.invalid", "sslmode": "verify-full"}
    if change and change != "crlf":
        with pytest.raises(ValueError, match="migration"):
            database.check_migrations(parameters, directory=tmp_path)
    else:
        database.check_migrations(parameters, directory=tmp_path)
    assert queries == ["SELECT name, sha256 FROM app.schema_migrations"]


def test_remote_entrypoint_does_not_wait_for_or_restore_a_baseline(monkeypatch):
    from deploy.docker import app_entrypoint, startup
    from scripts import run_product

    captured = []
    monkeypatch.setattr(run_product, "main", lambda arguments: captured.extend(arguments))
    monkeypatch.setattr(startup, "prepare_database", lambda *_: pytest.fail("Baseline invoked"))
    with patch.dict("os.environ", {}, clear=True):
        assert app_entrypoint.main(["serve", "--remote-database"]) == 0
    assert "--remote-database" in captured
    assert "--container-local" in captured


def test_light_compose_contains_only_the_app_service():
    # Remote mode ships its own standalone Compose service, never local DB/init services.
    import yaml

    root = Path(__file__).resolve().parents[3]
    services = yaml.safe_load((root / "deploy/compose.light.yaml").read_text())["services"]
    assert set(services) == {"app"}
    assert services["app"]["command"] == ["serve", "--remote-database"]
    assert "depends_on" not in services["app"]
    assert "DAYLOOM_BASELINE_ID" not in services["app"]["environment"]
