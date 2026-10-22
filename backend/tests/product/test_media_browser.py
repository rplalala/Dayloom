"""Actual V3/Product/PostgreSQL/Chromium media acceptance, external transport only."""

import json
from pathlib import Path

from playwright.sync_api import expect

from backend.tests.product.browser_harness import open_json_export
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
        page.get_by_role("link", name="View full itinerary").click(timeout=30000)
        expect(page.get_by_text("Unsaved preview", exact=True)).to_be_visible()
        expect(page.locator(".activity-photo img").first).to_be_visible()
        expect(page.locator(".activity-photo .media-provider")).to_have_count(0)
        page.get_by_role("button", name="View Place poi-0-1", exact=True).click()
        expect(page.get_by_role("dialog").get_by_role("link", name="Controlled Photographer")).to_be_visible()
        page.keyboard.press("Escape")
        expect(page.locator(".nearby-sidebar-groups .nearby-photo img").first).to_be_visible()
        expect(page.locator(".nearby-sidebar-groups .media-provider")).to_have_count(0)
        assert (signals / "retrieval-entered").exists() and (signals / "retrieval-closed").exists()
        preview_id = page.url.rsplit("/", 1)[-1]
        metadata = page.request.get(base + f"/api/previews/{preview_id}/media").json()
        assert metadata["items"] and all(
            item["kind"] == "verified_place" for item in metadata["items"].values()
        )
        assert len(metadata["items"]) <= 12
        assert page.request.get(base + f"/api/previews/{preview_id}/media?width=1281").status == 422
        assert "media_bindings" not in page.request.get(base + f"/api/previews/{preview_id}").text()
        page.evaluate("scrollTo(0, 0)")
        page.screenshot(path=str(scratch / "corrected-flow-desktop.png"), full_page=True)
        # Only the external image transport fails; Product metadata/persistence remain real.
        page.route(
            "https://lh3.googleusercontent.com/**",
            lambda route: route.fulfill(status=404, body="expired"),
        )
        page.reload()
        expect(page.locator(".activity-photo").first.get_by_label(
            "Illustration", exact=True
        )).to_be_visible()
        page.get_by_role("button", name="Save to My trips", exact=True).click()
        page.get_by_role("link", name="View saved itinerary", exact=True).click()
        expect(page.locator(".activity-photo").first.get_by_label(
            "Illustration", exact=True
        )).to_be_visible()
        saved_url = page.url
        page.goto(base + "/trips")
        expect(page.locator(".trip-card-photo .media-photo img").first).to_be_visible()
        expect(page.locator(".trip-card-photo .media-photo").first).to_contain_text("Unsplash")
        page.goto(saved_url)
        page.unroute("https://lh3.googleusercontent.com/**")
        page.get_by_role("button", name="View Place poi-0-1", exact=True).click()
        page.get_by_role("button", name="Refresh place photos", exact=True).click()
        expect(page.get_by_role("dialog").get_by_role("link", name="Controlled Photographer")).to_be_visible()
        page.keyboard.press("Escape")
        expect(page.locator(".activity-photo img").first).to_be_visible()
        page.reload()
        expect(page.locator(".activity-photo img").first).to_be_visible()
        page.locator(".detail-cover").get_by_role("button", name="Photo credits", exact=True).click()
        expect(page.get_by_role("link", name="Dan Freeman").first).to_be_visible()
        # Copy reuses persisted server bindings; only subsequent display requests resolve photos.
        original_id = saved_url.rsplit("/", 1)[-1]
        copy_posts, generation_posts = [], []
        page.on(
            "request",
            lambda request: (
                copy_posts.append(request.url)
                if request.method == "POST" and request.url.endswith("/api/copies")
                else generation_posts.append(request.url)
                if request.method == "POST" and "/api/planning" in request.url
                else None
            ),
        )
        page.get_by_role("button", name="Make a copy", exact=True).click()
        page.get_by_role("link", name="View saved copy", exact=True).click()
        expect(page.locator(".activity-photo img").first).to_be_visible()
        page.get_by_role("button", name="View Place poi-0-1", exact=True).click()
        expect(page.get_by_role("dialog").get_by_role("link", name="Controlled Photographer")).to_be_visible()
        page.keyboard.press("Escape")
        assert len(copy_posts) == 1 and generation_posts == []
        saved_url = page.url
        assert saved_url.rsplit("/", 1)[-1] != original_id
        account = page.request.get(base + "/api/auth/current").json()
        assert (
            page.request.delete(
                base + f"/api/trips/{original_id}",
                headers={"Origin": base, "X-CSRF-Token": account["csrf_token"]},
                data={"revision": 1, "confirmed": True},
            ).status
            == 204
        )
        page.reload()
        expect(page.locator(".activity-photo img").first).to_be_visible()
        with page.expect_download() as download:
            open_json_export(page)
        exported = Path(download.value.path()).read_text(encoding="utf-8")
        assert "media_bindings" not in exported and "photos/" not in exported
        assert "googleusercontent" not in exported
        for width in (800, 390):
            page.set_viewport_size({"width": width, "height": 1000})
            disclosure = page.get_by_role("button", name="Show nearby for", exact=False).first
            if disclosure.get_attribute("aria-expanded") == "false":
                disclosure.click()
            expect(page.locator(".nearby-inline .nearby-photo img").first).to_be_visible()
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.evaluate("scrollTo(0, 0)")
            page.screenshot(path=str(scratch / f"corrected-flow-{width}.png"), full_page=True)
        # Arbitrary imported provider IDs never acquire a Google image.
        payload = source()
        payload["days"][0]["activities"][0]["source_place_id"] = "poi-0-0"
        page.goto(base + "/import")
        page.get_by_label("Itinerary JSON", exact=True).fill(json.dumps(payload))
        page.get_by_role("button", name="Preview import", exact=True).click()
        expect(page.get_by_role("heading", name="Old journey", exact=True)).to_be_visible()
        expect(page.locator('.activity-photo img[alt$="· place photograph"]')).to_have_count(0)
        expect(page.locator(".activity-photo").first.get_by_label(
            "Illustration", exact=True
        )).to_be_visible()
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


def test_illustrated_lists_detail_credits_and_atmosphere_controls_across_viewports(task_app):  # noqa: F811
    base, browser = task_app.base_url, task_app.browser
    context = browser.new_context(viewport={"width": 1440, "height": 1000})
    scratch = Path(".scratch/product-polish/browser")
    scratch.mkdir(parents=True, exist_ok=True)
    signals = Path(".scratch/task-browser/signals")
    for signal in signals.iterdir():
        if signal.is_file():
            signal.unlink()
    try:
        page = context.new_page()
        register_browser(page, base)
        page.goto(base + "/plan")
        for label, value in (("Destination", "Sydney"), ("Start date", "2026-09-12"),
                             ("End date", "2026-09-13"), ("Travelers", "2"),
                             ("Whole-trip budget", "1800")):
            page.get_by_label(label, exact=True).fill(value)
        (signals / "model-release").touch()
        (signals / "media-nearby").touch()
        page.get_by_role("button", name="Generate itinerary", exact=False).click()
        page.get_by_role("link", name="View full itinerary").click(timeout=30000)
        for width in (1440, 800, 390):
            page.set_viewport_size({"width": width, "height": 1000})
            expect(page.get_by_text("Planning review", exact=False)).to_have_count(0)
            expect(page.locator(".activity-photo .media-provider")).to_have_count(0)
            assert page.locator(".activity-photo img").first.get_attribute("src").startswith("/dayloom/")
            if width <= 800:
                disclosure = page.get_by_role("button", name="Show nearby for", exact=False).first
                if disclosure.get_attribute("aria-expanded") == "false":
                    disclosure.click()
            region = ".nearby-inline" if width <= 800 else ".nearby-sidebar-groups"
            row = page.locator(f"{region} .nearby-item").first
            expect(row.get_by_role("link", name="Controlled Photographer")).to_have_count(0)
            assert row.locator("img").first.get_attribute("src").startswith("/dayloom/")
            details = row.get_by_role("button", name="Details →", exact=True)
            details.focus()
            page.keyboard.press("Enter")
            dialog = page.get_by_role("dialog")
            expect(dialog.get_by_role("img", name="Controlled nearby park · place photograph")).to_be_visible()
            author = dialog.get_by_role("link", name="Controlled Photographer")
            expect(author).to_be_visible()
            credit = dialog.locator("figcaption")
            assert credit.evaluate("el => el.scrollWidth <= el.clientWidth")
            provider = credit.locator(".media-provider")
            assert provider.evaluate("el => getComputedStyle(el).fontSize") == "12px"
            author.focus()
            page.keyboard.press("Tab")
            expect(dialog.get_by_role("link", name="Photo source")).to_be_focused()
            page.screenshot(path=str(scratch / f"place-detail-{width}.png"))
            page.keyboard.press("Escape")
            expect(details).to_be_focused()
            expect(row.get_by_role("link", name="Controlled Photographer")).to_have_count(0)
            page.evaluate("scrollTo(0, 0)")
            figure = page.locator(".detail-cover .atmosphere-photo")
            caption = figure.locator(".photo-credit-content")
            page.mouse.move(0, 0)
            expect(caption).not_to_be_visible()
            figure.get_by_role("button", name="Photo credits", exact=True).focus()
            expect(caption.get_by_role("link", name="Dan Freeman")).to_be_visible()
            page.keyboard.press("Escape")
            expect(caption).not_to_be_visible()
            figure.get_by_role("button", name="Photo credits", exact=True).click()
            expect(caption).to_be_visible()
            assert caption.evaluate("el => el.getBoundingClientRect().left >= 0 && el.getBoundingClientRect().right <= innerWidth")
            figure.get_by_role("button", name="Hide photo credits", exact=True).click()
            expect(caption).not_to_be_visible()
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.screenshot(path=str(scratch / f"illustrated-lists-{width}.png"), full_page=True)
        page.get_by_role("button", name="Save to My trips", exact=True).click()
        page.goto(base + "/trips")
        card = page.locator(".trip-card-photo").first
        caption = card.locator(".photo-credit-content")
        page.mouse.move(0, 0)
        expect(caption).not_to_be_visible()
        card.locator(".media-image-link").hover()
        expect(caption.get_by_role("link", name="Dan Freeman")).to_be_visible()
        page.mouse.move(0, 0)
        expect(caption).not_to_be_visible()
        card.get_by_role("button", name="Photo credits", exact=True).click()
        expect(caption.get_by_role("link", name="Photo source")).to_be_visible()
        card.get_by_role("button", name="Hide photo credits", exact=True).click()
        card.locator(".media-image-link").click()
        expect(page.get_by_text("Saved itinerary", exact=True)).to_be_visible()
        mobile = browser.new_context(storage_state=context.storage_state(), has_touch=True,
                                     is_mobile=True, viewport={"width": 390, "height": 844})
        try:
            touch_page = mobile.new_page()
            touch_page.goto(page.url)
            photo = touch_page.locator(".detail-cover .atmosphere-photo")
            credits = photo.locator(".photo-credit-content")
            expect(credits).not_to_be_visible()
            photo.get_by_role("button", name="Photo credits", exact=True).tap()
            expect(credits.get_by_role("link", name="Dan Freeman")).to_be_visible()
            photo.get_by_role("button", name="Hide photo credits", exact=True).tap()
            expect(credits).not_to_be_visible()
        finally:
            mobile.close()
    finally:
        (signals / "media-nearby").unlink(missing_ok=True)
        context.close()
