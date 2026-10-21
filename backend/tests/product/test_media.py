"""Media API and provider transport contracts use controlled external responses."""

import asyncio
import json
from datetime import date
from uuid import uuid4

import httpx
import pytest

from backend.app.main import app
from backend.app.product.detail import ProductDetail
from backend.app.product.task_store import TaskStore
from backend.app.schemas.request import PlanningRequest
from backend.tests.api.test_product_planning import make_product_payload
from backend.tests.product.test_accounts import client, register  # noqa: F401


def bound_preview(owner, bindings=None):
    store = TaskStore()
    task, _ = store.accept(
        owner,
        str(uuid4()),
        PlanningRequest.model_validate(make_product_payload()),
        None,
        date(2026, 9, 11),
    )
    bindings = bindings or {"activity:stop": "left-place"}
    detail = ProductDetail(
        id=str(uuid4()),
        title="Photo journey",
        destination="Sydney",
        provenance="generated",
        trust="generated_projection",
        days=[
            {
                "date": "2026-09-12",
                "activities": [
                    {
                        "activity_id": slot.removeprefix("activity:"),
                        "title": "Same display name",
                        "start_time": "2026-09-12T10:00:00+10:00",
                        "end_time": "2026-09-12T11:00:00+10:00",
                    }
                    for slot in bindings
                    if slot.startswith("activity:")
                ],
            }
        ],
    )
    detail._media_bindings = bindings
    assert store.complete(store.claim(task["id"]), detail)
    return detail


def test_owner_media_survives_save_without_public_or_import_authority(client):  # noqa: F811
    from backend.app.product.media import MediaProviders, get_media_providers

    calls = []

    def provider(request):
        calls.append(request)
        if request.url.path.endswith("/media"):
            return httpx.Response(
                200, json={"photoUri": "https://lh3.googleusercontent.com/verified"}
            )
        return httpx.Response(
            200,
            json={
                "photos": [
                    {
                        "name": "places/left-place/photos/current",
                        "authorAttributions": [
                            {
                                "displayName": "Travel Photographer",
                                "uri": "https://www.google.com/maps/contrib/123",
                            }
                        ],
                    }
                ]
            },
        )

    app.dependency_overrides[get_media_providers] = lambda: MediaProviders(
        google_key="controlled-key", transport=httpx.MockTransport(provider)
    )
    try:
        owner = register(client)
        detail = bound_preview(owner["id"])
        # Application-only projection is the input seam; no HTTP body grants identity.
        url = f"/api/previews/{detail.id}/media"
        response = client.get(url)
        assert response.status_code == 200
        assert (
            response.json()["items"]["activity:stop"]["authors"][0]["name"] == "Travel Photographer"
        )
        assert response.headers["cache-control"] == "no-store"
        assert "controlled-key" not in response.text
        assert len(calls) == 2
        assert calls[0].headers["X-Goog-FieldMask"] == "photos"
        assert calls[1].url.params["maxWidthPx"] == "960"
        assert calls[1].url.params["skipHttpRedirect"] == "true"
        assert client.get(url + "?width=4801").status_code == 422
        saved = client.post(
            f"/api/previews/{detail.id}/save",
            json={},
            headers={"Origin": "http://localhost:5120", "X-CSRF-Token": owner["csrf_token"]},
        ).json()["saved_trip_id"]
        assert client.get(f"/api/trips/{saved}/media").json() == response.json()
        assert "left-place" not in client.get(f"/api/trips/{saved}").text
        client.post(
            "/api/auth/logout",
            json={},
            headers={"Origin": "http://localhost:5120", "X-CSRF-Token": owner["csrf_token"]},
        )
        register(client, "other@example.com")
        assert client.get(url).status_code == 404
        assert client.get(f"/api/trips/{saved}/media").status_code == 404
        assert client.get(f"/api/trips/{uuid4()}/media").status_code == 404
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize(
    "fault",
    [
        "missing",
        "expired",
        "redirect",
        "foreign-resource",
        "foreign-image",
        "oversize",
        "attribution",
    ],
)
def test_google_failures_never_become_photos_or_follow_arbitrary_destinations(fault):
    from backend.app.product.media import MediaProviders

    visited = []

    def provider(request):
        visited.append(str(request.url))
        if fault == "redirect":
            return httpx.Response(302, headers={"Location": "https://arbitrary.invalid/private"})
        if fault == "oversize":
            return httpx.Response(200, content=b" " * (256 * 1024 + 1))
        if request.url.path.endswith("/media"):
            if fault == "expired":
                return httpx.Response(404)
            return httpx.Response(
                200,
                json={
                    "photoUri": "https://arbitrary.invalid/private"
                    if fault == "foreign-image"
                    else "https://lh3.googleusercontent.com/valid"
                },
            )
        return httpx.Response(
            200,
            json={
                "photos": []
                if fault == "missing"
                else [
                    {
                        "name": "places/another/photos/current"
                        if fault == "foreign-resource"
                        else "places/verified/photos/current",
                        "authorAttributions": "invalid" if fault == "attribution" else [],
                    }
                ]
            },
        )

    adapter = MediaProviders(google_key="controlled", transport=httpx.MockTransport(provider))
    assert asyncio.run(adapter.google("verified", 960, 640)) == {"status": "unavailable"}
    assert len(visited) <= 2 and all(
        url.startswith("https://places.googleapis.com/") for url in visited
    )


def test_curated_metadata_preserves_hotlink_tracking_current_credit_and_no_download():
    from backend.app.product.media import MediaProviders
    from backend.tests.product.media_fakes import media_transport

    calls = []

    def transport(request):
        calls.append(request)
        return media_transport(request)

    adapter = MediaProviders(unsplash_key="controlled", transport=httpx.MockTransport(transport))
    result = asyncio.run(adapter.curated("sydney", 640))
    assert result["kind"] == "atmosphere"
    assert (
        result["image_url"]
        == "https://images.unsplash.com/controlled-7Zb7kUyQg1E?ixid=controlled-tracking&w=640&h=1280&fit=max&auto=format"
    )
    assert result["authors"][0]["name"] == "Dan Freeman"
    assert "utm_source=dayloom&utm_medium=referral" in result["authors"][0]["url"]
    assert len(calls) == 1 and calls[0].url.path == "/photos/7Zb7kUyQg1E"
    assert asyncio.run(MediaProviders().curated("sydney", 640)) == {"status": "unavailable"}


def test_import_claims_never_create_media_authority(client):  # noqa: F811
    from backend.app.product.media import MediaProviders, get_media_providers

    owner = register(client)
    headers = {"Origin": "http://localhost:5120", "X-CSRF-Token": owner["csrf_token"]}
    from backend.tests.product.test_imports import source

    payload = source()
    # Imported Google source IDs remain source text and grant no display authority.
    payload["days"][0]["activities"][0]["source_place_id"] = "left-place"
    headers["X-Import-Key"] = str(uuid4())
    app.dependency_overrides[get_media_providers] = lambda: MediaProviders(
        google_key="controlled",
        transport=httpx.MockTransport(lambda request: pytest.fail("Import must not call Google")),
    )
    try:
        response = client.post("/api/imports", headers=headers, content=json.dumps(payload))
        assert response.status_code == 200, response.text
        preview = response.json()["id"]
        assert client.get(f"/api/previews/{preview}/media").json()["items"] == {}
        payload["media_bindings"] = {"activity:a": "left-place"}
        headers["X-Import-Key"] = str(uuid4())
        forged = client.post("/api/imports", headers=headers, content=json.dumps(payload))
        assert forged.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_display_batch_limits_provider_work_and_survives_recreation(client):  # noqa: F811
    from backend.app.product.media import MediaProviders, get_media_providers
    from backend.tests.product.media_fakes import media_transport

    calls = []

    def transport(request):
        calls.append(request)
        return media_transport(request)

    adapter = MediaProviders(google_key="controlled", transport=httpx.MockTransport(transport))
    app.dependency_overrides[get_media_providers] = lambda: adapter
    try:
        owner = register(client)
        detail = bound_preview(
            owner["id"], {f"activity:{index}": f"place-{index}" for index in range(15)}
        )
        response = client.get(f"/api/previews/{detail.id}/media?width=200&height=1280")
        assert len(response.json()["items"]) == 12 and len(calls) == 24
        assert all(
            request.url.params["maxHeightPx"] == "1280"
            for request in calls
            if request.url.path.endswith("/media")
        )
        from fastapi.testclient import TestClient

        from backend.app.main import create_app

        recreated = create_app()
        recreated.dependency_overrides[get_media_providers] = lambda: adapter
        with TestClient(recreated, base_url="http://localhost:5120") as another:
            another.cookies.update(client.cookies)
            assert (
                another.get(f"/api/previews/{detail.id}/media").json()["items"]
                == response.json()["items"]
            )
    finally:
        app.dependency_overrides.clear()


def test_media_storage_constraints_and_public_migration_integrity(client, tmp_path):  # noqa: F811
    from pathlib import Path

    import psycopg
    from psycopg.types.json import Jsonb

    from backend.app.product.database import connect, migrate
    from backend.app.product.settings import ProductSettings

    owner = register(client)
    detail = bound_preview(owner["id"])
    with connect() as connection:
        for invalid in (
            [],
            {"activity:stop": "https://arbitrary.invalid/photo"},
            {"nearby:0": 123},
        ):
            with pytest.raises(psycopg.errors.CheckViolation), connection.transaction():
                connection.execute(
                    "UPDATE app.itinerary_previews SET media_bindings=%s WHERE id=%s",
                    (Jsonb(invalid), detail.id),
                )
    dsn = ProductSettings().database_url.get_secret_value()
    assert migrate(dsn) == []
    migration = Path("backend/app/product/migrations/006_media_bindings.sql")
    (tmp_path / migration.name).write_bytes(
        migration.read_bytes() + b"\n-- deliberate checksum change"
    )
    with pytest.raises(ValueError, match="checksum"):
        migrate(dsn, tmp_path)


def test_decided_receipts_erase_bindings_and_never_resurrect_deleted_media(client):  # noqa: F811
    from fastapi.testclient import TestClient

    from backend.app.main import create_app
    from backend.app.product.database import connect
    from backend.app.product.media import MediaProviders, get_media_providers
    from backend.tests.product.media_fakes import media_transport

    owner = register(client)
    headers = {"Origin": "http://localhost:5120", "X-CSRF-Token": owner["csrf_token"]}
    adapter = MediaProviders(
        google_key="controlled", transport=httpx.MockTransport(media_transport)
    )
    app.dependency_overrides[get_media_providers] = lambda: adapter
    try:
        preview = bound_preview(owner["id"])
        saved = client.post(f"/api/previews/{preview.id}/save", json={}, headers=headers).json()
        identity = saved["saved_trip_id"]
        assert client.get(f"/api/trips/{identity}/media").json()["items"]
        with connect() as connection:
            receipt = connection.execute(
                "SELECT media_bindings FROM app.itinerary_previews WHERE id=%s", (preview.id,)
            ).fetchone()
        assert receipt["media_bindings"] == {}
        assert (
            client.request(
                "DELETE",
                f"/api/trips/{identity}",
                json={"confirmed": True, "revision": 1},
                headers=headers,
            ).status_code
            == 204
        )
        assert client.get(f"/api/previews/{preview.id}/media").json()["items"] == {}
        discarded = bound_preview(owner["id"])
        assert (
            client.post(
                f"/api/previews/{discarded.id}/discard", json={"confirmed": True}, headers=headers
            ).status_code
            == 200
        )
        with connect() as connection:
            receipt = connection.execute(
                "SELECT media_bindings FROM app.itinerary_previews WHERE id=%s", (discarded.id,)
            ).fetchone()
        assert receipt["media_bindings"] == {}
        recreated = create_app()
        recreated.dependency_overrides[get_media_providers] = lambda: MediaProviders(
            google_key="controlled",
            transport=httpx.MockTransport(
                lambda request: pytest.fail("Decided receipt must not resolve photos")
            ),
        )
        with TestClient(recreated, base_url="http://localhost:5120") as recovered:
            recovered.cookies.update(client.cookies)
            for item in (preview, discarded):
                assert recovered.get(f"/api/previews/{item.id}/media").json()["items"] == {}
    finally:
        app.dependency_overrides.pop(get_media_providers, None)
