"""The opt-in acceptance entry rejects unsafe storage before invoking Docker."""

import subprocess
import sys

import pytest

from backend.tests.deployment.test_release_package import ROOT


@pytest.mark.parametrize(
    "project,database",
    [
        ("dayloom-acceptance-test", "dayloom"),
        ("dayloom", "dayloom_acceptance_test"),
    ],
)
def test_full_archive_acceptance_refuses_non_test_storage(tmp_path, project, database):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "backend.tests.deployment.archive_acceptance",
            "cold",
            "--work",
            str(tmp_path),
            "--archive",
            str(tmp_path / "missing.tar.gz"),
            "--manifest",
            str(tmp_path / "manifest.json"),
            "--source-evidence",
            str(tmp_path / "source.json"),
            "--topk-sql",
            str(tmp_path / "topk.sql"),
            "--project",
            project,
            "--database",
            database,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 2
    assert "test database and project" in result.stderr
    assert not list(tmp_path.iterdir())
