"""Real browser -> Vite -> FastAPI -> isolated PostgreSQL account journeys.

Set PRODUCT_TEST_DATABASE_URL and PRODUCT_BROWSER_TESTS=1. External services are unused.
All transient processes, screenshots and logs belong to this worktree's .scratch.
"""

import os
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
SCRATCH = ROOT / ".scratch" / "browser"


@pytest.fixture(scope="module")
def browser_app():
    dsn = SecretStr(os.environ.get("PRODUCT_TEST_DATABASE_URL", ""))
    if os.environ.get("PRODUCT_BROWSER_TESTS") != "1" or not dsn.get_secret_value():
        pytest.skip("Enable browser acceptance with an explicitly isolated Product test database")
    require_test_database(dsn)
    SCRATCH.mkdir(parents=True, exist_ok=True)
    api_port = os.environ.get("PRODUCT_TEST_API_PORT", "8120")
    web_port = os.environ.get("PRODUCT_TEST_WEB_PORT", "5120")
    base = f"http://localhost:{web_port}"
    env = isolated_environment(dsn, api_port, web_port, SCRATCH / "tmp")
    subprocess.run([sys.executable, "scripts/migrate_product.py"], cwd=ROOT, env=env, check=True)
    processes = []
    outputs = []
    try:
        for name, command in [
            (
                "api",
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "backend.app.main:create_app",
                    "--factory",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    api_port,
                ],
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
            ),
        ]:
            output = (SCRATCH / f"{name}.log").open("w", encoding="utf-8")
            outputs.append(output)
            processes.append(
                subprocess.Popen(
                    command,
                    cwd=ROOT / "frontend" if name == "vite" else ROOT,
                    env=env,
                    stdout=output,
                    stderr=subprocess.STDOUT,
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
                    raise AssertionError(f"Local acceptance server did not start: {endpoint}")
                time.sleep(0.1)
        # The driver starts under the same allowlist; browser launch receives it explicitly.
        with patch.dict(os.environ, env, clear=True):
            playwright = sync_playwright().start()
        try:
            browser = playwright.chromium.launch(env=env)
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


def login(page, email):
    page.get_by_label("Email address").fill(email)
    page.get_by_label("Password", exact=True).fill("a secure password")
    page.get_by_role("button", name="Log in", exact=True).click()


def register_browser(page, base):
    email = f"browser-{uuid4()}@example.com"
    page.goto(base + "/login")
    page.get_by_role("tab", name="Sign up").click()
    page.get_by_label("Display name").fill("Alice Smith")
    page.get_by_label("Email address").fill(email)
    page.get_by_label("Password", exact=True).fill("a secure password")
    page.get_by_label("Confirm password").fill("a secure password")
    page.get_by_role("button", name="Create account", exact=True).click()
    expect(page.get_by_role("heading", name="My trips", exact=True)).to_be_visible()
    return email


def test_logout_invalidation_survives_product_unmount_and_later_login(browser_app):
    base, browser = browser_app.base_url, browser_app.browser
    context = browser.new_context()
    try:
        first = context.new_page()
        email = register_browser(first, base)
        first.goto(base + "/plan")
        first.get_by_label("Additional preferences").fill("Never restore after explicit logout")
        first.get_by_role("button", name="Generate itinerary").click()
        old_action = first.evaluate(
            "JSON.parse(sessionStorage.getItem('dayloom.editor.v1')).actionId"
        )
        assert old_action
        first.goto(base + "/dev")
        second = context.new_page()
        second.goto(base + "/account")
        second.get_by_role("button", name="Log out", exact=True).click()
        expect(second.get_by_role("link", name="Log in", exact=True).last).to_be_visible()
        second.goto(base + "/login")
        login(second, email)
        expect(second.get_by_role("heading", name="My trips", exact=True)).to_be_visible()
        first.goto(base + "/plan")
        expect(first.get_by_label("Additional preferences")).to_have_value("")
        assert (
            first.evaluate("JSON.parse(sessionStorage.getItem('dayloom.editor.v1')).actionId")
            is None
        )
    finally:
        context.close()


@pytest.mark.parametrize("lost_response", [False, True])
def test_logout_fences_current_response_and_focus_until_completion(browser_app, lost_response):
    base, browser = browser_app.base_url, browser_app.browser
    context = browser.new_context()
    try:
        page = context.new_page()
        register_browser(page, base)
        page.goto(base + "/account")
        expect(page.get_by_role("button", name="Log out", exact=True)).to_be_visible()
        currents, logouts = [], []

        def hold_current(route):
            currents.append((route, route.fetch()))

        page.route("**/api/auth/current", hold_current)
        page.route("**/api/auth/logout", lambda route: logouts.append(route))

        def barrier(route):
            for current, response in currents:
                current.fulfill(response=response)
            currents.clear()
            route.continue_()

        page.route("**/health?logout-barrier", barrier)
        with page.expect_request("**/api/auth/logout"):
            page.get_by_role("button", name="Log out", exact=True).click()
        page.evaluate("""async () => {
            window.dispatchEvent(new Event('focus'));
            await fetch('/health?logout-barrier');
            await new Promise(requestAnimationFrame);
        }""")
        assert logouts
        response = logouts[0].fetch()  # The real API commits global revocation in PostgreSQL.
        assert response.status == 204
        if lost_response:
            logouts[0].abort()
            expect(page.get_by_role("alert")).to_contain_text("Could not end the server session")
        else:
            logouts[0].fulfill(response=response)
        expect(page.get_by_role("button", name="Log out", exact=True)).to_have_count(0)
        expect(page.get_by_text("Alice Smith", exact=True)).to_have_count(0)
        page.unroute("**/api/auth/current")
        page.evaluate("window.dispatchEvent(new Event('focus'))")
        expect(page.get_by_role("button", name="Log out", exact=True)).to_have_count(0)
        page.reload()
        expect(page.get_by_role("button", name="Log out", exact=True)).to_have_count(0)
    finally:
        context.close()


def test_guest_auth_expiry_restore_account_switch_and_cross_tab_logout(browser_app):
    base, browser = browser_app.base_url, browser_app.browser
    context = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = context.new_page()
    generation = []
    page.on(
        "request",
        lambda request: (
            generation.append(request.url)
            if urlsplit(request.url).path.startswith("/api/planning")
            else None
        ),
    )
    try:
        page.goto(base)
        expect(
            page.get_by_role("heading", name="So much to discover. So easy to plan.")
        ).to_be_visible()
        page.screenshot(path=str(SCRATCH / "home-desktop.png"), full_page=True)
        page.goto(base + "/trips")
        expect(page.get_by_role("link", name="View itinerary →")).to_have_count(3)
        page.goto(base + "/plan")
        page.get_by_label("Destination", exact=True).fill("Kyoto")
        page.get_by_label("Additional preferences").fill("Private slow mornings")
        page.get_by_role("button", name="Generate itinerary").click()
        expect(page.get_by_role("heading", name="Welcome back.")).to_be_visible()
        page.screenshot(path=str(SCRATCH / "auth-desktop.png"), full_page=True)
        page.get_by_role("tab", name="Sign up").click()
        email = f"browser-{uuid4()}@example.com"
        page.get_by_label("Display name").fill("Alice Smith")
        page.get_by_label("Email address").fill(email)
        page.get_by_label("Password", exact=True).fill("a secure password")
        page.get_by_label("Confirm password").fill("a secure password")
        page.get_by_role("button", name="Create account", exact=True).click()
        expect(page.get_by_label("Destination", exact=True)).to_have_value("Kyoto")
        assert not generation
        page.goto(base + "/trips")
        expect(
            page.get_by_text("No trips yet. Start with an idea and make it yours.")
        ).to_be_visible()
        expect(page.get_by_text("EXAMPLE · SYDNEY", exact=True)).to_have_count(0)
        page.goto(base + "/plan")
        page.get_by_label("Additional preferences").fill("Quarantined account-only input")
        page.screenshot(path=str(SCRATCH / "brief-desktop.png"), full_page=True)
        cookies = context.cookies()
        cookie = next(c for c in cookies if c["name"] == "dayloom_session")
        assert cookie["httpOnly"] is True
        claims = jwt.decode(cookie["value"], options={"verify_signature": False})
        claims["exp"] = datetime.now(UTC) - timedelta(seconds=1)
        cookie["value"] = jwt.encode(claims, BROWSER_TEST_SIGNING_KEY, algorithm="HS256")
        context.add_cookies([cookie])
        page.evaluate("window.dispatchEvent(new Event('focus'))")
        expect(page.get_by_role("heading", name="Log in to continue your brief.")).to_be_visible()
        expect(page.get_by_label("Additional preferences")).to_have_count(0)
        page.get_by_role("link", name="Log in", exact=True).last.click()
        login(page, email)
        expect(page.get_by_label("Additional preferences")).to_have_value(
            "Quarantined account-only input"
        )
        assert not generation
        other = context.new_page()
        other.goto(base + "/plan")
        other.get_by_label("Additional preferences").fill("Second tab private input")
        page.goto(base + "/account")
        page.get_by_role("button", name="Log out", exact=True).click()
        expect(other.get_by_label("Additional preferences")).to_have_value("")
        page.goto(base + "/plan")
        expect(page.get_by_label("Additional preferences")).to_have_value("")
        page.get_by_role("button", name="Generate itinerary").click()
        page.get_by_role("tab", name="Sign up").click()
        page.get_by_label("Display name").fill("Bob Jones")
        page.get_by_label("Email address").fill(f"browser-{uuid4()}@example.com")
        page.get_by_label("Password", exact=True).fill("a secure password")
        page.get_by_label("Confirm password").fill("a secure password")
        page.get_by_role("button", name="Create account", exact=True).click()
        expect(page.get_by_label("Additional preferences")).to_have_value("")
        page.get_by_label("Additional preferences").fill("Bob account-only input")
        bob_cookie = next(c for c in context.cookies() if c["name"] == "dayloom_session")
        bob_claims = jwt.decode(bob_cookie["value"], options={"verify_signature": False})
        bob_claims["exp"] = datetime.now(UTC) - timedelta(seconds=1)
        bob_cookie["value"] = jwt.encode(bob_claims, BROWSER_TEST_SIGNING_KEY, algorithm="HS256")
        context.add_cookies([bob_cookie])
        page.evaluate("window.dispatchEvent(new Event('focus'))")
        expect(page.get_by_role("heading", name="Log in to continue your brief.")).to_be_visible()
        page.get_by_role("link", name="Log in", exact=True).last.click()
        login(page, email)
        expect(page.get_by_label("Additional preferences")).to_have_value("")
        page.get_by_label("Additional preferences").fill("Input before confirmed revocation")
        other.goto(base + "/plan")
        other.get_by_label("Additional preferences").fill("Other tab before revocation")
        # Revoke through a separate API client: no browser logout notification is sent.
        token = next(c["value"] for c in context.cookies() if c["name"] == "dayloom_session")
        response = httpx.post(
            base.replace("localhost", "127.0.0.1") + "/api/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 204
        page.evaluate("window.dispatchEvent(new Event('focus'))")
        expect(page.get_by_label("Additional preferences")).to_have_value("")
        expect(other.get_by_label("Additional preferences")).to_have_value("")
        assert not generation
        for width in [390, 800]:
            page.set_viewport_size({"width": width, "height": 1000})
            page.screenshot(path=str(SCRATCH / f"brief-{width}.png"), full_page=True)
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        page.goto(base + "/dev")
        expect(page.get_by_text("Local development and research")).to_be_visible()
    finally:
        context.close()
