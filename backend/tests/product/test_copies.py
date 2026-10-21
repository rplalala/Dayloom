"""Explicit whole-trip copying through real HTTP and isolated PostgreSQL."""

import json
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID, uuid4

import httpx
from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.product.database import connect
from backend.tests.product.test_accounts import client, register  # noqa: F401
from backend.tests.product.test_imports import conflicting_source, source
from backend.tests.product.test_saved import historical_content, pending


def headers(account):
    return {"Origin": "http://localhost:5120", "X-CSRF-Token": account["csrf_token"]}


def imported(client, account):  # noqa: F811
    preview = client.post(
        "/api/imports",
        headers=headers(account) | {"X-Import-Key": str(uuid4())},
        content=json.dumps(
            {"itinerary": conflicting_source(), "request": {"traveler_count": None}}
        ),
    )
    assert preview.status_code == 200, preview.text
    saved = client.post(
        f"/api/previews/{preview.json()['id']}/save", headers=headers(account), json={}
    )
    assert saved.status_code == 200, saved.text
    return saved.json()["saved_trip_id"]


def copy(client, account, kind, source_id, key):  # noqa: F811
    return client.post(
        "/api/copies",
        headers=headers(account),
        json={
            "source_kind": kind,
            "source_id": source_id,
            "operation_key": key,
        },
    )


def test_keep_example_commits_saved_snapshot_without_task_or_pending_preview(client):  # noqa: F811
    account = register(client)
    headers = {"Origin": "http://localhost:5120", "X-CSRF-Token": account["csrf_token"]}
    source = client.get("/api/examples/sydney-example").json()
    response = client.post(
        "/api/copies",
        headers=headers,
        json={
            "source_kind": "example",
            "source_id": "sydney-example",
            "operation_key": "keep-once",
        },
    )
    assert response.status_code == 200, response.text
    receipt = response.json()
    assert receipt["state"] == "saved" and receipt["outcome"] == "saved"
    detail = client.get(f"/api/trips/{receipt['saved_trip_id']}").json()
    assert detail == source | {"id": receipt["saved_trip_id"], "title": source["title"] + " (copy)"}
    assert client.get("/api/previews").json() == []
    assert client.get("/api/planning/tasks").json() == []
    assert client.get("/api/copies/example/keep-once").json() == receipt
    assert client.get("/api/library").json()["total"] == 1


def test_historical_import_copy_is_independent_lossless_and_replays_after_both_deletions(client):  # noqa: F811
    account = register(client)
    original = imported(client, account)
    expected = client.get(f"/api/trips/{original}").json()
    result = copy(client, account, "copied", str(UUID(original)).upper(), "historical")
    assert result.status_code == 200, result.text
    receipt = result.json()
    copied = receipt["saved_trip_id"]
    assert copied != original
    detail = client.get(f"/api/trips/{copied}").json()
    assert detail == expected | {"id": copied, "title": expected["title"] + " (copy)"}
    assert detail["request"]["known_fields"] == ["traveler_count"]
    assert detail["request"]["traveler_count"] is None
    assert detail["trust"] == "unverified_import"
    descendant = copy(client, account, "copied", copied, "descendant").json()["saved_trip_id"]
    client.patch(
        f"/api/trips/{original}",
        headers=headers(account),
        json={"title": "Renamed source", "revision": 1},
    )
    assert copy(client, account, "copied", original, "historical").json() == receipt
    client.request(
        "DELETE",
        f"/api/trips/{original}",
        headers=headers(account),
        json={"confirmed": True, "revision": 2},
    )
    assert copy(client, account, "copied", original, "historical").json() == receipt
    assert copy(client, account, "copied", original, "new-key").status_code == 404
    client.request(
        "DELETE",
        f"/api/trips/{copied}",
        headers=headers(account),
        json={"confirmed": True, "revision": 1},
    )
    deleted = receipt | {"outcome": "saved_result_deleted"}
    with TestClient(create_app(), base_url="http://localhost:5120") as recreated:
        recreated.cookies.update(client.cookies)
        assert recreated.get("/api/copies/copied/historical").json() == deleted
        assert copy(recreated, account, "copied", original, "historical").json() == deleted
    assert client.get(f"/api/trips/{descendant}").json()["trust"] == "unverified_import"
    assert client.get("/api/library").json()["total"] == 1
    with connect() as connection:
        row = connection.execute(
            "SELECT source_kind,source_id FROM app.trips WHERE id=%s", (descendant,)
        ).fetchone()
        assert row == {"source_kind": "copied", "source_id": copied}


def test_concurrent_copy_lost_reply_conflict_and_owner_checks(client):  # noqa: F811
    account = register(client)
    original = imported(client, account)
    cookies = dict(client.cookies)

    def send(_):
        with TestClient(create_app(), base_url="http://localhost:5120") as other:
            other.cookies.update(cookies)
            result = copy(other, account, "copied", original, "concurrent")
            assert result.status_code == 200, result.text
            return result.json()

    with ThreadPoolExecutor(max_workers=3) as workers:
        receipts = list(workers.map(send, range(3)))
    assert receipts[0] == receipts[1] == receipts[2]
    assert client.get("/api/copies/copied/concurrent").json() == receipts[0]
    second = copy(client, account, "example", "sydney-example", "second").json()["saved_trip_id"]
    assert copy(client, account, "copied", second, "concurrent").status_code == 409
    assert client.get("/api/library").json()["total"] == 3
    assert client.get("/api/previews").json() == []
    assert client.get("/api/planning/tasks").json() == []
    assert (
        client.post(
            "/api/copies",
            json={"source_kind": "example", "source_id": "sydney-example", "operation_key": "csrf"},
        ).status_code
        == 403
    )
    with TestClient(create_app(), base_url="http://localhost:5120") as stranger:
        other = register(stranger, "stranger@example.com")
        assert stranger.get("/api/copies/copied/concurrent").status_code == 404
        assert copy(stranger, other, "copied", original, "concurrent").status_code == 404
        assert (
            copy(stranger, other, "copied", receipts[0]["saved_trip_id"], "stolen").status_code
            == 404
        )
    for invalid in ["../../secret", "unknown", "SYDNEY-EXAMPLE"]:
        assert copy(client, account, "example", invalid, "invalid").status_code == 422
    assert (
        client.post(
            "/api/copies",
            headers=headers(account),
            json={
                "source_kind": "example",
                "source_id": "sydney-example",
                "operation_key": "forged",
                "snapshot": source(),
            },
        ).status_code
        == 422
    )


def test_copy_child_failure_rolls_back_receipt_and_snapshot_together(client):  # noqa: F811
    account = register(client)
    with connect() as connection:
        connection.execute(
            "CREATE FUNCTION app.reject_copy_child() RETURNS trigger LANGUAGE plpgsql "
            "AS $$ BEGIN RAISE EXCEPTION 'deliberate child failure'; END $$"
        )
        connection.execute(
            "CREATE TRIGGER reject_copy_child BEFORE INSERT ON app.trip_activities "
            "FOR EACH ROW EXECUTE FUNCTION app.reject_copy_child()"
        )
    try:
        result = copy(client, account, "example", "sydney-example", "atomic")
        assert result.status_code == 503 and "deliberate" not in result.text
        assert client.get("/api/copies/example/atomic").status_code == 404
        assert client.get("/api/library").json()["total"] == 0
        assert client.get("/api/previews").json() == []
        with connect() as connection:
            assert (
                connection.execute("SELECT count(*) AS n FROM app.itinerary_previews").fetchone()[
                    "n"
                ]
                == 0
            )
            assert (
                connection.execute("SELECT count(*) AS n FROM app.trip_weather").fetchone()["n"]
                == 0
            )
    finally:
        with connect() as connection:
            connection.execute("DROP TRIGGER reject_copy_child ON app.trip_activities")
            connection.execute("DROP FUNCTION app.reject_copy_child()")
    assert copy(client, account, "example", "sydney-example", "atomic").status_code == 200


def test_generated_copy_retains_evidence_and_copy_mutation_never_calls_http_providers(
    client,  # noqa: F811
    monkeypatch,
):
    account = register(client)
    preview = pending(account["id"], **historical_content())
    original = client.post(
        f"/api/previews/{preview.id}/save", headers=headers(account), json={}
    ).json()["saved_trip_id"]
    expected = client.get(f"/api/trips/{original}").json()
    tasks = client.get("/api/planning/tasks").json()

    def forbidden(*args, **kwargs):
        raise AssertionError("Copy must not call an external HTTP adapter")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)
    receipt = copy(client, account, "copied", original, "generated").json()
    copied = receipt["saved_trip_id"]
    assert client.get(f"/api/trips/{copied}").json() == expected | {
        "id": copied,
        "title": "A saved journey (copy)",
    }
    assert client.get("/api/planning/tasks").json() == tasks
    assert client.get("/api/previews").json() == []
    rename = client.patch(
        f"/api/trips/{copied}",
        headers=headers(account),
        json={"title": "Independent title", "revision": 1},
    )
    assert rename.status_code == 200
    assert client.get(f"/api/trips/{original}").json() == expected
    assert (
        client.request(
            "DELETE",
            f"/api/trips/{copied}",
            headers=headers(account),
            json={"revision": 2, "confirmed": True},
        ).status_code
        == 204
    )
    assert client.get(f"/api/trips/{original}").json() == expected
