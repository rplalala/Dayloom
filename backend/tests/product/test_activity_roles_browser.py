"""Controlled real-browser/API/database acceptance for distinct timeline structures."""

# Imported pytest fixtures retain their public names.
# ruff: noqa: F811

import json
from pathlib import Path

import pytest
from playwright.sync_api import expect

from backend.tests.product.browser_harness import open_json_export
from backend.tests.product.test_browser import browser_app, register_browser  # noqa: F401
from backend.tests.product.test_imports import source
from backend.tests.product.test_saved import pending


def test_generated_experiences_show_distinct_guidance_after_save_and_reload(
    browser_app, monkeypatch
):  # noqa: F811
    import os

    monkeypatch.setenv("DAYLOOM_DB_URL", os.environ["DAYLOOM_DB_TEST_URL"])
    context = browser_app.browser.new_context(viewport={"width": 1440, "height": 1000})
    try:
        page = context.new_page()
        register_browser(page, browser_app.base_url)
        owner = context.request.get(browser_app.base_url + "/api/auth/current").json()
        quotes = ["Must include: an art museum, a waterfront walk."]
        detail = pending(
            owner["id"],
            days=[
                {
                    "date": "2020-01-04",
                    "activities": [
                        {
                            "activity_id": "museum",
                            "title": "An afternoon of art",
                            "place_name": "Art Gallery",
                            "activity_kind": "main_poi",
                            "time_use": "scheduled",
                            "start_time": "2020-01-04T12:00:00+11:00",
                            "end_time": "2020-01-04T13:00:00+11:00",
                        }
                    ],
                }
            ],
            completion={
                "policy_completion": "incomplete",
                "attention_items": [
                    {
                        "title": "Sydney Opera House",
                        "description": (
                            "Your requested visits or dates for this place are not fully arranged."
                        ),
                    }
                ],
                "required_experiences": [
                    {
                        "requirement": "An art museum",
                        "source_quotes": quotes,
                        "target": 1,
                        "scheduled": 1,
                        "frequency": "one_off",
                        "status": "satisfied",
                        "reason": "supported_visit_coverage",
                        "planned_visits": [
                            {
                                "activity_id": "museum",
                                "place_name": "Art Gallery",
                                "date": "2020-01-04",
                            }
                        ],
                    },
                    {
                        "requirement": "A waterfront walk",
                        "source_quotes": quotes,
                        "target": 1,
                        "scheduled": 0,
                        "frequency": "one_off",
                        "status": "unverified",
                        "reason": "matching_evidence_incomplete",
                    },
                ],
            },
        )
        page.goto(browser_app.base_url + f"/previews/{detail.id}")
        expect(page.get_by_role("region", name="Trip highlights")).to_contain_text("An art museum")
        expect(page.get_by_role("region", name="Still to arrange")).to_contain_text(
            "A waterfront walk"
        )
        expect(page.get_by_role("region", name="Still to arrange")).to_contain_text(
            "Sydney Opera House"
        )
        expect(page.get_by_text(quotes[0], exact=True)).to_have_count(0)
        expect(page.get_by_text("matching visits scheduled", exact=False)).to_have_count(0)
        page.get_by_role("button", name="Save to My trips", exact=True).click()
        page.get_by_role("link", name="View saved itinerary", exact=True).click()
        page.reload()
        navigation = page.get_by_role("button", name="View Art Gallery · Jan 4", exact=True)
        navigation.click()
        expect(
            page.get_by_role("group", name="Art Gallery on 2020-01-04", exact=True)
        ).to_be_focused()
        expect(page.get_by_role("region", name="Still to arrange")).to_contain_text(
            "A waterfront walk"
        )
    finally:
        context.close()


@pytest.mark.parametrize("width", [1440, 390])
def test_activity_structures_survive_save_reload_and_keyboard_details(browser_app, width):  # noqa: F811
    context = browser_app.browser.new_context(
        viewport={"width": width, "height": 1000}, has_touch=width < 800
    )
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
    artifact["nearby"] = [
        {"place_name": "Optional café", "anchor_activity_id": "meal"},
        {"place_name": "Optional harbour lookout", "anchor_activity_id": "ride"},
    ]
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
        atmosphere = supporting.locator(".supporting-photo")
        expect(atmosphere.get_by_text("Atmosphere photo", exact=True)).to_be_visible()
        atmosphere.locator("img").evaluate(
            "async image => { await image.decode(); "
            "if (!(image.naturalWidth > 0 && image.naturalHeight > 0)) "
            "throw new Error('Missing image'); }"
        )
        assert (
            atmosphere.bounding_box()["width"]
            < principal.locator(".activity-photo").bounding_box()["width"]
        )
        credit = atmosphere.get_by_role("button", name="Photo credits", exact=True)
        if width < 800:
            credit.tap()
        else:
            credit.focus()
            page.keyboard.press("Enter")
        expect(
            atmosphere.get_by_role("link", name="Supporting Photographer", exact=True)
        ).to_be_visible()
        atmosphere.get_by_role("button", name="Hide photo credits", exact=True).click()
        marker = supporting.locator("..").locator(".activity-marker")
        expect(marker).to_be_visible()
        assert supporting.evaluate("e => getComputedStyle(e).borderTopStyle") == "solid"
        assert (
            supporting.evaluate("e => getComputedStyle(e).backgroundColor") == "rgb(255, 255, 255)"
        )
        transport = page.get_by_role("button", name="Ride to the harbour · 13:00–13:30", exact=True)
        expect(transport).to_be_visible()
        if width > 800:
            page.get_by_role(
                "button", name="Find Ride to the harbour in Day 1 itinerary", exact=True
            ).click()
            expect(transport).to_be_focused()
        else:
            disclosure = page.get_by_role(
                "button", name="Show nearby for Ride to the harbour on 2020-01-04", exact=True
            )
            disclosure.click()
            expect(page.get_by_text("Optional harbour lookout", exact=True).first).to_be_visible()
            disclosure.click()
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
        expect(dialog.locator(".place-photo")).to_have_count(0)
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
