"""Shared PostgreSQL connection settings, independent of Product and planner policies."""

from pathlib import Path

from psycopg.conninfo import conninfo_to_dict, make_conninfo
from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.app.runtime.deployment import DEPLOYMENT_FILE, DeploymentYamlSettingsSource

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DAYLOOM_DB_", env_file=PROJECT_ROOT / ".env",
        extra="ignore", hide_input_in_errors=True,
        yaml_file=DEPLOYMENT_FILE,
    )

    host: str = Field(default="127.0.0.1", min_length=1)
    port: int = Field(default=55432, ge=1, le=65535)
    name: str = Field(default="dayloom", min_length=1)
    user: str = Field(default="dayloom", min_length=1)
    password: SecretStr = SecretStr("")
    url: SecretStr | None = None

    @classmethod
    def settings_customise_sources(
        cls, settings_cls, init_settings, env_settings, dotenv_settings, file_secret_settings
    ):
        return (
            init_settings, env_settings, dotenv_settings, file_secret_settings,
            DeploymentYamlSettingsSource(settings_cls, section="database"),
        )

    @field_validator("url", mode="before")
    @classmethod
    def blank_url_uses_connection_fields(cls, value):
        return None if value == "" else value

    @model_validator(mode="after")
    def validate_connection(self):
        if self.url is None and not self.password.get_secret_value():
            raise ValueError("Set DAYLOOM_DB_PASSWORD or DAYLOOM_DB_URL")
        self.connection_parameters()
        return self

    def connection_parameters(self) -> dict:
        if self.url is not None:
            try:
                parameters = conninfo_to_dict(self.url.get_secret_value())
            except Exception:
                raise ValueError("Invalid DAYLOOM_DB_URL") from None
            if not parameters.get("dbname"):
                raise ValueError("DAYLOOM_DB_URL must specify a database name")
        else:
            parameters = {
                "host": self.host, "port": self.port, "dbname": self.name,
                "user": self.user, "password": self.password.get_secret_value(),
            }
        # The retained vector extension may live in tripworld or public. Avoid
        # depending on PostgreSQL's "$user" path after the login role is renamed.
        parameters["options"] = (
            parameters.get("options", "") + " -c search_path=tripworld,public"
        ).strip()
        return parameters

    @property
    def connection_string(self) -> SecretStr:
        return SecretStr(make_conninfo(**self.connection_parameters()))
