"""Product configuration is loaded only when a Product service is used."""

from pathlib import Path
from urllib.parse import urlparse

import yaml
from pydantic import BaseModel, ConfigDict, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict, YamlConfigSettingsSource

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class ProductOptions(BaseModel):
    """The non-secret deployment options accepted in product.yaml."""

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    origin: str = "https://localhost"
    allow_insecure_loopback: bool = False
    session_seconds: int = 3600


class ProductYamlSettingsSource(YamlConfigSettingsSource):
    def _read_file(self, file_path):
        try:
            with file_path.open(encoding="utf-8") as yaml_file:
                options = yaml.load(yaml_file, Loader=ProductYamlLoader)
        except yaml.YAMLError:
            # Parser diagnostics can echo pasted credentials or whole source lines.
            raise ValueError("Invalid Product YAML syntax or duplicate setting") from None

        return ProductOptions.model_validate(
            {} if options is None else options
        ).model_dump(exclude_unset=True)


class ProductYamlLoader(yaml.SafeLoader):
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


class ProductSettings(ProductOptions, BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PRODUCT_", env_file=PROJECT_ROOT / ".env", extra="ignore",
        hide_input_in_errors=True, yaml_file=PROJECT_ROOT / "product.yaml",
        yaml_file_encoding="utf-8",
    )

    database_url: SecretStr
    jwt_secret: SecretStr

    @classmethod
    def settings_customise_sources(
        cls, settings_cls, init_settings, env_settings, dotenv_settings, file_secret_settings
    ):
        return (
            init_settings, env_settings, dotenv_settings, file_secret_settings,
            ProductYamlSettingsSource(settings_cls),
        )

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
