"""Real editor/browser/API/PostgreSQL journey with external GeoDB/model substitutes."""

import os
import re
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
import jwt
import pytest
from playwright.sync_api import expect, sync_playwright
from pydantic import SecretStr

from backend.tests.product.browser_harness import (
    BROWSER_TEST_SIGNING_KEY,
    BrowserApplication,
    isolated_environment,
)
from backend.tests.product.database_safety import require_test_database

ROOT = Path(__file__).resolve().parents[3]
SCRATCH = ROOT / ".scratch" / "editor-browser"


@pytest.fixture(scope="module")
def editor_app():
    dsn = SecretStr(os.environ.get("PRODUCT_TEST_DATABASE_URL", ""))
    if os.environ.get("PRODUCT_BROWSER_TESTS") != "1" or not dsn.get_secret_value():
        pytest.skip("Enable browser acceptance with an explicitly isolated Product test database")
    require_test_database(dsn)
    SCRATCH.mkdir(parents=True, exist_ok=True)
    api_port = os.environ.get("PRODUCT_TEST_API_PORT", "8199")
    web_port = os.environ.get("PRODUCT_TEST_WEB_PORT", "5199")
    base = f"http://localhost:{web_port}"
    environment = isolated_environment(dsn, api_port, web_port, SCRATCH / "tmp")
    subprocess.run(
        [sys.executable, "scripts/migrate_product.py"], cwd=ROOT, env=environment, check=True
    )
    processes, outputs = [], []
    try:
        for name, command, directory in [
            (
                "api",
                [sys.executable, "-m", "backend.tests.product.editor_server", "--port", api_port],
                ROOT,
            ),
            (
                "vite",
                [
                    "node",
                    str(ROOT / "frontend/node_modules/vite/bin/vite.js"),
                    "--host",
                    "127.0.0.1",
                    "--port",
                    web_port,
                    "--strictPort",
                ],
                ROOT / "frontend",
            ),
        ]:
            output = (SCRATCH / f"{name}.log").open("w", encoding="utf-8")
            outputs.append(output)
            processes.append(
                subprocess.Popen(
                    command, cwd=directory, env=environment, stdout=output, stderr=subprocess.STDOUT
                )
            )
        for endpoint in [f"http://127.0.0.1:{api_port}/health", f"http://127.0.0.1:{web_port}"]:
            deadline = time.monotonic() + 30
            while True:
                try:
                    if httpx.get(endpoint, timeout=1).status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                if time.monotonic() > deadline:
                    raise AssertionError(f"Local editor server did not start: {endpoint}")
                time.sleep(0.1)
        with patch.dict(os.environ, environment, clear=True):
            playwright = sync_playwright().start()
        try:
            browser = playwright.chromium.launch(env=environment)
            try:
                yield BrowserApplication(base, browser)
            finally:
                browser.close()
        finally:
            playwright.stop()
    finally:
        for process in processes:
            process.terminate()
        for process in processes:
            process.wait(timeout=10)
        for output in outputs:
            output.close()


@pytest.mark.parametrize("replacement", ["paste", "type"])
def test_manual_identical_replacement_detaches_owned_text(editor_app, replacement):
    context = editor_app.browser.new_context(permissions=["clipboard-read", "clipboard-write"])
    page = context.new_page()
    try:
        page.goto(editor_app.base_url + "/plan")
        nature = page.get_by_role("button", name="Nature", exact=True)
        nature.click()
        notes = page.get_by_label("Additional preferences")
        original = "Enjoy parks, waterfronts and gentle outdoor experiences."
        expect(notes).to_have_value(original)
        notes.focus()
        notes.press("Control+A")
        if replacement == "paste":
            notes.press("Control+C")
            notes.press("Control+V")
        else:
            page.keyboard.insert_text(original)
        expect(notes).to_have_value(original)
        expect(nature).to_have_attribute("aria-pressed", "false")
        nature.click()
        nature.click()
        expect(notes).to_have_value(original)
    finally:
        context.close()


@pytest.mark.parametrize(
    "width,time_zone",
    [(390, "Pacific/Kiritimati"), (800, "America/Los_Angeles"), (1440, "Australia/Sydney")],
)
def test_complete_editor_journey(editor_app, width, time_zone):
    context = editor_app.browser.new_context(
        viewport={"width": width, "height": 1000}, timezone_id=time_zone
    )
    page = context.new_page()
    page.set_default_timeout(5000)
    generation = []
    page.on(
        "request",
        lambda request: (
            generation.append(request.url)
            if request.method == "POST" and urlsplit(request.url).path.startswith("/api/planning")
            else None
        ),
    )
    try:
        page.goto(editor_app.base_url + "/plan")
        destination = page.get_by_label("Destination", exact=True)
        destination.fill("Kyo")
        page.get_by_role("option", name="Kyoto, Kyoto Prefecture, Japan").click()
        expect(destination).to_have_value("Kyoto, Kyoto Prefecture, Japan")
        window = page.request.get(editor_app.base_url + "/api/planning/date-window").json()
        page.get_by_label("Start date", exact=True).fill(window["allowedStart"])
        page.get_by_label("End date", exact=True).fill(window["allowedStart"])
        page.get_by_label("Travelers", exact=True).fill("2")
        page.get_by_label("Whole-trip budget", exact=True).fill("0")
        page.get_by_label("Currency", exact=True).select_option("CAD")
        page.get_by_label("Places or experiences to include").fill("An art museum")
        page.get_by_label("Places or experiences to avoid").fill("Large malls")
        notes = page.get_by_label("Additional preferences")
        notes.fill("My own sentence.\n")
        nature = page.get_by_role("button", name="Nature", exact=True)
        nature.click()
        relaxed = page.get_by_role("button", name="Take it slowly Relaxed")
        balanced = page.get_by_role("button", name="A little of both Balanced")
        relaxed.click()
        balanced.click()
        expect(relaxed).to_have_attribute("aria-pressed", "false")
        expect(balanced).to_have_attribute("aria-pressed", "true")
        balanced.click()
        expect(balanced).to_have_attribute("aria-pressed", "false")
        walk = page.get_by_role("button", name="Walking", exact=True)
        transit = page.get_by_role("button", name="Public transit", exact=True)
        walk.click()
        transit.click()
        expect(notes).to_have_value(
            re.compile("Prefer walking and public transit where practical\\.")
        )
        walk.click()
        transit.click()
        original = notes.input_value().replace("parks", "quiet parks")
        notes.fill(original)
        expect(nature).to_have_attribute("aria-pressed", "false")
        # A manually identical sentence is never owned or removed by a control.
        notes.fill(original + "\nEnjoy parks, waterfronts and gentle outdoor experiences.")
        nature.click()
        nature.click()
        expect(notes).to_have_value(
            original + "\nEnjoy parks, waterfronts and gentle outdoor experiences."
        )
        photography = page.get_by_role("button", name="Photography", exact=True)
        photography.click()
        photo_sentence = "Include scenic viewpoints and time for photography."
        photo_start = notes.input_value().index(photo_sentence)
        notes.press("Control+End")
        notes.press("Enter")
        notes.press_sequentially(photo_sentence)
        expect(photography).to_have_attribute("aria-pressed", "true")
        notes.evaluate(
            "(node, range) => node.setSelectionRange(range[0], range[1])",
            [photo_start, photo_start + len(photo_sentence) + 1],
        )
        notes.press("Backspace")
        expect(photography).to_have_attribute("aria-pressed", "false")
        photography.click()
        photography.click()
        expect(notes).to_have_value(re.compile(re.escape(photo_sentence)))
        notes.fill("  " + notes.input_value() + "\n")
        balanced.click()
        original = notes.input_value()
        page.get_by_role("button", name="Polish preferences", exact=True).click()
        expect(page.get_by_role("heading", name="Suggested rewrite")).to_be_visible()
        expect(notes).to_have_value(original)
        page.get_by_role("button", name="Dismiss", exact=True).click()
        expect(notes).to_have_value(original)
        page.get_by_role("button", name="Polish preferences", exact=True).click()
        page.get_by_role("button", name="Apply rewrite", exact=True).click()
        expect(notes).to_have_value(
            original.replace("quiet parks", "peaceful parks").replace(
                "time to rest", "unhurried breaks"
            )
        )
        expect(balanced).to_have_attribute("aria-pressed", "false")
        page.get_by_role("button", name="Undo rewrite", exact=True).click()
        expect(notes).to_have_value(original)
        expect(balanced).to_have_attribute("aria-pressed", "false")
        # Delay the actual bounded API response; a later edit must fence its preview.
        delayed = []
        page.route(
            "**/api/input-assistance/preferences/polish",
            lambda route: delayed.append(route),
        )
        page.get_by_role("button", name="Polish preferences", exact=True).click()
        page.wait_for_function(
            "document.querySelector('.preference-assistance button')"
            ".textContent.includes('Polishing')"
        )
        assert delayed
        response = delayed[0].fetch()
        notes.fill(original + "\nNewer text wins.")
        delayed[0].fulfill(response=response)
        expect(page.get_by_role("button", name="Apply rewrite", exact=True)).to_have_count(0)
        expect(notes).to_have_value(original + "\nNewer text wins.")
        expect(page.get_by_role("button", name="Polish preferences", exact=True)).to_be_disabled()
        page.unroute("**/api/input-assistance/preferences/polish")
        # Tab recovery retains all fields/metadata and performs no generation.
        relaxed.click()
        page.reload()
        expect(page.get_by_role("button", name="Take it slowly Relaxed")).to_have_attribute(
            "aria-pressed", "true"
        )
        expect(page.get_by_label("Places or experiences to include")).to_have_value("An art museum")
        page.get_by_role("button", name="Generate itinerary").click()
        page.get_by_role("tab", name="Sign up").click()
        page.get_by_label("Display name").fill("Editor Traveler")
        email = f"editor-{uuid4()}@example.com"
        page.get_by_label("Email address").fill(email)
        page.get_by_label("Password", exact=True).fill("a secure password")
        page.get_by_label("Confirm password").fill("a secure password")
        page.get_by_role("button", name="Create account", exact=True).click()
        expect(page.get_by_label("Start date", exact=True)).to_have_value(window["allowedStart"])
        page.get_by_label("Start date", exact=True).fill("2026-02-30")
        page.get_by_role("button", name="Generate itinerary").click()
        expect(page.get_by_role("alert")).to_contain_text("Enter real dates")
        page.get_by_label("Start date", exact=True).fill(window["allowedStart"])
        page.get_by_label("Travelers", exact=True).fill("1.5")
        page.get_by_role("button", name="Generate itinerary").click()
        expect(page.get_by_role("alert")).to_contain_text("whole number of travelers")
        page.get_by_label("Travelers", exact=True).fill("2")
        page.get_by_role("button", name="Generate itinerary").click()
        expect(page.get_by_role("status")).to_contain_text("Your brief is ready")
        page.reload()  # A new editor allowance avoids racing a just-sent recovered-city lookup.
        destination.fill("Unavailable city")
        expect(
            page.get_by_text("Suggestions are unavailable. You can enter a destination manually.")
        ).to_be_visible()
        expect(destination).to_have_value("Unavailable city")
        assert not generation
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        pair = page.locator(".preference-pair > fieldset")
        first, second = pair.nth(0).bounding_box(), pair.nth(1).bounding_box()
        assert first and second
        assert second["y"] > first["y"] if width <= 800 else abs(second["y"] - first["y"]) < 2
        page.screenshot(path=str(SCRATCH / f"editor-{width}.png"), full_page=True)
        # Extended editor metadata is quarantined and restored only for the same account.
        cookie = next(value for value in context.cookies() if value["name"] == "dayloom_session")
        claims = jwt.decode(cookie["value"], options={"verify_signature": False})
        claims["exp"] = datetime.now(UTC) - timedelta(seconds=1)
        cookie["value"] = jwt.encode(claims, BROWSER_TEST_SIGNING_KEY, algorithm="HS256")
        context.add_cookies([cookie])
        page.evaluate("window.dispatchEvent(new Event('focus'))")
        expect(page.get_by_role("heading", name="Log in to continue your brief.")).to_be_visible()
        expect(page.get_by_label("Places or experiences to include")).to_have_count(0)
        expect(page.get_by_role("button", name="Take it slowly Relaxed")).to_have_count(0)
        page.get_by_role("link", name="Log in", exact=True).last.click()
        page.get_by_label("Email address").fill(email)
        page.get_by_label("Password", exact=True).fill("a secure password")
        page.get_by_role("button", name="Log in", exact=True).click()
        expect(page.get_by_label("Places or experiences to include")).to_have_value("An art museum")
        expect(page.get_by_role("button", name="Take it slowly Relaxed")).to_have_attribute(
            "aria-pressed", "true"
        )
        page.goto(editor_app.base_url + "/account")
        page.get_by_role("button", name="Log out", exact=True).click()
        page.goto(editor_app.base_url + "/plan")
        expect(page.get_by_label("Places or experiences to include")).to_have_value("")
        expect(page.get_by_label("Additional preferences")).to_have_value("")
        expect(page.get_by_role("button", name="Take it slowly Relaxed")).to_have_attribute(
            "aria-pressed", "false"
        )
        assert not generation
    finally:
        context.close()
