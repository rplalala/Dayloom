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
    assert "Management token" in output
    assert "synthetic-private-readiness-error" not in output


@pytest.mark.parametrize("arguments", [["--check"], ["--host", "0.0.0.0"]])
def test_check_and_nonlocal_launch_remain_strict(local_launcher, arguments):
    with patch.dict(os.environ, {}, clear=True), pytest.raises(SystemExit) as failure:
        run_product.main(arguments)
    assert "synthetic-private" not in str(failure.value)
