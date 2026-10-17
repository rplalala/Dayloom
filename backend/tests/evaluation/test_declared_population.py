"""Synthetic checks for the separately versioned finite-candidate scoring policy."""

import copy
import json

import pytest

from backend.evaluation.declared_population import (
    PROFILE_ID,
    UnreadyPopulation,
    population_readiness,
)
from backend.evaluation.intake import load_batch
from backend.evaluation.quality_report import build_quality_report
from backend.tests.evaluation import test_routes as route_tests
from backend.tests.evaluation.test_daily_density import density_reviews
from backend.tests.evaluation.test_quality_report import report
from backend.tests.evaluation.test_requirement_schedule import context

pytest_plugins = ("backend.tests.evaluation.test_intake",)
prepared_scenario = route_tests.prepared_scenario
route_case = route_tests.route_case


def test_declared_profile_retains_unknown_factual_candidates_with_known_denominators(route_case):
    case = route_case(unresolved_names=["Museum A", "Museum B"])
    result = report(
        case,
        quality_profile="rtpeval_declared_population_1",
        density_reviews=density_reviews(case[0].to_dict(), "ordinary"),
    )
    assert result["status"] == "complete", result["diagnostics"]
    assert result["rules_profile_id"] == "rtpeval_declared_population_1"
    for version in result["groups"][0]["versions"].values():
        assert version["dimensions"]["grounding"]["counts"] == {"PASS": 0, "FAIL": 0, "UNKNOWN": 2}
        assert version["dimensions"]["grounding"]["denominator"] == 2
        assert version["dimensions"]["routes"]["denominator"] == 1
        assert version["overall_total"]["score_0_100"] is not None
        assert version["candidate_inventory"]["grounding"]


def test_numerical_population_gate_rejects_unreviewed_density_before_snapshot_access(route_case):
    case = route_case()
    result = build_quality_report(
        case[0],
        case[1],
        "must-not-be-read",
        quality_profile="rtpeval_declared_population_1",
        generated_at="2026-10-16T00:00:00Z",
    ).to_dict()
    assert result["status"] == "needs_population_resolution"
    assert any(d["reason"] == "density_policy_unresolved" for d in result["diagnostics"])


def declared_results(results):
    route_tests.no_departure(results)
    for result in results.values():
        plan = result["itinerary"]
        plan["output_version"] = "itinerary_3"
        for activity in plan["days"][0]["activities"]:
            activity["time_use"] = "scheduled"


def test_known_date_offset_conflicts_keep_the_candidate_population_ready(batch):
    _, results, write, _, _ = batch
    declared_results(results)
    for activity in results["v0"]["itinerary"]["days"][0]["activities"]:
        for field in ("start_time", "end_time"):
            activity[field] = activity[field].replace("+00:00", "+01:00").replace("Z", "+01:00")
    for version in results:
        write(version)
    loaded = load_batch(write())
    intake = loaded.to_dict()
    original = copy.deepcopy(intake)
    readiness = population_readiness(
        intake, context(loaded, "Europe/London"), density_reviews=density_reviews(intake)
    )
    assert readiness["status"] == "ready", readiness["diagnostics"]
    row = next(row for row in readiness["rows"] if row["version"] == "v0")
    assert {name: len(checks) for name, checks in row["inventory"].items()} == {
        "requirements": 0,
        "grounding": 2,
        "non_overlap": 2,
        "opening": 2,
        "routes": 1,
    }
    assert len(readiness["time_uncertainties"]) == 2
    assert all(
        item["interval"]["reasons"] == ["timezone_offset_conflict"]
        and item["interval"]["interval"] is None
        for item in readiness["time_uncertainties"]
    )
    assert readiness["provider_calls"] == 0
    assert intake == original


@pytest.mark.parametrize(
    ("start", "end", "day"),
    [
        ("2020-01-02T09:00:00Z", "2020-01-02T10:00:00Z", "2020-01-01"),
        ("2020-01-01T23:30:00Z", "2020-01-02T00:30:00Z", "2020-01-01"),
        ("2020-01-01T00:15:00+01:00", "2020-01-01T00:45:00+01:00", "2020-01-01"),
        ("2020-01-01T09:00:00Z", "2020-01-01T08:00:00Z", "2020-01-01"),
        ("2020-01-01T09:00:00+01:00", "2020-01-01T10:00:00+01:00", "2020-01-02"),
    ],
)
def test_unknown_or_conflicting_date_membership_still_blocks(batch, start, end, day):
    _, results, write, _, _ = batch
    declared_results(results)
    changed_day = results["v0"]["itinerary"]["days"][0]
    changed_day["date"] = day
    changed_day["activities"][0].update(start_time=start, end_time=end)
    for version in results:
        write(version)
    intake = load_batch(write())
    if intake.status != "accepted":
        assert intake.status == "needs_material_correction"
        return
    readiness = population_readiness(
        intake.to_dict(), context(intake, "Europe/London"), density_reviews=density_reviews(intake)
    )
    assert readiness["status"] == "needs_population_resolution"
    assert any(
        item["reason"] == "activity_date_or_interval_unresolved"
        and item["sources"][0]["pointer"] == "/itinerary/days/0/activities/0"
        for item in readiness["diagnostics"]
    )
    assert readiness["provider_calls"] == 0


@pytest.mark.parametrize("start", [None, "invalid"])
def test_invalid_timestamps_are_rejected_before_population_preparation(batch, start):
    _, results, write, _, _ = batch
    declared_results(results)
    results["v0"]["itinerary"]["days"][0]["activities"][0]["start_time"] = start
    for version in results:
        write(version)
    assert load_batch(write()).status == "needs_material_correction"


def test_prepare_freezes_offset_conflicts_without_rewriting_sources(batch):
    from backend.evaluation.evaluation_run import prepare_run
    from backend.tests.evaluation.test_evaluation_run import options, run_prices

    _, results, write, _, root = batch
    declared_results(results)
    activity = results["v0"]["itinerary"]["days"][0]["activities"][0]
    activity.update(start_time="2020-01-01T09:00:00+01:00", end_time="2020-01-01T10:00:00+01:00")
    for version in results:
        write(version)
    manifest = write()
    intake = load_batch(manifest)
    originals = {p: p.read_bytes() for p in root.glob("*.json")}
    directory = root / "prepared"
    prepared = prepare_run(
        manifest,
        directory,
        options=options(),
        prices=run_prices(),
        schedule_context=context(intake, "Europe/London"),
        density_reviews=density_reviews(intake),
    )
    population = prepared["population_readiness"]
    assert prepared["status"] == "prepared"
    assert population["status"] == "ready"
    uncertainty = population["time_uncertainties"][0]
    assert uncertainty["interval"]["original_start"] == "2020-01-01T09:00:00+01:00"
    assert uncertainty["interval"]["status"] == "unknown"
    assert (
        uncertainty["source"]["artifact_sha256"]
        == prepared["intake"]["inventory"][0]["runs"]["v0"]["final"]["context"]["artifact_sha256"]
    )
    assert json.loads((directory / "preparation.json").read_bytes()) == prepared
    assert not (directory / "execution").exists()
    assert {p: p.read_bytes() for p in originals} == originals


def test_offset_conflicts_remain_unknown_in_the_final_candidate_metrics(route_case):
    def conflict(results):
        declared_results(results)
        activity = results["v0"]["itinerary"]["days"][0]["activities"][0]
        activity.update(
            start_time="2020-01-01T09:00:00+01:00", end_time="2020-01-01T10:00:00+01:00"
        )

    case = route_case(change=conflict)
    result = report(case, density_reviews=density_reviews(case[0]))
    assert result["status"] == "complete", result["diagnostics"]
    version = result["groups"][0]["versions"]["v0"]
    assert version["dimensions"]["non_overlap"]["denominator"] == 2
    assert version["dimensions"]["non_overlap"]["counts"]["UNKNOWN"] == 2
    checks = version["primary_metrics"]["opening"]["checks"]
    first = next(check for check in checks if check["activity_id"] == "a")
    assert first["state"] == "UNKNOWN"
    assert "timezone_offset_conflict" in first["reasons"]
    assert first["interval"]["original_start"] == "2020-01-01T09:00:00+01:00"
    assert version["primary_metrics"]["routes"]["checks"][0]["state"] == "UNKNOWN"
    assert version["overall_total"]["score_0_100"] is not None


@pytest.mark.parametrize("end", ["14:00", "15:00"])
def test_historical_opt_in_rejects_nonpositive_intervals_with_wrong_offsets(batch, end):
    from backend.evaluation.evaluation_run import prepare_run
    from backend.tests.evaluation.test_evaluation_run import options, run_prices
    from backend.tests.evaluation.test_intake import activity

    _, results, write, _, root = batch
    route_tests.no_departure(results)
    rest = activity("rest", "Rest", "15:00", end, role="free_time")
    for field in ("start_time", "end_time"):
        rest[field] = rest[field].replace("+00:00", "+01:00")
    results["v0"]["itinerary"]["days"][0]["activities"].append(rest)
    for version in results:
        write(version)
    manifest = write()
    intake = load_batch(manifest)
    assert intake.status == "accepted"
    directory = root / "must-not-prepare"
    with pytest.raises(UnreadyPopulation) as caught:
        prepare_run(
            manifest,
            directory,
            options=options(),
            prices=run_prices(),
            quality_profile=PROFILE_ID,
            schedule_context=context(intake, "Europe/London"),
            density_reviews=density_reviews(intake),
        )
    assert any(
        item["reason"] == "activity_date_or_interval_unresolved"
        and item["sources"][0]["pointer"] == "/itinerary/days/0/activities/2"
        for item in caught.value.report["diagnostics"]
    )
    assert not directory.exists()


def test_new_wire_selects_candidate_profile_in_normal_report_entry(route_case):
    case = route_case(change=declared_results)
    result = report(case, density_reviews=density_reviews(case[0].to_dict(), "ordinary"))
    assert result["status"] == "complete", result["diagnostics"]
    assert result["rules_profile_id"] == "rtpeval_declared_population_1"


def test_candidate_profile_keeps_overlap_failure_in_a_known_population(route_case):
    def overlap(results):
        declared_results(results)
        for result in results.values():
            result["itinerary"]["days"][0]["activities"][1]["start_time"] = "2020-01-01T09:30:00Z"

    case = route_case(change=overlap)
    result = report(case, density_reviews=density_reviews(case[0].to_dict(), "ordinary"))
    assert result["status"] == "complete", result["diagnostics"]
    for version in result["groups"][0]["versions"].values():
        assert version["dimensions"]["non_overlap"]["counts"]["FAIL"] == 2
        assert version["dimensions"]["routes"]["denominator"] == 1
        assert version["overall_total"]["score_0_100"] is not None


def test_normal_cli_freezes_candidate_inventory_before_any_execution(batch, capsys):
    import json

    from backend.evaluation.evaluation_run_cli import main
    from backend.evaluation.intake import load_batch
    from backend.tests.evaluation.test_evaluation_run import options, run_prices

    _, results, write, _, root = batch
    declared_results(results)
    for version in results:
        write(version)
    manifest = write()
    for name, value in (
        ("options", options()),
        ("prices", run_prices()),
        ("density", density_reviews(load_batch(manifest).to_dict(), "ordinary")),
    ):
        (root / (name + ".json")).write_text(json.dumps(value), encoding="utf-8")
    directory = root / "prepared"
    assert (
        main(
            [
                "prepare",
                str(manifest),
                "--directory",
                str(directory),
                "--options",
                str(root / "options.json"),
                "--prices",
                str(root / "prices.json"),
                "--density-reviews",
                str(root / "density.json"),
            ]
        )
        == 0
    )
    preparation = json.loads((directory / "preparation.json").read_bytes())
    assert preparation["quality_profile"] == "rtpeval_declared_population_1"
    assert preparation["population_readiness"]["status"] == "ready"
    assert len(preparation["population_readiness"]["rows"]) == 4
    assert not (directory / "execution").exists()
    capsys.readouterr()


def test_confirmed_same_place_exclusion_keeps_the_route_candidate_visible(route_case):
    def same_place(results):
        declared_results(results)
        for result in results.values():
            result["itinerary"]["days"][0]["activities"][1]["place_name"] = "Museum A"

    case = route_case(change=same_place)
    result = report(case, density_reviews=density_reviews(case[0].to_dict(), "ordinary"))
    assert result["status"] == "complete", result["diagnostics"]
    for version in result["groups"][0]["versions"].values():
        routes = version["primary_metrics"]["routes"]
        assert routes["candidate_count"] == 1
        assert routes["verified_na_count"] == 1
        assert version["dimensions"]["routes"]["denominator"] == 0
        assert len(version["candidate_inventory"]["routes"]) == 1


def test_wholly_na_group_does_not_receive_an_arbitrary_score(route_case):
    def empty(results):
        declared_results(results)
        for result in results.values():
            result["itinerary"]["days"][0]["activities"] = []
            result["itinerary"]["transfers"] = []

    case = route_case(change=empty)
    result = report(case, density_reviews=density_reviews(case[0].to_dict(), "ordinary"))
    assert result["status"] == "complete", result["diagnostics"]
    for version in result["groups"][0]["versions"].values():
        assert version["overall_total"]["score_0_100"] is None
        assert version["auxiliary_total"]["reason"] == "no_scorable_dimensions"
