"""Real browser -> Product API -> PostgreSQL draft lifecycle; external adapters are fakes."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import jwt
from playwright.sync_api import expect

from backend.tests.product.browser_harness import BROWSER_TEST_SIGNING_KEY
from backend.tests.product.test_browser import login, register_browser
from backend.tests.product.test_drafts import editor
from backend.tests.product.test_editor_browser import editor_app  # noqa: F401


def test_multiple_drafts_conflict_copy_delete_and_browser_recreation(editor_app):  # noqa: F811
    base, browser = editor_app.base_url, editor_app.browser
    context = browser.new_context()
    try:
        first = context.new_page()
        register_browser(first, base)
        first.get_by_role("button", name="Plan a trip").click()
        first.get_by_label("Destination").fill("Kyoto")
        first.get_by_role("button", name="Nature", exact=True).click()
        first.get_by_label("Draft title").fill("Kyoto unfinished")
        first.get_by_role("button", name="Save draft", exact=True).click()
        expect(first.get_by_text("Draft saved.", exact=True)).to_be_visible()
        saved_url = first.url
        first.reload()
        expect(first.get_by_label("Destination")).to_have_value("Kyoto")
        expect(first.get_by_role("button", name="Nature", exact=True)).to_have_attribute(
            "aria-pressed", "true"
        )
        # An independent tab loads the same revision; the first writer wins.
        other = context.new_page()
        other.goto(saved_url)
        expect(other.get_by_label("Destination")).to_have_value("Kyoto")
        first.get_by_label("Destination").fill("Server revision")
        first.get_by_role("button", name="Save draft", exact=True).click()
        expect(first.get_by_text("Draft saved.", exact=True)).to_be_visible()
        other.get_by_label("Destination").fill("Keep my local work")
        other.get_by_role("button", name="Save draft", exact=True).click()
        expect(other.get_by_role("button", name="Reload saved draft")).to_be_visible()
        expect(other.get_by_label("Destination")).to_have_value("Keep my local work")
        other.get_by_label("Draft title").fill("Local independent idea")
        other.get_by_role("button", name="Save as new draft").click()
        expect(other.get_by_text("Draft saved.", exact=True)).to_be_visible()
        assert other.url != saved_url
        new_url = other.url
        new_id = parse_qs(urlsplit(new_url).query)["draft"][0]
        created = other.request.get(base + f"/api/drafts/{new_id}").json()
        assert created["revision"] == 1
        assert created["editor"]["destination"] == "Keep my local work"
        expect(other.get_by_label("Destination")).to_have_value("Keep my local work")
        expect(other.get_by_label("Draft title")).to_have_value("Local independent idea")
        other.get_by_role("button", name="Save draft", exact=True).click()
        expect(other.get_by_text("Draft saved.", exact=True)).to_be_visible()
        assert other.url == new_url
        assert other.request.get(base + f"/api/drafts/{new_id}").json()["revision"] == 2
        reload_tab = context.new_page()
        reload_tab.goto(saved_url)
        expect(reload_tab.get_by_label("Destination")).to_have_value("Server revision")
        first.get_by_label("Destination").fill("Latest saved revision")
        first.get_by_role("button", name="Save draft", exact=True).click()
        expect(first.get_by_text("Draft saved.", exact=True)).to_be_visible()
        reload_tab.get_by_label("Destination").fill("A local conflict to replace")
        reload_tab.get_by_role("button", name="Save draft", exact=True).click()
        reload_tab.once("dialog", lambda dialog: dialog.accept())
        reload_tab.get_by_role("button", name="Reload saved draft").click()
        expect(reload_tab.get_by_label("Destination")).to_have_value("Latest saved revision")
        reload_tab.close()
        # New browser context has no tab recovery; the server snapshot is sufficient.
        recovered = browser.new_context(storage_state=context.storage_state())
        try:
            page = recovered.new_page()
            page.goto(base + "/trips")
            expect(page.get_by_role("heading", name="Kyoto unfinished")).to_be_visible()
            expect(page.get_by_role("heading", name="Local independent idea")).to_be_visible()
            page.get_by_role("button", name="Manage Kyoto unfinished", exact=True).click()
            page.get_by_role("button", name="Copy Kyoto unfinished", exact=True).click()
            expect(page.get_by_role("heading", name="Kyoto unfinished (copy)")).to_be_visible()
            page.get_by_role("button", name="Manage Kyoto unfinished (copy)", exact=True).click()
            page.get_by_role("button", name="Rename Kyoto unfinished (copy)", exact=True).click()
            page.get_by_label("New draft title").fill("Independent copy")
            page.get_by_role("button", name="Save title", exact=True).click()
            expect(page.get_by_role("heading", name="Independent copy")).to_be_visible()
            page.get_by_role("button", name="Manage Kyoto unfinished", exact=True).click()
            page.get_by_role("button", name="Delete Kyoto unfinished", exact=True).click()
            page.get_by_role("button", name="Cancel", exact=True).click()
            expect(page.get_by_role("heading", name="Kyoto unfinished", exact=True)).to_be_visible()
            page.get_by_role("button", name="Manage Kyoto unfinished", exact=True).click()
            page.get_by_role("button", name="Delete Kyoto unfinished", exact=True).click()
            page.get_by_role("button", name="Delete draft", exact=True).click()
            expect(page.get_by_role("heading", name="Kyoto unfinished", exact=True)).to_have_count(
                0
            )
            expect(page.get_by_role("heading", name="Independent copy", exact=True)).to_be_visible()
            page.get_by_label("Search trips").fill("Keep my local")
            page.get_by_role("button", name="Search", exact=True).click()
            expect(page.get_by_role("heading", name="Local independent idea")).to_be_visible()
            expect(page.get_by_role("heading", name="Independent copy", exact=True)).to_have_count(
                0
            )
            page.get_by_role("link", name="Continue planning", exact=False).click()
            expect(page.get_by_label("Destination")).to_have_value("Keep my local work")
            notes = page.get_by_label("Additional preferences")
            notes.fill("🌿 My edited sentence")
            page.get_by_role("button", name="Save draft", exact=True).click()
            expect(page.get_by_text("Draft saved.", exact=True)).to_be_visible()
            page.reload()
            expect(notes).to_have_value("🌿 My edited sentence")
            expect(page.get_by_role("button", name="Nature", exact=True)).to_have_attribute(
                "aria-pressed", "false"
            )
            scratch = Path(".scratch/draft-browser")
            scratch.mkdir(exist_ok=True)
            for width in [1440, 800, 390]:
                page.set_viewport_size({"width": width, "height": 900})
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                page.screenshot(path=str(scratch / f"draft-{width}.png"), full_page=True)
            page.goto(base + "/trips")
            expect(page.get_by_role("heading", name="Local independent idea")).to_be_visible()
            page.screenshot(path=str(scratch / "library-390.png"), full_page=True)
        finally:
            recovered.close()
    finally:
        context.close()


def test_draft_expiry_quarantines_identity_title_and_unsaved_edits(editor_app):  # noqa: F811
    context = editor_app.browser.new_context()
    try:
        page = context.new_page()
        email = register_browser(page, editor_app.base_url)
        page.goto(editor_app.base_url + "/plan")
        page.get_by_label("Draft title").fill("Before expiry")
        page.get_by_role("button", name="Save draft", exact=True).click()
        expect(page.get_by_text("Draft saved.", exact=True)).to_be_visible()
        original_url = page.url
        page.get_by_label("Destination").fill("Unsaved private destination")
        page.get_by_label("Draft title").fill("Unsaved private title")
        cookie = next(c for c in context.cookies() if c["name"] == "dayloom_session")
        claims = jwt.decode(cookie["value"], options={"verify_signature": False})
        claims["exp"] = datetime.now(UTC) - timedelta(seconds=1)
        expired = jwt.encode(claims, BROWSER_TEST_SIGNING_KEY, algorithm="HS256")
        context.add_cookies(
            [
                {
                    "name": "dayloom_session",
                    "value": expired,
                    "domain": urlsplit(editor_app.base_url).hostname,
                    "path": "/",
                }
            ]
        )
        page.evaluate("window.dispatchEvent(new Event('focus'))")
        expect(page.get_by_role("heading", name="Log in to continue your brief.")).to_be_visible()
        expect(page.get_by_label("Destination")).to_have_count(0)
        page.get_by_role("link", name="Log in", exact=True).last.click()
        login(page, email)
        expect(page.get_by_label("Destination")).to_have_value("Unsaved private destination")
        expect(page.get_by_label("Draft title")).to_have_value("Unsaved private title")
        page.get_by_role("button", name="Save draft", exact=True).click()
        expect(page.get_by_text("Draft saved.", exact=True)).to_be_visible()
        assert page.url == original_url
        page.goto(editor_app.base_url + "/account")
        page.get_by_role("button", name="Log out", exact=True).click()
        page.goto(editor_app.base_url + "/plan")
        expect(page.get_by_label("Draft title")).to_have_value("")
        expect(page.get_by_label("Destination")).to_have_value("")
    finally:
        context.close()


def test_guest_draft_save_returns_to_review_with_title_and_no_automatic_write(editor_app):  # noqa: F811
    context = editor_app.browser.new_context()
    try:
        page = context.new_page()
        page.goto(editor_app.base_url + "/plan")
        page.get_by_label("Destination").fill("My incomplete idea")
        page.get_by_label("Draft title").fill("Guest title to retain")
        page.get_by_role("button", name="Save draft", exact=True).click()
        page.get_by_role("tab", name="Sign up").click()
        page.get_by_label("Display name").fill("Guest traveler")
        page.get_by_label("Email address").fill(f"draft-guest-{uuid4()}@example.com")
        page.get_by_label("Password", exact=True).fill("a secure password")
        page.get_by_label("Confirm password").fill("a secure password")
        page.get_by_role("button", name="Create account", exact=True).click()
        expect(page.get_by_label("Destination")).to_have_value("My incomplete idea")
        expect(page.get_by_label("Draft title")).to_have_value("Guest title to retain")
        assert page.request.get(editor_app.base_url + "/api/library").json()["total"] == 0
        page.get_by_role("button", name="Save draft", exact=True).click()
        expect(page.get_by_text("Draft saved.", exact=True)).to_be_visible()
        assert page.request.get(editor_app.base_url + "/api/library").json()["total"] == 1
    finally:
        context.close()


def test_private_draft_link_returns_through_login_to_its_server_snapshot(editor_app):  # noqa: F811
    context = editor_app.browser.new_context()
    try:
        page = context.new_page()
        email = register_browser(page, editor_app.base_url)
        page.goto(editor_app.base_url + "/plan")
        page.get_by_label("Draft title").fill("A private saved idea")
        page.get_by_label("Destination").fill("Private destination")
        page.get_by_role("button", name="Save draft", exact=True).click()
        expect(page.get_by_text("Draft saved.", exact=True)).to_be_visible()
        target = page.url
        page.goto(editor_app.base_url + "/account")
        page.get_by_role("button", name="Log out", exact=True).click()
        page.goto(target)
        expect(page.get_by_role("heading", name="Log in to open this draft.")).to_be_visible()
        page.get_by_role("link", name="Log in", exact=True).last.click()
        login(page, email)
        expect(page.get_by_label("Destination")).to_have_value("Private destination")
        assert page.url == target
    finally:
        context.close()


def test_late_persisted_save_cannot_rebind_another_open_draft(editor_app):  # noqa: F811
    context = editor_app.browser.new_context()
    held = {}
    try:
        page = context.new_page()
        base = editor_app.base_url
        register_browser(page, base)
        account = page.request.get(base + "/api/auth/current").json()
        headers = {"Origin": base, "X-CSRF-Token": account["csrf_token"]}
        drafts = []
        for title in ["Draft A", "Draft B"]:
            response = page.request.post(
                base + "/api/drafts",
                headers=headers,
                data={"title": title, "editor": editor(destination=title)},
            )
            assert response.status == 201
            drafts.append(response.json())
        first, second = drafts
        page.goto(base + f"/plan?draft={first['id']}")
        expect(page.get_by_label("Destination")).to_have_value("Draft A")

        def barrier(route):
            if route.request.method != "PUT":
                route.continue_()
                return
            # The real API has committed. Hold delivery, not persistence or coordination.
            held["response"] = route.fetch()
            held["route"] = route
            page.evaluate("window.__draftSaveCommitted = true")

        page.route(base + f"/api/drafts/{first['id']}", barrier)
        page.get_by_label("Destination").fill("Accepted A edit")
        page.get_by_role("button", name="Save draft", exact=True).click()
        page.wait_for_function("window.__draftSaveCommitted === true")
        assert held["response"].status == 200
        assert page.request.get(base + f"/api/drafts/{first['id']}").json()["revision"] == 2
        # Real SPA navigation unmounts A's controls, retaining the account provider.
        page.get_by_role("link", name="My trips", exact=True).first.click()
        page.get_by_role("link", name="Continue Draft B", exact=True).click()
        expect(page.get_by_label("Destination")).to_have_value("Draft B")
        second_url = page.url
        page.get_by_label("Destination").fill("New B local edit")
        with page.expect_response(
            lambda response: response.url.endswith(first["id"]) and response.request.method == "PUT"
        ) as delivered:
            held["route"].fulfill(response=held["response"])
        delivered.value.finished()
        # Drain the original fetch promise before observing route and recovery.
        page.evaluate(
            "() => new Promise(resolve => requestAnimationFrame("
            "() => requestAnimationFrame(resolve)))"
        )
        assert page.url == second_url
        expect(page.get_by_label("Destination")).to_have_value("New B local edit")
        expect(page.get_by_label("Draft title")).to_have_value("Draft B")
        page.get_by_role("button", name="Save draft", exact=True).click()
        expect(page.get_by_text("Draft saved.", exact=True)).to_be_visible()
        saved_a = page.request.get(base + f"/api/drafts/{first['id']}").json()
        saved_b = page.request.get(base + f"/api/drafts/{second['id']}").json()
        assert saved_a["revision"] == 2 and saved_a["editor"]["destination"] == "Accepted A edit"
        assert saved_b["revision"] == 2 and saved_b["editor"]["destination"] == "New B local edit"
    finally:
        context.close()
