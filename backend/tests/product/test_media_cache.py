"""Persistent image URLs are verified through the Product media HTTP interface."""

import httpx
import pytest

from backend.app.product.media import MediaProviders, get_media_providers
from backend.tests.product.media_fakes import media_transport
from backend.tests.product.test_accounts import client, register  # noqa: F401
from backend.tests.product.test_media import bound_preview


@pytest.fixture
def images(client):  # noqa: F811
    calls = []

    def transport(request):
        calls.append(request)
        if request.url.path.endswith("/media"):
            return httpx.Response(200, json={
                "photoUri": f"https://lh3.googleusercontent.com/photo-{len(calls)}",
            })
        return media_transport(request)

    client.app.dependency_overrides[get_media_providers] = lambda: MediaProviders(
        google_key="controlled", unsplash_key="controlled",
        transport=httpx.MockTransport(transport),
    )
    try:
        yield calls
    finally:
        client.app.dependency_overrides.pop(get_media_providers, None)


def test_reloads_and_application_recreation_reuse_persisted_urls(client, images):  # noqa: F811
    from fastapi.testclient import TestClient

    from backend.app.main import create_app

    owner = register(client)
    detail = bound_preview(owner["id"])
    path = f"/api/previews/{detail.id}/media"
    first = client.get(path)
    assert first.status_code == 200
    assert first.json()["items"]["activity:stop"]["status"] == "available"
    assert client.get(path).json() == first.json()
    assert len(images) == 2
    app = create_app()
    app.dependency_overrides[get_media_providers] = (
        client.app.dependency_overrides[get_media_providers]
    )
    with TestClient(app, base_url="http://localhost:5120") as another:
        another.cookies.update(client.cookies)
        assert another.get(path).json() == first.json()
    assert len(images) == 2


def test_single_slot_refresh_compares_versions_and_keeps_other_images(client, images):  # noqa: F811
    owner = register(client)
    detail = bound_preview(owner["id"], {"activity:left": "left", "activity:right": "right"})
    path = f"/api/previews/{detail.id}/media"
    original = client.get(path).json()["items"]
    assert len(images) == 4
    version = original["activity:left"]["cache_revision"]
    params = {"slot": "activity:left", "refresh": version}
    changed = client.get(path, params=params).json()["items"]["activity:left"]
    assert changed["image_url"] != original["activity:left"]["image_url"]
    assert changed["cache_revision"] != version
    assert len(images) == 6
    assert client.get(path, params=params).json()["items"]["activity:left"] == changed
    assert len(images) == 6
    assert client.get(path).json()["items"]["activity:right"] == original["activity:right"]
    assert client.get(path, params={"refresh": version}).status_code == 422
    client.get(path, params={"slot": "activity:left", "refresh": changed["cache_revision"]})
    assert len(images) == 8


def test_cover_and_supporting_urls_survive_save_and_do_not_retrack_adoptions(client, images):  # noqa: F811
    from backend.tests.product.test_destination_media import destination_preview

    owner = register(client)
    detail = destination_preview(owner["id"], "Melbourne")
    root = f"/api/previews/{detail.id}"
    cover = client.get(root + "/cover-media").json()
    supporting = client.get(root + "/supporting-media").json()
    assert cover["status"] == "available"
    assert supporting["items"]["activity:walk"]["status"] == "available"
    assert len(images) == 4
    assert client.get(root + "/cover-media").json() == cover
    assert client.get(root + "/supporting-media").json() == supporting
    saved = client.post(root + "/save", json={}, headers={
        "Origin": "http://localhost:5120", "X-CSRF-Token": owner["csrf_token"],
    }).json()["saved_trip_id"]
    assert client.get(f"/api/trips/{saved}/cover-media").json() == cover
    assert client.get(f"/api/trips/{saved}/supporting-media").json() == supporting
    assert client.get(root + "/cover-media").json() == cover
    assert len(images) == 4


def test_concurrent_misses_and_refreshes_share_one_acquisition(client):  # noqa: F811
    import asyncio
    from concurrent.futures import ThreadPoolExecutor

    owner = register(client)
    detail = bound_preview(owner["id"])
    path = f"/api/previews/{detail.id}/media"
    calls = []

    async def provider(request):
        calls.append(request)
        await asyncio.sleep(0.05)
        return media_transport(request)

    client.app.dependency_overrides[get_media_providers] = lambda: MediaProviders(
        google_key="controlled", transport=httpx.MockTransport(provider),
    )
    try:
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: client.get(path).json(), range(4)))
        assert all(result == results[0] for result in results)
        assert results[0]["items"]["activity:stop"]["status"] == "available"
        assert len(calls) == 2
        version = results[0]["items"]["activity:stop"]["cache_revision"]
        with ThreadPoolExecutor(max_workers=4) as pool:
            refreshed = list(pool.map(lambda _: client.get(path, params={
                "slot": "activity:stop", "refresh": version,
            }).json(), range(4)))
        assert all(result == refreshed[0] for result in refreshed)
        assert refreshed[0]["items"]["activity:stop"]["cache_revision"] != version
        assert len(calls) == 4
    finally:
        client.app.dependency_overrides.pop(get_media_providers, None)


def test_existing_resource_fields_keep_only_safe_successes_and_invalidate_changes(client, images):  # noqa: F811
    import json

    import psycopg
    from psycopg.types.json import Jsonb

    from backend.app.product.database import connect

    owner = register(client)
    detail = bound_preview(owner["id"])
    path = f"/api/previews/{detail.id}/media"
    original = client.get(path).json()
    with connect() as connection:
        assert connection.execute(
            "SELECT to_regclass('app.media_cache') AS name",
        ).fetchone()["name"] is None
        row = connection.execute(
            "SELECT media_cache FROM app.itinerary_previews WHERE id=%s", (detail.id,),
        ).fetchone()
        text = json.dumps(row["media_cache"])
        assert "controlled-key" not in text and "places/left-place/photos/" not in text
        assert "acquired_at" in text and "Controlled Photographer" in text
        with pytest.raises(psycopg.errors.CheckViolation), connection.transaction():
            connection.execute(
                "UPDATE app.itinerary_previews SET media_cache='[]' WHERE id=%s", (detail.id,),
            )
        connection.execute("UPDATE app.itinerary_previews SET media_bindings=%s WHERE id=%s",
                           (Jsonb({"activity:stop": "another-place"}), detail.id))
    assert client.get(path).json() != original
    assert len(images) == 4
    register(client, "another@example.com")
    assert client.get(path).status_code == 404
    assert client.get(f"/api/previews/{detail.id}/cover-media").status_code == 404
    assert len(images) == 4


def test_failed_acquisition_is_not_a_permanent_negative_cache(client):  # noqa: F811
    owner = register(client)
    detail = bound_preview(owner["id"])
    calls = []
    failing = True

    def provider(request):
        calls.append(request)
        return httpx.Response(503) if failing else media_transport(request)

    client.app.dependency_overrides[get_media_providers] = lambda: MediaProviders(
        google_key="controlled", transport=httpx.MockTransport(provider),
    )
    try:
        path = f"/api/previews/{detail.id}/media"
        failed = client.get(path).json()["items"]["activity:stop"]
        assert failed["status"] == "unavailable" and len(calls) == 1
        failing = False
        recovered = client.get(path).json()["items"]["activity:stop"]
        assert recovered["status"] == "available" and len(calls) == 3
        assert client.get(path).json()["items"]["activity:stop"] == recovered
        assert len(calls) == 3
    finally:
        client.app.dependency_overrides.pop(get_media_providers, None)


def test_discard_during_acquisition_cannot_publish_or_resurrect_images(client):  # noqa: F811
    import asyncio
    import threading
    from concurrent.futures import ThreadPoolExecutor

    from backend.app.product.database import connect

    owner = register(client)
    detail = bound_preview(owner["id"])
    entered, release = threading.Event(), threading.Event()

    async def provider(request):
        entered.set()
        await asyncio.to_thread(release.wait, 5)
        return media_transport(request)

    client.app.dependency_overrides[get_media_providers] = lambda: MediaProviders(
        google_key="controlled", transport=httpx.MockTransport(provider),
    )
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(client.get, f"/api/previews/{detail.id}/media")
            try:
                assert entered.wait(5)
                response = client.post(f"/api/previews/{detail.id}/discard", json={
                    "confirmed": True,
                }, headers={
                    "Origin": "http://localhost:5120", "X-CSRF-Token": owner["csrf_token"],
                })
                assert response.status_code == 200
            finally:
                release.set()
            assert future.result(timeout=10).status_code == 404
        with connect() as connection:
            assert connection.execute(
                "SELECT media_cache FROM app.itinerary_previews WHERE id=%s", (detail.id,),
            ).fetchone()["media_cache"] == {}
        assert client.get(f"/api/previews/{detail.id}/media").json()["items"] == {}
    finally:
        release.set()
        client.app.dependency_overrides.pop(get_media_providers, None)
