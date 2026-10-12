"""Explicit producer-source inventory to a validated, exact-byte research bundle."""

import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from backend.cli.collection import CollectionError, _json, _path, _require

from .context import load_context, slot_key
from .dispatch import read_dispatch
from .population import population_report
from .sources import Sources

RESERVED = {"research-export.json", "census-export.json"}
OBSERVATIONS = (
    "dispatched",
    "dispatched_at",
    "input_sha256",
    "configuration_sha256",
    "execution_metadata",
)
OPTIONAL = ("completion_ref", "result_ref", "usage_ref", "provenance_ref")


class ExportSources(Sources):
    def __init__(self, root):
        super().__init__(root)
        self.originals = {}

    def read_bytes(self, ref):
        raw = super().read_bytes(ref)
        name = Path(os.path.normpath(ref["path"])).as_posix()
        _require(name not in RESERVED, "Source collides with reserved export filename: " + name)
        previous = self.originals.get(name)
        _require(previous is None or previous == raw, "Contradictory source bytes: " + name)
        self.originals[name] = raw
        return raw


def _save(path, value):
    raw = (json.dumps(value, indent=2, ensure_ascii=True, allow_nan=False) + "\n").encode()
    path.write_bytes(raw)
    return {
        "path": path.name,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "media_type": "application/json",
        "availability": "available",
        "schema_version": value["schema_version"],
    }


def _profile_sources(sources, profile):
    seen = set()
    while True:
        configs = profile.get("configurations")
        _require(isinstance(configs, dict), "Explicit configuration reference map required")
        for ref in configs.values():
            sources.read_bytes(ref)
        previous = profile.get("previous_profile_ref")
        if previous is None:
            return
        _require(isinstance(previous, dict), "Explicit profile history reference required")
        key = previous.get("path")
        _require(key not in seen, "Cyclic profile source history")
        seen.add(key)
        profile = sources.read_ref(previous, "rtpeval_research_profile_1")


def _native_dependencies(sources, value, parent, seen):
    """Native completion/provenance references are relative to their own file."""
    if isinstance(value, dict):
        if "path" in value and "sha256" in value:
            if value.get("availability") == "unavailable":
                return
            relative = value["path"]
            _require(isinstance(relative, str), "Missing native dependency path")
            _require(
                not Path(relative).is_absolute()
                and not Path(relative).drive
                and ":" not in relative,
                "Native dependency path must be relative",
            )
            name = (parent.relative_to(sources.root) / relative).as_posix()
            ref = {
                **value,
                "path": name,
                "availability": "available",
                "media_type": value.get("media_type") or "application/octet-stream",
            }
            raw = sources.read_bytes(ref)
            path = _path(sources.root, name)
            if path not in seen:
                seen.add(path)
                try:
                    nested = _json(raw)
                except (ValueError, UnicodeError):
                    nested = None
                _native_dependencies(sources, nested, path.parent, seen)
            return
        for nested in value.values():
            _native_dependencies(sources, nested, parent, seen)
    elif isinstance(value, list):
        for nested in value:
            _native_dependencies(sources, nested, parent, seen)


def export_census(inventory_path, destination):
    path = Path(inventory_path).resolve()
    raw = path.read_bytes()
    inventory = _json(raw)
    _require(
        inventory.get("schema_version") == "rtpeval_research_census_export_1",
        "Expected rtpeval_research_census_export_1 inventory",
    )
    destination = Path(destination)
    _require(not os.path.lexists(destination), "Export directory must be fresh")
    destination = destination.resolve()
    _require(not path.parent.is_relative_to(destination), "Export destination contains source root")
    sources = ExportSources(path.parent)
    _require(path.name not in RESERVED, "Inventory collides with reserved export filename")
    sources.originals[path.name] = raw
    population = sources.read_ref(inventory.get("population_ref"), "rtpeval_research_population_1")
    profile = sources.read_ref(inventory.get("profile_ref"), "rtpeval_research_profile_1")
    cases = population.get("cases")
    if not isinstance(cases, list) or not all(isinstance(case, dict) for case in cases):
        raise CollectionError("Explicit original-input case objects required")
    for case in cases:
        sources.read_ref(case.get("input_ref"))
    _profile_sources(sources, profile)
    entries = inventory.get("attempt_sources")
    if not isinstance(entries, list):
        raise CollectionError("Explicit ordered attempt_sources required")
    attempts, diagnostics, provenance = [], [], []
    for index, entry in enumerate(entries):
        try:
            _require(isinstance(entry, dict), "Attempt source must be an object")
            _require(
                not any(field in entry for field in OBSERVATIONS),
                "Dispatch observations must come from producer_metadata_ref",
            )
            case = next(
                (c for c in population["cases"] if c["case_id"] == entry.get("case_id")), None
            )
            if case is None:
                raise CollectionError("Foreign attempt case")
            config = profile["configurations"].get(entry.get("version"))
            _require(config is not None, "Foreign attempt configuration/version")
            expected = {
                **entry,
                "input_sha256": case["input_ref"]["sha256"],
                "configuration_sha256": config["sha256"],
            }
            metadata = read_dispatch(sources, entry.get("producer_metadata_ref"), expected)
            provenance.append(
                {
                    "attempt_id": entry.get("attempt_id"),
                    "slot": list(slot_key(entry)),
                    "producer_metadata_ref": entry["producer_metadata_ref"],
                    "source_kind": metadata["source_kind"],
                    "declared_by": metadata["declared_by"],
                    "recorded_at": metadata["recorded_at"],
                    "evidence_refs": metadata.get("evidence_refs", []),
                }
            )
            row = {**entry, **{field: metadata[field] for field in OBSERVATIONS}}
            for field in OPTIONAL:
                ref = row.get(field)
                if ref is None or (
                    isinstance(ref, dict) and ref.get("availability") == "unavailable"
                ):
                    if ref is not None:
                        _require(ref.get("sha256") is None, "Unavailable source has digest")
                    row[field] = None
                    diagnostics.append(
                        {
                            "attempt_id": entry.get("attempt_id"),
                            "field": field,
                            "availability": "unavailable",
                            "reason": (ref or {}).get("reason", "not_supplied"),
                        }
                    )
                else:
                    if field in ("completion_ref", "provenance_ref"):
                        native_path = _path(sources.root, ref["path"])
                        row[field] = {
                            **ref,
                            "path": native_path.relative_to(sources.root).as_posix(),
                        }
                        native = sources.read_ref(row[field])
                        _native_dependencies(sources, native, native_path.parent, set())
                    else:
                        sources.read_ref(ref)
            attempts.append(row)
        except (CollectionError, OSError, ValueError, KeyError, TypeError) as exc:
            case_id = entry.get("case_id") if isinstance(entry, dict) else "?"
            attempt_id = entry.get("attempt_id") if isinstance(entry, dict) else "?"
            raise CollectionError(
                f"attempt_sources[{index}] case={case_id} attempt={attempt_id}: {exc}"
            ) from exc
    census = {
        "schema_version": "rtpeval_research_census_1",
        "population_id": population["population_id"],
        "population_revision": population["revision"],
        "profile_id": profile["profile_id"],
        "profile_revision": profile["revision"],
        "attempts": attempts,
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".rtpeval-census-", dir=destination.parent) as temporary:
        pending = Path(temporary) / "bundle"
        material = pending / "material"
        material.mkdir(parents=True)
        for name, original in sources.originals.items():
            target = _path(material, name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(original)
        census_ref = _save(material / "census-export.json", census)
        declaration = {
            "schema_version": "rtpeval_research_declaration_1",
            "population_ref": inventory["population_ref"],
            "profile_ref": inventory["profile_ref"],
            "census_ref": census_ref,
            "track_refs": {},
        }
        declaration_ref = _save(material / "research-export.json", declaration)
        context = load_context(material / declaration_ref["path"])
        report = population_report(context)
        diagnostics.extend(
            {
                "slot": list(slot_key(slot)),
                "availability": "unknown",
                "reason": "missing_census_record",
            }
            for slot in context.slots
            if not slot["attempts"]
        )
        # Sources are checked again before publication; copied originals must still match.
        for name, original in sources.originals.items():
            _require(
                _path(path.parent, name).read_bytes() == original,
                "Source changed during export: " + name,
            )
        receipt = {
            "schema_version": "rtpeval_research_census_export_report_1",
            "processing_status": "completed",
            "declaration_ref": {**declaration_ref, "path": "material/" + declaration_ref["path"]},
            "census_ref": {**census_ref, "path": "material/" + census_ref["path"]},
            "population_id": population["population_id"],
            "population_revision": population["revision"],
            "attempts": len(attempts),
            "planned_slots": len(context.slots),
            "missing_slots": sum(not slot["attempts"] for slot in context.slots),
            "source_bindings": [
                {"path": name, "sha256": hashlib.sha256(original).hexdigest()}
                for name, original in sorted(sources.originals.items())
            ],
            "source_root": "material",
            "metadata_provenance": provenance,
            "diagnostics": diagnostics,
            "validation_semantic_sha256": report["semantic_sha256"],
            "quality_qualification": "not_performed",
        }
        _require(not os.path.lexists(destination), "Export directory must be fresh")
        destination.mkdir(exist_ok=False)
        copied = {
            **sources.originals,
            "census-export.json": (material / "census-export.json").read_bytes(),
            "research-export.json": (material / "research-export.json").read_bytes(),
        }
        for name, original in copied.items():
            target = _path(destination / "material", name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(original)
            _require(target.read_bytes() == original, "Published bytes differ: " + name)
        load_context(destination / "material/research-export.json")
        # Directory renames can be unavailable on Windows. Publish completion last.
        _save(destination / "export.json", receipt)
    return receipt
