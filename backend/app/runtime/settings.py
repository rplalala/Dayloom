"""Shared environment-backed runtime settings."""

from pydantic_settings import SettingsConfigDict

from backend.app.runtime.configuration_paths import InstanceSettings


class RuntimeSettings(InstanceSettings):
    """Configuration shared by every independently runnable planner version."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def app_time_zone(self) -> str:
        """Read the validated project-wide calendar policy, never an env override."""

        from backend.app.runtime.config_loader import load_runtime_config

        return load_runtime_config().app.time_zone
