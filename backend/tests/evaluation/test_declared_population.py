"""Synthetic checks for the separately versioned finite-candidate scoring policy."""

from backend.evaluation.quality_report import build_quality_report
from backend.tests.evaluation import test_routes as route_tests
from backend.tests.evaluation.test_daily_density import density_reviews
from backend.tests.evaluation.test_quality_report import report

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
