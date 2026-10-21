"""Product configuration is loaded only when a Product service is used."""

from urllib.parse import urlparse

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ProductSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PRODUCT_", env_file=".env", extra="ignore", hide_input_in_errors=True
    )

    database_url: SecretStr
    jwt_secret: SecretStr
    origin: str = "https://localhost"
    allow_insecure_loopback: bool = False
    session_seconds: int = 3600

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
