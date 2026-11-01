"""Provider configuration round trips through its owned files without network calls."""

import os

import pytest
import yaml

from backend.app.product.configuration import LocalConfiguration
from backend.tests.product.test_configuration import connect_manager


def test_foundry_edits_update_yaml_while_credentials_stay_in_dotenv(tmp_path):
    yaml_path = tmp_path / "product.yaml"
    yaml_path.write_text(
        "# Local deployment\norigin: http://localhost:5173\n"
        "database:\n  host: localhost\n  port: 5432\n  name: retained\n  user: retained\n"
        "foundry:\n  endpoint: https://old.services.ai.azure.com/openai/v1 # Model URL\n"
        "  deployment: old-deployment\n", encoding="utf-8",
    )
    dotenv = tmp_path / ".env"
    dotenv.write_text("# Private settings\nDAYLOOM_DB_PASSWORD=retained\n", encoding="utf-8")
    manager, client = connect_manager(tmp_path)
    before = yaml.safe_load(yaml_path.read_text("utf-8"))
    with client:
        response = client.put("/api/config", json={
            "revision": manager.view()["revision"],
            "changes": {
                "AZURE_OPENAI_ENDPOINT": "https://new.services.ai.azure.com/openai/v1",
                "AZURE_OPENAI_DEPLOYMENT": "new-deployment",
                "AZURE_OPENAI_API_KEY": "synthetic-new-private",
            },
        })
    assert response.status_code == 200
    saved = yaml.safe_load(yaml_path.read_text("utf-8"))
    assert saved["foundry"] == {
        "endpoint": "https://new.services.ai.azure.com/openai/v1",
        "deployment": "new-deployment",
    }
    assert saved["database"] == before["database"]
    assert "# Local deployment" in yaml_path.read_text("utf-8")
    assert "# Model URL" in yaml_path.read_text("utf-8")
    assert "synthetic-new-private" not in yaml_path.read_text("utf-8")
    assert "AZURE_OPENAI_ENDPOINT" not in dotenv.read_text("utf-8")
    assert "AZURE_OPENAI_DEPLOYMENT" not in dotenv.read_text("utf-8")
    assert "DAYLOOM_DB_PASSWORD=retained" in dotenv.read_text("utf-8")
    assert "synthetic-new-private" in dotenv.read_text("utf-8")
    assert manager.initial["AZURE_OPENAI_DEPLOYMENT"] == "old-deployment"
    assert response.json()["restart_required"] is True
    assert "synthetic-new-private" not in response.text
    restarted = LocalConfiguration(tmp_path, origin=manager.origin, environment={})
    assert restarted.initial["AZURE_OPENAI_DEPLOYMENT"] == "new-deployment"
    assert restarted.view()["restart_required"] is False


def test_startup_moves_legacy_overrides_to_yaml_without_losing_saved_values(tmp_path):
    yaml_path = tmp_path / "product.yaml"
    yaml_path.write_text(
        "origin: http://localhost:5173\nfoundry:\n"
        "  endpoint: https://old.services.ai.azure.com/openai/v1\n"
        "  deployment: yaml-deployment\n", encoding="utf-8",
    )
    dotenv = tmp_path / ".env"
    dotenv.write_text(
        "# Private settings\nAZURE_OPENAI_ENDPOINT=https://new.services.ai.azure.com/openai/v1\n"
        "azure_openai_deployment=first\nAZURE_OPENAI_DEPLOYMENT=last\n"
        "OPENAI_API_KEY=synthetic-private\nDAYLOOM_DB_PASSWORD=retained\n", encoding="utf-8",
    )
    manager = LocalConfiguration(tmp_path, origin="http://localhost:5173", environment={})
    assert manager.initial["AZURE_OPENAI_DEPLOYMENT"] == "last"
    assert yaml.safe_load(yaml_path.read_text("utf-8"))["foundry"] == {
        "endpoint": "https://new.services.ai.azure.com/openai/v1", "deployment": "last",
    }
    assert dotenv.read_text("utf-8") == (
        "# Private settings\nOPENAI_API_KEY=synthetic-private\nDAYLOOM_DB_PASSWORD=retained\n"
    )
    yaml_before, env_before = yaml_path.read_bytes(), dotenv.read_bytes()
    restarted = LocalConfiguration(tmp_path, origin=manager.origin, environment={})
    assert restarted.initial == manager.initial
    assert yaml_path.read_bytes() == yaml_before
    assert dotenv.read_bytes() == env_before


@pytest.mark.parametrize("contents", [
    "", "# Empty deployment\n", "foundry: null\n", "foundry:\n", "foundry: {}\n",
    'foundry: {deployment: old}\n', '{origin: "http://localhost:5173"}\n',
])
def test_incomplete_yaml_can_be_completed_or_cleared_from_configuration(tmp_path, contents):
    path = tmp_path / "product.yaml"
    path.write_text(contents, encoding="utf-8")
    manager, client = connect_manager(tmp_path)
    with client:
        response = client.put("/api/config", json={
            "revision": manager.view()["revision"], "changes": {
                "AZURE_OPENAI_ENDPOINT": "https://new.services.ai.azure.com/openai/v1",
                "AZURE_OPENAI_DEPLOYMENT": "new-deployment",
            },
        })
        assert response.status_code == 200
        assert yaml.safe_load(path.read_text("utf-8"))["foundry"]["deployment"] == "new-deployment"
        response = client.put("/api/config", json={
            "revision": response.json()["revision"],
            "changes": {"AZURE_OPENAI_DEPLOYMENT": ""},
        })
        assert response.status_code == 200
        assert response.json()["fields"]["AZURE_OPENAI_DEPLOYMENT"]["configured"] is False
    restarted = LocalConfiguration(tmp_path, origin=manager.origin, environment={})
    assert restarted.initial["AZURE_OPENAI_ENDPOINT"] == "https://new.services.ai.azure.com/openai/v1"
    assert restarted.initial["AZURE_OPENAI_DEPLOYMENT"] == ""


def test_yaml_changes_outside_foundry_invalidate_a_stale_save(tmp_path):
    path = tmp_path / "product.yaml"
    path.write_text("session_seconds: 3600\n", encoding="utf-8")
    manager, client = connect_manager(tmp_path)
    revision = manager.view()["revision"]
    path.write_text("session_seconds: 7200\n", encoding="utf-8")
    with client:
        response = client.put("/api/config", json={
            "revision": revision, "changes": {"OPENAI_API_KEY": "stale-private"},
        })
    assert response.status_code == 409
    assert path.read_text("utf-8") == "session_seconds: 7200\n"
    assert not (tmp_path / ".env").exists()


def test_mixed_save_rolls_back_yaml_if_dotenv_replacement_fails(tmp_path, monkeypatch):
    yaml_path, dotenv = tmp_path / "product.yaml", tmp_path / ".env"
    yaml_path.write_text("foundry:\n  deployment: old\n", encoding="utf-8")
    dotenv.write_text("OPENAI_API_KEY=old-private\n", encoding="utf-8")
    manager, client = connect_manager(tmp_path)
    before = {path: path.read_bytes() for path in (yaml_path, dotenv)}
    replace = os.replace
    calls = 0

    def fail_second_replace(source, destination):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("synthetic-private-failure")
        return replace(source, destination)

    monkeypatch.setattr(os, "replace", fail_second_replace)
    with client:
        response = client.put("/api/config", json={
            "revision": manager.view()["revision"], "changes": {
                "AZURE_OPENAI_DEPLOYMENT": "new", "OPENAI_API_KEY": "new-private",
            },
        })
    assert response.status_code == 503
    assert "private" not in response.text
    assert calls == 3
    assert {path: path.read_bytes() for path in before} == before
    assert not list(tmp_path.glob("*.config-*"))


def test_migration_preserves_values_that_reference_a_retired_override(tmp_path):
    (tmp_path / ".env").write_text(
        "AZURE_OPENAI_DEPLOYMENT=first\nCOPY=${AZURE_OPENAI_DEPLOYMENT}\n"
        "AZURE_OPENAI_DEPLOYMENT=last\nSECOND_COPY=${AZURE_OPENAI_DEPLOYMENT}\n",
        encoding="utf-8",
    )
    manager = LocalConfiguration(tmp_path, origin="http://localhost:5173", environment={})
    values = manager.read()[1]
    assert values["COPY"] == "first"
    assert values["SECOND_COPY"] == "last"
    assert manager.initial["AZURE_OPENAI_DEPLOYMENT"] == "last"


def test_missing_yaml_deployment_still_fails_planner_validation(tmp_path):
    from unittest.mock import patch

    from pydantic import ValidationError
    from pydantic_settings import SettingsConfigDict

    from backend.app.versions.v0.config import V0Settings

    path = tmp_path / "product.yaml"
    path.write_text(
        "foundry:\n  endpoint: https://example.services.ai.azure.com/openai/v1\n",
        encoding="utf-8",
    )

    class Settings(V0Settings):
        model_config = SettingsConfigDict(yaml_file=path, env_file=None)

    with patch.dict(os.environ, {}, clear=True), pytest.raises(ValidationError) as error:
        Settings(AZURE_OPENAI_API_KEY="synthetic-private")
    assert error.value.errors()[0]["loc"] == ("AZURE_OPENAI_DEPLOYMENT",)


def test_adding_a_foundry_field_after_a_block_scalar_keeps_following_root_settings(tmp_path):
    path = tmp_path / "product.yaml"
    path.write_text(
        "foundry:\n  endpoint: >-\n    https://example.services.ai.azure.com/openai/v1\n"
        "origin: http://localhost:5173\n", encoding="utf-8",
    )
    manager, client = connect_manager(tmp_path)
    with client:
        response = client.put("/api/config", json={
            "revision": manager.view()["revision"],
            "changes": {"AZURE_OPENAI_DEPLOYMENT": "new-deployment"},
        })
    assert response.status_code == 200
    saved = yaml.safe_load(path.read_text("utf-8"))
    assert saved["origin"] == "http://localhost:5173"
    assert saved["foundry"] == {
        "endpoint": "https://example.services.ai.azure.com/openai/v1",
        "deployment": "new-deployment",
    }
