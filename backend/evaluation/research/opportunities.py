"""Source-bound canonical candidate opportunities; no relevance or quality judgments."""

from backend.cli.collection import _require

from .context import slot_key, text_fields
from .sources import digest

STAGES = ("discovered", "admitted", "enriched", "supplied")


def unavailable(reason):
    return {
        "status": "unavailable",
        "canonical_ids": [],
        "observed_count": 0,
        "complete_count": None,
        "reasons": [reason],
        "origin_partitions": {"google_only": [], "rag_only": [], "mixed": []},
    }


def opportunities_report(context):
    ref = context.declaration.get("track_refs", {}).get("opportunities")
    material = (
        context.read_ref(ref, "rtpeval_research_opportunities_1") if ref else {"observations": []}
    )
    _require(
        isinstance(material.get("observations"), list), "Explicit opportunity observations required"
    )
    observations = {}
    for entry in material["observations"]:
        text_fields(
            entry,
            (
                "case_id",
                "case_revision",
                "version",
                "repetition_id",
                "attempt_id",
                "run_id",
                "input_sha256",
                "configuration_sha256",
            ),
        )
        _require(entry["version"] in ("v1", "v2"), "Opportunity material only supports V1/V2")
        key = slot_key(entry)
        _require(
            key in context.selected_attempts and key not in observations,
            "Foreign or duplicate opportunity slot",
        )
        attempt = context.selected_attempts[key]
        _require(attempt is not None, "Opportunity capture requires selected dispatched attempt")
        for field in ("attempt_id", "run_id", "input_sha256", "configuration_sha256"):
            _require(
                entry[field] == attempt[field], "Opportunity attempt binding mismatch: " + field
            )
        _require(
            "result_sha256" in entry, "Explicit opportunity result availability binding required"
        )
        _require(
            entry.get("result_sha256") == (attempt.get("result_ref") or {}).get("sha256"),
            "Opportunity result binding mismatch",
        )
        capture = context.read_ref(entry.get("capture_ref"), "rtpeval_candidate_capture_1")
        _require(
            capture.get("version") == entry["version"] and capture.get("run_id") == entry["run_id"],
            "Capture run/version mismatch",
        )
        if capture.get("result_semantic_sha256") is not None:
            _require(
                attempt.get("result_ref") is not None,
                "Capture final semantic hash without saved result",
            )
            _require(
                capture["result_semantic_sha256"]
                == digest(context.read_ref(attempt["result_ref"])),
                "Capture final semantic hash mismatch",
            )
        observations[key] = (entry, capture)
    runs = []
    for slot in context.slots:
        if slot["version"] not in ("v1", "v2"):
            continue
        row = {
            **dict(
                zip(
                    ("case_id", "case_revision", "version", "repetition_id"),
                    slot_key(slot),
                    strict=True,
                )
            ),
            "attempt_id": slot["primary_attempt"]["attempt_id"]
            if slot["primary_attempt"]
            else None,
            "completion_status": slot["status"],
            "stages": {stage: unavailable("missing_historical_capture") for stage in STAGES},
            "scheduled": unavailable("missing_independent_associations"),
            "places": {},
            "omissions": [],
            "incremental_rag_ids": None,
            "diagnostics": [],
        }
        if slot_key(slot) in observations:
            entry, capture = observations[slot_key(slot)]
            row.update(_captured(capture))
            row["observation"] = entry
            if entry.get("identity_sources") is not None:
                row["scheduled"] = _scheduled(context, slot, entry)
                confirmed = set(row["scheduled"]["canonical_ids"])
                supplied = set(row["stages"]["supplied"]["canonical_ids"])
                if row["stages"]["supplied"]["status"] == "complete" and not confirmed <= supplied:
                    row["diagnostics"].append("independent_scheduling_conflicts_with_supplied_fate")
                if slot["primary_attempt"].get("result_ref"):
                    result = context.read_ref(slot["primary_attempt"]["result_ref"])
                    claimed = (result.get("rag_discovery") or {}).get("fate", {}).get("scheduled")
                    if claimed is not None and set(claimed) != confirmed & set(
                        pid for pid, place in row["places"].items() if place["rag_origins"]
                    ):
                        row["diagnostics"].append(
                            "producer_scheduled_fate_conflicts_with_independent_associations"
                        )
        runs.append(row)
    value = {
        "schema_version": "rtpeval_research_opportunities_report_1",
        "identity_unit": "canonical_place_id",
        "population_id": context.population["population_id"],
        "population_revision": context.population["revision"],
        "profile_id": context.profile["profile_id"],
        "profile_revision": context.profile["revision"],
        "runs": runs,
        "cross_version": _cross_version(runs),
        "source_bindings": context.sources.manifest(),
        "source_digest": digest(context.sources.manifest()),
    }
    value["semantic_sha256"] = digest(value)
    return value


def markdown(value):
    lines = [
        "# Canonical place opportunities",
        "",
        "Identity unit: canonical place ID. Counts describe observed opportunities; "
        "relevance is independently reviewed.",
        "",
        "| Case / revision / repetition | Version | Stage | Observed | Complete count | "
        "Status | Canonical IDs | Reasons |",
        "| --- | --- | --- | ---: | ---: | --- | --- | --- |",
    ]
    for run in value["runs"]:
        for name, stage in {**run["stages"], "scheduled": run["scheduled"]}.items():
            lines.append(
                f"| {run['case_id']} / {run['case_revision']} / {run['repetition_id']} "
                f"| {run['version']} | {name} | {stage['observed_count']} "
                f"| {stage['complete_count']} | {stage['status']} "
                f"| {', '.join(stage['canonical_ids'])} | {', '.join(stage['reasons'])} |"
            )
        if run["diagnostics"]:
            lines += [
                "",
                f"{run['case_id']} {run['version']} diagnostics: " + ", ".join(run["diagnostics"]),
                "",
            ]
    lines += [
        "",
        f"Source digest: `{value['source_digest']}`.",
        f"Semantic digest: `{value['semantic_sha256']}`.",
        "",
    ]
    return "\n".join(lines)


def _captured(capture):
    _require(isinstance(capture.get("stages"), dict), "Explicit captured stages required")
    _require(set(capture["stages"]) <= set(STAGES), "Unknown candidate stage")
    places, stages = {}, {}
    for name in STAGES:
        raw = capture["stages"].get(name)
        if raw is None:
            stages[name] = unavailable("missing_historical_capture")
            continue
        _require(isinstance(raw, dict), "Invalid stage capture object")
        _require(
            raw.get("status") in ("complete", "partial", "unavailable"),
            "Invalid stage capture completeness",
        )
        _require(
            isinstance(raw.get("places"), list) and isinstance(raw.get("reasons"), list),
            "Explicit stage places/reasons required",
        )
        _require(
            all(isinstance(reason, str) and reason for reason in raw["reasons"]),
            "Invalid stage reasons",
        )
        _require(raw["status"] != "partial" or raw["reasons"], "Partial capture requires reason")
        ids = set()
        for place in raw["places"]:
            text_fields(place, ("canonical_place_id",))
            pid = place["canonical_place_id"]
            google, rag = place.get("google_origins"), place.get("rag_origins")
            _require(
                isinstance(google, list) and isinstance(rag, list) and (google or rag),
                "Canonical candidate requires native discovery provenance",
            )
            for origin in google:
                text_fields(origin, ("intent_id", "source_query"))
                _require(
                    type(origin.get("provider_rank")) is int
                    and type(origin.get("actual_result_count")) is int
                    and 0 <= origin["provider_rank"] < origin["actual_result_count"],
                    "Invalid Google discovery rank/count",
                )
            for origin in rag:
                text_fields(
                    origin,
                    (
                        "entity_id",
                        "artifact_hash",
                        "text_hash",
                        "space_id",
                        "policy_version",
                        "resolution",
                        "evidence_ref",
                    ),
                )
                query = origin.get("query")
                _require(isinstance(query, dict), "RAG query provenance required")
                text_fields(query, ("query_id", "text"))
                _require(
                    query.get("version") == "rag_query_plan_1"
                    and query.get("origin") in ("user", "system_default"),
                    "Unsupported RAG query provenance",
                )
                for field in ("intent_ids", "requirement_refs"):
                    _require(
                        isinstance(query.get(field), list)
                        and all(isinstance(item, str) and item for item in query[field]),
                        "RAG query links required",
                    )
                _require(
                    (
                        query["origin"] == "user"
                        and query["intent_ids"]
                        and query["requirement_refs"]
                    )
                    or (
                        query["origin"] == "system_default"
                        and not query["intent_ids"]
                        and not query["requirement_refs"]
                    ),
                    "RAG query origin/link contradiction",
                )
                _require(
                    type(origin.get("rank")) is int and 1 <= origin["rank"] <= 20,
                    "Invalid RAG rank",
                )
                _require(
                    type(origin.get("cosine")) in (int, float)
                    and -1.00001 <= origin["cosine"] <= 1.00001
                    and type(origin.get("distance_km")) in (int, float)
                    and origin["distance_km"] >= 0,
                    "Invalid RAG similarity/distance",
                )
                _require(
                    origin["resolution"]
                    in ("google_observation", "request_resolved", "direct_id", "fallback")
                    and origin["evidence_ref"] == "google_places:" + pid,
                    "Invalid RAG canonical resolution",
                )
            ids.add(pid)
            merged = places.setdefault(
                pid, {"canonical_place_id": pid, "google_origins": [], "rag_origins": []}
            )
            for field in ("google_origins", "rag_origins"):
                indexed = {digest(origin): origin for origin in merged[field] + place[field]}
                merged[field] = [indexed[key] for key in sorted(indexed)]
        _require(
            raw["status"] != "unavailable" or not ids, "Unavailable stage contains memberships"
        )
        stages[name] = {
            "status": raw["status"],
            "canonical_ids": sorted(ids),
            "observed_count": len(ids),
            "complete_count": len(ids) if raw["status"] == "complete" else None,
            "reasons": raw["reasons"],
        }
    for stage in stages.values():
        ids = stage["canonical_ids"]
        stage["origin_partitions"] = {
            "google_only": [
                pid
                for pid in ids
                if places[pid]["google_origins"] and not places[pid]["rag_origins"]
            ],
            "rag_only": [
                pid
                for pid in ids
                if places[pid]["rag_origins"] and not places[pid]["google_origins"]
            ],
            "mixed": [
                pid for pid in ids if places[pid]["google_origins"] and places[pid]["rag_origins"]
            ],
        }
    for previous, name in zip(STAGES, STAGES[1:], strict=False):
        if stages[previous]["status"] == "complete":
            _require(
                set(stages[name]["canonical_ids"]) <= set(stages[previous]["canonical_ids"]),
                "Stage lineage contradicts complete prior stage",
            )
    pre = capture.get("pre_rag_google_ids")
    _require(
        pre is None or isinstance(pre, list) and all(isinstance(pid, str) and pid for pid in pre),
        "Invalid pre-RAG Google inventory",
    )
    if pre is not None:
        _require(
            set(pre) <= {pid for pid, place in places.items() if place["google_origins"]},
            "Pre-RAG Google inventory contradicts discovery provenance",
        )
    incremental = (
        sorted(set(stages["discovered"]["origin_partitions"]["rag_only"]) - set(pre))
        if pre is not None
        else None
    )
    omissions = capture.get("omissions")
    _require(isinstance(omissions, list), "Explicit omission observations required")
    for omission in omissions:
        text_fields(omission, ("canonical_place_id", "stage", "reason"))
        _require(
            omission["stage"] in STAGES and omission["canonical_place_id"] in places,
            "Foreign omission stage/place",
        )
    return {
        "stages": stages,
        "places": dict(sorted(places.items())),
        "omissions": omissions,
        "pre_rag_google_ids": pre,
        "incremental_rag_ids": incremental,
        "incremental_rag_status": stages["discovered"]["status"]
        if pre is not None
        else "unavailable",
        "rag_provenance": capture.get("rag"),
    }


def _scheduled(context, slot, entry):
    from pathlib import Path

    from backend.evaluation.identity import resolve_identities, resolve_legacy_identities
    from backend.evaluation.intake import load_batch

    bundle = entry["identity_sources"]
    _require(isinstance(bundle, dict), "Invalid identity source bundle")
    _require(bundle.get("mode") in ("program", "legacy"), "Explicit native identity mode required")
    manifest_ref = bundle.get("manifest_ref")
    manifest = context.read_ref(manifest_ref, "rtpeval_batch_1")
    base = Path(manifest_ref["path"]).parent
    if manifest.get("projection_reviews_ref"):
        ref = manifest["projection_reviews_ref"]
        context.read_ref({**ref, "path": (base / ref["path"]).as_posix()}, "rtpeval_reviews_1")
    for group in manifest.get("groups", []):
        refs = [group.get("input_ref"), group.get("requirement_spec_ref")]
        refs += [
            ref
            for run in group.get("selected_runs", {}).values()
            for name, ref in run.items()
            if name.endswith("_ref") and isinstance(ref, dict)
        ]
        for ref in refs:
            if ref is not None and ref.get("availability") == "available":
                context.read_ref({**ref, "path": (base / ref["path"]).as_posix()})
    intake = load_batch(context.root / manifest_ref["path"])
    prepared = intake.to_dict()
    _require(
        prepared.get("status") == "accepted", "Native identity intake requires material correction"
    )
    attempt = slot["primary_attempt"]
    matching = [
        group for group in prepared["inventory"] if group["group_id"] == attempt.get("group_id")
    ]
    _require(len(matching) == 1, "Identity intake group mismatch")
    group = matching[0]
    native_group = next(g for g in manifest["groups"] if g["group_id"] == group["group_id"])
    run = native_group["selected_runs"][slot["version"]]
    _require(
        group["input_sha256"] == attempt["input_sha256"]
        and run["run_id"] == attempt["run_id"]
        and run["result_ref"]["sha256"] == entry["result_sha256"],
        "Identity intake selected source mismatch",
    )
    evidence = context.read_ref(bundle.get("evidence_ref"), "rtpeval_identity_evidence_1")
    if bundle["mode"] == "legacy":
        reviews = context.read_ref(bundle["reviews_ref"]) if bundle.get("reviews_ref") else None
        audit = context.read_ref(bundle["audit_ref"]) if bundle.get("audit_ref") else None
        identity = resolve_legacy_identities(intake, evidence, reviews, audit).to_dict()
    else:
        _require(
            not bundle.get("reviews_ref") and not bundle.get("audit_ref"),
            "Program identity cannot adopt legacy reviews",
        )
        model_result = (
            context.read_ref(bundle["model_result_ref"]) if bundle.get("model_result_ref") else None
        )
        identity = resolve_identities(intake, evidence, model_result=model_result).to_dict()
    records = [
        record
        for record in identity["records"]
        if record["group_id"] == group["group_id"]
        and record["version"] == slot["version"]
        and record["projection"] == "final"
        and record["kind"] == "primary_visit"
    ]
    associations = [record for record in records if record["resolution"] == "resolved"]
    ids = sorted({record["canonical_place_id"] for record in associations})
    unresolved = any(record["resolution"] != "resolved" for record in records)
    unresolved_roles = any(
        activity["evaluation_role"] == "unresolved"
        for activity in group["runs"][slot["version"]]["final"]["activities"]
    )
    unresolved = unresolved or unresolved_roles
    return {
        "status": "partial" if unresolved else "complete",
        "canonical_ids": ids,
        "observed_count": len(ids),
        "complete_count": None if unresolved else len(ids),
        "reasons": ["unresolved_final_place_association"] if unresolved else [],
        "associations": associations,
        "identity_source_digest": digest(identity),
        "identity_sources": bundle,
    }


def _cross_version(runs):
    grouped = {}
    for row in runs:
        key = (row["case_id"], row["case_revision"], row["repetition_id"])
        grouped.setdefault(key, {})[row["version"]] = row
    comparisons = []
    for key, versions in grouped.items():
        row = dict(zip(("case_id", "case_revision", "repetition_id"), key, strict=True))
        for name in (*STAGES, "scheduled"):
            a, b = versions.get("v1"), versions.get("v2")
            sa = a["scheduled"] if a and name == "scheduled" else a["stages"][name] if a else None
            sb = b["scheduled"] if b and name == "scheduled" else b["stages"][name] if b else None
            complete = (
                sa is not None and sb is not None and sa["status"] == sb["status"] == "complete"
            )
            row[name] = {
                "status": "complete" if complete else "unavailable",
                "v2_added_ids": sorted(set(sb["canonical_ids"]) - set(sa["canonical_ids"]))
                if complete
                else None,
                "v1_only_ids": sorted(set(sa["canonical_ids"]) - set(sb["canonical_ids"]))
                if complete
                else None,
            }
        comparisons.append(row)
    return comparisons
