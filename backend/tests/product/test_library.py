"""Mixed library and immutable saved management through the real Product API."""

from backend.tests.product.test_accounts import client, register  # noqa: F401
from backend.tests.product.test_saved import historical_content, pending


def save(client, owner, headers, **changes):  # noqa: F811
    detail = pending(owner, **changes)
    response = client.post(f"/api/previews/{detail.id}/save", headers=headers, json={})
    assert response.status_code == 200, response.text
    return detail, response.json()["saved_trip_id"]


def test_saved_rename_is_title_only_revisioned_and_keeps_historical_snapshot(client):  # noqa: F811
    account = register(client)
    headers = {"Origin": "http://localhost:5120", "X-CSRF-Token": account["csrf_token"]}
    _, identity = save(client, account["id"], headers, **historical_content())
    original = client.get(f"/api/trips/{identity}").json()
    response = client.patch(
        f"/api/trips/{identity}",
        headers=headers,
        json={"title": "  A better name  ", "revision": 1},
    )
    assert response.status_code == 200, response.text
    assert response.json() == {"id": identity, "title": "A better name", "revision": 2}
    assert client.get(f"/api/trips/{identity}").json() == original | {"title": "A better name"}
    stale = client.patch(
        f"/api/trips/{identity}", headers=headers, json={"title": "Stale title", "revision": 1}
    )
    assert stale.status_code == 409
    assert stale.json()["detail"] == {"code": "trip_revision_conflict", "revision": 2}
    for body in [
        {"title": " ", "revision": 2},
        {"title": "Forged", "revision": 2, "destination": "Elsewhere"},
        {"title": "Forged", "revision": True},
    ]:
        assert client.patch(f"/api/trips/{identity}", headers=headers, json=body).status_code == 422
    assert client.get(f"/api/trips/{identity}").json() == original | {"title": "A better name"}


def test_confirmed_saved_delete_cascades_children_keeps_receipt_and_independent_content(client):  # noqa: F811
    from backend.app.product.database import connect

    account = register(client)
    headers = {"Origin": "http://localhost:5120", "X-CSRF-Token": account["csrf_token"]}
    preview, identity = save(client, account["id"], headers, **historical_content())
    _, independent = save(client, account["id"], headers, **historical_content())
    untouched = client.get(f"/api/trips/{independent}").json()
    for body in [{}, {"revision": 1}, {"revision": 1, "confirmed": False}]:
        assert (
            client.request(
                "DELETE", f"/api/trips/{identity}", headers=headers, json=body
            ).status_code
            == 422
        )
    assert (
        client.request(
            "DELETE",
            f"/api/trips/{identity}",
            headers=headers,
            json={"revision": 2, "confirmed": True},
        ).status_code
        == 409
    )
    result = client.request(
        "DELETE", f"/api/trips/{identity}", headers=headers, json={"revision": 1, "confirmed": True}
    )
    assert result.status_code == 204, result.text
    assert result.headers["cache-control"] == "no-store"
    assert client.get(f"/api/trips/{identity}").status_code == 404
    assert client.get(f"/api/trips/{independent}").json() == untouched
    receipt = client.get(f"/api/previews/{preview.id}").json()
    assert receipt["outcome"] == "saved_result_deleted" and receipt["saved_trip_id"] == identity
    late = client.post(f"/api/previews/{preview.id}/save", headers=headers, json={})
    assert late.status_code == 409
    assert late.json()["detail"]["decision"]["outcome"] == "saved_result_deleted"
    assert client.get("/api/library").json()["total"] == 1
    with connect() as connection:
        for table in ("trip_weather", "trip_activities", "trip_nearby", "trip_transfers"):
            assert (
                connection.execute(
                    f"SELECT count(*) AS n FROM app.{table} WHERE trip_id=%s", (identity,)
                ).fetchone()["n"]
                == 0
            )
        assert (
            connection.execute(
                "SELECT count(*) AS n FROM app.itinerary_previews WHERE id=%s", (preview.id,)
            ).fetchone()["n"]
            == 1
        )


def test_saved_child_read_views_are_owner_scoped_and_match_the_historical_snapshot(client):  # noqa: F811
    from uuid import uuid4

    account = register(client)
    headers = {"Origin": "http://localhost:5120", "X-CSRF-Token": account["csrf_token"]}
    _, identity = save(client, account["id"], headers, **historical_content())
    detail = client.get(f"/api/trips/{identity}").json()
    expected = {
        "weather": [{"date": day["date"], "weather": day["weather"]} for day in detail["days"]],
        "nearby": detail["nearby"],
        "transfers": detail["transfers"],
    }
    for view, items in expected.items():
        response = client.get(f"/api/trips/{identity}/{view}")
        assert response.status_code == 200, response.text
        assert response.headers["cache-control"] == "no-store"
        assert response.json() == {"trip_id": identity, "items": items}
    for view in expected:
        assert client.get(f"/api/trips/{uuid4()}/{view}").status_code == 404
    client.cookies.clear()
    other = register(client, "other@example.com")
    other_headers = {"Origin": "http://localhost:5120", "X-CSRF-Token": other["csrf_token"]}
    for view in expected:
        assert client.get(f"/api/trips/{identity}/{view}").status_code == 404
    assert (
        client.patch(
            f"/api/trips/{identity}",
            headers=other_headers,
            json={"title": "Private", "revision": 1},
        ).status_code
        == 404
    )
    assert (
        client.request(
            "DELETE",
            f"/api/trips/{identity}",
            headers=other_headers,
            json={"confirmed": True, "revision": 1},
        ).status_code
        == 404
    )


def test_mixed_library_pages_use_creation_time_and_stable_cross_kind_ties(client):  # noqa: F811
    from backend.app.product.database import connect
    from backend.tests.product.test_drafts import editor

    account = register(client)
    headers = {"Origin": "http://localhost:5120", "X-CSRF-Token": account["csrf_token"]}
    _, saved_id = save(client, account["id"], headers)
    second = client.post(
        "/api/drafts",
        headers=headers,
        json={"title": "Same title", "editor": editor(destination="Kyoto")},
    ).json()["id"]
    third = client.post(
        "/api/drafts",
        headers=headers,
        json={"title": "Same title", "editor": editor(destination="Sydney")},
    ).json()["id"]
    # Equal identifiers are possible in distinct tables. Seed exact cross-kind boundaries.
    with connect() as connection:
        connection.execute("UPDATE app.planning_drafts SET id=%s WHERE id=%s", (saved_id, second))
        connection.execute(
            "UPDATE app.planning_drafts SET created_at='2020-01-01Z',updated_at='2020-01-01Z'"
        )
        connection.execute(
            "UPDATE app.trips SET title='Same title',created_at='2020-01-01Z',"
            "updated_at='2020-01-01Z'"
        )
    expected = sorted([(saved_id, "draft"), (saved_id, "saved"), (third, "draft")])
    for sort in ("name", "newest", "oldest"):
        pages = [
            client.get(f"/api/library?sort={sort}&limit=1&offset={index}").json()
            for index in range(3)
        ]
        assert all(page["total"] == 3 for page in pages)
        assert [(page["items"][0]["id"], page["items"][0]["kind"]) for page in pages] == expected
    # Renaming updates metadata, but cannot move creation-ordered pages.
    assert (
        client.patch(
            f"/api/trips/{saved_id}",
            headers=headers,
            json={"title": "Renamed Sydney", "revision": 1},
        ).status_code
        == 200
    )
    assert [
        (row["id"], row["kind"]) for row in client.get("/api/library?sort=newest").json()["items"]
    ] == expected
    assert client.get("/api/library?q=sYdNeY").json()["total"] == 2
    assert client.get("/api/library?q=Kyoto").json()["total"] == 1
    assert client.get("/api/library?q=%25").json()["total"] == 0
    assert client.get("/api/library?offset=3").json()["items"] == []
    for query in ("limit=51", "limit=0", "offset=-1", "offset=10001", "sort=wrong"):
        assert client.get(f"/api/library?{query}").status_code == 422
