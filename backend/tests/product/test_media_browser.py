"""Actual V3/Product/PostgreSQL/Chromium media acceptance, external transport only."""

import json
from pathlib import Path

from playwright.sync_api import expect

from backend.tests.product.test_browser import register_browser
from backend.tests.product.test_imports import source
from backend.tests.product.test_task_browser import task_app  # noqa: F401


def test_verified_photo_credit_expiration_refresh_save_and_forged_import(task_app):  # noqa: F811
    base, browser = task_app.base_url, task_app.browser
    context = browser.new_context(viewport={"width": 1440, "height": 1000})
    scratch = Path(".scratch/media-browser")
    scratch.mkdir(parents=True, exist_ok=True)
    signals = Path(".scratch/task-browser/signals")
    for signal in signals.iterdir():
        if signal.is_file():
            signal.unlink()
    try:
        page = context.new_page()
        register_browser(page, base)
        page.goto(base + "/plan")
        page.get_by_label("Destination", exact=True).fill("Sydney")
        page.get_by_label("Start date", exact=True).fill("2026-09-12")
        page.get_by_label("End date", exact=True).fill("2026-09-13")
        page.get_by_label("Travelers", exact=True).fill("2")
        page.get_by_label("Whole-trip budget", exact=True).fill("1800")
        (signals / "model-release").touch()
        (signals / "media-nearby").touch()
        page.get_by_role("button", name="Generate itinerary", exact=False).click()
        page.get_by_role("link", name="Open task progress").click()
        page.get_by_role("link", name="Open itinerary preview").click(timeout=30000)
        expect(page.get_by_text("Unsaved itinerary preview", exact=True)).to_be_visible()
        expect(page.locator(".activity-photo img").first).to_be_visible()
        expect(page.locator(".activity-photo .media-provider").first).to_have_text("Google Maps")
        expect(page.get_by_role("link", name="Controlled Photographer").first).to_be_visible()
        page.get_by_role("button", name="View Place poi-0-1", exact=True).click()
        expect(page.get_by_role("dialog")).to_be_visible()
        page.keyboard.press("Escape")
        expect(page.locator(".nearby-sidebar-groups .nearby-photo img").first).to_be_visible()
        expect(page.locator(".nearby-sidebar-groups .nearby-photo").first).to_contain_text(
            "Google Maps"
        )
        assert (signals / "retrieval-entered").exists() and (signals / "retrieval-closed").exists()
        preview_id = page.url.rsplit("/", 1)[-1]
        metadata = page.request.get(base + f"/api/previews/{preview_id}/media").json()
        assert metadata["items"] and all(
            item["kind"] == "verified_place" for item in metadata["items"].values()
        )
        assert len(metadata["items"]) <= 12
        assert page.request.get(base + f"/api/previews/{preview_id}/media?width=1281").status == 422
        assert "media_bindings" not in page.request.get(base + f"/api/previews/{preview_id}").text()
        page.screenshot(path=str(scratch / "verified-desktop.png"), full_page=True)
        # Only the external image transport fails; Product metadata/persistence remain real.
        page.route(
            "https://lh3.googleusercontent.com/**",
            lambda route: route.fulfill(status=404, body="expired"),
        )
        page.reload()
        expect(page.locator(".activity-photo").first).to_contain_text(
            "Place photograph unavailable"
        )
        page.get_by_role("button", name="Save to My trips", exact=True).click()
        page.get_by_role("link", name="View saved itinerary", exact=True).click()
        expect(page.locator(".activity-photo").first).to_contain_text(
            "Place photograph unavailable"
        )
        saved_url = page.url
        page.goto(base + "/trips")
        expect(page.locator(".library-card-cover .media-photo img").first).to_be_visible()
        expect(page.locator(".library-card-cover .media-photo").first).to_contain_text("Unsplash")
        page.goto(saved_url)
        page.unroute("https://lh3.googleusercontent.com/**")
        page.get_by_role("button", name="Refresh place photos", exact=True).click()
        expect(page.locator(".activity-photo img").first).to_be_visible()
        page.reload()
        expect(page.locator(".activity-photo img").first).to_be_visible()
        expect(page.get_by_role("link", name="Dan Freeman").first).to_be_visible()
        for width in (800, 390):
            page.set_viewport_size({"width": width, "height": 1000})
            disclosure = page.get_by_role("button", name="Show nearby for", exact=False).first
            if disclosure.get_attribute("aria-expanded") == "false":
                disclosure.click()
            expect(page.locator(".nearby-inline .nearby-photo img").first).to_be_visible()
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.screenshot(path=str(scratch / f"verified-{width}.png"), full_page=True)
        # Arbitrary imported provider IDs never acquire a Google image.
        payload = source()
        payload["days"][0]["activities"][0]["source_place_id"] = "poi-0-0"
        page.goto(base + "/import")
        page.get_by_label("Itinerary JSON", exact=True).fill(json.dumps(payload))
        page.get_by_role("button", name="Preview import", exact=True).click()
        expect(page.get_by_role("heading", name="Old journey", exact=True)).to_be_visible()
        expect(page.locator(".activity-photo img")).to_have_count(0)
        expect(page.locator(".activity-photo").first).to_contain_text(
            "Place photograph unavailable"
        )
        imported_id = page.url.rsplit("/", 1)[-1]
        assert page.request.get(base + f"/api/previews/{imported_id}/media").json()["items"] == {}
        payload["media_bindings"] = {"activity:a": "poi-0-0"}
        page.goto(base + "/import")
        page.get_by_role("button", name="Start new import", exact=True).click()
        page.get_by_label("Itinerary JSON", exact=True).fill(json.dumps(payload))
        page.get_by_role("button", name="Preview import", exact=True).click()
        expect(page.get_by_role("alert")).to_contain_text("media authority")
        another = browser.new_context()
        try:
            other = another.new_page()
            register_browser(other, base)
            trip_id = saved_url.rsplit("/", 1)[-1]
            assert other.request.get(base + f"/api/trips/{trip_id}/media").status == 404
            assert other.request.get(base + f"/api/previews/{preview_id}/media").status == 404
        finally:
            another.close()
    finally:
        (signals / "media-nearby").unlink(missing_ok=True)
        context.close()
