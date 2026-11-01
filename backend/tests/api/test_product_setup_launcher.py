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
