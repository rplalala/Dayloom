"""Evaluation-owned request plans, bounded injected acquisition and offline snapshots."""

import asyncio
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from .identity import identity_references
from .intake import _constant, _float, _pairs, _read
from .records import IntakeResult, text, thaw

PLAN_VERSION = "rtpeval_snapshot_plan_1"
SNAPSHOT_VERSION = "rtpeval_snapshot_1"


def _bytes(value):
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _hash(value):
    return hashlib.sha256(_bytes(value)).hexdigest()


def _prepared(intake):
    value = intake.to_dict() if isinstance(intake, IntakeResult) else thaw(intake)
    if not isinstance(value, dict) or value.get("status") != "accepted":
        raise ValueError("Snapshot planning requires accepted intake")
    return value


def _references(prepared, paired):
    return [
        r for r in identity_references(prepared) if paired or r["projection"] in (None, "final")
    ]


def _base(prepared, phase, paired):
    return {
        "schema_version": PLAN_VERSION,
        "batch_id": prepared["batch_id"],
        "batch_revision": prepared["revision"],
        "intake_hash": _hash(prepared),
        "phase": phase,
        "paired": paired,
        "references": [],
        "legs": [],
        "optional_availability": [
            {"group_id": g["group_id"], "projection": label, "available": value is not None}
            for g in prepared["inventory"]
            for label, value in g["runs"]["v3"]["optional"].items()
        ]
        if paired
        else [],
    }


def _request(requests, operation, parameters):
    request = {"operation": operation, "parameters": parameters}
    key = _hash(request)
    requests[key] = {"key": key, **request}
    return key


def build_identity_plan(intake, paired=False):
    """Retain original references while deduplicating identical independent requests."""
    prepared = _prepared(intake)
    from .identity_program import subject_bindings

    bindings = subject_bindings(prepared)
    plan, requests = _base(prepared, "identity", paired), {}
    for ref in _references(prepared, paired):
        item = {"reference_id": ref["reference_id"], "source": ref["source"], "requests": {}}
        if text(ref["name"]):
            item["requests"]["search"] = _request(
                requests,
                "places_search",
                {
                    "query": ref["name"],
                    "destination": ref["destination"],
                    "location": ref["location"] if text(ref["location"]) else None,
                    "page_size": 20,
                },
            )
        claimed = ref["claimed_place_id"] or bindings.get(
            (ref["group_id"], ref["source"].get("subject_id"))
        )
        if text(claimed):
            item["requests"]["details"] = _request(
                requests,
                "places_details",
                {
                    "place_id": claimed,
                },
            )
        item["reason"] = None if item["requests"] else "missing_usable_identity_claim"
        plan["references"].append(item)
    plan["requests"] = [requests[k] for k in sorted(requests)]
    return plan


class TransportFailure(Exception):
    """Safe failure category supplied by an independently owned transport."""

    def __init__(self, code):
        if code not in ("connection_failed", "transport_failed", "unsupported_context"):
            raise ValueError("Unsupported transport failure category")
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class Response:
    """Transport response; body is the exact received byte sequence."""

    status_code: int
    body: bytes


@dataclass(frozen=True)
class AcquisitionPolicy:
    max_sends: int
    max_attempts: int = 2
    timeout_seconds: float = 20
    retry_delay_seconds: float = 1

    def validate(self):
        for value in (self.max_sends, self.max_attempts):
            if type(value) is not int or value < 1:
                raise ValueError("Acquisition limits must be positive integers")
        import math

        for value in (self.timeout_seconds, self.retry_delay_seconds):
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                raise ValueError("Invalid acquisition timing limit")
        if self.timeout_seconds == 0:
            raise ValueError("Timeout must be positive")


def _now():
    return datetime.now(UTC).isoformat()


def _decode(raw):
    return json.loads(
        raw.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_constant, parse_float=_float
    )


def _validate_plan(plan):
    if not isinstance(plan, dict) or plan.get("schema_version") != PLAN_VERSION:
        raise ValueError("Unsupported snapshot plan")
    if plan.get("phase") not in ("identity", "evidence"):
        raise ValueError("Unsupported snapshot phase")
    keys = set()
    for request in plan["requests"]:
        expected = _hash({"operation": request["operation"], "parameters": request["parameters"]})
        if request["key"] != expected or expected in keys:
            raise ValueError("Invalid or duplicate request key")
        if request["operation"] not in ("places_search", "places_details", "route_matrix"):
            raise ValueError("Unsupported snapshot operation")
        parameters = request["parameters"]
        if request["operation"] == "places_search":
            if (
                not isinstance(parameters, dict)
                or set(parameters) != {"query", "destination", "location", "page_size"}
                or not text(parameters["query"])
                or not text(parameters["destination"])
                or parameters["page_size"] != 20
                or parameters["location"] is not None
                and not text(parameters["location"])
            ):
                raise ValueError("Invalid search parameters")
        elif request["operation"] == "places_details":
            if (
                not isinstance(parameters, dict)
                or set(parameters) != {"place_id"}
                or not text(parameters["place_id"])
            ):
                raise ValueError("Invalid details parameters")
        else:
            if set(parameters) != {
                "origin",
                "destination",
                "mode",
                "departure",
                "time_basis",
                "routing_options",
                "source_kind",
            }:
                raise ValueError("Invalid route parameters")
            _route_parameters(parameters)
        keys.add(expected)
    operations = {r["key"]: r["operation"] for r in plan["requests"]}
    refs = set()
    for ref in plan["references"]:
        if ref["reference_id"] in refs:
            raise ValueError("Duplicate snapshot reference")
        refs.add(ref["reference_id"])
        if not set(ref["requests"].values()) <= keys:
            raise ValueError("Unlinked reference request")
        if any(
            kind not in ("details", "search") or operations[key] != "places_" + kind
            for kind, key in ref["requests"].items()
        ):
            raise ValueError("Reference request operation mismatch")
    for leg in plan["legs"]:
        if leg.get("request_key") is not None and leg["request_key"] not in keys:
            raise ValueError("Unlinked route request")
        if leg.get("request_key") is not None and operations[leg["request_key"]] != "route_matrix":
            raise ValueError("Route request operation mismatch")


def _summary(request, status_code, raw):
    if not 200 <= status_code < 300:
        return {"status": "provider_error", "reason": "http_error"}
    try:
        value = _decode(raw)
    except (ValueError, UnicodeError, RecursionError):
        return {"status": "malformed", "reason": "invalid_json"}
    if request["operation"] != "route_matrix":
        if not isinstance(value, dict):
            return {"status": "malformed", "reason": "expected_object"}
        return {"status": "available", "payload": value}
    if not isinstance(value, list):
        return {"status": "malformed", "reason": "expected_matrix_array"}
    if len(value) != 1 or not isinstance(value[0], dict):
        return {"status": "incomplete", "reason": "missing_or_duplicate_matrix_elements"}
    element = value[0]
    if (
        type(element.get("originIndex")) is not int
        or type(element.get("destinationIndex")) is not int
        or (element["originIndex"], element["destinationIndex"]) != (0, 0)
    ):
        return {"status": "incomplete", "reason": "unexpected_matrix_indices"}
    return {"status": "available", "element": element}


async def acquire_snapshot(plan, directory, transport, policy):
    """Acquire only through the caller's injected transport; publish a new snapshot."""
    _validate_plan(plan)
    policy.validate()
    plan = _decode(_bytes(plan))
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=False)
    (root / "raw").mkdir()
    started = _now()
    records, sends = [], 0
    for request in sorted(plan["requests"], key=lambda r: r["key"]):
        record = {"key": request["key"], "attempts": []}
        record["summary"] = {"status": "unavailable", "reason": "send_budget_exhausted"}
        for number in range(1, policy.max_attempts + 1):
            if sends >= policy.max_sends:
                break
            sent = _now()
            sends += 1
            attempt = {"attempt": number, "requested_at": sent}
            retryable = False
            try:
                response = await asyncio.wait_for(
                    transport(_decode(_bytes(request))), policy.timeout_seconds
                )
            except (TransportFailure, TimeoutError) as exc:
                code = exc.code if isinstance(exc, TransportFailure) else "timeout"
                attempt.update(error_code=code, raw=None, status_code=None)
                record["summary"] = {"status": "provider_error", "reason": code}
                retryable = code != "unsupported_context"
            else:
                if (
                    not isinstance(response, Response)
                    or type(response.status_code) is not int
                    or not 100 <= response.status_code <= 599
                    or not isinstance(response.body, bytes)
                ):
                    raise ValueError("Invalid injected transport response")
                name = "raw/" + request["key"] + "-" + str(number) + ".bin"
                with (root / name).open("xb") as handle:
                    handle.write(response.body)
                attempt.update(
                    status_code=response.status_code,
                    raw={
                        "path": name,
                        "sha256": hashlib.sha256(response.body).hexdigest(),
                    },
                )
                record["summary"] = _summary(request, response.status_code, response.body)
                retryable = response.status_code == 429 or response.status_code >= 500
            attempt["retrieved_at"] = _now()
            record["attempts"].append(attempt)
            if not retryable or number == policy.max_attempts or sends == policy.max_sends:
                break
            await asyncio.sleep(policy.retry_delay_seconds)
        records.append(record)
    manifest = {
        "schema_version": SNAPSHOT_VERSION,
        "plan": plan,
        "plan_hash": _hash(plan),
        "policy": asdict(policy),
        "started_at": started,
        "finished_at": _now(),
        "planner_to_oracle_lag_seconds": None,
        "lag_reason": "planner_times_not_supplied",
        "records": records,
        "ledger": {
            "namespace": "oracle",
            "actual_sends": sends,
            "retry_sends": sum(max(0, len(r["attempts"]) - 1) for r in records),
            "requested_matrix_elements": sum(
                len(r["attempts"])
                for r in records
                if next(q for q in plan["requests"] if q["key"] == r["key"])["operation"]
                == "route_matrix"
            ),
        },
    }
    with (root / "manifest.json").open("xb") as handle:
        handle.write(_bytes(manifest))
    return load_snapshot(root, expected_plan=plan)


def _utc_time(value):
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
            raise ValueError("UTC timestamp required")
        return parsed
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError("Invalid snapshot timestamp") from exc


def load_snapshot(directory, expected_plan=None):
    """Validate and replay persisted observations without any transport dependency."""
    root = Path(directory).resolve()
    value, _ = _read(root / "manifest.json")
    if value.get("schema_version") == "rtpeval_imported_snapshot_1":
        from .snapshot_import import load_imported_snapshot

        return load_imported_snapshot(root, expected_plan)
    if value.get("schema_version") != SNAPSHOT_VERSION:
        raise ValueError("Unsupported snapshot schema")

    def read_raw(name):
        relative = Path(name)
        path = (root / relative).resolve()
        if relative.is_absolute() or relative.drive or not path.is_relative_to(root):
            raise ValueError("Snapshot path escapes root")
        return path.read_bytes()

    return _validate_acquired_snapshot(value, read_raw, expected_plan)


def _validate_acquired_snapshot(value, read_raw, expected_plan=None):
    """Validate original acquisition bytes, including archive-backed import copies."""
    started = _utc_time(value.get("started_at"))
    finished = _utc_time(value.get("finished_at"))
    if finished < started:
        raise ValueError("Invalid snapshot collection time order")
    plan = value["plan"]
    _validate_plan(plan)
    if value["plan_hash"] != _hash(plan) or (expected_plan is not None and plan != expected_plan):
        raise ValueError("Snapshot plan mismatch")
    requests = {r["key"]: r for r in plan["requests"]}
    if len(value["records"]) != len(requests) or {r["key"] for r in value["records"]} != set(
        requests
    ):
        raise ValueError("Snapshot request coverage mismatch")
    policy = AcquisitionPolicy(**value["policy"])
    policy.validate()
    actual_sends = sum(len(r["attempts"]) for r in value["records"])
    ledger = {
        "namespace": "oracle",
        "actual_sends": actual_sends,
        "retry_sends": sum(max(0, len(r["attempts"]) - 1) for r in value["records"]),
        "requested_matrix_elements": sum(
            len(r["attempts"])
            for r in value["records"]
            if requests[r["key"]]["operation"] == "route_matrix"
        ),
    }
    if value["ledger"] != ledger or actual_sends > policy.max_sends:
        raise ValueError("Snapshot ledger mismatch")
    for record in value["records"]:
        if len(record["attempts"]) > policy.max_attempts:
            raise ValueError("Snapshot attempt limit exceeded")
        if not record["attempts"] and (
            actual_sends != policy.max_sends
            or record["summary"] != {"status": "unavailable", "reason": "send_budget_exhausted"}
        ):
            raise ValueError("Invalid unrequested snapshot record")
        derived = None
        previous = started
        for index, attempt in enumerate(record["attempts"], 1):
            if attempt["attempt"] != index:
                raise ValueError("Invalid attempt sequence")
            sent = _utc_time(attempt.get("requested_at"))
            received = _utc_time(attempt.get("retrieved_at"))
            if not previous <= sent <= received <= finished:
                raise ValueError("Invalid snapshot attempt time order")
            previous = received
            ref = attempt["raw"]
            if ref is None:
                if attempt.get("error_code") not in (
                    "connection_failed",
                    "transport_failed",
                    "unsupported_context",
                    "timeout",
                ):
                    raise ValueError("Invalid persisted transport failure")
                derived = {"status": "provider_error", "reason": attempt["error_code"]}
                continue
            raw = read_raw(ref["path"])
            if hashlib.sha256(raw).hexdigest() != ref["sha256"]:
                raise ValueError("Snapshot raw hash mismatch")
            derived = _summary(requests[record["key"]], attempt["status_code"], raw)
        if derived is not None and derived != record["summary"]:
            raise ValueError("Snapshot derived evidence mismatch")
    return value


def _place(raw):
    if not isinstance(raw, dict):
        return {}
    name = raw.get("displayName")
    return {
        "place_id": raw.get("id"),
        "display_name": name.get("text") if isinstance(name, dict) else None,
        "formatted_address": raw.get("formattedAddress"),
        "business_status": raw.get("businessStatus"),
        **({"address_components": raw["addressComponents"]} if "addressComponents" in raw else {}),
    }


def identity_evidence(snapshot, *, historical=False):
    """Convert independent snapshot observations to Ticket 03's existing wire."""
    from .identity import EVIDENCE_VERSION

    plan = snapshot["plan"]
    if plan["phase"] != "identity":
        raise ValueError("Identity snapshot required")
    requests = {r["key"]: r for r in plan["requests"]}
    observed = {r["key"]: r for r in snapshot["records"]}
    records = []
    imported = snapshot.get("schema_version") == "rtpeval_imported_snapshot_1"
    for ref in plan["references"]:
        item = {
            "reference_id": ref["reference_id"],
            "observation_id": _hash({"snapshot": _hash(snapshot), "ref": ref["reference_id"]}),
            "source_kind": "reused_google_places" if imported else "independent_google_places",
            **(
                {
                    "import_provenance": {
                        "snapshot_sha256": _hash(snapshot),
                        "paired": True,
                        "current_sends": 0,
                    }
                }
                if imported
                else {}
            ),
        }
        for kind, key in ref["requests"].items():
            record, parameters = observed[key], requests[key]["parameters"]
            summary = record["summary"]
            data = {
                "status": summary["status"],
                "snapshot_request_key": key,
                "attempts": record["attempts"],
                **({"acquisition_origin": record["origin"]} if imported else {}),
            }
            if kind == "details":
                data["requested_place_id"] = parameters["place_id"]
            else:
                data.update(query=parameters["query"], requested_page_size=parameters["page_size"])
            if summary["status"] == "available":
                data["retrieved_at"] = record["attempts"][-1]["retrieved_at"]
                payload = summary["payload"]
                if kind == "details":
                    data["place"] = _place(payload)
                else:
                    raw = payload.get("places", [])
                    if not isinstance(raw, list):
                        data["status"] = "malformed"
                    else:
                        data.update(
                            actual_result_count=len(raw), candidates=[_place(p) for p in raw]
                        )
                        if not historical and "nextPageToken" in payload:
                            data["next_page_token"] = payload["nextPageToken"]
            item[kind] = data
        records.append(item)
    return {
        "schema_version": EVIDENCE_VERSION,
        "batch_id": plan["batch_id"],
        "batch_revision": plan["batch_revision"],
        "records": records,
    }


def build_evidence_plan(intake, identity_report, route_contexts, paired=False):
    """Inventory canonical venues and candidate legs without choosing departure semantics."""
    from .identity import ASSOCIATION_POLICY_VERSION, IDENTITY_VERSION
    from .identity_adoption import needs_v0_replay
    from .identity_llm import needs_llm_replay
    from .identity_program import VERSIONED_TARGET_POLICIES, needs_versioned_replay
    from .identity_targets import versioned_references
    from .place_association import associated_place_id
    from .preparation import identity_ready

    prepared = _prepared(intake)
    report = identity_report.to_dict() if hasattr(identity_report, "to_dict") else identity_report
    replay_policy = (
        needs_v0_replay(report) or needs_llm_replay(report) or needs_versioned_replay(report)
    )
    if replay_policy and not identity_ready(prepared, report):
        raise ValueError("Identity report requires verified replay")
    if (
        report.get("schema_version") != IDENTITY_VERSION
        or not replay_policy
        and report.get("association_policy_version") != ASSOCIATION_POLICY_VERSION
        or report.get("batch_id") != prepared["batch_id"]
        or report.get("batch_revision") != prepared["revision"]
        or report.get("source_hashes") != prepared["source_hashes"]
    ):
        raise ValueError("Identity report batch/source mismatch")
    references = (
        versioned_references(prepared)
        if report.get("association_policy_version") in VERSIONED_TARGET_POLICIES
        else identity_references(prepared)
    )
    expected = {r["reference_id"]: r for r in references}
    identities = {r["reference_id"]: r for r in report["records"]}
    if set(expected) != set(identities) or len(identities) != len(report["records"]):
        raise ValueError("Identity report reference coverage mismatch")
    for rid, record in identities.items():
        if record["source"] != expected[rid]["source"]:
            raise ValueError("Identity report source mismatch")
        if record["resolution"] not in ("resolved", "unresolved") or (
            (record["resolution"] == "resolved") != text(record.get("canonical_place_id"))
        ):
            raise ValueError("Invalid identity resolution")
    plan, requests = _base(prepared, "evidence", paired), {}
    plan["identity_report_hash"] = _hash(report)
    for ref in references:
        if not paired and ref["projection"] not in (None, "final"):
            continue
        record = identities[ref["reference_id"]]
        pid = associated_place_id(record)
        item = {
            "reference_id": ref["reference_id"],
            "source": ref["source"],
            "requests": {},
            "canonical_place_id": record["canonical_place_id"],
            "reason": record["reason"],
            **({"associated_place_id": pid} if "place_association" in record else {}),
        }
        if pid is not None:
            item["requests"]["details"] = _request(requests, "places_details", {"place_id": pid})
        plan["references"].append(item)
    for group in prepared["inventory"]:
        for version, run in group["runs"].items():
            projections = [("final", run["final"])]
            if paired:
                projections.extend((k, v) for k, v in run["optional"].items() if v is not None)
            for label, projection in projections:
                for leg in projection["legs"]:
                    origin, destination = (
                        leg["from_source"]["record_id"],
                        leg["to_source"]["record_id"],
                    )
                    key = _hash({"origin_reference": origin, "destination_reference": destination})
                    plan["legs"].append(
                        {
                            "leg_id": key,
                            "origin_reference": origin,
                            "destination_reference": destination,
                            "group_id": group["group_id"],
                            "version": version,
                            "projection": label,
                            "adjacency_status": leg["adjacency_status"],
                            "request_key": None,
                            "reason": "route_context_missing",
                        }
                    )
    if not isinstance(route_contexts, list):
        raise ValueError("Route contexts must be an array")
    by_leg = {leg["leg_id"]: leg for leg in plan["legs"]}
    seen = set()
    for context in route_contexts:
        if (
            not isinstance(context, dict)
            or context.get("leg_id") not in by_leg
            or context["leg_id"] in seen
        ):
            raise ValueError("Duplicate or unlinked route context")
        seen.add(context["leg_id"])
        leg = by_leg[context["leg_id"]]
        parameters = _route_parameters(context)
        for side, reference in (
            ("origin", "origin_reference"),
            ("destination", "destination_reference"),
        ):
            adopted = associated_place_id(identities[leg[reference]])
            if adopted is None or parameters[side]["place_id"] != adopted:
                raise ValueError("Route endpoint identity mismatch or unresolved")
        leg["request_key"] = _request(requests, "route_matrix", parameters)
        leg["reason"] = None
    plan["requests"] = [requests[k] for k in sorted(requests)]
    return plan


def _route_parameters(context):
    import math

    parameters = {
        k: context[k]
        for k in (
            "origin",
            "destination",
            "mode",
            "departure",
            "time_basis",
            "routing_options",
            "source_kind",
        )
    }
    if parameters["source_kind"] != "independent_evaluation_context":
        raise ValueError("Independent route context required")
    if parameters["mode"] not in ("WALK", "TRANSIT", "DRIVE"):
        raise ValueError("Unsupported route mode")
    if parameters["time_basis"] == "explicit_departure":
        if not text(parameters["departure"]):
            raise ValueError("Explicit departure required")
        departure = datetime.fromisoformat(parameters["departure"])
        if departure.utcoffset() is None:
            raise ValueError("Aware departure required; no timezone inferred")
    elif parameters["time_basis"] == "time_independent":
        if parameters["departure"] is not None:
            raise ValueError("Time-independent query cannot claim a departure")
    else:
        raise ValueError("Explicit route time basis required")
    allowed = {
        "routing_preference",
        "avoid_tolls",
        "avoid_highways",
        "avoid_ferries",
        "language_code",
        "region_code",
    }
    options = parameters["routing_options"]
    if (
        not isinstance(options, dict)
        or not set(options) <= allowed
        or any(type(v) not in (str, bool) for v in options.values())
    ):
        raise ValueError("Unsupported routing options")
    for side in ("origin", "destination"):
        point = parameters[side]
        if not isinstance(point, dict) or set(point) != {
            "place_id",
            "latitude",
            "longitude",
            "evidence_sha256",
        }:
            raise ValueError("Explicit endpoint coordinates and evidence hash required")
        if not text(point["place_id"]) or not _sha(point["evidence_sha256"]):
            raise ValueError("Invalid endpoint provenance")
        for field, limit in (("latitude", 90), ("longitude", 180)):
            n = point[field]
            if type(n) not in (int, float) or not math.isfinite(n) or abs(n) > limit:
                raise ValueError("Invalid route coordinate")
    return _decode(_bytes(parameters))


def _sha(value):
    return (
        isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)
    )
