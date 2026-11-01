"""Public examples use bundled images and expose no guest mutation surface."""

import hashlib
import json
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.product.examples import COLLECTION, example_detail
from backend.app.product.media import get_media_providers

ROOT = Path(__file__).resolve().parents[3]


def test_nearby_venue_photographs_are_local_with_google_source_credits():
    with TestClient(create_app()) as client:
        for example_id, slots in {
            "sydney-example": ("nearby:0", "nearby:1", "nearby:2"),
            "london-example": ("nearby:2",),
        }.items():
            items = client.get(f"/api/examples/{example_id}/media").json()["items"]
            for slot in slots:
                media = items[slot]
                assert media["kind"] == "verified_place"
                assert media["image_url"].startswith("/dayloom/examples/")
                assert media["image_url"].endswith(".jpg")
                assert media["provider"] == "Google Maps"
                assert media["authors"]
                assert media["source_url"].startswith("https://www.google.com/maps/")
                assert media["license_url"] is None


def test_example_media_never_constructs_a_live_provider():
    app = create_app()

    def forbidden():
        raise AssertionError("Examples must not construct provider clients")

    app.dependency_overrides[get_media_providers] = forbidden
    with TestClient(app) as client:
        for example_id in COLLECTION:
            result = client.get(f"/api/examples/{example_id}/media")
            assert result.status_code == 200
            items = result.json()["items"]
            assert set(items) == set(example_detail(example_id)._media_bindings)
            for media in items.values():
                assert media["status"] == "available"
                assert media["image_url"].startswith("/dayloom/examples/")
                assert media["authors"] and media["source_url"]
                if media["provider"] != "Google Maps":
                    assert media["license_url"]


def test_bundled_photographs_match_the_published_asset_manifest():
    manifest = json.loads((ROOT / "backend/app/product/example_media.json").read_text("utf-8"))
    for asset in manifest["assets"].values():
        path = ROOT / "frontend/public" / asset["image_url"].lstrip("/")
        assert path.is_file()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == asset["sha256"]
        assert asset["sha256"][:12] in path.name
        assert path.stat().st_size == asset["bytes"]


def test_guest_requests_cannot_modify_a_public_example():
    with TestClient(create_app()) as client:
        for example_id in COLLECTION:
            url = f"/api/examples/{example_id}"
            before = client.get(url).json()
            for method in (client.put, client.patch, client.delete):
                assert method(url).status_code == 405
            assert client.get(url).json() == before
        assert client.post("/api/copies", json={
            "source_kind": "example", "source_id": "sydney-example", "operation_key": "guest-copy",
        }).status_code == 401


def test_bundled_image_mount_supports_browser_caching_without_a_provider(tmp_path):
    from backend.app.product.application import create_product_application

    (tmp_path / "index.html").write_text("Example frontend", encoding="utf-8")
    source = next((ROOT / "frontend/public/dayloom/examples").glob("*.jpg"))
    target = tmp_path / "dayloom/examples" / source.name
    target.parent.mkdir(parents=True)
    target.write_bytes(source.read_bytes())
    with TestClient(create_product_application(tmp_path)) as client:
        response = client.get(f"/dayloom/examples/{source.name}")
        assert response.status_code == 200
        assert response.content == source.read_bytes()
        assert response.headers["cache-control"] == "public, max-age=31536000, immutable"
        assert client.get(f"/dayloom/examples/{source.name}", headers={
            "If-None-Match": response.headers["etag"],
        }).status_code == 304
        assert client.get("/dayloom/examples/missing.jpg").status_code == 404
