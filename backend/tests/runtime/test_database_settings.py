"""Product, retrieval and maintenance share one credential-safe connection contract."""

import pytest
from pydantic import ValidationError
from pydantic_settings import SettingsConfigDict

from backend.app.runtime.database import DatabaseSettings


def test_shared_database_reads_yaml_and_preserves_override_precedence(monkeypatch, tmp_path):
    for key in ("URL", "HOST", "PORT", "NAME", "USER", "PASSWORD"):
        monkeypatch.delenv("DAYLOOM_DB_" + key, raising=False)
    path = tmp_path / "deployment.yaml"
    path.write_text(
        "database:\n  host: 127.0.0.1\n  port: 55618\n"
        "  name: yaml_test\n  user: yaml_user\n", encoding="utf-8"
    )

    class Settings(DatabaseSettings):
        model_config = SettingsConfigDict(yaml_file=path)

    assert Settings(_env_file=None, password="synthetic").name == "yaml_test"
    env = tmp_path / "settings.env"
    env.write_text("DAYLOOM_DB_NAME=dotenv_test\n", encoding="utf-8")
    assert Settings(_env_file=env, password="synthetic").name == "dotenv_test"
    monkeypatch.setenv("DAYLOOM_DB_NAME", "process_test")
    assert Settings(_env_file=env, password="synthetic").name == "process_test"
    explicit = Settings(_env_file=env, password="synthetic", name="explicit_test")
    assert explicit.name == "explicit_test"


def test_explicit_connection_url_overrides_split_settings():
    settings = DatabaseSettings(
        _env_file=None, host="unused.example", name="unused", user="unused",
        password="unused-secret",
        url="postgresql://test:controlled-url-key@127.0.0.1:55618/shared_test",
    )
    connection = settings.connection_parameters()
    assert connection["dbname"] == "shared_test"
    assert connection["port"] == "55618"
    assert connection["password"] == "controlled-url-key"
    assert "controlled-url-key" not in repr(settings)
    assert "controlled-url-key" not in repr(settings.connection_string)


@pytest.mark.parametrize(
    "url", ["", "private-sentinel", "host=127.0.0.1 password=private-sentinel"]
)
def test_invalid_or_implicit_database_urls_fail_without_disclosing_credentials(url):
    with pytest.raises(ValidationError) as failure:
        DatabaseSettings(_env_file=None, url=url)
    assert "DAYLOOM_DB_URL" in str(failure.value)
    assert "private-sentinel" not in str(failure.value)


def test_shared_database_defaults_do_not_require_product_or_provider_settings(monkeypatch):
    for key in ("URL", "HOST", "PORT", "NAME", "USER", "PASSWORD"):
        monkeypatch.delenv("DAYLOOM_DB_" + key, raising=False)
    settings = DatabaseSettings(_env_file=None, password="synthetic-only")
    connection = settings.connection_parameters()
    assert connection["dbname"] == "dayloom"
    assert connection["user"] == "dayloom"
    assert connection["host"] == "127.0.0.1"
    assert connection["port"] == 55432
