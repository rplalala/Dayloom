"""Profile changes and visible defaults through actual browser/API/PostgreSQL."""
# Reuse the credential-safe browser fixture at the real application boundary.
# ruff: noqa: F811

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import jwt
import pytest
from playwright.sync_api import expect

from backend.tests.product.browser_harness import BROWSER_TEST_SIGNING_KEY
from backend.tests.product.test_browser import login, register_browser
from backend.tests.product.test_editor_browser import editor_app  # noqa: F401

SCRATCH = Path(__file__).resolve().parents[3] / ".scratch" / "profile-browser"


def test_profile_edit_persists_and_prefills_only_new_brief(editor_app):
    SCRATCH.mkdir(parents=True, exist_ok=True)
    base, browser = editor_app.base_url, editor_app.browser
    context = browser.new_context(viewport={"width": 1440, "height": 1000})
    email = f"profile-{uuid4()}@example.com"
    try:
        page = context.new_page()
        page.goto(base + "/login")
        page.get_by_role("tab", name="Sign up").click()
        page.get_by_label("Display name").fill("Alice Smith")
        page.get_by_label("Email address").fill(email)
        page.get_by_label("Password", exact=True).fill("a secure password")
        page.get_by_label("Confirm password").fill("a secure password")
        page.get_by_role("button", name="Create account", exact=True).click()
        expect(page.get_by_role("heading", name="My trips", exact=True)).to_be_visible()
        page.goto(base + "/account")
        page.get_by_label("Display name").fill("Ada Lovelace")
        page.get_by_label("Default currency").select_option("JPY")
        page.get_by_role("button", name="Nature", exact=True).click()
        page.get_by_role("button", name="Relaxed", exact=True).click()
        page.get_by_role("button", name="Walking", exact=True).click()
        page.get_by_role("button", name="Public transit", exact=True).click()
        page.get_by_label("Additional preferences").fill("  Quiet mornings.\nKeep my wording. ")
        page.get_by_role("button", name="Save changes", exact=True).click()
        expect(page.get_by_role("status")).to_have_text("Your travel defaults have been saved.")
        expect(page.get_by_label("Account initials: AL")).to_be_visible()
        assert page.locator('input[type="file"]').count() == 0
        expect(page.get_by_role("button", name="Nature", exact=True)).to_have_attribute(
            "aria-pressed", "true"
        )
        assert page.get_by_text("Profile and travel defaults", exact=True).evaluate(
            "node => node.getBoundingClientRect().width <= 1"
        )
        page.evaluate("scrollTo(0, 0)")
        page.screenshot(path=str(SCRATCH / "account-1440.png"), full_page=True)
        page.reload()
        expect(page.get_by_label("Default currency")).to_have_value("JPY")
        for width in [800, 390]:
            page.set_viewport_size({"width": width, "height": 1000})
            page.evaluate("scrollTo(0, 0)")
            page.screenshot(path=str(SCRATCH / f"account-{width}.png"), full_page=True)
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.goto(base + "/plan")
        expect(page.get_by_label("Currency")).to_have_value("JPY")
        expect(page.get_by_role("button", name="Nature", exact=True)).to_have_attribute(
            "aria-pressed", "true"
        )
        expect(page.get_by_label("Additional preferences")).to_contain_text(
            "Prefer walking and public transit where practical."
        )
        page.get_by_label("Additional preferences").fill("My existing brief")
        page.goto(base + "/account")
        page.get_by_label("Default currency").select_option("USD")
        page.get_by_label("Additional preferences").fill("New defaults only")
        page.get_by_role("button", name="Save changes", exact=True).click()
        expect(page.get_by_role("status")).to_have_text("Your travel defaults have been saved.")
        page.goto(base + "/plan")
        expect(page.get_by_label("Currency")).to_have_value("JPY")
        expect(page.get_by_label("Additional preferences")).to_have_value("My existing brief")
        page.reload()
        expect(page.get_by_label("Additional preferences")).to_have_value("My existing brief")
    finally:
        context.close()
    fresh = browser.new_context(viewport={"width": 390, "height": 1000})
    try:
        page = fresh.new_page()
        page.goto(base + "/login?return=/plan")
        login(page, email)
        expect(page.get_by_label("Currency")).to_have_value("USD")
        expect(page.get_by_label("Additional preferences")).to_contain_text("New defaults only")
        page.evaluate("scrollTo(0, 0)")
        page.screenshot(path=str(SCRATCH / "new-brief-390.png"), full_page=True)
    finally:
        fresh.close()


@pytest.mark.parametrize("operation", ["load", "save"])
def test_expired_profile_response_hides_private_data_and_restores_brief(editor_app, operation):
    base, browser = editor_app.base_url, editor_app.browser
    context = browser.new_context()
    try:
        page = context.new_page()
        email = register_browser(page, base)
        page.get_by_role("link", name="Account settings", exact=True).click()
        page.get_by_label("Additional preferences").fill("Persisted profile notes")
        page.get_by_role("button", name="Save changes", exact=True).click()
        expect(page.get_by_role("status")).to_have_text("Your travel defaults have been saved.")
        page.get_by_role("link", name="Plan a trip", exact=True).click()
        page.get_by_label("Additional preferences").fill("Private unsaved brief to recover")
        if operation == "save":
            page.get_by_role("link", name="Account settings", exact=True).click()
            expect(page.get_by_label("Additional preferences")).to_have_value(
                "Persisted profile notes"
            )
        cookie = next(c for c in context.cookies() if c["name"] == "dayloom_session")
        claims = jwt.decode(cookie["value"], options={"verify_signature": False})
        claims["exp"] = datetime.now(UTC) - timedelta(seconds=1)
        cookie["value"] = jwt.encode(claims, BROWSER_TEST_SIGNING_KEY, algorithm="HS256")
        context.add_cookies([cookie])
        writes = []
        page.on(
            "request",
            lambda request: (
                writes.append(request.url)
                if request.method == "PUT" and request.url.endswith("/api/profile")
                else None
            ),
        )
        if operation == "save":
            page.get_by_label("Additional preferences").fill("Rejected profile update")
            page.get_by_role("button", name="Save changes", exact=True).click()
        else:
            page.get_by_role("link", name="Account settings", exact=True).click()
        expect(page.get_by_role("link", name="Log in", exact=True).last).to_be_visible()
        expect(page.get_by_label("Additional preferences")).to_have_count(0)
        expect(page.get_by_text("Alice Smith", exact=True)).to_have_count(0)
        page.get_by_role("link", name="Log in", exact=True).last.click()
        login(page, email)
        expect(page.get_by_label("Additional preferences")).to_have_value("Persisted profile notes")
        page.get_by_role("link", name="Plan a trip", exact=True).click()
        expect(page.get_by_label("Additional preferences")).to_have_value(
            "Private unsaved brief to recover"
        )
        assert len(writes) == (1 if operation == "save" else 0)
    finally:
        context.close()
