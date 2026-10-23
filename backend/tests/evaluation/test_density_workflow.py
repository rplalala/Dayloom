"""Density rules survive actual paired CLI and downstream independent channels."""

import copy
import hashlib
import json

import pytest

from backend.evaluation.mechanism_preparation import read_batch_sources
from backend.evaluation.records import canonical_digest
from backend.evaluation.v3_pair_cli import main
from backend.tests.evaluation import test_quality_report as quality
from backend.tests.evaluation import test_route_cli as route_commands
from backend.tests.evaluation import test_v3_pair_report as pairs
from backend.tests.evaluation.test_daily_density import density_reviews

pytest_plugins = ("backend.tests.evaluation.test_intake",)
pair_case = pairs.pair_case
route_case = pairs.route_case
prepared_scenario = pairs.prepared_scenario


def add_third_visit(itinerary):
    visit = copy.deepcopy(itinerary["days"][0]["activities"][0])
    visit.update(
        activity_id="extra",
        title="Gallery C",
        place_name="Gallery C",
        start_time="2020-01-01T12:00:00Z",
        end_time="2020-01-01T13:00:00Z",
    )
    itinerary["days"][0]["activities"].append(visit)


@pytest.mark.parametrize(
    "profile, expected_penalty", [("ordinary", 10), ("relaxed", 40), ("rich", 0)]
)
def test_final_and_paired_reports_use_the_same_final_three_visit_cost(
    pair_case,
    route_case,
    profile,
    expected_penalty,
):
    def change(results):
        pairs.no_departure(results)
        for result in results.values():
            add_third_visit(result["itinerary"])

    final_case = route_case(change=change)
    final = quality.report(final_case, density_reviews=density_reviews(final_case[0], profile))
    assert final["status"] == "complete", final["diagnostics"]
    version = final["groups"][0]["versions"]["v3"]
    paired_case = pair_case(before=add_third_visit)
    paired = pairs.report(paired_case, density_reviews=density_reviews(paired_case[0], profile))
    assert paired["status"] == "complete", paired["diagnostics"]
    stages = paired["groups"][0]["stages"]
    for row in (version, *stages.values()):
        assert row["daily_density"]["rules_profile_id"] == "rtpeval_daily_density_3"
        assert row["daily_density"]["mean_penalty_0_100"] == expected_penalty
        assert row["daily_density"]["days"][0]["known_primary_count"] == 3
        assert row["auxiliary_total"]["score_0_100"] == 37.5
        assert (
            row["overall_total"]["score_0_100"]
            == {
                "ordinary": 27.5,
                "relaxed": 0,
                "rich": 37.5,
            }[profile]
        )
    assert paired["groups"][0]["deltas"]["overall_total"]["percentage_points"] == 0


@pytest.mark.parametrize(
    "profile_id, expected_penalty",
    [(None, 10), ("rtpeval_daily_density_2", 0)],
)
def test_final_and_pair_select_versioned_rich_rules_without_rewriting_evidence(
    pair_case, route_case, profile_id, expected_penalty
):
    final_case = route_case(change=pairs.no_departure)
    paired_case = pair_case()
    reports = []
    originals = {
        path: path.read_bytes()
        for case in (final_case, paired_case)
        for path in case[2].parent.rglob("*")
        if path.is_file()
    }
    for case, build in ((final_case, quality.report), (paired_case, pairs.report)):
        reviews = density_reviews(case[0], "rich")
        if profile_id is not None:
            reviews["rules_profile_id"] = profile_id
        result = build(case, density_reviews=reviews)
        assert result["status"] == "complete", result["diagnostics"]
        rules = result["rules_profile"]["daily_density"]
        assert rules["profile_id"] == (profile_id or "rtpeval_daily_density_3")
        assert rules["penalties_by_count_0_to_5"]["rich"][2] == expected_penalty
        reports.append(result)
    rows = [
        reports[0]["groups"][0]["versions"]["v3"],
        *reports[1]["groups"][0]["stages"].values(),
    ]
    for row in rows:
        assert row["daily_density"]["mean_penalty_0_100"] == expected_penalty
        assert row["daily_density"]["rules_profile_id"] == (profile_id or "rtpeval_daily_density_3")
        assert row["auxiliary_total"]["score_0_100"] == 50
        assert row["overall_total"]["score_0_100"] == 50 - expected_penalty
    assert all(path.read_bytes() == original for path, original in originals.items())


def test_paired_cli_density_policy_preserves_provenance_and_read_only_sources(pair_case, capsys):
    case = pair_case()
    root = case[2].parent
    path = root / "density.json"
    path.write_text(json.dumps(density_reviews(case[0], exact_count=1)), encoding="utf-8")
    args = ["report", *route_commands.arguments(case)[1:], "--density-reviews", str(path)]
    originals = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    assert main(args) == 0
    out = json.loads(capsys.readouterr().out)
    assert (
        out["preparation_file_sha256"]["density_reviews"]
        == hashlib.sha256(path.read_bytes()).hexdigest()
    )
    pair = out["groups"][0]
    assert pair["stages"]["draft"]["daily_density"]["days"][0]["known_primary_count"] == 2
    assert pair["stages"]["draft"]["overall_total"]["score_0_100"] == 0
    assert pair["deltas"]["overall_total"]["percentage_points"] == 0
    assert {p: p.read_bytes() for p in root.rglob("*") if p.is_file()} == originals


def test_new_pair_report_can_be_linked_into_independent_mechanism_channel(pair_case, batch):
    case = pair_case()
    out = pairs.report(case, density_reviews=density_reviews(case[0]))
    prepared = case[0].to_dict()
    group = prepared["inventory"][0]
    context = group["runs"]["v3"]["final"]["context"]
    observation = {
        "group_id": group["group_id"],
        "run_id": context["run_id"],
        "version": "v3",
        "input_sha256": group["input_sha256"],
        "result_sha256": context["artifact_sha256"],
        "channel": "independent",
        "content": out,
        "content_sha256": canonical_digest(out),
    }
    mechanism = read_batch_sources(batch[4] / "manifest.json", observations=[observation]).to_dict()
    v3 = next(run for run in mechanism["runs"] if run["version"] == "v3")
    assert v3["channels"]["independent"]["status"] == "available"
