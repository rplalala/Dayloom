"""Retired developer HTTP routes must not expose internal planner results."""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.product.application import create_product_application


@pytest.mark.parametrize("with_frontend", [False, True])
def test_developer_routes_are_absent_from_api_and_product(tmp_path, with_frontend):
    (tmp_path / "index.html").write_text("Dayloom", encoding="utf-8")
    application = create_product_application(tmp_path) if with_frontend else create_app()
    with TestClient(application) as client:
        for path in ("/api/dev/planning", "/api/dev/planning/stream"):
            assert client.post(path, json={}).status_code == 404
        assert not any(path.startswith("/api/dev/") for path in application.openapi()["paths"])
        assert client.get("/health").json() == {"status": "ok"}
