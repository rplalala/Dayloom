"""Built frontend navigation shares the real API application and security boundary."""

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.app.product.application import create_product_application


def test_built_product_serves_navigation_assets_and_the_real_api(tmp_path):
    (tmp_path / "index.html").write_text("<html>Dayloom application</html>", encoding="utf-8")
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "app.js").write_text("window.dayloom = true;", encoding="utf-8")
    with TestClient(create_product_application(tmp_path)) as client:
        for path in ("/", "/plan", "/trips/saved-trip", "/planning/task-id", "/dev"):
            response = client.get(path)
            assert response.status_code == 200
            assert "Dayloom application" in response.text
        assert client.get("/assets/app.js").text == "window.dayloom = true;"
        assert client.get("/health").json() == {"status": "ok"}
        assert client.get("/api/not-a-route").status_code == 404
        assert client.get("/assets/missing.js").status_code == 404
        assert client.get("/dayloom/missing-image").status_code == 404


@pytest.mark.parametrize("explicit_key", [None, "dedicated-media-key"])
def test_curated_media_reads_existing_unsplash_configuration(tmp_path, monkeypatch, explicit_key):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("PRODUCT_UNSPLASH_ACCESS_KEY", raising=False)
    monkeypatch.delenv("UNSPLASH_API_KEY", raising=False)
    (tmp_path / "index.html").write_text("Dayloom", encoding="utf-8")
    configuration = "UNSPLASH_API_KEY=existing-local-key\n"
    if explicit_key:
        configuration += "PRODUCT_UNSPLASH_ACCESS_KEY=" + explicit_key + "\n"
    (tmp_path / ".env").write_text(configuration, encoding="utf-8")
    requests = []

    def provider(request):
        requests.append(request)
        return httpx.Response(200, json={
            "id": "7Zb7kUyQg1E", "urls": {"raw": "https://images.unsplash.com/current"},
            "user": {"name": "Photographer", "links": {"html": "https://unsplash.com/@author"}},
            "links": {"html": "https://unsplash.com/photos/current"},
        })

    original_client = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: original_client(
        **{**kwargs, "transport": httpx.MockTransport(provider)},
    ))
    with TestClient(create_product_application(tmp_path)) as client:
        response = client.get("/api/media/curated/sydney")
        assert response.status_code == 200
        assert response.json()["status"] == "available"
        assert response.json()["authors"][0]["name"] == "Photographer"
        assert response.headers["cache-control"] == "no-store"
        assert requests[0].headers["authorization"] == (
            "Client-ID " + (explicit_key or "existing-local-key")
        )
        assert "existing-local-key" not in response.text
