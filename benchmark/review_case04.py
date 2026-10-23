"""Replay case-04 completion and verify its offline date revision without providers."""

import hashlib
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.schemas.interpreted_requirements import InterpretedTripRequirements
from backend.app.schemas.request import PlanningRequest
from backend.app.versions.v3.completion import rich_completion
from backend.app.versions.v3.models import ValidationReport
from benchmark.verify_automatic import ROOT, digest, load, published_sha256

CASE = "benchmark/case-04/"


def completion_review():
    source = load(CASE + "analysis/repair/completion-input.json")
    report = load(CASE + "analysis/repair/validation.json")
    repair = load(CASE + "analysis/repair/repair.json")
    selection = load(CASE + "selection.json")
    assert (
        source["original_source"]["sha256"] == selection["versions"]["v3"]["selected_result_sha256"]
    )
    assert report == repair["adopted_report"]
    contract = InterpretedTripRequirements.model_validate(source["contract"])
    request = PlanningRequest.model_validate(load(CASE + "evaluation/input.json"))
    assert (
        contract.request_sha256
        == hashlib.sha256(request.additional_preferences.encode()).hexdigest()
    )
    assert contract.structured_input_sha256 == request.structured_hash()
    assert contract.requirements == request.trip_requirements()
    assert repair["selected_round_index"] is not None
    completion = rich_completion(
        ValidationReport.model_validate(report), contract, review_enabled=True, changed=True
    )
    return {
        "schema_version": "case_completion_review_1",
        "scope": "Offline completion classification of the original 24-25 October output",
        "implementation_revision": source["implementation_revision"],
        "run_id": selection["versions"]["v3"]["run_id"],
        "original_result_sha256": source["original_source"]["sha256"],
        "validation_semantic_sha256": digest(report),
        "contract_semantic_sha256": digest(source["contract"]),
        "original_completion": repair["soft_pace"]["completion"],
        "completion": completion,
        "retained_unknown_findings": [f for f in report["findings"] if f["status"] == "UNKNOWN"],
        "provider_calls": 0,
        "limitation": (
            "Saved validation evidence is unchanged; no generation or acquisition replay."
        ),
    }


def shift_time(value):
    return (datetime.fromisoformat(value) + timedelta(days=1)).isoformat()


def schedule_projection(original):
    """Retain submitted schedules, excluding old weather, prices and verified route claims."""
    activity_keys = (
        "activity_id",
        "title",
        "place_name",
        "source_place_id",
        "location",
        "activity_kind",
        "time_use",
    )
    return {
        "destination": original["destination"],
        "start_date": "2026-10-25",
        "end_date": "2026-10-26",
        "days": [
            {
                "date": str(date.fromisoformat(day["date"]) + timedelta(days=1)),
                "activities": [
                    {
                        **{key: activity[key] for key in activity_keys},
                        "start_time": shift_time(activity["start_time"]),
                        "end_time": shift_time(activity["end_time"]),
                    }
                    for activity in day["activities"]
                ],
            }
            for day in original["days"]
        ],
        "proposed_transfers": [
            {
                **{
                    key: transfer[key]
                    for key in (
                        "from_activity_id",
                        "to_activity_id",
                        "origin_place_id",
                        "destination_place_id",
                        "mode",
                    )
                },
                "departure_time": shift_time(transfer["departure_time"]),
                "arrival_time": shift_time(transfer["arrival_time"]),
            }
            for transfer in original.get("transfers", [])
        ],
    }


def verify():
    assert completion_review() == load(CASE + "analysis/repair/completion-review.json")
    revision = load(CASE + "rescheduled/revision.json")
    request = load("benchmark/inputs/case-04.json")
    PlanningRequest.model_validate(request)
    assert (request["start_date"], request["end_date"]) == ("2026-10-25", "2026-10-26")
    assert published_sha256(ROOT / "benchmark/inputs/case-04.json") == revision["input_sha256"]
    selection = load(CASE + "selection.json")
    assert (
        published_sha256(ROOT / CASE / "evaluation/input.json")
        == selection["evaluation_input"]["published_sha256"]
    )
    assert selection["evaluation_input"]["original_sha256"] == selection["input_sha256"]
    assert set(revision["versions"]) == {"v0", "v1", "v2", "v3"}
    for version, binding in revision["versions"].items():
        original = load(CASE + f"generation/{version}/itinerary.json")
        revised = load(CASE + binding["path"])
        assert revised["source_semantic_sha256"] == digest(original)
        assert revised["schedule"] == schedule_projection(original)
        assert revised["input_sha256"] == revision["input_sha256"]
        assert [day["date"] for day in revised["schedule"]["days"]] == ["2026-10-25", "2026-10-26"]
        assert revised["evaluation_status"] == "not_evaluated_for_revised_dates"
        assert (
            revised["original_result_sha256"]
            == selection["versions"][version]["selected_result_sha256"]
        )
        assert published_sha256(ROOT / CASE / binding["path"]) == binding["sha256"]
    print("Verified original-date completion and all four 25-26 October schedule revisions.")


if __name__ == "__main__":
    verify()
