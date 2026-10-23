"""Configuration diagnostics never include unrecognized dotenv credential input."""

import pytest
from psycopg.conninfo import conninfo_to_dict
from pydantic import ValidationError
from pydantic_settings import SettingsConfigDict

from backend.app.product.settings import ProductSettings


def test_product_uses_shared_dayloom_connection_fields(monkeypatch):
    monkeypatch.delenv("DAYLOOM_DB_URL", raising=False)
    for key, value in {
        "HOST": "127.0.0.1", "PORT": "55619", "NAME": "dayloom_settings_test",
        "USER": "dayloom_test_user", "PASSWORD": "synthetic password with @ and :",
    }.items():
        monkeypatch.setenv("DAYLOOM_DB_" + key, value)
    settings = ProductSettings(
        _env_file=None, jwt_secret="configuration-test-signing-key-32-characters"
    )
    connection = conninfo_to_dict(settings.database_url.get_secret_value())
    assert connection["dbname"] == "dayloom_settings_test"
    assert connection["user"] == "dayloom_test_user"
    assert connection["port"] == "55619"
    assert connection["password"] == "synthetic password with @ and :"


def test_product_and_database_use_the_same_explicit_env_file(monkeypatch, tmp_path):
    for key in ("URL", "HOST", "PORT", "NAME", "USER", "PASSWORD"):
        monkeypatch.delenv("DAYLOOM_DB_" + key, raising=False)
    dotenv = tmp_path / "controlled.env"
    dotenv.write_text(
        "DAYLOOM_DB_NAME=controlled_test\nDAYLOOM_DB_PASSWORD=synthetic-only\n"
        "PRODUCT_JWT_SECRET=configuration-test-signing-key-32-characters\n",
        encoding="utf-8",
    )
    connection = conninfo_to_dict(ProductSettings(_env_file=dotenv).database_url.get_secret_value())
    assert connection["dbname"] == "controlled_test"
    assert connection["password"] == "synthetic-only"


@pytest.fixture
def configured_settings(monkeypatch, tmp_path):
    for key in ("ORIGIN", "ALLOW_INSECURE_LOOPBACK", "SESSION_SECONDS"):
        monkeypatch.delenv("PRODUCT_" + key, raising=False)
    monkeypatch.setenv("DAYLOOM_DB_URL", "postgresql://localhost/dayloom_test")
    monkeypatch.setenv("PRODUCT_JWT_SECRET", "configuration-test-signing-key-32-characters")
    yaml_path = tmp_path / "product.yaml"
    yaml_path.write_text(
        "origin: http://localhost:5197\nallow_insecure_loopback: true\nsession_seconds: 7200\n",
        encoding="utf-8",
    )

    class ConfiguredSettings(ProductSettings):
        model_config = SettingsConfigDict(yaml_file=yaml_path, env_file=None)

    return ConfiguredSettings, yaml_path


def test_product_options_load_from_yaml_independently_of_working_directory(
    configured_settings, monkeypatch, tmp_path
):
    settings_type, _ = configured_settings
    other_directory = tmp_path / "other"
    other_directory.mkdir()
    monkeypatch.chdir(other_directory)
    settings = settings_type()
    assert settings.origin == "http://localhost:5197"
    assert settings.session_seconds == 7200
    assert settings.secure_cookie is False


@pytest.mark.parametrize("key", ["database_url", "jwt_secret", "session_second"])
def test_product_yaml_rejects_credentials_and_unknown_options(configured_settings, key):
    settings_type, yaml_path = configured_settings
    sentinel = "yaml-private42"
    with yaml_path.open("a", encoding="utf-8") as yaml_file:
        yaml_file.write(f"{key}: {sentinel}\n")
    with pytest.raises(ValidationError) as failure:
        settings_type()
    assert sentinel not in str(failure.value)
    assert key in str(failure.value)


def test_explicit_and_environment_settings_override_yaml_and_dotenv(
    configured_settings, monkeypatch, tmp_path
):
    settings_type, _ = configured_settings
    dotenv = tmp_path / "overrides.env"
    dotenv.write_text("PRODUCT_SESSION_SECONDS=1800\n", encoding="utf-8")
    assert settings_type(_env_file=dotenv).session_seconds == 1800
    monkeypatch.setenv("PRODUCT_SESSION_SECONDS", "900")
    monkeypatch.setenv("PRODUCT_ORIGIN", "https://dayloom.example")
    settings = settings_type(_env_file=dotenv)
    assert settings.session_seconds == 900
    assert settings.secure_cookie is True
    assert settings_type(session_seconds=300, _env_file=dotenv).session_seconds == 300


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"origin": "http://dayloom.example"}, "loopback exception"),
        ({"allow_insecure_loopback": False}, "loopback exception"),
        ({"origin": "https://dayloom.example/path"}, r"HTTP\(S\) origin"),
        ({"session_seconds": 0}, "session lifetime"),
        ({"session_seconds": 86401}, "session lifetime"),
        ({"jwt_secret": "short"}, "at least 32 characters"),
    ],
)
def test_yaml_does_not_bypass_product_security_validation(configured_settings, overrides, message):
    settings_type, _ = configured_settings
    with pytest.raises(ValidationError, match=message):
        settings_type(**overrides)


@pytest.mark.parametrize(
    "contents",
    [
        "origin: [yaml-private42",
        "origin: https://dayloom.example\norigin: http://yaml-private42\n",
    ],
)
def test_malformed_or_duplicate_yaml_fails_without_echoing_values(configured_settings, contents):
    settings_type, yaml_path = configured_settings
    yaml_path.write_text(contents, encoding="utf-8")
    with pytest.raises(ValueError, match="Product YAML") as failure:
        settings_type()
    assert "yaml-private42" not in str(failure.value)


@pytest.mark.parametrize("contents", ["false", "[]", "yaml-private42"])
def test_product_yaml_requires_a_settings_mapping(configured_settings, contents):
    settings_type, yaml_path = configured_settings
    yaml_path.write_text(contents, encoding="utf-8")
    with pytest.raises(ValidationError) as failure:
        settings_type()
    assert "yaml-private42" not in str(failure.value)


def test_missing_product_settings_hide_unrecognized_dotenv_secrets(monkeypatch, tmp_path):
    monkeypatch.delenv("DAYLOOM_DB_URL", raising=False)
    monkeypatch.delenv("PRODUCT_JWT_SECRET", raising=False)
    dotenv = tmp_path / "controlled.env"
    sentinel = "private42"
    dotenv.write_text(f"UNRECOGNIZED_PROVIDER_SECRET={sentinel}\n", encoding="utf-8")
    with pytest.raises(ValidationError) as failure:
        ProductSettings(_env_file=dotenv)
    assert "DAYLOOM_DB_PASSWORD" in str(failure.value)
    assert sentinel not in str(failure.value)
    assert sentinel not in repr(failure.value)
    assert "input_value" not in str(failure.value)
    assert "input_value" not in repr(failure.value)
