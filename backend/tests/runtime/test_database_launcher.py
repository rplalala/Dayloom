"""The public Compose launcher uses the same resolved settings as application clients."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def compose_environment():
    allowed = {
        "PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "USERPROFILE", "APPDATA",
        "LOCALAPPDATA", "PROGRAMDATA", "COMSPEC", "PATHEXT", "HOMEDRIVE", "HOMEPATH",
        "PROGRAMFILES", "PROGRAMFILES(X86)", "PROGRAMW6432",
    }
    env = {key: value for key, value in os.environ.items() if key.upper() in allowed}
    env.update(
        PYTHON_DOTENV_DISABLED="1",
        DAYLOOM_DB_PASSWORD="synthetic-compose-password", DAYLOOM_DB_VOLUME="launcher_test_volume",
    )
    return env


@pytest.mark.skipif(shutil.which("docker") is None, reason="Docker CLI is required")
@pytest.mark.parametrize("override", [False, True])
def test_compose_launcher_resolves_shared_configuration_without_starting_services(
    override, compose_environment,
):
    env = compose_environment
    if override:
        env.update(DAYLOOM_DB_HOST="127.0.0.1", DAYLOOM_DB_PORT="55621",
                   DAYLOOM_DB_NAME="launcher_test", DAYLOOM_DB_USER="launcher_user")
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_database.py"), "config", "--format", "json"],
        cwd=ROOT / ".scratch", env=env, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, "Public database launcher configuration failed"
    config = json.loads(result.stdout)
    service = config["services"]["postgres"]
    assert service["environment"]["POSTGRES_DB"] == ("launcher_test" if override else "dayloom")
    assert service["environment"]["POSTGRES_USER"] == ("launcher_user" if override else "dayloom")
    assert service["environment"]["POSTGRES_PASSWORD"] == "synthetic-compose-password"
    assert service["ports"][0]["published"] == ("55621" if override else "55432")
    assert config["volumes"]["dayloom_pgdata"]["name"] == "launcher_test_volume"


def test_compose_launcher_rejects_ipv6_host_for_its_ipv4_published_port(compose_environment):
    compose_environment["DAYLOOM_DB_HOST"] = "::1"
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_database.py"), "config", "--quiet"],
        cwd=ROOT / ".scratch", env=compose_environment, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 1
    assert "IPv4" in result.stderr


def test_launcher_fixture_failure_diagnostics_exclude_host_credentials(
    compose_environment, tmp_path,
):
    probe = tmp_path / "test_diagnostic_probe.py"
    probe.write_text(
        "from backend.tests.runtime.test_database_launcher import compose_environment\n"
        "def test_failure(compose_environment):\n    assert False\n", encoding="utf-8",
    )
    sentinel = "synthetic-host-credential-for-diagnostic-check"
    environment = {
        **compose_environment, "AWS_SECRET_ACCESS_KEY": sentinel, "PYTHONPATH": str(ROOT),
    }
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(probe), "-q", "-p", "no:cacheprovider"],
        cwd=ROOT, env=environment, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 1
    assert sentinel not in result.stdout + result.stderr
