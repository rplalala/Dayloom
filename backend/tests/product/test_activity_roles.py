"""Activity roles survive the public Product lifecycle without gaining authority."""

import json
from datetime import timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.product.preview_projection import generated_detail
from backend.app.product.task_store import TaskStore
from backend.app.schemas.request import PlanningRequest
from backend.app.services.product_presentation import present_product
from backend.tests.api.test_product_planning import make_product_payload
from backend.tests.product.test_accounts import client, register  # noqa: F401
from backend.tests.product.test_copies import copy, headers
from backend.tests.product.test_imports import source
from backend.tests.product.test_saved import historical_content, pending
from backend.tests.services.test_product_presentation import example


def projected_roles():
    result, evidence = example()
    principal, supporting = result.itinerary.days[0].activities
    principal.time_use = supporting.time_use = "scheduled"
    supporting.activity_kind = "generic_activity"
    supporting.source_place_id = None
    supporting.title = "Time by the water"
    result.itinerary.days[0].activities.append(
        supporting.model_copy(
            update={
                "activity_id": "legacy",
                "activity_kind": "unknown",
                "start_time": supporting.end_time,
                "end_time": supporting.end_time + timedelta(hours=1),
            }
        )
    )
    return generated_detail(
        present_product(result, evidence),
        PlanningRequest.model_validate(make_product_payload()),
    )


def test_final_roles_reach_public_preview_without_reclassifying_unknown_content():
    detail = projected_roles().model_dump(mode="json")
    activities = detail["days"][0]["activities"]
    assert [a.get("activity_kind", "unknown") for a in activities] == [
        "main_poi",
        "generic_activity",
        "unknown",
    ]
    assert [a.get("atmosphere_theme") for a in activities] == [None, "general", None]
    assert all(a["time_use"] == "scheduled" for a in activities)
    assert activities[1]["activity_id"] == "right"


def test_existing_saved_content_gains_unknown_role_without_inference_or_rewrite(client):  # noqa: F811
    import os

    from backend.app.product.database import connect, migrate

    owner = register(client)
    detail = pending(owner["id"], **historical_content())
    receipt = client.post(f"/api/previews/{detail.id}/save", headers=headers(owner), json={})
    trip_id = receipt.json()["saved_trip_id"]
    expected = client.get(f"/api/trips/{trip_id}").json()
    with connect() as connection:
        # Pre-009 schema/data precondition, restricted by the isolated client fixture.
        connection.execute("ALTER TABLE app.trip_activities DROP COLUMN activity_kind")
        connection.execute("ALTER TABLE app.trip_activities DROP COLUMN atmosphere_theme")
        connection.execute("DELETE FROM app.schema_migrations WHERE name='009_activity_roles.sql'")
    assert migrate(os.environ["DAYLOOM_DB_URL"]) == ["009_activity_roles.sql"]
    assert migrate(os.environ["DAYLOOM_DB_URL"]) == []
    actual = client.get(f"/api/trips/{trip_id}").json()
    assert actual == expected
    assert all(
        a.get("activity_kind", "unknown") == "unknown" and a.get("atmosphere_theme") is None
        for day in actual["days"]
        for a in day["activities"]
    )


def test_roles_survive_save_recreation_and_independent_copy(client):  # noqa: F811
    owner = register(client)
    detail = projected_roles()
    request = PlanningRequest.model_validate(make_product_payload())
    store = TaskStore()
    task, _ = store.accept(owner["id"], str(uuid4()), request, None, request.start_date)
    assert store.complete(store.claim(task["id"]), detail)
    preview = client.get(f"/api/previews/{detail.id}").json()["snapshot"]
    assert preview["days"][0]["activities"][1]["activity_kind"] == "generic_activity"
    receipt = client.post(f"/api/previews/{detail.id}/save", headers=headers(owner), json={})
    assert receipt.status_code == 200, receipt.text
    saved_id = receipt.json()["saved_trip_id"]
    with TestClient(create_app(), base_url="http://localhost:5120") as recreated:
        recreated.cookies.update(client.cookies)
        saved = recreated.get(f"/api/trips/{saved_id}").json()
        assert saved["days"] == preview["days"]
        copied = copy(recreated, owner, "copied", saved_id, "roles-copy")
        assert copied.status_code == 200, copied.text
        copy_id = copied.json()["saved_trip_id"]
        assert copy_id != saved_id
        assert recreated.get(f"/api/trips/{copy_id}").json()["days"] == preview["days"]


def test_imported_roles_and_themes_are_display_claims_without_place_or_completion_authority(client):  # noqa: F811
    import httpx

    from backend.app.product.media import MediaProviders, get_media_providers

    owner = register(client)
    artifact = source()
    artifact["days"][0]["activities"][0].update(
        activity_kind="main_poi",
        atmosphere_theme="walk",
        source_place_id="claimed-google-id",
    )
    artifact["completion"] = {"policy_completion": "complete"}
    response = client.post(
        "/api/imports",
        content=json.dumps(artifact),
        headers=headers(owner) | {"X-Import-Key": "roles-import"},
    )
    assert response.status_code == 200, response.text
    preview = response.json()["snapshot"]
    assert preview["trust"] == "unverified_import"
    assert preview["completion"]["policy_completion"] == "unassessed"
    activity = preview["days"][0]["activities"][0]
    assert activity["activity_kind"] == "main_poi" and activity["atmosphere_theme"] == "walk"
    assert "source_place_id" not in activity
    saved = client.post(
        f"/api/previews/{response.json()['id']}/save", headers=headers(owner), json={}
    ).json()["saved_trip_id"]
    assert client.get(f"/api/trips/{saved}").json()["days"] == preview["days"]

    def no_provider(request):
        raise AssertionError("Imported declarations must not trigger a provider")

    client.app.dependency_overrides[get_media_providers] = lambda: MediaProviders(
        google_key="controlled", transport=httpx.MockTransport(no_provider)
    )
    try:
        media = client.get(f"/api/trips/{saved}/media?slot=activity:a")
        assert media.status_code == 200, media.text
        assert media.json()["items"]["activity:a"]["status"] == "unavailable"
    finally:
        client.app.dependency_overrides.pop(get_media_providers, None)
