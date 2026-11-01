"""Independent copies retain only server-owned stable place identities."""

import json
from datetime import date, datetime
from types import SimpleNamespace
from uuid import uuid4

import httpx
from fastapi.testclient import TestClient

from backend.app.evidence.models import PlaceEvidence
from backend.app.main import create_app
from backend.app.product.database import connect
from backend.app.product.media import MediaProviders, get_media_providers
from backend.app.product.preview_projection import generated_detail
from backend.app.product.task_store import TaskStore
from backend.app.schemas.request import PlanningRequest
from backend.app.services.product_presentation import present_product
from backend.tests.api.test_product_planning import make_product_payload
from backend.tests.product.media_fakes import media_transport
from backend.tests.product.test_accounts import client, register  # noqa: F401
from backend.tests.product.test_copies import copy, headers
from backend.tests.product.test_imports import source
from backend.tests.services.test_product_presentation import example


def trusted_source(owner):
    result, evidence = example()
    activity = result.itinerary.days[0].activities[0]
    result.v3 = SimpleNamespace(
        final_places=(
            PlaceEvidence(
                place_id=activity.source_place_id,
                name="Adopted provider place",
                latitude=1,
                longitude=2,
                availability="available",
                retrieved_at=datetime.now(),
                source_ref="google_places:left-place",
            ),
        )
    )
    request = PlanningRequest.model_validate(make_product_payload())
    detail = generated_detail(present_product(result, evidence), request)
    store = TaskStore()
    task, _ = store.accept(owner, str(uuid4()), request, None, date(2026, 9, 11))
    assert store.complete(store.claim(task["id"]), detail)
    return detail


def test_verified_private_bindings_copy_atomically_without_provider_work_or_resource_urls(client):  # noqa: F811
    owner = register(client)
    calls = []

    def external(request):
        calls.append(request)
        return media_transport(request)

    provider = MediaProviders(google_key="controlled-only", transport=httpx.MockTransport(external))
    client.app.dependency_overrides[get_media_providers] = lambda: provider
    try:
        preview = trusted_source(owner["id"])
        bindings = preview._media_bindings
        assert list(bindings.values()) == ["left-place"]
        original = client.post(
            f"/api/previews/{preview.id}/save", headers=headers(owner), json={}
        ).json()["saved_trip_id"]
        receipt = copy(client, owner, "copied", original, "verified-copy").json()
        copied = receipt["saved_trip_id"]
        descendant = copy(client, owner, "copied", copied, "verified-descendant").json()[
            "saved_trip_id"
        ]
        assert calls == []
        with connect() as connection:
            rows = connection.execute(
                "SELECT media_bindings FROM app.trips WHERE id=ANY(%s::uuid[])",
                ([original, copied, descendant],),
            ).fetchall()
            assert len(rows) == 3 and all(row["media_bindings"] == bindings for row in rows)
            decided = connection.execute(
                "SELECT media_bindings,snapshot,original_request FROM app.itinerary_previews "
                "WHERE id=ANY(%s::uuid[])",
                ([str(preview.id), receipt["id"]],),
            ).fetchall()
            assert all(
                row == {"media_bindings": {}, "snapshot": None, "original_request": None}
                for row in decided
            )
        detail = client.get(f"/api/trips/{copied}")
        assert detail.json()["trust"] == "generated_projection"
        assert "media_bindings" not in detail.text and "left-place" not in detail.text
        assert "photos/" not in detail.text and "googleusercontent" not in detail.text
        assert (
            client.request(
                "DELETE",
                f"/api/trips/{original}",
                headers=headers(owner),
                json={"revision": 1, "confirmed": True},
            ).status_code
            == 204
        )
        assert copy(client, owner, "copied", original, "verified-copy").json() == receipt
        assert calls == []
        recreated = create_app()
        recreated.dependency_overrides[get_media_providers] = lambda: provider
        with TestClient(recreated, base_url="http://localhost:5120") as recovered:
            recovered.cookies.update(client.cookies)
            first = recovered.get(f"/api/trips/{copied}/media")
            assert first.status_code == 200 and list(first.json()["items"]) == list(bindings)
            assert len(calls) == 2
            descendant_items = recovered.get(f"/api/trips/{descendant}/media").json()["items"]
            for slot, media in first.json()["items"].items():
                assert descendant_items[slot]["cache_revision"] != media["cache_revision"]
                descendant_media = descendant_items[slot]
                assert {k: v for k, v in descendant_media.items() if k != "cache_revision"} == {
                    k: v for k, v in media.items() if k != "cache_revision"
                }
            assert len(calls) == 4
        with connect() as connection:
            assert (
                connection.execute(
                    "SELECT media_bindings FROM app.trips WHERE id=%s", (copied,)
                ).fetchone()["media_bindings"]
                == bindings
            )
        assert (
            client.request(
                "DELETE",
                f"/api/trips/{copied}",
                headers=headers(owner),
                json={"revision": 1, "confirmed": True},
            ).status_code
            == 204
        )
        assert client.get(f"/api/previews/{receipt['id']}/media").json()["items"] == {}
        assert len(calls) == 4
        assert client.get(f"/api/trips/{descendant}").status_code == 200
    finally:
        client.app.dependency_overrides.pop(get_media_providers, None)


def test_imported_google_claims_and_copy_bodies_cannot_grant_private_media_authority(client):  # noqa: F811
    owner = register(client)
    payload = source()
    payload["days"][0]["activities"][0]["source_place_id"] = "left-place"
    payload["policy_completion"] = "complete"

    def forbidden(request):
        raise AssertionError("Imported copies must not call media providers")

    client.app.dependency_overrides[get_media_providers] = lambda: MediaProviders(
        google_key="controlled-only",
        transport=httpx.MockTransport(forbidden),
    )
    try:
        imported = client.post(
            "/api/imports",
            headers=headers(owner) | {"X-Import-Key": "claims"},
            content=json.dumps(payload),
        )
        assert imported.status_code == 200
        original = client.post(
            f"/api/previews/{imported.json()['id']}/save", headers=headers(owner), json={}
        ).json()["saved_trip_id"]
        receipt = copy(client, owner, "copied", original, "claim-copy").json()
        copied = receipt["saved_trip_id"]
        assert client.get(f"/api/trips/{copied}").json()["trust"] == "unverified_import"
        assert client.get(f"/api/trips/{copied}/media").json()["items"] == {}
        assert client.get(f"/api/previews/{receipt['id']}/media").json()["items"] == {}
        with connect() as connection:
            assert (
                connection.execute(
                    "SELECT media_bindings FROM app.trips WHERE id=%s", (copied,)
                ).fetchone()["media_bindings"]
                == {}
            )
        forged = client.post(
            "/api/copies",
            headers=headers(owner),
            json={
                "source_kind": "copied",
                "source_id": original,
                "operation_key": "forged",
                "media_bindings": {"activity:a": "left-place"},
            },
        )
        assert forged.status_code == 422
        assert (
            client.get(
                "/api/copies", params={"source_kind": "copied", "operation_key": "forged"}
            ).status_code
            == 404
        )
        payload["media_bindings"] = {"activity:a": "left-place"}
        assert (
            client.post(
                "/api/imports",
                headers=headers(owner) | {"X-Import-Key": "forged-import"},
                content=json.dumps(payload),
            ).status_code
            == 422
        )
    finally:
        client.app.dependency_overrides.pop(get_media_providers, None)
