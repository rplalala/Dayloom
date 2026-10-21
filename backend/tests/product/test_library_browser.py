"""Actual browser/API/PostgreSQL mixed collection and saved-trip management."""

from pathlib import Path

from playwright.sync_api import expect

from backend.app.product.database import connect
from backend.tests.product.test_browser import browser_app, register_browser  # noqa: F401
from backend.tests.product.test_drafts import editor
from backend.tests.product.test_saved import historical_content, pending


def test_browser_manages_saved_snapshot_with_mixed_pagination_and_empty_states(browser_app):  # noqa: F811
    base = browser_app.base_url
    context = browser_app.browser.new_context(
        viewport={"width": 1440, "height": 1000}, reduced_motion="reduce"
    )
    try:
        page = context.new_page()
        register_browser(page, base)
        expect(page.get_by_role("heading", name="Your next journey starts here.")).to_be_visible()
        account = page.request.get(base + "/api/auth/current").json()
        headers = {"Origin": base, "X-CSRF-Token": account["csrf_token"]}
        preview = pending(account["id"], **historical_content())
        decision = page.request.post(
            base + f"/api/previews/{preview.id}/save", headers=headers, data={}
        ).json()
        identity = decision["saved_trip_id"]
        saved_url = base + f"/api/trips/{identity}"
        original = page.request.get(saved_url).json()
        for index in range(12):
            response = page.request.post(
                base + "/api/drafts",
                headers=headers,
                data={
                    "title": f"Same title {index:02}",
                    "editor": editor(destination="Kyoto" if index % 2 else "Sydney"),
                },
            )
            assert response.status == 201
        with connect() as connection:
            connection.execute(
                "UPDATE app.planning_drafts SET created_at='2020-01-01Z' WHERE owner_id=%s",
                (account["id"],),
            )
            connection.execute(
                "UPDATE app.trips SET created_at='2020-01-01Z' WHERE owner_id=%s", (account["id"],)
            )
        expected = page.request.get(base + "/api/library?limit=50").json()["items"]
        page.reload()
        expect(page.locator(".trip-card")).to_have_count(12)
        first_page = page.locator(".draft-card-cover").evaluate_all(
            "nodes => nodes.map(node => node.getAttribute('href'))"
        )
        # Cover links are actual owner-specific destinations, not client-merged lists.
        assert first_page == [
            f"/plan?draft={row['id']}" if row["kind"] == "draft" else f"/trips/{row['id']}"
            for row in expected[:12]
        ]
        scratch = Path(".scratch/library-browser")
        scratch.mkdir(exist_ok=True)
        for width in (1440, 800, 390):
            page.set_viewport_size({"width": width, "height": 1000})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.screenshot(path=str(scratch / f"mixed-library-{width}.png"), full_page=True)
        page.set_viewport_size({"width": 1440, "height": 1000})
        page.get_by_role("button", name="Next", exact=True).click()
        expect(page.locator(".trip-card")).to_have_count(1)
        expect(page.get_by_role("button", name="Next", exact=True)).to_be_disabled()
        page.get_by_role("button", name="Previous", exact=True).click()
        page.get_by_label("Search trips").fill("saved journey")
        page.get_by_role("button", name="Search", exact=True).click()
        expect(page.locator(".trip-card")).to_have_count(1)
        page.get_by_role("button", name="Manage A saved journey", exact=True).click()
        page.get_by_role("button", name="Rename A saved journey", exact=True).click()
        page.get_by_label("New trip title").fill("Harbour memories")
        page.get_by_role("button", name="Save title", exact=True).click()
        expect(page.get_by_role("heading", name="No matching journeys.")).to_be_visible()
        assert page.request.get(saved_url).json() == original | {"title": "Harbour memories"}
        page.get_by_label("Search trips").fill("harbour memories")
        page.get_by_role("button", name="Search", exact=True).click()
        expect(page.get_by_role("heading", name="Harbour memories", exact=True)).to_be_visible()
        page.get_by_role("link", name="View Harbour memories", exact=True).click()
        expect(page.get_by_role("heading", name="Harbour memories", exact=True)).to_be_visible()
        expect(page.get_by_text("Free time · no fixed place", exact=True)).to_be_visible()
        page.get_by_text("Planning review · incomplete", exact=True).click()
        expect(page.get_by_text("Unresolved opening hours", exact=False)).to_be_visible()
        for view in ("weather", "nearby", "transfers"):
            assert page.request.get(saved_url + "/" + view).status == 200
        page.get_by_role("link", name="Back to My trips", exact=True).first.click()
        page.get_by_label("Search trips").fill("Harbour memories")
        page.get_by_role("button", name="Search", exact=True).click()
        expect(page.get_by_role("heading", name="Harbour memories", exact=True)).to_be_visible()
        for width in (1440, 800, 390):
            page.set_viewport_size({"width": width, "height": 1000})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.screenshot(path=str(scratch / f"saved-management-{width}.png"), full_page=True)
        page.get_by_role("button", name="Manage Harbour memories", exact=True).click()
        page.get_by_role("button", name="Delete Harbour memories", exact=True).click()
        expect(page.get_by_role("dialog")).to_contain_text("Independent copies stay")
        page.get_by_role("button", name="Cancel", exact=True).click()
        assert page.request.get(saved_url).status == 200
        page.get_by_role("button", name="Manage Harbour memories", exact=True).click()
        page.get_by_role("button", name="Delete Harbour memories", exact=True).click()
        page.get_by_role("button", name="Delete trip", exact=True).click()
        expect(page.get_by_role("heading", name="No matching journeys.")).to_be_visible()
        assert page.request.get(saved_url).status == 404
        late = page.request.post(
            base + f"/api/previews/{preview.id}/save", headers=headers, data={}
        )
        assert late.status == 409
        assert late.json()["detail"]["decision"]["outcome"] == "saved_result_deleted"
        page.get_by_label("Search trips").fill("no such place")
        page.get_by_role("button", name="Search", exact=True).click()
        expect(page.get_by_role("heading", name="No matching journeys.")).to_be_visible()
    finally:
        context.close()


def test_saved_mutation_expiry_hides_collection_before_delayed_session_recovery(browser_app):  # noqa: F811
    from datetime import UTC, datetime, timedelta
    from urllib.parse import urlsplit

    import jwt

    from backend.tests.product.browser_harness import BROWSER_TEST_SIGNING_KEY
    from backend.tests.product.test_browser import login

    base = browser_app.base_url
    context = browser_app.browser.new_context()
    held = []
    writes = []
    try:
        page = context.new_page()
        email = register_browser(page, base)
        account = page.request.get(base + "/api/auth/current").json()
        headers = {"Origin": base, "X-CSRF-Token": account["csrf_token"]}
        preview = pending(account["id"])
        assert (
            page.request.post(
                base + f"/api/previews/{preview.id}/save", headers=headers, data={}
            ).status
            == 200
        )
        page.reload()
        expect(page.get_by_role("heading", name="A saved journey", exact=True)).to_be_visible()
        page.get_by_role("button", name="Manage A saved journey", exact=True).click()
        page.get_by_role("button", name="Rename A saved journey", exact=True).click()
        page.get_by_label("New trip title").fill("Private new title")
        cookie = next(cookie for cookie in context.cookies() if cookie["name"] == "dayloom_session")
        claims = jwt.decode(cookie["value"], options={"verify_signature": False})
        claims["exp"] = datetime.now(UTC) - timedelta(seconds=1)
        context.add_cookies(
            [
                {
                    "name": "dayloom_session",
                    "value": jwt.encode(claims, BROWSER_TEST_SIGNING_KEY, algorithm="HS256"),
                    "domain": urlsplit(base).hostname,
                    "path": "/",
                }
            ]
        )
        page.route("**/api/auth/current", lambda route: held.append(route))
        page.on(
            "request",
            lambda request: writes.append(request.url) if request.method == "PATCH" else None,
        )
        with page.expect_response(lambda response: response.request.method == "PATCH") as rejected:
            page.get_by_role("button", name="Save title", exact=True).click()
        assert rejected.value.status == 401
        expect(page.get_by_role("heading", name="A saved journey", exact=True)).to_have_count(0)
        expect(page.get_by_role("dialog")).to_have_count(0)
        assert len(writes) == 1
        for route in held:
            route.continue_()
        page.unroute("**/api/auth/current")
        expect(page.get_by_role("heading", name="Your trips are private.")).to_be_visible()
        page.get_by_role("link", name="Log in", exact=True).last.click()
        login(page, email)
        expect(page.get_by_role("heading", name="A saved journey", exact=True)).to_be_visible()
        assert len(writes) == 1
        assert (
            page.request.get(base + "/api/library").json()["items"][0]["title"] == "A saved journey"
        )
    finally:
        context.close()


def test_r7_library_toolbar_stays_compact_above_mobile_breakpoint(browser_app):  # noqa: F811
    context = browser_app.browser.new_context()
    try:
        page = context.new_page()
        register_browser(page, browser_app.base_url)
        for width in (1440, 800, 561, 560, 390):
            page.set_viewport_size({"width": width, "height": 1000})
            search = page.get_by_role("search").bounding_box()
            sort = page.get_by_label("Sort trips").bounding_box()
            if width > 560:
                assert sort["x"] >= search["x"] + search["width"]
                assert (
                    abs((search["y"] + search["height"] / 2) - (sort["y"] + sort["height"] / 2)) < 8
                )
            else:
                assert sort["y"] >= search["y"] + search["height"]
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    finally:
        context.close()


def test_r7_saved_and_draft_management_is_a_keyboard_accessible_card_dialog(browser_app):  # noqa: F811
    context = browser_app.browser.new_context(
        viewport={"width": 800, "height": 1000}, reduced_motion="reduce"
    )
    try:
        page = context.new_page()
        base = browser_app.base_url
        register_browser(page, base)
        account = page.request.get(base + "/api/auth/current").json()
        headers = {"Origin": base, "X-CSRF-Token": account["csrf_token"]}
        preview = pending(account["id"])
        assert (
            page.request.post(
                base + f"/api/previews/{preview.id}/save", headers=headers, data={}
            ).status
            == 200
        )
        assert (
            page.request.post(
                base + "/api/drafts",
                headers=headers,
                data={"title": "A draft idea", "editor": editor()},
            ).status
            == 201
        )
        page.reload()
        expect(page.locator(".trip-card")).to_have_count(2)
        notice = page.locator(".task-completion-notice")
        expect(notice).to_be_visible()
        assert page.get_by_role("banner").bounding_box()["y"] == 0
        assert page.locator("main").bounding_box()["y"] < 100
        scratch = Path(".scratch/library-browser")
        page.screenshot(path=str(scratch / "r7-completion-notice-800.png"), full_page=True)
        notice.get_by_role("link", name="View preview", exact=True).focus()
        page.keyboard.press("Enter")
        expect(page.get_by_text("Saved to My trips.", exact=True)).to_be_visible()
        page.get_by_role("link", name="My trips", exact=True).first.click()
        expect(page.locator(".trip-card")).to_have_count(2)
        notice.get_by_role("button", name="Dismiss completion notice").click()
        expect(notice).to_have_count(0)
        assert page.get_by_role("banner").bounding_box()["y"] == 0
        for title in ("A saved journey", "A draft idea"):
            trigger = page.get_by_role("button", name=f"Manage {title}", exact=True)
            expect(trigger).to_be_visible()
            expect(trigger).to_have_attribute("aria-haspopup", "dialog")
            expect(trigger).to_have_attribute("aria-expanded", "false")
            card = trigger.locator("xpath=ancestor::article")
            assert (
                trigger.bounding_box()["x"]
                > card.bounding_box()["x"] + card.bounding_box()["width"] / 2
            )
            expect(page.get_by_role("button", name=f"Rename {title}", exact=True)).to_have_count(0)
            trigger.focus()
            page.keyboard.press("Enter")
            expect(trigger).to_have_attribute("aria-expanded", "true")
            dialog = page.get_by_role("dialog")
            expect(dialog).to_contain_text(title)
            rename = page.get_by_role("button", name=f"Rename {title}", exact=True)
            expect(rename).to_be_focused()
            if title == "A draft idea":
                page.keyboard.press("Tab")
                expect(page.get_by_role("button", name=f"Copy {title}", exact=True)).to_be_focused()
                page.keyboard.press("Shift+Tab")
            page.keyboard.press("Enter")
            expect(
                page.get_by_label(
                    "New draft title" if title == "A draft idea" else "New trip title"
                )
            ).to_be_focused()
            page.keyboard.press("Escape")
            expect(dialog).to_have_count(0)
            expect(trigger).to_be_focused()
            page.keyboard.press("Enter")
            page.keyboard.press("Tab")
            if title == "A draft idea":
                page.keyboard.press("Tab")
            expect(page.get_by_role("button", name=f"Delete {title}", exact=True)).to_be_focused()
            page.keyboard.press("Enter")
            expect(
                page.get_by_role(
                    "heading",
                    name="Delete draft?" if title == "A draft idea" else "Delete trip?",
                    exact=True,
                )
            ).to_be_visible()
            page.keyboard.press("Escape")
            expect(dialog).to_have_count(0)
            expect(trigger).to_be_focused()
            trigger.click()
            page.mouse.click(3, 100)
            expect(dialog).to_have_count(0)
            expect(trigger).to_be_focused()
        for width in (1440, 800, 390):
            page.set_viewport_size({"width": width, "height": 1000})
            expect(page.locator(".trip-card")).to_have_count(2)
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.evaluate("window.scrollTo({top: 0, behavior: 'instant'})")
            page.wait_for_function("window.scrollY === 0")
            page.screenshot(
                path=str(scratch / f"r7-library-correction-{width}.png"), full_page=True
            )
        page.get_by_role("button", name="Manage A saved journey", exact=True).click()
        expect(page.get_by_role("heading", name="Manage your trip", exact=True)).to_be_visible()
        page.screenshot(path=str(scratch / "r7-manage-dialog-390.png"))
    finally:
        context.close()
