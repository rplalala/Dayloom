"""Source-bound preparation, execution and network-free final evaluation replay."""

import asyncio
import hashlib
import math
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import httpx

from .cost_report import build_cost_report, validate_prices
from .intake import _read, load_batch
from .records import canonical_digest
from .snapshot import TransportFailure, _bytes, build_identity_plan

VERSION = "rtpeval_execution_preparation_3"
PREVIOUS_VERSION = "rtpeval_execution_preparation_2"
LEGACY_VERSION = "rtpeval_execution_preparation_1"


def _save(root, name, value):
    (root / name).write_bytes(_bytes(value))


def _now():
    return datetime.now(UTC).isoformat()


def _options(options, *, allow_no_google=False):
    value = dict(options)
    required = {
        "max_google_sends",
        "max_cost_usd",
        "timeout_seconds",
        "total_timeout_seconds",
        "model",
        "model_endpoint",
        "max_input_tokens",
        "max_output_tokens",
    }
    optional = set() if allow_no_google else {"reasoning_effort", "assess_missing_hours"}
    if not required <= set(value) or set(value) - required - optional:
        raise ValueError(
            "Explicit execution options required; credentials are not preparation data"
        )
    if "reasoning_effort" in value and value["reasoning_effort"] not in ("low", "medium"):
        raise ValueError("Identity reasoning effort must be low or medium")
    if "assess_missing_hours" in value and type(value["assess_missing_hours"]) is not bool:
        raise ValueError("assess_missing_hours must be a boolean")
    if not allow_no_google:
        value.setdefault("assess_missing_hours", True)
    for key in ("max_google_sends", "max_input_tokens", "max_output_tokens"):
        minimum = 0 if key == "max_google_sends" and allow_no_google else 1
        if type(value[key]) is not int or value[key] < minimum:
            raise ValueError("Positive integer execution limit required: " + key)
    for key in ("timeout_seconds", "total_timeout_seconds"):
        if type(value[key]) not in (int, float) or not math.isfinite(value[key]) or value[key] <= 0:
            raise ValueError("Positive finite timing limit required: " + key)
    budget = Decimal(value["max_cost_usd"])
    if not budget.is_finite() or budget <= 0:
        raise ValueError("Positive USD reference allowance required")
    endpoint = httpx.URL(value["model_endpoint"])
    if (
        endpoint.scheme != "https"
        or endpoint.username
        or endpoint.password
        or endpoint.query
        or endpoint.fragment
    ):
        raise ValueError("HTTPS model endpoint without embedded credentials required")
    if not isinstance(value["model"], str) or not value["model"].strip():
        raise ValueError("Explicit model/deployment required")
    value["model_endpoint"] = str(endpoint).rstrip("/") + "/"
    return value


def _verify(preparation, *, implementation=False):
    if preparation.get("schema_version") not in (
        VERSION,
        PREVIOUS_VERSION,
        LEGACY_VERSION,
    ) or canonical_digest(
        {k: v for k, v in preparation.items() if k != "content_sha256"}
    ) != preparation.get("content_sha256"):
        raise ValueError("Evaluation preparation digest mismatch")
    if load_batch(preparation["manifest"]).to_dict() != preparation["intake"]:
        raise ValueError("Original evaluation sources changed")
    if "semantic_readiness" in preparation:
        from .review_artifacts import review_inputs
        from .semantic_readiness import review_readiness

        occupancy = review_inputs(
            preparation["manifest"],
            _read(Path(preparation["manifest"]))[0],
            preparation["intake"],
            preparation["context"]["occupancy_reviews"],
        )
        readiness = review_readiness(preparation["intake"], occupancy)
        if readiness != preparation["semantic_readiness"] or readiness["status"] != "ready":
            raise ValueError("Prepared semantic review coverage changed")
    if "population_readiness" in preparation:
        from .declared_population import PROFILE_ID, population_readiness

        current = population_readiness(
            preparation["intake"],
            preparation["context"]["schedule_context"],
            preparation["context"]["occupancy_reviews"],
            preparation["context"]["density_reviews"],
        )
        if (
            preparation.get("quality_profile") != PROFILE_ID
            or current != preparation["population_readiness"]
            or current["status"] != "ready"
        ):
            raise ValueError("Prepared numerical population changed")
    root = Path(preparation["directory"])
    if _read(root / "preparation.json")[0] != preparation:
        raise ValueError("Saved execution preparation changed")
    if implementation and any(
        hashlib.sha256(Path(path).read_bytes()).hexdigest() != sha
        for path, sha in preparation["implementation_hashes"].items()
    ):
        raise ValueError("Evaluation implementation changed since preparation")
    return root


def _unknowns(identity, quality):
    units = []
    for row in identity["records"]:
        if row["projection"] in (None, "final") and row["grounding_verdict"] == "UNKNOWN":
            units.append(
                {
                    "stage": "identity",
                    "version": row["version"],
                    "group_id": row["group_id"],
                    "source": row["source"],
                    "reference_id": row["reference_id"],
                    "reasons": [row["reason"]],
                }
            )
    for stage, report in quality.get("components", {}).items():
        for row in report.get("results", []):
            for dimension in ("requirements", "non_overlap", "opening", "routes"):
                value = row.get(dimension, {})
                for check in value.get("checks", []):
                    if check.get("state") == "UNKNOWN":
                        reasons = check.get("reasons") or (
                            [check["reason"]] if check.get("reason") else []
                        )
                        if not reasons:
                            reasons = (
                                [
                                    c.get("reason", c.get("kind", "unresolved_evidence"))
                                    for c in check.get("components", [])
                                    if isinstance(c, dict) and c.get("state") == "UNKNOWN"
                                ]
                                if isinstance(check.get("components"), list)
                                else [
                                    c.get("reason") or "unresolved_evidence"
                                    for c in check.get("components", {}).values()
                                    if c.get("state") == "UNKNOWN"
                                ]
                            )
                        units.append(
                            {
                                "stage": stage,
                                "dimension": dimension,
                                "version": row["version"],
                                "group_id": row["group_id"],
                                "source": check.get("source")
                                or check.get("sources")
                                or row.get("source_hashes"),
                                "reference_id": check.get(
                                    "reference_id",
                                    check.get(
                                        "leg_id",
                                        check.get("obligation_id", check.get("commitment_id")),
                                    ),
                                ),
                                "reasons": reasons,
                                "check": check,
                            }
                        )
                if value.get("denominator_unresolved"):
                    units.append(
                        {
                            "stage": stage,
                            "dimension": dimension,
                            "version": row["version"],
                            "source": row.get("source_hashes"),
                            "reasons": value.get("reasons", ["denominator_unresolved"]),
                        }
                    )
    return units


def _acquisition_links(unknowns, snapshots, identity):
    """Explain source-owned upstream requests without changing native verdicts."""
    refs = {r["reference_id"]: r for r in identity["records"]}
    evidence = {key: [] for key in refs}
    legs = {}
    queries = {}
    for snapshot in snapshots:
        records = {r["key"]: r for r in snapshot["records"]}
        queries.update(
            {(snapshot["plan"]["phase"], key): record for key, record in records.items()}
        )
        for item in snapshot["plan"]["references"]:
            for operation, key in item["requests"].items():
                record = records[key]
                owners = [
                    key
                    for key, ref in refs.items()
                    if ref.get("evidence_reference_id", key) == item["reference_id"]
                ]
                for owner in owners:
                    evidence[owner].append(
                        {
                            "phase": snapshot["plan"]["phase"],
                            "operation": operation,
                            "request_key": key,
                            "status": record["summary"]["status"],
                            "reason": record["summary"].get("reason"),
                            "attempts": record["attempts"],
                        }
                    )
        for leg in snapshot["plan"].get("legs", []):
            legs[leg["leg_id"]] = leg
    for unit in unknowns:
        if unit["stage"] == "daily_density":
            continue
        key = unit.get("reference_id")
        selected = [key] if key in refs else []
        if key in legs:
            leg = legs[key]
            selected = [leg["origin_reference"], leg["destination_reference"]]
        if not selected:
            selected = [
                key
                for key, r in refs.items()
                if r["group_id"] == unit.get("group_id") and r["version"] in (unit["version"], None)
            ]
        unit["acquisition"] = [
            {"reference_id": key, "source": refs[key]["source"], **item}
            for key in selected
            for item in evidence[key]
        ]
        if key in legs and legs[key]["request_key"] is None:
            unit["acquisition"].append(
                {
                    "phase": "evidence",
                    "operation": "route_matrix",
                    "request_key": None,
                    "status": "not_executed",
                    "reason": legs[key]["reason"],
                }
            )
        elif key in legs:
            request_key = legs[key]["request_key"]
            record = queries[("evidence", request_key)]
            unit["acquisition"].append(
                {
                    "phase": "evidence",
                    "operation": "route_matrix",
                    "request_key": request_key,
                    "status": record["summary"]["status"],
                    "reason": record["summary"].get("reason"),
                    "attempts": record["attempts"],
                }
            )


def _report(
    preparation,
    execution,
    identity,
    evidence_plan,
    usage,
    generated_at,
    *,
    opening_judgment=None,
    opening_assessment=None,
):
    from .cost_report import build_cost_report
    from .opening import score_opening
    from .quality_report import build_quality_report
    from .requirement_schedule import score_requirement_schedule
    from .routes import score_routes
    from .snapshot import load_snapshot

    context = preparation["context"]
    quality = build_quality_report(
        preparation["intake"],
        identity,
        execution / "evidence-snapshot",
        **context,
        expected_plan=evidence_plan,
        identity_snapshot_directory=execution / "identity-snapshot",
        generated_at=generated_at,
        opening_judgment=opening_judgment,
        quality_profile=preparation.get("quality_profile"),
    ).to_dict()
    snapshots = [
        load_snapshot(execution / name) for name in ("identity-snapshot", "evidence-snapshot")
    ]
    failures = [
        {"phase": snapshot["plan"]["phase"], "request_key": r["key"], "summary": r["summary"]}
        for snapshot in snapshots
        for r in snapshot["records"]
        if r["summary"]["status"] != "available"
    ]
    reports = {
        "identity": identity,
        "requirement_schedule": score_requirement_schedule(
            preparation["intake"],
            identity,
            context["schedule_context"],
            context["occupancy_reviews"],
        ).to_dict(),
        "opening": score_opening(
            preparation["intake"],
            identity,
            execution / "evidence-snapshot",
            context["schedule_context"],
            expected_plan=evidence_plan,
            opening_judgment=opening_judgment,
        ).to_dict(),
        "routes": score_routes(
            preparation["intake"],
            identity,
            execution / "evidence-snapshot",
            context["schedule_context"],
            context["occupancy_reviews"],
            context["route_reviews"],
            expected_plan=evidence_plan,
            identity_snapshot_directory=execution / "identity-snapshot",
        ).to_dict(),
    }
    unknowns = _unknowns(identity, {"components": reports})
    for group in quality["groups"]:
        for version, result in group["versions"].items():
            for day in result["daily_density"]["days"]:
                if day["state"] == "UNKNOWN":
                    unknowns.append(
                        {
                            "stage": "daily_density",
                            "group_id": group["group_id"],
                            "version": version,
                            "source": result["component_source_hashes"]["requirement_schedule"],
                            "date": day["date"],
                            "reasons": [day["reason"]],
                            "check": day,
                        }
                    )
    _acquisition_links(unknowns, snapshots, identity)
    cost = build_cost_report(
        [{"sha256": canonical_digest(usage), "usage": usage}], preparation["prices"]
    )
    return {
        **({"opening_assessment": opening_assessment} if opening_assessment is not None else {}),
        "schema_version": "rtpeval_execution_report_1",
        "preparation_sha256": preparation["content_sha256"],
        "scope": preparation["scope"],
        "generated_at": generated_at,
        "processing_status": quality["status"],
        "acquisition_status": "partial" if failures else "complete",
        "evidence_status": "unresolved" if unknowns else "decidable",
        "quality": quality,
        "unknowns": unknowns,
        "acquisition_failures": failures,
        "reports": reports,
        "not_evaluated": [
            {"version": "v3", "projection": label, "reason": "outside_four_final_scope"}
            for group in preparation["intake"]["inventory"]
            for label, projection in group["runs"]["v3"]["optional"].items()
            if projection is not None
        ]
        + [
            {"track": track, "reason": "outside_four_final_scope"}
            for track in ("human", "controlled_repair")
        ],
        "usage": {
            "actual_google_sends": sum(e["provider"] == "google" for e in usage["provider_events"]),
            "actual_model_sends": len(usage["model_calls"]),
            "retries": 0,
            "raw": usage,
            "cost": cost,
            "actual_billing": None,
        },
    }


async def execute_run(
    preparation, *, approved_sha256, google_api_key, model_api_key, http_client=None
):
    """Execute one explicitly approved fresh package; preserve failed attempts without retry."""
    from .evaluation_transport import EvaluationTransport, check_tokenizer
    from .identity_binding import RESULT_VERSION as BOUND_RESULT_VERSION
    from .identity_llm import prepare_identity_judgment
    from .identity_program import resolve_versioned_identities
    from .primary_opening import assess_primary_opening
    from .routes import prepare_routes
    from .snapshot import AcquisitionPolicy, acquire_snapshot, identity_evidence

    root = _verify(preparation, implementation=True)
    if approved_sha256 != preparation["content_sha256"]:
        raise ValueError("Exact evaluation preparation approval required")
    if not google_api_key or not model_api_key:
        raise ValueError("Independent Google and V0 model credentials required")
    check_tokenizer()
    execution = root / "execution"
    execution.mkdir(exist_ok=False)
    _save(execution, "started.json", {"preparation_sha256": approved_sha256, "started_at": _now()})
    owns_client = http_client is None
    client = http_client or httpx.AsyncClient(follow_redirects=False)
    transport = EvaluationTransport(preparation, execution, client, google_api_key, model_api_key)
    options, intake, context = preparation["options"], preparation["intake"], preparation["context"]
    try:
        async with asyncio.timeout(options["total_timeout_seconds"]):
            snapshot = await acquire_snapshot(
                preparation["identity_plan"],
                execution / "identity-snapshot",
                transport.google,
                AcquisitionPolicy(
                    options["max_google_sends"],
                    max_attempts=1,
                    timeout_seconds=options["timeout_seconds"],
                    retry_delay_seconds=0,
                ),
            )
            evidence = identity_evidence(snapshot)
            _save(execution, "identity-evidence.json", evidence)
            common_subjects = preparation["schema_version"] == VERSION
            subject_material = None
            if common_subjects:
                from .primary_subjects import assess_subjects

                subject_material = await assess_subjects(
                    preparation, execution, evidence, transport
                )
            packet = prepare_identity_judgment(
                intake, evidence, model=options["model"], visits_only=common_subjects
            )
            material = None
            if packet is not None:
                packet = packet.to_dict()
                _save(execution, "model-packet.json", packet)
                response, event = await transport.model(
                    packet, reasoning_effort=options.get("reasoning_effort", "low")
                )
                material = {
                    "schema_version": BOUND_RESULT_VERSION,
                    "packet": packet,
                    "binding_source": {"intake": intake, "evidence": evidence},
                    "requested_at": event["requested_at"],
                    "retrieved_at": event["retrieved_at"],
                    "response": response,
                    "response_sha256": canonical_digest(response),
                }
                _save(execution, "model-result.json", material)
            identity = resolve_versioned_identities(
                intake,
                evidence,
                model_result=material,
                common_subjects=common_subjects,
                subject_result=subject_material,
            ).to_dict()
            _save(execution, "identity-report.json", identity)
            routes = prepare_routes(
                intake,
                identity,
                **{
                    k: context[k]
                    for k in ("schedule_context", "occupancy_reviews", "route_reviews")
                },
                identity_snapshot_directory=execution / "identity-snapshot",
            ).to_dict()
            _save(execution, "route-preparation.json", routes)
            if routes["status"] != "complete":
                raise ValueError("Native route preparation requires correction")
            plan = routes["evidence_plan"]
            _save(execution, "evidence-plan.json", plan)
            remaining = options["max_google_sends"] - sum(
                e["provider"] == "google" for e in transport.events
            )
            if remaining < len(plan["requests"]):
                raise ValueError("Insufficient remaining Google allowance for evidence phase")
            await acquire_snapshot(
                plan,
                execution / "evidence-snapshot",
                transport.google,
                AcquisitionPolicy(
                    max(1, remaining),
                    max_attempts=1,
                    timeout_seconds=options["timeout_seconds"],
                    retry_delay_seconds=0,
                ),
            )
            opening_stage, opening_material = None, None
            if preparation["schema_version"] in (VERSION, PREVIOUS_VERSION):
                opening_stage, opening_material = await assess_primary_opening(
                    preparation, execution, identity, plan, transport
                )
                _save(execution, "opening-assessment.json", opening_stage)
            usage = transport.usage()
            _save(execution, "usage.json", usage)
            report = _report(
                preparation,
                execution,
                identity,
                plan,
                usage,
                _now(),
                opening_judgment=opening_material,
                opening_assessment=opening_stage,
            )
            _verify(preparation, implementation=True)
    except (
        ValueError,
        KeyError,
        TypeError,
        OSError,
        TimeoutError,
        RuntimeError,
        TransportFailure,
        asyncio.CancelledError,
        KeyboardInterrupt,
    ) as exc:
        usage = transport.usage()
        _save(execution, "usage.json", usage)
        report = {
            "schema_version": "rtpeval_execution_report_1",
            "preparation_sha256": approved_sha256,
            "processing_status": "stopped",
            "acquisition_status": "partial",
            "evidence_status": "not_completed",
            "error_type": type(exc).__name__,
            "reason": "execution_cancelled"
            if isinstance(exc, asyncio.CancelledError)
            else "execution_interrupted"
            if isinstance(exc, KeyboardInterrupt)
            else exc.code
            if isinstance(exc, TransportFailure)
            else str(exc)
            if type(exc) is ValueError
            else "execution_failed",
            "usage": {
                "actual_google_sends": sum(e["provider"] == "google" for e in transport.events),
                "actual_model_sends": len(transport.model_calls),
                "retries": 0,
                "actual_billing": None,
                "cost": build_cost_report(
                    [{"sha256": canonical_digest(usage), "usage": usage}], preparation["prices"]
                ),
                "raw": usage,
            },
        }
    finally:
        if owns_client:
            await client.aclose()
    _save(execution, "report.json", report)
    hashes = {
        str(p.relative_to(execution)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in execution.rglob("*")
        if p.is_file()
    }
    _save(execution, "receipt.json", {"preparation_sha256": approved_sha256, "files": hashes})
    return report


def verify_receipt(execution, preparation_sha256):
    """Verify the closed inventory of an execution without replaying historical rules."""
    execution = Path(execution)
    receipt = _read(execution / "receipt.json")[0]
    if receipt["preparation_sha256"] != preparation_sha256:
        raise ValueError("Execution receipt belongs to another preparation")
    for name, sha in receipt["files"].items():
        path = (execution / name).resolve()
        if (
            not path.is_relative_to(execution.resolve())
            or hashlib.sha256(path.read_bytes()).hexdigest() != sha
        ):
            raise ValueError("Execution artifact integrity mismatch")
    files = {
        str(p.relative_to(execution))
        for p in execution.rglob("*")
        if p.is_file() and p.name != "receipt.json"
    }
    if files != set(receipt["files"]):
        raise ValueError("Execution receipt file inventory mismatch")
    return _read(execution / "receipt.json")[1]


def replay_run(directory):
    """Verify originals and all captured bytes, then independently recompose the final report."""
    from .evaluation_transport import usage_event, verify_model_capture
    from .identity_program import resolve_versioned_identities
    from .routes import prepare_routes
    from .snapshot import identity_evidence, load_snapshot

    preparation = _read(Path(directory) / "preparation.json")[0]
    root = _verify(preparation)
    execution = root / "execution"
    verify_receipt(execution, preparation["content_sha256"])
    saved = _read(execution / "report.json")[0]
    usage = _read(execution / "usage.json")[0]
    journal = [
        _read(p)[0] for p in sorted((execution / "http").glob("*.json"), key=lambda p: int(p.stem))
    ]
    if [usage_event(e) for e in journal] != usage["provider_events"]:
        raise ValueError("HTTP journal and usage differ")
    if saved["processing_status"] == "stopped":
        if saved["usage"]["raw"] != usage:
            raise ValueError("Stopped report usage differs")
        return saved
    evidence = identity_evidence(
        load_snapshot(execution / "identity-snapshot", expected_plan=preparation["identity_plan"])
    )
    from .identity import identity_references

    common_subjects = preparation["schema_version"] == VERSION
    needs_v0 = not common_subjects or any(
        r["version"] == "v0" and r["kind"] == "primary_visit"
        for r in identity_references(preparation["intake"])
    )
    material = _read(execution / "model-result.json")[0] if needs_v0 else None
    model_events = [e for e in journal if e.get("model_event_id") == "v0-identity"]
    if len(model_events) != int(needs_v0):
        raise ValueError("Model HTTP receipt missing or duplicated")
    identity_calls = [call for call in usage["model_calls"] if call["operation"] == "identity"]
    if len(identity_calls) != int(needs_v0):
        raise ValueError("Exactly one identity model attempt required")
    if needs_v0:
        verify_model_capture(
            execution,
            model_events[0],
            material,
            preparation["options"],
            identity_calls[0],
            reasoning_effort=preparation["options"].get("reasoning_effort", "low"),
        )
    elif any((execution / name).exists() for name in ("model-packet.json", "model-result.json")):
        raise ValueError("Unselected V0 stage has unexpected material")
    subject_material = None
    if common_subjects:
        from .primary_subjects import replay_subjects

        subject_material = replay_subjects(preparation, execution, evidence, journal, usage)
    identity = resolve_versioned_identities(
        preparation["intake"],
        evidence,
        model_result=material,
        common_subjects=common_subjects,
        subject_result=subject_material,
    ).to_dict()
    if identity != _read(execution / "identity-report.json")[0]:
        raise ValueError("Identity report replay differs")
    context = preparation["context"]
    routes = prepare_routes(
        preparation["intake"],
        identity,
        **{k: context[k] for k in ("schedule_context", "occupancy_reviews", "route_reviews")},
        identity_snapshot_directory=execution / "identity-snapshot",
    ).to_dict()
    if (
        routes != _read(execution / "route-preparation.json")[0]
        or routes["evidence_plan"] != _read(execution / "evidence-plan.json")[0]
    ):
        raise ValueError("Route preparation replay differs")
    opening_stage, opening_material = None, None
    if preparation["schema_version"] in (VERSION, PREVIOUS_VERSION):
        from .primary_opening import replay_primary_opening

        opening_stage, opening_material = replay_primary_opening(
            preparation, execution, identity, routes["evidence_plan"], journal, usage
        )
        if opening_stage != _read(execution / "opening-assessment.json")[0]:
            raise ValueError("Opening assessment stage replay differs")
    expected_models = (
        int(needs_v0) + int(opening_material is not None) + int(subject_material is not None)
    )
    if (
        len(usage["model_calls"]) != expected_models
        or sum(e["provider"] == "azure_foundry" for e in journal) != expected_models
    ):
        raise ValueError("Model HTTP inventory differs from selected stages")
    report = _report(
        preparation,
        execution,
        identity,
        routes["evidence_plan"],
        usage,
        saved["generated_at"],
        opening_judgment=opening_material,
        opening_assessment=opening_stage,
    )
    if report != saved:
        raise ValueError("Final evaluation report replay differs")
    return report


def prepare_run(
    manifest,
    directory,
    *,
    options,
    prices,
    schedule_context=None,
    occupancy_reviews=None,
    route_reviews=None,
    density_reviews=None,
    quality_profile=None,
):
    """Validate original material and freeze an offline, unconsumed execution package."""
    source = Path(manifest).resolve()
    from .evaluation_transport import check_tokenizer

    check_tokenizer()
    intake = load_batch(source).to_dict()
    if intake["status"] != "accepted":
        raise ValueError("Accepted four-version batch required")
    from .review_artifacts import review_inputs

    occupancy_reviews = review_inputs(source, _read(source)[0], intake, occupancy_reviews)
    options = _options(options)
    validate_prices(prices)
    if prices["currency"] != "USD":
        raise ValueError("Execution reference allowance is denominated in USD")
    from .identity import identity_references
    from .subject_correspondence import POLICY_VERSION as SUBJECT_POLICY_VERSION

    references = identity_references(intake)
    has_subjects = any(r["kind"] == "requirement_subject" for r in references)
    has_v0 = any(r["version"] == "v0" and r["kind"] == "primary_visit" for r in references)
    if has_subjects:
        from .cost_report import estimate

        event = {
            "provider": "azure_foundry",
            "operation": "requirement_subject",
            "outcome": "completed",
            "model": options["model"],
            "input_tokens": options["max_input_tokens"],
            "output_tokens": options["max_output_tokens"],
            "cached_input_tokens": 0,
            "cache_write_input_tokens": options["max_input_tokens"],
        }
        estimate_usd, _, reason = estimate(
            event, "model", {"timing": {"started_at": _now()}}, prices
        )
        if estimate_usd is None:
            raise ValueError("Subject stage price unavailable: " + reason)
        if estimate_usd > Decimal(options["max_cost_usd"]):
            raise ValueError("Subject stage reservation exceeds execution reference allowance")
    from ._route_inputs import route_reviews as read_route_reviews
    from ._schedule_preparation import _occupancy_reviews, _validate_spec
    from .daily_density import prepare_density_policies
    from .preparation import schedule_timezones

    schedule_timezones(intake, schedule_context)
    _occupancy_reviews(intake, occupancy_reviews)
    from .semantic_readiness import MissingSemanticReviews, review_readiness

    readiness = review_readiness(intake, occupancy_reviews)
    if readiness["status"] != "ready":
        raise MissingSemanticReviews(readiness)
    read_route_reviews(intake, route_reviews)
    prepare_density_policies(intake, density_reviews)
    for group in intake["inventory"]:
        _validate_spec(group)
    from .declared_population import (
        PROFILE_ID,
        UnreadyPopulation,
        population_readiness,
        select_profile,
    )

    selected_profile = select_profile(intake, quality_profile)
    population = None
    if selected_profile == PROFILE_ID:
        population = population_readiness(
            intake, schedule_context, occupancy_reviews, density_reviews
        )
        if population["status"] != "ready":
            raise UnreadyPopulation(population)
    implementation = [
        *Path(__file__).parent.glob("*.py"),
        Path(__file__).parents[1] / "model_references.py",
        Path(__file__).parents[1] / "pace_policy.py",
        Path(__file__).parents[1] / "activity_semantics.py",
        Path(__file__).parents[1] / "app" / "runtime" / "token_counting.py",
    ]
    value = {
        "schema_version": VERSION,
        "status": "prepared",
        "prepared_at": _now(),
        "manifest": str(source),
        "directory": str(Path(directory).resolve()),
        "intake": intake,
        "semantic_readiness": readiness,
        **(
            {"quality_profile": selected_profile, "population_readiness": population}
            if population is not None
            else {}
        ),
        "options": options,
        "prices": prices,
        "identity_plan": build_identity_plan(intake),
        "context": {
            "schedule_context": schedule_context,
            "occupancy_reviews": occupancy_reviews,
            "route_reviews": route_reviews,
            "density_reviews": density_reviews,
        },
        "implementation_hashes": {
            str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest() for p in implementation
        },
        "scope": "four_final_automatic_quality",
        "subject_policy": SUBJECT_POLICY_VERSION,
        "max_model_sends": int(has_v0)
        + int(options.get("assess_missing_hours", True))
        + int(has_subjects),
        "max_retries": 0,
    }
    value["content_sha256"] = canonical_digest(value)
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=False)
    _save(root, "preparation.json", value)
    return value
