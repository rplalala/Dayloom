"""Independent reviewed-interest opportunities and pinned corpus proxies, offline only."""

from backend.cli.collection import _require

from .corpus_coverage import _coverage, _coverage_summary, _rag_coverage
from .opportunities import STAGES, opportunities_report
from .relevance_material import _interests, _reviews
from .rendering import cell as _cell
from .rendering import table_row as _row
from .sources import digest

ALL_STAGES = (*STAGES, "scheduled")


def relevance_report(context):
    ref = context.declaration.get("track_refs", {}).get("relevance")
    material = (
        context.read_ref(ref, "rtpeval_research_relevance_1")
        if ref
        else {
            "interest_inventory_refs": [],
            "review_refs": [],
            "coverage_refs": [],
        }
    )
    if ref:
        for field, expected in (
            ("population_id", context.population["population_id"]),
            ("population_revision", context.population["revision"]),
            ("profile_id", context.profile["profile_id"]),
            ("profile_revision", context.profile["revision"]),
        ):
            _require(
                material.get(field) == expected, "Relevance declaration binding mismatch: " + field
            )
    for field in ("interest_inventory_refs", "review_refs", "coverage_refs"):
        _require(
            isinstance(material.get(field), list),
            "Explicit relevance references required: " + field,
        )
    opportunities = opportunities_report(context)
    inventories = _interests(context, material["interest_inventory_refs"])
    reviews = _reviews(context, material["review_refs"], inventories, opportunities["runs"])
    runs = []
    for raw in opportunities["runs"]:
        row = {
            **{
                key: raw[key]
                for key in (
                    "case_id",
                    "case_revision",
                    "version",
                    "repetition_id",
                    "attempt_id",
                    "completion_status",
                )
            },
            "relevance_status": "unavailable",
            "stages": {
                name: {
                    "status": "unavailable",
                    "observed_count": 0,
                    "complete_count": None,
                    "canonical_ids": [],
                    "reasons": ["missing_independent_interests"],
                }
                for name in ALL_STAGES
            },
            "end_to_end": {
                "status": "unavailable",
                "observed_count": 0,
                "complete_count": None,
                "canonical_ids": [],
                "reasons": ["missing_independent_interests"],
            },
        }
        key = (raw["case_id"], raw["case_revision"])
        inventory = inventories.get(key)
        if inventory is not None:
            row["interest_inventory"] = inventory["value"]
            interests = inventory["value"]["interests"]
            row["relevance_status"] = "applicable" if interests else "not_applicable"
            native_stages = {**raw["stages"], "scheduled": raw["scheduled"]}
            labels = reviews.get(key, {})
            row["stages"] = {
                name: _stage(stage, interests, labels, raw["places"])
                for name, stage in native_stages.items()
            }
            row["per_interest"] = [
                {
                    "interest_id": interest["interest_id"],
                    "source_pointer": interest["source_pointer"],
                    "stages": {
                        name: _stage(stage, [interest], labels, raw["places"])
                        for name, stage in native_stages.items()
                    },
                }
                for interest in interests
            ]
            row["end_to_end"] = _principal(row["stages"])
            for item in row["per_interest"]:
                item["end_to_end"] = _principal(item["stages"])
                item["conversions"] = _conversions(item["stages"])
        row["conversions"] = _conversions(row["stages"])
        runs.append(row)
    coverage, coverage_profile = _coverage(context, material, inventories)
    _rag_coverage(coverage, opportunities["runs"])
    groups = dict.fromkeys(
        (run["case_id"], run["case_revision"], run["repetition_id"]) for run in runs
    )
    value = {
        "schema_version": "rtpeval_research_relevance_report_1",
        "processing_status": "completed",
        "track": "relevance",
        "applicability": "applicable"
        if any(run["relevance_status"] == "applicable" for run in runs)
        else "not_applicable"
        if not runs or all(run["relevance_status"] == "not_applicable" for run in runs)
        else "unavailable",
        "identity_unit": "canonical_place_id",
        "population_id": context.population["population_id"],
        "population_revision": context.population["revision"],
        "profile_id": context.profile["profile_id"],
        "profile_revision": context.profile["revision"],
        "population_digest": digest(context.population),
        "measurement_coverage": {
            "opportunities": opportunities["measurement_coverage"],
            "corpus": {
                "unit": "original_requests",
                "planned_cases": len(context.population["cases"]),
                **{
                    status: sum(row["status"] == status for row in coverage)
                    for status in ("complete", "partial", "unavailable")
                },
            },
        },
        "review_coverage": {
            "unit": "original_requests",
            "planned_cases": len(context.population["cases"]),
            "interest_inventory_cases": len(inventories),
            "relevance_review_cases": len(reviews),
            "relevance_review_records": sum(len(labels) for labels in reviews.values()),
        },
        "diagnostics": opportunities["diagnostics"],
        "runs": runs,
        "opportunity_semantic_sha256": opportunities["semantic_sha256"],
        "interest_inventory_bindings": [
            {
                "case_id": key[0],
                "case_revision": key[1],
                "sha256": inventory["sha256"],
                "value": inventory["value"],
            }
            for key, inventory in inventories.items()
        ],
        "independent_reviews": [
            record for labels in reviews.values() for record in labels.values()
        ],
        "comparisons": [_comparison(key, runs) for key in groups],
        "coverage": coverage,
        "coverage_profile": coverage_profile,
        "coverage_summary": _coverage_summary(
            coverage, coverage_profile, [_comparison(key, runs) for key in groups]
        ),
        "source_bindings": context.sources.manifest(),
        "source_digest": digest(context.sources.manifest()),
    }
    value["semantic_sha256"] = digest(value)
    return value


def markdown(value):
    lines = [
        "# Independent relevance and corpus coverage",
        "",
        "Counts use unique canonical places, overall and once per applicable interest. "
        "Independent reviews bind original request pointers and venue evidence. "
        "Unknown and absent reviews remain separate; planner/query labels are not review truth.",
        "",
        "End-to-end = relevant AND admitted AND supplied AND independently scheduled. "
        "Exact V2-minus-V1 deltas require completed compatible pairs and complete chain/reviews. "
        "Stage counts can remain available for failed runs without making their pair comparable.",
        "",
        "| Case / revision / repetition | Version | Interest | Stage | Observed relevant | "
        "Complete relevant | Status | Judged / inventoried | Unknown / absent | "
        "Canonical IDs | Reasons |",
        "| --- | --- | --- | --- | ---: | ---: | --- | --- | --- | --- | --- |",
    ]
    for run in value["runs"]:
        label = f"{run['case_id']} / {run['case_revision']} / {run['repetition_id']}"
        views = [
            ("overall", run["stages"]),
            *((item["interest_id"], item["stages"]) for item in run.get("per_interest", [])),
        ]
        for interest, stages in views:
            for name, stage in stages.items():
                review = stage.get("review_coverage", {})
                lines.append(
                    _row(
                        label,
                        run["version"],
                        interest,
                        name,
                        stage["observed_count"],
                        stage["complete_count"],
                        stage["status"],
                        f"{review.get('judged_subjects')} / {review.get('inventoried_subjects')}",
                        f"{review.get('unknown_subjects')} / "
                        f"{review.get('absent_review_subjects')}",
                        stage["canonical_ids"],
                        stage["reasons"],
                    )
                )
        stage = run["end_to_end"]
        lines.append(
            _row(
                label,
                run["version"],
                "overall",
                "end_to_end",
                stage["observed_count"],
                stage["complete_count"],
                stage["status"],
                None,
                None,
                stage["canonical_ids"],
                stage["reasons"],
            )
        )
    lines += [
        "",
        "## Conversions",
        "",
        "The numerator is the relevant identity intersection of both stages; "
        "the denominator is all relevant identities in the earlier stage. "
        "Zero denominators and incomplete stages/reviews have unavailable fractions.",
        "",
        "| Case / repetition | Version | Conversion | numerator | denominator | "
        "Fraction | Status | Reasons |",
        "| --- | --- | --- | ---: | ---: | ---: | --- | --- |",
    ]
    for run in value["runs"]:
        for name, conversion in run["conversions"].items():
            lines.append(
                _row(
                    run["case_id"] + " / " + run["repetition_id"],
                    run["version"],
                    name,
                    conversion["numerator"],
                    conversion["denominator"],
                    conversion["fraction"],
                    conversion["status"],
                    conversion["reasons"],
                )
            )
    lines += [
        "",
        "## Selected V1/V2 pairs",
        "",
        "| Case / revision / repetition | Metric | Delta | V1 | V2 | Gained | Lost "
        "| Retained | Status | Reasons |",
        "| --- | --- | ---: | ---: | ---: | --- | --- | --- | --- | --- |",
    ]
    for pair in value["comparisons"]:
        for name, difference in {**pair["stages"], "end_to_end": pair["end_to_end"]}.items():
            lines.append(
                _row(
                    f"{pair['case_id']} / {pair['case_revision']} / {pair['repetition_id']}",
                    name,
                    difference["delta"],
                    difference["v1_count"],
                    difference["v2_count"],
                    difference["gained_ids"],
                    difference["lost_ids"],
                    difference["retained_ids"],
                    difference["status"],
                    difference["reasons"],
                )
            )
    lines += [
        "",
        "## Pinned corpus coverage",
        "",
        value["coverage_summary"]["interpretation"],
        "",
        "Eligible count measures corpus entities in the fixed scope, not unique venues. "
        "Optional interest coverage uses a reviewed sample denominator; unknown coding "
        "retains bounds. Missing, timeout and truncated counts remain unavailable/partial.",
        "",
        "| Case / revision | Eligible entity count | Observed subtotal | Status | "
        "Stratum | Timing basis | Interest fraction | Bounds | Reasons |",
        "| --- | ---: | ---: | --- | --- | --- | ---: | --- | --- |",
    ]
    for coverage in value["coverage"]:
        reviewed = coverage.get("interest_coverage", {})
        lines.append(
            _row(
                coverage["case_id"] + " / " + coverage["case_revision"],
                coverage["eligible_entity_count"],
                coverage["observed_subtotal"],
                coverage["status"],
                coverage["stratum_id"],
                coverage.get("timing_basis"),
                reviewed.get("fraction"),
                f"{reviewed.get('lower_bound')} .. {reviewed.get('upper_bound')}",
                coverage["reasons"],
            )
        )
        if coverage.get("snapshot_identity"):
            snapshot = coverage["snapshot_identity"]
            lines += [
                "",
                "Pinned snapshot: "
                + _cell(snapshot["snapshot_ref"]["path"])
                + " SHA-256 `"
                + snapshot["snapshot_ref"]["sha256"]
                + "`; artifact `"
                + snapshot["artifact_sha256"]
                + "`, policy "
                + _cell(snapshot["policy_version"])
                + ", space "
                + _cell(snapshot["space_id"])
                + ".",
                "Fixed scope: `"
                + _cell(coverage["scope"])
                + "`; scope SHA-256 `"
                + coverage["scope_sha256"]
                + "`.",
                "Measurement: "
                + _cell(coverage["measurement_method"])
                + " at "
                + _cell(coverage["measured_at"])
                + ".",
            ]
    summary = value["coverage_summary"]
    lines += [
        "",
        "## Descriptive strata",
        "",
        f"Available pairs: {summary['available_pairs']}; "
        f"omitted pairs: {summary['omitted_pairs']}; "
        f"unstratified pairs: {summary['unstratified_pairs']}.",
        "",
        "| Stratum | Lower inclusive | Upper exclusive | Case IDs | Available pairs "
        "| Omitted pairs | End-to-end delta median |",
        "| --- | ---: | ---: | --- | ---: | ---: | ---: |",
    ]
    for stratum in summary["strata"]:
        lines.append(
            _row(
                stratum["stratum_id"],
                stratum["min_inclusive"],
                stratum["max_exclusive"],
                stratum["case_ids"],
                stratum["available_pairs"],
                stratum["omitted_pairs"],
                stratum["delta_median"],
            )
        )
    if value["coverage_profile"]:
        profile = value["coverage_profile"]
        lines += [
            "",
            "Strata profile: "
            + _cell(profile["coverage_profile_id"])
            + " / "
            + _cell(profile["revision"])
            + "; declared metric "
            + _cell(profile["metric"])
            + "; timing "
            + _cell(profile["timing_basis"])
            + ".",
        ]
    lines += [
        "",
        "## Independent reviews",
        "",
        "| Review / revision | Interest | Canonical / unresolved subject | Verdict "
        "| Reviewer / kind | Time | Rationale |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for review in value["independent_reviews"]:
        lines.append(
            _row(
                review["review_id"] + " / " + review["revision"],
                review["interest_id"],
                review.get("canonical_place_id") or review["unresolved_subject_id"],
                review["verdict"],
                review["reviewer_ref"] + " / " + review["reviewer_kind"],
                review["reviewed_at"],
                review["rationale"],
            )
        )
    lines += [
        "",
        f"Source digest: `{value['source_digest']}`.",
        f"Semantic digest: `{value['semantic_sha256']}`.",
        "",
    ]
    return "\n".join(lines)


def _stage(stage, interests, labels, places):
    if not interests:
        return {
            "status": "not_applicable",
            "canonical_ids": [],
            "observed_count": 0,
            "complete_count": None,
            "reasons": ["no_user_poi_interests"],
        }
    ids = set(stage["canonical_ids"])
    relevant, negative, unknown, absent = set(), set(), set(), set()
    supplied = unknown_judgments = missing = judged = 0
    for pid in ids:
        verdicts = [
            labels.get((interest["interest_id"], pid), {}).get("verdict") for interest in interests
        ]
        supplied += sum(v is not None for v in verdicts)
        unknown_judgments += verdicts.count("unknown")
        missing += verdicts.count(None)
        judged += any(v is not None for v in verdicts)
        if "relevant" in verdicts:
            relevant.add(pid)
        elif all(v == "not_relevant" for v in verdicts):
            negative.add(pid)
        elif all(v is None for v in verdicts):
            absent.add(pid)
        else:
            unknown.add(pid)
    complete = stage["status"] == "complete" and not missing and not unknown_judgments
    reasons = list(stage["reasons"])
    if missing:
        reasons.append("missing_relevance_reviews")
    if unknown_judgments:
        reasons.append("unknown_relevance_judgments")
    origins = stage.get("origin_partitions") or {
        "google_only": [
            pid
            for pid in ids
            if places.get(pid, {}).get("google_origins")
            and not places.get(pid, {}).get("rag_origins")
        ],
        "rag_only": [
            pid
            for pid in ids
            if places.get(pid, {}).get("rag_origins")
            and not places.get(pid, {}).get("google_origins")
        ],
        "mixed": [
            pid
            for pid in ids
            if places.get(pid, {}).get("rag_origins") and places.get(pid, {}).get("google_origins")
        ],
    }
    return {
        "status": "complete"
        if complete
        else "unavailable"
        if stage["status"] == "unavailable"
        else "partial",
        "stage_status": stage["status"],
        "canonical_ids": sorted(relevant),
        "observed_count": len(relevant),
        "complete_count": len(relevant) if complete else None,
        "origin_partitions": {
            name: sorted(set(members) & relevant) for name, members in origins.items()
        },
        "review_coverage": {
            "judged_subjects": judged,
            "inventoried_subjects": len(ids),
            "fraction": judged / len(ids) if ids else None,
            "relevant_subjects": len(relevant),
            "negative_subjects": len(negative),
            "unknown_subjects": len(unknown),
            "absent_review_subjects": len(absent),
            "expected_judgments": len(ids) * len(interests),
            "supplied_judgments": supplied,
            "unknown_judgments": unknown_judgments,
            "missing_judgments": missing,
        },
        "reasons": reasons,
    }


def _conversions(stages):
    result = {}
    for left, right in (
        *zip(ALL_STAGES[:-1], ALL_STAGES[1:], strict=True),
        ("admitted", "supplied"),
    ):
        a, b = stages[left], stages[right]
        denominator = a["complete_count"]
        complete = a["status"] == b["status"] == "complete"
        numerator = len(set(a["canonical_ids"]) & set(b["canonical_ids"])) if complete else None
        result[left + "_to_" + right] = {
            "status": "complete" if complete and denominator else "unavailable",
            "numerator": numerator,
            "denominator": denominator,
            "fraction": numerator / denominator if complete and denominator else None,
            "reasons": []
            if complete and denominator
            else ["zero_denominator" if complete else "incomplete_chain"],
        }
    return result


def _difference(a, b, compatible):
    complete = compatible and a["status"] == b["status"] == "complete"
    first, second = set(a["canonical_ids"]), set(b["canonical_ids"])
    return {
        "status": "complete" if complete else "unavailable",
        "delta": len(second) - len(first) if complete else None,
        "v1_count": a["complete_count"],
        "v2_count": b["complete_count"],
        "gained_ids": sorted(second - first) if complete else [],
        "lost_ids": sorted(first - second) if complete else [],
        "retained_ids": sorted(first & second) if complete else [],
        "reasons": [] if complete else ["incomplete_or_incompatible_pair"],
    }


def _comparison(key, runs):
    pair = {
        run["version"]: run
        for run in runs
        if (run["case_id"], run["case_revision"], run["repetition_id"]) == key
    }
    if "v1" not in pair or "v2" not in pair:
        missing = {
            "status": "unavailable",
            "delta": None,
            "v1_count": None,
            "v2_count": None,
            "gained_ids": [],
            "lost_ids": [],
            "retained_ids": [],
            "reasons": ["missing_planned_version"],
        }
        return {
            "case_id": key[0],
            "case_revision": key[1],
            "repetition_id": key[2],
            "end_to_end": missing,
            "stages": {name: dict(missing) for name in ALL_STAGES},
            "per_interest": [],
        }
    a, b = pair["v1"], pair["v2"]
    compatible = a["completion_status"] == b["completion_status"] == "completed" and a.get(
        "interest_inventory"
    ) == b.get("interest_inventory")
    return {
        "case_id": key[0],
        "case_revision": key[1],
        "repetition_id": key[2],
        "end_to_end": _difference(a["end_to_end"], b["end_to_end"], compatible),
        "stages": {
            name: _difference(a["stages"][name], b["stages"][name], compatible)
            for name in ALL_STAGES
        },
        "per_interest": [
            {
                "interest_id": interest["interest_id"],
                "end_to_end": _difference(
                    interest["end_to_end"], b["per_interest"][index]["end_to_end"], compatible
                ),
                "stages": {
                    name: _difference(
                        interest["stages"][name],
                        b["per_interest"][index]["stages"][name],
                        compatible,
                    )
                    for name in ALL_STAGES
                },
            }
            for index, interest in enumerate(a.get("per_interest", []))
        ]
        if a.get("per_interest") and b.get("per_interest")
        else [],
    }


def _principal(stages):
    required = [stages[name] for name in ("admitted", "supplied", "scheduled")]
    ids = sorted(set.intersection(*(set(stage["canonical_ids"]) for stage in required)))
    complete = all(stage["status"] == "complete" for stage in required)
    applicable = not all(stage["status"] == "not_applicable" for stage in required)
    return {
        "status": "not_applicable" if not applicable else "complete" if complete else "partial",
        "canonical_ids": ids,
        "observed_count": len(ids),
        "complete_count": len(ids) if complete else None,
        "reasons": []
        if complete
        else ["no_user_poi_interests"]
        if not applicable
        else ["incomplete_relevance_or_chain"],
    }
