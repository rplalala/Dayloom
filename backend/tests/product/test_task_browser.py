"""Real editor/browser/API/PostgreSQL journey with external GeoDB/model substitutes."""

import os
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
from playwright.sync_api import expect, sync_playwright
from pydantic import SecretStr

from backend.tests.product.browser_harness import (
    BrowserApplication,
    isolated_environment,
)
from backend.tests.product.database_safety import require_test_database

ROOT = Path(__file__).resolve().parents[3]
SCRATCH = ROOT / ".scratch" / "task-browser"


@pytest.fixture(scope="module")
def task_app():
    dsn = SecretStr(os.environ.get("PRODUCT_TEST_DATABASE_URL", ""))
    if os.environ.get("PRODUCT_BROWSER_TESTS") != "1" or not dsn.get_secret_value():
        pytest.skip("Enable browser acceptance with an explicitly isolated Product test database")
    require_test_database(dsn)
    SCRATCH.mkdir(parents=True, exist_ok=True)
    api_port = os.environ.get("PRODUCT_TEST_API_PORT", "8202")
    web_port = os.environ.get("PRODUCT_TEST_WEB_PORT", "5202")
    base = f"http://localhost:{web_port}"
    environment = isolated_environment(dsn, api_port, web_port, SCRATCH / "tmp")
    subprocess.run(
        [sys.executable, "scripts/migrate_product.py"], cwd=ROOT, env=environment, check=True
    )
    signals = SCRATCH / "signals"
    signals.mkdir(exist_ok=True)
    for signal in signals.iterdir():
        if signal.is_file():
            signal.unlink()
    processes, outputs = [], []
    try:
        for name, command, directory in [
            (
                "api",
                [sys.executable, "-m", "backend.tests.product.task_server", "--port", api_port],
                ROOT,
            ),
            (
                "vite",
                [
                    "node",
                    str(ROOT / "frontend/node_modules/vite/bin/vite.js"),
                    "--host",
                    "127.0.0.1",
                    "--port",
                    web_port,
                    "--strictPort",
                ],
                ROOT / "frontend",
            ),
        ]:
            output = (SCRATCH / f"{name}.log").open("w", encoding="utf-8")
            outputs.append(output)
            processes.append(
                subprocess.Popen(
                    command, cwd=directory, env=environment, stdout=output, stderr=subprocess.STDOUT
                )
            )
        for endpoint in [f"http://127.0.0.1:{api_port}/health", f"http://127.0.0.1:{web_port}"]:
            deadline = time.monotonic() + 30
            while True:
                try:
                    if httpx.get(endpoint, timeout=1).status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                if time.monotonic() > deadline:
                    raise AssertionError(f"Local editor server did not start: {endpoint}")
                time.sleep(0.1)
        with patch.dict(os.environ, environment, clear=True):
            playwright = sync_playwright().start()
        try:
            browser = playwright.chromium.launch(env=environment)
            try:
                yield BrowserApplication(base, browser)
            finally:
                browser.close()
        finally:
            playwright.stop()
    finally:
        for process in processes:
            process.terminate()
        for process in processes:
            process.wait(timeout=10)
        for output in outputs:
            output.close()


def test_browser_leaves_running_task_edits_b_and_recovers_after_logout(task_app):
    from backend.tests.product.test_browser import login, register_browser

    base, browser = task_app.base_url, task_app.browser
    context = browser.new_context(viewport={"width": 1440, "height": 1000})
    signals = SCRATCH / "signals"
    try:
        page = context.new_page()
        email = register_browser(page, base)
        page.goto(base + "/plan")
        page.get_by_label("Destination", exact=True).fill("Sydney")
        page.get_by_label("Start date", exact=True).fill("2026-09-12")
        page.get_by_label("End date", exact=True).fill("2026-09-13")
        page.get_by_label("Travelers", exact=True).fill("2")
        page.get_by_label("Whole-trip budget", exact=True).fill("1800")
        held_recovery = []
        post_count = []

        def lose_accepted_response(route):
            if route.request.method == "POST" and route.request.url.endswith("/api/planning/tasks"):
                post_count.append("one")
                route.fetch()
                route.abort("failed")
            elif "operation_key=" in route.request.url:
                held_recovery.append(route)
            else:
                route.continue_()

        page.route("**/api/planning/tasks*", lose_accepted_response)
        with page.expect_request(lambda request: "operation_key=" in request.url):
            page.get_by_role("button", name="Generate itinerary", exact=False).click()
        page.get_by_label("Destination", exact=True).fill("Kyoto")
        page.get_by_label("Draft title", exact=True).fill("Brief B while A runs")
        page.get_by_role("button", name="Save draft", exact=True).click()
        expect(page.get_by_text("Draft saved.", exact=False)).to_be_visible()
        assert held_recovery
        held_recovery[0].continue_()
        expect(page.get_by_role("link", name="Planning task running")).to_be_visible()
        expect(page.get_by_label("Destination", exact=True)).to_have_value("Kyoto")
        assert post_count == ["one"]
        # A stale editor observer cannot bind its response to B. The global task entry
        # recovers the accepted A from the canonical account read instead.
        expect(page.get_by_role("link", name="Open task progress")).to_have_count(0)
        accepted_task = page.request.get(base + "/api/planning/tasks/active").json()
        assert accepted_task["request"]["destination"] == "Sydney"
        task_id = accepted_task["id"]
        task_url = "/planning/" + task_id
        page.unroute("**/api/planning/tasks*", lose_accepted_response)
        page.get_by_role("button", name="Generate itinerary", exact=False).click()
        expect(page.get_by_text("Planning is already running.", exact=False)).to_be_visible()
        assert (signals / "executions").read_text().splitlines() == ["one"]
        page.goto(base + task_url)
        expect(page.get_by_role("heading", name="Sydney", exact=True)).to_be_visible()
        page.reload()
        expect(page.get_by_text("You can edit another brief", exact=False)).to_be_visible()
        page.screenshot(path=str(SCRATCH / "running-desktop.png"), full_page=True)
        page.close()
        page = context.new_page()
        page.goto(base + "/account")
        page.get_by_role("button", name="Log out", exact=True).click()
        page.goto(base + "/planning")
        expect(page.get_by_role("heading", name="Your planning tasks are private.")).to_be_visible()
        (signals / "model-release").touch()
        page.goto(base + "/login?return=/planning")
        login(page, email)
        expect(page.get_by_role("heading", name="Planning tasks", exact=True)).to_be_visible()
        expect(page.get_by_role("link", name="Open itinerary preview")).to_be_visible(timeout=30000)
        assert (signals / "executions").read_text().splitlines() == ["one"]
        assert (signals / "retrieval-entered").exists() and (signals / "retrieval-closed").exists()
        page.get_by_role("link", name="Open itinerary preview").click()
        expect(page.get_by_text("Unsaved itinerary preview", exact=True)).to_be_visible()
        preview_url = page.url
        page.reload()
        expect(page.get_by_text("Unsaved itinerary preview", exact=True)).to_be_visible()
        page.screenshot(path=str(SCRATCH / "preview-desktop.png"), full_page=True)
        page.set_viewport_size({"width": 800, "height": 1000})
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        page.screenshot(path=str(SCRATCH / "preview-800.png"), full_page=True)
        page.set_viewport_size({"width": 390, "height": 844})
        expect(page.get_by_role("link", name="Planning tasks", exact=True)).to_be_visible()
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        page.screenshot(path=str(SCRATCH / "preview-390.png"), full_page=True)
        page.goto(base + "/trips")
        expect(page.get_by_text("Brief B while A runs", exact=True)).to_be_visible()
        assert page.get_by_text("Sydney journey", exact=True).count() == 0
        # The task still exposes its submitted A, independently of B and browser recovery.
        snapshot = page.request.get(base + f"/api/planning/tasks/{task_id}").json()
        assert snapshot["state"] == "completed" and snapshot["request"]["destination"] == "Sydney"
        page.goto(preview_url)
        expect(page.get_by_text("Unsaved itinerary preview", exact=True)).to_be_visible()
        saved_responses = []

        def hold_committed_save(route):
            saved_responses.append((route, route.fetch()))

        page.route("**/api/previews/*/save", hold_committed_save)
        page.get_by_role("button", name="Save to My trips", exact=True).click()
        expect(page.get_by_role("button", name="Saving decision…", exact=True)).to_be_visible()
        page.get_by_role("link", name="All recoverable previews →", exact=True).click()
        page.get_by_role("link", name="My trips", exact=True).click()
        page.get_by_role("link", name="Continue planning →", exact=True).click()
        expect(page.get_by_label("Destination", exact=True)).to_have_value("Kyoto")
        assert saved_responses and saved_responses[0][1].status == 200
        saved_responses[0][0].fulfill(response=saved_responses[0][1])
        expect(page.get_by_label("Destination", exact=True)).to_have_value("Kyoto")
        assert "/plan?draft=" in page.url
        page.unroute("**/api/previews/*/save", hold_committed_save)
        page.goto(preview_url)
        expect(page.get_by_text("Saved to My trips.", exact=True)).to_be_visible()
        page.get_by_role("link", name="View saved itinerary", exact=True).click()
        expect(page.get_by_text("Saved itinerary", exact=True)).to_be_visible()
        page.screenshot(path=str(SCRATCH / "saved-390.png"), full_page=True)
        page.set_viewport_size({"width": 800, "height": 1000})
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        page.screenshot(path=str(SCRATCH / "saved-800.png"), full_page=True)
        page.set_viewport_size({"width": 1440, "height": 1000})
        page.screenshot(path=str(SCRATCH / "saved-desktop.png"), full_page=True)
        saved_url = page.url
        page.reload()
        expect(page.get_by_text("Saved itinerary", exact=True)).to_be_visible()
        page.goto(base + "/trips")
        expect(page.get_by_text("Brief B while A runs", exact=True)).to_be_visible()
        page.get_by_role("link", name="View details →", exact=True).click()
        assert page.url == saved_url
        assert (signals / "executions").read_text().splitlines() == ["one"]
    finally:
        context.close()


@pytest.mark.parametrize("decision", ["save", "discard"])
def test_browser_recovers_a_lost_decision_response_without_replaying_write(task_app, decision):
    from backend.tests.product.test_browser import register_browser

    base, browser = task_app.base_url, task_app.browser
    context = browser.new_context(viewport={"width": 1440, "height": 1000})
    try:
        page = context.new_page()
        register_browser(page, base)
        (SCRATCH / "signals/model-release").touch()
        page.goto(base + "/plan")
        for label, value in [
            ("Destination", "Sydney"),
            ("Start date", "2026-09-12"),
            ("End date", "2026-09-13"),
            ("Travelers", "2"),
            ("Whole-trip budget", "1800"),
        ]:
            page.get_by_label(label, exact=True).fill(value)
        page.get_by_role("button", name="Generate itinerary", exact=False).click()
        page.get_by_role("link", name="Open task progress", exact=False).click()
        page.get_by_role("link", name="Open itinerary preview", exact=False).click(timeout=30000)
        preview_url = page.url
        writes = []

        def lose_response(route):
            result = route.fetch()
            assert result.status == 200
            writes.append("one")
            route.abort("failed")

        page.route(f"**/api/previews/*/{decision}", lose_response)
        if decision == "discard":
            page.get_by_role("button", name="Discard preview", exact=True).click()
            expect(page.get_by_role("dialog")).to_be_visible()
            assert writes == []
            page.get_by_role("button", name="Keep preview", exact=True).click()
            expect(page.get_by_text("Unsaved itinerary preview", exact=True)).to_be_visible()
            page.get_by_role("button", name="Discard preview", exact=True).click()
            page.get_by_role("button", name="Confirm discard", exact=True).click()
        else:
            page.get_by_role("button", name="Save to My trips", exact=True).click()
        expected = "Saved to My trips." if decision == "save" else "Preview discarded."
        expect(page.get_by_text(expected, exact=True)).to_be_visible()
        assert writes == ["one"]
        assert page.url == preview_url
        page.reload()
        expect(page.get_by_text(expected, exact=True)).to_be_visible()
        page.goto(base + "/planning")
        expect(page.get_by_text("No pending previews.", exact=True)).to_be_visible()
    finally:
        context.close()
