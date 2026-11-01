"""Validated non-secret deployment configuration shared by every runtime entry point."""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings, SettingsConfigDict, YamlConfigSettingsSource

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEPLOYMENT_FILE = PROJECT_ROOT / "product.yaml"


class ProductOptions(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    origin: str = "https://localhost"
    allow_insecure_loopback: bool = False
    session_seconds: int = 3600
    runtime_profile: Literal["development", "acceptance"] = "acceptance"


class DatabaseOptions(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    host: str = Field(min_length=1)
    port: int = Field(ge=1, le=65535)
    name: str = Field(min_length=1)
    user: str = Field(min_length=1)


class FoundryOptions(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    endpoint: AnyHttpUrl | None = None
    deployment: str | None = Field(default=None, min_length=1)


class DeploymentOptions(ProductOptions):
    database: DatabaseOptions | None = None
    foundry: FoundryOptions | None = None


class DeploymentYamlLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        self.flatten_mapping(node)
        result = {}
        for key, value in self.construct_pairs(node, deep=deep):
            try:
                if key in result:
                    raise yaml.YAMLError("Duplicate setting")
                result[key] = value
            except TypeError:
                raise yaml.YAMLError("Invalid setting key") from None
        return result


class DeploymentYamlSettingsSource(YamlConfigSettingsSource):
    def __init__(self, settings_cls, *, section=None, aliases=None):
        self.section, self.aliases = section, aliases or {}
        super().__init__(settings_cls)

    def _read_file(self, file_path):
        try:
            with file_path.open(encoding="utf-8") as stream:
                data = yaml.load(stream, Loader=DeploymentYamlLoader)
        except yaml.YAMLError:
            raise ValueError("Invalid Product YAML syntax or duplicate setting") from None
        options = DeploymentOptions.model_validate({} if data is None else data)
        if self.section:
            section = getattr(options, self.section)
            values = {} if section is None else section.model_dump(mode="json", exclude_none=True)
        else:
            values = options.model_dump(exclude={"database", "foundry"}, exclude_unset=True)
        return {self.aliases.get(key, key): value for key, value in values.items()}


class ProductPolicySettings(ProductOptions, BaseSettings):
    """Non-secret policy selection also works for guest input assistance."""

    model_config = SettingsConfigDict(
        env_prefix="PRODUCT_", env_file=PROJECT_ROOT / ".env", extra="ignore",
        hide_input_in_errors=True, yaml_file=DEPLOYMENT_FILE,
    )

    @classmethod
    def settings_customise_sources(
        cls, settings_cls, init_settings, env_settings, dotenv_settings, file_secret_settings
    ):
        return (
            init_settings, env_settings, dotenv_settings, file_secret_settings,
            DeploymentYamlSettingsSource(settings_cls),
        )
