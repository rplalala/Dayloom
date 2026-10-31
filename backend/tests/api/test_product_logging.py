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


def test_uvicorn_access_formatter_keeps_its_structured_arguments():
    from uvicorn.logging import AccessFormatter

    from backend.app.observability.product_service_logs import ServiceRedaction

    record = logging.LogRecord(
        "uvicorn.access",
        logging.INFO,
        __file__,
        1,
        '%s - "%s %s HTTP/%s" %d',
        ("127.0.0.1:1", "GET", "/health?password=private-value", "1.1", 200),
        None,
    )
    ServiceRedaction().filter(record)
    output = AccessFormatter(
        '%(client_addr)s - "%(request_line)s" %(status_code)s', use_colors=False
    ).format(record)
    assert "200 OK" in output
    assert "private-value" not in output


def test_http_audit_retains_validated_resource_ids_for_empty_responses(tmp_path, monkeypatch):
    from uuid import UUID

    from fastapi import Response

    monkeypatch.setenv("PRODUCT_LOG_DIRECTORY", str(tmp_path))
    monkeypatch.setenv("PRODUCT_LOG_ENABLED", "true")
    application = create_app()

    @application.delete("/api/test-resource/{resource_id}")
    def remove(resource_id: UUID):
        return Response(status_code=204)

    resource_id = "4bfac526-f5d1-40f2-844b-5c4808169968"
    with TestClient(application) as client:
        assert client.delete("/api/test-resource/" + resource_id).status_code == 204
    row = next(row for row in ProductLogs().read() if row["event"] == "http_completed")
    assert row["data"]["resource_id"] == resource_id


def test_media_fallback_reason_is_recorded_without_credentials(tmp_path, monkeypatch):
    import asyncio

    from backend.app.product.media import MediaProviders

    monkeypatch.setenv("PRODUCT_LOG_DIRECTORY", str(tmp_path))
    monkeypatch.setenv("PRODUCT_LOG_ENABLED", "true")
    assert asyncio.run(MediaProviders().google("place-one", 960, 640)) == {"status": "unavailable"}
    event = next(row for row in ProductLogs().read() if row["event"] == "media_unavailable")
    assert event["data"] == {"provider": "google", "reason": "credentials_missing"}
