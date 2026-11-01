"""Operational archives are checked through the shipped maintenance CLI."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def maintenance(*args):
    return subprocess.run(
        [sys.executable, "-m", "deploy.release.maintenance", *map(str, args)],
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": str(ROOT)},
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_invalid_backup_is_rejected_without_revealing_private_contents(tmp_path):
    (tmp_path / "database.pgcustom").write_text("private-fixture-data")
    result = maintenance("verify", tmp_path)
    assert result.returncode == 2
    assert "Invalid operational backup" in result.stderr
    assert "private-fixture-data" not in result.stdout + result.stderr
    assert "Traceback" not in result.stderr


def private_archive(root):
    (root / "config").mkdir(parents=True)
    files = {
        "config/.env": "PRODUCT_JWT_SECRET=controlled-private-identity\n",
        "config/product.yaml": "origin: http://localhost:5173\n",
        "config/.config-access.json": '{"retained":"preferences"}',
        "database.pgcustom": "controlled dump",
        "backup.json": json.dumps(
            {
                "format": "dayloom-private-backup-v1",
                "receipt": {"format_version": 1, "baseline_id": "a" * 64},
            }
        ),
    }
    for name, content in files.items():
        (root / name).write_text(content, encoding="utf-8")
    (root / "SHA256SUMS.txt").write_text(
        "".join(
            hashlib.sha256((root / name).read_bytes()).hexdigest() + "  " + name + "\n"
            for name in sorted(files)
        ),
        encoding="utf-8",
    )


def test_verified_private_configuration_is_restored_only_into_an_empty_destination(tmp_path):
    archive = tmp_path / "private.dayloom-backup"
    private_archive(archive)
    assert maintenance("verify", archive).returncode == 0
    destination = tmp_path / "recovered"
    restored = maintenance("restore-config", archive, "--config", destination)
    assert restored.returncode == 0, restored.stderr
    assert (destination / ".env").read_text() == "PRODUCT_JWT_SECRET=controlled-private-identity\n"
    (destination / ".env").write_text("Keep existing instance")
    rejected = maintenance("restore-config", archive, "--config", destination)
    assert rejected.returncode == 2
    assert (destination / ".env").read_text() == "Keep existing instance"
    (archive / "config/.env").write_text("tampered-private-key")
    corrupt = maintenance("verify", archive)
    assert corrupt.returncode == 2
    assert "tampered-private-key" not in corrupt.stdout + corrupt.stderr


def test_maintenance_rejects_an_external_database_without_connecting_or_exposing_its_url(tmp_path):
    from backend.tests.deployment.test_launch_cli import launch

    prepared = launch(
        "prepare",
        "--directory",
        str(tmp_path),
        "--origin",
        "http://localhost:5183",
        "--app-image",
        "app:controlled",
        "--baseline-image",
        "baseline:controlled",
        "--baseline-id",
        "a" * 64,
        "--uid",
        "1000",
        "--gid",
        "1000",
        "--project",
        "dayloom-controlled-test",
    )
    assert prepared.returncode == 0
    environment = {
        key: value
        for key, value in os.environ.items()
        if key.upper() in {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP"}
    }
    environment.update(PYTHONPATH=str(ROOT), DAYLOOM_CONFIG_DIR=str(tmp_path))

    def check():
        return subprocess.run(
            [sys.executable, "-m", "deploy.docker.upgrade", "--check-local-target"],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=15,
        )

    assert check().returncode == 0
    with (tmp_path / ".env").open("a", encoding="utf-8") as stream:
        stream.write(
            "DAYLOOM_DB_URL='host=127.0.0.1 port=9 dbname=controlled_test "
            "user=controlled password=controlled-private'\n"
        )
    rejected = check()
    assert rejected.returncode == 2
    assert "split connection fields" in rejected.stderr
    assert "controlled-private" not in rejected.stdout + rejected.stderr
