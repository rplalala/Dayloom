"""Daily pace penalties through the independent policy/scoring boundary."""

import copy

import pytest

from backend.evaluation.daily_density import prepare_density_policies, score_daily_density
from backend.evaluation.records import MaterialError


def density_reviews(intake, profile="ordinary", *, exact_count=None, days=()):
    """Source-linked synthetic review for real intake/report/CLI test cases."""
    prepared = intake.to_dict() if hasattr(intake, "to_dict") else intake
    return {
        "schema_version": "rtpeval_density_reviews_1",
        "batch_id": prepared["batch_id"],
        "batch_revision": prepared["revision"],
        "groups": [
            {
                "group_id": group["group_id"],
                "input_sha256": group["input_sha256"],
                "reviewer_ref": "independent-reviewer",
                "reviewed_at": "2026-10-04T00:00:00Z",
                "review_origin": "agent",
                "rationale": "Synthetic independent policy fixture.",
                "default": {
                    "profile": profile,
                    "exact_count": exact_count,
                    "source_refs": [
                        {
                            "field_path": "additional_preferences",
                            "quote": group["input"]["additional_preferences"],
                        }
                    ],
                },
                "days": list(days),
            }
            for group in prepared["inventory"]
        ],
    }


def scenario(profile="ordinary", *, counts=(1, 4, 5), overrides=()):
    original = {
        "start_date": "2026-10-07",
        "end_date": "2026-10-09",
        "additional_preferences": "Independently reviewed pace and daily counts.",
    }
    group = {"group_id": "g", "input_sha256": "a" * 64, "input": original}
    intake = {"batch_id": "batch", "revision": "1", "inventory": [group]}
    sources = [
        {"field_path": "additional_preferences", "quote": original["additional_preferences"]}
    ]
    reviews = {
        "schema_version": "rtpeval_density_reviews_1",
        "batch_id": "batch",
        "batch_revision": "1",
        "groups": [
            {
                "group_id": "g",
                "input_sha256": group["input_sha256"],
                "reviewer_ref": "independent-agent",
                "reviewed_at": "2026-10-04T00:00:00Z",
                "review_origin": "agent",
                "rationale": "Test-only reviewed policy.",
                "default": {"profile": profile, "exact_count": None, "source_refs": sources},
                "days": [{**item, "source_refs": sources} for item in overrides],
            }
        ],
    }
    density = [
        {"date": f"2026-10-{7 + i:02}", "known_primary_count": n, "possible_primary_count": 0}
        for i, n in enumerate(counts)
    ]
    return intake, group, reviews, density


def test_ordinary_sparse_and_busy_days_reduce_the_score_in_requested_order():
    intake, group, reviews, density = scenario()
    policies = prepare_density_policies(intake, reviews)
    result = score_daily_density(group, density, policies["g"])
    assert [day["penalty_0_100"] for day in result["days"]] == [40, 50, 80]
    assert result["exact_mean_penalty"] == {"numerator": 170, "denominator": 3}
    assert result["requested_day_count"] == 3


@pytest.mark.parametrize(
    "profile, expected",
    [
        ("ordinary", [100, 40, 0, 10, 50, 80, 100, 100]),
        ("relaxed", [100, 20, 0, 40, 70, 90, 100, 100]),
        ("rich", [100, 60, 10, 0, 30, 70, 100, 100]),
    ],
)
def test_all_pace_windows_and_out_of_window_counts(profile, expected):
    for count, penalty in enumerate(expected):
        intake, group, reviews, density = scenario(profile, counts=(count,) * 3)
        result = score_daily_density(group, density, prepare_density_policies(intake, reviews)["g"])
        assert [row["penalty_0_100"] for row in result["days"]] == [penalty] * 3
        assert result["mean_penalty_0_100"] == penalty


@pytest.mark.parametrize("count", [4, 5])
def test_busy_day_cost_orders_rich_before_ordinary_before_relaxed(count):
    penalties = {}
    for profile in ("ordinary", "relaxed", "rich"):
        intake, group, reviews, density = scenario(profile, counts=(count,) * 3)
        result = score_daily_density(group, density, prepare_density_policies(intake, reviews)["g"])
        penalties[profile] = result["mean_penalty_0_100"]
    assert penalties["rich"] < penalties["ordinary"] < penalties["relaxed"]


@pytest.mark.parametrize(
    "profile, exact_mean",
    [
        ("ordinary", {"numerator": 140, "denominator": 3}),
        ("relaxed", {"numerator": 200, "denominator": 3}),
        ("rich", {"numerator": 100, "denominator": 3}),
    ],
)
def test_mixed_busy_days_keep_exact_mean_under_the_final_table(profile, exact_mean):
    intake, group, reviews, density = scenario(profile, counts=(3, 4, 5))
    result = score_daily_density(group, density, prepare_density_policies(intake, reviews)["g"])
    assert result["exact_mean_penalty"] == exact_mean


@pytest.mark.parametrize("count", [0, 1, 3, 4, 5, 6, 1000000])
def test_explicit_matching_count_exempts_only_its_requested_date(count):
    intake, group, reviews, density = scenario(
        "relaxed",
        counts=(count, 1, 1),
        overrides=[
            {
                "date": "2026-10-07",
                "profile": "relaxed",
                "exact_count": count,
            }
        ],
    )
    result = score_daily_density(group, density, prepare_density_policies(intake, reviews)["g"])
    assert [row["penalty_0_100"] for row in result["days"]] == [0, 20, 20]


def test_conflicting_explicit_count_is_not_a_blanket_exemption():
    intake, group, reviews, density = scenario(counts=(2, 4, 6))
    reviews["groups"][0]["default"]["exact_count"] = 4
    result = score_daily_density(group, density, prepare_density_policies(intake, reviews)["g"])
    assert [row["penalty_0_100"] for row in result["days"]] == [100, 0, 100]
    assert result["days"][0]["reason"] == "explicit_count_mismatch"


def test_date_pace_override_takes_precedence_over_trip_pace():
    intake, group, reviews, density = scenario(
        "ordinary",
        counts=(3, 3, 3),
        overrides=[
            {
                "date": "2026-10-08",
                "profile": "relaxed",
                "exact_count": None,
            }
        ],
    )
    result = score_daily_density(group, density, prepare_density_policies(intake, reviews)["g"])
    assert [row["penalty_0_100"] for row in result["days"]] == [10, 40, 10]


def test_possible_counts_preserve_nonmonotonic_penalty_bounds():
    intake, group, reviews, density = scenario(counts=(1, 2, 6))
    density[0]["possible_primary_count"] = 4
    density[1]["possible_primary_count"] = 1
    density[2]["possible_primary_count"] = 1000000
    result = score_daily_density(group, density, prepare_density_policies(intake, reviews)["g"])
    assert result["days"][0]["penalty_bounds"] == {"lower": 0, "upper": 80}
    assert result["days"][0]["penalty_0_100"] is None
    assert result["days"][1]["penalty_0_100"] is None
    assert result["days"][1]["penalty_bounds"] == {"lower": 0, "upper": 10}
    assert result["days"][2]["penalty_0_100"] == 100
    assert result["mean_penalty_0_100"] is None


def test_missing_pace_review_is_unknown_unless_request_has_no_preferences():
    intake, group, _, density = scenario(counts=(1, 1, 1))
    result = score_daily_density(group, density, prepare_density_policies(intake)["g"])
    assert result["mean_penalty_0_100"] is None
    assert result["days"][0]["reason"] == "density_policy_unresolved"
    group["input"].pop("additional_preferences")
    ordinary = score_daily_density(group, density, prepare_density_policies(intake)["g"])
    assert ordinary["mean_penalty_0_100"] == 40


def test_rich_two_and_three_days_have_five_point_mean_and_uncertain_count_stays_unavailable():
    intake, group, reviews, density = scenario("rich", counts=(2, 3))
    group["input"]["end_date"] = "2026-10-08"
    policy = prepare_density_policies(intake, reviews)["g"]
    result = score_daily_density(group, density, policy)
    assert result["exact_mean_penalty"] == {"numerator": 5, "denominator": 1}
    density[0]["possible_primary_count"] = 1
    uncertain = score_daily_density(group, density, policy)
    assert uncertain["days"][0]["penalty_bounds"] == {"lower": 0, "upper": 10}
    assert uncertain["mean_penalty_0_100"] is None


def test_unknown_numeric_policy_is_not_silently_scored_with_current_rules():
    intake, _, reviews, _ = scenario("rich")
    reviews["rules_profile_id"] = "unrecognized"
    with pytest.raises(MaterialError, match="Unsupported daily density rules profile"):
        prepare_density_policies(intake, reviews)


@pytest.mark.parametrize("fault", ["input", "batch", "duplicate", "date", "quote", "origin"])
def test_stale_or_unsupported_policy_is_material_error(fault):
    intake, _, reviews, _ = scenario()
    record = reviews["groups"][0]
    if fault == "input":
        record["input_sha256"] = "b" * 64
    elif fault == "batch":
        reviews["batch_revision"] = "stale"
    elif fault == "duplicate":
        reviews["groups"].append(copy.deepcopy(record))
    elif fault == "date":
        record["days"] = [{"date": "2099-01-01", **record["default"]}]
    elif fault == "quote":
        record["default"]["source_refs"][0]["quote"] = "not in the original request"
    else:
        record["review_origin"] = "planner"
    with pytest.raises(MaterialError):
        prepare_density_policies(intake, reviews)
