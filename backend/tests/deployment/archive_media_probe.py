"""Test-only stdin probe for production-image media HTTP and external transport.

This file is excluded from application images with the rest of backend/tests.
It never follows a persisted URL and never sends an external request.
"""

import json
import sys

import httpx
from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.product.media import MediaProviders, MediaSettings, get_media_providers
from backend.app.product.settings import ProductSettings

calls = []


def transport(request):
    calls.append(request)
    assert request.url.host == "places.googleapis.com"
    assert request.headers["X-Goog-Api-Key"] == "controlled-t8-google"
    if request.url.path.endswith("/media"):
        return httpx.Response(
            200, json={"photoUri": "https://lh3.googleusercontent.com/controlled-t8"}
        )
    place = request.url.path.rsplit("/", 1)[-1]
    return httpx.Response(
        200,
        json={
            "photos": [
                {
                    "name": f"places/{place}/photos/controlled",
                    "googleMapsUri": "https://www.google.com/maps/place/?q=controlled",
                    "authorAttributions": [
                        {
                            "displayName": "Controlled Photographer",
                            "uri": "https://www.google.com/maps/contrib/123",
                        }
                    ],
                }
            ]
        },
    )


settings = MediaSettings()
assert settings.google_places_media_key.get_secret_value() == "controlled-t8-google"
application = create_app()
application.dependency_overrides[get_media_providers] = lambda: MediaProviders(
    google_key=settings.google_places_media_key.get_secret_value(),
    unsplash_key=settings.unsplash_access_key.get_secret_value(),
    transport=httpx.MockTransport(transport),
)
origin = ProductSettings().origin
with TestClient(application, base_url=origin) as client:
    login = client.post(
        "/api/auth/login",
        headers={"Origin": origin},
        json={"email": "admin@admin.com", "password": "admin123456"},
    )
    assert login.status_code == 200
    library = client.get("/api/library").json()["items"]
    reusable, candidate = 0, None
    for trip in (item for item in library if item["kind"] == "saved"):
        path = "/api/trips/" + trip["id"] + "/media"
        response = client.get(path)
        assert response.status_code == 200
        original = response.json()["items"]
        reusable += sum(item["status"] == "available" for item in original.values())
        if candidate is None:
            for slot, item in original.items():
                if item["status"] == "available" and item["provider"] == "Google Maps":
                    candidate = path, slot, item, original
                    break
    assert reusable > 0 and len(calls) == 0
    if "--read-only" in sys.argv:
        print(json.dumps({"reused_place_slots": reusable, "read_acquisitions": 0}))
        raise SystemExit(0)
    assert candidate is not None
    path, slot, old, original = candidate
    params = {"slot": slot, "refresh": old["cache_revision"]}
    changed = client.get(path, params=params).json()["items"][slot]
    assert len(calls) == 2
    assert changed["image_url"] == "https://lh3.googleusercontent.com/controlled-t8"
    assert changed["cache_revision"] != old["cache_revision"]
    assert client.get(path, params=params).json()["items"][slot] == changed
    assert len(calls) == 2
    current = client.get(path).json()["items"]
    assert all(current[key] == item for key, item in original.items() if key != slot)
    other = client.post(
        "/api/auth/register",
        headers={"Origin": origin},
        json={
            "email": "archive-owned@example.test",
            "password": "controlled acceptance password",
            "display_name": "Archive Acceptance",
        },
    )
    assert other.status_code in {201, 409}
    if other.status_code == 409:
        assert (
            client.post(
                "/api/auth/login",
                headers={"Origin": origin},
                json={
                    "email": "archive-owned@example.test",
                    "password": "controlled acceptance password",
                },
            ).status_code
            == 200
        )
    assert client.get(path).status_code == 404 and len(calls) == 2
print(
    json.dumps(
        {
            "reused_place_slots": reusable,
            "read_acquisitions": 0,
            "selected_refresh_requests": len(calls),
            "destination_key_verified": True,
            "duplicate_refresh_reused": True,
            "account_boundary": True,
        }
    )
)
