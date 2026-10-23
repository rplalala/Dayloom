"""Preview decisions through Product HTTP and real isolated PostgreSQL."""

from datetime import date
from uuid import uuid4

import pytest

from backend.app.product.detail import ProductDetail
from backend.app.product.task_store import TaskStore
from backend.app.schemas.request import PlanningRequest
from backend.tests.api.test_product_planning import make_product_payload
from backend.tests.product.test_accounts import client, register  # noqa: F401


def pending(owner, **changes):
    store = TaskStore()
    task, _ = store.accept(
        owner,
        str(uuid4()),
        PlanningRequest.model_validate(make_product_payload()),
        None,
        date(2026, 9, 11),
    )
    claim = store.claim(task["id"])
    detail = ProductDetail(
        id=str(uuid4()),
        title="A saved journey",
        destination="Sydney",
        provenance="generated",
        trust="generated_projection",
        **changes,
    )
    assert store.complete(claim, detail)
    return detail


def test_save_is_explicit_durable_and_repeated_decision_has_one_identity(client):  # noqa: F811
    account = register(client)
    detail = pending(account["id"])
    headers = {"Origin": "http://localhost:5120", "X-CSRF-Token": account["csrf_token"]}
    assert client.get("/api/library").json()["items"] == []
    saved = client.post(f"/api/previews/{detail.id}/save", headers=headers, json={})
    assert saved.status_code == 200, saved.text
    decision = saved.json()
    assert decision["state"] == "saved"
    assert (
        client.post(f"/api/previews/{detail.id}/save", headers=headers, json={}).json() == decision
    )
    expected = detail.model_dump(mode="json") | {"id": decision["saved_trip_id"]}
    assert client.get(f"/api/trips/{decision['saved_trip_id']}").json() == expected
    assert client.get("/api/previews").json() == []
    assert client.get("/api/library").json()["items"][0]["kind"] == "saved"
    from fastapi.testclient import TestClient

    from backend.app.main import create_app

    with TestClient(create_app(), base_url="http://localhost:5120") as recreated:
        recreated.cookies.update(client.cookies)
        assert recreated.get(f"/api/trips/{decision['saved_trip_id']}").json() == expected


def historical_content():
    return {
        "start_date": "2020-01-01",
        "end_date": "2020-01-04",
        "request": {"destination": "Sydney", "traveler_count": None},
        "completion": {
            "policy_completion": "incomplete",
            "policy_reasons": ["Unresolved opening hours"],
        },
        "days": [
            {
                "date": "2020-01-04",
                "weather": {
                    "summary": None,
                    "temperature_min_c": 0,
                    "attribution": "Weather source",
                    "source_url": "https://example.com/weather",
                },
                "activities": [
                    {
                        "activity_id": "later",
                        "title": "Later stop",
                        "start_time": "2020-01-04T11:00:00.123400789+11:00",
                        "end_time": "2020-01-04T00:40:00.123400789Z",
                        "estimated_cost": {"amount": "0.00", "currency": "AUD"},
                    },
                    {
                        "activity_id": "earlier",
                        "title": "Earlier stop",
                        "start_time": "2020-01-04T09:00:00",
                        "end_time": "2020-01-04T10:00:00",
                    },
                    {
                        "activity_id": "free",
                        "title": "Time to explore",
                        "time_use": "free_window",
                        "start_time": "2020-01-04T12:00:00",
                        "end_time": "2020-01-04T13:00:00",
                    },
                ],
            },
            {"date": "2020-01-01", "activities": []},
        ],
        "nearby": [
            {
                "place_name": "First optional place",
                "anchor_activity_id": "later",
                "associated_day": "2020-01-04",
                "uncertainty": "Unverified",
                "attribution": "Nearby source",
            },
            {
                "place_name": "Orphan",
                "anchor_activity_id": "missing",
                "associated_day": "2020-01-03",
            },
            {
                "place_name": "Date mismatch",
                "anchor_activity_id": "later",
                "associated_day": "2020-01-01",
            },
            {"place_name": "Free window reference", "anchor_activity_id": "free"},
        ],
        "transfers": [
            {
                "from_activity_id": "earlier",
                "to_activity_id": "later",
                "status": "unknown",
                "validation_state": "UNKNOWN",
                "unknowns": ["Route unavailable"],
                "reserve_seconds": 0,
            },
            {
                "from_activity_id": "later",
                "to_activity_id": "free",
                "departure_time": "2020-01-04T11:40:00.123400+11:00",
                "arrival_time": "2020-01-04T12:00:00.123400+11:00",
                "estimate_kind": "provider",
                "status": "confirmed",
                "validation_state": "CONFIRMED",
                "provider_duration_seconds": 1200,
                "distance_meters": 100,
                "attribution": "Routes source",
            },
        ],
    }


def test_saved_roundtrip_keeps_actual_order_missing_facts_and_weather_sources(client):  # noqa: F811
    account = register(client)
    detail = pending(account["id"], **historical_content())
    headers = {"Origin": "http://localhost:5120", "X-CSRF-Token": account["csrf_token"]}
    decision = client.post(f"/api/previews/{detail.id}/save", headers=headers, json={}).json()
    actual = client.get(f"/api/trips/{decision['saved_trip_id']}")
    assert actual.status_code == 200, actual.text
    expected = detail.model_dump(mode="json") | {"id": decision["saved_trip_id"]}
    assert actual.json() == expected
    assert client.get(f"/api/previews/{detail.id}").json()["snapshot"] == expected
    from backend.app.product.database import connect

    with connect() as connection:
        references = connection.execute(
            "SELECT resolved_activity_id FROM app.trip_nearby WHERE trip_id=%s ORDER BY position",
            (decision["saved_trip_id"],),
        ).fetchall()
    assert [row["resolved_activity_id"] for row in references] == ["later", None, None, None]


def test_child_write_failure_keeps_pending_preview_and_explicit_retry_succeeds(client):  # noqa: F811
    from backend.app.product.database import connect

    account = register(client)
    detail = pending(account["id"], **historical_content())
    headers = {"Origin": "http://localhost:5120", "X-CSRF-Token": account["csrf_token"]}
    with connect() as connection:
        connection.execute(
            "CREATE FUNCTION app.reject_saved_child() RETURNS trigger LANGUAGE plpgsql "
            "AS $$ BEGIN RAISE EXCEPTION 'deliberate child failure'; END $$"
        )
        connection.execute(
            "CREATE TRIGGER reject_saved_child BEFORE INSERT ON app.trip_activities "
            "FOR EACH ROW EXECUTE FUNCTION app.reject_saved_child()"
        )
    try:
        failed = client.post(f"/api/previews/{detail.id}/save", headers=headers, json={})
        assert failed.status_code == 503
        assert "deliberate" not in failed.text
        assert client.get(f"/api/previews/{detail.id}").json()["snapshot"] == detail.model_dump(
            mode="json"
        )
        assert client.get("/api/library").json()["total"] == 0
        with connect() as connection:
            assert connection.execute("SELECT count(*) AS n FROM app.trips").fetchone()["n"] == 0
            assert (
                connection.execute("SELECT count(*) AS n FROM app.trip_weather").fetchone()["n"]
                == 0
            )
    finally:
        with connect() as connection:
            connection.execute("DROP TRIGGER reject_saved_child ON app.trip_activities")
            connection.execute("DROP FUNCTION app.reject_saved_child()")
    assert (
        client.post(f"/api/previews/{detail.id}/save", headers=headers, json={}).json()["state"]
        == "saved"
    )


@pytest.mark.parametrize("actions", [("save", "save"), ("save", "discard")])
def test_concurrent_decisions_commit_one_winner_and_late_save_does_not_resurrect(client, actions):  # noqa: F811
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from fastapi.testclient import TestClient

    from backend.app.main import create_app
    from backend.app.product.database import connect

    account = register(client)
    detail = pending(account["id"], **historical_content())
    headers = {"Origin": "http://localhost:5120", "X-CSRF-Token": account["csrf_token"]}
    barrier = Barrier(2)

    def decide(action):
        with TestClient(create_app(), base_url="http://localhost:5120") as other:
            other.cookies.update(client.cookies)
            barrier.wait()
            result = other.post(
                f"/api/previews/{detail.id}/{action}",
                headers=headers,
                json={"confirmed": True} if action == "discard" else {},
            )
            assert result.status_code in (200, 409)
            value = result.json()
            return value["detail"]["decision"] if result.status_code == 409 else value

    with ThreadPoolExecutor(2) as pool:
        first, second = list(pool.map(decide, actions))
    assert first == second
    receipt = client.get(f"/api/previews/{detail.id}").json()
    if receipt["state"] == "saved":
        with connect() as connection:
            connection.execute("DELETE FROM app.trips WHERE id=%s", (receipt["saved_trip_id"],))
        response = client.post(f"/api/previews/{detail.id}/save", headers=headers, json={})
        assert response.status_code == 409
        late = response.json()["detail"]["decision"]
        assert late["outcome"] == "saved_result_deleted"
        assert late["saved_trip_id"] == receipt["saved_trip_id"]
        assert client.get(f"/api/trips/{receipt['saved_trip_id']}").status_code == 404
    else:
        assert receipt["snapshot"] is None
        late = client.post(f"/api/previews/{detail.id}/save", headers=headers, json={})
        assert late.status_code == 409
        assert late.json()["detail"]["decision"]["state"] == "discarded"
    assert client.get("/api/library").json()["total"] == 0


def test_losing_decision_reports_safe_conflict_without_removing_saved_trip(client):  # noqa: F811
    account = register(client)
    headers = {"Origin": "http://localhost:5120", "X-CSRF-Token": account["csrf_token"]}
    detail = pending(account["id"])
    saved = client.post(f"/api/previews/{detail.id}/save", headers=headers, json={}).json()
    losing = client.post(
        f"/api/previews/{detail.id}/discard", headers=headers, json={"confirmed": True}
    )
    assert losing.status_code == 409
    assert losing.json()["detail"]["decision"] == saved
    assert client.get(f"/api/trips/{saved['saved_trip_id']}").status_code == 200


@pytest.mark.parametrize("action", ["save", "discard", "delete"])
def test_completed_http_and_sse_observers_expose_safe_decisions_after_content_is_removed(
    client,  # noqa: F811
    action,
):
    from backend.app.api.dependencies import get_planning_service
    from backend.app.product.database import connect
    from backend.app.product.task_coordinator import TaskCoordinator
    from backend.app.product.tasks import get_coordinator
    from backend.tests.api.test_product_planning import make_planning_service
    from backend.tests.versions.v0.fakes import FakeStructuredLLMClient

    account = register(client)
    headers = {"Origin": "http://localhost:5120", "X-CSRF-Token": account["csrf_token"]}
    detail = pending(account["id"])
    with connect() as connection:
        key = connection.execute(
            "SELECT operation_key FROM app.itinerary_previews WHERE id=%s", (detail.id,)
        ).fetchone()["operation_key"]
    selected = "save" if action == "delete" else action
    receipt = client.post(
        f"/api/previews/{detail.id}/{selected}",
        headers=headers,
        json={"confirmed": True} if selected == "discard" else {},
    ).json()
    if action == "delete":
        with connect() as connection:
            connection.execute("DELETE FROM app.trips WHERE id=%s", (receipt["saved_trip_id"],))
    service = make_planning_service(FakeStructuredLLMClient([]))
    client.app.dependency_overrides[get_planning_service] = lambda: service
    coordinator = TaskCoordinator(TaskStore())
    client.app.dependency_overrides[get_coordinator] = lambda: coordinator
    try:
        response = client.post(
            "/api/planning",
            json=make_product_payload(),
            headers={**headers, "Idempotency-Key": key},
        )
        assert response.status_code == 202, response.text
        expected = "saved_result_deleted" if action == "delete" else receipt["state"]
        assert response.json()["preview_decision"]["outcome"] == expected
        assert (response.json()["result"] is not None) == (action == "save")
        stream = client.post(
            "/api/planning/stream",
            json=make_product_payload(),
            headers={**headers, "Idempotency-Key": key},
        )
        assert stream.status_code == 200
        assert "event: result" in stream.text and f'"outcome": "{expected}"' in stream.text
    finally:
        client.app.dependency_overrides.clear()


def test_discard_requires_confirmation_and_owner_checks_cover_every_saved_boundary(client):  # noqa: F811
    account = register(client)
    headers = {"Origin": "http://localhost:5120", "X-CSRF-Token": account["csrf_token"]}
    discarded = pending(account["id"])
    assert (
        client.post(f"/api/previews/{discarded.id}/discard", headers=headers, json={}).status_code
        == 422
    )
    assert client.get(f"/api/previews/{discarded.id}").json()["state"] == "pending"
    receipt = client.post(
        f"/api/previews/{discarded.id}/discard", headers=headers, json={"confirmed": True}
    ).json()
    assert receipt["state"] == "discarded"
    assert (
        client.post(
            f"/api/previews/{discarded.id}/discard", headers=headers, json={"confirmed": True}
        ).json()
        == receipt
    )
    detail = pending(account["id"])
    saved = client.post(f"/api/previews/{detail.id}/save", headers=headers, json={}).json()
    client.cookies.clear()
    other = register(client, "other@example.com")
    other_headers = {"Origin": "http://localhost:5120", "X-CSRF-Token": other["csrf_token"]}
    assert client.get(f"/api/trips/{saved['saved_trip_id']}").status_code == 404
    assert client.get(f"/api/previews/{detail.id}").status_code == 404
    for action in ("save", "discard"):
        assert (
            client.post(
                f"/api/previews/{detail.id}/{action}",
                headers=other_headers,
                json={"confirmed": True} if action == "discard" else {},
            ).status_code
            == 404
        )
    assert client.get("/api/library").json()["total"] == 0
