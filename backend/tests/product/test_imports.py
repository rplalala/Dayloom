"""Historical import behavior through the bounded public normalization seam."""

import copy
import json

import pytest

from backend.app.product.imports import ImportError, normalize_import
from backend.tests.product.test_accounts import client, register  # noqa: F401


def source():
    return {
        "destination": "Sydney",
        "title": "Old journey",
        "days": [
            {
                "date": "2020-01-04",
                "activities": [
                    {
                        "activity_id": "a",
                        "title": "Museum",
                        "start_time": "2020-01-04T11:00:00.123456789+11:00",
                        "end_time": "2020-01-04T00:40:00.123456789Z",
                    },
                ],
            },
            {"date": "2020-01-01", "activities": []},
        ],
        "nearby": [{"place_name": "Optional", "anchor_activity_id": "missing"}],
    }


def test_historical_import_preserves_order_empty_days_precision_and_partial_request():
    detail = normalize_import(
        json.dumps({"request": {"traveler_count": None}, "itinerary": source()})
    )
    assert detail.start_date == "2020-01-01"
    assert [d.date for d in detail.days] == ["2020-01-04", "2020-01-01"]
    assert detail.days[1].activities == []
    assert detail.days[0].activities[0].end_time == "2020-01-04T00:40:00.123456789Z"
    assert detail.request.known_fields == ["traveler_count"]
    assert detail.trust == "unverified_import"
    assert detail.nearby[0].anchor_activity_id == "missing"


@pytest.mark.parametrize(
    "change,location",
    [
        (lambda v: v["days"][0].update(date="2020-02-30"), "date"),
        (
            lambda v: v["days"][0]["activities"][0].update(
                end_time="2020-01-04T10:00:00Z".replace("Z", "")
            ),
            "activities",
        ),
        (
            lambda v: v["days"][0]["activities"][0].update(end_time="2020-01-04T00:00:00+11:00"),
            "activities",
        ),
        (
            lambda v: v["days"][0]["activities"][0].update(
                start_time="2020-01-04T11:00:00.1234567890+11:00"
            ),
            "start",
        ),
        (
            lambda v: v.update(transfers=[{"from_activity_id": "a", "to_activity_id": "missing"}]),
            "transfers",
        ),
        (lambda v: v.update(operation_key="forged"), "operation_key"),
        (
            lambda v: v["days"][0]["activities"][0].update(media_binding={"place": "Google"}),
            "media_binding",
        ),
        (lambda v: v.update(schema_version="future"), "schema_version"),
    ],
)
def test_import_rejects_invalid_temporal_structure_and_artifact_authority(change, location):
    value = copy.deepcopy(source())
    change(value)
    with pytest.raises(ImportError) as error:
        normalize_import(json.dumps(value))
    assert location in error.value.path


def test_claims_stay_unverified_and_nested_optional_orphans_keep_supplied_context():
    value = source()
    value["days"][0]["activities"][0]["nearby"] = [{"place_name": "Nested"}]
    value["policy_completion"] = "complete"
    detail = normalize_import(json.dumps(value))
    assert detail.completion.policy_completion == "unassessed"
    assert detail.completion.source_claims == ['policy_completion: "complete"']
    assert detail.nearby[0].anchor_activity_id == "a"
    assert detail.nearby[0].associated_day == "2020-01-04"


@pytest.mark.parametrize(
    "value",
    [
        {"itinerary": source(), "_prototype": []},
        {"itinerary": source(), "request": {"budget": {"amount": 3}}},
    ],
)
def test_malformed_known_metadata_returns_a_located_validation_error(value):
    with pytest.raises(ImportError) as error:
        normalize_import(json.dumps(value))
    assert error.value.path.startswith("$.")


def test_import_api_receipt_survives_save_recreation_and_conflicting_partial_request(client):  # noqa: F811
    from fastapi.testclient import TestClient

    from backend.app.main import create_app

    account = register(client)
    headers = {
        "Origin": "http://localhost:5120",
        "X-CSRF-Token": account["csrf_token"],
        "X-Import-Key": "import-once",
    }
    content = {"itinerary": source(), "request": {"traveler_count": None}}
    first = client.post("/api/imports", headers=headers, content=json.dumps(content))
    assert first.status_code == 200, first.text
    receipt = first.json()
    assert receipt["state"] == "pending"
    assert client.get("/api/imports/import-once").json() == receipt
    assert (
        client.post("/api/imports", headers=headers, content=json.dumps(content)).json() == receipt
    )
    content["request"]["traveler_count"] = 2
    assert (
        client.post("/api/imports", headers=headers, content=json.dumps(content)).status_code == 409
    )
    content["request"]["traveler_count"] = None
    saved = client.post(f"/api/previews/{receipt['id']}/save", headers=headers, json={}).json()
    detail = client.get(f"/api/trips/{saved['saved_trip_id']}").json()
    assert detail["request"]["known_fields"] == ["traveler_count"]
    assert detail["days"][0]["activities"][0]["start_time"].endswith(".123456789+11:00")
    with TestClient(create_app(), base_url="http://localhost:5120") as recreated:
        recreated.cookies.update(client.cookies)
        retry = recreated.post("/api/imports", headers=headers, content=json.dumps(content))
        assert retry.status_code == 200, retry.text
        assert retry.json()["saved_trip_id"] == saved["saved_trip_id"]
        assert retry.json()["snapshot"] == detail
    assert len(client.get("/api/library").json()["items"]) == 1


def test_import_concurrency_discard_and_owner_isolation(client):  # noqa: F811
    from concurrent.futures import ThreadPoolExecutor

    from fastapi.testclient import TestClient

    from backend.app.main import create_app

    account = register(client)
    headers = {
        "Origin": "http://localhost:5120",
        "X-CSRF-Token": account["csrf_token"],
        "X-Import-Key": "racing",
    }
    cookies = dict(client.cookies)

    def send(_):
        with TestClient(create_app(), base_url="http://localhost:5120") as other:
            other.cookies.update(cookies)
            result = other.post("/api/imports", headers=headers, content=json.dumps(source()))
            assert result.status_code == 200, result.text
            return result.json()

    with ThreadPoolExecutor(max_workers=3) as workers:
        receipts = list(workers.map(send, range(3)))
    assert len({item["id"] for item in receipts}) == 1
    identity = receipts[0]["id"]
    assert len(client.get("/api/previews").json()) == 1
    assert (
        client.post(
            f"/api/previews/{identity}/discard", headers=headers, json={"confirmed": True}
        ).status_code
        == 200
    )
    retry = client.post("/api/imports", headers=headers, content=json.dumps(source())).json()
    assert retry["state"] == "discarded" and retry["snapshot"] is None
    assert client.get("/api/previews").json() == []
    with TestClient(create_app(), base_url="http://localhost:5120") as other:
        stranger = register(other, "other@example.com")
        assert other.get("/api/imports/racing").status_code == 404
        headers["X-CSRF-Token"] = stranger["csrf_token"]
        distinct = other.post("/api/imports", headers=headers, content=json.dumps(source()))
        assert distinct.status_code == 200 and distinct.json()["id"] != identity


def test_public_api_rejects_malformed_fields_without_leaving_previews(client):  # noqa: F811
    account = register(client)
    headers = {
        "Origin": "http://localhost:5120",
        "X-CSRF-Token": account["csrf_token"],
        "X-Import-Key": "invalid",
    }
    cases = []
    value = source()
    value["days"].append(copy.deepcopy(value["days"][0]))
    cases.append((value, "date"))
    value = source()
    value["days"][0]["activities"].append(copy.deepcopy(value["days"][0]["activities"][0]))
    cases.append((value, "activity_id"))
    value = source()
    value["days"][1]["activities"] = [
        {
            "activity_id": "b",
            "title": "Other day",
            "start_time": "2020-01-01T09:00",
            "end_time": "2020-01-01T10:00",
        }
    ]
    value["transfers"] = [{"from_activity_id": "a", "to_activity_id": "b"}]
    cases.append((value, "transfers"))
    value = source()
    value["days"][0]["activities"][0]["end_time"] = "2020-01-04T12:00"
    cases.append((value, "activities"))
    value = source()
    value["days"][0]["activities"][0]["end_time"] = "2020-01-04T11:30+12:00"
    cases.append((value, "activities"))
    value = source()
    value["days"][0]["activities"][0]["estimated_cost"] = {"amount": 3}
    cases.append((value, "currency"))
    value = source()
    value["days"][0]["activities"][0]["estimated_cost"] = {"amount": True, "currency": "AUD"}
    cases.append((value, "amount"))
    value = source()
    value["days"][0]["activities"][0]["estimated_cost"] = {"amount": "Infinity", "currency": "AUD"}
    cases.append((value, "amount"))
    value = source()
    value["days"][0]["weather"] = {"temperature_min_c": True}
    cases.append((value, "temperature_min_c"))
    value = source()
    value["start_date"] = ""
    cases.append((value, "start_date"))
    for value, path in cases:
        result = client.post("/api/imports", headers=headers, content=json.dumps(value))
        assert result.status_code == 422, result.text
        assert path in result.json()["detail"]["path"]
    assert client.post("/api/imports", headers=headers, content='{"days":NaN}').status_code == 422
    assert (
        client.post(
            "/api/imports", headers=headers, content="x" * (5 * 1024 * 1024 + 1)
        ).status_code
        == 413
    )
    assert client.get("/api/previews").json() == []


def test_public_import_retains_claims_aliases_and_semantic_money_identity(client):  # noqa: F811
    account = register(client)
    headers = {
        "Origin": "http://localhost:5120",
        "X-CSRF-Token": account["csrf_token"],
        "X-Import-Key": "claims",
    }
    value = source()
    value["days"][0]["activities"].append(
        {
            "activity_id": "b",
            "title": "A free window",
            "time_use": "free_window",
            "start_time": "2020-01-04T12:00Z",
            "end_time": "2020-01-04T13:00Z",
        }
    )
    value["transfers"] = [
        {
            "from_activity_id": "a",
            "to_activity_id": "b",
            "estimate_kind": "derived",
            "validation_state": "PASS",
            "provider_duration_seconds": 0,
            "distance_meters": None,
        }
    ]
    wrapper = {
        "itinerary": value,
        "input": {"people": 2, "activity_budget": "20.00", "currency": "AUD"},
        "origin": "Google verified",
        "policy_completion": "complete",
    }
    result = client.post("/api/imports", headers=headers, content=json.dumps(wrapper))
    assert result.status_code == 200, result.text
    detail = result.json()["snapshot"]
    assert detail["request"]["known_fields"] == ["budget", "traveler_count"]
    assert detail["completion"]["policy_completion"] == "unassessed"
    assert 'origin: "Google verified"' in detail["completion"]["source_claims"]
    assert detail["transfers"][0]["source_status"] == "PASS"
    assert detail["transfers"][0]["status"] == "source_claim"
    wrapper["input"]["activity_budget"] = 20
    retry = client.post("/api/imports", headers=headers, content=json.dumps(wrapper))
    assert retry.status_code == 200, retry.text
    assert retry.json()["id"] == result.json()["id"]
    wrapper["itinerary"]["days"][0]["activities"][0]["owner_id"] = "forged"
    assert (
        client.post("/api/imports", headers=headers, content=json.dumps(wrapper)).status_code == 422
    )


def test_public_import_fingerprints_exact_high_precision_requests(client):  # noqa: F811
    account = register(client)
    headers = {
        "Origin": "http://localhost:5120",
        "X-CSRF-Token": account["csrf_token"],
        "X-Import-Key": "precision",
    }
    value = {
        "itinerary": source(),
        "request": {"budget": {"amount": "123456789012345678901234567890.1", "currency": "AUD"}},
    }
    assert (
        client.post("/api/imports", headers=headers, content=json.dumps(value)).status_code == 200
    )
    value["request"]["budget"]["amount"] = "123456789012345678901234567890.2"
    assert (
        client.post("/api/imports", headers=headers, content=json.dumps(value)).status_code == 409
    )
    headers["X-Import-Key"] = "large-exponent"
    value["request"]["budget"]["amount"] = "1e100000"
    assert (
        client.post("/api/imports", headers=headers, content=json.dumps(value)).status_code == 200
    )
    value["request"]["budget"]["amount"] = "10e99999"
    assert (
        client.post("/api/imports", headers=headers, content=json.dumps(value)).status_code == 200
    )
    headers["X-Import-Key"] = "numeric-precision"
    value["request"]["budget"]["amount"] = "0.12345678901234567890123456789"
    numeric = json.dumps(value).replace(
        '"0.12345678901234567890123456789"', "0.12345678901234567890123456789"
    )
    accepted = client.post("/api/imports", headers=headers, content=numeric)
    assert accepted.status_code == 200, accepted.text
    assert (
        accepted.json()["snapshot"]["request"]["budget"]["amount"]
        == "0.12345678901234567890123456789"
    )
    assert (
        client.post(
            "/api/imports", headers=headers, content=numeric.replace("56789,", "56788,")
        ).status_code
        == 409
    )


def test_documented_bare_versions_and_bundled_r7_fixture_import_through_api(client):  # noqa: F811
    from pathlib import Path

    account = register(client)
    headers = {"Origin": "http://localhost:5120", "X-CSRF-Token": account["csrf_token"]}
    for version in ("itinerary_1", "itinerary_2", "itinerary_3"):
        value = source() | {"output_version": version}
        headers["X-Import-Key"] = version
        response = client.post("/api/imports", headers=headers, content=json.dumps(value))
        assert response.status_code == 200, response.text
        assert response.json()["snapshot"]["days"][1]["activities"] == []
    headers["X-Import-Key"] = "actual-r7"
    fixture = Path("backend/app/product/examples/nearby-linking.json").read_text(encoding="utf-8")
    response = client.post("/api/imports", headers=headers, content=fixture)
    assert response.status_code == 200, response.text
    assert any(
        item["anchor_activity_id"] == "missing-activity"
        for item in response.json()["snapshot"]["nearby"]
    )


def test_invalid_known_field_declarations_are_located_errors():
    for known in ([{}], ["traveler_count", "traveler_count"], []):
        with pytest.raises(ImportError) as error:
            normalize_import(
                json.dumps(
                    {"itinerary": source(), "request": {"traveler_count": 2, "known_fields": known}}
                )
            )
        assert error.value.path == "$.request.known_fields"


@pytest.mark.parametrize("claims", [True, 42, "complete", None, {}, {"claimed": "PASS"}, [42]])
def test_public_import_rejects_malformed_source_claims_with_field_location(client, claims):  # noqa: F811
    account = register(client)
    headers = {
        "Origin": "http://localhost:5120",
        "X-CSRF-Token": account["csrf_token"],
        "X-Import-Key": "invalid-claims",
    }
    value = source() | {"completion": {"source_claims": claims}}
    response = client.post("/api/imports", headers=headers, content=json.dumps(value))
    assert response.status_code == 422, response.text
    assert response.json()["detail"]["path"].startswith("$.completion.source_claims")
    assert client.get("/api/previews").json() == []


@pytest.mark.parametrize("field", ["temperature_min_c", "max_wind_speed_kph"])
def test_public_import_rejects_unrepresentable_weather_with_field_location(client, field):  # noqa: F811
    account = register(client)
    headers = {
        "Origin": "http://localhost:5120",
        "X-CSRF-Token": account["csrf_token"],
        "X-Import-Key": "invalid-measurement",
    }
    value = source()
    value["days"][0]["weather"] = {field: 10**1000}
    response = client.post("/api/imports", headers=headers, content=json.dumps(value))
    assert response.status_code == 422, response.text
    assert response.json()["detail"]["path"] == f"$.days[0].weather.{field}"
    assert client.get("/api/previews").json() == []


def conflicting_source(next_start="10:00"):
    return {
        "title": "Historical connection conflict",
        "destination": "Sydney",
        "days": [
            {
                "date": "2020-01-01",
                "activities": [
                    {
                        "activity_id": "first",
                        "title": "First stop",
                        "start_time": "2020-01-01T09:00",
                        "end_time": "2020-01-01T10:00",
                    },
                    {
                        "activity_id": "second",
                        "title": "Second stop",
                        "start_time": "2020-01-01T" + next_start,
                        "end_time": "2020-01-01T11:00",
                    },
                ],
            }
        ],
        "transfers": [
            {
                "from_activity_id": "first",
                "to_activity_id": "second",
                "preceding_end_time": "2020-01-01T10:00",
                "following_start_time": "2020-01-01T" + next_start,
                "provider_duration_seconds": 300,
                "validation_state": "CONFIRMED",
            }
        ],
    }


@pytest.mark.parametrize("next_start", ["10:00", "09:59"])
def test_public_import_saves_zero_and_negative_available_connection_gaps(client, next_start):  # noqa: F811
    account = register(client)
    headers = {
        "Origin": "http://localhost:5120",
        "X-CSRF-Token": account["csrf_token"],
        "X-Import-Key": "conflict",
    }
    value = conflicting_source(next_start)
    response = client.post("/api/imports", headers=headers, content=json.dumps(value))
    assert response.status_code == 200, response.text
    preview = response.json()
    saved = client.post(f"/api/previews/{preview['id']}/save", headers=headers, json={})
    assert saved.status_code == 200, saved.text
    detail = client.get(f"/api/trips/{saved.json()['saved_trip_id']}").json()
    transfer = detail["transfers"][0]
    assert transfer["following_start_time"] == "2020-01-01T" + next_start
    assert transfer["source_status"] == "CONFIRMED" and transfer["status"] == "source_claim"
    assert detail["trust"] == "unverified_import"


def test_exported_origin_and_existing_claims_are_retained_only_as_source_claims(client):  # noqa: F811
    account = register(client)
    headers = {
        "Origin": "http://localhost:5120",
        "X-CSRF-Token": account["csrf_token"],
        "X-Import-Key": "exported-origin",
    }
    origin = {
        "provenance": "generated",
        "trust": "generated_projection",
        "assertion": "source_snapshot_only",
    }
    wrapper = {
        "schema_version": "dayloom_export_1",
        "origin": origin,
        "completion": {
            "source_claims": ["Original supplied note"],
            "policy_completion": "complete",
        },
        "itinerary": conflicting_source(),
    }
    response = client.post("/api/imports", headers=headers, content=json.dumps(wrapper))
    assert response.status_code == 200, response.text
    detail = response.json()["snapshot"]
    assert detail["provenance"] == "imported" and detail["trust"] == "unverified_import"
    assert detail["completion"]["policy_completion"] == "unassessed"
    assert "Original supplied note" in detail["completion"]["source_claims"]
    assert 'policy_completion: "complete"' in detail["completion"]["source_claims"]
    source_origin = next(
        claim for claim in detail["completion"]["source_claims"] if claim.startswith("origin: ")
    )
    assert json.loads(source_origin.removeprefix("origin: ")) == origin


@pytest.mark.parametrize(
    "change",
    [
        {"following_start_time": "2020-01-01T10:00Z"},
        {"departure_time": "2020-01-01T10:00", "arrival_time": "2020-01-01T09:59"},
        {"departure_time": "2020-01-01T10:00", "arrival_time": "2020-01-01T10:00"},
    ],
)
def test_conflicting_schedule_gaps_do_not_relax_transfer_time_validation(client, change):  # noqa: F811
    account = register(client)
    headers = {
        "Origin": "http://localhost:5120",
        "X-CSRF-Token": account["csrf_token"],
        "X-Import-Key": "malformed-conflict",
    }
    value = conflicting_source()
    value["transfers"][0].update(change)
    response = client.post("/api/imports", headers=headers, content=json.dumps(value))
    assert response.status_code == 422, response.text
    assert response.json()["detail"]["path"].startswith("$.transfers[0]")


def test_deleted_import_receipt_survives_recreation_and_concurrent_replay_without_resurrection(
    client,  # noqa: F811
):  # noqa: F811
    from concurrent.futures import ThreadPoolExecutor

    from fastapi.testclient import TestClient

    from backend.app.main import create_app

    account = register(client)
    headers = {
        "Origin": "http://localhost:5120",
        "X-CSRF-Token": account["csrf_token"],
        "X-Import-Key": "deleted-import",
    }
    content = json.dumps(source())
    preview = client.post("/api/imports", headers=headers, content=content).json()
    saved = client.post(f"/api/previews/{preview['id']}/save", headers=headers, json={}).json()
    identity = saved["saved_trip_id"]
    assert (
        client.request(
            "DELETE",
            f"/api/trips/{identity}",
            headers=headers,
            json={"revision": 1, "confirmed": True},
        ).status_code
        == 204
    )
    receipt = client.get("/api/imports/deleted-import").json()
    assert receipt["id"] == preview["id"] and receipt["saved_trip_id"] == identity
    assert receipt["outcome"] == "saved_result_deleted" and receipt["snapshot"] is None
    cookies = dict(client.cookies)

    def replay(_):
        with TestClient(create_app(), base_url="http://localhost:5120") as recreated:
            recreated.cookies.update(cookies)
            assert recreated.get("/api/imports/deleted-import").json() == receipt
            result = recreated.post("/api/imports", headers=headers, content=content)
            assert result.status_code == 200, result.text
            return result.json()

    with ThreadPoolExecutor(max_workers=3) as workers:
        assert list(workers.map(replay, range(3))) == [receipt, receipt, receipt]
    assert client.get(f"/api/trips/{identity}").status_code == 404
    assert client.get("/api/previews").json() == []
    assert client.get("/api/library").json()["total"] == 0
    late_save = client.post(f"/api/previews/{preview['id']}/save", headers=headers, json={})
    assert late_save.status_code == 409
    assert late_save.json()["detail"]["decision"]["outcome"] == "saved_result_deleted"
    assert (
        client.post(
            "/api/imports", headers=headers, content=json.dumps(source() | {"title": "Changed"})
        ).status_code
        == 409
    )
    headers["X-Import-Key"] = "explicit-new-import"
    new_preview = client.post("/api/imports", headers=headers, content=content)
    assert new_preview.status_code == 200, new_preview.text
    assert new_preview.json()["id"] != preview["id"] and new_preview.json()["state"] == "pending"
    new_saved = client.post(
        f"/api/previews/{new_preview.json()['id']}/save", headers=headers, json={}
    ).json()
    assert new_saved["saved_trip_id"] != identity
    assert client.get("/api/library").json()["total"] == 1
    assert client.get("/api/imports/deleted-import").json() == receipt


def test_structured_export_origin_retains_only_public_source_metadata(client):  # noqa: F811
    account = register(client)
    headers = {
        "Origin": "http://localhost:5120",
        "X-CSRF-Token": account["csrf_token"],
        "X-Import-Key": "public-origin",
    }
    origin = {
        "provenance": "generated",
        "trust": "generated_projection",
        "assertion": "source_snapshot_only",
    }
    value = {
        "schema_version": "dayloom_export_1",
        "itinerary": source(),
        "origin": origin | {"provider_diagnostics": {"api_key": "PRIVATE-SOURCE-MARKER"}},
    }
    response = client.post("/api/imports", headers=headers, content=json.dumps(value))
    assert response.status_code == 200, response.text
    claims = response.json()["snapshot"]["completion"]["source_claims"]
    assert (
        json.loads(
            next(claim.removeprefix("origin: ") for claim in claims if claim.startswith("origin: "))
        )
        == origin
    )
    assert (
        "PRIVATE-SOURCE-MARKER" not in response.text and "provider_diagnostics" not in response.text
    )
