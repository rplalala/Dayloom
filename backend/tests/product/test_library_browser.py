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
        page.get_by_role("button", name="Delete Harbour memories", exact=True).click()
        expect(page.get_by_role("dialog")).to_contain_text("Independent copies stay")
        page.get_by_role("button", name="Cancel", exact=True).click()
        assert page.request.get(saved_url).status == 200
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
