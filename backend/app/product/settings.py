"""Product configuration is loaded only when a Product service is used."""

from pathlib import Path
from urllib.parse import urlparse

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.app.runtime.database import DatabaseSettings
from backend.app.runtime.deployment import DeploymentYamlSettingsSource, ProductOptions

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class ProductSettings(ProductOptions, BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PRODUCT_", env_file=PROJECT_ROOT / ".env", extra="ignore",
        hide_input_in_errors=True, yaml_file=PROJECT_ROOT / "product.yaml",
        yaml_file_encoding="utf-8", populate_by_name=True,
    )

    database_url: SecretStr = Field(
        validation_alias="DAYLOOM_DB_URL",
    )
    jwt_secret: SecretStr

    @classmethod
    def settings_customise_sources(
        cls, settings_cls, init_settings, env_settings, dotenv_settings, file_secret_settings
    ):
        def shared_database():
            if any(
                {"DAYLOOM_DB_URL", "database_url"}.intersection(source())
                for source in (init_settings, env_settings, dotenv_settings, file_secret_settings)
            ):
                return {}
            class ProductDatabaseSettings(DatabaseSettings):
                model_config = SettingsConfigDict(yaml_file=settings_cls.model_config["yaml_file"])

            return {"DAYLOOM_DB_URL": ProductDatabaseSettings(
                _env_file=dotenv_settings.env_file
            ).connection_string}

        return (
            init_settings, env_settings, dotenv_settings, file_secret_settings,
            shared_database, DeploymentYamlSettingsSource(settings_cls),
        )

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value):
        return DatabaseSettings(url=value, _env_file=None).connection_string

    @model_validator(mode="after")
    def validate_security(self):
        origin = urlparse(self.origin)
        if (
            origin.scheme not in {"http", "https"}
            or not origin.hostname
            or origin.path not in {"", "/"}
            or origin.query
            or origin.fragment
            or origin.username
            or origin.password
        ):
            raise ValueError("Product origin must be an HTTP(S) origin")
        if len(self.jwt_secret.get_secret_value()) < 32:
            raise ValueError("Product signing key must contain at least 32 characters")
        if origin.scheme != "https" and not (
            self.allow_insecure_loopback and origin.hostname in {"localhost", "127.0.0.1", "::1"}
        ):
            raise ValueError("HTTP cookies require the explicit loopback exception")
        if not 1 <= self.session_seconds <= 86400:
            raise ValueError("Product session lifetime must be between 1 and 86400 seconds")
        return self

    @property
    def secure_cookie(self) -> bool:
        return urlparse(self.origin).scheme == "https"
