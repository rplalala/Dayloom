"""Curated examples are public, allowlisted source claims, with lossless detail."""

import asyncio

from httpx import ASGITransport, AsyncClient

from backend.app.main import create_app


def test_guest_can_follow_curated_collection_to_lossless_example():
    async def journey():
        async with AsyncClient(
            transport=ASGITransport(app=create_app()), base_url="http://test"
        ) as c:
            collection = await c.get("/api/examples")
            assert collection.status_code == 200
            assert [item["id"] for item in collection.json()] == [
                "sydney-example",
                "kyoto-design",
                "melbourne-design",
            ]
            response = await c.get("/api/examples/nearby-linking")
            assert response.status_code == 200
            detail = response.json()
            assert detail["schema_version"] == "product_detail_1"
            assert detail["provenance"] == "example"
            assert detail["trust"] == "source_fixture"
            assert detail["request"] is None
            assert detail["days"][0]["activities"][0]["start_time"] == "2026-10-13T12:00:00+11:00"
            assert [day["date"] for day in detail["days"]] == [
                "2026-10-13",
                "2026-10-14",
                "2026-10-15",
            ]
            assert detail["nearby"][-1]["anchor_activity_id"] == "missing-activity"
            assert detail["nearby"][-2]["anchor_activity_id"] is None
            assert "evidence_refs" not in response.text
            assert "source_place_id" not in response.text
            assert detail["transfers"][0]["validation_state"] is None
            assert detail["transfers"][0]["source_status"] == "PASS"
            assert detail["transfers"][0]["status"] == "source_claim"
            for card in collection.json():
                assert (await c.get(f"/api/examples/{card['id']}")).status_code == 200
            assert (await c.get("/api/examples/not-an-example")).status_code == 404
            assert (await c.post("/api/examples", json=detail)).status_code == 405

    asyncio.run(journey())
