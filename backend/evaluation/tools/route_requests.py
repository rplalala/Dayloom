"""Offline V0 request inventory; neither preparation nor preflight sends requests."""

import math
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from ..identity import resolve_identities
from ..identity_adoption import load_v0_material
from ..identity_program import COMMON_POLICY_VERSION, VERSIONED_TARGET_POLICIES
from ..identity_program import POLICY_VERSION as IDENTITY_POLICY_VERSION
from ..intake import _read
from ..place_association import associated_place_id
from ..preparation import identity_ready
from ..records import MaterialError, canonical_digest, freeze, require, thaw
from ..routes import prepare_routes
from ..snapshot import build_identity_plan, load_snapshot

PACKAGE_VERSION = "rtpeval_v0_route_requests_2"
DETAILS_MASK = "id,location"
ROUTES_MASK = "originIndex,destinationIndex,status,condition,distanceMeters,duration,fallbackInfo"
PRICE_URL = "https://developers.google.com/maps/billing-and-pricing/pricing"
SKU_URL = "https://developers.google.com/maps/billing-and-pricing/sku-details"
MATRIX_URL = "https://developers.google.com/maps/documentation/routes/reference/rest/v2/TopLevel/computeRouteMatrix"
COVERAGE_URL = "https://developers.google.com/maps/coverage"
DETAILS_URL = "https://developers.google.com/maps/documentation/places/web-service/place-details"


def _request(operation, parameters, mask):
    value = {"operation": operation, "parameters": parameters, "field_mask": mask}
    return {
        "key": canonical_digest(value),
        **value,
        "billable_units": 1,
        "sku": "Places API Place Details Essentials"
        if operation == "places_details"
        else "Routes: Compute Route Matrix Essentials",
        "estimate_usd": "0.005000",
    }


def _money(units):
    return format(Decimal(units) * Decimal("0.005"), ".6f")


def _budget(details, ready, conditional, region_code):
    return {
        "currency": "USD",
        "checked_on": "2026-10-07" if region_code == "AU" else "2026-10-05",
        "price_url": PRICE_URL,
        "sku_url": SKU_URL,
        "rate_per_1000_usd": "5.00",
        "assumptions": "Global first paid tier; no free credits or volume discounts assumed",
        "billable_units": "One Details request; one element per directed 1x1 Routes matrix",
        "proposed_usd": _money(details + ready),
        "unready_routes_usd": _money(conditional),
        "inventory_ceiling_usd": _money(details + ready + conditional),
        "planning_upper_bound_usd": "0.060000",
        "actual_billing": None,
        "unavailable_billing": ["account tier", "remaining free usage", "taxes", "actual invoice"],
    }


def _provider(leg, now, region_code):
    mode = leg["mode"]
    checks = []
    if mode in ("WALK", "DRIVE") and region_code == "KR":
        checks.append("regional_" + mode.lower() + "_unavailable_or_low_quality")
    elif mode == "WALK":
        pass
    elif mode == "TRANSIT":
        checks.append("regional_transit_coverage_unverified")
        if leg["evaluation_departure"] is None:
            checks.append("departure_unresolved")
        elif datetime.fromisoformat(leg["evaluation_departure"]) < now:
            checks.append("historical_matrix_transit_availability_unverified")
    else:
        checks.append("provider_mode_unsupported")
    return {
        "region_code": region_code,
        "checked_on": "2026-10-07" if region_code == "AU" else "2026-10-05",
        "coverage_url": COVERAGE_URL,
        "method_url": MATRIX_URL,
        "readiness_checks": checks,
        "temporal_semantics": "Explicit original departure for TRANSIT; WALK is time independent",
        "limitations": [
            "AU walking coverage is documented; exact pair success is not yet observed"
            if region_code == "AU"
            else "KR walking/driving coverage is unavailable or low quality, not proof of no route",
            "The country coverage table omits transit; API regional support is unverified",
            "Matrix permits past TRANSIT timestamps but documents no guaranteed schedule horizon",
            "Compute Routes 7/100-day horizon is not copied to Compute Route Matrix",
            "Time-independent results cannot certify conditions on the itinerary date",
        ],
    }


def _route_request(leg, points):
    origin, destination = leg["canonical_endpoints"]
    if None in (origin, destination) or origin == destination or leg["applicability"] == "N/A":
        return None
    parameters = {
        "origin_place_id": origin,
        "destination_place_id": destination,
        "mode": leg["mode"],
        "departure": leg["evaluation_departure"] if leg["mode"] == "TRANSIT" else None,
        "time_basis": "explicit_departure" if leg["mode"] == "TRANSIT" else "time_independent",
        "routing_options": {},
    }
    request = _request("route_matrix", parameters, ROUTES_MASK)
    request["method"] = "POST"
    request["url"] = "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"
    request["body"] = None
    if (
        origin in points
        and destination in points
        and (
            leg["mode"] == "WALK"
            or leg["mode"] == "TRANSIT"
            and parameters["departure"] is not None
        )
    ):
        body = {"travelMode": leg["mode"]}
        for side, pid in (("origins", origin), ("destinations", destination)):
            point = points[pid]
            body[side] = [
                {
                    "waypoint": {
                        "location": {"latLng": {k: point[k] for k in ("latitude", "longitude")}}
                    }
                }
            ]
        if parameters["departure"] is not None:
            body["departureTime"] = parameters["departure"]
        request["body"] = body
        request["coordinate_evidence"] = {
            pid: points[pid]["evidence_sha256"] for pid in (origin, destination)
        }
        request["key"] = canonical_digest(
            {
                "parameters": parameters,
                "body": body,
                "field_mask": ROUTES_MASK,
                "coordinate_evidence": request["coordinate_evidence"],
            }
        )
    return request


@dataclass(frozen=True)
class RouteRequestPackage:
    status: str
    data: object

    def to_dict(self):
        return {"status": self.status, **thaw(self.data)}


def _details_plan(intake, identity, requests, links):
    plan = build_identity_plan(intake)
    plan.update(
        requests=[],
        references=[],
        legs=[],
        acquisition_field_mask=DETAILS_MASK,
        identity_report_hash=canonical_digest(identity),
    )
    for request in requests:
        wire = {k: request[k] for k in ("operation", "parameters")}
        key = canonical_digest(wire)
        plan["requests"].append({"key": key, **wire})
        for rid in links[request["parameters"]["place_id"]]:
            plan["references"].append({"reference_id": rid, "requests": {"details": key}})
    return plan


def _supplied_details(directory, plan, now):
    snapshot = load_snapshot(directory, expected_plan=plan)
    require(
        snapshot["policy"]["max_attempts"] == 1, "details", "Zero-retry Details evidence required"
    )
    requests = {r["key"]: r for r in plan["requests"]}
    points, diagnostics = [], []
    for record in snapshot["records"]:
        pid = requests[record["key"]]["parameters"]["place_id"]
        reason = "details_unavailable"
        if record["summary"]["status"] == "available":
            payload = record["summary"]["payload"]
            attempt = record["attempts"][-1]
            require(
                datetime.fromisoformat(attempt["retrieved_at"]) <= now,
                "details/time",
                "Details evidence is later than preparation",
            )
            point = payload.get("location")
            if payload.get("id") != pid:
                reason = "details_returned_identity_mismatch"
            elif not isinstance(point, dict) or any(
                type(point.get(k)) not in (int, float)
                or not math.isfinite(point[k])
                or abs(point[k]) > limit
                for k, limit in (("latitude", 90), ("longitude", 180))
            ):
                reason = "coordinates_invalid"
            else:
                source = {
                    "request_key": record["key"],
                    "raw_sha256": attempt["raw"]["sha256"],
                    "pointer": "/location",
                    "retrieved_at": attempt["retrieved_at"],
                }
                points.append(
                    {
                        "place_id": pid,
                        **{k: point[k] for k in ("latitude", "longitude")},
                        "source_kind": "independent_details_snapshot",
                        "observations": [source],
                        "evidence_sha256": canonical_digest(
                            {"place_id": pid, "coordinate": point, "source": source}
                        ),
                    }
                )
                continue
        diagnostics.append({"place_id": pid, "reason": reason})
    _, digest = _read(Path(directory) / "manifest.json")
    return points, diagnostics, digest, snapshot["ledger"]["actual_sends"]


def _reused_coordinates(directory, points, now):
    snapshot = load_snapshot(directory)
    require(
        datetime.fromisoformat(snapshot["finished_at"]) <= now,
        "snapshot/time",
        "Identity evidence is later than preparation",
    )
    requests = {r["key"]: r for r in snapshot["plan"]["requests"]}
    observations = {r["key"]: r for r in snapshot["records"]}
    valid, diagnostics = [], []
    for point in points:
        mismatch = False
        for source in point["observations"]:
            key = source["request_key"]
            if requests[key]["operation"] == "places_details":
                payload = observations[key]["summary"]["payload"]
                mismatch |= not (
                    requests[key]["parameters"]["place_id"]
                    == payload.get("id")
                    == point["place_id"]
                )
        if mismatch:
            diagnostics.append(
                {"place_id": point["place_id"], "reason": "details_returned_identity_mismatch"}
            )
        else:
            valid.append(point)
    return valid, diagnostics


def prepare_v0_route_requests(
    bundle_path,
    identity_report,
    *,
    prepared_at,
    schedule_context=None,
    occupancy_reviews=None,
    route_reviews=None,
    details_snapshot_directory=None,
    legacy=False,
    region_code="KR",
):
    """Replay current identities by default and retain every original V0 leg blocker."""
    base = {"schema_version": PACKAGE_VERSION, "legs": [], "requests": [], "diagnostics": []}
    try:
        now = datetime.fromisoformat(prepared_at)
        require(
            isinstance(region_code, str) and region_code in ("KR", "AU"),
            "provider/region_code",
            "Explicit KR or AU provider region required",
        )
        require(type(legacy) is bool, "legacy", "Explicit boolean replay policy required")
        require(
            now.utcoffset() is not None, "prepared_at", "Offset-aware preparation time required"
        )
        supplied_identity = (
            identity_report.to_dict()
            if hasattr(identity_report, "to_dict")
            else thaw(identity_report)
            if identity_report is not None
            else None
        )
        historical_wire = legacy and (
            supplied_identity is None
            or supplied_identity.get("association_policy_version") not in VERSIONED_TARGET_POLICIES
        )
        material = load_v0_material(None, bundle_path, historical=historical_wire)
        intake = thaw(material.intake)
        identity = (
            resolve_identities(intake, thaw(material.evidence)).to_dict()
            if supplied_identity is None
            else supplied_identity
        )
        require(
            legacy
            or identity.get("association_policy_version")
            in (IDENTITY_POLICY_VERSION, COMMON_POLICY_VERSION),
            "identity/policy",
            "Current version-specific identity report required; historical replay is explicit",
        )
        require(
            identity_ready(intake, identity)
            and identity.get("evidence_hash") == canonical_digest(thaw(material.evidence)),
            "identity",
            "Replay-verified V0 report required",
        )
        bundle, _ = _read(Path(bundle_path))
        if region_code == "AU":
            group = next(g for g in intake["inventory"] if g["group_id"] == bundle["group_id"])
            require(
                group["input"]["destination"].rsplit(",", 1)[-1].strip().casefold() == "australia",
                "provider/region_code",
                "AU profile requires an original destination explicitly declaring Australia",
            )
        root = (Path(bundle_path).resolve().parent / bundle["artifact_root"]).resolve()
        snapshot_directory = (root / bundle["artifacts"]["snapshot"]["path"]).parent
        routes = prepare_routes(
            intake,
            identity,
            schedule_context,
            occupancy_reviews,
            route_reviews,
            identity_snapshot_directory=snapshot_directory,
        ).to_dict()
        require(routes["status"] == "complete", "routes", str(routes["diagnostics"]))
        references = {r["reference_id"]: r for r in identity["records"]}
        selected = next(
            r
            for r in routes["results"]
            if r["version"] == "v0" and r["group_id"] == bundle["group_id"]
        )
        used = set()
        for original in selected["legs"]:
            ends = [original[k]["record_id"] for k in ("from_source", "to_source")]
            used.update(pid for pid in original["canonical_endpoints"] if pid is not None)
            blockers = [
                {
                    "reference_id": rid,
                    "reason": references[rid]["reason"],
                    "grounding_verdict": references[rid].get("grounding_verdict"),
                }
                for rid in ends
                if associated_place_id(references[rid]) is None
            ]
            base["legs"].append(
                {
                    **original,
                    "identity_eligible": not blockers,
                    "identity_blockers": blockers,
                    "identity_endpoints": [
                        {
                            key: references[rid][key]
                            for key in (
                                "reference_id",
                                "resolution",
                                "canonical_place_id",
                                "reason",
                                "grounding_verdict",
                                "original_claim",
                                "candidate_correspondence",
                                "place_association",
                            )
                            if key in references[rid]
                        }
                        for rid in ends
                    ],
                    "verdict": "N/A" if original["applicability"] == "N/A" else "UNKNOWN",
                }
            )
        points = [r for r in routes["coordinate_preparation"]["records"] if r["place_id"] in used]
        points, reused_diagnostics = _reused_coordinates(snapshot_directory, points, now)
        routes["coordinate_preparation"]["diagnostics"].extend(reused_diagnostics)
        point_map = {p["place_id"]: p for p in points}
        links = {
            pid: sorted(
                {
                    r["reference_id"]
                    for r in identity["records"]
                    if r["reference_id"]
                    in {
                        s[k]["record_id"]
                        for s in selected["legs"]
                        for k in ("from_source", "to_source")
                    }
                    and associated_place_id(r) == pid
                }
            )
            for pid in used
        }
        blocked = {
            r["place_id"]
            for r in routes["coordinate_preparation"]["diagnostics"]
            if r["reason"] != "coordinates_missing"
        }
        for pid in sorted(used - point_map.keys() - blocked):
            request = _request("places_details", {"place_id": pid}, DETAILS_MASK)
            request.update(
                method="GET",
                url="https://places.googleapis.com/v1/places/" + pid,
                reference_ids=links[pid],
                state="ready_for_approval",
            )
            base["requests"].append(request)
        base["details_plan"] = _details_plan(intake, identity, base["requests"], links)
        details_digest, observed_sends = None, 0
        coordinate_diagnostics = routes["coordinate_preparation"]["diagnostics"]
        reused_count = len(points)
        if details_snapshot_directory is not None:
            extra, diagnostic, details_digest, observed_sends = _supplied_details(
                details_snapshot_directory, base["details_plan"], now
            )
            points.extend(extra)
            point_map.update({p["place_id"]: p for p in extra})
            # Supplied bad/missing evidence remains blocked; never propose retries to fill a quota.
            base["requests"] = []
            coordinate_diagnostics = [
                d for d in coordinate_diagnostics if d["place_id"] not in used - blocked
            ] + diagnostic
        for leg in base["legs"]:
            provider = _provider(leg, now, region_code)
            leg["provider"] = provider
            leg["coordinate_ready"] = all(pid in point_map for pid in leg["canonical_endpoints"])
            leg["readiness_checks"] = list(
                dict.fromkeys(
                    leg["reasons"]
                    + provider["readiness_checks"]
                    + (["independent_coordinates_missing"] if not leg["coordinate_ready"] else [])
                    + (["continuous_window_unresolved"] if leg["selected_interval"] is None else [])
                )
            )
            leg["request"] = _route_request(leg, point_map)
            leg["request_state"] = (
                "blocked"
                if not leg["identity_eligible"]
                or region_code == "AU"
                and leg["request"] is None
                or leg["mode"] not in (("WALK", "TRANSIT") if region_code == "AU" else ("TRANSIT",))
                else "conditional"
                if leg["readiness_checks"]
                else "ready_for_approval"
            )
            if leg["request"]:
                leg["request"]["state"] = leg["request_state"]
                leg["request"]["leg_ids"] = [leg["leg_id"]]
        details = len(base["requests"])
        route_requests = {}
        for leg in base["legs"]:
            request = leg["request"]
            if request is not None:
                if request["key"] in route_requests:
                    previous = route_requests[request["key"]]
                    previous["leg_ids"].append(leg["leg_id"])
                    # A duplicate link cannot promote a blocked/conditional query to ready.
                    if request["state"] == "blocked" or previous["state"] == "ready_for_approval":
                        previous["state"] = request["state"]
                else:
                    route_requests[request["key"]] = thaw(freeze(request))
        base["requests"].extend(route_requests[key] for key in sorted(route_requests))
        ready = sum(r["state"] == "ready_for_approval" for r in route_requests.values())
        unready = sum(r["state"] != "ready_for_approval" for r in route_requests.values())
        conditional = sum(r["state"] == "conditional" for r in route_requests.values())
        require(details <= 8 and len(base["legs"]) <= 4, "limits", "Planning ceiling exceeded")
        base.update(
            prepared_at=prepared_at,
            identity_policy={
                "association_policy_version": identity["association_policy_version"],
                "legacy": legacy,
                "current_v0_model_result_present": identity.get(
                    "identity_versioned_replay", {}
                ).get("model_result")
                is not None,
                "report_origin": "derived_without_model_result"
                if identity_report is None
                else "supplied",
            },
            replay_inputs={
                "legacy": legacy,
                "schedule_context": schedule_context,
                "occupancy_reviews": occupancy_reviews,
                "route_reviews": route_reviews,
                "details_snapshot_directory": str(Path(details_snapshot_directory).resolve())
                if details_snapshot_directory is not None
                else None,
            },
            source_hashes={
                "material": canonical_digest(bundle),
                "identity": canonical_digest(identity),
                "route_preparation": canonical_digest(routes),
                "supplied_details": details_digest,
            },
            coordinates=points,
            reference_links=links,
            coordinate_diagnostics=coordinate_diagnostics,
            budget=_budget(details, ready, unready, region_code),
            limits={
                "max_details_sends": details,
                "max_routes_sends": ready,
                "planning_details_ceiling": 8,
                "planning_routes_ceiling": 4,
                "search_sends": 0,
                "model_sends": 0,
                "retries": 0,
                "single_call_timeout_seconds": 20,
                "total_deadline_seconds": 300,
                "max_cost_usd": _money(details + ready),
                "stops": [
                    "Missing explicit execution approval",
                    "Changed frozen inputs or inventory",
                    "Identity or coordinate mismatch",
                    "Provider/time unsupported",
                    "Any timeout or provider error",
                    "Any counter, cost or deadline limit",
                ],
            },
            authorization="preparation_only_not_live_approved",
            counts={
                "actual_sends": 0,
                "details_requests": details,
                "ready_routes": ready,
                "conditional_routes": conditional,
                "blocked_route_requests": unready - conditional,
                "directed_route_requests": len(route_requests),
                "provider_supported_legs": sum(
                    not leg["provider"]["readiness_checks"] for leg in base["legs"]
                ),
                "missing_coordinate_venues": len(used - point_map.keys()),
                "identity_eligible_legs": sum(leg["identity_eligible"] for leg in base["legs"]),
                "eligible_endpoint_occurrences": sum(
                    pid is not None for leg in base["legs"] for pid in leg["canonical_endpoints"]
                ),
                "eligible_endpoint_venues": len(used),
                "coordinate_ready_legs": sum(leg["coordinate_ready"] for leg in base["legs"]),
                "reused_coordinates": reused_count,
                "supplied_details_observed_sends": observed_sends,
            },
        )
        if region_code == "AU":
            base["replay_inputs"]["region_code"] = region_code
        base["inventory_sha256"] = canonical_digest(base)
        return RouteRequestPackage("complete", freeze(base))
    except (MaterialError, ValueError, TypeError, KeyError, OSError, StopIteration) as exc:
        diagnostic = [
            exc.diagnostic
            if isinstance(exc, MaterialError)
            else {"reason": "request_preparation_invalid", "explanation": str(exc)}
        ]
        return RouteRequestPackage(
            "needs_material_correction",
            freeze(
                {
                    "schema_version": PACKAGE_VERSION,
                    "legs": [],
                    "requests": [],
                    "diagnostics": diagnostic,
                }
            ),
        )


def preflight_v0_route_requests(bundle_path, identity_report, package, *, ledger, next_request_key):
    """Rehearse a proposed send against frozen sources/counters; never authorize or send it."""
    value = package.to_dict() if hasattr(package, "to_dict") else thaw(package)
    result = {"status": "stopped", "live_authorized": False, "reasons": []}
    try:
        expected = prepare_v0_route_requests(
            bundle_path, identity_report, prepared_at=value["prepared_at"], **value["replay_inputs"]
        ).to_dict()
        if value != expected or value.get("status") != "complete":
            result["reasons"].append("package_replay_mismatch")
            return result
        require(
            isinstance(ledger, dict)
            and set(ledger)
            == {
                "sent_request_keys",
                "elapsed_seconds",
                "cost_usd",
                "retry_sends",
                "search_sends",
                "model_sends",
            },
            "ledger",
            "Exact preparation ledger fields required",
        )
        sent = ledger["sent_request_keys"]
        require(
            isinstance(sent, list) and all(isinstance(k, str) for k in sent),
            "ledger",
            "Request-key ledger required",
        )
        require(
            type(ledger["elapsed_seconds"]) in (int, float)
            and math.isfinite(ledger["elapsed_seconds"])
            and ledger["elapsed_seconds"] >= 0,
            "ledger",
            "Finite nonnegative elapsed time required",
        )
        cost = Decimal(ledger["cost_usd"])
        require(cost.is_finite() and cost >= 0, "ledger", "Finite nonnegative cost required")
        for field, reason in (
            ("retry_sends", "retries_forbidden"),
            ("search_sends", "searches_forbidden"),
            ("model_sends", "models_forbidden"),
        ):
            require(
                type(ledger[field]) is int and ledger[field] >= 0, "ledger", "Invalid send counter"
            )
            if ledger[field]:
                result["reasons"].append(reason)
        ready = {r["key"]: r for r in value["requests"] if r["state"] == "ready_for_approval"}
        if next_request_key not in ready:
            result["reasons"].append("request_not_ready")
        if next_request_key in sent or len(set(sent)) != len(sent):
            result["reasons"].append("request_already_sent")
        if not set(sent) <= ready.keys():
            result["reasons"].append("foreign_sent_request")
        if len(sent) >= value["limits"]["max_details_sends"] + value["limits"]["max_routes_sends"]:
            result["reasons"].append("send_limit_exhausted")
        if (
            ledger["elapsed_seconds"] + value["limits"]["single_call_timeout_seconds"]
            > value["limits"]["total_deadline_seconds"]
        ):
            result["reasons"].append("total_deadline_exhausted")
        if cost < Decimal(_money(len(sent))):
            result["reasons"].append("cost_underreported")
        reserve = (
            Decimal(ready[next_request_key]["estimate_usd"])
            if next_request_key in ready
            else Decimal(0)
        )
        if cost + reserve > Decimal(value["limits"]["max_cost_usd"]):
            result["reasons"].append("cost_limit_exceeded")
        if not result["reasons"]:
            result["status"] = "within_prepared_limits"
        return result
    except (MaterialError, ValueError, TypeError, KeyError, OSError, ArithmeticError) as exc:
        result["reasons"].append("invalid_preflight_material")
        result["diagnostic"] = str(exc)
        return result
