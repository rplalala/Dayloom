"""Actual public example API and r7 desktop/mobile navigation acceptance."""

from pathlib import Path

from playwright.sync_api import expect

from backend.tests.product.test_browser import browser_app as browser_app
from backend.tests.product.test_browser import register_browser

EVIDENCE = Path(__file__).resolve().parents[3] / ".scratch" / "detail-browser"


def test_public_collection_detail_and_account_state_use_real_product_api(browser_app):
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    context = browser_app.browser.new_context(viewport={"width": 1440, "height": 1000})
    try:
        page = context.new_page()
        page.goto(browser_app.base_url + "/trips")
        expect(page.get_by_role("link", name="View details", exact=True)).to_have_count(3)
        page.get_by_role("link", name="Sydney · Three days by the harbour", exact=True).click()
        expect(
            page.get_by_role("heading", name="Sydney · Three days by the harbour")
        ).to_be_visible()
        page.get_by_text("Source and travel information", exact=True).click()
        expect(
            page.get_by_text(
                "Historical example · source claims, not a fresh verification.", exact=False
            )
        ).to_be_visible()
        assert page.request.get(browser_app.base_url + "/api/examples/sydney-example").status == 200
        activity_details = page.locator(".activity-actions").get_by_role(
            "button", name="Details", exact=True
        ).first
        activity_details.click()
        expect(page.get_by_role("dialog")).to_be_visible()
        expect(page.get_by_role("dialog")).to_contain_text(
            "Cost unavailable; not assumed to be free."
        )
        page.keyboard.press("Escape")
        expect(page.get_by_role("dialog")).to_have_count(0)
        expect(activity_details).to_be_focused()
        page.get_by_role("button", name="WALK · 25 min · Unverified source claim (PASS) →").click()
        expect(page.get_by_role("dialog")).to_contain_text(
            "Source claims are not a fresh route or timing check."
        )
        page.keyboard.press("Escape")
        page.goto(browser_app.base_url + "/examples/kyoto-design")
        expect(
            page.get_by_role("heading", name="Kyoto · Gardens and quiet streets")
        ).to_be_visible()
        expect(page.get_by_text("Free time · no fixed place", exact=True).first).to_be_visible()
        register_browser(page, browser_app.base_url)
        expect(page.get_by_role("link", name="View details", exact=True)).to_have_count(0)
        page.goto(browser_app.base_url + "/examples/sydney-example")
        expect(
            page.get_by_role("heading", name="Sydney · Three days by the harbour")
        ).to_be_visible()
        expect(page.get_by_role("link", name="Account settings")).to_be_visible()
        page.screenshot(path=str(EVIDENCE / "account-public-example.png"), full_page=True)
    finally:
        context.close()


def test_nearby_explicit_bidirectional_keyboard_navigation_and_responsive_hierarchy(browser_app):
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    context = browser_app.browser.new_context(
        viewport={"width": 1440, "height": 1000}, reduced_motion="reduce"
    )
    try:
        page = context.new_page()
        page.goto(browser_app.base_url + "/examples/nearby-linking")
        expect(
            page.get_by_role("heading", name="Sydney · Nearby linking scenarios")
        ).to_be_visible()
        first = page.get_by_role("region", name="Nearby for The Rocks on 2026-10-13", exact=True)
        later = page.get_by_role("region", name="Nearby for The Rocks on 2026-10-15", exact=True)
        expect(first.get_by_text("Around this stop · 2 places")).to_be_visible()
        expect(later.get_by_text("Around this stop · 1 places")).to_be_visible()
        expect(first.get_by_text("An evening discovery")).to_have_count(0)
        page.get_by_role("button", name="Collapse nearby for The Rocks on 2026-10-13").click()
        expect(first.get_by_text("A second harbour discovery")).not_to_be_visible()
        jump = page.get_by_role("button", name="Show 2 nearby places for The Rocks on 2026-10-13")
        jump.focus()
        page.keyboard.press("Enter")
        expect(first.get_by_text("A second harbour discovery")).to_be_visible()
        back = page.get_by_role("button", name="Find The Rocks in Day 1 itinerary")
        expect(back).to_be_focused()
        assert first.evaluate("el => getComputedStyle(el).animationName") == "none"
        page.keyboard.press("Enter")
        stop = page.locator('.activity-content[aria-label="The Rocks on 2026-10-13"]')
        expect(stop).to_be_focused()
        expect(stop).to_have_class("activity-content  nearby-linked-selected")
        page.get_by_role("button", name="Day 1 · 2026-10-13", exact=True).click()
        back.click()
        expect(stop).to_be_visible()
        expect(page.get_by_role("button", name="Day 1 · 2026-10-13", exact=True)).to_have_attribute(
            "aria-expanded", "true"
        )
        page.evaluate("window.scrollTo(0, 0)")
        page.screenshot(path=str(EVIDENCE / "nearby-desktop.png"), full_page=True)
        expect(page.locator(".nearby-linked-selected")).to_have_count(0, timeout=4000)
        later.hover()
        page.evaluate("window.scrollTo(0, 900)")
        expect(page.locator(".nearby-linked-selected")).to_have_count(0)
        other = page.get_by_role("region", name="Other nearby references")
        expect(other).to_contain_text("Anchor: missing-activity · Date: 2026-10-14")
        page.get_by_role("button", name="Filter Day 3 · 2026-10-15").click()
        expect(first).to_have_count(0)
        expect(later).to_be_visible()
        expect(other).to_have_count(0)
        page.get_by_role("button", name="All days", exact=True).click()
        for width in (801, 800, 390):
            page.set_viewport_size({"width": width, "height": 1000})
            inline = stop.get_by_role(
                "button", name="Show nearby for The Rocks on 2026-10-13", exact=True
            )
            if width <= 800:
                expect(first).not_to_be_visible()
                expect(inline).to_be_visible()
                expect(inline).to_have_attribute("aria-expanded", "false")
                inline.focus()
                page.keyboard.press("Enter")
                expect(inline).to_be_focused()
                expect(stop.get_by_text("A second harbour discovery")).to_be_visible()
                assert stop.locator(".activity-time, .activity-marker").count() == 0
                expect(other).to_be_visible()
                page.evaluate("window.scrollTo(0, 0)")
                page.screenshot(path=str(EVIDENCE / f"nearby-{width}.png"), full_page=True)
                stop.scroll_into_view_if_needed()
                page.screenshot(path=str(EVIDENCE / f"nearby-{width}-viewport.png"))
                inline.click()
            else:
                expect(first).to_be_visible()
                expect(inline).not_to_be_visible()
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        # A breakpoint change moves focus off the newly hidden representation.
        page.set_viewport_size({"width": 1440, "height": 1000})
        back.focus()
        page.set_viewport_size({"width": 800, "height": 1000})
        expect(
            stop.get_by_role("button", name="Show nearby for The Rocks on 2026-10-13")
        ).to_be_focused()
        page.get_by_role("button", name="Nearby", exact=True).click()
        expect(stop.get_by_text("A second harbour discovery")).to_be_visible()
    finally:
        context.close()
