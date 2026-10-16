"""Finite source-linked populations, separate from factual scoring and review coverage."""

from backend.activity_semantics import read_activity_claim

from ._schedule_preparation import _days, _occupancy_reviews, _validate_spec
from .daily_density import prepare_density_policies
from .occupancy import prepare_occupancy
from .preparation import schedule_timezones
from .records import canonical_digest, require
from .schedule_time import normalize_interval

PROFILE_ID = "rtpeval_declared_population_1"


class UnreadyPopulation(ValueError):
    def __init__(self, report):
        super().__init__("Numerical scoring population requires resolution before acquisition")
        self.report = report


def select_profile(intake, profile=None):
    """New-wire batches select the new policy; historical defaults stay unchanged."""
    require(profile in (None, PROFILE_ID), "quality_profile", "Unsupported quality profile")
    if profile is None and any(
        run["final"].get("wire_version") == "itinerary_3"
        for group in intake["inventory"]
        for run in group["runs"].values()
    ):
        return PROFILE_ID
    return profile


def population_readiness(
    intake, schedule_context=None, occupancy_reviews=None, density_reviews=None
):
    """Inventory membership before acquisition, with no providers or scorer execution."""
    zones = schedule_timezones(intake, schedule_context)
    reviews = _occupancy_reviews(intake, occupancy_reviews)
    density = prepare_density_policies(intake, density_reviews)
    rows, diagnostics = [], []

    def pending(group, version, reason, sources=()):
        diagnostics.append(
            {
                "group_id": group["group_id"],
                "version": version,
                "reason": reason,
                "sources": list(sources),
            }
        )

    for group in intake["inventory"]:
        incomplete = _validate_spec(group)
        obligations = group["requirement_spec"]["obligations"]
        for day in _days(group["input"]):
            policy = density[group["group_id"]]
            adopted = policy["days"].get(day, policy["default"])
            if (
                adopted is None
                or adopted["profile"] == "unresolved"
                and adopted["exact_count"] is None
            ):
                pending(group, None, "density_policy_unresolved")
        if incomplete or any(o["resolution"] != "resolved" for o in obligations):
            pending(group, None, "executable_obligation_population_unresolved")
        for version, run in group["runs"].items():
            projection = run["final"]
            occupancy = prepare_occupancy(
                projection, obligations, zones.get(group["group_id"]), reviews
            )
            inventory = {
                name: []
                for name in ("requirements", "grounding", "non_overlap", "opening", "routes")
            }
            claims = []
            for activity in projection["activities"]:
                role, raw = activity["evaluation_role"], activity["original"]
                claim = read_activity_claim(raw, projection["wire_version"])
                claims.append(
                    {
                        "source": activity["source"],
                        "kind": claim.kind,
                        "time_use": claim.time_use,
                        "provenance": claim.provenance,
                        "role_review": activity.get("review"),
                    }
                )
                if role == "unresolved":
                    pending(group, version, "role_population_unresolved", [activity["source"]])
                interval = normalize_interval(
                    raw.get("start_time"),
                    raw.get("end_time"),
                    activity["declared_day"],
                    zones.get(group["group_id"]),
                )
                if interval.span is None or activity["declared_day"] not in _days(group["input"]):
                    pending(
                        group, version, "activity_date_or_interval_unresolved", [activity["source"]]
                    )
                if role == "primary_visit":
                    for name in ("grounding", "opening"):
                        inventory[name].append(
                            {
                                "candidate_id": activity["source"]["record_id"],
                                "sources": [activity["source"]],
                            }
                        )
            if occupancy.candidates:
                pending(group, version, "occupancy_population_unresolved")
            if projection["unbound_transport"] or any(
                len(leg["claims"]) > 1 for leg in projection["legs"]
            ):
                pending(group, version, "selected_journey_association_unresolved")
            if any(leg["adjacency_status"] == "unresolved" for leg in projection["legs"]):
                pending(group, version, "legacy_adjacency_population_unresolved")
            for obligation in obligations:
                inventory["requirements"].append(
                    {
                        "candidate_id": obligation["obligation_id"],
                        "sources": obligation["source_refs"],
                    }
                )
            for unit in occupancy.to_dict()["commitments"]:
                inventory["non_overlap"].append(
                    {"candidate_id": unit["commitment_id"], "sources": unit["sources"]}
                )
            for leg in projection["legs"]:
                inventory["routes"].append(
                    {
                        "candidate_id": canonical_digest(
                            [leg["from_source"]["record_id"], leg["to_source"]["record_id"]]
                        ),
                        "sources": [leg["from_source"], leg["to_source"]],
                    }
                )
            rows.append(
                {
                    "group_id": group["group_id"],
                    "version": version,
                    "result_sha256": projection["context"].get("artifact_sha256"),
                    "inventory": inventory,
                    "activity_claims": claims,
                }
            )
    result = {
        "schema_version": "rtpeval_population_readiness_1",
        "profile_id": PROFILE_ID,
        "status": "needs_population_resolution" if diagnostics else "ready",
        "batch_id": intake["batch_id"],
        "revision": intake["revision"],
        "source_hashes": intake.get("source_hashes", {}),
        "rows": rows,
        "diagnostics": diagnostics,
        "provider_calls": 0,
        "review_hashes": {
            name: canonical_digest(value) if value is not None else None
            for name, value in (
                ("schedule_context", schedule_context),
                ("occupancy_reviews", occupancy_reviews),
                ("density_reviews", density_reviews),
            )
        },
    }
    result["content_sha256"] = canonical_digest(result)
    return result


def candidate_metrics(metrics, inventory):
    """Adopt outcomes onto the previously frozen inventory, never delete uncertainty."""
    adopted = {}
    for name, raw in metrics.items():
        checks = raw["checks"]
        keys = []
        for check in checks:
            if name == "requirements":
                key = check["obligation_id"]
            elif name == "non_overlap":
                key = check["commitment_id"]
            elif name == "routes":
                key = canonical_digest(
                    [check["from_source"]["record_id"], check["to_source"]["record_id"]]
                )
            else:
                key = check["source"]["record_id"]
            keys.append(key)
            require(
                check["state"] != "N/A" or bool(check.get("reason")),
                name,
                "Verified N/A requires an explicit reason",
            )
        expected = [c["candidate_id"] for c in inventory[name]]
        require(
            len(keys) == len(set(keys)) and set(keys) == set(expected),
            name,
            "Scored checks must exactly cover the frozen candidate population",
        )
        counts = {
            state: sum(c["state"] == state for c in checks)
            for state in ("PASS", "FAIL", "UNKNOWN", "N/A")
        }
        size = len(expected) - counts["N/A"]
        adopted[name] = {
            **raw,
            "counts": counts,
            "candidate_count": len(expected),
            "verified_na_count": counts["N/A"],
            "population_policy": PROFILE_ID,
            "denominator": size,
            "applicable_denominator": size,
            "denominator_unresolved": False,
        }
    return adopted
