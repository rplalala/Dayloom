"""Product HTTP logging through the real ASGI boundary."""

import logging

from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.observability.product_logs import ProductLogs


def test_http_logs_return_correlation_without_recording_credentials(tmp_path, monkeypatch):
    monkeypatch.setenv("PRODUCT_LOG_DIRECTORY", str(tmp_path))
    monkeypatch.setenv("PRODUCT_LOG_ENABLED", "true")
    with TestClient(create_app()) as client:
        response = client.get(
            "/health?password=must-not-appear", headers={"Authorization": "Bearer private-token"}
        )
    assert response.status_code == 200
    assert response.headers.get("x-request-id")
    rows = ProductLogs().read()
    assert rows[0]["event"] == "http_completed"
    assert rows[0]["request_id"] == response.headers["x-request-id"]
    assert "must-not-appear" not in str(rows)
    assert "private-token" not in str(rows)


def test_client_diagnostics_enforce_origin_size_and_allowlisted_fields(tmp_path, monkeypatch):
    monkeypatch.setenv("PRODUCT_LOG_DIRECTORY", str(tmp_path))
    monkeypatch.setenv("PRODUCT_LOG_ENABLED", "true")
    monkeypatch.setenv("PRODUCT_ORIGIN", "http://localhost:5173")
    with TestClient(create_app(), base_url="http://localhost:5173") as client:
        path = "/api/diagnostics/client-errors"
        assert client.post(path, json={"kind": "global_error"}).status_code == 403
        headers = {"Origin": "http://localhost:5173"}
        response = client.post(
            path,
            headers=headers,
            json={"kind": "global_error", "error_type": "TypeError", "path": "/plan"},
        )
        assert response.status_code == 202
        assert (
            client.post(
                path, headers=headers, json={"kind": "global_error", "password": "secret"}
            ).status_code
            == 422
        )
        assert client.post(path, headers=headers, content="x" * 5000).status_code == 413
    events = [row for row in ProductLogs().read() if row["event"] == "client_reported"]
    assert events[0]["data"]["error_type"] == "TypeError"


def test_service_exceptions_keep_locations_without_credentials(tmp_path, monkeypatch):
    monkeypatch.setenv("PRODUCT_LOG_DIRECTORY", str(tmp_path))
    monkeypatch.setenv("PRODUCT_LOG_ENABLED", "true")
    with TestClient(create_app()):
        try:
            raise ValueError("private exception payload")
        except ValueError:
            logging.getLogger("product.test").warning("password=private-password", exc_info=True)
    rows = [row for row in ProductLogs().read() if row["event"] == "service_log"]
    assert rows[0]["data"]["error"][0]["type"] == "ValueError"
    assert rows[0]["data"]["error"][0]["frames"]
    assert "private-password" not in str(rows)
    assert "private exception payload" not in str(rows)
