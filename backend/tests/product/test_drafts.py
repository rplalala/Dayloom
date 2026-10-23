"""Draft lifecycle through the public API and isolated real PostgreSQL."""

import os
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg.types.json import Jsonb
from pydantic import SecretStr

from backend.tests.product.test_accounts import client, register  # noqa: F401


def editor(**changes):
    return (
        dict(
            editor_version=1,
            destination="",
            start_date="",
            end_date="",
            travelers="",
            budget="",
            currency="AUD",
            required="",
            exclusions="",
            preferences="",
            interests=[],
            pace=None,
            transport=[],
            bindings=[],
        )
        | changes
    )


@pytest.mark.parametrize("currency", ["AUD", ""])
def test_incomplete_draft_round_trip_and_application_recreation(client, currency):  # noqa: F811
    account = register(client)
    headers = {"Origin": "http://localhost:5120", "X-CSRF-Token": account["csrf_token"]}
    draft = client.post(
        "/api/drafts",
        headers=headers,
        json={"title": "First idea", "editor": editor(currency=currency)},
    )
    assert draft.status_code == 201, draft.text
    data = draft.json()
    assert data["revision"] == 1 and data["editor"] == editor(currency=currency)
    from backend.app.main import create_app

    with TestClient(create_app(), base_url="http://localhost:5120") as recreated:
        recreated.cookies.update(client.cookies)
        assert recreated.get(f"/api/drafts/{data['id']}").json() == data
    changed = editor(
        currency=currency, destination="  Kyoto  ", travelers="not decided", start_date="later"
    )
    updated = client.put(
        f"/api/drafts/{data['id']}",
        headers=headers,
        json={"title": "First idea", "editor": changed, "revision": 1},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["id"] == data["id"]
    assert updated.json()["editor"] == changed
    assert updated.json()["revision"] == 2


def test_revision_copy_rename_delete_and_owner_boundary(client):  # noqa: F811
    account = register(client)
    headers = {"Origin": "http://localhost:5120", "X-CSRF-Token": account["csrf_token"]}
    original = client.post(
        "/api/drafts", headers=headers, json={"title": "Original", "editor": editor()}
    ).json()
    url = f"/api/drafts/{original['id']}"
    renamed = client.patch(url, headers=headers, json={"title": "New name", "revision": 1})
    assert renamed.status_code == 200 and renamed.json()["revision"] == 2
    stale = client.put(
        url,
        headers=headers,
        json={"title": "stale", "editor": editor(destination="local work"), "revision": 1},
    )
    assert stale.status_code == 409 and stale.json()["detail"]["code"] == "draft_revision_conflict"
    assert client.get(url).json()["title"] == "New name"
    assert client.delete(url + "?revision=1", headers=headers).status_code == 409
    assert client.post(url + "/copy", headers=headers, json={"revision": 1}).status_code == 409
    copied = client.post(url + "/copy", headers=headers, json={"revision": 2}).json()
    assert copied["id"] != original["id"] and copied["revision"] == 1
    assert (
        client.patch(url, headers=headers, json={"title": "  ", "revision": 2}).status_code == 422
    )
    assert client.delete(url + "?revision=2", headers=headers).status_code == 204
    assert client.get(url).status_code == 404
    assert client.get(f"/api/drafts/{copied['id']}").json()["title"] == "New name (copy)"
    client.cookies.clear()
    other = register(client, "other@example.com")
    other_headers = headers | {"X-CSRF-Token": other["csrf_token"]}
    copy_url = f"/api/drafts/{copied['id']}"
    assert client.get(copy_url).status_code == 404
    assert (
        client.put(
            copy_url,
            headers=other_headers,
            json={"title": "attack", "editor": editor(), "revision": 1},
        ).status_code
        == 404
    )
    assert (
        client.patch(
            copy_url, headers=other_headers, json={"title": "attack", "revision": 1}
        ).status_code
        == 404
    )
    assert (
        client.post(copy_url + "/copy", headers=other_headers, json={"revision": 1}).status_code
        == 404
    )
    assert client.delete(copy_url + "?revision=1", headers=other_headers).status_code == 404
    assert client.get("/api/library").json()["items"] == []


def test_library_bounded_search_and_stable_equal_name_pages(client):  # noqa: F811
    account = register(client)
    headers = {"Origin": "http://localhost:5120", "X-CSRF-Token": account["csrf_token"]}
    identifiers = []
    for destination in ["Kyoto", "Sydney", "Kyoto"]:
        draft = client.post(
            "/api/drafts",
            headers=headers,
            json={"title": "Same title", "editor": editor(destination=destination)},
        ).json()
        identifiers.append(draft["id"])
    pages = [client.get(f"/api/library?sort=name&limit=1&offset={n}").json() for n in range(3)]
    assert [p["items"][0]["id"] for p in pages] == sorted(identifiers)
    assert all(p["total"] == 3 and p["items"][0]["kind"] == "draft" for p in pages)
    assert client.get("/api/library?q=kyOto").json()["total"] == 2
    assert client.get("/api/library?q=%25").json()["total"] == 0
    assert client.get("/api/library?limit=51").status_code == 422
    assert client.get("/api/library?offset=-1").status_code == 422
    assert client.get("/api/library?sort=invalid").status_code == 422
    assert client.get("/api/library?sort=oldest").json()["items"][0]["id"] == identifiers[0]
    assert client.get("/api/library?sort=newest").json()["items"][0]["id"] == identifiers[-1]


def test_schema_bounds_and_safe_span_ownership(client):  # noqa: F811
    account = register(client)
    headers = {"Origin": "http://localhost:5120", "X-CSRF-Token": account["csrf_token"]}
    sentence = "Enjoy parks, waterfronts and gentle outdoor experiences."
    binding = {"key": "interest:Nature", "start": 3, "end": 3 + len(sentence), "text": sentence}
    snapshot = editor(
        preferences="🌿 " + sentence + "\n" + sentence, interests=["Nature"], bindings=[binding]
    )
    good = client.post("/api/drafts", headers=headers, json={"title": "Spans", "editor": snapshot})
    assert good.status_code == 201 and good.json()["editor"] == snapshot
    stale = snapshot | {"bindings": [binding | {"start": 0}]}
    bad = client.post(
        "/api/drafts", headers=headers, json={"title": "Stale", "editor": stale}
    ).json()
    assert bad["editor"]["preferences"] == snapshot["preferences"]
    assert bad["editor"]["bindings"] == [] and bad["editor"]["interests"] == []
    for start, end in [(-1, 20), (0, 50000), (20, 3)]:
        stale_offsets = client.post(
            "/api/drafts",
            headers=headers,
            json={
                "title": "Stale offsets",
                "editor": snapshot | {"bindings": [binding | {"start": start, "end": end}]},
            },
        )
        assert stale_offsets.status_code == 201
        assert stale_offsets.json()["editor"]["preferences"] == snapshot["preferences"]
        assert stale_offsets.json()["editor"]["bindings"] == []
    for changes in [
        {"editor_version": 2},
        {"editor_version": True},
        {"travelers": 2},
        {"preferences": "x" * 24001},
        {"interests": ["unsupported"]},
        {"transport": ["fly"]},
        {"pace": "fast"},
        {"currency": "XYZ"},
        {"interests": ["Nature", "Nature"]},
        {"unknown": "field"},
        {"bindings": [binding | {"key": "unsupported"}]},
        {"destination": "bad\u0000city"},
    ]:
        assert (
            client.post(
                "/api/drafts",
                headers=headers,
                json={"title": "Invalid", "editor": editor(**changes)},
            ).status_code
            == 422
        )


def test_simultaneous_edit_has_one_winner_and_no_lost_revision(client):  # noqa: F811
    account = register(client)
    headers = {"Origin": "http://localhost:5120", "X-CSRF-Token": account["csrf_token"]}
    data = client.post(
        "/api/drafts", headers=headers, json={"title": "Race", "editor": editor()}
    ).json()
    from backend.app.main import create_app

    cookies = dict(client.cookies)

    def write(value):
        with TestClient(create_app(), base_url="http://localhost:5120") as tab:
            tab.cookies.update(cookies)
            return tab.put(
                f"/api/drafts/{data['id']}",
                headers=headers,
                json={"title": value, "editor": editor(destination=value), "revision": 1},
            )

    with ThreadPoolExecutor(max_workers=2) as workers:
        responses = list(workers.map(write, ["First", "Second"]))
    assert sorted(response.status_code for response in responses) == [200, 409]
    saved = client.get(f"/api/drafts/{data['id']}").json()
    assert saved["revision"] == 2
    assert saved["title"] == next(
        response.json()["title"] for response in responses if response.status_code == 200
    )


def test_database_draft_constraints_and_account_cascade(client):  # noqa: F811
    account = register(client)
    dsn = SecretStr(os.environ["DAYLOOM_DB_URL"])
    with psycopg.connect(dsn.get_secret_value()) as connection:
        for title, snapshot, revision in [
            ("  ", editor(), 1),
            ("x" * 121, editor(), 1),
            ("Valid", {}, 1),
            ("Valid", [], 1),
            ("Valid", {"editor_version": True}, 1),
            ("Valid", editor(), 0),
        ]:
            with pytest.raises(psycopg.errors.CheckViolation):
                with connection.transaction():
                    connection.execute(
                        "INSERT INTO app.planning_drafts(id,owner_id,title,editor,revision) "
                        "VALUES (%s,%s,%s,%s,%s)",
                        (uuid4(), account["id"], title, Jsonb(snapshot), revision),
                    )
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            with connection.transaction():
                connection.execute(
                    "INSERT INTO app.planning_drafts(id,owner_id,title,editor) VALUES(%s,%s,%s,%s)",
                    (uuid4(), uuid4(), "Missing owner", Jsonb(editor())),
                )
        connection.execute(
            "INSERT INTO app.planning_drafts(id,owner_id,title,editor) VALUES(%s,%s,%s,%s)",
            (uuid4(), account["id"], "Cascade", Jsonb(editor())),
        )
        connection.execute("DELETE FROM app.users WHERE id=%s", (account["id"],))
        assert (
            connection.execute(
                "SELECT count(*) FROM app.planning_drafts WHERE owner_id=%s", (account["id"],)
            ).fetchone()[0]
            == 0
        )
