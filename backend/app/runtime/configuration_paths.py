"""Instance-local configuration paths shared by settings readers and launchers."""

import os
from pathlib import Path

from pydantic_settings import BaseSettings

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def configuration_directory(default: Path = PROJECT_ROOT) -> Path:
    """Keep host defaults; resolve an explicit instance relative to the project."""
    selected = os.environ.get("DAYLOOM_CONFIG_DIR")
    if not selected:
        return default
    path = Path(selected).expanduser()
    return (path if path.is_absolute() else default / path).resolve()


class InstanceSettings(BaseSettings):
    """Select the instance dotenv at construction time, respecting explicit overrides."""

    def __init__(self, **values):
        if os.environ.get("DAYLOOM_CONFIG_DIR") and "_env_file" not in values:
            values["_env_file"] = configuration_directory() / ".env"
        super().__init__(**values)
