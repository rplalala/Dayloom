"""Source-linked adopted V3 edit preparation, separate from independent quality."""

import copy
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .intake import _artifact, _constant, _float, _pairs, _read, load_batch
from .preparation import identity_ready
from .projection import ACTIVITY_FIELDS
from .records import MaterialError, canonical_digest, freeze, require, text, thaw

SOURCE_VERSION = "rtpeval_v3_result_sources_1"
PROVENANCE_VERSION = "rtpeval_v3_edit_provenance_1"
RULES_VERSION = "rtpeval_v3_correspondence_rules_1"


@dataclass(frozen=True)
class V3Correspondence:
    status: str
    data: object

    def to_dict(self):
        return {"status": self.status, **thaw(self.data)}


def _value(value):
    return value.to_dict() if hasattr(value, "to_dict") else thaw(value)


def read_v3_result_sources(intake, manifest_path):
    """Read exact selected result bytes through the existing safe artifact rules."""
    prepared = _value(intake)
    path = Path(manifest_path).resolve()
    require(load_batch(path).to_dict() == prepared, "manifest", "Intake/manifest replay mismatch")
    manifest, _ = _read(path)
    records = []
    for group in manifest["groups"]:
        run = group["selected_runs"]["v3"]
        _, digest = _artifact(path.parent, run["result_ref"])
        result_path = (path.parent / run["result_ref"]["path"]).resolve()
        require(result_path.is_relative_to(path.parent), "result", "Result escaped batch root")
        raw = result_path.read_bytes()
        require(
            hashlib.sha256(raw).hexdigest() == digest, "result", "Result changed during reading"
        )
        records.append(
            {
                "group_id": group["group_id"],
                "run_id": run["run_id"],
                "input_sha256": group["input_ref"]["sha256"],
                "result_sha256": digest,
                "raw_utf8": raw.decode("utf-8"),
            }
        )
    return {
        "schema_version": SOURCE_VERSION,
        "batch_id": prepared["batch_id"],
        "batch_revision": prepared["revision"],
        "records": records,
    }


def _activities(itinerary):
    require(
        isinstance(itinerary, dict) and isinstance(itinerary.get("days"), list),
        "lineage",
        "Itinerary snapshot required",
    )
    output = {}
    for day in itinerary["days"]:
        for raw in day["activities"]:
            aid = raw.get("activity_id")
            require(text(aid) and aid not in output, "lineage", "Missing/duplicate activity ID")
            output[aid] = {
                "declared_day": day["date"],
                "original": {field: raw[field] for field in ACTIVITY_FIELDS if field in raw},
            }
    return output


def _same_state(a, b):
    return _activities(a) == _activities(b) and all(
        a.get(field) == b.get(field)
        for field in ("output_version", "destination", "start_date", "end_date")
    )


def _content(activity):
    """Observable occurrence content, independent of the producer's ID allocation."""
    return [
        activity["declared_day"],
        activity["evaluation_role"],
        {key: value for key, value in activity["original"].items() if key != "activity_id"},
    ]


def _sources(prepared, supplied):
    if supplied is None:
        return {}
    envelope = _value(supplied)
    require(
        envelope.get("schema_version") == SOURCE_VERSION
        and (envelope.get("batch_id"), envelope.get("batch_revision"))
        == (prepared["batch_id"], prepared["revision"]),
        "result_sources",
        "Foreign/stale source envelope",
    )
    groups = {g["group_id"]: g for g in prepared["inventory"]}
    indexed = {}
    for row in envelope["records"]:
        gid = row["group_id"]
        require(
            gid in groups and gid not in indexed, "result_sources", "Foreign/duplicate source group"
        )
        group = groups[gid]
        run = group["runs"]["v3"]
        context = run["final"]["context"]
        require(
            (row["run_id"], row["input_sha256"], row["result_sha256"])
            == (context["run_id"], group["input_sha256"], context["artifact_sha256"]),
            gid,
            "Source association mismatch",
        )
        raw = row["raw_utf8"].encode("utf-8")
        require(
            hashlib.sha256(raw).hexdigest() == row["result_sha256"],
            gid,
            "Source byte hash mismatch",
        )
        result = json.loads(
            row["raw_utf8"], object_pairs_hook=_pairs, parse_constant=_constant, parse_float=_float
        )
        require(result.get("system_version") == "v3", gid, "Selected V3 result required")
        for label, projection in run["optional"].items():
            if projection is not None:
                expected = {
                    a["original"]["activity_id"]: {
                        "declared_day": a["declared_day"],
                        "original": a["original"],
                    }
                    for a in projection["activities"]
                }
                require(_activities(result["v3"][label]) == expected, gid, "Source/stage mismatch")
        indexed[gid] = result
    return indexed


def _adopted_chain(result):
    """Compose adopted occurrence origins, never internal compliance judgments."""
    v3 = result["v3"]
    repair = v3.get("repair")
    if not isinstance(repair, dict):
        return {
            "history": {},
            "origins": {aid: aid for aid in _activities(v3["draft"])},
            "normalizations": _reconcile_final(
                v3["draft"], v3["final_primary"], v3.get("final_places", [])
            ),
            "basis": "validated_unchanged_source_snapshots",
        }
    current = v3["draft"]
    require(_same_state(current, repair["original"]), "lineage", "Repair original/draft mismatch")
    history = {}
    origins = {aid: aid for aid in _activities(current)}
    seen_ids = set(origins)
    from .repair_selection import selected_prefix

    selected = selected_prefix(repair)
    retained = (current, copy.deepcopy(history), dict(origins))
    for number, row in enumerate(repair.get("rounds", []), 1):
        require(
            type(row["round_index"]) is int
            and row["round_index"] == number
            and _same_state(current, row["input_itinerary"]),
            "lineage",
            "Broken ordered round input",
        )
        result = row["result"]
        adopted = row["adopted"]
        require(
            _same_state(current, result["original"]) and _same_state(adopted, result["final"]),
            "lineage",
            "Round result/adopted mismatch",
        )
        before, after = _activities(current), _activities(adopted)
        changed = {aid for aid in before.keys() & after.keys() if before[aid] != after[aid]}
        removed, added = before.keys() - after.keys(), after.keys() - before.keys()

        def event(operation, pointer="adopted", round_index=number):
            return {
                "round_index": round_index,
                "operation": operation,
                "pointer": f"/v3/repair/rounds/{round_index - 1}/{pointer}",
            }

        if result["status"] in ("SKIPPED", "REJECTED"):
            require(
                not changed and not removed and not added,
                "lineage",
                "Rejected round changed adopted activities",
            )
        else:
            require(
                result["status"] in ("ACCEPTED_PARTIAL", "ACCEPTED_COMPLETE"),
                "lineage",
                "Unknown round status",
            )
            edits = _effective_edits(result, before, after)
            consumed, fragments = set(), set()
            for index, adjustment in enumerate(result.get("window_adjustments", [])):
                parent = adjustment["previous_fragment_id"]
                require(
                    parent in removed and parent not in consumed,
                    "lineage",
                    "Invalid consumed fragment",
                )
                root = origins[parent]
                require(adjustment["root_activity_id"] == root, "lineage", "Window root mismatch")
                ids = adjustment["fragment_ids"]
                require(
                    isinstance(ids, list)
                    and len(ids) == len(set(ids))
                    and set(ids) <= added
                    and not (set(ids) & fragments),
                    "lineage",
                    "Invalid/colliding fragments",
                )
                _validate_split(before[parent], [after[aid] for aid in ids], adjustment)
                consumed.add(parent)
                fragments.update(ids)
                for aid in ids:
                    origins[aid] = root
                history.setdefault(root, []).append(
                    event("split", f"result/window_adjustments/{index}")
                )
            for aid in removed - consumed:
                require(
                    any(
                        e.get("activity_id") == aid and e.get("operation") == "delete"
                        for e in edits
                    ),
                    "lineage",
                    "Removal lacks adopted delete support",
                )
                history.setdefault(origins[aid], []).append(event("delete"))
            for aid in changed:
                matching = [
                    e
                    for e in edits
                    if e.get("activity_id") == aid
                    and e.get("operation") in ("retime", "move", "replace")
                ]
                require(
                    len(matching) == 1,
                    "lineage",
                    "Changed activity lacks unique adopted edit support",
                )
                _validate_changed(before[aid], after[aid], matching[0])
                history.setdefault(origins[aid], []).append(event(matching[0]["operation"]))
            remaining = set(added) - fragments
            for proposal in [e for e in edits if e.get("operation") == "add"]:
                matches = [aid for aid in remaining if _addition_matches(after[aid], proposal)]
                require(len(matches) == 1, "lineage", "Addition lacks unique adopted membership")
                aid = matches[0]
                remaining.remove(aid)
                origins[aid] = aid
                history.setdefault(aid, []).append(event("add"))
            require(
                not remaining and not (set(added) & seen_ids),
                "lineage",
                "Unsupported addition/reused allocated ID",
            )
            seen_ids.update(added)
            for aid in removed:
                origins.pop(aid)
        current = adopted
        if selected == number:
            retained = (current, copy.deepcopy(history), dict(origins))
    if selected is not None:
        current, history, origins = retained
    require(_same_state(current, repair["final"]), "lineage", "Cumulative final mismatch")
    normalizations = _reconcile_final(current, v3["final_primary"], v3.get("final_places", []))
    return {"history": history, "origins": origins, "normalizations": normalizations}


def _reconcile_final(adopted, final, places):
    old, new = _activities(adopted), _activities(final)
    require(
        old.keys() == new.keys()
        and all(
            adopted.get(field) == final.get(field)
            for field in ("output_version", "destination", "start_date", "end_date")
        ),
        "lineage",
        "Final normalization membership/header mismatch",
    )
    ledger = {}
    for place in places:
        require(
            isinstance(place, dict)
            and text(place.get("place_id"))
            and text(place.get("name"))
            and place["place_id"] not in ledger,
            "lineage",
            "Invalid final place ledger",
        )
        ledger[place["place_id"]] = place["name"]
    normalizations = []
    for aid in old:
        require(
            old[aid]["declared_day"] == new[aid]["declared_day"],
            "lineage",
            "Final normalization changed date",
        )
        a, b = old[aid]["original"], new[aid]["original"]
        for field in set(a) | set(b):
            if a.get(field) == b.get(field):
                continue
            require(
                field == "place_name"
                and text(a.get("source_place_id"))
                and b.get("place_name") == ledger.get(a["source_place_id"]),
                "lineage",
                "Unexplained final activity change",
            )
            normalizations.append(
                {
                    "kind": "place_name_normalization",
                    "activity_id": aid,
                    "before": a.get(field),
                    "after": b.get(field),
                    "source_pointer": "/v3/final_places",
                }
            )

    def order(value):
        return [raw["activity_id"] for day in value["days"] for raw in day["activities"]]

    if order(adopted) != order(final):
        normalizations.append(
            {"kind": "activity_order", "source_pointer": "/v3/final_primary/days"}
        )
    if adopted.get("transfers", []) != final.get("transfers", []):
        normalizations.append(
            {"kind": "transfer_refresh", "source_pointer": "/v3/final_primary/transfers"}
        )
    return normalizations


def _effective_edits(result, before, after):
    edits = (result.get("effective_patch") or {}).get("edits", [])
    require(isinstance(edits, list), "lineage", "Edit list required")
    components = result.get("components", [])
    if not components:
        return edits
    active, used = [], set()
    for component in components:
        require(
            component["status"]
            in ("accepted", "rejected", "pending", "rolled_back", "not_attempted"),
            "lineage",
            "Unknown component status",
        )
        indices = component["edit_indices"]
        require(
            isinstance(indices, list)
            and all(type(i) is int and 0 <= i < len(edits) for i in indices)
            and len(set(indices)) == len(indices)
            and not (used & set(indices)),
            "lineage",
            "Invalid component edit membership",
        )
        used.update(indices)
        if component["status"] != "accepted":
            continue
        proposal = _activities(component["proposal"])
        for index in indices:
            edit = edits[index]
            aid = edit.get("activity_id")
            if edit["operation"] == "delete":
                require(
                    aid in before and aid not in proposal and aid not in after,
                    "lineage",
                    "Delete proposal/adoption mismatch",
                )
            elif edit["operation"] == "add":
                matches = [
                    key
                    for key in proposal.keys() - before.keys()
                    if _addition_matches(proposal[key], edit)
                ]
                require(
                    len(matches) == 1
                    and matches[0] in after
                    and proposal[matches[0]] == after[matches[0]],
                    "lineage",
                    "Add proposal/adoption mismatch",
                )
            else:
                require(
                    aid in before
                    and aid in proposal
                    and aid in after
                    and proposal[aid] == after[aid],
                    "lineage",
                    "Component proposal/adoption mismatch",
                )
                _validate_changed(before[aid], proposal[aid], edit)
            active.append(edit)
    return active


def _addition_matches(after, proposal):
    raw = after["original"]
    return (
        proposal.get("activity_id") is None
        and text(proposal.get("place_id"))
        and raw.get("source_place_id") == proposal["place_id"]
        and raw.get("activity_kind") == "main_poi"
        and after["declared_day"] == proposal.get("date")
        and all(
            datetime.fromisoformat(raw[field]) == datetime.fromisoformat(proposal[field])
            for field in ("start_time", "end_time")
        )
    )


def _validate_split(before, after, adjustment):
    raw = before["original"]
    require(raw.get("activity_kind") == "free_time", "lineage", "Only free time can split")
    start, end = (datetime.fromisoformat(raw[field]) for field in ("start_time", "end_time"))
    require(
        datetime.fromisoformat(adjustment["authorized_start"])
        <= start
        < end
        <= datetime.fromisoformat(adjustment["authorized_end"]),
        "lineage",
        "Window outside authorization",
    )
    cuts = sorted(
        (datetime.fromisoformat(a), datetime.fromisoformat(b)) for a, b in adjustment["consumed"]
    )
    require(
        bool(cuts) and all(start <= a < b <= end for a, b in cuts),
        "lineage",
        "Invalid consumed intervals",
    )
    pieces, cursor = [], start
    for left, right in cuts:
        if cursor < left:
            pieces.append((cursor, left))
        cursor = max(cursor, right)
    if cursor < end:
        pieces.append((cursor, end))
    observed = sorted(
        (
            datetime.fromisoformat(a["original"]["start_time"]),
            datetime.fromisoformat(a["original"]["end_time"]),
        )
        for a in after
    )
    require(observed == pieces, "lineage", "Fragment complement mismatch")
    for activity in after:
        require(
            activity["declared_day"] == before["declared_day"]
            and all(
                activity["original"].get(field) == raw.get(field)
                for field in (set(raw) | set(activity["original"]))
                - {"activity_id", "start_time", "end_time"}
            ),
            "lineage",
            "Fragment fields changed",
        )


def _validate_changed(before, after, edit):
    operation = edit["operation"]
    require(after["declared_day"] == edit["date"], "lineage", "Adopted edit date mismatch")
    raw = after["original"]
    start, end = (datetime.fromisoformat(edit[field]) for field in ("start_time", "end_time"))
    require(
        start < end
        and all(
            datetime.fromisoformat(raw[field]) == datetime.fromisoformat(edit[field])
            for field in ("start_time", "end_time")
        ),
        "lineage",
        "Adopted edit times mismatch",
    )
    require(
        start.date().isoformat() == edit["date"] == end.date().isoformat(),
        "lineage",
        "Cross-day edit unsupported",
    )
    if operation == "replace":
        require(
            text(edit["place_id"])
            and raw.get("source_place_id") == edit["place_id"]
            and raw.get("activity_kind") == "main_poi",
            "lineage",
            "Replacement place/role mismatch",
        )
    else:
        require(edit.get("place_id") is None, "lineage", "Time edit cannot change place ID")
        fields = set(before["original"]) | set(raw)
        require(
            all(
                before["original"].get(field) == raw.get(field)
                for field in fields - {"start_time", "end_time", "notes"}
            ),
            "lineage",
            "Unsupported time edit fields",
        )
        previous = before["original"].get("notes")
        prefix = (
            "Historical note from the pre-repair activity; not revalidated for this arrangement: "
        )
        allowed_notes = [previous]
        if previous:
            allowed_notes.append(previous if previous.startswith(prefix) else prefix + previous)
        require(raw.get("notes") in allowed_notes, "lineage", "Unsupported historical note rewrite")
        if operation == "retime":
            require(
                before["declared_day"] == after["declared_day"],
                "lineage",
                "Retime changed declared day",
            )


def _relation(before, after, basis, identities, events=()):
    left = [a["source"] for a in before]
    right = [a["source"] for a in after]
    old = [identities.get(a["source"]["record_id"], {}).get("canonical_place_id") for a in before]
    new = [identities.get(a["source"]["record_id"], {}).get("canonical_place_id") for a in after]
    identity_change = (
        "unresolved"
        if None in old + new
        else "same_canonical_venue"
        if old == new
        else "changed_canonical_venue"
    )
    unchanged = (
        len(before) == len(after) == 1
        and before[0]["original"] == after[0]["original"]
        and before[0]["declared_day"] == after[0]["declared_day"]
    )
    return {
        "before": left,
        "after": right,
        "relation": "removed"
        if not after
        else "added"
        if not before
        else "split"
        if len(after) > 1
        else "replaced"
        if any(e["operation"] == "replace" for e in events)
        else "moved"
        if [a["declared_day"] for a in before] != [a["declared_day"] for a in after]
        else "unchanged"
        if unchanged
        else "modified",
        "basis": basis,
        "operations": list(dict.fromkeys(e["operation"] for e in events)),
        "edit_sources": list(events),
        "identity_change": identity_change,
        "dates": {
            "before": [a["declared_day"] for a in before],
            "after": [a["declared_day"] for a in after],
        },
        "roles": {
            "before": [a["evaluation_role"] for a in before],
            "after": [a["evaluation_role"] for a in after],
        },
    }


def prepare_v3_correspondence(
    intake, identity_report, result_sources=None, correspondence_reviews=None, edit_provenance=None
):
    """Prepare deterministic occurrence relations without adopting internal verdicts."""
    prepared, identity = _value(intake), _value(identity_report)
    base = {
        "schema_version": PROVENANCE_VERSION,
        "rules_version": RULES_VERSION,
        "groups": [],
        "diagnostics": [],
    }
    try:
        require(
            prepared.get("status") == "accepted" and identity_ready(prepared, identity),
            "identity",
            "Current linked intake/identity required",
        )
        results = _sources(prepared, result_sources)
        identities = {r["reference_id"]: r for r in identity["records"]}
        for group in prepared["inventory"]:
            run = group["runs"]["v3"]
            row = {
                "group_id": group["group_id"],
                "run_id": run["final"]["context"]["run_id"],
                "result_sha256": run["final"]["context"]["artifact_sha256"],
                "relations": [],
                "normalizations": [],
                "diagnostics": [],
                "unresolved": {"before": [], "after": []},
            }
            if run["paired_available"]:
                before = run["optional"]["draft"]["activities"]
                after = run["optional"]["final_primary"]["activities"]
                history = None
                if group["group_id"] in results:
                    try:
                        history = _adopted_chain(results[group["group_id"]])
                    except (MaterialError, KeyError, TypeError, ValueError) as exc:
                        row["diagnostics"].append(
                            {"reason": "embedded_lineage_unavailable", "explanation": str(exc)}
                        )
                old = {a["original"]["activity_id"]: a for a in before}
                new = {a["original"]["activity_id"]: a for a in after}
                if history is not None:
                    row["normalizations"] = history["normalizations"]
                    origins, events = history["origins"], history["history"]
                    for root in sorted(set(old) | set(origins.values())):
                        parents = [old.pop(root)] if root in old else []
                        descendants = [
                            new.pop(aid) for aid in sorted(origins) if origins[aid] == root
                        ]
                        row["relations"].append(
                            _relation(
                                parents,
                                descendants,
                                history.get("basis", "validated_adopted_lineage"),
                                identities,
                                events.get(root, []),
                            )
                        )

                # Only unique exact content supplies weaker fallback correspondence.
                def signature(a):
                    return canonical_digest(_content(a))

                for aid, activity in list(old.items()):
                    key = signature(activity)
                    matches = [a for a in new.values() if signature(a) == key]
                    peers = [a for a in old.values() if signature(a) == key]
                    if len(matches) == len(peers) == 1:
                        match = matches[0]
                        row["relations"].append(
                            _relation([activity], [match], "unique_unchanged_content", identities)
                        )
                        old.pop(aid)
                        new.pop(match["original"]["activity_id"])

                def canonical(activity):
                    if activity["evaluation_role"] != "primary_visit":
                        return None
                    return identities[activity["source"]["record_id"]]["canonical_place_id"]

                for aid, activity in list(old.items()):
                    pid = canonical(activity)
                    if pid is None:
                        continue
                    peers = [a for a in before if canonical(a) == pid]
                    matches = [a for a in after if canonical(a) == pid]
                    if len(peers) == len(matches) == 1:
                        match = matches[0]
                        if match["original"]["activity_id"] not in new:
                            continue
                        row["relations"].append(
                            _relation(
                                [old.pop(aid)],
                                [new.pop(match["original"]["activity_id"])],
                                "unique_independent_canonical_identity",
                                identities,
                            )
                        )
                row["unresolved"] = {
                    "before": [a["source"] for a in old.values()],
                    "after": [a["source"] for a in new.values()],
                }
            base["groups"].append(row)
        base.update(
            batch_id=prepared["batch_id"],
            batch_revision=prepared["revision"],
            source_hashes={
                "intake": canonical_digest(prepared),
                "identity": canonical_digest(identity),
                "result_sources": canonical_digest(_value(result_sources))
                if result_sources is not None
                else None,
            },
        )
        if edit_provenance is not None:
            replayed = prepare_v3_correspondence(
                intake, identity_report, result_sources, correspondence_reviews
            ).to_dict()
            require(
                _value(edit_provenance) == replayed,
                "edit_provenance",
                "Prepared provenance differs from original-source replay",
            )
        _apply_reviews(prepared, identities, base["groups"], _value(correspondence_reviews))
        base["source_hashes"]["correspondence_reviews"] = (
            canonical_digest(_value(correspondence_reviews))
            if correspondence_reviews is not None
            else None
        )
        for row in base["groups"]:
            run = next(g for g in prepared["inventory"] if g["group_id"] == row["group_id"])[
                "runs"
            ]["v3"]
            row["coverage"] = {}
            for side, stage in (("before", "draft"), ("after", "final_primary")):
                projection = run["optional"].get(stage)
                count = len(projection["activities"]) if projection is not None else None
                unresolved = len(row["unresolved"][side]) if count is not None else None
                row["coverage"][side] = {
                    "occurrence_count": count,
                    "unresolved_count": unresolved,
                    "established_count": count - unresolved if count is not None else None,
                }
            row["review_requests"] = (
                [
                    {
                        "reason": "source_or_review_needed",
                        "before": row["unresolved"]["before"],
                        "after": row["unresolved"]["after"],
                        "diagnostics": row["diagnostics"],
                    }
                ]
                if any(row["unresolved"].values())
                else []
            )
        return V3Correspondence("complete", freeze(base))
    except (MaterialError, ValueError, KeyError, TypeError, OSError) as exc:
        base["groups"] = []
        base["diagnostics"] = [
            exc.diagnostic
            if isinstance(exc, MaterialError)
            else {"reason": "correspondence_material_invalid", "explanation": str(exc)}
        ]
        return V3Correspondence("needs_material_correction", freeze(base))


def _apply_reviews(prepared, identities, rows, envelope):
    if envelope is None:
        return
    require(
        envelope.get("schema_version") == "rtpeval_v3_correspondence_1"
        and (envelope.get("batch_id"), envelope.get("batch_revision"))
        == (prepared["batch_id"], prepared["revision"]),
        "correspondence_reviews",
        "Foreign/stale correspondence reviews",
    )
    groups = {g["group_id"]: g for g in prepared["inventory"]}
    indexed = {row["group_id"]: row for row in rows}
    used = set()
    for review in envelope["records"]:
        gid = review["group_id"]
        require(gid in groups, "correspondence_reviews", "Foreign review group")
        row = indexed[gid]
        require(
            review["run_id"] == row["run_id"] and review["result_sha256"] == row["result_sha256"],
            gid,
            "Stale review run/result",
        )
        require(
            all(text(review.get(field)) for field in ("reviewer_ref", "reviewed_at", "rationale"))
            and datetime.fromisoformat(review["reviewed_at"]).utcoffset() is not None,
            gid,
            "Review provenance required",
        )
        run = groups[gid]["runs"]["v3"]
        require(run["paired_available"], gid, "Review requires both source stages")
        selected = []
        for side, stage in (("before", "draft"), ("after", "final_primary")):
            refs = review[side]
            activities = {a["source"]["record_id"]: a for a in run["optional"][stage]["activities"]}
            require(isinstance(refs, list), gid, "Review source array required")
            matches = []
            for ref in refs:
                sid = ref["record_id"]
                require(
                    sid in activities and ref == activities[sid]["source"] and sid not in used,
                    gid,
                    "Invalid/overlapping review source",
                )
                used.add(sid)
                matches.append(activities[sid])
            selected.append(matches)
        left, right = selected
        relation = review["relation"]
        cardinality = {
            "unchanged": len(left) == len(right) == 1,
            "modified": len(left) == len(right) == 1,
            "moved": len(left) == len(right) == 1,
            "replaced": len(left) == len(right) == 1,
            "split": len(left) == 1 and len(right) > 1,
            "merged": len(left) > 1 and len(right) == 1,
            "complex": bool(left) and bool(right),
            "added": not left and bool(right),
            "removed": bool(left) and not right,
        }
        require(cardinality.get(relation, False), gid, "Review relation/cardinality mismatch")
        if relation == "unchanged":
            require(
                _content(left[0]) == _content(right[0]),
                gid,
                "Unchanged review contradicts observed fields",
            )
        if relation == "moved":
            require(
                left[0]["declared_day"] != right[0]["declared_day"],
                gid,
                "Moved review needs a date change",
            )
        if "supporting_refs" in review:
            require(
                isinstance(review["supporting_refs"], list)
                and all(text(ref) for ref in review["supporting_refs"]),
                gid,
                "Supporting references must be nonempty strings",
            )
        left_ids, right_ids = (
            {a["source"]["record_id"] for a in left},
            {a["source"]["record_id"] for a in right},
        )
        collisions = [
            r
            for r in row["relations"]
            if left_ids & {s["record_id"] for s in r["before"]}
            or right_ids & {s["record_id"] for s in r["after"]}
        ]
        if collisions:
            require(
                len(collisions) == 1
                and left_ids == {s["record_id"] for s in collisions[0]["before"]}
                and right_ids == {s["record_id"] for s in collisions[0]["after"]}
                and relation == collisions[0]["relation"],
                gid,
                "Review contradicts established correspondence",
            )
            collisions[0]["review"] = review
        else:
            record = _relation(left, right, "independent_correspondence_review", identities)
            record.update(relation=relation, review=review)
            row["relations"].append(record)
        for side, ids in (("before", left_ids), ("after", right_ids)):
            row["unresolved"][side] = [
                s for s in row["unresolved"][side] if s["record_id"] not in ids
            ]
