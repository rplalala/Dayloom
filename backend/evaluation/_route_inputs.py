"""Reviewed Input mode policy and independently sourced coordinate preparation."""

import math
import re

from ._route_rules import DEFAULT_OPTIONS
from ._schedule_preparation import _days, _sources
from .place_association import associated_place_id
from .preparation import _review_provenance
from .records import require, text

MODES = {"WALK", "TRANSIT", "DRIVE"}


def route_reviews(intake, envelope):
    if envelope is None:
        return {}
    require(
        isinstance(envelope, dict)
        and set(envelope) == {"schema_version", "batch_id", "revision", "groups"}
        and envelope["schema_version"] == "rtpeval_route_reviews_1"
        and envelope["batch_id"] == intake["batch_id"]
        and text(envelope["revision"])
        and isinstance(envelope["groups"], list),
        "route_reviews",
        "Invalid route review envelope",
    )
    groups = {g["group_id"]: g for g in intake["inventory"]}
    result = {}
    for record in envelope["groups"]:
        require(
            isinstance(record, dict)
            and set(record)
            <= {
                "group_id",
                "input_sha256",
                "reviewer_ref",
                "reviewed_at",
                "status",
                "policies",
                "reason",
                "source_refs",
                "stated_mode",
            },
            "route_reviews",
            "Unsupported route review fields",
        )
        gid = record.get("group_id")
        require(
            text(gid)
            and gid in groups
            and gid not in result
            and record.get("input_sha256") == groups[gid]["input_sha256"],
            "route_reviews",
            "Stale or duplicate Input review",
        )
        _review_provenance(record, gid)
        original = groups[gid]["input"]
        status = record.get("status")
        require(
            status in ("unrestricted", "restricted", "unresolved"), gid, "Invalid policy status"
        )
        policies = record.get("policies", [])
        require(
            isinstance(policies, list)
            and (bool(policies) if status == "restricted" else not policies),
            gid,
            "Restriction records contradict review status",
        )
        if status == "unresolved":
            require(text(record.get("reason")), gid, "Unresolved policy requires reason")
        if "source_refs" in record:
            _sources(record["source_refs"], original, gid)
        ids = set()
        days = _days(original)
        for policy in policies:
            require(
                isinstance(policy, dict)
                and set(policy)
                <= {
                    "policy_id",
                    "scope",
                    "dates",
                    "allowed_modes",
                    "source_refs",
                }
                and text(policy.get("policy_id"))
                and policy["policy_id"] not in ids,
                gid,
                "Invalid or duplicate policy",
            )
            ids.add(policy["policy_id"])
            _sources(policy.get("source_refs"), original, gid)
            allowed = policy.get("allowed_modes")
            require(
                isinstance(allowed, list)
                and bool(allowed)
                and all(isinstance(m, str) and m in MODES for m in allowed)
                and len(set(allowed)) == len(allowed),
                gid,
                "Invalid allowed mode set",
            )
            require(
                policy.get("scope") in ("whole_trip", "specified_dates"), gid, "Invalid mode scope"
            )
            dates = policy.get("dates", [])
            require(
                isinstance(dates, list)
                and all(isinstance(d, str) and d in days for d in dates)
                and len(set(dates)) == len(dates)
                and (bool(dates) if policy["scope"] == "specified_dates" else not dates),
                gid,
                "Invalid mode restriction dates",
            )
        for day in days:
            sets = [
                set(p["allowed_modes"])
                for p in policies
                if p["scope"] == "whole_trip" or day in p["dates"]
            ]
            require(
                not sets or bool(set.intersection(*sets)), gid, "Contradictory mode constraints"
            )
        stated = record.get("stated_mode")
        if stated is not None:
            require(
                isinstance(stated, dict)
                and set(stated) == {"mode", "source_refs"}
                and isinstance(stated["mode"], str)
                and stated["mode"] in MODES,
                gid,
                "Invalid explicitly stated Input mode",
            )
            _sources(stated["source_refs"], original, gid)
        result[gid] = record
    return result


def requirement_mode_review(group, review):
    """Bridge independently reviewed executable obligations into the existing route policy."""
    obligations = [
        o
        for o in group["requirement_spec"]["obligations"]
        if o["kind"] == "transport_modes" and o["resolution"] == "resolved"
    ]
    if not obligations:
        return review
    policies = list((review or {}).get("policies", []))
    additional = []

    def source_keys(item):
        return {
            (s["field_path"], s.get("quote"), s.get("occurrence", 0)) for s in item["source_refs"]
        }

    def intervals(item):
        result = []
        for ref in item["source_refs"]:
            if "quote" not in ref:
                return []
            original = group["input"][ref["field_path"]]
            start, offset = -1, 0
            for _ in range(ref.get("occurrence", 0) + 1):
                start = original.index(ref["quote"], offset)
                offset = start + len(ref["quote"])
            result.append((ref["field_path"], start, offset))
        return result

    def same_source_region(left, right):
        a, b = intervals(left), intervals(right)

        def covers(first, second):
            return all(
                any(f == g and (s <= u < v <= e or u <= s < e <= v) for g, u, v in second)
                for f, s, e in first
            )

        return bool(a and b) and covers(a, b) and covers(b, a)

    for policy in policies:
        shared = [o for o in obligations if source_keys(o) == source_keys(policy)]
        if shared:
            require(
                all(
                    policy["scope"] == "whole_trip"
                    and set(policy["allowed_modes"]) == set(o["allowed_modes"])
                    for o in shared
                ),
                group["group_id"],
                "Inconsistent source-bound transport interpretations",
            )
        elif not any(
            policy["scope"] == o["scope"]
            and set(policy["allowed_modes"]) == set(o["allowed_modes"])
            and same_source_region(policy, o)
            for o in obligations
        ):
            additional.append(policy)
    scoring_review = {
        **(review or {}),
        "policies": additional,
        "status": "unresolved"
        if review and review["status"] == "unresolved"
        else "restricted"
        if additional
        else "unrestricted",
    }
    policies.extend(
        {
            "policy_id": "requirement:" + o["obligation_id"],
            "scope": "whole_trip",
            "allowed_modes": o["allowed_modes"],
            "source_refs": o["source_refs"],
        }
        for o in obligations
    )
    for day in _days(group["input"]):
        sets = [
            set(p["allowed_modes"])
            for p in policies
            if p["scope"] == "whole_trip" or day in p.get("dates", [])
        ]
        require(
            bool(set.intersection(*sets)), group["group_id"], "Contradictory transport restrictions"
        )
    return {
        **(review or {}),
        "status": "restricted",
        "policies": policies,
        "unresolved_policy": review is not None and review["status"] == "unresolved",
        "scoring_review": scoring_review,
    }


def policy_component(review, mode, day):
    if review is None or review["status"] == "unresolved":
        return {"state": "UNKNOWN", "reason": "request_mode_policy_unavailable"}
    policies = [
        p for p in review.get("policies", []) if p["scope"] == "whole_trip" or day in p["dates"]
    ]
    if mode is None:
        return {"state": "UNKNOWN", "reason": "route_mode_unresolved", "policies": policies}
    failed = any(mode not in p["allowed_modes"] for p in policies)
    return {
        "state": "FAIL" if failed else "UNKNOWN" if review.get("unresolved_policy") else "PASS",
        "policies": policies,
        "reason": "claimed_mode_disallowed" if failed else None,
    }


def coordinates(intake, identity, envelope):
    if envelope is None:
        return {}, DEFAULT_OPTIONS
    require(
        isinstance(envelope, dict)
        and set(envelope)
        <= {
            "schema_version",
            "batch_id",
            "revision",
            "records",
            "mode_options",
        }
        and envelope.get("schema_version") == "rtpeval_route_coordinates_1"
        and envelope.get("batch_id") == intake["batch_id"]
        and text(envelope.get("revision"))
        and isinstance(envelope.get("records"), list),
        "coordinates",
        "Invalid coordinate envelope",
    )
    ids = {pid for r in identity["records"] if (pid := associated_place_id(r)) is not None}
    points = {}
    for point in envelope["records"]:
        require(
            isinstance(point, dict)
            and set(point)
            == {
                "place_id",
                "latitude",
                "longitude",
                "evidence_sha256",
                "source_ref",
                "reviewer_ref",
                "reviewed_at",
            },
            "coordinates",
            "Explicit independent coordinate record required",
        )
        pid = point["place_id"]
        require(
            text(pid) and pid in ids and pid not in points,
            "coordinates",
            "Foreign or duplicate canonical coordinate",
        )
        require(
            text(point["source_ref"])
            and isinstance(point["evidence_sha256"], str)
            and re.fullmatch(r"[0-9a-f]{64}", point["evidence_sha256"]),
            pid,
            "Invalid coordinate provenance",
        )
        _review_provenance(point, pid)
        for field, limit in (("latitude", 90), ("longitude", 180)):
            number = point[field]
            require(
                type(number) in (int, float) and math.isfinite(number) and abs(number) <= limit,
                pid,
                "Invalid coordinate",
            )
        points[pid] = {
            k: point[k] for k in ("place_id", "latitude", "longitude", "evidence_sha256")
        }
    options = envelope.get("mode_options", {})
    require(
        isinstance(options, dict) and set(options) <= MODES,
        "coordinates",
        "Unsupported mode option keys",
    )
    for option in options.values():
        require(
            isinstance(option, dict)
            and set(option) == {"time_basis", "routing_options"}
            and option["time_basis"] in ("time_independent", "explicit_departure")
            and isinstance(option["routing_options"], dict),
            "coordinates",
            "Invalid query option record",
        )
    return points, {**DEFAULT_OPTIONS, **options}


def route_context(leg, points, options):
    mode = leg["mode"]
    origin, destination = leg["canonical_endpoints"]
    if (
        mode is None
        or origin not in points
        or destination not in points
        or leg["applicability"] == "N/A"
        or "adjacency_unresolved" in leg["reasons"]
    ):
        return None
    option = options[mode]
    if option["time_basis"] == "explicit_departure" and leg["evaluation_departure"] is None:
        return None
    return {
        "leg_id": leg["leg_id"],
        "source_kind": "independent_evaluation_context",
        "origin": points[origin],
        "destination": points[destination],
        "mode": mode,
        "time_basis": option["time_basis"],
        "routing_options": option["routing_options"],
        "departure": leg["evaluation_departure"]
        if option["time_basis"] == "explicit_departure"
        else None,
    }
