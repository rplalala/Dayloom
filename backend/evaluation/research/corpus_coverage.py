"""Pinned geographic entity coverage and independently reviewed sample proxies."""

from math import isfinite
from statistics import median

from backend.cli.collection import _require

from .context import text_fields, timestamp
from .relevance_material import _case_key, _pointer, _reviewer
from .sources import digest


def _integer(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _snapshot(context, value):
    _require(isinstance(value, dict), "Pinned corpus snapshot identity required")
    text_fields(value, ("artifact_sha256", "policy_version", "space_id"))
    _require(
        len(value["artifact_sha256"]) == 64
        and all(c in "0123456789abcdef" for c in value["artifact_sha256"]),
        "Invalid corpus artifact hash",
    )
    snapshot = context.read_ref(value.get("snapshot_ref"))
    pointers = value.get("identity_pointers")
    _require(isinstance(pointers, dict), "Explicit pinned identity field pointers required")
    for field in ("artifact_sha256", "policy_version", "space_id"):
        _require(
            _pointer(snapshot, pointers.get(field)) == value[field],
            "Pinned corpus snapshot identity mismatch: " + field,
        )
    return value


def _coverage_binding(value, cases):
    key = _case_key(value)
    _require(
        key in cases and value.get("input_sha256") == cases[key]["input_ref"]["sha256"],
        "Foreign corpus coverage input binding",
    )
    scope = value.get("scope")
    _require(
        isinstance(scope, dict) and scope and isinstance(scope.get("kind"), str) and scope["kind"],
        "Explicit fixed geographic scope required",
    )
    _geography(scope)
    _require(value.get("scope_sha256") == digest(scope), "Fixed geographic scope hash mismatch")
    return key


def _timing(context, value, key=None):
    basis = value.get("timing_basis")
    _require(
        basis in ("prospective", "retrospective", "unverified"),
        "Explicit corpus declaration timing basis required",
    )
    declared = timestamp(value.get("declared_at"))
    attempts = [
        slot["primary_attempt"]
        for slot in context.slots
        if slot["primary_attempt"] is not None
        and (key is None or (slot["case_id"], slot["case_revision"]) == key)
    ]
    if basis == "prospective":
        if not attempts:
            return "unverified"
        _require(
            declared <= min(timestamp(a["dispatched_at"]) for a in attempts),
            "Prospective coverage declaration occurs after dispatch",
        )
    return basis


def _coverage(context, material, inventories):
    cases = {(case["case_id"], case["revision"]): case for case in context.population["cases"]}
    profile_ref = material.get("coverage_profile_ref")
    profile = (
        context.read_ref(profile_ref, "rtpeval_research_coverage_profile_1")
        if profile_ref
        else None
    )
    fixed = {}
    if profile is not None:
        text_fields(profile, ("coverage_profile_id", "revision"))
        _require(
            profile.get("population_id") == context.population["population_id"]
            and profile.get("population_revision") == context.population["revision"],
            "Foreign coverage profile population",
        )
        _snapshot(context, profile.get("snapshot_identity"))
        _require(
            profile.get("metric") in ("eligible_entity_count", "interest_coverage_fraction"),
            "Unsupported declared coverage metric",
        )
        _require(isinstance(profile.get("cases"), list), "Explicit coverage profile cases required")
        for binding in profile["cases"]:
            key = _coverage_binding(binding, cases)
            _require(key not in fixed, "Duplicate coverage profile case")
            fixed[key] = binding
        strata = profile.get("strata")
        _require(isinstance(strata, list) and strata, "Explicit fixed coverage strata required")
        ids, previous = set(), 0
        for index, stratum in enumerate(strata):
            text_fields(stratum, ("stratum_id",))
            lower, upper = stratum.get("min_inclusive"), stratum.get("max_exclusive")
            _require(stratum["stratum_id"] not in ids, "Duplicate coverage stratum identity")
            ids.add(stratum["stratum_id"])
            _require(
                isinstance(lower, (int, float))
                and not isinstance(lower, bool)
                and lower >= previous
                and lower >= 0,
                "Overlapping or invalid fixed coverage thresholds",
            )
            _require(
                upper is None
                and index == len(strata) - 1
                or isinstance(upper, (int, float))
                and not isinstance(upper, bool)
                and upper > lower,
                "Invalid coverage stratum upper threshold",
            )
            previous = upper if upper is not None else lower
        profile = {
            **profile,
            "declared_timing_basis": profile["timing_basis"],
            "timing_basis": _timing(context, profile),
        }
    supplied = {}
    for ref in material["coverage_refs"]:
        raw = context.read_ref(ref, "rtpeval_research_corpus_coverage_1")
        if raw.get("producer_completion_ref") is not None:
            completion = context.read_ref(
                raw["producer_completion_ref"], "rtpeval_corpus_completion_1"
            )
            _require(
                completion.get("processing_status") == "completed"
                and completion.get("coverage_sha256")
                == digest({k: v for k, v in raw.items() if k != "producer_completion_ref"}),
                "Uncommitted or changed corpus producer sidecar",
            )
            evidence = context.read_ref(
                completion.get("measurement_ref"), "rtpeval_corpus_measurement_1"
            )
            _require(
                evidence.get("finished_at") == raw.get("measured_at")
                and evidence.get("measurement_method") == raw.get("measurement_method"),
                "Corpus completion observation mismatch",
            )
        key = _coverage_binding(raw, cases)
        _require(key not in supplied, "Duplicate corpus coverage case")
        snapshot = _snapshot(context, raw.get("snapshot_identity"))
        text_fields(raw, ("measurement_method", "measured_at"))
        timestamp(raw["measured_at"])
        status = raw.get("count_status")
        count, observed = raw.get("eligible_entity_count"), raw.get("observed_subtotal")
        _require(
            status in ("complete", "partial", "unavailable"),
            "Explicit eligible entity count completeness required",
        )
        _require(count is None or _integer(count), "Invalid eligible entity count")
        _require(observed is None or _integer(observed), "Invalid observed entity subtotal")
        _require(
            isinstance(raw.get("reasons"), list)
            and all(isinstance(reason, str) and reason for reason in raw["reasons"]),
            "Explicit corpus count reasons required",
        )
        _require(
            status == "complete"
            and _integer(count)
            and observed == count
            or status != "complete"
            and count is None
            and raw["reasons"],
            "Partial/unavailable corpus cannot declare exact zero or count",
        )
        if profile is not None:
            _require(key in fixed, "Corpus case outside fixed coverage profile")
            _require(
                raw["scope"] == fixed[key]["scope"]
                and raw["scope_sha256"] == fixed[key]["scope_sha256"]
                and snapshot == profile["snapshot_identity"],
                "Incompatible fixed corpus snapshot or geographic scope",
            )
        row = {
            **raw,
            "status": status,
            "declared_timing_basis": raw["timing_basis"],
            "timing_basis": _timing(context, raw, key),
            "stratum_id": None,
            "interest_coverage": {
                "status": "unavailable",
                "fraction": None,
                "reasons": ["missing_reviewed_interest_coverage"],
            },
        }
        if raw.get("interest_coverage_ref") is not None:
            row["interest_coverage"] = _interest_coverage(context, raw, inventories.get(key))
        metric = (
            count
            if profile and profile["metric"] == "eligible_entity_count"
            else row["interest_coverage"]["fraction"]
            if profile
            else None
        )
        if metric is not None and status == "complete":
            for stratum in profile["strata"]:
                if metric >= stratum["min_inclusive"] and (
                    stratum["max_exclusive"] is None or metric < stratum["max_exclusive"]
                ):
                    row["stratum_id"] = stratum["stratum_id"]
                    break
        supplied[key] = row
    rows = [
        supplied.get(
            key,
            {
                "case_id": key[0],
                "case_revision": key[1],
                "status": "unavailable",
                "eligible_entity_count": None,
                "observed_subtotal": None,
                "stratum_id": None,
                "reasons": ["missing_independent_coverage"],
            },
        )
        for key in cases
    ]
    return rows, profile


def _coverage_summary(rows, profile, comparisons):
    strata = []
    by_case = {_case_key(row): row for row in rows}
    for definition in profile["strata"] if profile else []:
        pairs = [
            pair
            for pair in comparisons
            if by_case[_case_key(pair)]["stratum_id"] == definition["stratum_id"]
        ]
        deltas = [
            pair["end_to_end"]["delta"]
            for pair in pairs
            if pair["end_to_end"]["status"] == "complete"
        ]
        strata.append(
            {
                **definition,
                "case_ids": [
                    row["case_id"] for row in rows if row["stratum_id"] == definition["stratum_id"]
                ],
                "available_pairs": len(deltas),
                "omitted_pairs": len(pairs) - len(deltas),
                "delta_median": median(deltas) if deltas else None,
            }
        )
    return {
        "interpretation": "Descriptive eligible-entity/geographic proxy; "
        "repeated slots are not independent samples. "
        "No citywide recall or unique-venue coverage claim.",
        "available_pairs": sum(pair["end_to_end"]["status"] == "complete" for pair in comparisons),
        "omitted_pairs": sum(pair["end_to_end"]["status"] != "complete" for pair in comparisons),
        "unstratified_pairs": sum(
            by_case[_case_key(pair)]["stratum_id"] is None for pair in comparisons
        ),
        "strata": strata,
    }


def _interest_coverage(context, coverage, inventory):
    _require(inventory is not None, "Sample coding needs reviewed original interest inventory")
    value = context.read_ref(
        coverage["interest_coverage_ref"], "rtpeval_research_interest_coverage_1"
    )
    binding = {
        field: coverage[field]
        for field in ("case_id", "case_revision", "input_sha256", "scope_sha256")
    }
    binding["snapshot_sha256"] = coverage["snapshot_identity"]["snapshot_ref"]["sha256"]
    for field, expected in binding.items():
        _require(
            value.get(field) == expected, "Interest coverage source binding mismatch: " + field
        )
    _require(
        value.get("interest_inventory_sha256") == inventory["sha256"],
        "Stale sampled interest inventory",
    )
    text_fields(value, ("measurement_method", "uncertainty"))
    taxonomy = context.read_ref(value.get("taxonomy_ref"), "rtpeval_research_interest_taxonomy_1")
    interest_ids = taxonomy.get("interest_ids")
    _require(
        isinstance(interest_ids, list)
        and interest_ids
        and len(set(interest_ids)) == len(interest_ids)
        and all(
            interest in {item["interest_id"] for item in inventory["value"]["interests"]}
            for interest in interest_ids
        ),
        "Foreign or duplicate reviewed coverage taxonomy",
    )
    sample = context.read_ref(value.get("sample_ref"), "rtpeval_research_corpus_sample_1")
    coding = context.read_ref(value.get("coding_review_ref"), "rtpeval_research_corpus_coding_1")
    _reviewer(coding)
    for source in (sample, coding):
        for field, expected in binding.items():
            _require(source.get(field) == expected, "Stale coding/sample binding: " + field)
    for field, expected in (
        ("sample_sha256", value["sample_ref"]["sha256"]),
        ("taxonomy_sha256", value["taxonomy_ref"]["sha256"]),
        ("interest_inventory_sha256", inventory["sha256"]),
    ):
        _require(
            coding.get(field) == expected, "Stale independent coding evidence binding: " + field
        )
    sets = {}
    for field, source in (
        ("entity_ids", sample),
        ("relevant_entity_ids", coding),
        ("unknown_entity_ids", coding),
    ):
        members = source.get(field)
        _require(
            isinstance(members, list)
            and all(isinstance(member, str) and member for member in members)
            and len(set(members)) == len(members),
            "Malformed or duplicate sampled entity identities",
        )
        sets[field] = set(members)
    entities, relevant, unknown = (
        sets["entity_ids"],
        sets["relevant_entity_ids"],
        sets["unknown_entity_ids"],
    )
    _require(
        relevant <= entities and unknown <= entities and not (relevant & unknown),
        "Contradictory or foreign sample coding",
    )
    _require(
        _integer(value.get("numerator"))
        and _integer(value.get("denominator"))
        and value["numerator"] == len(relevant)
        and value["denominator"] == len(entities),
        "Sample numerator/denominator mismatch",
    )
    evidence_refs = coding.get("evidence_refs")
    _require(
        isinstance(evidence_refs, list) and evidence_refs,
        "Independent sample coding evidence required",
    )
    evidence_entities = set()
    for ref in evidence_refs:
        evidence = context.read_ref(ref)
        _require(
            evidence.get("source_kind")
            in (
                "independent_google_places",
                "independent_official",
                "independent_reviewed_description",
            ),
            "Planner material cannot establish sample coding",
        )
        for field, expected in binding.items():
            _require(
                evidence.get(field) == expected, "Foreign coding evidence snapshot/scope/input"
            )
        members = evidence.get("entity_ids")
        _require(
            isinstance(members, list)
            and all(isinstance(member, str) and member for member in members),
            "Coding evidence entity inventory required",
        )
        evidence_entities.update(members)
    _require(entities <= evidence_entities, "Missing independent sampled entity evidence")
    denominator = len(entities)
    _require(
        coverage["count_status"] != "complete" or denominator <= coverage["eligible_entity_count"],
        "Reviewed sample exceeds exact eligible corpus count",
    )
    return {
        **value,
        "status": "unavailable" if not denominator else "partial" if unknown else "complete",
        "fraction": len(relevant) / denominator if denominator and not unknown else None,
        "lower_bound": len(relevant) / denominator if denominator else None,
        "upper_bound": (len(relevant) + len(unknown)) / denominator if denominator else None,
        "unknown_entity_ids": sorted(unknown),
        "negative_entity_ids": sorted(entities - relevant - unknown),
        "interest_ids": interest_ids,
        "reasons": ["zero_denominator"]
        if not denominator
        else ["unknown_sample_coding"]
        if unknown
        else [],
    }


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value)


def _geography(scope):
    if scope["kind"] == "radius":
        _require(
            _number(scope.get("latitude"))
            and -90 <= scope["latitude"] <= 90
            and _number(scope.get("longitude"))
            and -180 <= scope["longitude"] <= 180
            and _number(scope.get("radius_m"))
            and scope["radius_m"] > 0,
            "Invalid radius geographic scope",
        )
    elif scope["kind"] == "bounding_box":
        _require(
            all(_number(scope.get(field)) for field in ("south", "north", "west", "east"))
            and -90 <= scope["south"] < scope["north"] <= 90
            and -180 <= scope["west"] < scope["east"] <= 180,
            "Invalid bounding-box geographic scope",
        )
    else:
        _require(False, "Unsupported fixed geographic scope kind")


def _rag_coverage(coverage, runs):
    by_case = {_case_key(row): row for row in coverage}
    for run in runs:
        row = by_case[_case_key(run)]
        snapshot = row.get("snapshot_identity")
        if snapshot is None:
            continue
        for place in run["places"].values():
            for origin in place["rag_origins"]:
                _require(
                    all(
                        origin.get(field) == snapshot[target]
                        for field, target in (
                            ("artifact_hash", "artifact_sha256"),
                            ("policy_version", "policy_version"),
                            ("space_id", "space_id"),
                        )
                    ),
                    "Pinned coverage is incompatible with selected RAG corpus",
                )
