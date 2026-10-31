"""Destination-aware covers and supporting photos through isolated browser/API/DB."""

# Imported pytest fixtures retain their public names.
# ruff: noqa: F811

import os
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from playwright.sync_api import expect

from backend.tests.product.test_browser import browser_app, register_browser  # noqa: F401
from backend.tests.product.test_destination_media import destination_preview


@pytest.mark.parametrize("width", [1440, 390])
def test_city_covers_supporting_reuse_refresh_and_missing_images(browser_app, monkeypatch, width):
    monkeypatch.setenv("DAYLOOM_DB_URL", os.environ["DAYLOOM_DB_TEST_URL"])
    context = browser_app.browser.new_context(viewport={"width": width, "height": 1000})
    scratch = Path(".scratch/destination-media-browser")
    scratch.mkdir(parents=True, exist_ok=True)
    try:
        page = context.new_page()
        register_browser(page, browser_app.base_url)
        owner = context.request.get(browser_app.base_url + "/api/auth/current").json()
        details = {
            city: destination_preview(owner["id"], city)
            for city in ("Melbourne", "New York", "Photo-empty city")
        }
        acquisitions = []
        covers = []

        def cover_cache():
            return page.evaluate(
                "() => (JSON.parse(sessionStorage.getItem('dayloom.photos.session.v1') || '{}')"
                ".entries || []).filter(entry => entry.owner !== null && "
                "entry.resource.startsWith('/api/media/destination?'))"
            )

        def record(request):
            parsed = urlsplit(request.url)
            if parsed.path.endswith("/supporting-media"):
                acquisitions.append((parsed.path, parse_qs(parsed.query).get("slot")))
            if parsed.path == "/api/media/destination":
                covers.append(parse_qs(parsed.query)["destination"][0])

        def open_city(city, cover_identity, activity_identity):
            page.goto(browser_app.base_url + f"/previews/{details[city].id}")
            page.wait_for_function(
                "identity => document.querySelector('.detail-cover img')?.src.includes(identity)",
                arg=cover_identity,
            )
            thumbnail = page.locator('[data-photo-slot="activity:walk"] img')
            expect(thumbnail).to_have_count(1)
            assert activity_identity in thumbnail.get_attribute("src")
            page.locator(".detail-cover img, [data-photo-slot] img").evaluate_all(
                "async images => Promise.all(images.map(image => image.decode()))"
            )

        page.on("request", record)
        open_city("Melbourne", "city-fallback", "melbourne-walk")
        assert len(acquisitions) == 1
        before = cover_cache()
        assert covers == ["Melbourne"] and len(before) == 1
        page.reload()
        page.wait_for_function(
            "document.querySelector('[data-photo-slot=\"activity:walk\"] img')?.naturalWidth > 0"
        )
        assert len(acquisitions) == 1
        assert covers == ["Melbourne"] and cover_cache() == before
        open_city("New York", "new-york-cover", "new-york-walk")
        assert len(acquisitions) == 2
        assert covers == ["Melbourne", "New York"]
        open_city("Melbourne", "city-fallback", "melbourne-walk")
        assert len(acquisitions) == 2
        assert covers == ["Melbourne", "New York"] and len(cover_cache()) == 2
        card = page.locator(".supporting-activity")
        card.get_by_role("button", name="Details", exact=False).click()
        dialog = page.get_by_role("dialog")
        expect(dialog.get_by_text("Atmosphere photo", exact=True)).to_be_visible()
        expect(dialog.get_by_text("Unsplash", exact=True)).to_be_visible()
        dialog.locator("img").evaluate("async image => image.decode()")
        dialog.screenshot(path=str(scratch / f"details-{width}.png"))
        dialog.get_by_role("button", name="Refresh photo", exact=True).click()
        page.wait_for_function(
            "document.querySelector('dialog [data-photo-state=available] img')?.naturalWidth > 0"
        )
        assert len(acquisitions) == 3 and acquisitions[-1][1] == ["activity:walk"]
        assert covers == ["Melbourne", "New York"]
        page.keyboard.press("Escape")
        page.goto(browser_app.base_url + f"/previews/{details['Photo-empty city'].id}")
        expect(page.locator(".detail-cover img")).to_have_attribute("src", "/dayloom/nature.svg")
        page.wait_for_function(
            "document.querySelector('.detail-cover figure')?.dataset.photoState === 'unavailable'"
        )
        expect(page.locator('.supporting-activity [data-photo-slot] img')).to_have_count(0)
        expect(page.locator(".supporting-activity")).to_be_visible()
        page.screenshot(path=str(scratch / f"missing-{width}.png"), full_page=True)
        assert covers == ["Melbourne", "New York", "Photo-empty city"]
        open_city("New York", "new-york-cover", "new-york-walk")
        assert len(covers) == 3
        second = context.new_page()
        second.goto(browser_app.base_url + "/account")
        second.get_by_role("button", name="Log out", exact=True).last.click()
        expect(second.get_by_role("link", name="Log in", exact=True).last).to_be_visible()
        page.wait_for_function(
            "() => !(JSON.parse(sessionStorage.getItem('dayloom.photos.session.v1') || '{}')"
            ".entries || []).some(entry => entry.owner !== null && "
            "entry.resource.startsWith('/api/media/destination?'))"
        )
        assert cover_cache() == []
        expect(page.locator('.detail-cover [data-photo-state="available"]')).to_have_count(0)
    finally:
        context.close()
