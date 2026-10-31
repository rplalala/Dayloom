"""Destination covers select one search result through the public media boundary."""

import asyncio
from datetime import date
from uuid import uuid4

import httpx
import pytest

from backend.app.product.detail import ProductDetail
from backend.app.product.media import MediaProviders, get_media_providers
from backend.app.product.task_store import TaskStore
from backend.app.schemas.request import PlanningRequest
from backend.tests.api.test_product_planning import make_product_payload
from backend.tests.product.test_accounts import client, register  # noqa: F401
from backend.tests.product.test_supporting_media import photo


def test_destination_covers_search_each_normalized_city_and_adopt_only_first(client):  # noqa: F811
    calls = []

    def provider(request):
        calls.append(request)
        assert request.url.host == "api.unsplash.com"
        if request.url.path == "/search/photos":
            query = request.url.params["query"]
            assert dict(request.url.params) == {
                "query": query,
                "page": "1",
                "per_page": "1",
                "order_by": "relevant",
                "orientation": "landscape",
                "content_filter": "high",
            }
            identity = "melbourne" if query == "Melbourne" else "new-york"
            return httpx.Response(200, json={"results": [photo(identity), photo("second")]})
        return httpx.Response(200, json={})

    client.app.dependency_overrides[get_media_providers] = lambda: MediaProviders(
        unsplash_key="controlled", transport=httpx.MockTransport(provider)
    )
    try:
        covers = []
        for destination in ("  Melbourne  ", "New   York"):
            response = client.get("/api/media/destination", params={"destination": destination})
            assert response.status_code == 200, response.text
            assert response.headers["cache-control"] == "no-store"
            covers.append(response.json())
        assert [request.url.params["query"] for request in calls[::2]] == [
            "Melbourne",
            "New York",
        ]
        assert [cover["alt"] for cover in covers] == [
            "Melbourne atmosphere",
            "New York atmosphere",
        ]
        assert all(cover["kind"] == "atmosphere" for cover in covers)
        assert "/melbourne?" in covers[0]["image_url"]
        assert "/new-york?" in covers[1]["image_url"]
        assert [request.url.path for request in calls[1::2]] == [
            "/photos/melbourne/download",
            "/photos/new-york/download",
        ]
        assert len(calls) == 4
    finally:
        client.app.dependency_overrides.pop(get_media_providers, None)


@pytest.mark.parametrize("failure", ["empty", "unsafe-first", "rate-limit", "tracking", "timeout"])
def test_cover_failure_never_tries_another_result_or_a_fixed_catalog(client, failure):  # noqa: F811
    calls = []

    def provider(request):
        calls.append(request)
        if failure == "timeout":
            raise httpx.ReadTimeout("Controlled timeout")
        if failure == "rate-limit" or request.url.path.endswith("/download"):
            return httpx.Response(429)
        first = photo("first")
        if failure == "unsafe-first":
            first["urls"]["raw"] = "https://unsafe.invalid/image"
        return httpx.Response(
            200,
            json={
                "results": [] if failure == "empty" else [first, photo("second")],
            },
        )

    client.app.dependency_overrides[get_media_providers] = lambda: MediaProviders(
        unsplash_key="controlled", transport=httpx.MockTransport(provider)
    )
    try:
        response = client.get("/api/media/destination", params={"destination": "Melbourne"})
        assert response.status_code == 200 and response.json() == {"status": "unavailable"}
        assert len(calls) == (2 if failure == "tracking" else 1)
        assert all(request.url.host == "api.unsplash.com" for request in calls)
    finally:
        client.app.dependency_overrides.pop(get_media_providers, None)


def test_cover_rejects_unbounded_labels_and_skips_empty_destinations(client):  # noqa: F811
    def no_network(request):
        raise AssertionError("No provider work expected")

    client.app.dependency_overrides[get_media_providers] = lambda: MediaProviders(
        unsplash_key="controlled", transport=httpx.MockTransport(no_network)
    )
    try:
        for destination in ("", "X" * 121):
            response = client.get("/api/media/destination", params={"destination": destination})
            assert response.status_code == 422
        assert client.get("/api/media/destination", params={"destination": "   "}).json() == {
            "status": "unavailable",
        }
    finally:
        client.app.dependency_overrides.pop(get_media_providers, None)


def test_cover_search_and_adoption_share_one_eight_second_deadline(monkeypatch):
    original_timeout = asyncio.timeout
    cancelled = []

    def bounded_timeout(seconds):
        assert seconds == 8
        return original_timeout(0.01)

    async def provider(request):
        if request.url.path == "/search/photos":
            return httpx.Response(200, json={"results": [photo("first")]})
        try:
            await asyncio.sleep(1)
        finally:
            cancelled.append(True)

    monkeypatch.setattr(asyncio, "timeout", bounded_timeout)
    service = MediaProviders(unsplash_key="controlled", transport=httpx.MockTransport(provider))
    assert asyncio.run(service.destination("Melbourne", 960, 640)) == {"status": "unavailable"}
    assert cancelled == [True]


def destination_preview(owner, destination):
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
        title="Private journey wording",
        destination=destination,
        provenance="generated",
        trust="generated_projection",
        days=[
            {
                "date": "2026-11-01",
                "activities": [
                    {
                        "activity_id": "walk",
                        "title": "Private activity wording",
                        "notes": "Private preferences",
                        "activity_kind": "generic_activity",
                        "time_use": "scheduled",
                        "atmosphere_theme": "walk",
                        "start_time": "2026-11-01T10:00:00+11:00",
                        "end_time": "2026-11-01T11:00:00+11:00",
                    }
                ],
            }
        ],
    )
    assert store.complete(store.claim(task["id"]), detail)
    return detail


def test_supporting_search_reads_each_owned_destination_instead_of_client_or_private_text(client):  # noqa: F811
    owner = register(client)
    calls = []

    def provider(request):
        calls.append(request)
        return httpx.Response(
            200, json={"results": [photo("first")]} if request.url.path == "/search/photos" else {}
        )

    client.app.dependency_overrides[get_media_providers] = lambda: MediaProviders(
        unsplash_key="controlled", transport=httpx.MockTransport(provider)
    )
    try:
        for city in ("Melbourne", "New York"):
            detail = destination_preview(owner["id"], city)
            response = client.get(
                f"/api/previews/{detail.id}/supporting-media",
                params={
                    "slot": "activity:walk",
                    "destination": "Untrusted client text",
                },
            )
            assert response.status_code == 200
            assert response.json()["items"]["activity:walk"]["status"] == "available"
        assert [request.url.params["query"] for request in calls[::2]] == [
            "Melbourne scenic walk",
            "New York scenic walk",
        ]
        assert len(calls) == 4
    finally:
        client.app.dependency_overrides.pop(get_media_providers, None)
