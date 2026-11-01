"""Incomplete local installs start configuration without changing live provider behavior."""

import os
from unittest.mock import patch

import pytest

from backend.app.runtime.deployment import ProductPolicySettings
from scripts import run_product


@pytest.fixture
def local_launcher(tmp_path, monkeypatch):
    from backend.app.product import application

    (tmp_path / "index.html").write_text("Dayloom setup", encoding="utf-8")
    (tmp_path / "product.yaml").write_text(
        "origin: http://localhost:5173\nallow_insecure_loopback: true\n"
        "foundry:\n  endpoint: https://example.services.ai.azure.com/openai/v1\n"
        "  deployment: gpt-6-luna\n",
        encoding="utf-8",
    )
    # The real launcher changes cwd; register restoration for later tests.
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(run_product, "PROJECT_ROOT", tmp_path)
    monkeypatch.setitem(ProductPolicySettings.model_config, "env_file", tmp_path / ".env")
    monkeypatch.setitem(ProductPolicySettings.model_config, "yaml_file", tmp_path / "product.yaml")
    create_application = application.create_product_application
    monkeypatch.setattr(
        application, "create_product_application", lambda: create_application(tmp_path)
    )
    monkeypatch.setattr(
        run_product,
        "check_runtime",
        lambda: (_ for _ in ()).throw(ValueError("synthetic-private-readiness-error")),
    )
    return tmp_path


def test_launcher_exposes_setup_and_pins_missing_credentials(local_launcher, monkeypatch, capsys):
    import uvicorn

    applications = []

    class Server:
        def __init__(self, config):
            applications.append(config.app)
            assert config.proxy_headers is False

        async def serve(self):
            manager = applications[0].state.local_configuration
            assert manager.running_ready is False
            assert os.environ["OPENAI_API_KEY"] == ""
            view = manager.view()
            manager.save(view["revision"], {"OPENAI_API_KEY": "saved-private-key"})
            assert os.environ["OPENAI_API_KEY"] == ""

    monkeypatch.setattr(uvicorn, "Server", Server)
    with patch.dict(os.environ, {}, clear=True):
        run_product.main([])
    output = capsys.readouterr().out
    assert "http://localhost:5173/config" in output
    assert "password verification enabled" in output
    assert "Management token" not in output
    assert "synthetic-private-readiness-error" not in output


def test_selected_instance_configuration_round_trips_through_setup_and_restart(
    tmp_path, monkeypatch,
):
    import uvicorn
    from fastapi.testclient import TestClient

    from backend.app.product import application
    from backend.app.runtime.configuration_paths import configuration_directory

    checkout = tmp_path / "checkout"
    instance = tmp_path / "instance"
    other = tmp_path / "other-instance"
    for directory in (checkout, instance, other):
        directory.mkdir()
    (checkout / "index.html").write_text("Dayloom setup", encoding="utf-8")
    (checkout / ".env").write_text("OPENAI_API_KEY=checkout-private\n", encoding="utf-8")
    (instance / "product.yaml").write_text(
        "origin: http://localhost:5198\nallow_insecure_loopback: true\n", encoding="utf-8",
    )
    (other / ".env").write_text("OPENAI_API_KEY=other-private\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(run_product, "PROJECT_ROOT", checkout)
    create_application = application.create_product_application
    monkeypatch.setattr(
        application, "create_product_application", lambda: create_application(checkout),
    )
    signing_keys = []

    class Server:
        def __init__(self, config):
            self.app = config.app

        async def serve(self):
            manager = self.app.state.local_configuration
            assert manager.root == configuration_directory()
            signing_keys.append(manager.initial["PRODUCT_JWT_SECRET"])
            with TestClient(
                self.app, base_url=manager.origin, client=("127.0.0.1", 50000),
                headers={"Origin": manager.origin},
            ) as client:
                session = client.post("/api/config/session", json={
                    "password": "dayloom-config-2026",
                })
                assert session.status_code == 200
                client.headers["X-CSRF-Token"] = session.json()["csrf_token"]
                view = client.get("/api/config").json()
                if len(signing_keys) == 1:
                    assert not view["fields"]["OPENAI_API_KEY"]["configured"]
                    assert not view["fields"]["OPENAI_API_KEY"]["locked"]
                    response = client.put("/api/config", json={
                        "revision": view["revision"], "changes": {
                            "OPENAI_API_KEY": "instance-private",
                            "AZURE_OPENAI_ENDPOINT": "https://instance.services.ai.azure.com/openai/v1",
                            "AZURE_OPENAI_DEPLOYMENT": "instance-model",
                        },
                    })
                    assert response.status_code == 200
                    assert response.json()["restart_required"] is True
                    assert manager.initial["OPENAI_API_KEY"] == ""
                else:
                    assert view["fields"]["OPENAI_API_KEY"]["configured"]
                    assert manager.initial["OPENAI_API_KEY"] == "instance-private"
                    assert manager.initial["AZURE_OPENAI_DEPLOYMENT"] == "instance-model"
                    assert view["restart_required"] is False

    monkeypatch.setattr(uvicorn, "Server", Server)
    for _ in range(2):
        with patch.dict(os.environ, {"DAYLOOM_CONFIG_DIR": str(instance)}, clear=True):
            run_product.main(["--port", "5198"])
    assert signing_keys[0] == signing_keys[1]
    assert (checkout / ".env").read_text("utf-8") == "OPENAI_API_KEY=checkout-private\n"
    assert (other / ".env").read_text("utf-8") == "OPENAI_API_KEY=other-private\n"
    assert not (checkout / ".config-access.json").exists()


@pytest.mark.parametrize("arguments", [["--check"], ["--host", "0.0.0.0"]])
def test_check_and_nonlocal_launch_remain_strict(local_launcher, arguments):
    with patch.dict(os.environ, {}, clear=True), pytest.raises(SystemExit) as failure:
        run_product.main(arguments)
    assert "synthetic-private" not in str(failure.value)


def test_launcher_pins_case_variants_without_shadowing_external_settings(
    local_launcher, monkeypatch,
):
    import uvicorn

    (local_launcher / ".env").write_text(
        "openai_api_key=synthetic-dotenv\nOPENAI_API_KEY=synthetic-dotenv-upper\n",
        encoding="utf-8",
    )

    class Server:
        def __init__(self, config):
            self.manager = config.app.state.local_configuration

        async def serve(self):
            assert self.manager.initial["OPENAI_API_KEY"] == "synthetic-external"
            assert os.environ["OPENAI_API_KEY"] == "synthetic-external"
            assert "openai_api_key" not in os.environ
            from backend.app.integrations.openai_search import SearchSettings
            assert SearchSettings().openai_api_key.get_secret_value() == "synthetic-external"

    monkeypatch.setattr(uvicorn, "Server", Server)
    # A plain dict reproduces Unix casing semantics on Windows without changing real credentials.
    with patch.object(os, "environ", {"OPENAI_API_KEY": "synthetic-external"}):
        run_product.main([])


def test_launcher_migrates_legacy_foundry_values_and_pins_yaml_until_restart(
    local_launcher, monkeypatch,
):
    import uvicorn
    import yaml

    dotenv = local_launcher / ".env"
    dotenv.write_text(
        "AZURE_OPENAI_ENDPOINT=https://new.services.ai.azure.com/openai/v1\n"
        "AZURE_OPENAI_DEPLOYMENT=saved-deployment\nAZURE_OPENAI_API_KEY=synthetic-private\n",
        encoding="utf-8",
    )

    class Server:
        def __init__(self, config):
            self.manager = config.app.state.local_configuration

        async def serve(self):
            assert os.environ["AZURE_OPENAI_DEPLOYMENT"] == "saved-deployment"
            assert self.manager.initial["AZURE_OPENAI_DEPLOYMENT"] == "saved-deployment"
            assert "AZURE_OPENAI_DEPLOYMENT" not in dotenv.read_text("utf-8")
            self.manager.save(self.manager.view()["revision"], {
                "AZURE_OPENAI_DEPLOYMENT": "next-deployment",
            })
            assert yaml.safe_load((local_launcher / "product.yaml").read_text("utf-8"))[
                "foundry"
            ]["deployment"] == "next-deployment"
            assert os.environ["AZURE_OPENAI_DEPLOYMENT"] == "saved-deployment"

    monkeypatch.setattr(uvicorn, "Server", Server)
    with patch.dict(os.environ, {}, clear=True):
        run_product.main([])


@pytest.mark.parametrize(
    "existing", [None, "", "synthetic-existing-signing-key-at-least-32-characters"],
)
def test_local_startup_initializes_signing_key_once_and_preserves_existing(
    local_launcher, monkeypatch, existing,
):
    import uvicorn
    from dotenv import dotenv_values
    dotenv = local_launcher / ".env"
    if existing is not None:
        dotenv.write_text("PRODUCT_JWT_SECRET=" + existing + "\n", encoding="utf-8")
    keys = []

    class Server:
        def __init__(self, config):
            self.manager = config.app.state.local_configuration

        async def serve(self):
            saved = dotenv_values(dotenv)["PRODUCT_JWT_SECRET"]
            assert len(saved) >= 32
            assert os.environ["PRODUCT_JWT_SECRET"] == saved
            assert self.manager.view()["restart_required"] is False
            keys.append(saved)

    monkeypatch.setattr(uvicorn, "Server", Server)
    for _ in range(2):
        with patch.dict(os.environ, {}, clear=True):
            run_product.main([])
    assert keys[0] == keys[1]
    if existing:
        assert keys[0] == existing


def test_launcher_keeps_split_database_and_signing_settings_pinned(local_launcher, monkeypatch):
    import uvicorn
    from psycopg.conninfo import conninfo_to_dict

    from backend.app.product.settings import ProductSettings

    (local_launcher / ".env").write_text(
        "DAYLOOM_DB_NAME=launcher_test\nDAYLOOM_DB_PASSWORD=synthetic-database-password\n",
        encoding="utf-8",
    )

    class Server:
        def __init__(self, config):
            self.manager = config.app.state.local_configuration

        async def serve(self):
            before = ProductSettings(_env_file=None)
            connection = conninfo_to_dict(before.database_url.get_secret_value())
            assert connection["dbname"] == "launcher_test"
            self.manager.save(self.manager.view()["revision"], {
                "DAYLOOM_DB_URL": "postgresql://localhost/next_test",
                "PRODUCT_JWT_SECRET": "synthetic-replacement-signing-key-at-least-32",
            })
            after = ProductSettings(_env_file=None)
            assert after.database_url == before.database_url
            assert after.jwt_secret == before.jwt_secret

    monkeypatch.setattr(uvicorn, "Server", Server)
    with patch.dict(os.environ, {}, clear=True):
        run_product.main([])
