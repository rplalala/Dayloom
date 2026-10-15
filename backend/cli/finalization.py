"""Offline source-bound RequirementSpec attachment and native-gated finalization."""

import json
from datetime import datetime
from pathlib import Path

from backend.cli.collection import (
    VERSIONS,
    CollectionError,
    _digest,
    _json,
    _path,
    _require,
    _text,
    read_staging,
)

EXCLUDED_CONTEXT = {"planner_interpretation", "generated_outputs", "scores", "mechanisms"}


def _timestamp(value):
    _require(_text(value), "Missing external-agent execution time")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    _require(parsed.utcoffset() is not None, "External-agent time requires UTC offset")
    return parsed


def _handoff(staging, handoff_path):
    path = Path(handoff_path).resolve()
    root = path.parent
    raw = path.read_bytes()
    value = _json(raw)
    _require(
        value.get("schema_version") == "rtpeval_requirement_handoff_1", "Invalid handoff schema"
    )
    _require(value.get("batch_id") == staging["batch_id"], "Handoff batch mismatch")
    groups = value.get("groups")
    _require(isinstance(groups, list), "Missing handoff groups")
    _require(
        all(isinstance(g, dict) for g in groups)
        and [g.get("group_id") for g in groups] == [g["group_id"] for g in staging["groups"]],
        "Handoff groups must match explicit staging membership and order",
    )
    files = {"requirement-handoff.json": raw}
    bindings = [
        {"original_path": str(path), "path": "requirement-handoff.json", "sha256": _digest(raw)}
    ]
    visited = set()

    def capture(ref, parent=root, schema=None, json_required=True):
        _require(isinstance(ref, dict), "Missing handoff artifact reference")
        source = _path(root, (parent.relative_to(root) / ref.get("path", "")).as_posix())
        _require(ref.get("availability") == "available", "Handoff evidence must be available")
        if json_required:
            _require(ref.get("media_type") == "application/json", "Handoff artifact must be JSON")
        data = source.read_bytes()
        _require(ref.get("sha256") == _digest(data), "Handoff artifact hash mismatch")
        name = "requirements/" + source.relative_to(root).as_posix()
        _require(name not in files or files[name] == data, "Conflicting handoff artifact")
        files[name] = data
        binding = {"original_path": str(source), "path": name, "sha256": _digest(data)}
        if binding not in bindings:
            bindings.append(binding)
        parsed = None
        if json_required or ref.get("media_type") == "application/json":
            parsed = _json(data)
        if schema:
            _require(
                ref.get("schema_version") == schema and parsed.get("schema_version") == schema,
                "Handoff artifact schema mismatch",
            )
        if source not in visited:
            visited.add(source)
            dependencies(parsed, source.parent)
        return {**ref, "path": name}, parsed

    def dependencies(item, parent):
        if isinstance(item, dict):
            if "path" in item and "sha256" in item:
                _require(item.get("availability") != "unavailable", "Unavailable handoff evidence")
                capture(item, parent, json_required=False)
                return
            for key, child in item.items():
                # This is an exact execution snapshot, whose refs belong to the separately
                # verified execution artifact directory, not the transcript directory.
                if (
                    item.get("schema_version") == "rtpeval_requirement_agent_transcript_1"
                    and key == "execution"
                ):
                    continue
                dependencies(child, parent)
        elif isinstance(item, list):
            for child in item:
                dependencies(child, parent)

    specifications = []
    for group, staged in zip(groups, staging["groups"], strict=True):
        _, original = capture(group.get("input_ref"))
        _require(
            group["input_ref"]["sha256"] == staged["input_ref"]["sha256"],
            "Handoff original input mismatch",
        )
        spec_ref, spec = capture(group.get("requirement_spec_ref"), schema="rtpeval_requirements_1")
        from backend.evaluation.intake import _requirements
        from backend.evaluation.records import MaterialError

        try:
            _requirements(spec, staged["group_id"], staged["input_ref"]["sha256"], original)
        except MaterialError as exc:
            raise CollectionError(str(exc.diagnostic)) from exc
        authored_ref, authored = capture(
            group.get("authored_requirement_spec_ref", group["requirement_spec_ref"]),
            schema="rtpeval_requirements_1",
        )
        _require(
            authored.get("group_id") == staged["group_id"]
            and authored.get("input_sha256") == staged["input_ref"]["sha256"],
            "Authored RequirementSpec original source/group mismatch",
        )
        records = []
        for operation in ("authoring", "review"):
            ref = group.get(operation + "_ref")
            _, record = capture(ref, schema="rtpeval_requirement_agent_execution_1")
            _require(
                record.get("operation") == operation
                and record.get("origin") == "external_codex"
                and _text(record.get("actor_ref"))
                and _text(record.get("execution_id")),
                "Missing external Codex origin or execution identity",
            )
            configuration = record.get("configuration")
            _require(
                isinstance(configuration, dict)
                and all(
                    configuration.get(key) == expected
                    for key, expected in {
                        "agent": "Codex",
                        "model": "gpt-6.1-sol",
                        "reasoning_effort": "high",
                    }.items()
                ),
                "External-agent configuration must be Codex gpt-6.1-sol high",
            )
            context = record.get("context")
            _require(
                isinstance(context, dict)
                and context.get("source") == "complete_original_request"
                and isinstance(context.get("excluded"), list)
                and set(context["excluded"]) == EXCLUDED_CONTEXT,
                "External requirements must record original-request-only context",
            )
            output_ref = authored_ref if operation == "authoring" else spec_ref
            output_spec = authored if operation == "authoring" else spec
            _require(
                (
                    record.get("group_id"),
                    record.get("input_sha256"),
                    record.get("requirement_spec_sha256"),
                )
                == (staged["group_id"], staged["input_ref"]["sha256"], output_ref["sha256"]),
                "External-agent source/spec binding mismatch",
            )
            parent = _path(root, ref["path"]).parent
            input_ref, recorded_input = capture(record.get("source_input_ref"), parent)
            recorded_spec_ref, recorded_spec = capture(
                record.get("requirement_spec_ref"), parent, "rtpeval_requirements_1"
            )
            _require(
                input_ref["sha256"] == staged["input_ref"]["sha256"]
                and recorded_input == original
                and recorded_spec_ref["sha256"] == output_ref["sha256"]
                and recorded_spec == output_spec,
                "External-agent complete source/spec references mismatch",
            )
            if operation == "review":
                review_input_ref, review_input = capture(
                    record.get("input_requirement_spec_ref"), parent, "rtpeval_requirements_1"
                )
                _require(
                    record.get("input_requirement_spec_sha256") == authored_ref["sha256"]
                    and review_input_ref["sha256"] == authored_ref["sha256"]
                    and review_input == authored,
                    "Review input does not match actual authored RequirementSpec lineage",
                )
            _, transcript = capture(
                record.get("transcript_ref"), parent, "rtpeval_requirement_agent_transcript_1"
            )
            _require(
                transcript.get("execution")
                == {key: item for key, item in record.items() if key != "transcript_ref"},
                "External-agent transcript execution/source/spec binding mismatch",
            )
            messages = transcript.get("messages")
            _require(
                isinstance(messages, list)
                and messages
                and all(
                    isinstance(message, dict)
                    and message.get("role") in ("system", "developer", "user", "assistant", "tool")
                    and _text(message.get("content"))
                    for message in messages
                ),
                "Missing external-agent transcript messages",
            )
            start, end = (
                _timestamp(record.get("started_at")),
                _timestamp(record.get("completed_at")),
            )
            _require(start <= end, "Reversed external-agent execution times")
            if operation == "authoring" and isinstance(authored.get("review"), dict):
                if authored["review"].get("status") == "reviewed":
                    _require(
                        _timestamp(authored["review"].get("reviewed_at")) <= end,
                        "Authored artifact contains future review metadata",
                    )
            records.append((record, start, end))
        author, reviewer = records
        _require(
            author[0]["execution_id"] != reviewer[0]["execution_id"]
            and author[0]["actor_ref"] != reviewer[0]["actor_ref"]
            and author[2] <= reviewer[1],
            "Independent authoring/review execution identities and ordered times required",
        )
        _require(
            spec["review"]["reviewer_ref"] == reviewer[0]["actor_ref"]
            and _timestamp(spec["review"]["reviewed_at"]) == reviewer[2],
            "RequirementSpec review does not match external review evidence",
        )
        specifications.append(
            {
                "group_id": staged["group_id"],
                "requirement_spec_ref": spec_ref,
                "authored_requirement_spec_ref": authored_ref,
            }
        )
    return specifications, files, bindings


def _assemble_attachment(staging_path, handoff_path):
    staging_path = Path(staging_path).resolve()
    staging = read_staging(staging_path)
    specifications, files, bindings = _handoff(staging, handoff_path)
    attachment = {
        "schema_version": "rtpeval_requirement_attachment_1",
        "status": "attached_pending_finalization",
        "staging_path": str(staging_path),
        "staging_sha256": _digest(staging_path.read_bytes()),
        "handoff_path": str(Path(handoff_path).resolve()),
        "groups": specifications,
        "source_bindings": bindings,
        "artifact_bindings": [
            {"path": name, "sha256": _digest(raw)} for name, raw in files.items()
        ],
    }
    return attachment, staging, files


def _check_originals(bindings):
    for binding in bindings:
        _require(
            _digest(Path(binding["original_path"]).read_bytes()) == binding["sha256"],
            "Handoff original source drift",
        )


def _write_files(output, files):
    output.mkdir(parents=True, exist_ok=False)
    for name, raw in files.items():
        target = _path(output, name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)


def attach_requirements(staging_path, handoff_path, directory):
    """Retain separately supplied review evidence without modifying source material."""
    output = Path(directory).resolve()
    _require(not output.exists(), "Attachment destination must be fresh")
    attachment, _, files = _assemble_attachment(staging_path, handoff_path)
    _check_originals(attachment["source_bindings"])
    read_staging(staging_path)
    _write_files(output, files)
    (output / "attachment.json").write_text(
        json.dumps(attachment, indent=2) + "\n", encoding="utf-8"
    )
    return attachment


def read_attachment(attachment_path):
    """Reconstruct supplied declarations and check both original and retained evidence."""
    path = Path(attachment_path).resolve()
    value = _json(path.read_bytes())
    _require(
        value.get("schema_version") == "rtpeval_requirement_attachment_1",
        "Invalid attachment schema",
    )
    expected, staging, files = _assemble_attachment(value["staging_path"], value["handoff_path"])
    _require(value == expected, "Attachment declaration/source mismatch")
    _check_originals(value["source_bindings"])
    for ref in value["artifact_bindings"]:
        _require(
            _digest(_path(path.parent, ref["path"]).read_bytes()) == ref["sha256"],
            "Attached artifact drift",
        )
    return value, staging, files


def finalize(attachment_path, directory, *, projection_reviews=None, occupancy_reviews=None):
    """Publish a fresh native manifest only after native intake accepts every group."""
    output = Path(directory).resolve()
    _require(not output.exists(), "Finalization destination must be fresh")
    attachment_path = Path(attachment_path).resolve()
    attachment, staging, files = read_attachment(attachment_path)
    _require(
        all(
            g["completion_attested"]
            and set(g["selected_runs"]) == set(VERSIONS)
            and all(r["completion_qualified"] for r in g["selected_runs"].values())
            for g in staging["groups"]
        ),
        "Finalization requires four qualified versions and producer completion declarations",
    )
    staging_path = Path(attachment["staging_path"])
    files["staging.json"] = staging_path.read_bytes()
    files["requirement-attachment.json"] = attachment_path.read_bytes()
    for ref in staging["artifact_bindings"]:
        _require(ref["path"] not in files, "Final material path collision")
        files[ref["path"]] = _path(staging_path.parent, ref["path"]).read_bytes()
        _require(_digest(files[ref["path"]]) == ref["sha256"], "Staged artifact drift")
    manifest = {
        "schema_version": "rtpeval_batch_1",
        **{
            k: staging[k]
            for k in ("batch_id", "revision", "created_at", "qualification_policy_ref")
        },
        "selected_group_ids": [g["group_id"] for g in staging["groups"]],
        "groups": [
            {
                "group_id": group["group_id"],
                "completion_attested": True,
                "input_ref": group["input_ref"],
                "requirement_spec_ref": reviewed["requirement_spec_ref"],
                "selected_runs": group["selected_runs"],
            }
            for group, reviewed in zip(staging["groups"], attachment["groups"], strict=True)
        ],
    }
    for field, supplied, schema in (
        ("projection_reviews_ref", projection_reviews, "rtpeval_reviews_1"),
        ("occupancy_reviews_ref", occupancy_reviews, "rtpeval_occupancy_reviews_1"),
    ):
        if field in staging:
            _require(supplied is None, "Conflicting staged and supplied " + field)
            manifest[field] = staging[field]
        elif supplied is not None:
            raw = Path(supplied).read_bytes()
            envelope = _json(raw)
            _require(envelope.get("schema_version") == schema, "Invalid " + field + " schema")
            name = "semantic-reviews/" + field + ".json"
            _require(name not in files, "Semantic review path collision")
            files[name] = raw
            manifest[field] = {
                "path": name,
                "sha256": _digest(raw),
                "schema_version": schema,
                "media_type": "application/json",
                "availability": "available",
            }
    _write_files(output, files)
    candidate = output / "intake-candidate.json"
    candidate.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    try:
        read_attachment(attachment_path)
        from backend.evaluation.intake import load_batch

        intake = load_batch(candidate)
        _require(
            intake.status == "accepted",
            "Native intake rejected finalization: " + str(intake.to_dict()),
        )
        from backend.evaluation.review_artifacts import review_inputs
        from backend.evaluation.semantic_readiness import review_readiness

        occupancy = review_inputs(candidate, manifest, intake.to_dict())
        readiness = review_readiness(intake.to_dict(), occupancy)
        candidate.rename(output / "manifest.json")
        (output / "semantic-readiness.json").write_bytes(
            (json.dumps(readiness, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
        )
    finally:
        if candidate.exists():
            candidate.unlink()
    return {
        "status": "accepted",
        "manifest": str(output / "manifest.json"),
        "intake": intake.to_dict(),
        "semantic_readiness": readiness,
    }
