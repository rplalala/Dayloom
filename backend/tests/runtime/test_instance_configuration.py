"""An instance's public settings readers use the same editable configuration."""

import os
from unittest.mock import patch

from backend.app.integrations.openai_search import SearchSettings
from backend.app.observability.product_logs import ProductLogSettings
from backend.app.product.media import MediaSettings
from backend.app.product.settings import ProductSettings
from backend.app.runtime.database import DatabaseSettings
from backend.app.runtime.deployment import ProductPolicySettings
from backend.app.versions.v0.config import V0Settings


def test_selected_instance_supplies_all_settings_from_any_working_directory(tmp_path, monkeypatch):
    instance = tmp_path / "instance"
    instance.mkdir()
    (instance / ".env").write_text(
        "DAYLOOM_DB_PASSWORD=instance-database-secret\n"
        "PRODUCT_JWT_SECRET=instance-signing-secret-at-least-32-characters\n"
        "AZURE_OPENAI_API_KEY=instance-model-key\nGOOGLE_MAPS_API_KEY=instance-maps-key\n"
        "OPENAI_API_KEY=instance-embedding-key\nUNSPLASH_API_KEY=instance-atmosphere-key\n",
        encoding="utf-8",
    )
    (instance / "product.yaml").write_text(
        "origin: http://localhost:5198\nallow_insecure_loopback: true\n"
        "database:\n  host: postgres\n  port: 5432\n  name: instance_test\n  user: instance_user\n"
        "foundry:\n  endpoint: https://instance.services.ai.azure.com/openai/v1\n"
        "  deployment: instance-model\n", encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    with patch.dict(os.environ, {"DAYLOOM_CONFIG_DIR": str(instance)}, clear=True):
        assert ProductPolicySettings().origin == "http://localhost:5198"
        parameters = DatabaseSettings().connection_parameters()
        assert parameters["host"] == "postgres"
        assert parameters["dbname"] == "instance_test"
        assert parameters["password"] == "instance-database-secret"
        assert "instance_test" in ProductSettings().database_url.get_secret_value()
        assert V0Settings().azure_openai_deployment == "instance-model"
        assert SearchSettings().openai_api_key.get_secret_value() == "instance-embedding-key"
        media = MediaSettings()
        assert media.google_places_media_key.get_secret_value() == "instance-maps-key"
        assert media.unsplash_access_key.get_secret_value() == "instance-atmosphere-key"


def test_instance_diagnostics_read_the_selected_configuration(tmp_path):
    (tmp_path / ".env").write_text("PRODUCT_LOG_ENABLED=false\n", encoding="utf-8")
    with patch.dict(os.environ, {"DAYLOOM_CONFIG_DIR": str(tmp_path)}, clear=True):
        assert ProductLogSettings().enabled is False


def test_explicit_dotenv_and_environment_overrides_keep_their_precedence(tmp_path):
    instance = tmp_path / "instance"
    instance.mkdir()
    (instance / ".env").write_text(
        "DAYLOOM_DB_PASSWORD=instance-secret\nDAYLOOM_DB_NAME=instance_test\n", encoding="utf-8",
    )
    override = tmp_path / "selected.env"
    override.write_text(
        "DAYLOOM_DB_PASSWORD=selected-secret\nDAYLOOM_DB_NAME=selected_test\n", encoding="utf-8",
    )
    with patch.dict(os.environ, {"DAYLOOM_CONFIG_DIR": str(instance)}, clear=True):
        selected = DatabaseSettings(_env_file=override)
        assert selected.name == "selected_test"
        assert selected.password.get_secret_value() == "selected-secret"
        explicit = DatabaseSettings(_env_file=None, password="explicit-secret")
        assert explicit.password.get_secret_value() == "explicit-secret"
        assert explicit.name == "dayloom"
        os.environ["DAYLOOM_DB_NAME"] = "process_test"
        assert DatabaseSettings().name == "process_test"
