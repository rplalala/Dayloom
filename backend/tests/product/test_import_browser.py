"""Real browser/API/PostgreSQL import, recovery and reusable export journey."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import jwt
from playwright.sync_api import expect

from backend.tests.product.browser_harness import BROWSER_TEST_SIGNING_KEY
from backend.tests.product.test_browser import browser_app, login, register_browser  # noqa: F401
from backend.tests.product.test_imports import conflicting_source, source


def test_browser_import_save_export_reimport_and_lost_response(browser_app):  # noqa: F811
    base, browser = browser_app.base_url, browser_app.browser
    context = browser.new_context(viewport={"width": 1440, "height": 1000})
    scratch = Path(".scratch/import-browser")
    scratch.mkdir(parents=True, exist_ok=True)
    try:
        page = context.new_page()
        register_browser(page, base)
        page.goto(base + "/import")
        page.get_by_label("Itinerary JSON", exact=True).fill(
            json.dumps({"request": {"traveler_count": None}, "itinerary": source()})
        )
        posts = []
        forbidden = []

        def lose_response(route):
            if route.request.method == "POST":
                posts.append(route.request.headers["x-import-key"])
                route.fetch()
                route.abort("failed")
            else:
                route.continue_()

        page.route("**/api/imports", lose_response)
        page.on(
            "request",
            lambda request: (
                forbidden.append(request.url)
                if request.method == "POST"
                and any(part in request.url for part in ["/api/planning", "/refresh", "/polish"])
                else None
            ),
        )
        page.get_by_role("button", name="Preview import", exact=True).click()
        expect(page.get_by_role("button", name="Check import status")).to_be_visible()
        page.get_by_role("button", name="Check import status").click()
        expect(page.get_by_role("heading", name="Old journey", exact=True)).to_be_visible()
        assert len(posts) == 1
        page.unroute("**/api/imports", lose_response)
        page.screenshot(path=str(scratch / "imported-preview.png"), full_page=True)
        page.get_by_role("button", name="Save to My trips", exact=True).click()
        page.get_by_role("link", name="View saved itinerary", exact=True).click()
        expect(
            page.get_by_text("Imported content · not regenerated or rechecked", exact=False)
        ).to_be_visible()
        with page.expect_download() as download:
            page.get_by_role("button", name="Export JSON", exact=True).click()
        exported = json.loads(Path(download.value.path()).read_text())
        assert exported["request"]["known_fields"] == ["traveler_count"]
        assert exported["itinerary"]["days"][1]["activities"] == []
        assert exported["itinerary"]["days"][0]["activities"][0]["start_time"].endswith(
            ".123456789+11:00"
        )
        assert exported["itinerary"]["nearby"][0]["anchor_activity_id"] == "missing"
        page.get_by_role("button", name="Copy summary", exact=True).click()
        expect(page.get_by_role("textbox", name="Itinerary summary", exact=True)).to_contain_text(
            "Optional Nearby"
        )
        page.get_by_role("button", name="Close", exact=True).click()
        page.goto(base + "/import")
        page.get_by_role("button", name="Start new import", exact=True).click()
        page.get_by_label("Choose JSON file").set_input_files(
            {
                "name": "export.json",
                "mimeType": "application/json",
                "buffer": json.dumps(exported).encode(),
            }
        )
        page.get_by_role("button", name="Preview import", exact=True).click()
        expect(page.get_by_role("heading", name="Old journey", exact=True)).to_be_visible()
        assert forbidden == []
        page.set_viewport_size({"width": 390, "height": 844})
        page.screenshot(path=str(scratch / "reimported-mobile.png"), full_page=True)
    finally:
        context.close()


def test_guest_paste_survives_login_return_without_automatic_import(browser_app):  # noqa: F811
    base, browser = browser_app.base_url, browser_app.browser
    context = browser.new_context(viewport={"width": 390, "height": 844})
    try:
        page = context.new_page()
        page.goto(base + "/import")
        content = json.dumps(source())
        page.get_by_label("Itinerary JSON", exact=True).fill(content)
        sent = []
        page.on(
            "request",
            lambda request: (
                sent.append(request.url)
                if request.method == "POST" and request.url.endswith("/api/imports")
                else None
            ),
        )
        page.get_by_role("link", name="Log in to preview").click()
        page.get_by_role("tab", name="Sign up").click()
        page.get_by_label("Display name").fill("Import Traveler")
        page.get_by_label("Email address").fill(f"import-{uuid4()}@example.com")
        page.get_by_label("Password", exact=True).fill("a secure password")
        page.get_by_label("Confirm password").fill("a secure password")
        page.get_by_role("button", name="Create account", exact=True).click()
        expect(page).to_have_url(base + "/import")
        expect(page.get_by_label("Itinerary JSON", exact=True)).to_have_value(content)
        assert sent == []
        page.get_by_role("button", name="Preview import", exact=True).click()
        expect(page.get_by_role("heading", name="Old journey", exact=True)).to_be_visible()
    finally:
        context.close()


def test_expired_import_hides_input_before_refresh_and_recovers_same_key(browser_app):  # noqa: F811
    base, browser = browser_app.base_url, browser_app.browser
    context = browser.new_context()
    try:
        page = context.new_page()
        email = register_browser(page, base)
        page.goto(base + "/import")
        page.get_by_label("Itinerary JSON", exact=True).fill(json.dumps(source()))
        cookie = next(c for c in context.cookies() if c["name"] == "dayloom_session")
        claims = jwt.decode(cookie["value"], options={"verify_signature": False})
        claims["exp"] = datetime.now(UTC) - timedelta(seconds=1)
        cookie["value"] = jwt.encode(claims, BROWSER_TEST_SIGNING_KEY, algorithm="HS256")
        context.add_cookies([cookie])
        held, keys = [], []
        page.route("**/api/auth/current", lambda route: held.append(route))
        page.on(
            "request",
            lambda request: (
                keys.append(request.headers["x-import-key"])
                if request.method == "POST" and request.url.endswith("/api/imports")
                else None
            ),
        )
        page.get_by_role("button", name="Preview import", exact=True).click()
        expect(page.get_by_label("Itinerary JSON", exact=True)).to_have_count(0)
        expect(page.get_by_role("heading", name="Your import is private.")).to_be_visible()
        assert len(keys) == 1 and held
        held[0].continue_()
        page.unroute("**/api/auth/current")
        page.get_by_role("link", name="Log in", exact=True).last.click()
        login(page, email)
        page.get_by_role("button", name="Check import status").click()
        expect(page.get_by_role("button", name="Retry import with same key")).to_be_visible()
        assert len(keys) == 1
        page.get_by_role("button", name="Retry import with same key").click()
        expect(page.get_by_role("heading", name="Old journey", exact=True)).to_be_visible()
        assert keys[0] == keys[1]
    finally:
        context.close()


def test_deferred_file_cannot_erase_a_later_accepted_import_identity(browser_app):  # noqa: F811
    base, browser = browser_app.base_url, browser_app.browser
    context = browser.new_context()
    try:
        page = context.new_page()
        register_browser(page, base)
        page.add_init_script("""(() => {
            const original = File.prototype.text;
            File.prototype.text = function () {
                if (this.name === 'deferred-a.json') {
                    return new Promise(resolve => { window.finishImportFile = resolve; });
                }
                return original.call(this);
            };
        })();""")
        page.goto(base + "/import")
        page.get_by_label("Choose JSON file").set_input_files(
            {"name": "deferred-a.json", "mimeType": "application/json", "buffer": b"{}"}
        )
        page.wait_for_function('typeof window.finishImportFile === "function"')
        pasted = source() | {"title": "Pasted journey B"}
        content = json.dumps(pasted)
        page.get_by_label("Itinerary JSON", exact=True).fill(content)
        posts = []

        def lose_response(route):
            posts.append(route.request.headers["x-import-key"])
            route.fetch()
            route.abort("failed")

        page.route("**/api/imports", lose_response)
        page.get_by_role("button", name="Preview import", exact=True).click()
        expect(page.get_by_role("button", name="Check import status")).to_be_visible()
        expect(page.get_by_role("button", name="Check import status")).to_be_enabled()
        assert len(posts) == 1
        page.evaluate(
            "(content) => window.finishImportFile(content)",
            json.dumps(source() | {"title": "Late file A"}),
        )
        retained = page.evaluate("JSON.parse(sessionStorage.getItem('dayloom.import.intent.v1'))")
        assert retained["content"] == content
        assert retained["key"] == posts[0] and retained["uncertain"] is True
        page.get_by_role("button", name="Check import status").click()
        expect(page.get_by_role("heading", name="Pasted journey B", exact=True)).to_be_visible()
        assert len(posts) == 1
        page.screenshot(
            path=str(Path(".scratch/import-browser/deferred-file-recovery.png")), full_page=True
        )
    finally:
        context.close()


def test_historical_connection_conflicts_export_and_reimport_with_source_provenance(browser_app):  # noqa: F811
    base, browser = browser_app.base_url, browser_app.browser
    context = browser.new_context()
    try:
        page = context.new_page()
        register_browser(page, base)
        for next_start in ("10:00", "09:59"):
            page.goto(base + "/import")
            expect(page.get_by_role("heading", name="Import itinerary", exact=True)).to_be_visible()
            new_import = page.get_by_role("button", name="Start new import", exact=True)
            if new_import.is_visible():
                new_import.click()
            page.get_by_label("Itinerary JSON", exact=True).fill(
                json.dumps(conflicting_source(next_start))
            )
            page.get_by_role("button", name="Preview import", exact=True).click()
            page.get_by_role("button", name="Save to My trips", exact=True).click()
            page.get_by_role("link", name="View saved itinerary", exact=True).click()
            with page.expect_download() as download:
                page.get_by_role("button", name="Export JSON", exact=True).click()
            exported = json.loads(Path(download.value.path()).read_text())
            assert exported["origin"] == {
                "provenance": "imported",
                "trust": "unverified_import",
                "assertion": "source_snapshot_only",
            }
            transfer = exported["itinerary"]["transfers"][0]
            assert transfer["preceding_end_time"] == "2020-01-01T10:00"
            assert transfer["following_start_time"] == "2020-01-01T" + next_start
            assert transfer["source_status"] == "CONFIRMED"
            assert transfer["status"] == "source_claim"
            page.goto(base + "/import")
            page.get_by_role("button", name="Start new import", exact=True).click()
            page.get_by_label("Itinerary JSON", exact=True).fill(json.dumps(exported))
            page.get_by_role("button", name="Preview import", exact=True).click()
            expect(
                page.get_by_role("heading", name="Historical connection conflict", exact=True)
            ).to_be_visible()
            preview_url = page.url.replace(base, "")
            preview = page.request.get(base + "/api" + preview_url).json()["snapshot"]
            assert preview["trust"] == "unverified_import"
            assert (
                preview["transfers"][0]["following_start_time"] == transfer["following_start_time"]
            )
            assert any(
                claim.startswith("origin: ") for claim in preview["completion"]["source_claims"]
            )
        page.screenshot(
            path=str(Path(".scratch/import-browser/conflict-reimport.png")), full_page=True
        )
    finally:
        context.close()


def test_imported_library_management_and_deleted_receipt_recovery(browser_app):  # noqa: F811
    base, browser = browser_app.base_url, browser_app.browser
    context = browser.new_context()
    try:
        page = context.new_page()
        register_browser(page, base)
        page.goto(base + "/import")
        page.get_by_label("Itinerary JSON", exact=True).fill(
            json.dumps({"request": {"traveler_count": None}, "itinerary": source()})
        )
        page.get_by_role("button", name="Preview import", exact=True).click()
        expect(page.get_by_role("heading", name="Old journey", exact=True)).to_be_visible()
        original_preview = page.url
        page.get_by_role("button", name="Save to My trips", exact=True).click()
        page.get_by_role("link", name="View saved itinerary", exact=True).click()
        page.get_by_role("link", name="Back to My trips", exact=True).first.click()
        page.get_by_role("button", name="Manage Old journey", exact=True).click()
        page.get_by_role("button", name="Rename Old journey", exact=True).click()
        page.get_by_label("New trip title").fill("Imported archive")
        page.get_by_role("button", name="Save title", exact=True).click()
        page.get_by_role("link", name="View Imported archive", exact=True).click()
        with page.expect_download() as download:
            page.get_by_role("button", name="Export JSON", exact=True).click()
        exported = json.loads(Path(download.value.path()).read_text())
        assert exported["title"] == "Imported archive"
        assert exported["request"]["known_fields"] == ["traveler_count"]
        page.get_by_role("link", name="Back to My trips", exact=True).first.click()
        page.get_by_role("button", name="Manage Imported archive", exact=True).click()
        page.get_by_role("button", name="Delete Imported archive", exact=True).click()
        page.get_by_role("button", name="Delete trip", exact=True).click()
        expect(page.get_by_role("heading", name="Your next journey starts here.")).to_be_visible()
        page.goto(base + "/import")
        page.get_by_role("button", name="Check import status").click()
        expect(page).to_have_url(original_preview)
        expect(page.get_by_text("This saved itinerary was deleted.", exact=True)).to_be_visible()
        page.goto(base + "/import")
        page.get_by_role("button", name="Start new import", exact=True).click()
        page.get_by_label("Itinerary JSON", exact=True).fill(json.dumps(exported))
        page.get_by_role("button", name="Preview import", exact=True).click()
        expect(page.get_by_role("heading", name="Imported archive", exact=True)).to_be_visible()
        assert page.url != original_preview
        assert page.request.get(base + "/api/library").json()["total"] == 0
        page.screenshot(
            path=str(Path(".scratch/import-browser/deleted-receipt-new-import.png")), full_page=True
        )
    finally:
        context.close()
