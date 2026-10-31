"""Controlled real-browser/API/database acceptance for distinct timeline structures."""

import json
from pathlib import Path

import pytest
from playwright.sync_api import expect

from backend.tests.product.browser_harness import open_json_export
from backend.tests.product.test_browser import browser_app, register_browser  # noqa: F401
from backend.tests.product.test_imports import source


@pytest.mark.parametrize("width", [1440, 390])
def test_activity_structures_survive_save_reload_and_keyboard_details(browser_app, width):  # noqa: F811
    context = browser_app.browser.new_context(viewport={"width": width, "height": 1000})
    artifact = source()
    activities = artifact["days"][0]["activities"]
    activities[0].update(title="Art museum", activity_kind="main_poi")
    for aid, title, kind, hour in [
        ("meal", "Lunch by the water", "generic_activity", 12),
        ("ride", "Ride to the harbour", "transport", 13),
        ("old", "Historic museum", "unknown", 14),
    ]:
        activities.append(
            {
                "activity_id": aid,
                "title": title,
                "activity_kind": kind,
                "time_use": "scheduled",
                "start_time": f"2020-01-04T{hour}:00:00",
                "end_time": f"2020-01-04T{hour}:30:00",
                "notes": "Enjoy a relaxed break.",
                "atmosphere_theme": "meal" if aid == "meal" else None,
            }
        )
    del activities[-1]["activity_kind"]  # An actual historical omission, not a guess.
    artifact["transfers"] = [
        {
            "from_activity_id": "a",
            "to_activity_id": "meal",
            "mode": "WALK",
            "provider_duration_seconds": 600,
            "distance_meters": 700,
            "status": "unknown",
            "unknowns": ["Route not verified"],
        }
    ]
    artifact["nearby"] = [{"place_name": "Optional café", "anchor_activity_id": "meal"}]
    try:
        page = context.new_page()
        register_browser(page, browser_app.base_url)
        page.goto(browser_app.base_url + "/import")
        page.get_by_label("Itinerary JSON", exact=True).fill(json.dumps(artifact))
        page.get_by_role("button", name="Preview import", exact=True).click()
        expect(page.get_by_role("heading", name="Old journey", exact=True)).to_be_visible()
        page.get_by_role("button", name="Save to My trips", exact=True).click()
        page.get_by_role("link", name="View saved itinerary", exact=True).click()
        page.reload()
        supporting = page.get_by_role("group", name="Lunch by the water on 2020-01-04", exact=True)
        principal = page.get_by_role("group", name="Art museum on 2020-01-04", exact=True)
        expect(supporting).to_have_class("activity-content supporting-activity ")
        expect(principal).to_have_class("activity-content principal-visit ")
        expect(supporting.get_by_text("12:00–12:30", exact=True)).to_be_visible()
        expect(supporting.get_by_text("Enjoy a relaxed break.", exact=True)).to_be_visible()
        expect(supporting.locator(":scope > figure, .activity-photo")).to_have_count(0)
        marker = supporting.locator("..").locator(".activity-marker")
        expect(marker).to_be_visible()
        assert supporting.evaluate("e => getComputedStyle(e).borderTopStyle") == "solid"
        assert (
            supporting.evaluate("e => getComputedStyle(e).backgroundColor") == "rgb(255, 255, 255)"
        )
        transport = page.get_by_role("button", name="Ride to the harbour · 13:00–13:30", exact=True)
        expect(transport).to_be_visible()
        expect(transport.locator(".activity-marker, img, figure")).to_have_count(0)
        assert (
            transport.locator(".transfer-copy").evaluate("e => getComputedStyle(e).borderTopStyle")
            == "dashed"
        )
        expect(page.locator(".transfer-connector")).to_have_count(2)
        expect(
            page.get_by_role("group", name="Historic museum on 2020-01-04", exact=True)
        ).to_have_class("activity-content unknown-activity ")
        details = supporting.get_by_role("button", name="Details", exact=False)
        details.focus()
        page.keyboard.press("Enter")
        dialog = page.get_by_role("dialog", name="Lunch by the water", exact=True)
        expect(dialog).to_be_visible()
        expect(dialog.locator("img")).to_have_count(0)
        page.keyboard.press("Escape")
        expect(details).to_be_focused()
        transport.focus()
        page.keyboard.press("Enter")
        expect(page.get_by_role("dialog", name="Ride to the harbour", exact=True)).to_be_visible()
        page.keyboard.press("Escape")
        expect(transport).to_be_focused()
        with page.expect_download() as download:
            open_json_export(page)
        exported = json.loads(Path(download.value.path()).read_text(encoding="utf-8"))
        exported_activity = exported["itinerary"]["days"][0]["activities"][1]
        assert exported_activity["activity_kind"] == "generic_activity"
        assert exported_activity["atmosphere_theme"] == "meal"
        assert exported_activity["time_use"] == "scheduled"
        assert exported["itinerary"]["nearby"][0]["anchor_activity_id"] == "meal"
        assert len(exported["itinerary"]["transfers"]) == 1
        scratch = Path(".scratch/activity-roles-browser")
        scratch.mkdir(parents=True, exist_ok=True)
        supporting.scroll_into_view_if_needed()
        page.screenshot(path=str(scratch / f"roles-{width}.png"), full_page=True)
        page.goto(browser_app.base_url + "/import")
        page.get_by_role("button", name="Start new import", exact=True).click()
        page.get_by_label("Itinerary JSON", exact=True).fill(json.dumps(exported))
        page.get_by_role("button", name="Preview import", exact=True).click()
        expect(
            page.get_by_role("group", name="Lunch by the water on 2020-01-04", exact=True)
        ).to_have_class("activity-content supporting-activity ")
    finally:
        context.close()
