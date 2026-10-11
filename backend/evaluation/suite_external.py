"""Offline validation and exact-byte retention of separately operated studies."""

import base64
import copy
import hashlib
from pathlib import Path

from .controlled_batch import build_controlled_batch
from .human_report import build_human_report
from .intake import _read
from .records import canonical_digest

EXTERNAL_TRACKS = ("human", "controlled_repair")


class Sources:
    """Read declared artifact references and retain their original bytes."""

    def __init__(self, root):
        self.root = Path(root).resolve()
        self.bindings = {}
        self.raw_artifacts = {}

    def read(self, ref, schema, *, prefix):
        if not isinstance(ref, dict) or ref.get("schema_version") != schema:
            raise ValueError(f"Explicit {schema} attachment reference required")
        name = ref.get("path")
        if not isinstance(name, str) or not name:
            raise ValueError("Explicit attachment path required")
        relative = Path(name)
        path = (self.root / relative).resolve()
        if relative.is_absolute() or relative.drive or not path.is_relative_to(self.root):
            raise ValueError("Attachment source escapes declaration root")
        value, sha = _read(path)
        if sha != ref.get("sha256") or value.get("schema_version") != schema:
            raise ValueError(f"Attachment hash/schema mismatch: {name}")
        self.bindings[str(path)] = sha
        target = prefix + "/" + path.relative_to(self.root).as_posix()
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != sha:
            raise ValueError("Attachment changed during validation")
        encoded = base64.b64encode(raw).decode("ascii")
        if target in self.raw_artifacts and self.raw_artifacts[target] != encoded:
            raise ValueError("Conflicting copied attachment artifact paths")
        self.raw_artifacts[target] = encoded
        return value, target


def _human(attachment, sources, cases, prefix):
    if set(attachment) - {"report", "presentation", "mapping", "answers", "source_context"}:
        raise ValueError("Unsupported human attachment fields")
    context = attachment.get("source_context", {})
    if not isinstance(context, dict) or set(context) != {"case_ids", "rater_ref", "source_hashes"}:
        raise ValueError("Explicit human source context required")
    ids = context.get("case_ids")
    selected = {case[0]["case_id"]: case[3] for case in cases}
    if (
        not isinstance(ids, list)
        or not ids
        or len(set(ids)) != len(ids)
        or not set(ids) <= selected.keys()
    ):
        raise ValueError("Human source context requires selected case_ids")
    expected = {}
    # A human package belongs to one native batch; distinct selected suite cases
    # must use separate packages rather than pooling identically named groups.
    if len(ids) != 1:
        raise ValueError("Human attachment requires one native case population")
    intake = selected[ids[0]]
    expected.update(intake["source_hashes"])
    for group in intake["inventory"]:
        gid = group["group_id"]
        expected[gid + "/input"] = group["input_sha256"]
        for version, run in group["runs"].items():
            expected[gid + "/" + version] = run["final"]["context"]["artifact_sha256"]
    report, target = sources.read(attachment["report"], "rtpeval_human_report_1", prefix=prefix)
    public, _ = sources.read(attachment["presentation"], "rtpeval_human_package_1", prefix=prefix)
    private, _ = sources.read(attachment["mapping"], "rtpeval_human_mapping_1", prefix=prefix)
    answers = attachment.get("answers")
    if not isinstance(answers, list):
        raise ValueError("Explicit human answer bundle array required")
    bundles = [sources.read(ref, "rtpeval_human_answers_1", prefix=prefix)[0] for ref in answers]
    if (
        context.get("rater_ref") != public.get("rater_ref")
        or context.get("source_hashes") != expected
        or not isinstance(private.get("preparation"), dict)
        or private["preparation"].get("source_hashes") != expected
    ):
        raise ValueError("Human source context/rater is foreign or stale")
    rebuilt = build_human_report(public, private, bundles, generated_at=report["generated_at"])
    if rebuilt != report:
        raise ValueError("Human report differs from native presentation/effective revisions")
    return {
        "processing_status": "complete",
        "evidence_status": "available"
        if all(task["answer_revision"] is not None for task in report["tasks"])
        else "partial"
        if any(task["answer_revision"] is not None for task in report["tasks"])
        else "unavailable",
        "applicability": "applicable",
        "report": target,
        "source_context": context,
        "rater_ref": public["rater_ref"],
        "presentation_id": report["presentation_id"],
        "presentation_hash": report["presentation_hash"],
        "mapping_hash": report["mapping_hash"],
        "main_task_count": report["main_task_count"],
        "missingness": report["missingness"],
        "effective_revisions": [
            {
                "task_id": row["task_id"],
                "answer_revision": row["answer_revision"],
                "answer_hash": row["answer_hash"],
            }
            for row in report["tasks"]
        ],
    }


def _controlled(attachment, sources, prefix):
    if set(attachment) != {"report", "manifest", "source_context"}:
        raise ValueError("Explicit controlled report/manifest/source_context required")
    report, target = sources.read(
        attachment["report"], "rtpeval_controlled_batch_report_1", prefix=prefix
    )
    manifest, _ = sources.read(attachment["manifest"], "rtpeval_controlled_batch_1", prefix=prefix)
    context = attachment["source_context"]
    if (
        not isinstance(context, dict)
        or not isinstance(context.get("population_id"), str)
        or not context["population_id"].strip()
        or context.get("batch_id") != manifest.get("batch_id")
        or context.get("revision") != manifest.get("revision")
    ):
        raise ValueError("Controlled population source context is foreign or stale")
    declared = context.get("cases")
    inventory = manifest.get("cases")
    if (
        not isinstance(declared, list)
        or not isinstance(inventory, list)
        or len(declared) != len(inventory)
    ):
        raise ValueError("Controlled source context case inventory mismatch")
    manifest_root = (sources.root / attachment["manifest"]["path"]).resolve().parent
    native_sources = Sources(manifest_root)
    for row, binding in zip(inventory, declared, strict=True):
        if (
            not isinstance(row, dict)
            or not isinstance(binding, dict)
            or any(
                binding.get(key) != row.get(key) for key in ("case_id", "role", "expected_goal_ids")
            )
        ):
            raise ValueError("Controlled case/role/goal inventory is foreign or stale")
        ref = row.get("report")
        if not isinstance(ref, dict) or ref.get("availability") not in {"available", "unavailable"}:
            raise ValueError("Controlled case requires explicit report availability")
        if ref["availability"] == "unavailable":
            if (
                binding.get("preparation_sha256") is not None
                or binding.get("expectations_sha256") is not None
            ):
                raise ValueError("Unavailable controlled case cannot claim resolved provenance")
            continue
        individual, _ = native_sources.read(
            ref, "rtpeval_controlled_report_1", prefix=prefix + "/cases"
        )
        if individual.get("content_hash") != canonical_digest(
            {k: v for k, v in individual.items() if k not in {"content_hash", "generated_at"}}
        ):
            raise ValueError("Controlled individual report content hash mismatch")
        if not isinstance(individual.get("source_hashes"), dict):
            raise ValueError("Controlled report source hashes are malformed")
        preparation_value = None
        for field, schema, key in (
            ("preparation", "rtpeval_controlled_preparation_1", "preparation"),
            ("expectations", "rtpeval_controlled_expectations_1", "expectations"),
        ):
            value, _ = sources.read(binding[field], schema, prefix=prefix + "/bindings")
            sha = canonical_digest(value)
            if (
                binding.get(field + "_sha256") != sha
                or individual.get("source_hashes", {}).get(key) != sha
            ):
                raise ValueError(f"Controlled {field} source binding is foreign or stale")
            if field == "preparation":
                preparation_value = value
                inventory_value = value.get("inventory")
                if (
                    not isinstance(inventory_value, list)
                    or len(inventory_value) != 1
                    or not isinstance(inventory_value[0], dict)
                ):
                    raise ValueError("Controlled preparation inventory is malformed")
            if field == "preparation" and (
                value.get("status") != "accepted"
                or value.get("batch_id") != "controlled:" + row["case_id"]
                or len(value.get("inventory", [])) != 1
                or value["inventory"][0].get("group_id") != row["case_id"]
            ):
                raise ValueError("Controlled preparation case binding is foreign or stale")
            if field == "expectations":
                targets = value.get("targets")
                if not isinstance(targets, list) or any(
                    not isinstance(goal, dict) for goal in targets
                ):
                    raise ValueError("Controlled expectations target inventory is malformed")
                if value.get("case_hash") != preparation_value.get("case_hash"):
                    raise ValueError("Controlled expectation/preparation case hashes differ")
            if field == "expectations" and (
                value.get("case_id") != row["case_id"]
                or {goal.get("goal_id") for goal in value.get("targets", [])}
                != set(row["expected_goal_ids"])
            ):
                raise ValueError("Controlled expectations goal binding is foreign or stale")
    rebuilt = build_controlled_batch(manifest, manifest_root, generated_at=report["generated_at"])
    if rebuilt != report or rebuilt.get("diagnostics"):
        raise ValueError("Controlled batch report differs from native inventory or is malformed")
    for row, original in zip(rebuilt["cases"], inventory, strict=True):
        if original["report"]["availability"] == "available" and row.get("diagnostics"):
            raise ValueError("Controlled supplied case report is malformed/foreign/stale")
    sources.bindings.update(native_sources.bindings)
    sources.raw_artifacts.update(native_sources.raw_artifacts)
    return {
        "processing_status": "complete",
        "evidence_status": "available"
        if not report["counts"]["unavailable_cases"]
        else "unavailable"
        if report["counts"]["unavailable_cases"] == report["counts"]["expected_cases"]
        else "partial",
        "applicability": "applicable",
        "report": target,
        "source_context": context,
        "population_id": context["population_id"],
        "counts": report["counts"],
        "case_inventory": declared,
    }


def prepare_external(tracks, cases, *, source_root):
    """Validate optional external reports before any suite provider work."""
    sources = Sources(source_root)
    external = {}
    for kind in EXTERNAL_TRACKS:
        declarations = tracks.get(kind, [])
        if not isinstance(declarations, list):
            raise ValueError(f"Explicit {kind} attachment array required")
        if any(not isinstance(item, dict) for item in declarations):
            raise ValueError(f"Explicit {kind} attachment objects required")
        external[kind] = [
            (
                _human(item, sources, cases, f"tracks/{kind}/{index:04d}")
                if kind == "human"
                else _controlled(item, sources, f"tracks/{kind}/{index:04d}")
            )
            for index, item in enumerate(declarations, 1)
        ]
        identities = [
            (row["rater_ref"], row["presentation_id"]) if kind == "human" else row["population_id"]
            for row in external[kind]
        ]
        if len(set(identities)) != len(identities):
            raise ValueError(f"Duplicate {kind} study population")
    return {
        "external": external,
        "source_bindings": sources.bindings,
        "raw_artifacts": sources.raw_artifacts,
        "artifacts": {},
    }


def compose_external(configuration):
    """Keep each study population visible without aggregating human quality."""
    result = {}
    for kind in EXTERNAL_TRACKS:
        studies = configuration.get("external", {}).get(kind, [])
        result[kind] = {
            "processing_status": "complete",
            "applicability": "applicable",
            "evidence_status": "available"
            if studies and all(row["evidence_status"] == "available" for row in studies)
            else "partial"
            if any(row["evidence_status"] != "unavailable" for row in studies)
            else "unavailable",
            "studies": studies,
        }
        if not studies:
            result[kind]["reason"] = "study_not_supplied"
    return result


def _selected_cases(preparation):
    return [
        (case, {}, {}, prepared["primary"]["intake"])
        for case, prepared in zip(
            preparation["declaration"]["cases"], preparation["cases"], strict=True
        )
    ]


def _attachment_configuration(declaration, preparation, source_root):
    if (
        set(declaration) != {"schema_version", "suite_id", "tracks"}
        or declaration.get("schema_version") != "rtpeval_suite_attachments_1"
        or declaration.get("suite_id") != preparation["suite_id"]
        or not isinstance(declaration.get("tracks"), dict)
        or not declaration["tracks"]
        or set(declaration["tracks"]) - set(EXTERNAL_TRACKS)
    ):
        raise ValueError("Explicit suite-bound external attachment declaration required")
    return prepare_external(
        declaration["tracks"], _selected_cases(preparation), source_root=source_root
    )


def _overlay(previous, configuration, tracks, revision_name):
    report = copy.deepcopy(previous)
    for kind, row in compose_external(configuration).items():
        if kind not in tracks:
            continue
        row = copy.deepcopy(row)
        for study in row["studies"]:
            study["report"] = revision_name + "/" + study["report"]
        report["tracks"][kind] = row
    return report


def verify_refreshes(root, preparation, original):
    """Rebuild every appended native attachment and verify a closed summary chain."""
    from .suite import _check_closed, track_artifact_path

    latest = original
    parent_sha = _read(root / "summary.json")[1]
    refreshes = root / "reports"
    if not refreshes.exists():
        return latest
    folders = sorted(refreshes.iterdir())
    for index, folder in enumerate(folders, 1):
        if not folder.is_dir() or folder.name != f"{index:04d}" or folder.is_symlink():
            raise ValueError("Unexpected suite report revision or missing lineage")
        _check_closed(folder, preparation["content_sha256"], refresh=True)
        lineage = _read(folder / "lineage.json")[0]
        saved, summary_sha = _read(folder / "summary.json")
        if (
            lineage.get("schema_version") != "rtpeval_suite_refresh_1"
            or lineage.get("preparation_sha256") != preparation["content_sha256"]
            or lineage.get("parent_summary_sha256") != parent_sha
            or lineage.get("summary_sha256") != summary_sha
        ):
            raise ValueError("Suite refresh parent/summary lineage mismatch")
        if lineage.get("attachments_sha256") is not None:
            declaration, declaration_sha = _read(folder / "attachments.json")
            if declaration_sha != lineage["attachments_sha256"]:
                raise ValueError("Suite refresh attachment declaration changed")
            config = _attachment_configuration(declaration, preparation, folder / "sources")
            frozen = _read(folder / "configuration.json")[0]
            if (
                config["external"] != frozen["external"]
                or config["raw_artifacts"] != frozen["raw_artifacts"]
            ):
                raise ValueError("Suite refresh native attachment replay differs")
            for name, raw in config["raw_artifacts"].items():
                if track_artifact_path(folder, name).read_bytes() != base64.b64decode(
                    raw, validate=True
                ):
                    raise ValueError("Suite refresh exact attachment bytes differ")
            expected = _overlay(
                latest, config, declaration["tracks"], folder.relative_to(root).as_posix()
            )
        else:
            expected = latest
        if saved != expected:
            raise ValueError("Suite refresh summary differs from native attachment composition")
        latest, parent_sha = saved, summary_sha
    return latest


def append_refresh(root, preparation, previous, *, attachments=None):
    """Preflight all inputs before appending any immutable report revision."""
    from .snapshot import _bytes
    from .suite import _close, _save, write_raw_artifacts

    config, declaration, raw_declaration = None, None, None
    source_bytes = {}
    if attachments is not None:
        source = Path(attachments).resolve()
        if source.is_relative_to(root):
            raise ValueError("Refresh attachment sources must be outside suite outputs")
        declaration, declaration_sha = _read(source)
        raw_declaration = source.read_bytes()
        if hashlib.sha256(raw_declaration).hexdigest() != declaration_sha:
            raise ValueError("Refresh declaration changed during validation")
        config = _attachment_configuration(declaration, preparation, source.parent)
        for path, sha in config["source_bindings"].items():
            resolved = Path(path)
            raw = resolved.read_bytes()
            if (
                not resolved.is_relative_to(source.parent)
                or resolved.is_relative_to(root)
                or hashlib.sha256(raw).hexdigest() != sha
            ):
                raise ValueError("Refresh dependency source binding changed/escaped")
            source_bytes[resolved.relative_to(source.parent)] = raw
    reports = root / "reports"
    folders = sorted(reports.iterdir()) if reports.exists() else []
    parent = folders[-1] / "summary.json" if folders else root / "summary.json"
    parent_sha = _read(parent)[1]
    name = f"reports/{len(folders) + 1:04d}"
    report = _overlay(previous, config, declaration["tracks"], name) if config else previous
    summary_raw = _bytes(report)
    lineage = {
        "schema_version": "rtpeval_suite_refresh_1",
        "preparation_sha256": preparation["content_sha256"],
        "parent_summary_sha256": parent_sha,
        "summary_sha256": hashlib.sha256(summary_raw).hexdigest(),
        "attachments_sha256": hashlib.sha256(raw_declaration).hexdigest()
        if raw_declaration is not None
        else None,
    }
    revision = root / name
    revision.mkdir(parents=True, exist_ok=False)
    if config:
        (revision / "attachments.json").write_bytes(raw_declaration)
        for relative, raw in source_bytes.items():
            copied = revision / "sources" / relative
            copied.parent.mkdir(parents=True, exist_ok=True)
            copied.write_bytes(raw)
        write_raw_artifacts(revision, config["raw_artifacts"])
        _save(revision, "configuration.json", config)
    _save(revision, "lineage.json", lineage)
    _save(revision, "summary.json", report)
    _close(revision, preparation["content_sha256"], refresh=True)
    return report


def verify_prepared_external(preparation):
    """Native initial-study verification uses source bytes bound by preparation."""
    root = Path(preparation["source_root"]).resolve()
    tracks = {
        kind: value
        for kind, value in preparation["declaration"].get("tracks", {}).items()
        if kind in EXTERNAL_TRACKS
    }
    config = prepare_external(tracks, _selected_cases(preparation), source_root=root)
    frozen = preparation["track_configuration"]
    if config["external"] != frozen.get("external", {}):
        raise ValueError("Prepared external native attachment replay differs")
    for name, encoded in config["raw_artifacts"].items():
        if frozen.get("raw_artifacts", {}).get(name) != encoded:
            raise ValueError("Prepared exact external dependency bytes differ")
