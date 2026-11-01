"""The packaged application prepares durable deployment settings without host tooling."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[3]


def launch(*args, instance=None):
    allowed = {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "USERPROFILE", "APPDATA",
               "LOCALAPPDATA", "COMSPEC", "PATHEXT", "HOME"}
    environment = {k: v for k, v in os.environ.items() if k.upper() in allowed}
    environment["PYTHONPATH"] = str(ROOT)
    if instance:
        environment["DAYLOOM_CONFIG_DIR"] = str(instance)
    return subprocess.run(
        [sys.executable, "-m", "deploy.docker.app_entrypoint", *args], cwd=ROOT,
        env=environment, capture_output=True, text=True, encoding="utf-8", timeout=20,
    )


def test_packaged_prepare_reuses_secrets_and_preserves_editable_provider_settings(tmp_path):
    directory = tmp_path / "instance"
    args = ["prepare", "--directory", str(directory), "--origin", "http://localhost:5199",
            "--app-image", "dayloom-app:controlled", "--baseline-image", "baseline:controlled",
            "--baseline-id", "b" * 64, "--uid", "1000", "--gid", "1000",
            "--project", "dayloom-controlled-test", "--database-name", "dayloom_t4_test"]
    first = launch(*args)
    assert first.returncode == 0, first.stderr
    assert "management_password" in json.loads(first.stdout)
    old = dotenv_values(directory / ".env")
    with (directory / ".env").open("a", encoding="utf-8") as stream:
        stream.write("OPENAI_API_KEY='controlled-saved-value'\n")
    repeated = launch(*args)
    assert repeated.returncode == 0, repeated.stderr
    assert "management_password" not in json.loads(repeated.stdout)
    current = dotenv_values(directory / ".env")
    assert current["DAYLOOM_DB_PASSWORD"] == old["DAYLOOM_DB_PASSWORD"]
    assert current["PRODUCT_JWT_SECRET"] == old["PRODUCT_JWT_SECRET"]
    assert current["OPENAI_API_KEY"] == "controlled-saved-value"
    assert current["DAYLOOM_BASELINE_ID"] == "b" * 64
    assert current["DAYLOOM_DB_NAME"] == "dayloom_t4_test"
    assert current["DAYLOOM_HOST_PORT"] == "5199"
    assert "controlled-saved-value" not in repeated.stdout
    deployment = directory / "product.yaml"
    with deployment.open("a", encoding="utf-8") as stream:
        stream.write("# Keep this deployment note.\n")
    changed_port = args.copy()
    changed_port[changed_port.index("http://localhost:5199")] = "http://localhost:5201"
    moved = launch(*changed_port)
    assert moved.returncode == 0, moved.stderr
    assert 'origin: "http://localhost:5201"' in deployment.read_text(encoding="utf-8")
    assert "# Keep this deployment note." in deployment.read_text(encoding="utf-8")


def test_serve_rejects_unreleased_installation_identity_before_starting_application():
    result = launch("serve", "--require-installation", "--baseline-id", "unreleased",
                    "--startup-timeout", "1")
    assert result.returncode == 2
    assert "released baseline identity" in result.stderr
    assert "Dayloom:" not in result.stdout


@pytest.mark.skipif(os.environ.get("DAYLOOM_T4_DATABASE_TESTS") != "1",
                    reason="Requires the isolated controlled T4 database")
def test_public_installation_check_migrates_once_and_rejects_mismatched_receipt(tmp_path):
    import psycopg

    from backend.app.product.configuration import LocalConfiguration
    from deploy.docker.instance import bootstrap_instance

    # Controlled-only disposable service; never fall back to runtime connection settings.
    dsn = ("host=127.0.0.1 port=55694 dbname=dayloom_t4_test "
           "user=controlled password=controlled-test-only")
    with psycopg.connect(dsn, autocommit=True) as connection:
        connection.execute("DROP SCHEMA IF EXISTS app CASCADE")
        connection.execute("CREATE SCHEMA app")
        connection.execute("CREATE TABLE app.deployment_baseline (singleton boolean, "
                           "format_version integer, baseline_id text)")
        connection.execute("INSERT INTO app.deployment_baseline VALUES (true,1,%s)", ("b" * 64,))
    directory = tmp_path / "guard"
    bootstrap_instance(directory, "http://localhost:5199")
    manager = LocalConfiguration(directory, origin="http://localhost:5199", environment={})
    manager.save(manager.view()["revision"], {"DAYLOOM_DB_URL": dsn})
    first = launch("check-installation", "--baseline-id", "b" * 64,
                   "--startup-timeout", "2", instance=directory)
    assert first.returncode == 0, first.stderr
    assert json.loads(first.stdout) == {"installed": True}
    again = launch("check-installation", "--baseline-id", "b" * 64,
                   "--startup-timeout", "2", instance=directory)
    assert again.returncode == 0, again.stderr
    wrong = launch("check-installation", "--baseline-id", "c" * 64,
                   "--startup-timeout", "2", instance=directory)
    assert wrong.returncode == 2
    assert "controlled-test-only" not in wrong.stdout + wrong.stderr
    with psycopg.connect(dsn, autocommit=True) as connection:
        assert connection.execute("SELECT count(*) FROM app.schema_migrations").fetchone()[0] == 10
