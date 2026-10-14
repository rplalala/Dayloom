"""Offline producer material collection; staging is never evaluator acceptance."""

import hashlib
import json
import math
from pathlib import Path

VERSIONS = ("v0", "v1", "v2", "v3")


class CollectionError(ValueError):
    """The explicit source selection is unsafe or inconsistent."""


def _json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise CollectionError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    def finite(value):
        number = float(value)
        if not math.isfinite(number):
            raise CollectionError("Nonfinite JSON number")
        return number

    def constant(value):
        raise CollectionError("Nonfinite JSON constant: " + value)

    value = json.loads(
        raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant, parse_float=finite
    )
    if not isinstance(value, dict):
        raise CollectionError("Expected a JSON object")
    return value


def _digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _require(condition, message):
    if not condition:
        raise CollectionError(message)


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _path(root, name, *, owner=None):
    _require(_text(name), "Missing relative source path")
    relative = Path(name)
    _require(
        not relative.is_absolute() and not relative.drive and ":" not in name,
        "Source path must be relative",
    )
    path = ((root if owner is None else owner) / relative).resolve()
    _require(path.is_relative_to(root), "Source path escapes collection root")
    return path


def _completion(declaration, version, policy):
    reasons = []
    if not isinstance(declaration, dict):
        return ["missing_completion_declaration"]
    if not all(_text(declaration.get(k)) for k in ("declared_by", "declared_at")):
        reasons.append("untraceable_completion_declaration")
    if declaration.get("policy_ref") != policy:
        reasons.append("completion_policy_mismatch")
    if declaration.get("workflow_status") != "completed":
        reasons.append("workflow_not_completed")
    mechanisms = declaration.get("required_mechanisms")
    if not isinstance(mechanisms, dict):
        return reasons + ["missing_required_mechanisms"]
    required = {"generation"}
    if version in ("v2", "v3"):
        required.add("retrieval")
    if version == "v3":
        required.update(("validation", "repair"))
    for name in sorted(required | set(mechanisms)):
        allowed = ("completed", "not_applicable") if name == "repair" else ("completed",)
        if mechanisms.get(name) not in allowed:
            reasons.append("required_mechanism_not_completed:" + str(name))
    return reasons


def _assemble(config_path):
    """Prepare a deterministic inventory without writing or executing providers."""
    config_path = Path(config_path).resolve()
    source_root = config_path.parent
    config_raw = config_path.read_bytes()
    config = _json(config_raw)
    if config.get("schema_version") != "rtpeval_collection_1":
        raise CollectionError("Expected rtpeval_collection_1 configuration")
    for key in ("batch_id", "revision", "created_at", "qualification_policy_ref"):
        _require(_text(config.get(key)), "Missing collection " + key)
    _require(
        isinstance(config.get("groups"), list) and config["groups"],
        "Expected explicit nonempty groups",
    )
    files = {"collection-config.json": config_raw}
    bindings = [
        {
            "original_path": str(config_path),
            "staged_path": "collection-config.json",
            "sha256": _digest(config_raw),
        }
    ]
    group_ids, run_ids = set(), set()

    def artifact(ref, schema=None):
        _require(isinstance(ref, dict), "Missing source artifact reference")
        source = _path(source_root, ref.get("path"))
        _require(
            ref.get("media_type") == "application/json" and ref.get("availability") == "available",
            "Required envelope must be available JSON",
        )
        raw = source.read_bytes()
        digest = _digest(raw)
        _require(ref.get("sha256") == digest, "Source hash mismatch: " + source.name)
        value = _json(raw)
        if schema:
            _require(
                value.get("schema_version") == schema and ref.get("schema_version") == schema,
                "Unsupported source schema: " + source.name,
            )
        target = "sources/" + source.relative_to(source_root).as_posix()
        files[target] = raw
        bindings.append({"original_path": str(source), "staged_path": target, "sha256": digest})
        return {**ref, "path": target}, value

    origins, used_origins = {}, set()
    entries = config.get("completion_origins", [])
    _require(isinstance(entries, list), "Completion origins must be an explicit list")
    for entry in entries:
        _require(isinstance(entry, dict), "Invalid completion origin")
        _require(
            all(_text(entry.get(k)) for k in ("group_id", "run_id"))
            and entry.get("version") in VERSIONS,
            "Missing completion origin identity",
        )
        _, selection = artifact(entry.get("selection_ref"))
        _require(
            selection.get("schema_version") == "rtpeval_collection_1", "Invalid origin selection"
        )
        _, completion = artifact(entry.get("completion_ref"))
        selection_path = _path(source_root, entry["selection_ref"]["path"])
        completion_path = _path(source_root, entry["completion_ref"]["path"])
        key = (selection_path, entry["group_id"], entry["version"], entry["run_id"])
        _require(key not in origins, "Duplicate completion origin")
        origins[key] = (completion_path, completion)

    visited = set()

    def selection_dependencies(selection, parent, selection_path):
        """Apply only explicit, exact-native bindings to legacy inline completions."""
        seen_groups, seen_runs = set(), set()
        for key, value in selection.items():
            if key != "groups":
                dependencies(value, parent)
                continue
            _require(isinstance(value, list), "Invalid origin selection groups")
            for group in value:
                _require(isinstance(group, dict), "Invalid origin selection group")
                gid = group.get("group_id")
                _require(_text(gid) and gid not in seen_groups, "Ambiguous origin selection group")
                seen_groups.add(gid)
                for group_key, group_value in group.items():
                    if group_key != "selected_runs":
                        dependencies(group_value, parent)
                        continue
                    _require(isinstance(group_value, dict), "Invalid origin selected runs")
                    for version, run in group_value.items():
                        _require(isinstance(run, dict), "Invalid origin selected run")
                        rid = run.get("run_id")
                        _require(
                            version in VERSIONS and _text(rid) and rid not in seen_runs,
                            "Ambiguous origin selected run",
                        )
                        seen_runs.add(rid)
                        identity = (
                            selection_path,
                            gid,
                            version,
                            rid,
                        )
                        origin = origins.get(identity)
                        for run_key, run_value in run.items():
                            owner = parent
                            if run_key == "completion" and origin:
                                native_path, native_completion = origin
                                _require(
                                    run_value == native_completion,
                                    "Completion origin differs from native declaration",
                                )
                                result_ref = run.get("result_ref")
                                _require(
                                    isinstance(result_ref, dict),
                                    "Completion origin requires a bound result",
                                )
                                result_path = _path(
                                    source_root, result_ref.get("path"), owner=parent
                                )
                                result_raw = result_path.read_bytes()
                                _require(
                                    _digest(result_raw) == result_ref.get("sha256"),
                                    "Completion origin result hash mismatch",
                                )
                                _require(
                                    _json(result_raw).get("system_version") == version,
                                    "Completion origin result version mismatch",
                                )
                                _require(
                                    native_path.parent == result_path.parent,
                                    "Completion origin owner differs from result owner",
                                )
                                owner = native_path.parent
                                used_origins.add(identity)
                            dependencies(run_value, owner)

    def dependencies(value, parent):
        if isinstance(value, dict):
            if "path" in value and "sha256" in value:
                if value.get("availability") == "unavailable":
                    return
                path = _path(source_root, value.get("path"), owner=parent)
                raw = path.read_bytes()
                _require(value["sha256"] == _digest(raw), "Dependency hash mismatch: " + path.name)
                target = "sources/" + path.relative_to(source_root).as_posix()
                files[target] = raw
                bindings.append(
                    {"original_path": str(path), "staged_path": target, "sha256": _digest(raw)}
                )
                if path not in visited:
                    visited.add(path)
                    try:
                        nested = _json(raw)
                    except (ValueError, UnicodeError):
                        nested = None
                    if path in {key[0] for key in origins}:
                        selection_dependencies(nested, path.parent, path)
                    else:
                        dependencies(nested, path.parent)
                return
            for nested in value.values():
                dependencies(nested, parent)
        elif isinstance(value, list):
            for nested in value:
                dependencies(nested, parent)

    groups = []
    for group in config["groups"]:
        _require(isinstance(group, dict) and _text(group.get("group_id")), "Missing group identity")
        gid = group["group_id"]
        _require(gid not in group_ids, "Duplicate group identity")
        group_ids.add(gid)
        input_ref, original = artifact(group.get("input_ref"))
        _require(
            original.get("input_version") == "planning_request_2", "Unsupported original input"
        )
        selected = group.get("selected_runs")
        _require(
            isinstance(selected, dict) and set(selected).issubset(VERSIONS),
            "Selected runs must explicitly name v0-v3",
        )
        runs = {}
        for version, run in selected.items():
            _require(
                isinstance(run, dict) and _text(run.get("run_id")), "Missing selected run identity"
            )
            rid = run["run_id"]
            _require(rid not in run_ids, "Duplicate run identity")
            run_ids.add(rid)
            result_ref, result = (
                artifact(run["result_ref"]) if run.get("result_ref") else (None, None)
            )
            if result:
                _require(result.get("system_version") == version, "Result version mismatch")
            usage_ref, usage = (
                artifact(run["usage_ref"], "rtpeval_usage_1")
                if run.get("usage_ref")
                else (None, None)
            )
            result_hash = result_ref["sha256"] if result_ref else None
            if run.get("provenance_ref"):
                _require("producer_declaration" not in run, "Ambiguous provenance declarations")
                provenance_ref, provenance = artifact(run["provenance_ref"], "rtpeval_provenance_1")
                provenance_parent = _path(source_root, run["provenance_ref"]["path"]).parent
            else:
                provenance = run.get("producer_declaration")
                _require(isinstance(provenance, dict), "Missing explicit provenance declaration")
                _require(
                    provenance.get("schema_version") == "rtpeval_provenance_1"
                    and all(
                        _text(provenance.get(k))
                        for k in ("declared_by", "declared_at", "rationale")
                    ),
                    "Untraceable producer provenance declaration",
                )
                raw = (json.dumps(provenance, indent=2) + "\n").encode("utf-8")
                provenance_parent = (
                    _path(source_root, run["result_ref"]["path"]).parent
                    if result_ref
                    else source_root
                )
                name = provenance_parent.relative_to(source_root) / (
                    "producer-declaration-" + str(len(groups)) + "-" + version + ".json"
                )
                target = "sources/" + name.as_posix()
                _require(
                    not (source_root / name).exists(),
                    "Producer declaration path collides with source",
                )
                files[target] = raw
                provenance_ref = {
                    "path": target,
                    "sha256": _digest(raw),
                    "media_type": "application/json",
                    "availability": "available",
                    "schema_version": "rtpeval_provenance_1",
                }
            dependencies(provenance, provenance_parent)
            _require(
                tuple(
                    provenance.get(k)
                    for k in ("group_id", "run_id", "version", "input_sha256", "result_sha256")
                )
                == (gid, rid, version, input_ref["sha256"], result_hash),
                "Provenance input/result/run association mismatch",
            )
            if usage:
                _require(
                    tuple(usage.get(k) for k in ("group_id", "run_id", "version", "result_sha256"))
                    == (gid, rid, version, result_hash),
                    "Usage/result association mismatch",
                )
                _require(
                    usage.get("collection_status") in ("available", "partial", "unavailable"),
                    "Usage requires explicit collection status",
                )
            completion = run.get("completion")
            reasons = _completion(completion, version, config["qualification_policy_ref"])
            if not result_ref:
                reasons.append("missing_material:result_ref")
            else:
                from backend.evaluation.projection import project
                from backend.evaluation.records import MaterialError

                try:
                    project(
                        result.get("itinerary"),
                        {
                            "batch_id": config["batch_id"],
                            "group_id": gid,
                            "run_id": rid,
                            "artifact_sha256": result_hash,
                        },
                        version=version,
                    )
                except MaterialError:
                    reasons.append("invalid_final_result")
            if not usage_ref:
                reasons.append("missing_material:usage_ref")
            if usage and usage.get("outcome") not in (None, "completed"):
                reasons.append("usage_records_unsuccessful_invocation")
            runs[version] = {
                **run,
                "completion": completion,
                "completion_qualified": not reasons,
                "blocking_reasons": reasons,
                "result_ref": result_ref,
                "usage_ref": usage_ref,
                "provenance_ref": provenance_ref,
            }
        groups.append(
            {
                **group,
                "input_ref": input_ref,
                "selected_runs": runs,
                "missing_versions": [v for v in VERSIONS if v not in runs],
            }
        )
    _require(used_origins == set(origins), "Unused completion origin binding")
    staging = {
        "schema_version": "rtpeval_staging_1",
        "batch_id": config["batch_id"],
        "revision": config["revision"],
        "created_at": config["created_at"],
        "qualification_policy_ref": config["qualification_policy_ref"],
        "groups": groups,
        "source_bindings": bindings,
        "source_config_ref": {
            "path": "collection-config.json",
            "sha256": _digest(config_raw),
            "media_type": "application/json",
            "availability": "available",
            "schema_version": "rtpeval_collection_1",
        },
        "qualified_four_version_batch": False,
        "pending_requirement_review": True,
        "status": "incomplete" if any(g["missing_versions"] for g in groups) else "pending_review",
        "diagnostics": [],
    }
    if any(not r["completion_qualified"] for g in groups for r in g["selected_runs"].values()):
        staging["status"] = "blocked"
    for group in groups:
        group["completion_attested"] = not group["missing_versions"] and all(
            r["completion_qualified"] for r in group["selected_runs"].values()
        )
    staging["artifact_bindings"] = [
        {"path": name, "sha256": _digest(raw)} for name, raw in files.items()
    ]
    return staging, files


def collect(config_path, output_directory):
    """Collect explicit sources into a fresh destination and return staging metadata."""
    output = Path(output_directory).resolve()
    _require(not output.exists(), "Collection destination must be fresh")
    staging, files = _assemble(config_path)
    # Recheck the source snapshot before publishing any material.
    for binding in staging["source_bindings"]:
        _require(
            _digest(Path(binding["original_path"]).read_bytes()) == binding["sha256"],
            "Source drift during collection",
        )
    output.mkdir(parents=True, exist_ok=False)
    for name, raw in files.items():
        path = _path(output, name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    (output / "staging.json").write_text(json.dumps(staging, indent=2) + "\n", encoding="utf-8")
    return staging


def read_staging(staging_path):
    """Verify original/copy hashes and rederive declarations before finalization."""
    path = Path(staging_path).resolve()
    staging = _json(path.read_bytes())
    _require(staging.get("schema_version") == "rtpeval_staging_1", "Expected rtpeval_staging_1")
    bindings = staging.get("source_bindings")
    _require(isinstance(bindings, list) and bindings, "Missing staging source bindings")
    for binding in bindings:
        original = Path(binding["original_path"])
        _require(_digest(original.read_bytes()) == binding["sha256"], "Original source drift")
        copied = _path(path.parent, binding["staged_path"])
        _require(_digest(copied.read_bytes()) == binding["sha256"], "Copied source drift")
    for ref in staging.get("artifact_bindings", []):
        _require(
            _digest(_path(path.parent, ref["path"]).read_bytes()) == ref["sha256"],
            "Staged artifact drift",
        )
    config_binding = next(
        (b for b in bindings if b["staged_path"] == "collection-config.json"), None
    )
    _require(config_binding is not None, "Missing source configuration binding")
    expected, _ = _assemble(config_binding["original_path"])
    _require(staging == expected, "Staging declaration/source mismatch")
    return staging
