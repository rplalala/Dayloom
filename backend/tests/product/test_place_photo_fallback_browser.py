"""Controlled real browser/API/DB check of place and city fallback outcomes."""

# Imported pytest fixtures retain their public names.
# ruff: noqa: F811

import os
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from playwright.sync_api import expect

from backend.tests.product.test_browser import browser_app, register_browser  # noqa: F401
from backend.tests.product.test_place_photo_fallback import fallback_preview

CACHE = "dayloom.photos.session.v1"


def cache(page):
    return page.evaluate(
        "key => (JSON.parse(sessionStorage.getItem(key)||'{}').entries||[])"
        ".filter(e=>e.owner!==null)",
        CACHE,
    )


def settled(page, mobile):
    if mobile:
        button = page.locator(".nearby-inline-trigger")
        expect(button).to_have_count(1)
        if button.get_attribute("aria-expanded") == "false":
            button.click()
    for slot in ("activity:square", "nearby:0", "activity:empty"):
        page.wait_for_function(
            "slot => [...document.querySelectorAll('[data-photo-slot]')].some(e=>"
            "e.dataset.photoSlot===slot&&e.dataset.photoState==='available'&&"
            "e.getBoundingClientRect().width>0&&e.querySelector('img')?.naturalWidth>0&&"
            "e.querySelector('img')?.naturalHeight>0)",
            arg=slot,
        )
    page.locator('[data-photo-state="available"][data-photo-slot] img').evaluate_all(
        "async images=>Promise.all(images.map(image=>image.decode()))"
    )


@pytest.mark.parametrize("width", [1440, 390])
def test_place_fallback_details_reload_single_refresh_and_logout(browser_app, monkeypatch, width):
    monkeypatch.setenv("DAYLOOM_DB_URL", os.environ["DAYLOOM_DB_TEST_URL"])
    base = browser_app.base_url
    context = browser_app.browser.new_context(
        viewport={"width": width, "height": 1000}, has_touch=width < 800
    )
    try:
        page = context.new_page()
        register_browser(page, base)
        owner = context.request.get(base + "/api/auth/current").json()
        detail = fallback_preview(owner["id"], include_empty=True)
        batches = []

        def record(request):
            parsed = urlsplit(request.url)
            if parsed.path.endswith("/media"):
                batches.append(parse_qs(parsed.query).get("slot", []))

        page.on("request", record)
        page.goto(base + f"/previews/{detail.id}")
        settled(page, width < 800)
        assert sorted(batches[0]) == ["activity:empty", "activity:square", "nearby:0"]
        assert len(cache(page)) == 3
        page.get_by_role("button", name="Save to My trips", exact=True).click()
        page.get_by_role("link", name="View saved itinerary", exact=True).click()
        settled(page, width < 800)
        saved_url = page.url
        before = cache(page)
        assert len(before) == 3 and {row["media"]["fallback"] for row in before} == {
            "google_no_photos"
        }
        assert len({row["media"]["image_url"] for row in before}) == 2
        count = len(batches)
        page.reload()
        settled(page, width < 800)
        assert batches[count:] == []
        assert cache(page) == before
        card = page.get_by_role("group", name="Federation Square on 2026-11-01", exact=True)
        expect(card).to_have_class("activity-content principal-visit ")
        expect(card.get_by_text("Atmosphere photo", exact=True)).to_have_count(0)
        card.locator(":scope > .activity-details .activity-actions").get_by_role(
            "button", name="Details", exact=False
        ).click()
        dialog = page.get_by_role("dialog", name="Federation Square", exact=True)
        expect(dialog.get_by_text("Atmosphere photo", exact=True)).to_be_visible()
        expect(dialog.get_by_text("Unsplash", exact=True)).to_be_visible()
        expect(dialog.get_by_text("Google Maps", exact=True)).to_have_count(0)
        caption = dialog.locator("figcaption").bounding_box()
        frame = dialog.locator(".photo-large").bounding_box()
        assert caption["y"] + caption["height"] <= frame["y"] + frame["height"]
        scratch = Path(".scratch/city-photo-fallback-browser")
        scratch.mkdir(parents=True, exist_ok=True)
        dialog.locator("img").evaluate("async image=>image.decode()")
        dialog.screenshot(path=str(scratch / f"details-{width}.png"))
        count = len(batches)
        dialog.get_by_role("button", name="Refresh photo", exact=True).click()
        expect(dialog.locator('figure[data-photo-state="available"]')).to_have_count(1)
        assert batches[count:] == [["activity:square"]]
        after = cache(page)
        assert [row for row in after if "city-fallback" in row["media"]["image_url"]] == [
            row for row in before if "city-fallback" in row["media"]["image_url"]
        ]
        dialog.get_by_role("link", name="Supporting Photographer", exact=True).focus()
        page.keyboard.press("Escape")
        expect(dialog).to_have_count(0)
        missing = fallback_preview(owner["id"], include_empty=True, destination="Photo-empty city")
        page.goto(base + f"/previews/{missing.id}")
        page.wait_for_function(
            "() => ['activity:square','activity:empty','nearby:0'].every(slot=>"
            "[...document.querySelectorAll('[data-photo-slot]')].some(e=>"
            "e.dataset.photoSlot===slot&&e.dataset.photoState==='unavailable'))"
        )
        expect(page.locator('[data-photo-slot="activity:empty"]')).to_have_attribute(
            "data-photo-state", "unavailable"
        )
        expect(
            page.get_by_role("group", name="No photo venue on 2026-11-01").get_by_label(
                "Illustration", exact=True
            )
        ).to_be_visible()
        assert cache(page) == after
        count = len(batches)
        page.goto(saved_url)
        settled(page, width < 800)
        assert batches[count:] == []
        second = context.new_page()
        second.goto(base + "/account")
        second.get_by_role("button", name="Log out", exact=True).last.click()
        expect(second.get_by_role("link", name="Log in", exact=True).last).to_be_visible()
        expect(page.locator('[data-photo-slot][data-photo-state="available"]')).to_have_count(0)
        assert cache(page) == []
    finally:
        context.close()
