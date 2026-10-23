"""Browser acceptance must isolate child processes and redact failure diagnostics."""

import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import SecretStr

ROOT = Path(__file__).resolve().parents[3]


def test_browser_children_receive_only_allowlisted_environment(monkeypatch, tmp_path):
    from backend.tests.product.browser_harness import isolated_environment

    for key in [
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "OPENAI_API_KEY",
        "GITHUB_TOKEN",
        "PRODUCT_JWT_SECRET",
        "DAYLOOM_DB_URL",
    ]:
        monkeypatch.setenv(key, "synthetic-host-secret-never-inherit")
    environment = isolated_environment(
        SecretStr("postgresql://local/isolated_test"), "8120", "5120", tmp_path
    )
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            """import os
assert not any(key in os.environ for key in
    ('AWS_ACCESS_KEY_ID','AWS_SECRET_ACCESS_KEY','OPENAI_API_KEY','GITHUB_TOKEN'))
assert 'synthetic-host-secret-never-inherit' not in os.environ.values()
""",
        ],
        env=environment,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, "Browser child environment isolation failed"


def test_fixture_failure_diagnostics_hide_environment_and_connection(tmp_path):
    from backend.tests.product.browser_harness import isolated_environment

    probe = tmp_path / "test_diagnostic_probe.py"
    probe.write_text(
        """import pytest
from unittest.mock import patch
from backend.tests.product.test_browser import browser_app

@pytest.fixture(scope="session",autouse=True)
def fail_before_migration():
    with patch(
        "subprocess.run",
        side_effect=RuntimeError("Intentional sanitized fixture diagnostic"),
    ):
        yield

def test_intentional_failure(browser_app):
    pass
""",
        encoding="utf-8",
    )
    environment = isolated_environment(
        SecretStr("postgresql://local/isolated_test"), "8120", "5120", tmp_path
    )
    environment["DAYLOOM_DB_TEST_URL"] = (
        "postgresql://user:synthetic-connection-secret@127.0.0.1/isolated_test"
    )
    environment["AWS_ACCESS_KEY_ID"] = "synthetic-access-key-never-report"
    environment["AWS_SECRET_ACCESS_KEY"] = "synthetic-secret-key-never-report"
    environment["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    environment["PRODUCT_BROWSER_TESTS"] = "1"
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(probe), "--showlocals", "--tb=long", "-q"],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1, "The diagnostic probe must exercise fixture failure"
    diagnostic = result.stdout + result.stderr
    assert "Intentional sanitized fixture diagnostic" in diagnostic
    assert all(
        marker not in diagnostic
        for marker in [
            "synthetic-connection-secret",
            "synthetic-access-key-never-report",
            "synthetic-secret-key-never-report",
        ]
    ), "Fixture diagnostic exposed sensitive environment data"


@pytest.mark.parametrize(
    "target",
    [
        "test_registration_profile_failure_rolls_back_account",
        "test_public_migration_rerun_checksum_and_tripworld_preservation",
    ],
)
def test_account_failure_frames_hide_connection_strings(tmp_path, target):
    from backend.tests.product.browser_harness import isolated_environment

    probe = tmp_path / "test_account_diagnostic_probe.py"
    probe.write_text(
        """from operator import attrgetter
import psycopg
from backend.tests.product import test_accounts as accounts

def test_account_connection_failure(tmp_path,monkeypatch):
    monkeypatch.setattr(psycopg,"connect",attrgetter("acceptance_connection_unavailable"))
    if "migration" in TARGET:
        getattr(accounts,TARGET)(None,tmp_path)
    else:
        getattr(accounts,TARGET)(None)
""".replace("TARGET", repr(target)),
        encoding="utf-8",
    )
    environment = isolated_environment(
        SecretStr("postgresql://user:synthetic-account-connection-secret@127.0.0.1/isolated_test"),
        "8120",
        "5120",
        tmp_path,
    )
    environment["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(probe), "--showlocals", "--tb=long", "-q"],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1, "The account diagnostic probe must exercise actual test failure"
    diagnostic = result.stdout + result.stderr
    assert "acceptance_connection_unavailable" in diagnostic
    assert "synthetic-account-connection-secret" not in diagnostic, (
        "Account failure frame exposed its database credential"
    )
