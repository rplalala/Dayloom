"""The public Compose launcher uses the same resolved settings as application clients."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.skipif(shutil.which("docker") is None, reason="Docker CLI is required")
@pytest.mark.parametrize("override", [False, True])
def test_compose_launcher_resolves_shared_configuration_without_starting_services(override):
    env = {key: value for key, value in os.environ.items() if not key.startswith("DAYLOOM_DB_")}
    env.update(
        PYTHON_DOTENV_DISABLED="1",
        DAYLOOM_DB_PASSWORD="synthetic-compose-password", DAYLOOM_DB_VOLUME="launcher_test_volume",
    )
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
