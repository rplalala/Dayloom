"""Selected-version capture with optional explicit, source-bound offline registration."""

import argparse
import copy
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from backend.cli.collection import VERSIONS, CollectionError, _json, _path, _require, _text, collect

PRODUCER_POLICY = "selected_workflow_1"
PRODUCER = "rtpeval.generate/" + PRODUCER_POLICY


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _ref(root, path, schema=None):
    value = {
        "path": Path(os.path.relpath(path, root)).as_posix(),
        "sha256": _sha(path),
        "media_type": "application/json",
        "availability": "available",
    }
    if schema:
        value["schema_version"] = schema
    return value


def _completion(value, version, manifest, now):
    mechanisms = {"generation": "completed" if value is not None else "failed"}
    observations = []
    if version in ("v2", "v3"):
        rag = getattr(value, "rag_discovery", {})
        if version == "v3" and getattr(value, "v3", None) is not None:
            rag = value.v3.original_rag_discovery
        complete = isinstance(rag, dict) and rag.get("status") in ("complete", "empty", "partial")
        complete = complete and not rag.get("cancellation")
        mechanisms["retrieval"] = "completed" if complete else "failed"
        observations.append(
            {
                "mechanism": "retrieval",
                "status": rag.get("status") if isinstance(rag, dict) else None,
            }
        )
    if version == "v3":
        from backend.app.versions.v3.state import V3Outcome

        outcome = getattr(value, "v3", None)
        valid = (
            isinstance(outcome, V3Outcome)
            and outcome.original_report is not None
            and outcome.final_report is not None
        )
        if valid:
            valid = outcome.final_primary.model_dump(
                exclude={"reference_recommendations"}
            ) == value.itinerary.model_dump(exclude={"reference_recommendations"})
        mechanisms["validation"] = "completed" if valid else "failed"
        mechanisms["repair"] = (
            "not_applicable"
            if valid
            and outcome.repair is None
            and outcome.scope is None
            and outcome.reason == "no_authorized_targets"
            else "completed"
            if valid and outcome.repair is not None
            else "failed"
        )
        if valid:
            observations.append(
                {
                    "mechanism": "repair",
                    "status": outcome.repair.status if outcome.repair else "not_applicable",
                    "reason": outcome.reason,
                }
            )
    capture_ok = manifest.get("status") == "completed"
    if not capture_ok:
        mechanisms["generation"] = "failed"
    completed = capture_ok and all(
        status in ("completed", "not_applicable") for status in mechanisms.values()
    )
    return {
        "declared_by": PRODUCER,
        "declared_at": now,
        "policy_ref": PRODUCER_POLICY,
        "producer_policy_ref": PRODUCER_POLICY,
        "workflow_status": "completed"
        if completed
        else manifest.get("status", "failed")
        if not capture_ok
        else "required_mechanism_failed",
        "required_mechanisms": mechanisms,
        "observations": observations,
        "failure_type": manifest.get("failure_type"),
    }


def _pending(group, version, run, now):
    return {
        **run,
        "producer_declaration": {
            "schema_version": "rtpeval_provenance_1",
            "group_id": group["group_id"],
            "run_id": run["run_id"],
            "version": version,
            "input_sha256": group["input_ref"]["sha256"],
            "result_sha256": None,
            "declared_by": PRODUCER,
            "declared_at": now,
            "rationale": "Explicit planned capture slot; no workflow attempt is attested.",
        },
        "completion": {
            "declared_by": PRODUCER,
            "declared_at": now,
            "policy_ref": PRODUCER_POLICY,
            "workflow_status": "not_started",
            "required_mechanisms": {"generation": "not_started"},
        },
    }


def _captured(root, group, version, run, capture, completion, now):
    result_path, usage_path, provenance_path = (
        capture / name for name in ("result.json", "usage.json", "provenance.json")
    )
    result_ref = _ref(root, result_path) if result_path.is_file() else None
    manifest = _json((capture / "manifest.json").read_bytes())
    usage_available = (
        usage_path.is_file()
        and manifest.get("status") != "capture_failed"
        and manifest.get("capture_status") != "capture_failed"
    )
    provenance = (
        _json(provenance_path.read_bytes())
        if provenance_path.is_file()
        else {
            "schema_version": "rtpeval_provenance_1",
            "group_id": group["group_id"],
            "run_id": run["run_id"],
            "version": version,
            "input_sha256": group["input_ref"]["sha256"],
            "result_sha256": result_ref["sha256"] if result_ref else None,
        }
    )
    provenance.update(
        declared_by=PRODUCER,
        declared_at=now,
        rationale="Selected Planner workflow observation; qualification is separate from quality.",
    )
    # A no-result declaration is rooted at the collection root, unlike a native result declaration.
    parent = capture if result_ref else root
    for name, key in (
        ("input.json", "captured_input_ref"),
        ("runtime.yaml", "captured_runtime_config_ref"),
        ("producer-completion.json", "producer_completion_ref"),
        ("manifest.json", "capture_manifest_ref"),
        ("failure.json", "capture_failure_ref"),
        ("provenance.json", "native_provenance_ref"),
    ):
        path = capture / name
        if path.is_file():
            provenance[key] = _ref(parent, path)
            if name == "runtime.yaml":
                provenance[key]["media_type"] = "application/yaml"
    return {
        **run,
        "result_ref": result_ref,
        "usage_ref": _ref(root, usage_path, "rtpeval_usage_1") if usage_available else None,
        "producer_declaration": provenance,
        "completion": completion,
    }


def _registration_selection(selection_path, selection_raw, args, input_path, destination):
    """Check locally decidable selection rules before and after Planner dispatch."""
    root = selection_path.parent
    config = _json(selection_raw)
    if config.get("schema_version") != "rtpeval_collection_1":
        raise CollectionError("Expected rtpeval_collection_1 registration selection")
    for key in ("batch_id", "revision", "created_at", "qualification_policy_ref"):
        _require(_text(config.get(key)), "Missing collection " + key)
    groups = config.get("groups")
    if (
        not isinstance(groups, list)
        or not groups
        or any(
            not isinstance(group, dict)
            or not isinstance(group.get("selected_runs"), dict)
            or any(not isinstance(run, dict) for run in group["selected_runs"].values())
            for group in groups
        )
    ):
        raise CollectionError("Expected explicit groups and selected_runs maps")
    group_ids, run_ids = set(), set()
    for group in groups:
        gid = group.get("group_id")
        _require(_text(gid), "Missing group identity")
        _require(gid not in group_ids, "Duplicate group identity")
        group_ids.add(gid)
        _require(set(group["selected_runs"]).issubset(VERSIONS), "Selected runs must name v0-v3")
        ref = group.get("input_ref")
        _require(isinstance(ref, dict), "Missing original input reference")
        _require(
            ref.get("media_type") == "application/json" and ref.get("availability") == "available",
            "Original input must be available JSON",
        )
        source = _path(root, ref.get("path"))
        _require(_sha(source) == ref.get("sha256"), "Selected original input hash mismatch")
        _require(
            _json(source.read_bytes()).get("input_version") == "planning_request_2",
            "Unsupported original input",
        )
        for run in group["selected_runs"].values():
            rid = run.get("run_id")
            _require(_text(rid), "Missing selected run identity")
            _require(rid not in run_ids, "Duplicate run identity")
            run_ids.add(rid)
            if "capture_directory" in run:
                _path(root, run["capture_directory"])
    output = args.output_directory.resolve()
    selected = [
        (g, v, r)
        for g in config["groups"]
        for v, r in g["selected_runs"].items()
        if g["group_id"] == args.group_id and v == args.version and r["run_id"] == args.run_id
    ]
    if len(selected) != 1:
        raise CollectionError("Generation must match exactly one explicitly selected run")
    group, _, run = selected[0]
    if any(
        run.get(key) is not None
        for key in (
            "result_ref",
            "usage_ref",
            "provenance_ref",
            "producer_declaration",
            "completion",
        )
    ):
        raise CollectionError("Registration refuses replacement of an existing selected capture")
    if _path(root, run.get("capture_directory")) != output:
        raise CollectionError("Selected capture_directory differs from Planner output directory")
    if _sha(input_path) != group["input_ref"]["sha256"]:
        raise CollectionError("Selected original input hash differs from Planner input")
    if selection_path.read_bytes() != selection_raw:
        raise CollectionError("Operator selection changed during Planner invocation")
    if os.path.lexists(destination):
        raise CollectionError("Registration destination must be fresh")
    _require(
        not output.is_relative_to(destination.resolve()),
        "Registration destination contains Planner output",
    )
    return config


def _register(selection_path, selection_raw, args, value, destination):
    root = selection_path.parent
    output = args.output_directory.resolve()
    config = _registration_selection(
        selection_path, selection_raw, args, output / "input.json", destination
    )
    now = datetime.now(UTC).isoformat()
    manifest = _json((output / "manifest.json").read_bytes())
    completion = _completion(value, args.version, manifest, now)
    selection_snapshot = root / ("generation-selection-" + uuid4().hex + ".json")
    selection_snapshot.write_bytes(selection_raw)
    completion["operator_selection_ref"] = _ref(output, selection_snapshot)
    completion["operator_config_ref"] = _ref(output, selection_path)
    (output / "operator-selection.json").write_bytes(selection_raw)
    _save(output / "producer-completion.json", completion)
    resolved = copy.deepcopy(config)
    for g in resolved["groups"]:
        for version, planned in list(g["selected_runs"].items()):
            if "capture_directory" not in planned:
                continue
            capture = _path(root, planned["capture_directory"])
            if g["group_id"] == args.group_id and version == args.version:
                declaration = completion
            elif capture.exists():
                declaration = _json((capture / "producer-completion.json").read_bytes())
            else:
                g["selected_runs"][version] = _pending(g, version, planned, now)
                continue
            g["selected_runs"][version] = _captured(
                root, g, version, planned, capture, declaration, now
            )
    config_path = root / ("generation-collection-" + uuid4().hex + ".json")
    _save(config_path, resolved)
    return collect(config_path, destination)


def main(argv=None, *, runtime=None, date_provider=None):
    from backend.evaluation.tools.planner_usage_cli import main as native

    options = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    options.add_argument("--register-batch", type=Path)
    options.add_argument("--registration-directory", type=Path)
    args, forwarded = options.parse_known_args(argv)
    if (args.register_batch is None) != (args.registration_directory is None):
        options.error("--register-batch and --registration-directory must be supplied together")
    if "--help" in forwarded or "-h" in forwarded:
        if args.register_batch:
            options.error("Registration is an explicit execution option")
        print(
            "Optional registration: --register-batch CONFIG "
            "--registration-directory FRESH_DIRECTORY"
        )
        return native(forwarded, runtime=runtime, date_provider=date_provider)
    if args.register_batch is None:
        return native(forwarded, runtime=runtime, date_provider=date_provider)
    invocation = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    invocation.add_argument("--version")
    invocation.add_argument("--group-id")
    invocation.add_argument("--run-id")
    invocation.add_argument("--output-directory", type=Path)
    invocation.add_argument("--input-json", type=Path)
    invocation.add_argument("--execute", action="store_true")
    selected, _ = invocation.parse_known_args(forwarded)
    if not selected.execute:
        options.error("Registration requires --execute; preparation remains offline")
    selection_path = args.register_batch.resolve()
    try:
        selection_raw = selection_path.read_bytes()
        _registration_selection(
            selection_path,
            selection_raw,
            selected,
            selected.input_json,
            args.registration_directory,
        )
    except (
        CollectionError,
        OSError,
        ValueError,
        KeyError,
        TypeError,
        AttributeError,
        RecursionError,
    ) as exc:
        print(
            json.dumps(
                {
                    "schema_version": "rtpeval_generation_registration_1",
                    "planner": {"status": "not_invoked"},
                    "registration": {"status": "failed", "diagnostics": [str(exc)]},
                }
            )
        )
        return 2
    observed = []
    planner_exit = native(
        forwarded, runtime=runtime, date_provider=date_provider, result_observer=observed.append
    )
    output = selected.output_directory.resolve()
    manifest = _json((output / "manifest.json").read_bytes())
    report = {
        "schema_version": "rtpeval_generation_registration_1",
        "planner": {
            "status": manifest["status"],
            "exit_code": planner_exit,
            "output_directory": str(output),
        },
        "registration": {"status": "failed"},
    }
    try:
        staging = _register(
            selection_path,
            selection_raw,
            selected,
            observed[-1] if observed else None,
            args.registration_directory,
        )
        report["registration"] = {
            "status": staging["status"],
            "directory": str(args.registration_directory.resolve()),
            "pending_requirement_review": True,
            "blocking_reasons": [
                reason
                for group in staging["groups"]
                for run in group["selected_runs"].values()
                for reason in run["blocking_reasons"]
            ],
        }
    except (CollectionError, OSError, ValueError, KeyError, TypeError, RecursionError) as exc:
        report["registration"]["diagnostics"] = [str(exc)]
    _save(output / "generation-registration.json", report)
    print(json.dumps(report))
    return (
        planner_exit if planner_exit else 2 if report["registration"]["status"] == "failed" else 0
    )
