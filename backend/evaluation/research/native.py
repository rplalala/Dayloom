"""Rebuild native offline reports from exact selected source artifacts."""

from backend.cli.collection import _path, _require
from backend.evaluation.intake import load_batch
from backend.evaluation.quality_report import build_quality_report, quality_content_hash
from backend.evaluation.records import canonical_digest
from backend.evaluation.snapshot import SNAPSHOT_VERSION, load_snapshot
from backend.evaluation.v3_correspondence import read_v3_result_sources
from backend.evaluation.v3_pair_report import build_v3_pair_report, pair_content_hash

COMMON = (
    "schedule_context",
    "occupancy_reviews",
    "route_reviews",
    "coordinate_evidence",
    "expected_plan",
    "density_reviews",
)
PAIR = ("correspondence_reviews", "edit_provenance")
CLI_NAMES = {"schedule_context": "context", "coordinate_evidence": "coordinates"}


def path_ref(context, ref, schema=None):
    value = context.read_ref(ref, schema)
    return value, _path(context.root, ref["path"])


def relative_ref(context, directory, ref):
    """Translate a native directory-relative reference into the declaration root."""
    _require(isinstance(ref, dict), "Native artifact reference required")
    path = _path(directory, ref.get("path"))
    _require(path.is_relative_to(context.root), "Native source escapes research root")
    return {**ref, "path": path.relative_to(context.root).as_posix()}


def snapshot_directory(context, ref):
    value, path = path_ref(context, ref, SNAPSHOT_VERSION)
    _require(path.name == "manifest.json", "Snapshot reference must name manifest.json")
    snapshot = load_snapshot(path.parent)
    _require(value == snapshot, "Snapshot changed during native read")
    for record in snapshot["records"]:
        for attempt in record["attempts"]:
            raw = attempt["raw"]
            if raw is not None:
                context.sources.read_bytes(
                    relative_ref(
                        context,
                        path.parent,
                        {
                            **raw,
                            "availability": "available",
                            "media_type": "application/octet-stream",
                        },
                    )
                )
    return path.parent


def selected_groups(context, descriptor):
    """Load a native batch and bind every native run to its declared first attempt."""
    manifest, path = path_ref(context, descriptor["manifest_ref"], "rtpeval_batch_1")
    intake = load_batch(path)
    _require(intake.status == "accepted", "Native intake requires material correction")
    for group in manifest["groups"]:
        for field in ("input_ref", "requirement_spec_ref"):
            context.read_ref(relative_ref(context, path.parent, group[field]))
        for run in group["selected_runs"].values():
            for field in ("result_ref", "usage_ref", "provenance_ref"):
                context.read_ref(relative_ref(context, path.parent, run[field]))
    if manifest.get("projection_reviews_ref") is not None:
        context.read_ref(relative_ref(context, path.parent, manifest["projection_reviews_ref"]))
    _require(context.read_ref(descriptor["manifest_ref"]) == manifest, "Native manifest changed")
    selected = {a["run_id"]: a for a in context.selected_attempts.values() if a is not None}
    groups = {}
    manifest_groups = {group["group_id"]: group for group in manifest["groups"]}
    for group in intake.to_dict()["inventory"]:
        attempts = {}
        keys = set()
        for version, run in group["runs"].items():
            projection = run["final"]["context"]
            attempt = selected.get(projection["run_id"])
            _require(
                attempt is not None and attempt["status"] == "completed",
                "Native run is not a completed selected first attempt",
            )
            _require(
                attempt["version"] == version
                and attempt.get("group_id") == group["group_id"]
                and attempt["input_sha256"] == group["input_sha256"]
                and (attempt.get("result_ref") or {}).get("sha256")
                == projection["artifact_sha256"],
                "Foreign native selected run/input/result binding",
            )
            original = manifest_groups[group["group_id"]]["selected_runs"][version]
            _require(
                all(
                    (attempt.get(field) or {}).get("sha256") == original[field]["sha256"]
                    for field in ("usage_ref", "provenance_ref")
                    if attempt.get(field) is not None
                ),
                "Foreign native selected usage/provenance binding",
            )
            keys.add(tuple(attempt[k] for k in ("case_id", "case_revision", "repetition_id")))
            attempts[version] = attempt
        _require(len(keys) == 1, "Native group combines different research requests/repetitions")
        key = keys.pop()
        _require(key not in groups, "Duplicate native research request/repetition")
        groups[key] = {"intake_group": group, "attempts": attempts}
    return intake, path, groups


def _rebuild(context, descriptor, kind):
    options = COMMON + (PAIR if kind == "pair" else ("opening_judgment",))
    allowed = {
        "manifest_ref",
        "report_ref",
        "identity_ref",
        "snapshot_ref",
        "identity_snapshot_ref",
        *(name + "_ref" for name in options),
    }
    _require(
        isinstance(descriptor, dict) and set(descriptor) <= allowed,
        "Unknown native report material fields",
    )
    intake, manifest_path, _ = selected_groups(context, descriptor)
    schema = "rtpeval_quality_report_2" if kind == "quality" else "rtpeval_v3_pair_report_2"
    saved = context.read_ref(descriptor["report_ref"], schema)
    hasher = quality_content_hash if kind == "quality" else pair_content_hash
    _require(saved.get("status") == "complete", "Complete native report required")
    _require(saved.get("content_hash") == hasher(saved), "Native report content hash mismatch")
    identity = context.read_ref(descriptor["identity_ref"], "rtpeval_identity_1")
    directory = (
        snapshot_directory(context, descriptor["snapshot_ref"])
        if descriptor.get("snapshot_ref")
        else None
    )
    values = {
        name: context.read_ref(descriptor[name + "_ref"]) if descriptor.get(name + "_ref") else None
        for name in options
    }
    if descriptor.get("identity_snapshot_ref"):
        values["identity_snapshot_directory"] = snapshot_directory(
            context, descriptor["identity_snapshot_ref"]
        )
    if kind == "pair":
        rebuilt = build_v3_pair_report(
            intake,
            identity,
            directory,
            **values,
            result_sources=read_v3_result_sources(intake, manifest_path),
            generated_at=saved["generated_at"],
        ).to_dict()
    else:
        _require(directory is not None, "Final quality snapshot required")
        rebuilt = build_quality_report(
            intake,
            identity,
            directory,
            **values,
            generated_at=saved["generated_at"],
        ).to_dict()
    _require(
        rebuilt["status"] == "complete",
        "Native replay requires material correction: " + str(rebuilt.get("diagnostics")),
    )
    metadata = saved.get("preparation_file_sha256")
    if metadata is not None:
        expected = {"identity": descriptor["identity_ref"]["sha256"]}
        expected.update(
            {
                CLI_NAMES.get(name, name): (descriptor.get(name + "_ref") or {}).get("sha256")
                for name in options
            }
        )
        _require(metadata == expected, "Native CLI preparation file hashes mismatch")
        rebuilt["preparation_file_sha256"] = metadata
        rebuilt["content_hash"] = hasher(rebuilt)
    _require(saved == rebuilt, "Saved native report differs from source replay")
    return saved


def read_quality(context, descriptor):
    """Return the unchanged native final-quality report after offline source replay."""
    return _rebuild(context, descriptor, "quality")


def read_pair(context, descriptor):
    """Return the unchanged native draft/final-primary report after offline source replay."""
    return _rebuild(context, descriptor, "pair")


def quality_rows(context, descriptors):
    """Index exact first-attempt native groups by case/revision/repetition."""
    _require(isinstance(descriptors, list), "Native quality descriptors must be an array")
    rows = {}
    for descriptor in descriptors:
        report = read_quality(context, descriptor)
        _, _, bindings = selected_groups(context, descriptor)
        native = {group["group_id"]: group for group in report["groups"]}
        for key, binding in bindings.items():
            gid = binding["intake_group"]["group_id"]
            _require(key not in rows and gid in native, "Duplicate or missing native quality group")
            rows[key] = {"report": report, "group": native[gid], "attempts": binding["attempts"]}
    return rows


def read_mechanism(context, descriptor):
    """Replay an optional mechanism view; internal adoption remains observational."""
    from backend.evaluation.mechanism_preparation import read_batch_sources
    from backend.evaluation.mechanism_report import report_mechanism

    _require(set(descriptor) <= {"manifest_ref", "report_ref"}, "Unknown mechanism descriptor")
    _, path, _ = selected_groups(context, descriptor)
    saved = context.read_ref(descriptor["report_ref"], "rtpeval_mechanism_report_1")
    rebuilt = report_mechanism(read_batch_sources(path))
    _require(
        saved == rebuilt and rebuilt["status"] == "complete",
        "Saved native mechanism report differs from source replay",
    )
    _require(
        saved.get("content_hash")
        == canonical_digest({k: v for k, v in saved.items() if k != "content_hash"}),
        "Native mechanism content hash mismatch",
    )
    return saved
