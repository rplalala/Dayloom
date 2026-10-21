"""Explicit Copy/Keep journeys through Chromium, FastAPI and PostgreSQL."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import jwt
import pytest
from playwright.sync_api import expect

from backend.tests.product.browser_harness import BROWSER_TEST_SIGNING_KEY
from backend.tests.product.test_browser import browser_app, login, register_browser  # noqa: F401


def context_for(browser, width=1440):
    context = browser.new_context(
        viewport={"width": width, "height": 1000}, reduced_motion="reduce"
    )
    # The shared IsolatedBrowser installs controlled image responses before navigation.
    return context


def seed_example(page, base):
    account = page.request.get(base + "/api/auth/current").json()
    result = page.request.post(
        base + "/api/copies",
        headers={"Origin": base, "X-CSRF-Token": account["csrf_token"]},
        data={
            "source_kind": "example",
            "source_id": "sydney-example",
            "operation_key": str(uuid4()),
        },
    )
    assert result.status == 200
    return result.json()["saved_trip_id"]


def test_guest_keep_returns_to_review_without_automatic_write_or_lost_brief(browser_app):  # noqa: F811
    base, browser = browser_app.base_url, browser_app.browser
    context = context_for(browser, 390)
    try:
        page = context.new_page()
        page.goto(base + "/plan")
        page.get_by_label("Additional preferences").fill("Keep my guest brief")
        page.goto(base + "/examples/sydney-example")
        posts = []
        page.on(
            "request",
            lambda request: (
                posts.append(request.url)
                if request.method == "POST"
                and any(part in request.url for part in ("/api/copies", "/api/planning"))
                else None
            ),
        )
        page.get_by_role("button", name="Keep a copy", exact=True).click()
        page.get_by_role("tab", name="Sign up").click()
        page.get_by_label("Display name").fill("Example Traveler")
        page.get_by_label("Email address").fill(f"keep-{uuid4()}@example.com")
        page.get_by_label("Password", exact=True).fill("a secure password")
        page.get_by_label("Confirm password").fill("a secure password")
        page.get_by_role("button", name="Create account", exact=True).click()
        expect(page).to_have_url(base + "/examples/sydney-example")
        expect(page.get_by_role("button", name="Keep a copy", exact=True)).to_be_visible()
        assert posts == []
        assert page.request.get(base + "/api/library").json()["total"] == 0
        page.get_by_role("button", name="Keep a copy", exact=True).click()
        expect(
            page.get_by_text("An independent copy was added to My trips.", exact=True)
        ).to_be_visible()
        assert len(posts) == 1
        page.get_by_role("link", name="View saved copy", exact=True).click()
        expect(
            page.get_by_role(
                "heading", name="Sydney · Three days by the harbour (copy)", exact=True
            )
        ).to_be_visible()
        page.goto(base + "/plan")
        expect(page.get_by_label("Additional preferences")).to_have_value("Keep my guest brief")
    finally:
        context.close()


@pytest.mark.parametrize("width", [390, 800, 1440])
def test_library_copy_keyboard_lost_reply_recovery_and_independent_detail(browser_app, width):  # noqa: F811
    base, browser = browser_app.base_url, browser_app.browser
    context = context_for(browser, width)
    scratch = Path(".scratch/copy-browser")
    scratch.mkdir(parents=True, exist_ok=True)
    try:
        page = context.new_page()
        register_browser(page, base)
        original = seed_example(page, base)
        page.goto(base + "/trips")
        expect(page.get_by_role("button", name="Copy", exact=True)).to_be_visible()
        assert page.get_by_role("tab", name="Examples", exact=True).count() == 0
        page.get_by_role("button", name="Copy", exact=True).focus()
        page.keyboard.press("Enter")
        dialog = page.get_by_role("dialog", name="Keep an independent copy")
        expect(dialog).to_be_visible()
        page.keyboard.press("Escape")
        expect(dialog).not_to_be_visible()
        page.get_by_role(
            "button", name="Manage Sydney · Three days by the harbour (copy)", exact=True
        ).click()
        page.get_by_role(
            "button", name="Copy Sydney · Three days by the harbour (copy)", exact=True
        ).click()
        posts = []

        def lose(route):
            if route.request.method == "POST":
                posts.append(route.request.post_data_json)
                route.fetch()
                route.abort()
            else:
                route.continue_()

        page.route("**/api/copies", lose)
        dialog.get_by_role("button", name="Make a copy", exact=True).click()
        expect(dialog.get_by_role("button", name="Check copy status", exact=True)).to_be_visible()
        page.reload()
        page.get_by_role("button", name="Copy", exact=True).first.click()
        # Choose the original by a stable source id if ordering changed after the commit.
        page.keyboard.press("Escape")
        page.get_by_role(
            "button", name="Manage Sydney · Three days by the harbour (copy)", exact=True
        ).click()
        page.get_by_role(
            "button", name="Copy Sydney · Three days by the harbour (copy)", exact=True
        ).click()
        dialog.get_by_role("button", name="Check copy status", exact=True).click()
        expect(
            dialog.get_by_text("An independent copy was added to My trips.", exact=True)
        ).to_be_visible()
        assert len(posts) == 1 and posts[0]["source_id"] == original
        expect(page.get_by_text("Loading your collection…", exact=True)).not_to_be_visible()
        page.screenshot(path=str(scratch / f"library-copy-{width}.png"), full_page=True)
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        dialog.get_by_role("link", name="View saved copy", exact=True).click()
        expect(
            page.get_by_role(
                "heading", name="Sydney · Three days by the harbour (copy) (copy)", exact=True
            )
        ).to_be_visible()
        expect(
            page.get_by_text(
                "Historical example · source claims, not a fresh verification", exact=False
            )
        ).to_be_visible()
        page.screenshot(path=str(scratch / f"saved-copy-{width}.png"), full_page=True)
    finally:
        context.close()


def test_copy_uncommitted_lost_reply_requires_get_then_explicit_same_key_retry(browser_app):  # noqa: F811
    base, browser = browser_app.base_url, browser_app.browser
    context = context_for(browser)
    try:
        page = context.new_page()
        register_browser(page, base)
        page.goto(base + "/examples/sydney-example")
        keys = []

        def lose(route):
            keys.append(route.request.post_data_json["operation_key"])
            route.abort()

        page.route("**/api/copies", lose)
        page.get_by_role("button", name="Keep a copy", exact=True).click()
        page.get_by_role("button", name="Check copy status", exact=True).click()
        expect(
            page.get_by_role("button", name="Retry copy with same key", exact=True)
        ).to_be_visible()
        assert page.request.get(base + "/api/library").json()["total"] == 0
        page.unroute("**/api/copies", lose)
        with page.expect_request(
            lambda request: request.method == "POST" and request.url.endswith("/api/copies")
        ) as sent:
            page.get_by_role("button", name="Retry copy with same key", exact=True).click()
        assert sent.value.post_data_json["operation_key"] == keys[0]
        expect(page.get_by_role("link", name="View saved copy", exact=True)).to_be_visible()
    finally:
        context.close()


def test_copy_expiry_quarantine_same_owner_recovery_logout_and_other_owner_clear(browser_app):  # noqa: F811
    base, browser = browser_app.base_url, browser_app.browser
    context = context_for(browser)
    try:
        page = context.new_page()
        email = register_browser(page, base)
        page.goto(base + "/examples/sydney-example")
        posts = []

        def lose(route):
            posts.append(route.request.post_data_json)
            route.fetch()
            route.abort()

        page.route("**/api/copies", lose)
        page.get_by_role("button", name="Keep a copy", exact=True).click()
        expect(page.get_by_role("button", name="Check copy status", exact=True)).to_be_visible()
        token = next(
            cookie["value"] for cookie in context.cookies() if cookie["name"] == "dayloom_session"
        )
        claims = jwt.decode(token, options={"verify_signature": False})
        claims["exp"] = datetime.now(UTC) - timedelta(minutes=1)
        context.add_cookies(
            [
                {
                    "name": "dayloom_session",
                    "value": jwt.encode(claims, BROWSER_TEST_SIGNING_KEY, algorithm="HS256"),
                    "url": base,
                    "httpOnly": True,
                }
            ]
        )
        page.reload()
        expect(page.get_by_text("Your copy action is private.", exact=False)).to_be_visible()
        assert page.get_by_role("button", name="Check copy status", exact=True).count() == 0
        page.get_by_role("link", name="Log in", exact=True).last.click()
        login(page, email)
        expect(page).to_have_url(base + "/examples/sydney-example")
        expect(page.get_by_role("button", name="Check copy status", exact=True)).to_be_visible()
        assert len(posts) == 1
        page.get_by_role("button", name="Check copy status", exact=True).click()
        expect(page.get_by_role("link", name="View saved copy", exact=True)).to_be_visible()
        page.goto(base + "/account")
        page.get_by_role("button", name="Log out", exact=True).click()
        expect(page.get_by_role("link", name="Log in", exact=True).last).to_be_visible()
        assert page.evaluate("sessionStorage.getItem('dayloom.copy.intent.v1')") is None
        page.goto(base + "/login")
        login(page, email)
        expect(page.get_by_role("heading", name="My trips", exact=True)).to_be_visible()
        page.goto(base + "/examples/sydney-example")
        expect(page.get_by_role("button", name="Keep a copy", exact=True)).to_be_visible()
        assert len(posts) == 1
        page.unroute("**/api/copies", lose)
    finally:
        context.close()


def test_late_copy_reply_cannot_navigate_or_overwrite_another_page(browser_app):  # noqa: F811
    base, browser = browser_app.base_url, browser_app.browser
    context = context_for(browser)
    try:
        page = context.new_page()
        register_browser(page, base)
        page.goto(base + "/examples/sydney-example")
        held = []
        page.route("**/api/copies", lambda route: held.append((route, route.fetch())))
        page.get_by_role("button", name="Keep a copy", exact=True).click()
        expect(page.get_by_role("button", name="Checking copy…", exact=True)).to_be_visible()
        page.goto(base + "/plan")
        page.get_by_label("Additional preferences").fill("A different brief stays here")
        assert len(held) == 1
        held[0][0].fulfill(response=held[0][1])
        expect(page).to_have_url(base + "/plan")
        expect(page.get_by_label("Additional preferences")).to_have_value(
            "A different brief stays here"
        )
        assert page.get_by_role("link", name="View saved copy", exact=True).count() == 0
    finally:
        context.close()


def test_different_account_login_clears_copy_identity_without_replay(browser_app):  # noqa: F811
    base, browser = browser_app.base_url, browser_app.browser
    context = context_for(browser)
    try:
        page = context.new_page()
        register_browser(page, base)
        page.goto(base + "/examples/sydney-example")
        page.route("**/api/copies", lambda route: route.abort())
        page.get_by_role("button", name="Keep a copy", exact=True).click()
        expect(page.get_by_role("button", name="Check copy status", exact=True)).to_be_visible()
        assert page.evaluate("JSON.parse(sessionStorage.getItem('dayloom.copy.intent.v1'))[0].key")
        page.goto(base + "/login?return=/examples/sydney-example")
        page.get_by_role("tab", name="Sign up").click()
        page.get_by_label("Display name").fill("Other traveler")
        page.get_by_label("Email address").fill(f"other-copy-{uuid4()}@example.com")
        page.get_by_label("Password", exact=True).fill("a secure password")
        page.get_by_label("Confirm password").fill("a secure password")
        page.get_by_role("button", name="Create account", exact=True).click()
        expect(page).to_have_url(base + "/examples/sydney-example")
        expect(page.get_by_role("button", name="Keep a copy", exact=True)).to_be_visible()
        assert page.evaluate("sessionStorage.getItem('dayloom.copy.intent.v1')") is None
        assert page.request.get(base + "/api/library").json()["total"] == 0
    finally:
        context.close()


def test_deleted_copy_receipt_is_visible_without_resurrection(browser_app):  # noqa: F811
    base, browser = browser_app.base_url, browser_app.browser
    context = context_for(browser)
    try:
        page = context.new_page()
        register_browser(page, base)
        page.goto(base + "/examples/sydney-example")
        page.get_by_role("button", name="Keep a copy", exact=True).click()
        link = page.get_by_role("link", name="View saved copy", exact=True)
        expect(link).to_be_visible()
        saved_id = link.get_attribute("href").split("/")[-1]
        account = page.request.get(base + "/api/auth/current").json()
        deleted = page.request.delete(
            base + f"/api/trips/{saved_id}",
            headers={"Origin": base, "X-CSRF-Token": account["csrf_token"]},
            data={"revision": 1, "confirmed": True},
        )
        assert deleted.status == 204
        page.reload()
        page.get_by_role("button", name="Check copy status", exact=True).click()
        expect(
            page.get_by_text("This saved copy was deleted. It will not be recreated.", exact=True)
        ).to_be_visible()
        assert link.count() == 0
        assert page.request.get(base + "/api/library").json()["total"] == 0
    finally:
        context.close()


def test_other_tab_logout_removes_this_tabs_quarantined_copy_identity(browser_app):  # noqa: F811
    base, browser = browser_app.base_url, browser_app.browser
    context = context_for(browser)
    try:
        page = context.new_page()
        register_browser(page, base)
        page.goto(base + "/examples/sydney-example")
        page.route("**/api/copies", lambda route: route.abort())
        page.get_by_role("button", name="Keep a copy", exact=True).click()
        expect(page.get_by_role("button", name="Check copy status", exact=True)).to_be_visible()
        other = context.new_page()
        other.goto(base + "/account")
        other.get_by_role("button", name="Log out", exact=True).click()
        expect(page.get_by_role("button", name="Keep a copy", exact=True)).to_be_visible()
        assert page.evaluate("sessionStorage.getItem('dayloom.copy.intent.v1')") is None
    finally:
        context.close()


def test_unconfirmed_copy_a_survives_a_copy_of_b_and_return_to_a(browser_app):  # noqa: F811
    base, browser = browser_app.base_url, browser_app.browser
    context = context_for(browser)
    try:
        page = context.new_page()
        register_browser(page, base)
        sent = []

        def lose(route):
            sent.append(route.request.post_data_json)
            route.fetch()
            route.abort()

        page.route("**/api/copies", lose)
        for slug in ("sydney-example", "kyoto-design"):
            page.goto(base + f"/examples/{slug}")
            page.get_by_role("button", name="Keep a copy", exact=True).click()
            expect(page.get_by_role("button", name="Check copy status", exact=True)).to_be_visible()
        page.goto(base + "/examples/sydney-example")
        page.get_by_role("button", name="Check copy status", exact=True).click()
        expect(page.get_by_role("link", name="View saved copy", exact=True)).to_be_visible()
        page.goto(base + "/examples/kyoto-design")
        page.get_by_role("button", name="Check copy status", exact=True).click()
        expect(page.get_by_role("link", name="View saved copy", exact=True)).to_be_visible()
        assert len(sent) == 2
        assert sent[0]["operation_key"] != sent[1]["operation_key"]
        assert page.request.get(base + "/api/library").json()["total"] == 2
    finally:
        context.close()


@pytest.mark.parametrize("entry", ["source", "library"])
@pytest.mark.parametrize("delete_result", [False, True])
def test_source_deleted_copy_recovers_only_its_receipt_without_source_or_new_write(
    browser_app,  # noqa: F811
    entry,
    delete_result,
):
    base, browser = browser_app.base_url, browser_app.browser
    context = context_for(browser)
    try:
        page = context.new_page()
        email = register_browser(page, base)
        original = seed_example(page, base)
        page.goto(base + f"/trips/{original}")
        replies, posts = [], []

        def lose(route):
            posts.append(route.request.post_data_json)
            replies.append(route.fetch().json())
            route.abort()

        page.route("**/api/copies", lose)
        page.get_by_role("button", name="Make a copy", exact=True).click()
        expect(page.get_by_role("button", name="Check copy status", exact=True)).to_be_visible()
        account = page.request.get(base + "/api/auth/current").json()
        for identity in [original] + ([replies[0]["saved_trip_id"]] if delete_result else []):
            assert (
                page.request.delete(
                    base + f"/api/trips/{identity}",
                    headers={"Origin": base, "X-CSRF-Token": account["csrf_token"]},
                    data={"revision": 1, "confirmed": True},
                ).status
                == 204
            )
        page.goto(base + (f"/trips/{original}" if entry == "source" else "/trips"))
        if entry == "source" and delete_result:
            token = next(
                cookie["value"]
                for cookie in context.cookies()
                if cookie["name"] == "dayloom_session"
            )
            claims = jwt.decode(token, options={"verify_signature": False})
            claims["exp"] = datetime.now(UTC) - timedelta(minutes=1)
            context.add_cookies(
                [
                    {
                        "name": "dayloom_session",
                        "value": jwt.encode(claims, BROWSER_TEST_SIGNING_KEY, algorithm="HS256"),
                        "url": base,
                        "httpOnly": True,
                    }
                ]
            )
            page.reload()
            page.get_by_role("link", name="Log in", exact=True).last.click()
            login(page, email)
        if entry == "library":
            page.get_by_role("link", name="Check pending copy status", exact=True).click()
        expect(page.get_by_role("button", name="Make a copy", exact=True)).not_to_be_visible()
        page.get_by_role("button", name="Check copy status", exact=True).click()
        if delete_result:
            expect(
                page.get_by_text(
                    "This saved copy was deleted. It will not be recreated.", exact=True
                )
            ).to_be_visible()
            assert page.get_by_role("link", name="View saved copy", exact=True).count() == 0
        else:
            link = page.get_by_role("link", name="View saved copy", exact=True)
            expect(link).to_have_attribute("href", f"/trips/{replies[0]['saved_trip_id']}")
        assert len(posts) == 1
        assert page.request.get(base + "/api/library").json()["total"] == (
            0 if delete_result else 1
        )
    finally:
        context.close()
