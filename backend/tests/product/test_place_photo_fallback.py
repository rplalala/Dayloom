"""Authorized place photos fall back to first-result atmosphere, never place identity."""

import asyncio
from datetime import date
from uuid import uuid4

import httpx
import pytest

from backend.app.product.detail import ProductDetail
from backend.app.product.media import MediaProviders
from backend.app.product.task_store import TaskStore
from backend.app.schemas.request import PlanningRequest
from backend.tests.api.test_product_planning import make_product_payload
from backend.tests.product.test_accounts import client, register  # noqa: F401
from backend.tests.product.test_supporting_media import photo


@pytest.mark.parametrize("city_has_photo", [True, False])
def test_empty_place_search_tries_city_once_before_illustration(city_has_photo):
    calls, searches = [], []

    def provider(request):
        calls.append(request)
        if request.url.host == "places.googleapis.com":
            return httpx.Response(200, json={"photos": []})
        if request.url.path == "/search/photos":
            query = request.url.params["query"]
            searches.append(query)
            assert request.url.params["per_page"] == "1"
            return httpx.Response(
                200,
                json={
                    "results": [photo("city-first"), photo("second")]
                    if query == "Melbourne" and city_has_photo
                    else []
                },
            )
        assert request.url.path == "/photos/city-first/download"
        return httpx.Response(200, json={"url": "https://images.unsplash.com/city-first"})

    adapter = MediaProviders(
        google_key="controlled", unsplash_key="controlled", transport=httpx.MockTransport(provider)
    )
    result = asyncio.run(
        adapter.google(
            "cafe", 960, 640, fallback_query="Chicamocha Melbourne", city_query="Melbourne"
        )
    )
    assert searches == ["Chicamocha Melbourne", "Melbourne"]
    assert len(calls) == (4 if city_has_photo else 3)
    if city_has_photo:
        assert result["fallback"] == "google_no_photos" and result["kind"] == "atmosphere"
        assert "city-first" in result["image_url"]
    else:
        assert result == {"status": "unavailable"}


def test_google_no_photos_searches_first_unsplash_result_and_tracks_adoption():
    calls = []

    def provider(request):
        calls.append(request)
        if request.url.host == "places.googleapis.com":
            return httpx.Response(200, json={})
        if request.url.path == "/search/photos":
            assert request.url.params["query"] == "Federation Square Melbourne"
            assert request.url.params["per_page"] == "1"
            return httpx.Response(200, json={"results": [photo("first"), photo("second")]})
        assert request.url.path == "/photos/first/download"
        return httpx.Response(200, json={"url": "https://images.unsplash.com/first"})

    adapter = MediaProviders(
        google_key="controlled", unsplash_key="controlled", transport=httpx.MockTransport(provider)
    )
    media = asyncio.run(
        adapter.google(
            "square", 960, 640, fallback_query="Federation Square Melbourne", city_query="Melbourne"
        )
    )
    assert media["status"] == "available"
    assert media["provider"] == "Unsplash" and media["kind"] == "atmosphere"
    assert media["fallback"] == "google_no_photos" and media["theme"] == "general"
    assert "first" in media["image_url"] and "second" not in media["image_url"]
    assert len(calls) == 3


def fallback_preview(owner, *, include_empty=False, destination="Melbourne"):
    store = TaskStore()
    task, _ = store.accept(
        owner,
        str(uuid4()),
        PlanningRequest.model_validate(make_product_payload()),
        None,
        date(2026, 9, 11),
    )
    detail = ProductDetail(
        id=str(uuid4()),
        title="Private trip title",
        destination=destination,
        provenance="generated",
        trust="generated_projection",
        days=[
            {
                "date": "2026-11-01",
                "activities": [
                    {
                        "activity_id": "square",
                        "title": "Private activity wording",
                        "place_name": "Federation Square",
                        "activity_kind": "main_poi",
                        "notes": "Private preference wording",
                        "start_time": "2026-11-01T10:00:00+11:00",
                        "end_time": "2026-11-01T11:00:00+11:00",
                    }
                ],
            }
        ],
        nearby=[
            {
                "place_name": "Chicamocha",
                "anchor_activity_id": "square",
                "associated_day": "2026-11-01",
            }
        ],
    )
    detail._media_bindings = {"activity:square": "square", "nearby:0": "cafe"}
    if include_empty:
        detail.days[0].activities.append(
            detail.days[0]
            .activities[0]
            .model_copy(
                update={
                    "activity_id": "empty",
                    "title": "No photo venue",
                    "place_name": "No photo venue",
                }
            )
        )
        detail._media_bindings["activity:empty"] = "no-photo-empty"
        detail._media_bindings.update(
            {"activity:square": "no-photo-square", "nearby:0": "no-photo-cafe"}
        )
    assert store.complete(store.claim(task["id"]), detail)
    return detail


def test_owned_place_fallbacks_use_public_context_after_save_copy_and_recreation(client):  # noqa: F811
    from fastapi.testclient import TestClient

    from backend.app.main import create_app
    from backend.app.product.media import get_media_providers

    queries = []
    calls = []

    def provider(request):
        calls.append(request)
        assert "Private" not in str(request.url)
        if request.url.host == "places.googleapis.com":
            assert request.headers["X-Goog-FieldMask"] == "photos"
            return httpx.Response(200, json={"photos": []})
        if request.url.path == "/search/photos":
            query = request.url.params["query"]
            queries.append(query)
            return httpx.Response(
                200,
                json={"results": [photo("square" if query.startswith("Federation") else "cafe")]},
            )
        return httpx.Response(200, json={"url": "https://images.unsplash.com/fixture"})

    adapter = MediaProviders(
        google_key="controlled", unsplash_key="controlled", transport=httpx.MockTransport(provider)
    )
    client.app.dependency_overrides[get_media_providers] = lambda: adapter
    try:
        owner = register(client)
        detail = fallback_preview(owner["id"])
        path = f"/api/previews/{detail.id}/media"
        first = client.get(path)
        assert first.status_code == 200, first.text
        assert first.headers["cache-control"] == "no-store"
        items = first.json()["items"]
        assert {m.get("fallback") for m in items.values()} == {"google_no_photos"}
        assert set(queries) == {"Federation Square Melbourne", "Chicamocha Melbourne"}
        assert len(calls) == 6
        headers = {"Origin": "http://localhost:5120", "X-CSRF-Token": owner["csrf_token"]}
        saved = client.post(f"/api/previews/{detail.id}/save", headers=headers, json={}).json()[
            "saved_trip_id"
        ]
        copied = client.post(
            "/api/copies",
            headers=headers,
            json={"source_kind": "copied", "source_id": saved, "operation_key": str(uuid4())},
        ).json()["saved_trip_id"]
        application = create_app()
        application.dependency_overrides[get_media_providers] = lambda: adapter
        with TestClient(application, base_url="http://localhost:5120") as recreated:
            recreated.cookies.update(client.cookies)
            assert recreated.get(f"/api/trips/{saved}/media").json()["items"] == items
            copied_items = recreated.get(f"/api/trips/{copied}/media").json()["items"]
            for slot, media in items.items():
                assert copied_items[slot]["cache_revision"] != media["cache_revision"]
                assert {k: v for k, v in copied_items[slot].items() if k != "cache_revision"} == {
                    k: v for k, v in media.items() if k != "cache_revision"
                }
            assert (
                recreated.get(f"/api/trips/{saved}").json()["days"][0]["activities"][0][
                    "activity_kind"
                ]
                == "main_poi"
            )
        before = len(calls)
        assert client.get(path, params={"slot": "activity:unbound"}).json()["items"] == {
            "activity:unbound": {"status": "unavailable"}
        }
        register(client, "bob@example.com")
        assert client.get(path).status_code == 404
        assert len(calls) == before
    finally:
        client.app.dependency_overrides.pop(get_media_providers, None)


@pytest.mark.parametrize("fault", ["empty", "unsafe-first", "tracking-failure", "no-key"])
def test_unsplash_without_usable_first_photo_returns_illustration_state(fault):
    calls = []

    def provider(request):
        calls.append(request)
        if request.url.host == "places.googleapis.com":
            return httpx.Response(200, json={"photos": []})
        if request.url.path == "/search/photos":
            first = photo("first")
            if fault == "unsafe-first":
                first["urls"]["raw"] = "https://evil.test/image"
            return httpx.Response(
                200, json={"results": [] if fault == "empty" else [first, photo("second")]}
            )
        return httpx.Response(429)

    adapter = MediaProviders(
        google_key="controlled",
        unsplash_key="" if fault == "no-key" else "controlled",
        transport=httpx.MockTransport(provider),
    )
    assert asyncio.run(
        adapter.google(
            "square", 960, 640, fallback_query="Federation Square Melbourne", city_query="Melbourne"
        )
    ) == {"status": "unavailable"}
    assert len(calls) == (
        1 if fault == "no-key" else 3 if fault in {"tracking-failure", "empty"} else 2
    )


@pytest.mark.parametrize(
    "fault",
    [
        "google-success",
        "http-error",
        "timeout",
        "malformed",
        "missing-key",
        "invalid-id",
        "media-error",
    ],
)
def test_fallback_is_only_for_confirmed_missing_google_photos(fault):
    calls = []

    def provider(request):
        calls.append(request)
        assert request.url.host == "places.googleapis.com"
        if fault == "timeout":
            raise httpx.ReadTimeout("Controlled timeout")
        if fault == "http-error" or (
            fault == "media-error" and request.url.path.endswith("/media")
        ):
            return httpx.Response(403)
        if fault == "malformed":
            return httpx.Response(200, json={"photos": "bad payload"})
        if request.url.path.endswith("/media"):
            return httpx.Response(200, json={"photoUri": "https://lh3.googleusercontent.com/photo"})
        return httpx.Response(200, json={"photos": [{"name": "places/square/photos/first"}]})

    adapter = MediaProviders(
        google_key="" if fault == "missing-key" else "controlled",
        unsplash_key="controlled",
        transport=httpx.MockTransport(provider),
    )
    media = asyncio.run(
        adapter.google(
            "bad/id" if fault == "invalid-id" else "square",
            960,
            640,
            fallback_query="Federation Square Melbourne",
            city_query="Melbourne",
        )
    )
    if fault == "google-success":
        assert media["provider"] == "Google Maps" and media["kind"] == "verified_place"
        assert "fallback" not in media
    else:
        assert media == {"status": "unavailable"}
    assert len(calls) <= 2


def test_examples_stay_local_while_fixed_london_cover_keeps_provider_fallback(client):  # noqa: F811
    from backend.app.product.media import get_media_providers

    calls = []

    def provider(request):
        calls.append(request)
        if request.url.host == "places.googleapis.com":
            return httpx.Response(200, json={})
        if request.url.path == "/search/photos":
            if request.url.params["query"] == "Tower Bridge London":
                return httpx.Response(200, json={"results": []})
            return httpx.Response(200, json={"results": [photo("first")]})
        return httpx.Response(200, json={"url": "https://images.unsplash.com/first"})

    adapter = MediaProviders(
        google_key="controlled", unsplash_key="controlled", transport=httpx.MockTransport(provider)
    )
    client.app.dependency_overrides[get_media_providers] = lambda: adapter
    try:
        example = client.get("/api/examples/sydney-example").json()
        slot = "activity:" + example["days"][0]["activities"][0]["activity_id"]
        media = client.get("/api/examples/sydney-example/media", params={"slot": slot}).json()[
            "items"
        ][slot]
        assert media["image_url"].startswith("/dayloom/examples/")
        assert calls == []
        cover = client.get("/api/media/curated/london").json()
        assert cover["fallback"] == "google_no_photos"
        assert cover["alt"] == "London atmosphere"
        assert len(calls) == 4
        assert calls[-2].url.params["query"] == "London"
    finally:
        client.app.dependency_overrides.pop(get_media_providers, None)


def test_fallback_chain_keeps_the_existing_slot_timeout_and_completed_neighbors():
    from fastapi import Response

    from backend.app.product.media import resolve_photos

    cancelled = []

    async def provider(request):
        if request.url.host == "places.googleapis.com":
            return httpx.Response(200, json={})
        if request.url.path == "/search/photos":
            if request.url.params["query"] == "Slow place Melbourne":
                return httpx.Response(200, json={"results": []})
            if request.url.params["query"] == "Melbourne":
                try:
                    await asyncio.sleep(1)
                finally:
                    cancelled.append(True)
            return httpx.Response(200, json={"results": [photo("first")]})
        return httpx.Response(200, json={"url": "https://images.unsplash.com/first"})

    adapter = MediaProviders(
        google_key="controlled", unsplash_key="controlled", transport=httpx.MockTransport(provider)
    )

    async def run():
        result = await resolve_photos(
            [("fast", "square"), ("slow", "cafe")],
            adapter,
            960,
            640,
            Response(),
            fallback_queries={
                "fast": "Federation Square Melbourne",
                "slow": "Slow place Melbourne",
            },
            provider_timeout_seconds=0.02,
            city_query="Melbourne",
        )
        assert result["items"]["fast"]["fallback"] == "google_no_photos"
        assert result["items"]["slow"] == {"status": "unavailable"}
        assert cancelled == [True]

    asyncio.run(run())


def test_city_search_is_not_repeated_when_it_is_already_the_primary_query():
    calls = []

    def provider(request):
        calls.append(request)
        return httpx.Response(
            200, json={} if request.url.host == "places.googleapis.com" else {"results": []}
        )

    adapter = MediaProviders(
        google_key="controlled", unsplash_key="controlled", transport=httpx.MockTransport(provider)
    )
    assert asyncio.run(
        adapter.google("cafe", 960, 640, fallback_query="Melbourne", city_query="Melbourne")
    ) == {"status": "unavailable"}
    assert len(calls) == 2


def test_owned_city_search_uses_destination_without_private_request_text(client):  # noqa: F811
    from backend.app.product.media import get_media_providers

    queries = []

    def provider(request):
        assert "Private" not in str(request.url)
        if request.url.host == "places.googleapis.com":
            return httpx.Response(200, json={})
        if request.url.path == "/search/photos":
            query = request.url.params["query"]
            queries.append(query)
            return httpx.Response(
                200, json={"results": [] if query == "Chicamocha Melbourne" else [photo("city")]}
            )
        return httpx.Response(200, json={"url": "https://images.unsplash.com/city"})

    adapter = MediaProviders(
        google_key="controlled", unsplash_key="controlled", transport=httpx.MockTransport(provider)
    )
    client.app.dependency_overrides[get_media_providers] = lambda: adapter
    try:
        owner = register(client)
        detail = fallback_preview(owner["id"])
        items = client.get(f"/api/previews/{detail.id}/media").json()["items"]
        assert items["nearby:0"]["fallback"] == "google_no_photos"
        assert sorted(queries) == [
            "Chicamocha Melbourne",
            "Federation Square Melbourne",
            "Melbourne",
        ]
    finally:
        client.app.dependency_overrides.pop(get_media_providers, None)
