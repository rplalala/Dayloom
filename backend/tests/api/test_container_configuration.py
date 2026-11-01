"""Container-local configuration retains the existing authenticated HTTP boundary."""

import json
import os
import subprocess
import sys
from unittest.mock import patch

from dotenv import dotenv_values
from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.product.configuration import DEFAULT_TEST_PASSWORD, LocalConfiguration
from backend.app.product.configuration_api import enable_local_configuration
from backend.tests.api.test_product_setup_launcher import local_launcher  # noqa: F401


def test_explicit_forwarder_can_configure_without_trusting_other_private_peers(tmp_path):
    manager = LocalConfiguration(
        tmp_path, origin="http://localhost:5198", environment={},
        management_peers=("172.22.0.1",), default_password_hint=False,
    )
    app = create_app()
    enable_local_configuration(app, manager, ready=False)
    with TestClient(app, base_url=manager.origin, client=("172.22.0.1", 50000)) as client:
        access = client.get("/api/config/access")
        assert access.status_code == 200
        assert "default_test_password" not in access.json()
        client.headers["Origin"] = manager.origin
        session = client.post("/api/config/session", json={"password": DEFAULT_TEST_PASSWORD})
        assert session.status_code == 200
        assert client.get("/api/config").status_code == 401
        client.headers["X-CSRF-Token"] = session.json()["csrf_token"]
        view = client.get("/api/config").json()
        assert view["fields"]["OPENAI_API_KEY"]["locked"] is False
        saved = client.put("/api/config", json={
            "revision": view["revision"], "changes": {"OPENAI_API_KEY": "controlled-new-key"},
        })
        assert saved.status_code == 200
        assert client.get("/api/auth/me").status_code == 503
        client.headers["Origin"] = "http://other.local"
        assert client.post("/api/config/session", json={}).status_code == 403
        client.headers["Origin"] = manager.origin
        client.headers["Host"] = "other.local"
        assert client.get("/api/config/access").status_code == 403
    with TestClient(app, base_url=manager.origin, client=("172.22.0.2", 50000)) as client:
        client.headers["X-Forwarded-For"] = "127.0.0.1"
        assert client.get("/api/config/access").status_code == 403
    assert LocalConfiguration(tmp_path, origin=manager.origin, environment={}).initial[
        "OPENAI_API_KEY"
    ] == "controlled-new-key"


def test_container_launcher_serves_setup_at_a_different_internal_port(
    local_launcher, monkeypatch, capsys,  # noqa: F811
):
    import uvicorn

    from deploy.docker.instance import bootstrap_instance
    from scripts import run_product

    first_use = bootstrap_instance(local_launcher, "http://localhost:5173")

    class Server:
        def __init__(self, config):
            self.config = config

        async def serve(self):
            assert self.config.host == "0.0.0.0"
            assert self.config.port == 8000
            assert self.config.proxy_headers is False
            with TestClient(self.config.app, base_url="http://localhost:5173",
                            client=("172.22.0.1", 50000)) as client:
                assert client.get("/config").status_code == 200
                assert "default_test_password" not in client.get("/api/config/access").json()
                assert client.get("/api/auth/me").status_code == 503

    monkeypatch.setattr(uvicorn, "Server", Server)
    with patch.dict(os.environ, {}, clear=True):
        run_product.main([
            "--container-local", "--host", "0.0.0.0", "--port", "8000",
            "--management-peer", "172.22.0.1",
        ])
    output = capsys.readouterr().out
    assert first_use["management_password"] not in output
    assert "http://localhost:5173/config" in output


def test_bootstrap_creates_private_configuration_once_and_authenticates_through_api(tmp_path):
    directory = tmp_path / "instance"
    command = [
        sys.executable, "-m", "deploy.docker.app_entrypoint", "bootstrap",
        "--directory", str(directory), "--origin", "http://localhost:5198",
        "--database-name", "container_test",
    ]
    first = subprocess.run(command, capture_output=True, text=True, check=False)
    assert first.returncode == 0, first.stderr
    result = json.loads(first.stdout)
    password = result["management_password"]
    assert len(password) >= 32
    values = dotenv_values(directory / ".env")
    assert len(values["DAYLOOM_DB_PASSWORD"]) >= 32
    assert len(values["PRODUCT_JWT_SECRET"]) >= 32
    assert values["DAYLOOM_DB_PASSWORD"] != values["PRODUCT_JWT_SECRET"]
    assert not values.get("OPENAI_API_KEY")
    state = (directory / ".config-access.json").read_text("utf-8")
    assert password not in state
    before = {path.name: path.read_bytes() for path in directory.iterdir() if path.is_file()}
    again = subprocess.run(command, capture_output=True, text=True, check=False)
    assert again.returncode == 0, again.stderr
    assert "management_password" not in json.loads(again.stdout)
    after = {path.name: path.read_bytes() for path in directory.iterdir() if path.is_file()}
    assert after == before
    manager = LocalConfiguration(
        directory, origin="http://localhost:5198", environment={},
        management_peers=("172.22.0.1",), default_password_hint=False,
    )
    app = create_app()
    enable_local_configuration(app, manager, ready=False)
    with TestClient(app, base_url=manager.origin, client=("172.22.0.1", 50000),
                    headers={"Origin": manager.origin}) as client:
        denied = client.post("/api/config/session", json={"password": DEFAULT_TEST_PASSWORD})
        assert denied.status_code == 401
        session = client.post("/api/config/session", json={"password": password})
        assert session.status_code == 200
        client.headers["X-CSRF-Token"] = session.json()["csrf_token"]
        view = client.get("/api/config").json()
        assert view["fields"]["OPENAI_API_KEY"]["locked"] is False


def test_explicit_host_reset_rotates_only_management_access(tmp_path):
    from deploy.docker.instance import bootstrap_instance

    first = bootstrap_instance(tmp_path, "http://localhost:5173")
    saved_environment = (tmp_path / ".env").read_bytes()
    command = [sys.executable, "-m", "deploy.docker.app_entrypoint",
               "reset-management-password", "--directory", str(tmp_path)]
    reset = subprocess.run(command, capture_output=True, text=True, check=False)
    assert reset.returncode == 0, reset.stderr
    replacement = json.loads(reset.stdout)["management_password"]
    assert replacement != first["management_password"]
    assert (tmp_path / ".env").read_bytes() == saved_environment
    assert replacement not in (tmp_path / ".config-access.json").read_text("utf-8")
    manager = LocalConfiguration(tmp_path, origin="http://localhost:5173", environment={})
    app = create_app()
    enable_local_configuration(app, manager, ready=False)
    with TestClient(app, base_url=manager.origin, client=("127.0.0.1", 50000),
                    headers={"Origin": manager.origin}) as client:
        denied = client.post("/api/config/session", json={"password": first["management_password"]})
        assert denied.status_code == 401
        assert client.post("/api/config/session", json={"password": replacement}).status_code == 200
