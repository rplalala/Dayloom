"""Imported text and exact activity amounts must fit normalized PostgreSQL storage."""

# Imported pytest fixtures retain their public names.
# ruff: noqa: F811

import json
import os
from decimal import Decimal

import psycopg
import pytest
from pydantic import SecretStr

from backend.tests.product.test_accounts import client, register  # noqa: F401
from backend.tests.product.test_imports import source


@pytest.mark.parametrize("field", ["title", "notes", "key"])
def test_nul_text_and_keys_are_located_import_errors_without_receipts(client, field):
    account = register(client)
    headers = {
        "Origin": "http://localhost:5120",
        "X-CSRF-Token": account["csrf_token"],
        "X-Import-Key": "nul-text",
    }
    artifact = source()
    if field == "title":
        artifact["title"] = "A\0B"
        expected_path = "$.title"
    elif field == "notes":
        artifact["days"][0]["activities"][0]["notes"] = "Before\0after"
        expected_path = "$.days[0].activities[0].notes"
    else:
        artifact["bad\0key"] = "A value"
        expected_path = '$["bad\\u0000key"]'
    response = client.post("/api/imports", headers=headers, content=json.dumps(artifact))
    assert response.status_code == 422, response.text
    assert response.json()["detail"]["path"] == expected_path
    assert client.get("/api/imports/nul-text").status_code == 404
    assert client.get("/api/previews").json() == []


def test_unstorable_activity_amount_rejects_import_instead_of_failing_save(client):
    account = register(client)
    headers = {
        "Origin": "http://localhost:5120",
        "X-CSRF-Token": account["csrf_token"],
        "X-Import-Key": "huge-activity-cost",
    }
    artifact = source()
    artifact["days"][0]["activities"][0]["estimated_cost"] = {
        "amount": "1e1000000",
        "currency": "AUD",
    }
    response = client.post("/api/imports", headers=headers, content=json.dumps(artifact))
    observation = {"import_status": response.status_code}
    if response.status_code == 200:
        # Capture the real pre-fix persistence failure/rollback before asserting the
        # required import-boundary behavior. Never format the enormous amount.
        preview = response.json()
        save = client.post(f"/api/previews/{preview['id']}/save", headers=headers, json={})
        observation.update(
            save_status=save.status_code,
            preview_state=client.get(f"/api/previews/{preview['id']}").json()["state"],
            saved_count=client.get("/api/library").json()["total"],
        )
    assert response.status_code == 422, observation
    assert response.json()["detail"]["path"] == "$.days[0].activities[0].estimated_cost.amount"
    assert client.get("/api/imports/huge-activity-cost").status_code == 404
    assert client.get("/api/previews").json() == []


def test_valid_unicode_and_surrogate_pairs_survive_save_while_lone_surrogates_reject(client):
    account = register(client)
    headers = {
        "Origin": "http://localhost:5120",
        "X-CSRF-Token": account["csrf_token"],
        "X-Import-Key": "unicode",
    }
    artifact = source()
    artifact["title"] = "Café 🗺️"
    artifact["days"][0]["activities"][0]["notes"] = (
        "Quiet morning 🦘\nKeep literal \\u0000 wording."
    )
    # ASCII JSON escapes exercise actual paired-surrogate decoding at the API boundary.
    response = client.post(
        "/api/imports", headers=headers, content=json.dumps(artifact, ensure_ascii=True)
    )
    assert response.status_code == 200, response.text
    saved = client.post(f"/api/previews/{response.json()['id']}/save", headers=headers, json={})
    assert saved.status_code == 200, saved.text
    detail = client.get(f"/api/trips/{saved.json()['saved_trip_id']}").json()
    assert detail["title"] == "Café 🗺️"
    assert (
        detail["days"][0]["activities"][0]["notes"] == artifact["days"][0]["activities"][0]["notes"]
    )
    for key_case in (False, True):
        invalid = source()
        if key_case:
            invalid["bad\ud800key"] = "Value"
            expected_path = '$["bad\\ud800key"]'
        else:
            invalid["title"] = "A\ud800B"
            expected_path = "$.title"
        headers["X-Import-Key"] = "invalid-unicode"
        result = client.post("/api/imports", headers=headers, content=json.dumps(invalid))
        assert result.status_code == 422, result.text
        assert result.json()["detail"]["path"] == expected_path
        assert client.get("/api/imports/invalid-unicode").status_code == 404


@pytest.mark.parametrize("amount", ["1e131072", "1e-16384"])
def test_activity_amount_outside_exact_storage_boundary_is_located_and_creates_no_preview(
    client, amount
):
    account = register(client)
    headers = {
        "Origin": "http://localhost:5120",
        "X-CSRF-Token": account["csrf_token"],
        "X-Import-Key": "outside-boundary",
    }
    artifact = source()
    artifact["days"][0]["activities"][0]["estimated_cost"] = {"amount": amount, "currency": "AUD"}
    response = client.post("/api/imports", headers=headers, content=json.dumps(artifact))
    assert response.status_code == 422, response.text
    assert response.json()["detail"]["path"] == "$.days[0].activities[0].estimated_cost.amount"
    assert client.get("/api/imports/outside-boundary").status_code == 404


@pytest.mark.parametrize(
    "amount",
    [
        "123456789012345678901234567890.1234567890123456789",
        "1e-16383",
        "1.0e-16383",
        "10e-16384",
        "0e-1000000",
        "0e1000000",
    ],
)
def test_exact_activity_costs_and_insignificant_scale_survive_save_without_capping_request_budget(
    client, amount
):
    account = register(client)
    headers = {
        "Origin": "http://localhost:5120",
        "X-CSRF-Token": account["csrf_token"],
        "X-Import-Key": "exact-cost",
    }
    artifact = source()
    artifact["days"][0]["activities"][0]["estimated_cost"] = {"amount": amount, "currency": "AUD"}
    wrapper = {
        "itinerary": artifact,
        "request": {"budget": {"amount": "1e100000", "currency": "AUD"}},
    }
    response = client.post("/api/imports", headers=headers, content=json.dumps(wrapper))
    assert response.status_code == 200, response.text
    saved = client.post(f"/api/previews/{response.json()['id']}/save", headers=headers, json={})
    assert saved.status_code == 200, saved.text
    detail = client.get(f"/api/trips/{saved.json()['saved_trip_id']}").json()
    actual = Decimal(detail["days"][0]["activities"][0]["estimated_cost"]["amount"])
    if actual != Decimal(amount):
        pytest.fail("Saved cost changed its exact value")
    assert Decimal(detail["request"]["budget"]["amount"]) == Decimal("1e100000")
    assert detail["request"]["known_fields"] == ["budget"]
    # Another representation of mathematical zero uses the same operation identity.
    if actual.is_zero():
        wrapper["itinerary"]["days"][0]["activities"][0]["estimated_cost"]["amount"] = "0.000"
        replay = client.post("/api/imports", headers=headers, content=json.dumps(wrapper))
        assert (
            replay.status_code == 200
            and replay.json()["saved_trip_id"] == saved.json()["saved_trip_id"]
        )


def test_integer_numeric_boundary_saves_and_pg_reads_exactly_without_amount_expansion(client):
    account = register(client)
    headers = {
        "Origin": "http://localhost:5120",
        "X-CSRF-Token": account["csrf_token"],
        "X-Import-Key": "integer-boundary",
    }
    artifact = source()
    artifact["days"][0]["activities"][0]["estimated_cost"] = {
        "amount": "1e131071",
        "currency": "AUD",
    }
    response = client.post("/api/imports", headers=headers, content=json.dumps(artifact))
    assert response.status_code == 200, response.text
    saved = client.post(f"/api/previews/{response.json()['id']}/save", headers=headers, json={})
    assert saved.status_code == 200, saved.text
    database = SecretStr(os.environ["PRODUCT_TEST_DATABASE_URL"])
    with psycopg.connect(database.get_secret_value()) as connection:
        # The SQL comparison reads the exact stored value but returns only a boolean:
        # neither Python nor HTTP/log output expands a 131072-digit integer.
        assert connection.execute(
            "SELECT cost_amount=%s::numeric FROM app.trip_activities "
            "WHERE trip_id=%s AND activity_id='a'",
            (Decimal("1e131071"), saved.json()["saved_trip_id"]),
        ).fetchone()[0]
    assert client.get("/api/library").json()["total"] == 1
