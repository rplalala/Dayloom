"""Saved original requirements reopen without invented facts or profile overlay."""
# ruff: noqa: F811

import json
import re
from pathlib import Path
from uuid import uuid4

import pytest
from playwright.sync_api import expect

from backend.tests.product.browser_harness import (
    expect_recovered_draft_name,
    seed_legacy_draft_title,
)
from backend.tests.product.test_browser import register_browser
from backend.tests.product.test_imports import source
from backend.tests.product.test_task_browser import SCRATCH, task_app  # noqa: F401

REPLAN_SCREENSHOTS = Path(__file__).resolve().parents[3] / ".scratch/replan-browser"


def headers(page, base):
    account = page.request.get(base + "/api/auth/current").json()
    return {"Origin": base, "X-CSRF-Token": account["csrf_token"]}


def save_import(page, base, request):
    response = page.request.post(
        base + "/api/imports",
        data=json.dumps({"request": request, "itinerary": source()}),
        headers={**headers(page, base), "X-Import-Key": str(uuid4())},
    )
    assert response.status == 200
    preview = response.json()
    saved = page.request.post(
        base + f"/api/previews/{preview['id']}/save", headers=headers(page, base), data={}
    )
    assert saved.ok
    return saved.json()["saved_trip_id"]


@pytest.mark.parametrize(
    "original_request", [None, {}, {"destination": "Original destination", "traveler_count": None}]
)
def test_partial_original_request_opens_blank_without_inference_or_generation(
    task_app, original_request
):  # noqa: F811
    base, browser = task_app.base_url, task_app.browser
    context = browser.new_context(viewport={"width": 1440, "height": 1000})
    try:
        page = context.new_page()
        register_browser(page, base)
        trip_id = save_import(page, base, original_request)
        original = page.request.get(base + f"/api/trips/{trip_id}").json()
        page.goto(base + f"/trips/{trip_id}")
        expect(page.get_by_role("heading", name="Old journey", exact=True)).to_be_visible()
        sent = []
        page.on(
            "request", lambda request: sent.append(request.url) if request.method != "GET" else None
        )
        page.get_by_role(
            "button",
            name="Plan again" if original_request else "Plan another journey →",
            exact=True,
        ).click()
        expect(page).to_have_url(base + "/plan")
        for field in (
            "Start date",
            "End date",
            "Travelers",
            "Whole-trip budget",
            "Currency",
            "Places or experiences to include",
            "Additional preferences",
        ):
            expect(page.get_by_label(field, exact=True)).to_have_value("")
        expect(page.get_by_label("Destination", exact=True)).to_have_value(
            "Original destination" if original_request else ""
        )
        assert sent == []
        assert page.request.get(base + f"/api/trips/{trip_id}").json() == original
    finally:
        context.close()


def profile(page, base, currency, notes):
    updated = page.request.put(
        base + "/api/profile",
        headers=headers(page, base),
        data={
            "display_name": "Default Traveler",
            "currency": currency,
            "interests": ["Nature"],
            "pace": "relaxed",
            "transport": ["walk"],
            "notes": notes,
        },
    )
    assert updated.ok
    assert page.request.get(base + "/api/profile").json()["notes"] == notes


def fill_generation_fields(page):
    for label, value in [
        ("Destination", "Sydney"),
        ("Start date", "2026-09-12"),
        ("End date", "2026-09-13"),
        ("Travelers", "2"),
        ("Whole-trip budget", "1800"),
    ]:
        page.get_by_label(label, exact=True).fill(value)
    page.get_by_label("Currency", exact=True).select_option("AUD")
    page.get_by_label("Additional preferences").fill("")


def open_completed_preview_and_save(page, base, task_id):
    page.goto(base + f"/planning/{task_id}")
    page.get_by_role("link", name="Open itinerary preview", exact=False).click(timeout=30000)
    expect(page.get_by_text("Unsaved preview", exact=True)).to_be_visible()
    page.get_by_role("button", name="Save to My trips", exact=True).click()
    page.get_by_role("link", name="View saved itinerary", exact=True).click()
    expect(page.get_by_text("Saved itinerary", exact=True)).to_be_visible()
    return page.url.rsplit("/", 1)[1]


def submit(page, base):
    with page.expect_response(
        lambda response: (
            response.url == base + "/api/planning/tasks" and response.request.method == "POST"
        )
    ) as response:
        page.get_by_role("button", name="Generate itinerary", exact=False).click()
    assert response.value.status == 202
    return response.value.json()


def test_unknown_replan_currency_survives_draft_save_and_reopen_without_defaults(task_app):
    base, browser = task_app.base_url, task_app.browser
    context = browser.new_context()
    executions = SCRATCH / "signals/executions"
    before = executions.read_text().splitlines() if executions.exists() else []
    try:
        page = context.new_page()
        register_browser(page, base)
        trip_id = save_import(page, base, {"destination": "Sydney"})
        original = page.request.get(base + f"/api/trips/{trip_id}").json()
        page.goto(base + f"/trips/{trip_id}")
        page.get_by_role("button", name="Plan again", exact=True).click()
        expect(page.get_by_label("Currency", exact=True)).to_have_value("")
        seed_legacy_draft_title(page, "Unknown original budget currency")
        with page.expect_response(
            lambda response: (
                response.url == base + "/api/drafts" and response.request.method == "POST"
            )
        ) as response:
            page.get_by_role("button", name="Save draft", exact=True).click()
        assert response.value.status == 201, response.value.json()
        draft = response.value.json()
        assert draft["editor"]["currency"] == ""
        for field in ("travelers", "budget", "required", "preferences"):
            assert draft["editor"][field] == ""
        expect(page.get_by_text("Draft saved.", exact=True)).to_be_visible()
        profile(page, base, "JPY", "Only a genuinely new brief may use these defaults")
        reopened = browser.new_context(storage_state=context.storage_state())
        try:
            restored = reopened.new_page()
            restored.goto(base + f"/plan?draft={draft['id']}")
            expect(restored.get_by_label("Currency", exact=True)).to_have_value("")
            expect(restored.get_by_label("Destination", exact=True)).to_have_value("Sydney")
            expect(restored.get_by_label("Additional preferences")).to_have_value("")
            restored.reload()
            expect(restored.get_by_label("Currency", exact=True)).to_have_value("")
            writes = []
            restored.on(
                "request",
                lambda request: writes.append(request.url) if request.method == "POST" else None,
            )
            restored.get_by_role("button", name="Generate itinerary", exact=False).click()
            expect(restored.get_by_role("alert")).to_contain_text("select a supported currency")
            assert writes == []
            rejected = restored.request.post(
                base + "/api/planning/tasks",
                headers=headers(restored, base),
                data={
                    "operation_key": str(uuid4()),
                    "editor_snapshot": draft["editor"],
                    "request": {
                        "destination": "Sydney",
                        "start_date": "2026-09-12",
                        "end_date": "2026-09-13",
                        "traveler_count": 2,
                        "budget": {"amount": "1800", "currency": ""},
                    },
                },
            )
            assert rejected.status == 422
            detail = rejected.json()["detail"]
            locations = (
                [item["loc"] for item in detail] if isinstance(detail, list) else [detail["loc"]]
            )
            assert ["body", "request", "budget", "currency"] in locations
            assert restored.request.get(base + "/api/planning/tasks/recent").json() == []
            assert restored.request.get(base + f"/api/drafts/{draft['id']}").json() == draft
            assert restored.request.get(base + f"/api/trips/{trip_id}").json() == original
        finally:
            reopened.close()
        after = executions.read_text().splitlines() if executions.exists() else []
        assert after == before
    finally:
        context.close()


def test_combined_defaults_drafts_immutable_tasks_saved_and_replan_with_new_generation(task_app):  # noqa: F811
    """All dependent features run together; only external providers are replaced."""
    from backend.tests.product.test_browser import login

    base, browser = task_app.base_url, task_app.browser
    context = browser.new_context(viewport={"width": 1440, "height": 1000})
    REPLAN_SCREENSHOTS.mkdir(parents=True, exist_ok=True)
    signals = SCRATCH / "signals"
    (signals / "model-release").unlink(missing_ok=True)
    try:
        page = context.new_page()
        email = register_browser(page, base)
        profile(page, base, "AUD", "Original profile wording")
        page.goto(base + "/plan")
        expect(page.get_by_label("Additional preferences")).to_have_value(
            re.compile("Original profile wording")
        )
        fill_generation_fields(page)
        seed_legacy_draft_title(page, "Original request draft")
        page.get_by_role("button", name="Save draft", exact=True).click()
        expect(page.get_by_text("Draft saved.", exact=True)).to_be_visible()
        draft_url = page.url
        draft_id = draft_url.split("draft=")[1]
        draft = page.request.get(base + f"/api/drafts/{draft_id}").json()
        task = submit(page, base)
        assert task["request"]["budget"] == {"amount": "1800", "currency": "AUD"}
        expect(page.get_by_role("link", name="Planning task running", exact=True)).to_be_visible()
        profile(page, base, "JPY", "Updated defaults while task runs")
        page.goto(base + "/account")
        expect(page.get_by_label("Default currency")).to_have_value("JPY")
        page.goto(draft_url)
        expect(page.get_by_label("Currency", exact=True)).to_have_value("AUD")
        expect(page.get_by_label("Additional preferences")).to_have_value("")
        page.reload()
        expect(page.get_by_label("Currency", exact=True)).to_have_value("AUD")
        assert page.request.get(base + f"/api/drafts/{draft_id}").json() == draft
        running = page.request.get(base + f"/api/planning/tasks/{task['id']}").json()
        assert running["state"] == "running" and running["request"] == task["request"]
        assert running["editor_snapshot"] == draft["editor"]
        (signals / "model-release").touch()
        generated_id = open_completed_preview_and_save(page, base, task["id"])
        original = page.request.get(base + f"/api/trips/{generated_id}").json()
        assert original["request"]["budget"] == task["request"]["budget"]
        expect(page.get_by_role("button", name="Plan again", exact=True)).to_be_visible()
        page.evaluate("scrollTo(0, 0)")
        page.screenshot(
            path=str(REPLAN_SCREENSHOTS / "saved-plan-again-desktop.png"), full_page=True
        )
        before = len((signals / "executions").read_text().splitlines())
        writes = []
        page.on(
            "request",
            lambda request: writes.append(request.url) if request.method != "GET" else None,
        )
        page.get_by_role("button", name="Plan again", exact=True).click()
        expect(page).to_have_url(base + "/plan")
        expect(page.get_by_label("Destination", exact=True)).to_have_value("Sydney")
        expect(page.get_by_label("Currency", exact=True)).to_have_value("AUD")
        expect(page.get_by_label("Travelers", exact=True)).to_have_value("2")
        expect(page.get_by_label("Whole-trip budget", exact=True)).to_have_value("1800")
        expect(page.get_by_label("Places or experiences to include", exact=True)).to_have_value("")
        expect(page.get_by_label("Additional preferences")).to_have_value("")
        expect_recovered_draft_name(page, "")
        assert writes == [] and len((signals / "executions").read_text().splitlines()) == before
        profile(page, base, "EUR", "Never overlay replan")
        page.goto(base + "/account")
        page.goto(base + "/plan")
        expect(page.get_by_label("Currency", exact=True)).to_have_value("AUD")
        expect(page.get_by_label("Additional preferences")).to_have_value("")
        page.evaluate("scrollTo(0, 0)")
        page.screenshot(
            path=str(REPLAN_SCREENSHOTS / "generated-replan-desktop.png"), full_page=True
        )
        next_task = submit(page, base)
        assert next_task["id"] != task["id"] and next_task["request"] == task["request"]
        next_id = open_completed_preview_and_save(page, base, next_task["id"])
        assert next_id != generated_id
        assert page.request.get(base + f"/api/trips/{generated_id}").json() == original
        assert page.request.get(base + f"/api/drafts/{draft_id}").json() == draft
        assert (
            page.request.get(base + f"/api/planning/tasks/{task['id']}").json()["request"]
            == task["request"]
        )
        # Historical request dates remain original in the form and need explicit correction.
        imported_id = save_import(
            page,
            base,
            {"destination": "Sydney", "start_date": "2020-01-01", "end_date": "2020-01-04"},
        )
        imported = page.request.get(base + f"/api/trips/{imported_id}").json()
        page.goto(base + f"/trips/{imported_id}")
        page.get_by_role("button", name="Plan again", exact=True).click()
        expect(page.get_by_label("Start date", exact=True)).to_have_value("2020-01-01")
        for field in [
            "Travelers",
            "Whole-trip budget",
            "Currency",
            "Places or experiences to include",
            "Additional preferences",
        ]:
            expect(page.get_by_label(field, exact=True)).to_have_value("")
        profile(page, base, "GBP", "Newest defaults for a genuinely new brief")
        page.reload()
        expect(page.get_by_label("Currency", exact=True)).to_have_value("")
        expect(page.get_by_label("Additional preferences")).to_have_value("")
        writes.clear()
        page.get_by_role("button", name="Generate itinerary", exact=False).click()
        expect(page.get_by_role("alert")).to_contain_text("Enter real dates")
        expect(page.get_by_role("alert")).to_contain_text("whole number of travelers")
        expect(page.get_by_role("alert")).to_contain_text("select a supported currency")
        assert writes == []
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.evaluate("scrollTo(0, 0)")
        page.screenshot(
            path=str(REPLAN_SCREENSHOTS / "imported-blank-replan-mobile.png"), full_page=True
        )
        fill_generation_fields(page)
        imported_task = submit(page, base)
        imported_new_id = open_completed_preview_and_save(page, base, imported_task["id"])
        assert imported_new_id not in {generated_id, next_id, imported_id}
        assert page.request.get(base + f"/api/trips/{imported_id}").json() == imported
        assert (signals / "retrieval-entered").exists() and (signals / "retrieval-closed").exists()
        assert len((signals / "executions").read_text().splitlines()) == before + 2
        # Fresh authenticated editor gets current defaults; reopened server draft does not.
        fresh = browser.new_context(storage_state=context.storage_state())
        try:
            reopened = fresh.new_page()
            reopened.goto(base + "/plan")
            expect(reopened.get_by_label("Currency", exact=True)).to_have_value("GBP")
            expect(reopened.get_by_label("Additional preferences")).to_have_value(
                re.compile("Newest defaults")
            )
            reopened.goto(draft_url)
            expect(reopened.get_by_label("Currency", exact=True)).to_have_value("AUD")
            expect(reopened.get_by_label("Additional preferences")).to_have_value("")
        finally:
            fresh.close()
        other = browser.new_context()
        try:
            stranger = other.new_page()
            register_browser(stranger, base)
            for resource in [
                f"/api/trips/{generated_id}",
                f"/api/trips/{imported_id}",
                f"/api/drafts/{draft_id}",
                f"/api/planning/tasks/{task['id']}",
            ]:
                assert stranger.request.get(base + resource).status == 404
            stranger.goto(base + f"/trips/{generated_id}")
            expect(
                stranger.get_by_role(
                    "heading", name="This saved itinerary is unavailable.", exact=True
                )
            ).to_be_visible()
            expect(stranger.get_by_role("button", name="Plan again", exact=True)).to_have_count(0)
        finally:
            other.close()
        # Returning to the original account keeps all source snapshots independently readable.
        page.goto(base + "/login")
        login(page, email)
        assert page.request.get(base + f"/api/trips/{imported_id}").json() == imported
    except Exception:
        page.screenshot(path=str(REPLAN_SCREENSHOTS / "failure.png"), full_page=True)
        (REPLAN_SCREENSHOTS / "failure.html").write_text(page.content(), encoding="utf-8")
        raise
    finally:
        (signals / "model-release").touch()
        context.close()
