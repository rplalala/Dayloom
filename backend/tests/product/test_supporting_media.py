"""First-result atmosphere selection uses controlled media transport only."""

import asyncio

import httpx
import pytest

from backend.app.product.media import MediaProviders
from backend.tests.product.test_accounts import client, register  # noqa: F401
from backend.tests.product.test_saved import pending


def photo(identity):
    return {
        "id": identity,
        "urls": {"raw": f"https://images.unsplash.com/{identity}?ixid=kept"},
        "links": {
            "html": f"https://unsplash.com/photos/{identity}",
            "download_location": f"https://api.unsplash.com/photos/{identity}/download?ixid=kept",
        },
        "user": {
            "name": "Fixture Photographer",
            "links": {"html": "https://unsplash.com/@fixture"},
        },
    }


@pytest.mark.parametrize("invalid_first", [False, True])
@pytest.mark.parametrize("destination", ["Melbourne", "New York"])
def test_search_selects_only_first_result_and_tracks_only_valid_new_adoption(
    invalid_first, destination
):
    calls = []

    def provider(request):
        calls.append(request)
        if request.url.path == "/search/photos":
            assert dict(request.url.params) == {
                "query": f"{destination} relaxed meal",
                "page": "1",
                "per_page": "1",
                "order_by": "relevant",
                "orientation": "landscape",
                "content_filter": "high",
            }
            first = photo("first")
            if invalid_first:
                first["urls"]["raw"] = "https://evil.test/photo"
            return httpx.Response(200, json={"results": [first, photo("second")]})
        assert request.url.path == "/photos/first/download"
        return httpx.Response(200, json={"url": "https://images.unsplash.com/first"})

    service = MediaProviders(unsplash_key="controlled", transport=httpx.MockTransport(provider))
    result = asyncio.run(service.supporting("meal", 960, 640, destination=destination))
    assert result["status"] == ("unavailable" if invalid_first else "available")
    assert len(calls) == (1 if invalid_first else 2)
    if not invalid_first:
        assert result["kind"] == "atmosphere" and result["theme"] == "meal"
        assert "first" in result["image_url"] and "ixid=kept" in result["image_url"]
        assert result["authors"][0]["name"] == "Fixture Photographer"


@pytest.mark.parametrize(
    "failure", ["empty", "unsafe-profile", "unsafe-tracking", "rate-limit", "timeout"]
)
def test_search_failures_do_not_retry_or_select_another_photo(failure):
    calls = []

    def provider(request):
        calls.append(request)
        if failure == "rate-limit":
            return httpx.Response(429)
        if failure == "timeout":
            raise httpx.ReadTimeout("Controlled timeout")
        first = photo("first")
        if failure == "unsafe-profile":
            first["user"]["links"]["html"] = "https://evil.test/profile"
        if failure == "unsafe-tracking":
            first["links"]["download_location"] = "https://api.unsplash.com/photos/other/download"
        return httpx.Response(
            200, json={"results": [] if failure == "empty" else [first, photo("second")]}
        )

    service = MediaProviders(unsplash_key="controlled", transport=httpx.MockTransport(provider))
    assert asyncio.run(service.supporting("meal", 360, 240, destination="Melbourne"))[
        "status"
    ] == "unavailable"
    assert len(calls) == 1


def test_missing_access_and_unknown_theme_do_not_send_provider_requests():
    def no_network(request):
        raise AssertionError("No request expected")

    assert (
        asyncio.run(
            MediaProviders(transport=httpx.MockTransport(no_network)).supporting(
                "meal", 360, 240, destination="Melbourne"
            )
        )["status"]
        == "unavailable"
    )
    service = MediaProviders(unsplash_key="controlled", transport=httpx.MockTransport(no_network))
    assert (
        asyncio.run(service.supporting(
            "private arbitrary user wording", 360, 240, destination="Melbourne"
        ))["status"]
        == "unavailable"
    )
    assert asyncio.run(service.supporting("meal", 360, 240))["status"] == "unavailable"


def test_owned_supporting_slots_share_one_theme_search_and_reject_other_roles(client):  # noqa: F811
    from backend.app.product.media import get_media_providers

    owner = register(client)
    activities = []
    for aid, kind, time_use in [
        ("meal1", "generic_activity", "scheduled"),
        ("meal2", "generic_activity", "scheduled"),
        ("main", "main_poi", "scheduled"),
        ("old", "unknown", "scheduled"),
        ("free", "generic_activity", "free_window"),
    ]:
        activities.append(
            dict(
                activity_id=aid,
                title="Private user wording",
                activity_kind=kind,
                time_use=time_use,
                atmosphere_theme="meal",
                start_time="2020-01-01T10:00:00",
                end_time="2020-01-01T11:00:00",
            )
        )
    detail = pending(owner["id"], days=[{"date": "2020-01-01", "activities": activities}])
    calls = []

    def provider(request):
        calls.append(request)
        assert "Private" not in str(request.url)
        return httpx.Response(
            200,
            json={"results": [photo("first")]}
            if request.url.path == "/search/photos"
            else {"url": "https://images.unsplash.com/first"},
        )

    client.app.dependency_overrides[get_media_providers] = lambda: MediaProviders(
        unsplash_key="controlled", transport=httpx.MockTransport(provider)
    )
    try:
        path = f"/api/previews/{detail.id}/supporting-media"
        result = client.get(
            path, params=[("slot", f"activity:{a['activity_id']}") for a in activities]
        )
        assert result.status_code == 200, result.text
        assert len(calls) == 2
        assert calls[0].url.params["query"] == "Sydney relaxed meal"
        assert result.json()["items"]["activity:meal1"]["kind"] == "atmosphere"
        assert result.json()["items"]["activity:meal1"] == result.json()["items"]["activity:meal2"]
        for aid in ("main", "old", "free"):
            assert result.json()["items"][f"activity:{aid}"]["status"] == "unavailable"
        register(client, "other@example.com")
        assert client.get(path).status_code == 404
        assert len(calls) == 2
    finally:
        client.app.dependency_overrides.pop(get_media_providers, None)
