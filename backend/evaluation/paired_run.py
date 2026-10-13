"""Source-bound paired preparation and offline verification using native scorers."""

import hashlib
import math
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path

from .cost_report import amount, estimate, money, validate_prices
from .intake import _artifact, _read, load_batch
from .records import canonical_digest
from .snapshot import (
    _bytes,
    build_identity_plan,
    identity_evidence,
    load_snapshot,
)

VERSION = "rtpeval_pair_acquisition_preparation_1"
CONTEXT_FILES = {
    "schedule_context": "context",
    "occupancy_reviews": "occupancy_reviews",
    "route_reviews": "route_reviews",
    "density_reviews": "density_reviews",
    "correspondence_reviews": "correspondence_reviews",
}


def now():
    return datetime.now(UTC).isoformat()


def save(root, name, value):
    path = Path(root) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_bytes(value))


def fresh(directory):
    path = Path(directory)
    if os.path.lexists(path):
        raise ValueError("Fresh paired output directory required")
    return path.resolve()


def file_inventory(directory):
    files = {}
    for path in Path(directory).rglob("*"):
        if path.is_symlink():
            raise ValueError("Paired artifacts must not contain symlinks")
        if path.is_file():
            files[str(path.relative_to(directory))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return files


def options_checked(value, *, allow_zero=False):
    fields = {"max_google_sends", "max_cost_usd", "timeout_seconds", "total_timeout_seconds"}
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError("Explicit paired limits required; no credentials or model configuration")
    minimum = 0 if allow_zero else 1
    if type(value["max_google_sends"]) is not int or value["max_google_sends"] < minimum:
        raise ValueError("Positive integer Google request ceiling required")
    if not allow_zero and amount(value["max_cost_usd"]) == 0:
        raise ValueError("Positive USD reference spend ceiling required")
    amount(value["max_cost_usd"])
    for key in ("timeout_seconds", "total_timeout_seconds"):
        if type(value[key]) not in (int, float) or not math.isfinite(value[key]) or value[key] <= 0:
            raise ValueError("Positive finite timeout required: " + key)
    return value


def selection_checked(intake, selection):
    if not isinstance(selection, dict) or set(selection) != {
        "schema_version",
        "batch_id",
        "batch_revision",
        "runs",
    }:
        raise ValueError("Explicit paired selection required")
    if (selection["schema_version"], selection["batch_id"], selection["batch_revision"]) != (
        "rtpeval_pair_selection_1",
        intake["batch_id"],
        intake["revision"],
    ):
        raise ValueError("Foreign paired selection")
    expected = []
    for group in intake["inventory"]:
        run = group["runs"]["v3"]["final"]["context"]
        expected.append(
            {
                "group_id": group["group_id"],
                "run_id": run["run_id"],
                "input_sha256": group["input_sha256"],
                "requirement_spec_sha256": group["requirement_spec_sha256"],
                "result_sha256": run["artifact_sha256"],
                "stage_pointers": {"draft": "/v3/draft", "final_primary": "/v3/final_primary"},
            }
        )
    if selection["runs"] != expected:
        raise ValueError("Selected V3 run/stage/input/RequirementSpec binding mismatch")


def unresolved_identity(intake):
    from .identity import EVIDENCE_VERSION
    from .identity_program import resolve_versioned_identities

    return resolve_versioned_identities(
        intake,
        {
            "schema_version": EVIDENCE_VERSION,
            "batch_id": intake["batch_id"],
            "batch_revision": intake["revision"],
            "records": [],
        },
    ).to_dict()


def available(intake):
    return any(g["runs"]["v3"]["paired_available"] for g in intake["inventory"])


def routes(intake, identity, context, identity_snapshot=None):
    from .routes import prepare_routes

    result = prepare_routes(
        intake,
        identity,
        **{key: context[key] for key in ("schedule_context", "occupancy_reviews", "route_reviews")},
        paired=True,
        identity_snapshot_directory=identity_snapshot,
    ).to_dict()
    if result["status"] != "complete":
        raise ValueError(
            "Paired route preparation requires correction: " + str(result["diagnostics"])
        )
    return result


def validate_context(intake, context):
    from ._route_inputs import route_reviews
    from ._schedule_preparation import _occupancy_reviews, _validate_spec
    from .daily_density import prepare_density_policies
    from .preparation import schedule_timezones

    zones = schedule_timezones(intake, context["schedule_context"])
    _occupancy_reviews(intake, context["occupancy_reviews"])
    reviewed_routes = route_reviews(intake, context["route_reviews"])
    prepare_density_policies(intake, context["density_reviews"])
    for group in intake["inventory"]:
        _validate_spec(group)
        if not group["runs"]["v3"]["paired_available"]:
            continue
        gid = group["group_id"]
        if gid not in zones or gid not in reviewed_routes:
            raise ValueError("Independent schedule context and route review required for " + gid)
        density = context["density_reviews"] or {}
        if group["input"].get("additional_preferences") and gid not in {
            row["group_id"] for row in density.get("groups", [])
        }:
            raise ValueError("Independent density review required for " + gid)


def lineage(intake, identity, source, context):
    from .v3_correspondence import prepare_v3_correspondence, read_v3_result_sources

    result = prepare_v3_correspondence(
        intake, identity, read_v3_result_sources(intake, source), context["correspondence_reviews"]
    ).to_dict()
    if result["status"] != "complete":
        raise ValueError("Paired lineage requires correction: " + str(result["diagnostics"]))
    return result


def request_billing(request, wire):
    billing = {"endpoint": wire["endpoint"], "field_mask": wire["field_mask"]}
    if request["operation"] == "route_matrix":
        billing.update(
            travel_mode=request["parameters"]["mode"],
            routing_preference=request["parameters"]["routing_options"].get("routing_preference"),
        )
    return billing


def price_inventory(identity_plan, evidence_plan, prices, stamp, *, deferred, route_preparation):
    from ._route_rules import DEFAULT_OPTIONS
    from .evaluation_transport import DETAILS_MASK, ROUTE_MASK, google_wire

    events = []
    for request in [*identity_plan["requests"], *evidence_plan["requests"]]:
        wire = google_wire(request)
        events.append((request["operation"], 1, request_billing(request, wire)))
    pending = []
    if deferred:
        # Native occurrence rows bound venue sends; native reviewed modes bound route sends.
        pending.append(
            (
                "places_details",
                len(evidence_plan["references"]),
                {"endpoint": "details", "field_mask": DETAILS_MASK},
            )
        )
        for result in route_preparation["results"]:
            for leg in result["legs"]:
                if leg["mode"] is not None:
                    pending.append(
                        (
                            "route_matrix",
                            1,
                            {
                                "endpoint": "computeRouteMatrix",
                                "field_mask": ROUTE_MASK,
                                "travel_mode": leg["mode"],
                                "routing_preference": DEFAULT_OPTIONS[leg["mode"]][
                                    "routing_options"
                                ].get("routing_preference"),
                            },
                        )
                    )
    total = amount("0")
    for operation, count, billing in [*events, *pending]:
        if not count:
            continue
        event = {
            "provider": "google",
            "operation": "place_details" if operation == "places_details" else operation,
            "outcome": "completed",
            "element_count": 1 if operation == "route_matrix" else None,
            "billing_context": billing,
        }
        value, _, reason = estimate(event, "provider", {"timing": {"started_at": stamp}}, prices)
        if value is None:
            raise ValueError("Paired acquisition price unavailable: " + reason)
        total += value * count
    return {
        "identity_request_count": len(identity_plan["requests"]),
        "evidence_status": "deferred_until_identity" if deferred else "exact",
        "evidence_request_count": None if deferred else len(evidence_plan["requests"]),
        "evidence_request_upper_bound": sum(count for _, count, _ in pending)
        if deferred
        else len(evidence_plan["requests"]),
        "estimated_cost_usd": money(total),
        "estimate_basis": "occurrence_upper_bound" if deferred else "native_request_inventory",
    }


def prepare(
    manifest,
    directory,
    *,
    selection,
    options,
    prices,
    context,
    files,
    identity_snapshot=None,
    snapshot=None,
):
    root, source = fresh(directory), Path(manifest).resolve()
    for path in (identity_snapshot, snapshot):
        if path and root.is_relative_to(Path(path).resolve()):
            raise ValueError("Paired destination must be outside cached source directories")
    intake = load_batch(source).to_dict()
    if intake["status"] != "accepted":
        raise ValueError("Qualified source manifest required")
    selection_checked(intake, selection)
    validate_prices(prices)
    if prices["currency"] != "USD":
        raise ValueError("Paired spend ceiling requires USD prices")
    validate_context(intake, context)
    identity_plan = build_identity_plan(intake, paired=True)
    identity = unresolved_identity(intake)
    cached = {}
    if identity_snapshot:
        frozen = load_snapshot(identity_snapshot, expected_plan=identity_plan)
        from .identity_program import resolve_versioned_identities

        identity = resolve_versioned_identities(intake, identity_evidence(frozen)).to_dict()
        cached["identity"] = str(Path(identity_snapshot).resolve())
    route_preparation = routes(intake, identity, context, identity_snapshot)
    evidence_plan = route_preparation["evidence_plan"]
    if snapshot:
        if not identity_snapshot:
            raise ValueError("Saved paired evidence requires its exact identity snapshot")
        load_snapshot(snapshot, expected_plan=evidence_plan)
        cached["evidence"] = str(Path(snapshot).resolve())
    imported = any(
        load_snapshot(path)["schema_version"] == "rtpeval_imported_snapshot_1"
        for path in cached.values()
    )
    if imported and set(cached) != {"identity", "evidence"}:
        raise ValueError("Imported evidence requires both phases; no automatic supplemental sends")
    options_checked(options, allow_zero=imported)
    lineage(intake, identity, source, context)
    stamp = now()
    inventory = (
        price_inventory(
            identity_plan,
            evidence_plan,
            prices,
            stamp,
            deferred=available(intake) and not identity_snapshot,
            route_preparation=route_preparation,
        )
        if available(intake) and not imported
        else {}
    )
    if not available(intake):
        inventory = {
            "identity_request_count": 0,
            "evidence_status": "pair_unavailable",
            "evidence_request_count": 0,
            "evidence_request_upper_bound": 0,
            "estimated_cost_usd": "0",
            "estimate_basis": "no_available_pair",
        }
    if imported:
        inventory = {
            "identity_request_count": len(identity_plan["requests"]),
            "evidence_status": "exact" if available(intake) else "pair_unavailable",
            "evidence_request_count": len(evidence_plan["requests"]),
            "evidence_request_upper_bound": len(evidence_plan["requests"]),
            "estimated_cost_usd": "0",
            "estimate_basis": "offline_import_zero_current_sends",
        }
    pins = {str(source): hashlib.sha256(source.read_bytes()).hexdigest()}
    original = _read(source)[0]
    native_names = {source.name}
    for group in original["groups"]:
        refs = [
            group["input_ref"],
            group["requirement_spec_ref"],
            *(
                ref
                for run in group["selected_runs"].values()
                for key, ref in run.items()
                if key.endswith("_ref")
            ),
        ]
        for ref in refs:
            schema = ref.get("schema_version")
            _, sha = _artifact(
                source.parent, ref, schema if schema and schema.startswith("rtpeval_") else None
            )
            name = str((source.parent / ref["path"]).resolve().relative_to(source.parent))
            native_names.add(name)
            pins[str(source.parent / name)] = sha
    if original.get("projection_reviews_ref"):
        ref = original["projection_reviews_ref"]
        _, sha = _artifact(source.parent, ref, "rtpeval_reviews_1")
        native_names.add(ref["path"])
        pins[str((source.parent / ref["path"]).resolve())] = sha
    for path in files.values():
        if path:
            p = Path(path).resolve()
            pins[str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
    expected_files = {
        "selection": selection,
        "options": options,
        "prices": prices,
        **{cli.replace("_", "-"): context[native] for native, cli in CONTEXT_FILES.items()},
    }
    for name, path in files.items():
        if path and _read(Path(path))[0] != expected_files[name]:
            raise ValueError("Paired context changed during preparation")
    for directory_path in cached.values():
        for p in Path(directory_path).rglob("*"):
            if p.is_symlink():
                raise ValueError("Cached evidence symlinks are forbidden")
            if p.is_file():
                pins[str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
    implementation = [
        *Path(__file__).parent.glob("*.py"),
        Path(__file__).parents[1] / "cli/pair_acquire.py",
        Path(__file__).parents[1] / "model_references.py",
        Path(__file__).parents[1] / "pace_policy.py",
    ]
    value = {
        "schema_version": VERSION,
        "status": "prepared",
        "scope": "selected_v3_paired_evidence",
        "prepared_at": stamp,
        "directory": str(root),
        "manifest": str(source),
        "native_manifest": "material/native/" + source.name,
        "intake": intake,
        "selection": selection,
        "options": options,
        "prices": prices,
        "context": context,
        "identity_plan": identity_plan,
        "evidence_plan": evidence_plan,
        "route_preparation": route_preparation,
        "request_inventory": inventory,
        "cached_snapshots": cached,
        "source_bindings": pins,
        "input_files": {name: str(Path(path).resolve()) for name, path in files.items() if path},
        "implementation_hashes": {
            str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest() for p in implementation
        },
        "max_model_sends": 0,
        "max_retries": 0,
        **({"execution_mode": "offline_reuse", "max_current_google_sends": 0} if imported else {}),
    }
    root.mkdir(parents=True, exist_ok=False)
    for name in native_names:
        target = root / "material/native" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((source.parent / name).read_bytes())
    for name, path in files.items():
        if path:
            target = root / "material/context" / (name + ".json")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(Path(path).read_bytes())
    for name, path in cached.items():
        shutil.copytree(path, root / "material/cache" / name)
    for path, sha in pins.items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != sha:
            raise ValueError("Paired source changed during preparation")
    value["material_hashes"] = file_inventory(root / "material")
    if load_batch(root / value["native_manifest"]).to_dict() != intake:
        raise ValueError("Copied paired source differs")
    for name, expected in expected_files.items():
        if (
            expected is not None
            and _read(root / "material/context" / (name + ".json"))[0] != expected
        ):
            raise ValueError("Copied paired context differs")
    value["content_sha256"] = canonical_digest(value)
    save(root, "preparation.json", value)
    return value


def verify(directory):
    root = Path(directory).resolve()
    value = _read(root / "preparation.json")[0]
    if (
        value.get("schema_version") != VERSION
        or value.get("directory") != str(root)
        or canonical_digest({k: v for k, v in value.items() if k != "content_sha256"})
        != value.get("content_sha256")
    ):
        raise ValueError("Paired preparation binding mismatch")
    for path, sha in {**value["source_bindings"], **value["implementation_hashes"]}.items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != sha:
            raise ValueError("Paired source/implementation changed since preparation")
    if file_inventory(root / "material") != value["material_hashes"]:
        raise ValueError("Paired material inventory differs")
    if load_batch(Path(value["manifest"])).to_dict() != value["intake"]:
        raise ValueError("Original paired source differs from frozen intake")
    expected_files = {
        "selection": value["selection"],
        "options": value["options"],
        "prices": value["prices"],
        **{
            cli.replace("_", "-"): value["context"][native] for native, cli in CONTEXT_FILES.items()
        },
    }
    if set(value["input_files"]) != {
        name for name, data in expected_files.items() if data is not None
    }:
        raise ValueError("Paired original input inventory differs")
    for name, path in value["input_files"].items():
        if str(Path(path).resolve()) not in value["source_bindings"] or (
            _read(Path(path))[0] != expected_files[name]
            or _read(root / "material/context" / (name + ".json"))[0] != expected_files[name]
        ):
            raise ValueError("Paired frozen options/reviews differ from originals")
    if load_batch(root / value["native_manifest"]).to_dict() != value["intake"]:
        raise ValueError("Copied paired sources changed")
    selection_checked(value["intake"], value["selection"])
    imported = value.get("execution_mode") == "offline_reuse"
    options_checked(value["options"], allow_zero=imported)
    validate_context(value["intake"], value["context"])
    validate_prices(value["prices"])
    identity_plan = build_identity_plan(value["intake"], paired=True)
    if value["identity_plan"] != identity_plan:
        raise ValueError("Prepared paired identity plan differs from native sources")
    identity = unresolved_identity(value["intake"])
    cache = root / "material/cache/identity" if "identity" in value["cached_snapshots"] else None
    if cache:
        from .identity_program import resolve_versioned_identities

        identity = resolve_versioned_identities(
            value["intake"], identity_evidence(load_snapshot(cache, expected_plan=identity_plan))
        ).to_dict()
    route_preparation = routes(value["intake"], identity, value["context"], cache)
    plan = route_preparation["evidence_plan"]
    if plan != value["evidence_plan"] or route_preparation != value["route_preparation"]:
        raise ValueError("Prepared paired evidence plan differs from native sources")
    if "evidence" in value["cached_snapshots"]:
        load_snapshot(root / "material/cache/evidence", expected_plan=plan)
    actual_imported = any(
        load_snapshot(root / "material/cache" / phase)["schema_version"]
        == "rtpeval_imported_snapshot_1"
        for phase in value["cached_snapshots"]
    )
    if (
        imported != actual_imported
        or actual_imported
        and (
            set(value["cached_snapshots"]) != {"identity", "evidence"}
            or value.get("max_current_google_sends") != 0
        )
    ):
        raise ValueError("Paired offline import mode/source mismatch")
    return value


def preflight(directory, approved_sha256):
    value = verify(directory)
    if value["content_sha256"] != approved_sha256:
        raise ValueError("Exact paired preparation approval required")
    if os.path.lexists(Path(directory) / "execution"):
        raise ValueError("Paired execution already consumed; no retry or resume")
    if available(value["intake"]):
        price_inventory(
            value["identity_plan"],
            value["evidence_plan"],
            value["prices"],
            now(),
            deferred=value["request_inventory"]["evidence_status"] == "deferred_until_identity",
            route_preparation=value["route_preparation"],
        )
    return value


def usage_summary(usage, prices):
    from .cost_report import build_cost_report

    return {
        "actual_google_sends": len(usage["provider_events"]),
        "actual_model_sends": 0,
        "retries": 0,
        "actual_billing": None,
        "reserved_reference_cost_usd": reserved_cost(usage, prices),
        "cost": build_cost_report([{"sha256": canonical_digest(usage), "usage": usage}], prices),
        "raw": usage,
    }


def reserved_cost(usage, prices):
    total = amount("0")
    for event in usage["provider_events"]:
        value, _, reason = estimate({**event, "outcome": "completed"}, "provider", usage, prices)
        if value is None:
            raise ValueError("Paired reservation cannot be replayed: " + reason)
        total += value
    return money(total)


def capture_status(preparation, execution):
    if not available(preparation["intake"]):
        return "pair_unavailable"
    partial = any(
        record["summary"]["status"] != "available"
        for phase in ("identity", "evidence")
        for record in load_snapshot(execution / (phase + "-snapshot"))["records"]
    )
    return "partial" if partial else "available"


def native_report(preparation, execution, identity, plan, generated_at):
    from .v3_correspondence import read_v3_result_sources
    from .v3_pair_report import build_v3_pair_report

    has_pair = available(preparation["intake"])
    report = build_v3_pair_report(
        preparation["intake"],
        identity,
        execution / "evidence-snapshot" if has_pair else None,
        **preparation["context"],
        expected_plan=plan if has_pair else None,
        identity_snapshot_directory=execution / "identity-snapshot" if has_pair else None,
        result_sources=read_v3_result_sources(
            preparation["intake"], Path(preparation["directory"]) / preparation["native_manifest"]
        ),
        edit_provenance=_read(execution / "edit-provenance.json")[0],
        generated_at=generated_at,
    ).to_dict()
    if report["status"] != "complete":
        raise ValueError("Native pair report requires correction: " + str(report["diagnostics"]))
    return report


def write_receipt(execution, digest):
    files = {
        str(p.relative_to(execution)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in execution.rglob("*")
        if p.is_file()
    }
    save(execution, "receipt.json", {"preparation_sha256": digest, "files": files})


def verify_receipt(execution, digest):
    receipt = _read(execution / "receipt.json")[0]
    files = file_inventory(execution)
    files.pop("receipt.json", None)
    if receipt != {"preparation_sha256": digest, "files": files}:
        raise ValueError("Paired closed receipt differs")


def verify_journal(preparation, execution, inventory, usage):
    from .evaluation_transport import google_wire, usage_event

    events = [
        _read(p)[0] for p in sorted((execution / "http").glob("*.json"), key=lambda p: int(p.stem))
    ]
    if [usage_event(e) for e in events] != usage["provider_events"] or usage["model_calls"]:
        raise ValueError("Paired HTTP journal/usage mismatch")
    if [event["event_id"] for event in events] != [str(i) for i in range(1, len(events) + 1)]:
        raise ValueError("Paired HTTP event sequence mismatch")
    by_id = {event["event_id"]: event for event in events}
    owned = []
    if set(inventory["phases"]) - {"identity", "evidence"}:
        raise ValueError("Unknown paired acquisition phase")
    for phase in ("identity", "evidence"):
        if phase not in inventory["phases"]:
            continue
        record = inventory["phases"][phase]
        if record["status"] not in ("acquired", "reused_verified_snapshot", "stopped"):
            raise ValueError("Invalid paired phase status")
        plan = record["plan"]
        if not plan["paired"] or plan["phase"] != phase:
            raise ValueError("Paired phase/plan mismatch")
        if phase == "identity" and plan != preparation["identity_plan"]:
            raise ValueError("Paired identity inventory mismatch")
        if plan != _read(execution / (phase + "-plan.json"))[0]:
            raise ValueError("Paired saved phase plan mismatch")
        requests = {r["key"]: r for r in plan["requests"]}
        ids = record["event_ids"]
        if len({by_id[eid]["request_key"] for eid in ids}) != len(ids):
            raise ValueError("Paired acquisition must not retry a request")
        owned.extend(ids)
        for eid in ids:
            event = by_id[eid]
            request = requests[event["request_key"]]
            wire = google_wire(request)
            operation = (
                "place_details"
                if request["operation"] == "places_details"
                else request["operation"]
            )
            billing = request_billing(request, wire)
            if (
                event["provider"] != "google"
                or event["request"] != wire
                or event["operation"] != operation
                or event["billing_context"] != billing
                or event["element_count"] != (1 if operation == "route_matrix" else None)
            ):
                raise ValueError("Paired HTTP context differs from native request")
            raw_path = execution / "http" / (eid + ".bin")
            if event.get("status_code") is not None and not raw_path.is_file():
                raise ValueError("Paired HTTP response missing")
        if record["status"] == "stopped":
            raw_directory = execution / (phase + "-snapshot") / "raw"
            expected_raw = set()
            for eid in ids:
                event = by_id[eid]
                if event.get("status_code") is None:
                    continue
                name = event["request_key"] + "-1.bin"
                expected_raw.add(name)
                captured = (execution / "http" / (eid + ".bin")).read_bytes()
                if (raw_directory / name).read_bytes() != captured:
                    raise ValueError("Paired stopped response differs from partial snapshot")
            if {p.name for p in raw_directory.glob("*")} != expected_raw:
                raise ValueError("Paired stopped raw response inventory mismatch")
        if record["status"] in ("acquired", "reused_verified_snapshot"):
            snapshot = load_snapshot(execution / (phase + "-snapshot"), expected_plan=plan)
            if record["status"] == "reused_verified_snapshot":
                if ids or phase not in preparation["cached_snapshots"]:
                    raise ValueError("Unbound cached paired evidence")
                original = load_snapshot(
                    Path(preparation["directory"]) / "material/cache" / phase, expected_plan=plan
                )
                if snapshot != original:
                    raise ValueError("Copied cached snapshot differs")
                continue
            attempts = [
                (r["key"], attempt)
                for r in sorted(snapshot["records"], key=lambda r: r["key"])
                for attempt in r["attempts"]
            ]
            if len(attempts) != len(ids):
                raise ValueError("Paired HTTP/snapshot attempt coverage mismatch")
            for (key, attempt), eid in zip(attempts, ids, strict=True):
                event = by_id[eid]
                if (
                    event["request_key"] != key
                    or event.get("status_code") != attempt["status_code"]
                ):
                    raise ValueError("Paired snapshot/HTTP response mismatch")
                if attempt["raw"]:
                    captured = (execution / "http" / (eid + ".bin")).read_bytes()
                    if hashlib.sha256(captured).hexdigest() != attempt["raw"]["sha256"]:
                        raise ValueError("Paired captured response differs")
                if (
                    not attempt["requested_at"]
                    <= event["requested_at"]
                    <= event.get("retrieved_at", attempt["retrieved_at"])
                    <= attempt["retrieved_at"]
                ):
                    raise ValueError("Paired HTTP retrieval time differs")
    if (
        owned != [event["event_id"] for event in events]
        or len(events) > preparation["options"]["max_google_sends"]
    ):
        raise ValueError("Paired journal inventory or send ceiling mismatch")
    if amount(reserved_cost(usage, preparation["prices"])) > amount(
        preparation["options"]["max_cost_usd"]
    ):
        raise ValueError("Paired recorded sends exceed reference spend ceiling")


def replay(directory):
    from .identity_program import resolve_versioned_identities

    preparation = verify(directory)
    execution = Path(directory).resolve() / "execution"
    verify_receipt(execution, preparation["content_sha256"])
    saved, usage = _read(execution / "report.json")[0], _read(execution / "usage.json")[0]
    inventory = _read(execution / "inventory.json")[0]
    if saved["preparation_sha256"] != preparation["content_sha256"] or saved[
        "usage"
    ] != usage_summary(usage, preparation["prices"]):
        raise ValueError("Paired execution report/usage binding mismatch")
    verify_journal(preparation, execution, inventory, usage)
    if saved["processing_status"] == "stopped":
        return saved
    has_pair = available(preparation["intake"])
    if inventory["pair_available"] != has_pair:
        raise ValueError("Paired source availability mismatch")
    if saved["evidence_status"] != capture_status(preparation, execution):
        raise ValueError("Paired capture status differs")
    if has_pair:
        evidence = identity_evidence(
            load_snapshot(
                execution / "identity-snapshot", expected_plan=preparation["identity_plan"]
            )
        )
        identity = resolve_versioned_identities(preparation["intake"], evidence).to_dict()
        if evidence != _read(execution / "identity-evidence.json")[0]:
            raise ValueError("Paired identity evidence replay differs")
        route_preparation = routes(
            preparation["intake"], identity, preparation["context"], execution / "identity-snapshot"
        )
        plan = route_preparation["evidence_plan"]
        if (
            route_preparation != _read(execution / "route-preparation.json")[0]
            or plan != _read(execution / "evidence-plan.json")[0]
        ):
            raise ValueError("Paired evidence inventory replay differs")
        load_snapshot(execution / "evidence-snapshot", expected_plan=plan)
    else:
        identity, plan = unresolved_identity(preparation["intake"]), preparation["evidence_plan"]
        if inventory["phases"] or usage["provider_events"]:
            raise ValueError("Unavailable pair must not dispatch")
    if identity != _read(execution / "identity-report.json")[0]:
        raise ValueError("Paired identity report replay differs")
    edit = lineage(
        preparation["intake"],
        identity,
        Path(directory) / preparation["native_manifest"],
        preparation["context"],
    )
    if edit != _read(execution / "edit-provenance.json")[0]:
        raise ValueError("Paired edit lineage replay differs")
    pair = native_report(preparation, execution, identity, plan, saved["generated_at"])
    if pair != saved["pair"] or pair != _read(execution / "pair-report.json")[0]:
        raise ValueError("Paired native diagnostic replay differs")
    return saved


def export(directory, destination):
    """Publish a fresh portable native report handoff after offline source replay."""
    root = fresh(destination)
    if root.is_relative_to(Path(directory).resolve()):
        raise ValueError("Paired export must be outside its source directory")
    report = replay(directory)
    if report["processing_status"] != "complete":
        raise ValueError("Stopped acquisition cannot export a completed pair handoff")
    source = Path(directory).resolve()
    preparation = verify(source)
    root.mkdir(parents=True, exist_ok=False)
    for name in ("material", "execution"):
        shutil.copytree(source / name, root / name)
    save(root, "source-preparation.json", preparation)
    pair = {
        "identity": "execution/identity-report.json",
        "edit_provenance": "execution/edit-provenance.json",
    }
    descriptor = {}

    def ref(name):
        path = root / name
        value, sha = _read(path)
        return {
            "path": name,
            "sha256": sha,
            "media_type": "application/json",
            "availability": "available",
            **({"schema_version": value["schema_version"]} if "schema_version" in value else {}),
        }

    descriptor["manifest_ref"] = ref(preparation["native_manifest"])
    descriptor["report_ref"] = ref("execution/pair-report.json")
    descriptor["identity_ref"] = ref(pair["identity"])
    descriptor["edit_provenance_ref"] = ref(pair["edit_provenance"])
    for native, cli in CONTEXT_FILES.items():
        if preparation["context"][native] is not None:
            name = "material/context/" + cli.replace("_", "-") + ".json"
            pair[cli] = name
            descriptor[native + "_ref"] = ref(name)
    if available(preparation["intake"]):
        for name in ("snapshot", "identity_snapshot"):
            path = "execution/" + ("evidence" if name == "snapshot" else "identity") + "-snapshot"
            pair[name] = path
            descriptor[name + "_ref"] = ref(path + "/manifest.json")
        pair["expected_plan"] = "execution/evidence-plan.json"
        descriptor["expected_plan_ref"] = ref(pair["expected_plan"])
    handoff = {
        "schema_version": "rtpeval_pair_acquisition_export_1",
        "processing_status": "complete",
        "preparation_sha256": preparation["content_sha256"],
        "evidence_status": report["evidence_status"],
        "manifest": preparation["native_manifest"],
        "suite_pair": pair,
        "research_pair": descriptor,
    }
    # Completion marker is written only after every copied byte matches the source.
    for name in ("material", "execution"):
        for path in (source / name).rglob("*"):
            if (
                path.is_file()
                and path.read_bytes() != (root / path.relative_to(source)).read_bytes()
            ):
                raise ValueError("Paired handoff copy differs from source")
    verify(source)
    save(root, "handoff.json", handoff)
    write_receipt(root, preparation["content_sha256"])
    return handoff
