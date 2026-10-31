"""Credential-safe process configuration and public browser fixture context."""

import base64
import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import Browser, expect
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


def open_preferences(page):
    """Expose optional editor controls through the traveler's disclosure action."""
    notes = page.get_by_label("Additional preferences", exact=True)
    notes.wait_for(state="attached")
    if not notes.is_visible():
        page.get_by_text("Personalize your trip", exact=True).click()


class IsolatedEnvironment(dict[str, str]):
    """Subprocess-compatible mapping whose diagnostic representation excludes values."""

    def __repr__(self) -> str:
        return "<isolated browser environment; credential values hidden>"

    __str__ = __repr__


def seed_legacy_draft_title(page, value):
    """Seed a pre-r7 local recovery record; current naming uses Library Rename.

    This is an explicit legacy-data precondition, not a production editing hook.
    The real provider restores it after reload and real Save must preserve it.
    """
    page.get_by_role("button", name="Review travel brief", exact=True).wait_for()
    page.evaluate("""value => {
        const key = 'dayloom.editor.v1';
        const record = JSON.parse(sessionStorage.getItem(key));
        if (!record || !record.brief) throw new Error('Missing legacy recovery precondition');
        sessionStorage.setItem(key, JSON.stringify({...record, draftTitle:value}));
    }""", value)
    page.reload()
    page.get_by_role("button", name="Review travel brief", exact=True).wait_for()


def expect_recovered_draft_name(page, value):
    """Observe historical local names without inventing a naming control in r7."""
    page.get_by_role("button", name="Review travel brief", exact=True).click()
    dialog = page.get_by_role("dialog", name="Your travel brief", exact=True)
    expect(dialog.get_by_role("textbox")).to_have_count(0)
    if value:
        expect(dialog.get_by_text("Recovered draft name: " + value, exact=True)).to_be_visible()
    else:
        expect(dialog.get_by_text("Recovered draft name:", exact=False)).to_have_count(0)
    page.get_by_role("button", name="Keep editing", exact=True).click()


def open_json_export(page):
    """Open the r7 export choice before selecting the lossless JSON artifact."""
    page.get_by_role("button", name="Export itinerary", exact=True).click()
    page.get_by_role("button", name="Export JSON", exact=True).click()


@dataclass(frozen=True)
class BrowserApplication:
    base_url: str
    browser: Browser = field(repr=False)


class IsolatedBrowser:
    """Install browser network isolation before any acceptance page can navigate.

    Chromium is outside pytest's Python socket guard. All older browser contexts
    inherit the same test-only image replacement and external-request denial.
    """

    def __init__(self, browser):
        self.browser = browser

    def new_context(self, **kwargs):
        context = self.browser.new_context(**kwargs)

        def intercept(route):
            url = urlsplit(route.request.url)
            if url.hostname in {"localhost", "127.0.0.1", "::1"}:
                return route.continue_()
            if (
                url.hostname in {"images.unsplash.com", "lh3.googleusercontent.com"}
                and route.request.resource_type == "image"
            ):
                return route.fulfill(
                    status=200,
                    content_type="image/png",
                    body=base64.b64decode(
                        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jvS8AAAAASUVORK5CYII="
                    ),
                )
            return route.abort("blockedbyclient")

        context.route("**/*", intercept)
        return context

    def close(self):
        self.browser.close()


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
            "CHROME_LOG_FILE": str(temporary_directory / "chromium.log"),
            "PYTHONUTF8": "1",
            "PYTHONUNBUFFERED": "1",
            "DAYLOOM_DB_URL": database_url.get_secret_value(),
            "PRODUCT_JWT_SECRET": BROWSER_TEST_SIGNING_KEY,
            "PRODUCT_ALLOW_INSECURE_LOOPBACK": "true",
            "PRODUCT_ORIGIN": f"http://localhost:{web_port}",
            "PRODUCT_API_PROXY": f"http://127.0.0.1:{api_port}",
            "PRODUCT_LOG_DIRECTORY": str(temporary_directory / "diagnostics"),
        }
    )
    return environment
