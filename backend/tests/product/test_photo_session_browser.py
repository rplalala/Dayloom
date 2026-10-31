"""Chromium session-cache checks against real Product UI and controlled HTTP boundaries.

No database, planner execution, provider credentials or external requests are used.
Enable with PRODUCT_BROWSER_TESTS=1. Only the local Vite process is started.
"""

import json
import os
import subprocess
import time
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from playwright.sync_api import expect, sync_playwright
from pydantic import SecretStr

from backend.tests.product.browser_harness import IsolatedBrowser, isolated_environment

ROOT = Path(__file__).resolve().parents[3]
CACHE = "dayloom.photos.session.v1"


@pytest.fixture(scope="module")
def photo_browser(tmp_path_factory):
    if os.environ.get("PRODUCT_BROWSER_TESTS") != "1":
        pytest.skip("Enable controlled Chromium checks with PRODUCT_BROWSER_TESTS=1")
    scratch = tmp_path_factory.mktemp("photo-session")
    port = os.environ.get("PRODUCT_PHOTO_TEST_WEB_PORT", "5123")
    base = f"http://localhost:{port}"
    # No API is started; every /api request is intercepted before navigation.
    env = isolated_environment(
        SecretStr("postgresql://unused@localhost/unused_test"), "9", port, scratch
    )
    with (scratch / "vite.log").open("w", encoding="utf-8") as output:
        process = subprocess.Popen(
            [
                "node",
                str(ROOT / "frontend/node_modules/vite/bin/vite.js"),
                "--host",
                "127.0.0.1",
                "--port",
                port,
                "--strictPort",
            ],
            cwd=ROOT / "frontend",
            env=env,
            stdout=output,
            stderr=subprocess.STDOUT,
        )
        try:
            deadline = time.monotonic() + 30
            while True:
                try:
                    if httpx.get(base, timeout=1).status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                if process.poll() is not None or time.monotonic() > deadline:
                    raise AssertionError("Controlled photo-test Vite server did not start")
                time.sleep(0.1)
            with patch.dict(os.environ, env, clear=True), sync_playwright() as playwright:
                browser = IsolatedBrowser(playwright.chromium.launch(env=env))
                try:
                    yield base, browser
                finally:
                    browser.close()
        finally:
            process.terminate()
            process.wait(timeout=10)


class PhotoBoundary:
    def __init__(self, context, private=False):
        self.private = private
        self.authorized = True
        self.batches = []
        self.detail_reads = 0
        self.detail = {
            "schema_version": "product_detail_1",
            "id": "photo-fixture",
            "title": "Photo session fixture",
            "destination": "Sydney",
            "provenance": "generated" if private else "example",
            "trust": "generated_projection" if private else "source_fixture",
            "request": None,
            "days": [
                {
                    "date": "2026-10-31",
                    "activities": [
                        {
                            "activity_id": f"stop-{i}",
                            "title": f"Fixture place {i}",
                            "time_use": "scheduled",
                            "start_time": "2026-10-31T10:00:00+11:00",
                            "end_time": "2026-10-31T11:00:00+11:00",
                        }
                        for i in range(20)
                    ],
                }
            ],
            "transfers": [],
            "nearby": [],
        }
        context.route("**/api/**", self.respond)

    @property
    def path(self):
        return "/trips/photo-fixture" if self.private else "/examples/photo-fixture"

    def respond(self, route):
        parsed = urlsplit(route.request.url)
        path = parsed.path
        if not path.startswith("/api/"):
            return route.fallback()
        status = 200
        if path == "/api/auth/current":
            if self.private and self.authorized:
                body = {
                    "id": "alice",
                    "email": "alice@example.com",
                    "display_name": "Alice",
                    "initials": "A",
                    "csrf_token": "controlled-test-csrf",
                }
            else:
                status, body = 401, {"detail": {"code": "session_expired"}}
        elif path == "/api" + self.path:
            self.detail_reads += 1
            status, body = (200, self.detail) if self.authorized else (404, {})
        elif path == "/api" + self.path + "/media":
            slots = parse_qs(parsed.query).get("slot", [])
            self.batches.append(slots)
            body = {
                "items": {
                    slot: {
                        "status": "available",
                        "kind": "verified_place",
                        "provider": "Google Maps",
                        "image_url": f"https://lh3.googleusercontent.com/fixture/{slot}",
                        "authors": [
                            {
                                "name": "Fixture photographer",
                                "url": "https://www.google.com/maps/contrib/123",
                            }
                        ],
                        "source_url": "https://www.google.com/maps/photo/fixture",
                    }
                    for slot in slots
                }
            }
        elif path == "/api/planning/tasks":
            body = []
        else:
            body = {"status": "unavailable"}
        route.fulfill(status=status, content_type="application/json", body=json.dumps(body))


def available_photos(page):
    return page.locator('.activity-photo[data-photo-state="available"]')


def test_reload_hits_partial_misses_expiry_and_credits(photo_browser):
    base, browser = photo_browser
    context = browser.new_context()
    try:
        boundary = PhotoBoundary(context)
        page = context.new_page()
        page.goto(base + boundary.path)
        expect(available_photos(page)).to_have_count(20)
        assert [len(batch) for batch in boundary.batches] == [12, 8]
        reads_before_reload = boundary.detail_reads
        boundary.batches.clear()
        page.reload()
        expect(available_photos(page)).to_have_count(20)
        assert boundary.batches == []
        assert boundary.detail_reads > reads_before_reload
        page.get_by_role("button", name="View Fixture place 0", exact=True).click()
        dialog = page.get_by_role("dialog")
        expect(dialog.get_by_role("link", name="Fixture photographer")).to_be_visible()
        expect(dialog.get_by_role("link", name="Photo source")).to_have_attribute(
            "href", "https://www.google.com/maps/photo/fixture"
        )
        page.keyboard.press("Escape")
        page.evaluate(
            """key => {
            const saved = JSON.parse(sessionStorage.getItem(key));
            saved.entries.splice(0, 2);
            sessionStorage.setItem(key, JSON.stringify(saved));
        }""",
            CACHE,
        )
        page.reload()
        expect(available_photos(page)).to_have_count(20)
        assert sum(map(len, boundary.batches)) == 2
        boundary.batches.clear()
        page.evaluate(
            """key => {
            const saved = JSON.parse(sessionStorage.getItem(key));
            saved.entries.forEach(entry => { entry.fetchedAt -= 1800000; });
            sessionStorage.setItem(key, JSON.stringify(saved));
        }""",
            CACHE,
        )
        page.reload()
        expect(available_photos(page)).to_have_count(20)
        assert sum(map(len, boundary.batches)) == 20
    finally:
        context.close()


def test_closed_tab_new_tab_and_restored_expired_session(photo_browser):
    base, browser = photo_browser
    context = browser.new_context()
    try:
        boundary = PhotoBoundary(context)
        page = context.new_page()
        page.goto(base + boundary.path)
        expect(available_photos(page)).to_have_count(20)
        restored = page.evaluate("key => sessionStorage.getItem(key)", CACHE)
        page.close()
        boundary.batches.clear()
        page = context.new_page()
        page.goto(base + boundary.path)
        expect(available_photos(page)).to_have_count(20)
        assert sum(map(len, boundary.batches)) == 20
        # Simulate browser session restoration: storage can return, but fixed TTL still applies.
        saved = json.loads(restored)
        for entry in saved["entries"]:
            entry["fetchedAt"] -= 1800000
        page.evaluate(
            "([key, data]) => sessionStorage.setItem(key, data)", [CACHE, json.dumps(saved)]
        )
        boundary.batches.clear()
        page.reload()
        expect(available_photos(page)).to_have_count(20)
        assert sum(map(len, boundary.batches)) == 20
    finally:
        context.close()


def test_broken_cached_photo_has_one_slot_retry_then_manual_recovery(photo_browser):
    base, browser = photo_browser
    context = browser.new_context()
    try:
        boundary = PhotoBoundary(context)
        page = context.new_page()
        page.goto(base + boundary.path)
        expect(available_photos(page)).to_have_count(20)
        boundary.batches.clear()
        page.route(
            "https://lh3.googleusercontent.com/**stop-0", lambda route: route.fulfill(status=404)
        )
        page.reload()
        expect(available_photos(page)).to_have_count(19)
        expect(page.get_by_role("button", name="Retry photo", exact=True)).to_have_count(1)
        assert boundary.batches == [["activity:stop-0"]]
        page.unroute("https://lh3.googleusercontent.com/**stop-0")
        page.get_by_role("button", name="Retry photo", exact=True).click()
        expect(available_photos(page)).to_have_count(20)
        assert boundary.batches == [["activity:stop-0"], ["activity:stop-0"]]
    finally:
        context.close()


def test_private_cache_never_bypasses_authentication_or_detail_ownership(photo_browser):
    base, browser = photo_browser
    context = browser.new_context()
    try:
        boundary = PhotoBoundary(context, private=True)
        page = context.new_page()
        page.goto(base + boundary.path)
        expect(available_photos(page)).to_have_count(20)
        boundary.batches.clear()
        boundary.authorized = False
        page.reload()
        expect(
            page.get_by_role("heading", name="Log in to view your saved itinerary.")
        ).to_be_visible()
        expect(available_photos(page)).to_have_count(0)
        assert boundary.batches == []
        assert (
            page.evaluate("key => JSON.parse(sessionStorage.getItem(key)).entries.length", CACHE)
            == 0
        )
        boundary.authorized = True
        context.route(
            "**/api/trips/photo-fixture", lambda route: route.fulfill(status=404, body="{}")
        )
        page.reload()
        expect(
            page.get_by_role("heading", name="This saved itinerary is unavailable.")
        ).to_be_visible()
        expect(available_photos(page)).to_have_count(0)
        assert boundary.batches == []
    finally:
        context.close()
