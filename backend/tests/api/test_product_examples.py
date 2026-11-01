"""Guests receive two complete historical V3 projections, never provider identities."""

import asyncio

from httpx import ASGITransport, AsyncClient

from backend.app.main import create_app


def test_guest_can_read_two_complete_source_backed_examples():
    async def journey():
        async with AsyncClient(
            transport=ASGITransport(app=create_app()), base_url="http://test"
        ) as client:
            collection = await client.get("/api/examples")
            assert collection.status_code == 200
            cards = collection.json()
            assert [card["id"] for card in cards] == ["sydney-example", "london-example"]
            for card in cards:
                response = await client.get(f"/api/examples/{card['id']}")
                assert response.status_code == 200
                detail = response.json()
                assert detail["provenance"] == "example"
                assert detail["trust"] == "source_fixture"
                assert detail["request"]["budget"]
                assert card["day_count"] == 3
                assert card["stop_count"] == 6
                assert card["transfer_count"] == 3
                assert len(detail["nearby"]) == 3
                for day in detail["days"]:
                    assert day["weather"]["summary"]
                    assert day["weather"]["temperature_min_c"] is not None
                    assert day["weather"]["temperature_max_c"] is not None
                    assert day["weather"]["precipitation_probability_percent"] is not None
                    assert day["weather"]["max_wind_speed_kph"] is not None
                    assert day["weather"]["attribution"]
                    for activity in day["activities"]:
                        assert activity["location"]
                        assert activity["estimated_cost"] is None
                for transfer in detail["transfers"]:
                    assert transfer["provider_duration_seconds"] > 0
                    assert transfer["distance_meters"] > 0
                    assert transfer["validation_state"] == "PASS"
                    assert transfer["status"] == "confirmed"
                assert "source_place_id" not in response.text
                assert "media_bindings" not in response.text
                assert "evidence_refs" not in response.text
            sydney = (await client.get("/api/examples/sydney-example")).json()
            assert sydney["days"][0]["date"] == "2026-10-13"
            assert sydney["days"][0]["weather"]["precipitation_probability_percent"] == 100
            assert sydney["transfers"][0]["provider_duration_seconds"] == 1468
            london = (await client.get("/api/examples/london-example")).json()
            assert london["days"][0]["date"] == "2026-10-15"
            assert london["days"][0]["weather"]["temperature_max_c"] == 20.5
            assert london["transfers"][0]["distance_meters"] == 568
            for removed in ["nearby-linking", "kyoto-design", "melbourne-design", "not-an-example"]:
                assert (await client.get(f"/api/examples/{removed}")).status_code == 404
            assert (await client.post("/api/examples", json=sydney)).status_code == 405

    asyncio.run(journey())


def test_example_photos_use_local_assets_with_illustration_fallbacks():
    import httpx

    from backend.app.product.media import MediaProviders, get_media_providers
    from backend.tests.product.media_fakes import media_transport

    async def journey():
        application = create_app()
        application.dependency_overrides[get_media_providers] = lambda: MediaProviders(
            google_key="test-only", transport=httpx.MockTransport(media_transport)
        )
        async with AsyncClient(
            transport=ASGITransport(app=application), base_url="http://test"
        ) as client:
            for example in ("sydney-example", "london-example"):
                response = await client.get(f"/api/examples/{example}/media")
                assert response.status_code == 200
                assert response.headers["cache-control"] == "public, max-age=86400"
                photos = response.json()["items"]
                assert len(photos) == 9
                assert sum(slot.startswith("activity:") for slot in photos) == 6
                assert all(photo["status"] == "available" and photo["authors"]
                           and photo["image_url"].startswith("/dayloom/examples/")
                           for slot, photo in photos.items() if slot.startswith("activity:"))
                assert all(photo == {"status": "unavailable"}
                           for slot, photo in photos.items() if slot.startswith("nearby:"))
                assert "test-only" not in response.text
                oversized = await client.get(f"/api/examples/{example}/media?width=1281")
                assert oversized.status_code == 422
            for unknown in ("nearby-linking", "not-an-example", "ChIJ-forged"):
                assert (await client.get(f"/api/examples/{unknown}/media")).status_code == 404
            cover = await client.get("/api/media/curated/london")
            assert cover.status_code == 200
            assert cover.json()["status"] == "available"
            assert cover.json()["provider"] == "Google Maps"

    asyncio.run(journey())
