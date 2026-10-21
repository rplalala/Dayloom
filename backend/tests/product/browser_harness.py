"""Credential-safe process configuration and public browser fixture context."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from playwright.sync_api import Browser
from pydantic import SecretStr

BROWSER_TEST_SIGNING_KEY = "browser-test-key-with-at-least-32-characters"
_OS_TOOL_KEYS = (
    "PATH",
    "PATHEXT",
    "SYSTEMROOT",
    "WINDIR",
    "COMSPEC",
    "SYSTEMDRIVE",
    "LOCALAPPDATA",
    "APPDATA",
    "USERPROFILE",
    "HOME",
    "HOMEDRIVE",
    "HOMEPATH",
    "PROGRAMFILES",
    "PROGRAMFILES(X86)",
    "PROGRAMDATA",
)


class IsolatedEnvironment(dict[str, str]):
    """Subprocess-compatible mapping whose diagnostic representation excludes values."""

    def __repr__(self) -> str:
        return "<isolated browser environment; credential values hidden>"

    __str__ = __repr__


@dataclass(frozen=True)
class BrowserApplication:
    base_url: str
    browser: Browser = field(repr=False)


def isolated_environment(
    database_url: SecretStr, api_port: str, web_port: str, temporary_directory: Path
) -> IsolatedEnvironment:
    """Inherit OS/tool paths only; provider/account credentials are never inherited."""
    temporary_directory.mkdir(parents=True, exist_ok=True)
    environment = IsolatedEnvironment(
        {key: os.environ[key] for key in _OS_TOOL_KEYS if key in os.environ}
    )
    environment.update(
        {
            "TEMP": str(temporary_directory),
            "TMP": str(temporary_directory),
            "TMPDIR": str(temporary_directory),
            "PYTHONUTF8": "1",
            "PYTHONUNBUFFERED": "1",
            "PRODUCT_DATABASE_URL": database_url.get_secret_value(),
            "PRODUCT_JWT_SECRET": BROWSER_TEST_SIGNING_KEY,
            "PRODUCT_ALLOW_INSECURE_LOOPBACK": "true",
            "PRODUCT_ORIGIN": f"http://localhost:{web_port}",
            "PRODUCT_API_PROXY": f"http://127.0.0.1:{api_port}",
        }
    )
    return environment
