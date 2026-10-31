"""Complete controlled Product journey; every intended photo slot is exercised."""

# Imported pytest fixtures retain their public names.
# ruff: noqa: F811

import json
import os
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from playwright.sync_api import expect

from backend.app.main import create_app
from backend.app.product.task_store import TaskStore
from backend.tests.product.activity_media_fixture import complete_media_detail
from backend.tests.product.browser_harness import BROWSER_TEST_SIGNING_KEY, open_json_export
from backend.tests.product.media_fakes import replace_media
from backend.tests.product.test_browser import SCRATCH, browser_app, register_browser  # noqa: F401

CACHE = "dayloom.photos.session.v1"


def cached(page, resource):
    return page.evaluate(
        """([key, resource]) => (JSON.parse(sessionStorage.getItem(key) || '{}').entries || [])
        .filter(entry => entry.resource.split('?')[0].startsWith(resource))
        .sort((a,b) => a.key.localeCompare(b.key))""",
        [CACHE, resource],
    )


def complete_images(page, slots, mobile):
    if mobile:
        expect(page.locator(".nearby-inline-trigger")).to_have_count(
            sum(slot.startswith("nearby:") for slot in slots)
        )
        for button in page.locator(".nearby-inline-trigger").all():
            if button.get_attribute("aria-expanded") == "false":
                button.click()
    page.wait_for_function(
        """slots => slots.every(slot => [...document.querySelectorAll('[data-photo-slot]')]
        .some(el => el.dataset.photoSlot === slot && el.dataset.photoState === 'available'
          && el.getBoundingClientRect().width > 0 && el.querySelector('img')?.naturalWidth > 0
          && el.querySelector('img')?.naturalHeight > 0))""",
        arg=slots,
    )
    page.locator('[data-photo-slot][data-photo-state="available"] img').evaluate_all(
        "async images => { await Promise.all(images.map(image => image.decode())); "
        "if (images.some(image => !(image.naturalWidth > 0 && image.naturalHeight > 0))) "
        "throw new Error('Undecoded photo'); }"
    )


def provider_counts(offset):
    lines = (SCRATCH / "api.log").read_text(encoding="utf-8")[offset:].splitlines()
    return Counter(
        "google"
        if "https://places.googleapis.com/" in line
        else "search"
        if "https://api.unsplash.com/search/photos" in line
        else "adoption"
        if "/photos/supporting-first/download" in line
        else "curated"
        for line in lines
        if "httpx: HTTP Request: GET https://" in line
    )


@pytest.mark.parametrize("width", [1440, 390])
def test_complete_roles_media_lifecycle(browser_app, monkeypatch, width):
    detail, request = complete_media_detail()
    activities = [a for day in detail.days for a in day.activities]
    roles = Counter(a.activity_kind for a in activities)
    themes = {a.atmosphere_theme for a in activities if a.activity_kind == "generic_activity"}
    slots = [f"activity:{a.activity_id}" for a in activities] + [
        f"nearby:{i}" for i in range(len(detail.nearby))
    ]
    # Preflight precedes browser execution. Two cold resources, selected refresh,
    # and one delayed refresh: no product caps, responses or page batches are changed.
    budget = {
        "slots": len(slots),
        "themes": len(themes),
        "metadata_acquisitions": 2 * len(slots) + 2,
        "google": 2 * len(detail._media_bindings) * 2,
        "search": 2 * len(themes) + 2,
        "adoption": 2 * len(themes) + 2,
    }
    print(f"Full-page preflight ({width}px): {budget}")
    assert roles == {"main_poi": 27, "generic_activity": 2}
    assert len(detail.nearby) == 18 and len(slots) == 47
    assert len(detail.transfers) == 9 and themes == {"meal", "walk"}
    base = browser_app.base_url
    monkeypatch.setenv("DAYLOOM_DB_URL", os.environ["DAYLOOM_DB_TEST_URL"])
    monkeypatch.setenv("PRODUCT_JWT_SECRET", BROWSER_TEST_SIGNING_KEY)
    monkeypatch.setenv("PRODUCT_ORIGIN", base)
    monkeypatch.setenv("PRODUCT_ALLOW_INSECURE_LOOPBACK", "true")
    context = browser_app.browser.new_context(
        viewport={"width": width, "height": 1000}, has_touch=width < 800
    )
    try:
        page = context.new_page()
        register_browser(page, base)
        owner = context.request.get(base + "/api/auth/current").json()
        headers = {"Origin": base, "X-CSRF-Token": owner["csrf_token"]}
        task_store = TaskStore()
        task, _ = task_store.accept(owner["id"], str(uuid4()), request, None, date(2026, 10, 31))
        assert task_store.complete(task_store.claim(task["id"]), detail)
        metadata = []

        def record(request):
            parsed = urlsplit(request.url)
            if parsed.path.endswith(("/media", "/supporting-media")):
                metadata.extend(parse_qs(parsed.query).get("slot", []))

        page.on("request", record)
        offset = len((SCRATCH / "api.log").read_text(encoding="utf-8"))
        page.goto(base + f"/previews/{detail.id}")
        complete_images(page, slots, width < 800)
        assert Counter(metadata) == Counter(slots)
        expect(page.get_by_role("region", name="Trip highlights")).to_contain_text("An art museum")
        expect(page.get_by_role("region", name="Needs confirmation")).to_contain_text(
            "A waterfront walk"
        )
        expect(page.get_by_text("matching visits scheduled", exact=False)).to_have_count(0)
        expect(
            page.get_by_text("Some travel details still need checking", exact=False)
        ).to_have_count(0)
        for region in ("Trip highlights", "Needs confirmation"):
            expect(page.get_by_role("region", name=region)).not_to_contain_text("Must include:")
        page.get_by_role("button", name="Save to My trips", exact=True).click()
        page.get_by_role("link", name="View saved itinerary", exact=True).click()
        complete_images(page, slots, width < 800)
        trip_id = urlsplit(page.url).path.rsplit("/", 1)[-1]
        resource = f"/api/trips/{trip_id}/"
        assert Counter(metadata) == Counter({slot: 2 for slot in slots})
        assert cached(page, f"/api/previews/{detail.id}/") == []
        before = cached(page, resource)
        assert len(before) == len(slots)
        page.reload()
        complete_images(page, slots, width < 800)
        assert cached(page, resource) == before  # Original acquisition times and credits.
        assert len(metadata) == 2 * len(slots)

        supporting = page.get_by_role(
            "group", name="Explore local food options on 2026-11-02", exact=True
        )
        principal = page.locator(".principal-visit").first
        assert (
            supporting.locator(".supporting-photo").bounding_box()["width"]
            < principal.locator(".activity-photo").bounding_box()["width"]
        )
        expect(supporting.locator("..").locator(".activity-marker")).to_be_visible()
        assert (
            supporting.evaluate("e => getComputedStyle(e).backgroundColor") == "rgb(255, 255, 255)"
        )
        expect(page.locator(".transfer-connector")).to_have_count(9)
        expect(
            page.locator(".transfer-connector .activity-marker, .transfer-connector img")
        ).to_have_count(0)
        expect(supporting.get_by_text("Atmosphere photo", exact=True)).to_have_count(0)
        expect(supporting.get_by_role("button", name="Photo credits", exact=True)).to_have_count(0)
        details = supporting.get_by_role("button", name="Details", exact=False)
        if width < 800:
            details.tap()
        else:
            details.focus()
            page.keyboard.press("Enter")
        photo_dialog = page.get_by_role("dialog", name="Explore local food options", exact=True)
        expect(
            photo_dialog.get_by_role("link", name="Supporting Photographer", exact=True)
        ).to_be_visible()
        expect(photo_dialog.get_by_text("Atmosphere photo", exact=True)).to_be_visible()
        caption = photo_dialog.locator(".supporting-photo figcaption").bounding_box()
        label = photo_dialog.get_by_text("Atmosphere photo", exact=True).bounding_box()
        frame = photo_dialog.locator(".photo-large").bounding_box()
        assert caption["y"] + caption["height"] <= frame["y"] + frame["height"]
        assert label["y"] + label["height"] <= frame["y"] + frame["height"]
        assert caption["y"] + caption["height"] <= label["y"]
        page.keyboard.press("Escape")
        scratch = Path(".scratch/activity-media-details")
        scratch.mkdir(parents=True, exist_ok=True)
        complete_images(page, slots, width < 800)
        page.screenshot(path=str(scratch / f"full-page-{width}.png"), full_page=True)
        supporting.locator("..").screenshot(path=str(scratch / f"supporting-{width}.png"))
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")

        with page.expect_download() as download:
            open_json_export(page)
        exported = json.loads(Path(download.value.path()).read_text(encoding="utf-8"))
        assert exported["itinerary"]["days"] == detail.model_dump(mode="json")["days"]
        recreated_app = create_app()
        replace_media(recreated_app)
        with TestClient(recreated_app, base_url=base) as recreated:
            for cookie in context.cookies():
                recreated.cookies.set(cookie["name"], cookie["value"])
            reopened = recreated.get(f"/api/trips/{trip_id}")
            assert reopened.status_code == 200
            expected = detail.model_dump(mode="json") | {"id": trip_id}
            assert reopened.json() == expected
            copied = recreated.post(
                "/api/copies",
                headers=headers,
                json={"source_kind": "copied", "source_id": trip_id, "operation_key": str(uuid4())},
            )
            assert copied.status_code == 200, copied.text
            copied_detail = recreated.get(f"/api/trips/{copied.json()['saved_trip_id']}").json()
            assert copied_detail == expected | {
                "id": copied_detail["id"],
                "title": expected["title"] + " (copy)",
            }
            imported = recreated.post(
                "/api/imports", headers=headers | {"X-Import-Key": str(uuid4())}, json=exported
            )
            assert imported.status_code == 200, imported.text
            imported_detail = recreated.get(f"/api/previews/{imported.json()['id']}").json()[
                "snapshot"
            ]
            assert imported_detail["trust"] == "unverified_import"
            assert imported_detail["completion"]["policy_completion"] == "unassessed"
            assert imported_detail["days"] == expected["days"]
            assert "required_experiences" not in imported_detail["completion"]
            assert "_media_bindings" not in imported_detail

        supporting.get_by_role("button", name="Details", exact=False).click()
        dialog = page.get_by_role("dialog", name="Explore local food options", exact=True)
        dialog.get_by_role("button", name="Refresh photo", exact=True).click()
        complete_images(page, slots, width < 800)
        after = cached(page, resource)
        selected = "activity:support-meal"

        def unchanged(rows):
            return [row for row in rows if json.loads(row["key"])[6] != selected]

        assert unchanged(after) == unchanged(before)
        assert metadata[-1] == selected and len(metadata) == 2 * len(slots) + 1
        page.keyboard.press("Escape")

        # Let the real controlled provider finish, but delay delivery until after
        # another tab revokes the account. Its late success must not restore photos.
        held = []

        def hold(route):
            held.append((route, route.fetch()))
            page.evaluate("window.supportingRefreshHeld = true")

        page.route("**/supporting-media?**", hold)
        supporting.get_by_role("button", name="Details", exact=False).click()
        page.get_by_role("dialog").get_by_role("button", name="Refresh photo", exact=True).click()
        page.wait_for_function("window.supportingRefreshHeld === true")
        assert len(held) == 1
        second = context.new_page()
        second.goto(base + "/account")
        second.get_by_role("button", name="Log out", exact=True).last.click()
        expect(second.get_by_role("link", name="Log in", exact=True).last).to_be_visible()
        held[0][0].fulfill(response=held[0][1])
        assert cached(page, resource) == []
        expect(page.locator('[data-photo-slot][data-photo-state="available"]')).to_have_count(0)
        assert context.request.get(base + f"/api/trips/{trip_id}").status == 401
        assert (
            context.request.get(base + f"/api/trips/{trip_id}/media?slot=activity:visit-0").status
            == 401
        )
        assert (
            context.request.get(
                base + f"/api/trips/{trip_id}/supporting-media?slot={selected}"
            ).status
            == 401
        )
        register_browser(second, base)
        assert context.request.get(base + f"/api/trips/{trip_id}").status == 404
        assert (
            context.request.get(base + f"/api/trips/{trip_id}/media?slot=activity:visit-0").status
            == 404
        )
        assert (
            context.request.get(
                base + f"/api/trips/{trip_id}/supporting-media?slot={selected}"
            ).status
            == 404
        )
        assert cached(page, resource) == []
        assert len(metadata) == budget["metadata_acquisitions"]
        counts = provider_counts(offset)
        assert {key: counts[key] for key in ("google", "search", "adoption")} == {
            key: budget[key] for key in ("google", "search", "adoption")
        }
        # Curated covers are separate: two detail mounts, reload, account tab,
        # logout landing and next account library, with up to two covers per mount.
        assert counts["curated"] <= 2 * (2 + 1 + 1 + 1 + 1)
        print(
            f"Full-page result ({width}px): {dict(counts)}, "
            f"metadata slots={len(metadata)}, reload misses=0"
        )
    finally:
        for open_page in context.pages:
            open_page.unroute_all(behavior="ignoreErrors")
        context.close()
