"""Completion receipts preserve native failures and unknown costs without execution."""

import json
from decimal import Decimal

import pytest

from tools.validation.generation_receipt import complete_generation_receipt


def complete(tmp_path, cost):
    receipt = tmp_path / "execution-v3.json"
    receipt.write_text(json.dumps({"started_at": "saved-start", "retries": 0}), encoding="utf-8")
    capture = tmp_path / "capture"
    capture.mkdir()
    (capture / "failure.json").write_text(
        json.dumps({"error": "SemanticAssessmentError"}), encoding="utf-8"
    )
    if cost is not None:
        (capture / "cost-report.json").write_text(json.dumps({"runs": [cost]}), encoding="utf-8")
    result = complete_generation_receipt(
        receipt,
        capture,
        completed_at="saved-end",
        exit_code=1,
        spent_before_usd=Decimal("12.686448525"),
    )
    assert json.loads(receipt.read_text(encoding="utf-8")) == result
    assert result["completed_at"] == "saved-end" and result["exit_code"] == 1
    assert result["failure.json"] == {"error": "SemanticAssessmentError"}
    assert result["started_at"] == "saved-start" and result["retries"] == 0
    return result


def test_unknown_cost_keeps_subtotal_and_native_completion(tmp_path):
    result = complete(
        tmp_path,
        {
            "best_available_total": None,
            "best_available_observed_subtotal": "3.036190545",
            "unpriced_event_count": 2,
        },
    )
    assert result["estimated_usd"] is None and result["cumulative_usd"] is None
    assert result["unpriced_event_count"] == 2
    assert result["observed_subtotal_usd"] == "3.036190545"
    assert result["cumulative_known_subtotal_usd"] == "15.722639070"


@pytest.mark.parametrize("amount,expected", [("0", "12.686448525"), ("2.5", "15.186448525")])
def test_known_total_including_zero_remains_exact(tmp_path, amount, expected):
    result = complete(
        tmp_path,
        {
            "best_available_total": amount,
            "best_available_observed_subtotal": amount,
            "unpriced_event_count": 0,
        },
    )
    assert result["estimated_usd"] == amount and result["cumulative_usd"] == expected


def test_missing_cost_does_not_invent_zero_or_lose_completion(tmp_path):
    result = complete(tmp_path, None)
    assert result["estimated_usd"] is None and result["cumulative_usd"] is None
    assert result["observed_subtotal_usd"] is None
    assert result["cumulative_known_subtotal_usd"] == "12.686448525"


def test_malformed_cost_still_saves_native_completion(tmp_path):
    receipt = tmp_path / "receipt.json"
    receipt.write_text("{}", encoding="utf-8")
    (tmp_path / "cost-report.json").write_text("invalid", encoding="utf-8")
    result = complete_generation_receipt(
        receipt,
        tmp_path,
        completed_at="saved-end",
        exit_code=1,
        spent_before_usd=Decimal(0),
    )
    assert json.loads(receipt.read_text(encoding="utf-8"))["exit_code"] == 1
    assert result["cumulative_usd"] is None
    assert result["receipt_errors"] == ["cost-report.json:JSONDecodeError"]
