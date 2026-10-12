"""Source-bound corpus producer; preparation and saved export stay offline."""

import hashlib
import json
import os
from contextlib import nullcontext
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from time import monotonic
from typing import Any

from backend.cli.collection import CollectionError, _json, _path, _require

from .census_export import _native_dependencies
from .context import load_context
from .corpus_coverage import _coverage, _coverage_binding, _rag_coverage, _snapshot, _timing
from .opportunities import opportunities_report
from .relevance import relevance_report
from .relevance_material import _pointer
from .sources import Sources, digest


class CorpusSources(Sources):
    def __init__(self, root, max_bytes):
        super().__init__(root)
        self.max_bytes = max_bytes
        self.originals = {}

    def read_bytes(self, ref):
        ref = _object(ref, "Explicit corpus source reference required")
        path = _path(self.root, ref.get("path"))
        _require(path.stat().st_size <= self.max_bytes, "Source byte limit exceeded")
        raw = super().read_bytes(ref)
        name = Path(os.path.normpath(ref["path"])).as_posix()
        _require(name not in self.originals or self.originals[name] == raw, "Source drift: " + name)
        _require(
            sum(map(len, self.originals.values())) + (0 if name in self.originals else len(raw))
            <= self.max_bytes,
            "Total source byte limit exceeded",
        )
        self.originals[name] = raw
        return raw


def _ref(name, raw, schema=None):
    return {
        "path": name,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "availability": "available",
        "media_type": "application/json",
        **({"schema_version": schema} if schema else {}),
    }


def _bytes(value):
    return (json.dumps(value, indent=2, ensure_ascii=True, allow_nan=False) + "\n").encode()


def _fresh(destination):
    path = Path(destination)
    _require(not os.path.lexists(path), "Output directory must be fresh")
    return path.resolve()


def _configuration(value):
    value = _object(value, "Explicit measurement configuration required")
    fields = (
        "max_entities",
        "max_source_bytes",
        "statement_timeout_ms",
        "connect_timeout_seconds",
        "batch_size",
    )
    _require(
        isinstance(value, dict) and set(value) == {*fields, "timeout_seconds"},
        "Explicit measurement limits required",
    )
    for field in fields:
        _require(
            type(value[field]) is int and value[field] > 0, "Invalid measurement limit: " + field
        )
    timeout = value["timeout_seconds"]
    _require(type(timeout) in (int, float) and 0 < timeout <= 3600, "Invalid timeout_seconds")
    _require(value["batch_size"] <= value["max_entities"], "Batch size exceeds scan limit")
    return value


def _object(value, message) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CollectionError(message)
    return value


def _load(path):
    from backend.app.tripworld.database.policy import POLICY_VERSION
    from backend.app.tripworld.database.vectors import SPACE, SPACE_ID
    from backend.app.tripworld.retrieval.entities import ENTITY_VERSION, TEXT_VERSION

    path = Path(path).resolve()
    _require(path.stat().st_size <= 1024 * 1024, "Request metadata exceeds one MiB")
    raw = path.read_bytes()
    request = _json(raw)
    _require(
        request.get("schema_version") == "rtpeval_corpus_request_1",
        "Expected rtpeval_corpus_request_1",
    )
    config = _configuration(request.get("measurement_configuration"))
    sources = CorpusSources(path.parent, config["max_source_bytes"])
    sources.read_bytes(_ref(path.name, raw))
    declaration_ref = _object(
        request.get("declaration_ref"), "Explicit declaration reference required"
    )
    sources.read_ref(declaration_ref, "rtpeval_research_declaration_1")
    declaration_path = _path(sources.root, declaration_ref["path"])
    _require(
        declaration_path.parent == sources.root, "Declaration must use the request source root"
    )
    context = load_context(declaration_path)
    for binding in context.sources.manifest():
        sources.read_bytes(
            {**binding, "availability": "available", "media_type": "application/json"}
        )
    context.sources = sources
    relevance_report(context)
    for entry in context.census["attempts"] if context.census else []:
        for field in ("completion_ref", "provenance_ref"):
            ref = entry.get(field)
            if ref:
                native = sources.read_ref(ref)
                _native_dependencies(
                    sources, native, _path(sources.root, ref["path"]).parent, set()
                )
    cases = {(c["case_id"], c["revision"]): c for c in context.population["cases"]}
    key = _coverage_binding(request, cases)
    _timing(context, request, key)
    identity = _object(
        _snapshot(context, request.get("snapshot_identity")), "Snapshot identity required"
    )
    _require(
        identity["policy_version"] == POLICY_VERSION and identity["space_id"] == SPACE_ID,
        "Production policy/embedding space mismatch",
    )
    _rag_coverage(
        [request],
        [
            run
            for run in opportunities_report(context)["runs"]
            if (run["case_id"], run["case_revision"]) == key
        ],
    )
    source = _object(request.get("source"), "Explicit corpus source required")
    _require(
        isinstance(source, dict) and source.get("kind") in ("saved_dataset", "database"),
        "Explicit supported corpus source required",
    )
    _require(
        set(source) <= {"kind", "manifest_pointer", "dataset_ref", "embedding_index_ref"},
        "Unexpected corpus source field (connection secrets are not material)",
    )
    snapshot = sources.read_ref(identity["snapshot_ref"])
    manifest = (
        _pointer(snapshot, source["manifest_pointer"])
        if source.get("manifest_pointer")
        else snapshot
    )
    _require(
        isinstance(manifest, dict) and manifest.get("output_sha256") == identity["artifact_sha256"],
        "Pinned corpus manifest artifact mismatch",
    )
    _require(
        type(manifest.get("entity_count")) is int and manifest["entity_count"] >= 0,
        "Pinned entity count required",
    )
    inputs = _object(manifest.get("inputs"), "Pinned manifest inputs required")
    _require(
        inputs.get("retrieval_entity_builder_version") == ENTITY_VERSION
        and inputs.get("retrieval_text_template_version") == TEXT_VERSION,
        "Pinned entity/text policy mismatch",
    )
    if source["kind"] == "saved_dataset":
        dataset = source.get("dataset_ref")
        _require(
            isinstance(dataset, dict) and dataset.get("sha256") == identity["artifact_sha256"],
            "Dataset must be the exact pinned corpus artifact",
        )
        sources.read_bytes(dataset)
        index = sources.read_ref(
            source.get("embedding_index_ref"), "rtpeval_corpus_embedding_index_1"
        )
        _require(
            index.get("artifact_sha256") == identity["artifact_sha256"]
            and index.get("space_id") == SPACE_ID
            and index.get("configuration") == SPACE,
            "Saved embedding membership snapshot/space mismatch",
        )
        hashes = index.get("text_hashes")
        _require(
            isinstance(hashes, list)
            and all(
                isinstance(h, str) and len(h) == 64 and all(c in "0123456789abcdef" for c in h)
                for h in hashes
            ),
            "Explicit saved embedding text hashes required",
        )
    else:
        _require(
            set(source) <= {"kind", "manifest_pointer"},
            "Database source cannot substitute a saved dataset",
        )
    profile_ref = request.get("coverage_profile_ref")
    _coverage(context, {"coverage_refs": [], "coverage_profile_ref": profile_ref}, {})
    if profile_ref:
        profile = sources.read_ref(profile_ref)
        binding = next(
            (r for r in profile["cases"] if (r["case_id"], r["case_revision"]) == key), None
        )
        _require(
            binding is not None
            and binding["scope"] == request["scope"]
            and binding["scope_sha256"] == request["scope_sha256"]
            and profile["snapshot_identity"] == identity,
            "Coverage profile snapshot/scope mismatch",
        )
    return request, sources, context, manifest


def _publish(destination, sources, derived, receipt, validate=None):
    destination = _fresh(destination)
    _require(not sources.root.is_relative_to(destination), "Destination contains source root")
    destination.parent.mkdir(parents=True, exist_ok=True)
    files = dict(sources.originals)
    for name, raw in derived.items():
        _require(
            name not in files or files[name] == raw,
            "Derived filename collides with original: " + name,
        )
        files[name] = raw
    completion_ref = receipt.get("completion_ref")
    final_name = Path(completion_ref["path"]).name if completion_ref else None
    if final_name:
        _require(
            final_name in files
            and hashlib.sha256(files[final_name]).hexdigest() == completion_ref["sha256"],
            "Missing final corpus completion bytes",
        )
    with TemporaryDirectory(prefix=".rtpeval-corpus-", dir=destination.parent) as temporary:
        material = Path(temporary) / "material"
        for name, raw in files.items():
            target = _path(material, name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        if validate:
            validate(material)
        for name, raw in sources.originals.items():
            _require(
                _path(sources.root, name).read_bytes() == raw,
                "Source drift before publication: " + name,
            )
        _fresh(destination)
        destination.mkdir(exist_ok=False)
        for name, raw in files.items():
            if name == final_name:
                continue
            target = _path(destination / "material", name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            _require(target.read_bytes() == raw, "Published bytes differ: " + name)
        receipt = {
            **receipt,
            "source_bindings": [
                {"path": name, "sha256": hashlib.sha256(raw).hexdigest()}
                for name, raw in sorted(files.items())
            ],
            "source_root": "material",
        }
        (destination / "receipt.json").write_bytes(_bytes(receipt))
        if final_name:
            target = destination / "material" / final_name
            target.write_bytes(files[final_name])
            _require(target.read_bytes() == files[final_name], "Published completion bytes differ")
        if validate:
            validate(destination / "material")
    return receipt


def prepare(path, destination):
    _fresh(destination)
    request, sources, _, _ = _load(path)
    raw = sources.originals[Path(path).name]
    return _publish(
        destination,
        sources,
        {},
        {
            "schema_version": "rtpeval_corpus_preparation_1",
            "processing_status": "prepared",
            "request_ref": _ref("material/" + Path(path).name, raw, request["schema_version"]),
            "database_connections": 0,
        },
    )


def _saved_request(path, schema, status):
    path = Path(path).resolve()
    sources = Sources(path.parent)
    receipt = _json(path.read_bytes())
    _require(
        receipt.get("schema_version") == schema and receipt.get("processing_status") == status,
        "Saved producer receipt required",
    )
    ref = _object(receipt.get("request_ref"), "Saved request reference required")
    sources.read_ref(ref, "rtpeval_corpus_request_1")
    return _path(path.parent, ref["path"]), receipt


def _sidecar(request, manifest, evidence):
    from .context import timestamp
    from .corpus_scan import eligible

    _require(
        evidence.get("request_sha256") == evidence["request_ref"]["sha256"],
        "Measurement request digest mismatch",
    )
    started, finished = timestamp(evidence["started_at"]), timestamp(evidence["finished_at"])
    _require(started <= finished, "Measurement clock moved backwards")
    rows = evidence.get("observations")
    _require(isinstance(rows, list), "Saved scan observations required")
    identities = set()
    observed = 0
    for row in rows:
        identity = row["entity"]["retrieval_entity_id"]
        _require(
            isinstance(identity, str) and identity and identity not in identities,
            "Duplicate or missing measured entity identity",
        )
        identities.add(identity)
        observed += eligible(row, request, manifest)
    reason = evidence.get("termination_reason")
    _require(
        reason
        in (
            None,
            "scan_limit",
            "timeout",
            "retrieval_failure",
            "truncated_scan",
            "observation_byte_limit",
        ),
        "Unsupported measurement termination",
    )
    verified = evidence.get("source_verified")
    _require(
        type(verified) is bool and (verified or not rows),
        "Unverified source cannot claim observations",
    )
    _require(
        len(rows) <= request["measurement_configuration"]["max_entities"]
        and len(rows) <= manifest["entity_count"],
        "Saved observations exceed scan/source bound",
    )
    _require(
        sum(len(_bytes(row)) for row in rows)
        <= request["measurement_configuration"]["max_source_bytes"],
        "Saved observations exceed byte limit",
    )
    complete = reason is None
    _require(
        not complete or verified and len(rows) == manifest["entity_count"],
        "Incomplete scan cannot declare exact corpus count",
    )
    return {
        "schema_version": "rtpeval_research_corpus_coverage_1",
        **{
            key: request[key]
            for key in (
                "case_id",
                "case_revision",
                "input_sha256",
                "scope",
                "scope_sha256",
                "snapshot_identity",
                "declared_at",
                "timing_basis",
            )
        },
        "measurement_method": evidence["measurement_method"],
        "measured_at": evidence["finished_at"],
        "count_status": "complete" if complete else "partial" if rows else "unavailable",
        "eligible_entity_count": observed if complete else None,
        "observed_subtotal": observed if verified else None,
        "reasons": [] if complete else [reason],
    }


def _coverage_declaration(context, request, sidecar_ref):
    ref = context.declaration.get("track_refs", {}).get("relevance")
    material = (
        context.read_ref(ref)
        if ref
        else {
            "schema_version": "rtpeval_research_relevance_1",
            "population_id": context.population["population_id"],
            "population_revision": context.population["revision"],
            "profile_id": context.profile["profile_id"],
            "profile_revision": context.profile["revision"],
            "interest_inventory_refs": [],
            "review_refs": [],
            "coverage_refs": [],
        }
    )
    key = (request["case_id"], request["case_revision"])
    kept = [
        r
        for r in material["coverage_refs"]
        if (lambda value: (value["case_id"], value["case_revision"]) != key)(context.read_ref(r))
    ]
    material = {
        **material,
        "coverage_refs": [*kept, sidecar_ref],
        "coverage_profile_ref": request.get("coverage_profile_ref"),
    }
    prefix = sidecar_ref["path"].removesuffix("-sidecar.json")
    raw = _bytes(material)
    declaration = {
        **context.declaration,
        "track_refs": {
            k: v
            for k, v in context.declaration.get("track_refs", {}).items()
            if k == "opportunities"
        },
    }
    declaration["track_refs"]["relevance"] = _ref(
        prefix + "-relevance.json", raw, material["schema_version"]
    )
    return {prefix + "-relevance.json": raw, prefix + "-research.json": _bytes(declaration)}


def measure(path, destination, *, database=False, dsn_env=None, clock=None, timer=None):
    _fresh(destination)
    request_path, _ = _saved_request(path, "rtpeval_corpus_preparation_1", "prepared")
    request, sources, context, manifest = _load(request_path)
    kind = request["source"]["kind"]
    _require(
        kind == "database"
        and database
        and isinstance(dsn_env, str)
        and dsn_env
        or kind == "saved_dataset"
        and not database
        and dsn_env is None,
        "Database source requires explicit --database and --dsn-env; saved data must stay offline",
    )
    from .corpus_scan import dataset_rows, eligible

    clock = clock or (lambda: datetime.now(UTC))
    timer = timer or monotonic
    started, start_tick = clock().isoformat(), timer()
    raw_request = sources.originals[request_path.name]
    evidence = {
        "schema_version": "rtpeval_corpus_measurement_1",
        "request_sha256": hashlib.sha256(raw_request).hexdigest(),
        "request_ref": _ref(request_path.name, raw_request, request["schema_version"]),
        "measurement_method": kind + "_full_entity_scan_1",
        "started_at": started,
        "source_verified": False,
        "observations": [],
        "termination_reason": None,
        "source_identity": {
            "kind": kind,
            "artifact_sha256": request["snapshot_identity"]["artifact_sha256"],
            "manifest": manifest,
        },
    }
    config = request["measurement_configuration"]
    database_adapter = None
    if kind == "database":
        from .corpus_database import DatabaseRows

        database_adapter = DatabaseRows(
            request, manifest, dsn_env, timer=timer, deadline=start_tick + config["timeout_seconds"]
        )
        adapter = database_adapter
    else:
        adapter = nullcontext(dataset_rows(request, sources, manifest))
    try:
        with adapter as rows:
            evidence["source_verified"] = True
            if database_adapter is not None:
                evidence["source_identity"] = database_adapter.identity
            observed_bytes = 0
            for row in rows:
                if timer() - start_tick >= config["timeout_seconds"]:
                    evidence["termination_reason"] = "timeout"
                    break
                if len(evidence["observations"]) >= config["max_entities"]:
                    evidence["termination_reason"] = "scan_limit"
                    break
                observed_bytes += len(_bytes(row))
                if observed_bytes > config["max_source_bytes"]:
                    evidence["termination_reason"] = "observation_byte_limit"
                    break
                eligible(row, request, manifest)
                evidence["observations"].append(row)
            if (
                evidence["termination_reason"] is None
                and len(evidence["observations"]) != manifest["entity_count"]
            ):
                evidence["termination_reason"] = "truncated_scan"
    except (CollectionError, ValueError, KeyError, TypeError):
        raise
    except Exception as exc:
        evidence["termination_reason"] = (
            "timeout"
            if isinstance(exc, TimeoutError) or getattr(exc, "sqlstate", None) == "57014"
            else "retrieval_failure"
        )
        evidence["exception_type"] = type(exc).__name__
    evidence["finished_at"] = clock().isoformat()
    sidecar = _sidecar(request, manifest, evidence)
    prefix, suffix = "_corpus", 1
    names = ("measurement", "sidecar", "relevance", "research", "completion")
    while any(prefix + "-" + name + ".json" in sources.originals for name in names):
        suffix += 1
        prefix = "_corpus-" + str(suffix)
    evidence_raw = _bytes(evidence)
    measurement_ref = _ref(prefix + "-measurement.json", evidence_raw, evidence["schema_version"])
    completion = {
        "schema_version": "rtpeval_corpus_completion_1",
        "processing_status": "completed",
        "coverage_sha256": digest(sidecar),
        "measurement_ref": measurement_ref,
    }
    completion_raw = _bytes(completion)
    completion_ref = _ref(prefix + "-completion.json", completion_raw, completion["schema_version"])
    sidecar = {**sidecar, "producer_completion_ref": completion_ref}
    sidecar_raw = _bytes(sidecar)
    sidecar_ref = _ref(prefix + "-sidecar.json", sidecar_raw, sidecar["schema_version"])
    derived = {
        measurement_ref["path"]: evidence_raw,
        sidecar_ref["path"]: sidecar_raw,
        completion_ref["path"]: completion_raw,
        **_coverage_declaration(context, request, sidecar_ref),
    }
    declaration_ref = _ref(
        prefix + "-research.json",
        derived[prefix + "-research.json"],
        "rtpeval_research_declaration_1",
    )
    return _publish(
        destination,
        sources,
        derived,
        {
            "schema_version": "rtpeval_corpus_result_1",
            "processing_status": "completed",
            "request_ref": {**evidence["request_ref"], "path": "material/" + request_path.name},
            "measurement_ref": {**measurement_ref, "path": "material/" + measurement_ref["path"]},
            "completion_ref": {**completion_ref, "path": "material/" + completion_ref["path"]},
            "sidecar_ref": {**sidecar_ref, "path": "material/" + sidecar_ref["path"]},
            "declaration_ref": {**declaration_ref, "path": "material/" + declaration_ref["path"]},
            "count_status": sidecar["count_status"],
        },
        lambda root: relevance_report(load_context(root / declaration_ref["path"])),
    )


def export(path, destination):
    _fresh(destination)
    request_path, receipt = _saved_request(path, "rtpeval_corpus_result_1", "completed")
    request, sources, _, manifest = _load(request_path)
    wrapper = Sources(Path(path).resolve().parent)
    refs = {}
    for field, schema in (
        ("measurement_ref", "rtpeval_corpus_measurement_1"),
        ("completion_ref", "rtpeval_corpus_completion_1"),
        ("sidecar_ref", "rtpeval_research_corpus_coverage_1"),
        ("declaration_ref", "rtpeval_research_declaration_1"),
    ):
        ref = _object(receipt.get(field), "Saved source reference required: " + field)
        wrapper.read_ref(ref, schema)
        original = _path(wrapper.root, ref["path"])
        _require(
            original.parent == sources.root, "Measurement material must share the declaration root"
        )
        refs[field] = {**ref, "path": original.name}
    evidence = sources.read_ref(refs["measurement_ref"])
    sources.read_ref(evidence.get("request_ref"), "rtpeval_corpus_request_1")
    _require(
        evidence["request_ref"]["sha256"]
        == hashlib.sha256(sources.originals[request_path.name]).hexdigest(),
        "Saved measurement/request mismatch",
    )
    kind = request["source"]["kind"]
    _require(
        evidence["measurement_method"] == kind + "_full_entity_scan_1", "Foreign measurement method"
    )
    identity = evidence.get("source_identity", {})
    _require(
        identity.get("kind") == kind
        and identity.get("artifact_sha256") == request["snapshot_identity"]["artifact_sha256"]
        and identity.get("manifest") == manifest,
        "Saved measurement source identity mismatch",
    )
    if kind == "saved_dataset":
        from .corpus_scan import dataset_rows

        actual = iter(dataset_rows(request, sources, manifest))
        for saved in evidence["observations"]:
            _require(next(actual, None) == saved, "Saved observation differs from pinned dataset")
        if evidence["termination_reason"] is None:
            _require(next(actual, None) is None, "Saved scan is truncated")
    elif evidence["source_verified"]:
        from .corpus_database import validate_identity

        validate_identity(identity, request, manifest)
    expected = _sidecar(request, manifest, evidence)
    completion = sources.read_ref(refs["completion_ref"])
    _require(
        completion.get("processing_status") == "completed"
        and completion.get("coverage_sha256") == digest(expected)
        and completion.get("measurement_ref") == refs["measurement_ref"],
        "Saved corpus completion mismatch",
    )
    expected = {**expected, "producer_completion_ref": refs["completion_ref"]}
    _require(
        sources.read_ref(refs["sidecar_ref"]) == expected
        and receipt.get("count_status") == expected["count_status"],
        "Saved sidecar disagrees with measurement evidence",
    )
    declaration = sources.read_ref(refs["declaration_ref"])
    context = load_context(sources.root / refs["declaration_ref"]["path"])
    for binding in context.sources.manifest():
        sources.read_bytes(
            {**binding, "availability": "available", "media_type": "application/json"}
        )
    context.sources = sources
    relevance_report(context)
    material = context.read_ref(declaration["track_refs"]["relevance"])
    _require(
        refs["sidecar_ref"] in material["coverage_refs"]
        and material.get("coverage_profile_ref") == request.get("coverage_profile_ref"),
        "Export declaration does not use saved coverage/profile",
    )
    return _publish(
        destination,
        sources,
        {},
        {**receipt, "database_connections": 0, "export_mode": "offline_saved_measurement"},
        lambda root: relevance_report(load_context(root / refs["declaration_ref"]["path"])),
    )
