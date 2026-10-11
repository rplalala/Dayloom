"""Read-only adapter for explicitly selected independently evidenced V3 pairs."""

import hashlib
from datetime import UTC, datetime
from pathlib import Path

from .daily_density import prepare_density_policies
from .intake import _read
from .routes import prepare_routes
from .snapshot import build_evidence_plan
from .v3_correspondence import prepare_v3_correspondence, read_v3_result_sources
from .v3_pair_report import build_v3_pair_report, pair_content_hash

FILES = {
    "context": "schedule_context",
    "occupancy_reviews": "occupancy_reviews",
    "route_reviews": "route_reviews",
    "coordinates": "coordinate_evidence",
    "expected_plan": "expected_plan",
    "edit_provenance": "edit_provenance",
    "correspondence_reviews": "correspondence_reviews",
    "density_reviews": "density_reviews",
}


def _path(root, name):
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Explicit relative pair evidence path required")
    relative = Path(name)
    path = (root / relative).resolve()
    if relative.is_absolute() or relative.drive or not path.is_relative_to(root):
        raise ValueError("Pair evidence escapes declaration root")
    return path


def prepare_pairs(cases, *, source_root):
    """Freeze native pair reports from supplied material without acquiring evidence."""
    artifacts, bindings, records = {}, {}, {}
    for index, (case, paths, _, intake) in enumerate(cases, 1):
        tracks = case.get("tracks", {})
        if "pair" not in tracks:
            continue
        config = tracks["pair"]
        if not isinstance(config, dict) or set(config) - set(FILES) - {
            "identity",
            "snapshot",
            "identity_snapshot",
        }:
            raise ValueError("Unsupported pair track configuration")
        if not config:
            records[case["case_id"]] = {
                "processing_status": "complete",
                "evidence_status": "unavailable",
                "applicability": "applicable",
                "reason": "pair_material_missing",
                "report": None,
            }
            continue
        if "identity" not in config:
            raise ValueError("Independent identity report required for supplied pair evidence")
        identity, sha = _read(_path(source_root, config["identity"]))
        bindings[str(_path(source_root, config["identity"]))] = sha
        files, hashes = {}, {"identity": sha}
        for name, parameter in FILES.items():
            if name in config:
                path = _path(source_root, config[name])
                files[parameter], hashes[name] = _read(path)
                bindings[str(path)] = hashes[name]
        directories = {}
        for name in ("snapshot", "identity_snapshot"):
            if name in config:
                path = _path(source_root, config[name])
                if not path.is_dir():
                    raise ValueError("Pair snapshot directory is missing")
                directories[name] = path
                for artifact in path.rglob("*"):
                    if artifact.is_symlink():
                        raise ValueError("Pair snapshot symlinks are forbidden")
                    if artifact.is_file():
                        bindings[str(artifact)] = hashlib.sha256(artifact.read_bytes()).hexdigest()
        sources = read_v3_result_sources(intake, paths["manifest"])
        if "snapshot" not in directories:
            preparation = prepare_routes(
                intake,
                identity,
                files.get("schedule_context"),
                files.get("occupancy_reviews"),
                files.get("route_reviews"),
                files.get("coordinate_evidence"),
                paired=True,
                identity_snapshot_directory=directories.get("identity_snapshot"),
            ).to_dict()
            correspondence = prepare_v3_correspondence(
                intake,
                identity,
                sources,
                files.get("correspondence_reviews"),
                files.get("edit_provenance"),
            ).to_dict()
            prepare_density_policies(intake, files.get("density_reviews"))
            for value in (preparation, correspondence):
                if value["status"] != "complete":
                    raise ValueError("Pair material invalid: " + str(value["diagnostics"]))
            if files.get("expected_plan") is not None and files[
                "expected_plan"
            ] != build_evidence_plan(intake, identity, preparation["route_contexts"], paired=True):
                raise ValueError("Pair expected plan differs from independently bound preparation")
            if intake["inventory"][0]["runs"]["v3"]["paired_available"]:
                records[case["case_id"]] = {
                    "processing_status": "complete",
                    "evidence_status": "unavailable",
                    "applicability": "applicable",
                    "reason": "pair_material_missing",
                    "report": None,
                }
                continue
        report = build_v3_pair_report(
            intake,
            identity,
            directories.get("snapshot"),
            **files,
            result_sources=sources,
            identity_snapshot_directory=directories.get("identity_snapshot"),
            generated_at=datetime.now(UTC).isoformat(),
        ).to_dict()
        if report["status"] != "complete":
            raise ValueError("Pair material invalid: " + str(report["diagnostics"]))
        report["preparation_file_sha256"] = hashes
        report["content_hash"] = pair_content_hash(report)
        name = f"tracks/{index:04d}/pair.json"
        artifacts[name] = report
        records[case["case_id"]] = {
            "processing_status": "complete",
            "evidence_status": "available"
            if all(group["pair_status"] == "available" for group in report["groups"])
            else "unavailable",
            "applicability": "applicable",
            "report": name,
            "content_hash": report["content_hash"],
        }
    return {"artifacts": artifacts, "source_bindings": bindings, "pair_cases": records}


def compose_pairs(preparation, directory, cases):
    """Expose native comparison diagnostics separately from the four final scores."""
    config = preparation["track_configuration"]
    for case in cases:
        record = config.get("pair_cases", {}).get(case["case_id"])
        if record is None:
            case["tracks"]["pair"] = {
                "processing_status": "not_requested",
                "evidence_status": "unavailable",
                "applicability": "not_requested",
                "reason": "pair_not_requested",
            }
            continue
        if record["report"] is None:
            case["tracks"]["pair"] = dict(record)
            continue
        report = _read(directory / record["report"])[0]
        if pair_content_hash(report) != record["content_hash"]:
            raise ValueError("Pair report content hash differs")
        case["tracks"]["pair"] = {**record, "native_report": report}
