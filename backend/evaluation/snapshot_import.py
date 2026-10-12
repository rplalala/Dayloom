"""Offline, source-labelled observation imports; never acquire or copy judgments."""

import copy
import hashlib
from datetime import UTC, datetime
from pathlib import Path

from .intake import _read
from .snapshot import _bytes, _decode, _hash, _utc_time, _validate_plan

IMPORTED_VERSION = "rtpeval_imported_snapshot_1"
ZERO_LEDGER = {
    "namespace": "oracle",
    "actual_sends": 0,
    "retry_sends": 0,
    "requested_matrix_elements": 0,
}


def _inventory(root):
    from .paired_run import file_inventory

    return file_inventory(root)


def _safe(root, name):
    relative = Path(name)
    path = (root / relative).resolve()
    if relative.is_absolute() or relative.drive or not path.is_relative_to(root.resolve()):
        raise ValueError("Imported source path escapes root")
    return path


def _primary(root, source, plan, phase):
    """Replay copied closed provider receipts without requiring the original filesystem."""
    from .evaluation_transport import google_wire, usage_event
    from .records import canonical_digest
    from .snapshot import SNAPSHOT_VERSION, _validate_acquired_snapshot

    def raw(name):
        return _safe(root, source["files"][name.replace("\\", "/")]["path"]).read_bytes()

    def read(name):
        return _decode(raw(name))

    preparation = read("preparation.json")
    unsigned = {k: v for k, v in preparation.items() if k != "content_sha256"}
    if (
        canonical_digest(unsigned) != preparation["content_sha256"]
        or preparation["scope"] != "four_final_automatic_quality"
        or _hash(preparation["intake"]) != plan["intake_hash"]
    ):
        raise ValueError("Primary source intake/preparation mismatch")
    receipt = read("execution/receipt.json")
    execution_files = {
        name.removeprefix("execution/"): ref["sha256"]
        for name, ref in source["files"].items()
        if name.startswith("execution/") and name != "execution/receipt.json"
    }
    normalized_receipt = {
        **receipt,
        "files": {name.replace("\\", "/"): sha for name, sha in receipt["files"].items()},
    }
    if normalized_receipt != {
        "preparation_sha256": preparation["content_sha256"],
        "files": execution_files,
    }:
        raise ValueError("Imported primary closed receipt mismatch")
    report = read("execution/report.json")
    if report["processing_status"] != "complete":
        raise ValueError("Completed primary evaluation required for reuse")
    usage = read("execution/usage.json")
    journal = [
        read(name)
        for name in sorted(
            (n for n in source["files"] if n.startswith("execution/http/") and n.endswith(".json")),
            key=lambda n: int(Path(n).stem),
        )
    ]
    if [usage_event(e) for e in journal] != usage["provider_events"]:
        raise ValueError("Primary source HTTP/usage mismatch")
    snapshot_base = "execution/" + phase + "-snapshot/"
    snapshot = read(snapshot_base + "manifest.json")
    if snapshot["schema_version"] != SNAPSHOT_VERSION:
        raise ValueError("Native primary acquisition snapshot required")
    _validate_acquired_snapshot(snapshot, lambda name: raw(snapshot_base + name))
    if snapshot["plan"]["paired"] or snapshot["plan"]["intake_hash"] != plan["intake_hash"]:
        raise ValueError("Primary source snapshot intake mismatch")
    requests = {r["key"]: r for r in snapshot["plan"]["requests"]}
    candidates = []
    for row in snapshot["records"]:
        if not row["attempts"]:
            continue
        request = requests[row["key"]]
        attempt = row["attempts"][-1]
        events = [
            e
            for e in journal
            if e["provider"] == "google"
            and e.get("request_key") == row["key"]
            and attempt["requested_at"] <= e["requested_at"] <= attempt["retrieved_at"]
        ]
        if len(events) != 1:
            raise ValueError("Primary observation requires a single closed HTTP receipt")
        event = events[0]
        if (
            event["request"] != google_wire(request)
            or event.get("status_code") != attempt["status_code"]
            or not attempt["requested_at"]
            <= event["requested_at"]
            <= event.get("retrieved_at", attempt["retrieved_at"])
            <= attempt["retrieved_at"]
        ):
            raise ValueError("Primary source request/time mismatch")
        if attempt["raw"]:
            observed = raw(snapshot_base + attempt["raw"]["path"])
            if observed != raw("execution/http/" + event["event_id"] + ".bin"):
                raise ValueError("Primary source response mismatch")
        candidates.append(
            {
                "request": request,
                "attempt": attempt,
                "summary": row["summary"],
                "raw_path": source["files"][
                    (snapshot_base + attempt["raw"]["path"]).replace("\\", "/")
                ]["path"]
                if attempt["raw"]
                else None,
                "origin": {
                    "kind": "primary_evaluation",
                    "source_phase": phase,
                    "request_key": row["key"],
                    "http_event_id": event["event_id"],
                    "observation_time_basis": "per_request_utc",
                },
            }
        )
    return candidates, {
        "kind": "primary_evaluation",
        "usage_sha256": hashlib.sha256(raw("execution/usage.json")).hexdigest(),
        "attribution": "inherited_source_only",
        "charged_in_current_phase": False,
        "actual_source_google_sends": sum(e["provider"] == "google" for e in journal),
    }


def _same_request(source, target):
    """Match route semantics while keeping each validated coordinate lineage separately."""
    if source == target:
        return True
    if source["operation"] != "route_matrix" or target["operation"] != "route_matrix":
        return False

    def parameters(request):
        value = copy.deepcopy(request["parameters"])
        for endpoint in ("origin", "destination"):
            value[endpoint].pop("evidence_sha256")
        return value

    return parameters(source) == parameters(target)


def _derive(root, plan, sources, intake):
    observations, inherited = [], []
    for source in sources:
        path = _safe(root, source["path"])
        expected_files = {ref["path"]: ref["sha256"] for ref in source["files"].values()}
        if len(expected_files) != len(source["files"]) or _inventory(path) != expected_files:
            raise ValueError("Imported source file inventory/hash mismatch")
        if source["kind"] == "primary_evaluation":
            rows, usage = _primary(path, source, plan, plan["phase"])
            other_phase = "evidence" if plan["phase"] == "identity" else "identity"
            previous, _ = _primary(path, source, plan, other_phase)
            rows.extend(previous)
        elif source["kind"] == "planner_generation":
            from .generation_import import generation_observations

            rows, usage = generation_observations(
                lambda name, path=path, source=source: _safe(
                    path, source["files"][name]["path"]
                ).read_bytes(),
                source,
                plan,
                intake,
            )
        else:
            raise ValueError("Unsupported import source kind")
        observations.extend((source, row) for row in rows)
        inherited.append({**usage, "source_path": source["path"]})
    records = []
    for request in plan["requests"]:
        matches = [(s, r) for s, r in observations if _same_request(r["request"], request)]
        chosen = next(
            ((s, r) for s, r in matches if r["summary"]["status"] == "available"),
            matches[0] if matches else None,
        )
        if chosen is None:
            records.append(
                {
                    "key": request["key"],
                    "attempts": [],
                    "origin": None,
                    "summary": {"status": "unavailable", "reason": "no_compatible_observation"},
                }
            )
            continue
        source, row = chosen
        attempt = copy.deepcopy(row["attempt"])
        if attempt["raw"]:
            attempt["raw"]["path"] = (Path(source["path"]) / row["raw_path"]).as_posix()
        records.append(
            {
                "key": request["key"],
                "attempts": [attempt],
                "origin": {
                    **row["origin"],
                    "source_path": source["path"],
                    "source_files_sha256": _hash(source["files"]),
                },
                "summary": row["summary"],
            }
        )
    return records, inherited


def import_snapshot(plan, directory, *, intake, primary_runs=(), generations=()):
    """Import matching provider observations into a fresh zero-send paired snapshot."""
    from .evaluation_run import replay_run

    _validate_plan(plan)
    if not plan["paired"] or plan["intake_hash"] != _hash(intake):
        raise ValueError("Paired import intake mismatch")
    root = Path(directory).resolve()
    if root.exists():
        raise ValueError("Fresh import directory required")
    paths = [("primary_evaluation", Path(p).resolve()) for p in primary_runs]
    paths += [("planner_generation", Path(p).resolve()) for p in generations]
    if len({path for _, path in paths}) != len(paths):
        raise ValueError("Duplicate import source")
    for kind, path in paths:
        if root.is_relative_to(path):
            raise ValueError("Import destination must be outside source")
        if kind == "primary_evaluation":
            replay_run(path)
    root.mkdir(parents=True, exist_ok=False)
    sources = []
    for index, (kind, path) in enumerate(paths):
        before = _inventory(path)
        name = "s" + str(index)
        destination = root / name
        destination.mkdir()
        files = {}
        for number, (original, sha) in enumerate(sorted(before.items())):
            copied = str(number)
            (destination / copied).write_bytes(_safe(path, original).read_bytes())
            files[original.replace("\\", "/")] = {"path": copied, "sha256": sha}
        if _inventory(path) != before:
            raise ValueError("Primary source changed during import")
        sources.append({"kind": kind, "path": name, "files": files})
    records, inherited = _derive(root, plan, sources, intake)
    value = {
        "schema_version": IMPORTED_VERSION,
        "imported_at": datetime.now(UTC).isoformat(),
        "plan": plan,
        "plan_hash": _hash(plan),
        "intake": intake,
        "records": records,
        "ledger": ZERO_LEDGER,
        "inherited_usage": inherited,
        "sources": sources,
    }
    (root / "manifest.json").write_bytes(_bytes(value))
    receipt = {
        "schema_version": "rtpeval_snapshot_import_receipt_1",
        "manifest_sha256": _hash(value),
        "files": _inventory(root),
        "current_sends": 0,
    }
    (root / "import-receipt.json").write_bytes(_bytes(receipt))
    return load_imported_snapshot(root, expected_plan=plan)


def load_imported_snapshot(directory, expected_plan=None):
    """Replay provenance, full source hashes, matching requests and derived summaries."""
    root = Path(directory).resolve()
    value = _read(root / "manifest.json")[0]
    imported_at = _utc_time(value["imported_at"])
    plan = value["plan"]
    _validate_plan(plan)
    if (
        value["schema_version"] != IMPORTED_VERSION
        or not plan["paired"]
        or value["plan_hash"] != _hash(plan)
        or plan["intake_hash"] != _hash(value["intake"])
        or expected_plan is not None
        and plan != expected_plan
    ):
        raise ValueError("Imported snapshot plan mismatch")
    receipt = _read(root / "import-receipt.json")[0]
    files = _inventory(root)
    files.pop("import-receipt.json", None)
    if receipt != {
        "schema_version": "rtpeval_snapshot_import_receipt_1",
        "manifest_sha256": _hash(value),
        "files": files,
        "current_sends": 0,
    }:
        raise ValueError("Imported snapshot receipt mismatch")
    records, inherited = _derive(root, plan, value["sources"], value["intake"])
    if (
        value["ledger"] != ZERO_LEDGER
        or value["inherited_usage"] != inherited
        or value["records"] != records
    ):
        raise ValueError("Imported snapshot derived evidence/usage mismatch")
    for row in records:
        for attempt in row["attempts"]:
            if (
                not _utc_time(attempt["requested_at"])
                <= _utc_time(attempt["retrieved_at"])
                <= imported_at
            ):
                raise ValueError("Imported observation time mismatch")
    return value


def import_pair(manifest, directory, *, context, primary_runs=(), generations=()):
    """Prepare both phases for cached native paired reporting, without network access."""
    from .identity_program import resolve_versioned_identities
    from .intake import load_batch
    from .paired_run import fresh, routes, save, validate_context, write_receipt
    from .snapshot import build_identity_plan, identity_evidence

    root = fresh(directory)
    intake = load_batch(manifest).to_dict()
    if intake["status"] != "accepted":
        raise ValueError("Qualified import manifest required")
    validate_context(intake, context)
    plan = build_identity_plan(intake, paired=True)
    identity_snapshot = import_snapshot(
        plan,
        root / "identity-snapshot",
        intake=intake,
        primary_runs=primary_runs,
        generations=generations,
    )
    identity = resolve_versioned_identities(intake, identity_evidence(identity_snapshot)).to_dict()
    route = routes(intake, identity, context, root / "identity-snapshot")
    import_snapshot(
        route["evidence_plan"],
        root / "evidence-snapshot",
        intake=intake,
        primary_runs=primary_runs,
        generations=generations,
    )
    if load_batch(manifest).to_dict() != intake:
        raise ValueError("Original paired source changed during import")
    save(root, "identity-plan.json", plan)
    save(root, "identity-report.json", identity)
    save(root, "evidence-plan.json", route["evidence_plan"])
    value = {
        "schema_version": "rtpeval_pair_import_1",
        "processing_status": "complete",
        "current_sends": 0,
        "identity_snapshot": "identity-snapshot",
        "snapshot": "evidence-snapshot",
    }
    save(root, "handoff.json", value)
    write_receipt(root, _hash(value))
    return value
