"""Source-linked daily pace policy and exact deductions for independent reports."""

from fractions import Fraction

from backend.pace_policy import PENALTIES, PENALTY_PROFILES, PROFILE_ID, daily_penalty

from ._schedule_preparation import _days, _sources
from .preparation import _review_provenance
from .quality_aggregation import _fraction
from .records import require, text

RULES = {
    "profile_id": PROFILE_ID,
    "penalties_by_count_0_to_5": PENALTIES,
    "count_6_or_more": 100,
    "explicit_count": "matching reviewed exact count exempts defaults; mismatch deducts 100",
    "population": "source-distinct primary visit occurrences on every requested date",
    "mean": "equal requested-date weight; exact arithmetic; empty dates included",
    "overall": "max(0, five-dimensional auxiliary score minus mean daily penalty)",
    "unknown": "no guessed count or pace; bounds retained; unresolved deduction is unavailable",
}


def density_rules(reviews=None):
    """Select numeric rules separately from the reviewed request semantics."""
    profile = (
        reviews.get("rules_profile_id", PROFILE_ID) if isinstance(reviews, dict) else PROFILE_ID
    )
    require(
        isinstance(profile, str) and profile in PENALTY_PROFILES,
        "density_reviews/rules_profile_id",
        "Unsupported daily density rules profile",
    )
    return {**RULES, "profile_id": profile, "penalties_by_count_0_to_5": PENALTY_PROFILES[profile]}


def _policy(value, group, pointer):
    require(
        isinstance(value, dict)
        and set(value) == {"profile", "exact_count", "source_refs"}
        and value["profile"] in (*PENALTIES, "unresolved")
        and (
            value["exact_count"] is None
            or type(value["exact_count"]) is int
            and value["exact_count"] >= 0
        ),
        pointer,
        "Expected reviewed pace and optional nonnegative exact daily count",
    )
    _sources(value["source_refs"], group["input"], pointer)
    require(
        all(text(ref.get("quote")) for ref in value["source_refs"]),
        pointer,
        "Daily density semantics require quoted original input",
    )
    return value


def prepare_density_policies(intake, reviews=None):
    """Validate independent request policies; never use planner interpretations."""
    profile_id = density_rules(reviews)["profile_id"]
    groups = {group["group_id"]: group for group in intake["inventory"]}
    policies = {}
    if reviews is not None:
        require(
            isinstance(reviews, dict)
            and reviews.get("schema_version") == "rtpeval_density_reviews_1"
            and reviews.get("batch_id") == intake["batch_id"]
            and reviews.get("batch_revision") == intake["revision"]
            and isinstance(reviews.get("groups"), list),
            "density_reviews",
            "Invalid or stale density review envelope",
        )
        for record in reviews["groups"]:
            require(isinstance(record, dict), "density_reviews", "Expected review object")
            gid = record.get("group_id")
            require(
                text(gid)
                and gid in groups
                and gid not in policies
                and record.get("input_sha256") == groups[gid]["input_sha256"],
                "density_reviews",
                "Foreign, duplicate or stale reviewed group",
            )
            _review_provenance(record, gid)
            require(
                record.get("review_origin") in ("human", "agent")
                and text(record.get("rationale"))
                and isinstance(record.get("days"), list),
                gid,
                "Independent review origin, rationale and dated overrides required",
            )
            group = groups[gid]
            default = _policy(record.get("default"), group, gid + "/default")
            overrides = {}
            for item in record["days"]:
                require(isinstance(item, dict), gid, "Invalid dated policy")
                day = item.get("date")
                require(
                    text(day) and day in _days(group["input"]) and day not in overrides,
                    gid,
                    "Foreign or duplicate policy date",
                )
                overrides[day] = _policy(
                    {key: value for key, value in item.items() if key != "date"}, group, day
                )
            policies[gid] = {
                "default": default,
                "days": overrides,
                "review": {
                    key: record[key]
                    for key in (
                        "reviewer_ref",
                        "reviewed_at",
                        "review_origin",
                        "rationale",
                    )
                },
            }
    for gid, group in groups.items():
        if gid not in policies:
            # Free text may contain date-specific pace or count constraints. Absence
            # of a reviewed policy is never an assertion that no such request exists.
            preferences = group["input"].get("additional_preferences")
            policies[gid] = {
                "default": None
                if preferences
                else {
                    "profile": "ordinary",
                    "exact_count": None,
                    "source_refs": [],
                },
                "days": {},
                "review": None,
            }
    return {gid: {**policy, "rules_profile_id": profile_id} for gid, policy in policies.items()}


def _penalty(count, policy, rules_profile_id):
    return daily_penalty(
        count, policy["profile"], policy["exact_count"], rules_profile_id=rules_profile_id
    )


def score_daily_density(group, density, policy):
    """Score a requested-date population, retaining nonmonotonic uncertainty bounds."""
    rules_profile_id = density_rules(policy)["profile_id"]
    dates = _days(group["input"])
    require(
        isinstance(density, list)
        and len(density) == len(dates)
        and {item["date"] for item in density} == set(dates),
        "density",
        "Exactly one density measurement per requested date required",
    )
    rows = []
    for item in sorted(density, key=lambda item: item["date"]):
        lower, possible = item["known_primary_count"], item["possible_primary_count"]
        require(
            type(lower) is int and lower >= 0 and type(possible) is int and possible >= 0,
            "density",
            "Expected nonnegative known and possible visit counts",
        )
        upper = lower + possible
        adopted = policy["days"].get(item["date"], policy["default"])
        if adopted is None or adopted["profile"] == "unresolved" and adopted["exact_count"] is None:
            bounds = (0, 100)
            reason = "density_policy_unresolved"
        else:
            # Counts >=6 have identical default cost; exact requested counts may
            # be arbitrarily large and are checked without expanding that range.
            if adopted["exact_count"] is not None:
                target = adopted["exact_count"]
                bounds = (
                    (0, 0)
                    if lower == upper == target
                    else ((0, 100) if lower <= target <= upper else (100, 100))
                )
                reason = "explicit_count_match" if bounds == (0, 0) else "explicit_count_mismatch"
            else:
                candidates = [
                    _penalty(n, adopted, rules_profile_id)
                    for n in range(min(lower, 6), min(upper, 6) + 1)
                ]
                bounds = min(candidates), max(candidates)
                reason = "default_pace_penalty"
        penalty = bounds[0] if bounds[0] == bounds[1] else None
        rows.append(
            {
                "date": item["date"],
                "known_primary_count": lower,
                "possible_primary_count": possible,
                "count_bounds": {"lower": lower, "upper": upper},
                "policy": adopted,
                "penalty_0_100": penalty,
                "penalty_bounds": {"lower": bounds[0], "upper": bounds[1]},
                "state": "UNKNOWN" if penalty is None else "PASS" if penalty == 0 else "FAIL",
                "reason": "count_unresolved"
                if penalty is None and reason != "density_policy_unresolved"
                else reason,
            }
        )
    mean = (
        sum(Fraction(row["penalty_0_100"]) for row in rows) / len(rows)
        if all(row["penalty_0_100"] is not None for row in rows)
        else None
    )
    return {
        "rules_profile_id": rules_profile_id,
        "requested_day_count": len(rows),
        "days": rows,
        "review": policy["review"],
        "mean_penalty_0_100": float(mean) if mean is not None else None,
        "exact_mean_penalty": _fraction(mean) if mean is not None else None,
        "mean_penalty_bounds": {
            key: float(sum(Fraction(row["penalty_bounds"][key]) for row in rows) / len(rows))
            for key in ("lower", "upper")
        },
    }


def apply_density_penalty(version):
    """Add the overall score while preserving the original five-dimensional score."""
    baseline = version["auxiliary_total"]
    penalty = version["daily_density"]["exact_mean_penalty"]
    exact = baseline["exact_fraction"]
    total = (
        max(
            Fraction(0),
            Fraction(exact["numerator"], exact["denominator"])
            - Fraction(penalty["numerator"], penalty["denominator"]) / 100,
        )
        if exact is not None and penalty is not None
        else None
    )
    version["overall_total"] = {
        "score_0_100": float(total * 100) if total is not None else None,
        "exact_fraction": _fraction(total) if total is not None else None,
        "reason": baseline["reason"]
        if exact is None
        else "density_penalty_unresolved"
        if penalty is None
        else None,
    }
