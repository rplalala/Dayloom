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
        page.get_by_role("link", name="Open task progress").click()
        page.get_by_role("link", name="Open itinerary preview").click(timeout=30000)
        expect(page.get_by_text("Unsaved preview", exact=True)).to_be_visible()
        expect(page.locator(".activity-photo img").first).to_be_visible()
        expect(page.locator(".activity-photo .media-provider").first).to_have_text("Google Maps")
        expect(page.get_by_role("link", name="Controlled Photographer").first).to_be_visible()
        page.get_by_role("button", name="View Place poi-0-1", exact=True).click()
        expect(page.get_by_role("dialog")).to_be_visible()
        page.keyboard.press("Escape")
        expect(page.locator(".nearby-sidebar-groups .nearby-photo img").first).to_be_visible()
        expect(page.locator(".nearby-sidebar-groups .nearby-media").first).to_contain_text(
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
        page.evaluate("scrollTo(0, 0)")
        page.screenshot(path=str(scratch / "corrected-flow-desktop.png"), full_page=True)
        # Only the external image transport fails; Product metadata/persistence remain real.
        page.route(
            "https://lh3.googleusercontent.com/**",
            lambda route: route.fulfill(status=404, body="expired"),
        )
        page.reload()
        expect(page.locator(".activity-photo").first.get_by_label(
            "Place photograph unavailable · illustration", exact=True
        )).to_be_visible()
        page.get_by_role("button", name="Save to My trips", exact=True).click()
        page.get_by_role("link", name="View saved itinerary", exact=True).click()
        expect(page.locator(".activity-photo").first.get_by_label(
            "Place photograph unavailable · illustration", exact=True
        )).to_be_visible()
        saved_url = page.url
        page.goto(base + "/trips")
        expect(page.locator(".trip-card-photo .media-photo img").first).to_be_visible()
        expect(page.locator(".trip-card-photo .media-photo").first).to_contain_text("Unsplash")
        page.goto(saved_url)
        page.unroute("https://lh3.googleusercontent.com/**")
        page.get_by_text("Source and travel information", exact=True).click()
        page.get_by_role("button", name="Refresh place photos", exact=True).click()
        expect(page.locator(".activity-photo img").first).to_be_visible()
        page.reload()
        expect(page.locator(".activity-photo img").first).to_be_visible()
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
        expect(page.get_by_role("link", name="Controlled Photographer").first).to_be_visible()
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
            "Place photograph unavailable · illustration", exact=True
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


def test_nearby_photo_attribution_stays_readable_inside_responsive_rows(task_app):  # noqa: F811
    base, browser = task_app.base_url, task_app.browser
    context = browser.new_context(viewport={"width": 1440, "height": 1000})
    context.route(
        "https://lh3.googleusercontent.com/**",
        lambda route: route.fulfill(
            status=200,
            content_type="image/svg+xml",
            body='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 90">'
            '<rect width="120" height="90" fill="#b8d8d0"/>'
            '<circle cx="90" cy="22" r="11" fill="#f8dd8c"/>'
            '<path d="M0 75L35 30L69 69L91 46L120 80V90H0Z" fill="#427a66"/>'
            '<text x="6" y="84" font-size="7" fill="white">CONTROLLED MEDIA</text></svg>',
        ),
    )
    scratch = Path(".scratch/media-browser")
    scratch.mkdir(parents=True, exist_ok=True)
    signals = Path(".scratch/task-browser/signals")
    for signal in signals.iterdir():
        if signal.is_file():
            signal.unlink()
    failures, measurements = [], []
    try:
        page = context.new_page()
        register_browser(page, base)
        page.goto(base + "/plan")
        for label, value in (
            ("Destination", "Sydney"),
            ("Start date", "2026-09-12"),
            ("End date", "2026-09-13"),
            ("Travelers", "2"),
            ("Whole-trip budget", "1800"),
        ):
            page.get_by_label(label, exact=True).fill(value)
        (signals / "model-release").touch()
        (signals / "media-nearby").touch()
        page.get_by_role("button", name="Generate itinerary", exact=False).click()
        page.get_by_role("link", name="Open task progress").click()
        page.get_by_role("link", name="Open itinerary preview").click(timeout=30000)
        preview_id = page.url.rsplit("/", 1)[-1]
        metadata = page.request.get(base + f"/api/previews/{preview_id}/media").json()
        assert metadata["items"]["nearby:0"]["kind"] == "verified_place"
        for width in (1440, 800, 390):
            page.set_viewport_size({"width": width, "height": 1000})
            provider = page.locator(".activity-photo .media-provider").first
            expect(provider).to_be_visible()
            credit = provider.evaluate("""node => {
                const range = document.createRange(); range.selectNodeContents(node);
                const label = node.getBoundingClientRect();
                const caption = node.parentElement.getBoundingClientRect();
                return {font:getComputedStyle(node).fontSize,
                    whitespace:getComputedStyle(node).whiteSpace,
                    lines:range.getClientRects().length, left:label.left, right:label.right,
                    captionLeft:caption.left, captionRight:caption.right};
            }""")
            assert (
                credit["font"] == "12px"
                and credit["whitespace"] == "nowrap"
                and credit["lines"] == 1
            )
            assert (
                credit["left"] >= credit["captionLeft"]
                and credit["right"] <= credit["captionRight"]
            )
            if width <= 800:
                disclosure = page.get_by_role("button", name="Show nearby for", exact=False).first
                if disclosure.get_attribute("aria-expanded") == "false":
                    disclosure.click()
            region = ".nearby-inline" if width <= 800 else ".nearby-sidebar-groups"
            row = page.locator(f"{region} .nearby-item").first
            expect(
                row.get_by_role("img", name="Controlled nearby park · place photograph")
            ).to_be_visible()
            expect(row.get_by_role("link", name="Controlled Photographer")).to_be_visible()
            bounds = row.evaluate("""row => {
                const box = el => {
                    const r = el.getBoundingClientRect();
                    return {left:r.left, right:r.right, top:r.top, bottom:r.bottom,
                            width:r.width, height:r.height};
                };
                const inside = (child, parent) => child.left >= parent.left - 1 &&
                    child.right <= parent.right + 1 && child.top >= parent.top - 1 &&
                    child.bottom <= parent.bottom + 1;
                const intersects = (a,b) => Math.min(a.right,b.right)-Math.max(a.left,b.left)>1 &&
                    Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)>1;
                const figure = row.querySelector('figure');
                const caption = row.querySelector('figcaption');
                const body = row.querySelector('.nearby-body');
                const photo = row.querySelector('img');
                const r = box(row), f = box(figure), c = box(caption), b = box(body);
                const credits = [...caption.querySelectorAll('a,.media-provider')];
                const clipped = credits.some(credit => {
                    const bounds = box(credit);
                    for (let parent = credit.parentElement; parent; parent = parent.parentElement) {
                        const style = getComputedStyle(parent), limit = box(parent);
                        if (['hidden','clip','auto','scroll'].includes(style.overflowY) &&
                            (bounds.top < limit.top-1 || bounds.bottom > limit.bottom+1)) {
                            return true;
                        }
                        if (['hidden','clip','auto','scroll'].includes(style.overflowX) &&
                            (bounds.left < limit.left-1 || bounds.right > limit.right+1)) {
                            return true;
                        }
                    }
                    return false;
                });
                const image = box(photo);
                return {row:r, figure:f, caption:c, body:b, image, checks:{
                    figureInsideRow:inside(f,r), captionInsideFigure:inside(c,f),
                    creditsInsideFigure:credits.every(credit=>inside(box(credit),f)),
                    captionAvoidsDetails:!intersects(c,b),
                    creditsAvoidDetails:credits.every(credit=>!intersects(box(credit),b)),
                    photoBesideDetails:image.right <= b.left+1 && Math.abs(image.top-b.top)<2,
                    creditsBelowPhotoAndDetails:c.top >= Math.max(image.bottom,b.bottom)-1,
                    creditsNotClipped:!clipped,
                    noCaptionOverflow:caption.scrollWidth <= caption.clientWidth+1,
                }};
            }""")
            measurements.append({"width": width, **bounds})
            issues = [key for key, passed in bounds["checks"].items() if not passed]
            if issues:
                failures.append({"width": width, "failed": issues})
            details = row.get_by_role("button", name="Details →", exact=True)
            details.focus()
            page.keyboard.press("Enter")
            expect(page.get_by_role("dialog")).to_contain_text("Controlled nearby park")
            page.keyboard.press("Escape")
            expect(details).to_be_focused()
            author = row.get_by_role("link", name="Controlled Photographer")
            author.focus()
            page.keyboard.press("Tab")
            expect(row.get_by_role("link", name="Photo source")).to_be_focused()
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.evaluate("scrollTo(0, 0)")
            phase = "attribution-red" if issues else "corrected"
            page.screenshot(path=str(scratch / f"{phase}-{width}.png"), full_page=True)
            row.screenshot(path=str(scratch / f"{phase}-row-{width}.png"))
        phase = "red" if failures else "green"
        (scratch / f"attribution-layout-{phase}.json").write_text(
            json.dumps(measurements, indent=2), encoding="utf-8"
        )
        assert not failures, json.dumps(failures)
    finally:
        (signals / "media-nearby").unlink(missing_ok=True)
        context.close()
