"""Verify case-04's selected new-date outputs and Rich completion without providers."""

import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.schemas.interpreted_requirements import InterpretedTripRequirements
from backend.app.schemas.request import PlanningRequest
from backend.app.versions.v3.completion import rich_completion
from backend.app.versions.v3.models import ValidationReport
from benchmark.verify_automatic import ROOT, load, published_sha256

CASE = "benchmark/case-04/"


def verify():
    request_data = load("benchmark/inputs/case-04.json")
    request = PlanningRequest.model_validate(request_data)
    assert request_data == load(CASE + "evaluation/input.json")
    dates = ["2026-10-25", "2026-10-26"]
    assert [str(request.start_date), str(request.end_date)] == dates
    selection = load(CASE + "selection.json")
    input_hash = published_sha256(ROOT / "benchmark/inputs/case-04.json")
    assert selection["input_sha256"] == input_hash
    assert selection["evaluation_input"]["original_sha256"] == input_hash
    assert selection["evaluation_input"]["published_sha256"] == input_hash
    assert set(selection["versions"]) == {"v0", "v1", "v2", "v3"}
    for version, binding in selection["versions"].items():
        itinerary = load(CASE + f"generation/{version}/itinerary.json")
        provenance = load(CASE + f"generation/{version}/provenance.json")
        assert [day["date"] for day in itinerary["days"]] == dates
        assert [itinerary["start_date"], itinerary["end_date"]] == dates
        assert binding["selected_input_sha256"] == provenance["input_sha256"] == input_hash
        assert binding["selected_result_sha256"] == provenance["result_sha256"]
        assert binding["run_id"] == provenance["run_id"]
        assert binding["source_revision"] == provenance["source_revision"]

    source = load(CASE + "analysis/repair/completion-input.json")
    report = load(CASE + "analysis/repair/validation.json")
    repair = load(CASE + "analysis/repair/repair.json")
    assert (
        source["original_source"]["sha256"] == selection["versions"]["v3"]["selected_result_sha256"]
    )
    assert report == repair["adopted_report"]
    contract = InterpretedTripRequirements.model_validate(source["contract"])
    assert (
        contract.request_sha256
        == hashlib.sha256(request.additional_preferences.encode()).hexdigest()
    )
    assert contract.structured_input_sha256 == request.structured_hash()
    assert contract.requirements == request.trip_requirements()
    completion = rich_completion(
        ValidationReport.model_validate(report),
        contract,
        review_enabled=source["quantity_review_enabled"],
        changed=repair["selected_round_index"] is not None,
    )
    assert completion == repair["soft_pace"]["completion"]
    assert completion["status"] == "complete"
    assert [day["date"] for day in completion["days"]] == dates
    assert all(day["count"] == 3 and day["state"] == "satisfied" for day in completion["days"])
    final = load(CASE + "analysis/repair/final-primary.json")
    selected = load(CASE + "generation/v3/itinerary.json")
    assert {k: v for k, v in final.items() if k != "reference_recommendations"} == {
        k: v for k, v in selected.items() if k != "reference_recommendations"
    }
    primary = load(CASE + "evaluation/primary/quality.json")["groups"][0]["versions"]
    pair = load(CASE + "evaluation/v3-pair/report.json")["groups"][0]
    for version, score in primary.items():
        assert score["run_id"] == selection["versions"][version]["run_id"]
        assert [day["date"] for day in score["daily_density"]["days"]] == dates
    assert pair["run_id"] == selection["versions"]["v3"]["run_id"]
    for stage in pair["stages"].values():
        assert [day["date"] for day in stage["daily_density"]["days"]] == dates
    print("Verified four new-date outputs, matched Primary/Pair and native Rich completion (3/3).")


if __name__ == "__main__":
    verify()
