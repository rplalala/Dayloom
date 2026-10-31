"""Actual browser diagnostics through Vite, FastAPI and the local log sink."""
# ruff: noqa: F811

from backend.app.observability.product_logs import ProductLogs, ProductLogSettings
from backend.tests.product.test_browser import SCRATCH, browser_app  # noqa: F401


def test_browser_error_reaches_server_without_message_or_query(browser_app):
    context = browser_app.browser.new_context()
    try:
        page = context.new_page()
        page.goto(browser_app.base_url + "/login")
        with page.expect_response(
            lambda response: (
                response.url.endswith("/api/diagnostics/client-errors")
                and response.request.post_data_json.get("kind") == "global_error"
            )
        ) as pending:
            page.evaluate("setTimeout(() => { throw new TypeError('private-browser-secret'); }, 0)")
        response = pending.value
        assert response.status == 202
        assert "private-browser-secret" not in response.request.post_data
        logs = ProductLogs(ProductLogSettings(directory=SCRATCH / "tmp" / "diagnostics"))
        reports = [row for row in logs.read() if row.get("event") == "client_reported"]
        assert any(
            row["data"].get("kind") == "global_error"
            and row["data"].get("error_type") == "TypeError"
            for row in reports
        )
    finally:
        context.close()
