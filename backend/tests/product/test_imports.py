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
