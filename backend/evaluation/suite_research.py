"""Source-bound offline research reports for an optional suite population."""

import base64
import copy
import hashlib
import json
from pathlib import Path

from ..cli.collection import CollectionError
from .research.context import load_context
from .research.links import benefit_resource_links
from .research.registry import TRACKS, build_report
from .research.rendering import render_markdown
from .research.sources import Sources, digest
from .snapshot import _bytes


def _json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def _ref(path, raw):
    return {"path": path, "sha256": hashlib.sha256(raw).hexdigest()}


def prepare_research(attachment, *, source_root, output_root, refresh=False):
    """Build each selected track independently and freeze its exact source union."""
    if (
        not isinstance(attachment, dict)
        or set(attachment) != {"schema_version", "declaration_ref", "selected_tracks"}
        or attachment.get("schema_version") != "rtpeval_suite_research_1"
    ):
        raise ValueError(
            "Research: explicit suite research declaration and selected_tracks required"
        )
    selected = attachment["selected_tracks"]
    if (
        not isinstance(selected, list)
        or not selected
        or any(not isinstance(name, str) or name not in TRACKS for name in selected)
        or len(set(selected)) != len(selected)
    ):
        raise ValueError("Research: explicit distinct registered selected_tracks required")
    source_root, output_root = Path(source_root).resolve(), Path(output_root).resolve()
    try:
        Sources(source_root).read_ref(
            attachment["declaration_ref"], "rtpeval_research_declaration_1"
        )
    except (CollectionError, OSError, ValueError, TypeError, KeyError) as exc:
        raise ValueError(f"Research declaration: {exc}") from exc
    declaration = (source_root / attachment["declaration_ref"]["path"]).resolve()
    relative_root = declaration.parent.relative_to(source_root).as_posix()
    prefix = "sources" if refresh else "tracks/research/sources"
    frozen_root = (Path(prefix) / relative_root).as_posix()
    index = {
        "schema_version": "rtpeval_suite_research_index_1",
        "processing_status": "complete",
        "selected_tracks": sorted(selected),
        "source_root": frozen_root,
        "source_prefix": prefix,
        "attachment": attachment,
        "declaration_ref": attachment["declaration_ref"],
        "tracks": {
            name: {"processing_status": "not_requested", "reason": "track_not_selected"}
            for name in TRACKS
        },
    }
    bindings, raw_artifacts = {}, {}
    reports = {}
    for name in sorted(selected):
        try:
            context = load_context(declaration)
            report, render = build_report(context, name)
            reports[name] = report
            dependencies = []
            for binding in context.sources.manifest():
                path = (context.root / binding["path"]).resolve()
                if not path.is_relative_to(source_root):
                    raise ValueError("source escapes suite attachment root")
                raw = path.read_bytes()
                if hashlib.sha256(raw).hexdigest() != binding["sha256"]:
                    raise ValueError("source changed during report build")
                key = str(path)
                if key in bindings and bindings[key] != binding["sha256"]:
                    raise ValueError("source union contains conflicting bytes")
                bindings[key] = binding["sha256"]
                target = (Path(prefix) / path.relative_to(source_root)).as_posix()
                dependencies.append(target)
                if not refresh:
                    raw_artifacts[target] = base64.b64encode(raw).decode("ascii")
            json_path = f"tracks/research/reports/{name}.json"
            md_path = f"tracks/research/reports/{name}.md"
            json_raw = _json_bytes(report)
            md_raw = render_markdown(
                report,
                render,
                source_root=output_root / frozen_root,
                output_path=output_root / md_path,
            ).encode("utf-8")
            for path, raw in ((json_path, json_raw), (md_path, md_raw)):
                raw_artifacts[path] = base64.b64encode(raw).decode("ascii")
            index["tracks"][name] = {
                **{
                    key: report[key]
                    for key in (
                        "schema_version",
                        "processing_status",
                        "applicability",
                        "measurement_coverage",
                        "review_coverage",
                        "population_digest",
                        "source_digest",
                        "semantic_sha256",
                        "diagnostics",
                    )
                    if key in report
                },
                "json": _ref(json_path, json_raw),
                "markdown": _ref(md_path, md_raw),
                "source_dependencies": dependencies,
            }
        except (CollectionError, OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
            raise ValueError(f"Research {name}: {exc}") from exc
    index["population"] = {
        "population_id": context.population["population_id"],
        "revision": context.population["revision"],
        "digest": digest(context.population),
        "profile_id": context.profile["profile_id"],
        "profile_revision": context.profile["revision"],
        "profile_digest": digest(context.profile),
        "census_ref": context.declaration.get("census_ref"),
        "planned_slots": len(context.slots),
        "unique_requests": len(context.population["cases"]),
    }
    index["population_digest"] = digest(context.population)
    index["profile_ids"] = {
        "selection": context.profile["profile_id"],
        "selection_revision": context.profile["revision"],
    }
    index["measurement_coverage"] = {
        name: report["measurement_coverage"] for name, report in reports.items()
    }
    index["review_coverage"] = {name: report["review_coverage"] for name, report in reports.items()}
    index["source_bindings"] = [
        {"path": Path(path).relative_to(source_root).as_posix(), "sha256": sha}
        for path, sha in sorted(bindings.items())
    ]
    index["source_digest"] = digest(index["source_bindings"])
    index["applicability"] = "applicable"
    index["diagnostics"] = []
    index["benefit_resource_links"] = benefit_resource_links(context, reports)
    index["interpretation"] = "descriptive_source_compatible_links_only"
    index["controlled_resource_link"] = {
        "applicability": "not_applicable",
        "reason": "controlled_simulation_is_a_separate_population",
    }
    index["semantic_sha256"] = digest(index)
    raw_artifacts["tracks/research/index.json"] = base64.b64encode(_bytes(index)).decode("ascii")
    return {
        "research": index,
        "source_bindings": bindings,
        "raw_artifacts": raw_artifacts,
        "artifacts": {},
    }


def compose_research(configuration, *, invalid_artifacts=()):
    """Expose complete processing separately from research measurement coverage."""
    index = copy.deepcopy(configuration["research"])
    raw = base64.b64decode(
        configuration["raw_artifacts"]["tracks/research/index.json"], validate=True
    )
    index["index"] = _ref("tracks/research/index.json", raw)
    changed = set(invalid_artifacts)
    affected = []
    for track in index["tracks"].values():
        if track["processing_status"] == "not_requested":
            continue
        dependencies = track["source_dependencies"] + [
            track["json"]["path"],
            track["markdown"]["path"],
        ]
        invalid = sorted(changed.intersection(dependencies))
        if invalid:
            track.update(
                processing_status="needs_material_correction",
                evidence_status="unavailable",
                reason="prepared_track_artifact_changed",
                invalid_artifacts=invalid,
            )
            affected.extend(invalid)
    if "tracks/research/index.json" in changed:
        affected.append("tracks/research/index.json")
    if affected:
        for link in index["benefit_resource_links"]:
            fields = [link.get("benefit"), link.get("resources")]
            if any(
                binding
                and index["tracks"][binding["track"]]["processing_status"]
                == "needs_material_correction"
                for binding in fields
            ):
                link.update(status="unavailable", source_compatible=False)
                link["reasons"].append("research_material_correction")
        index.update(
            processing_status="needs_material_correction",
            invalid_artifacts=sorted(set(affected)),
            reason="prepared_track_artifact_changed",
        )
    return index


def relocate_index(index, prefix):
    """Locate an immutable research index inside one appended suite revision."""
    result = copy.deepcopy(index)
    for field in ("source_root", "source_prefix"):
        result[field] = prefix + "/" + result[field]
    result["index"]["path"] = prefix + "/" + result["index"]["path"]
    for track in result["tracks"].values():
        if track["processing_status"] == "not_requested":
            continue
        for field in ("json", "markdown"):
            track[field]["path"] = prefix + "/" + track[field]["path"]
        track["source_dependencies"] = [
            prefix + "/" + path for path in track["source_dependencies"]
        ]
    return result


class ResearchIntegrityError(ValueError):
    """A bound initial research dependency changed during native suite execution."""

    def __init__(self, path, artifacts):
        self.research_material_correction = artifacts
        super().__init__(f"Research original source changed: {path}")


def original_source_correction(preparation, path):
    """Attribute an original-source stop to precisely the reports that consumed it."""
    index = preparation["track_configuration"].get("research")
    if index is None:
        return
    relative = Path(path).resolve().relative_to(Path(preparation["source_root"]).resolve())
    target = (Path(index["source_prefix"]) / relative).as_posix()
    if any(target in entry.get("source_dependencies", []) for entry in index["tracks"].values()):
        raise ResearchIntegrityError(path, [target])


def verify_initial_index(preparation, original):
    """Verify the closed initial research view before authorizing any fresh revision."""
    configuration = preparation["track_configuration"]
    if "research" not in configuration:
        return
    correction = {
        path
        for row in original["cases"]
        for path in (row.get("primary_report") or {}).get("research_material_correction", [])
    }
    expected = compose_research(configuration, invalid_artifacts=correction)
    if original.get("tracks", {}).get("research") != expected:
        raise ValueError("Initial research index differs from source-bound reconstruction")
