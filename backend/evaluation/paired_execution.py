"""Explicit paired dispatch; native transports own budgets and HTTP accounting."""

import asyncio
import json
import os
import shutil
from pathlib import Path

from .evaluation_transport import EvaluationTransport
from .identity_program import resolve_versioned_identities
from .paired_run import (
    available,
    capture_status,
    lineage,
    now,
    preflight,
    routes,
    save,
    usage_summary,
    write_receipt,
)
from .snapshot import (
    AcquisitionPolicy,
    TransportFailure,
    acquire_snapshot,
    identity_evidence,
    load_snapshot,
)


class RedactingClient:
    """Remove echoed credentials from captured bodies before native persistence."""

    def __init__(self, client, credential):
        self.client, self.credential = client, credential

    async def request(self, *args, **kwargs):
        import httpx

        response = await self.client.request(*args, **kwargs)
        raw = await response.aread()
        safe = raw.replace(self.credential.encode(), b"<redacted>")

        def redact(value):
            if isinstance(value, list):
                return [redact(v) for v in value]
            if isinstance(value, dict):
                return {
                    k: "<redacted>"
                    if k.lower().replace("_", "").replace("-", "")
                    in {
                        "apikey",
                        "authorization",
                        "accesstoken",
                        "refreshtoken",
                        "password",
                        "secret",
                        "token",
                    }
                    else redact(v)
                    for k, v in value.items()
                }
            return value

        try:
            value = json.loads(safe)
            redacted = redact(value)
            if value != redacted:
                safe = json.dumps(redacted, ensure_ascii=False).encode()
        except (ValueError, UnicodeError):
            pass
        return httpx.Response(response.status_code, content=safe)


async def execute(directory, *, approved_sha256, env_file=None, http_client=None):
    preparation = preflight(directory, approved_sha256)
    root = Path(directory).resolve()
    intake, context, options = preparation["intake"], preparation["context"], preparation["options"]
    has_pair = available(intake)
    cached = preparation["cached_snapshots"]
    needs_provider = has_pair and ("identity" not in cached or "evidence" not in cached)
    key = None
    if needs_provider:
        if env_file:
            from dotenv import load_dotenv

            load_dotenv(env_file, override=False)
        key = os.environ.get("GOOGLE_MAPS_API_KEY")
        if not key:
            raise ValueError("Independent Google credential required for uncached paired requests")
    execution = root / "execution"
    execution.mkdir(exist_ok=False)
    save(execution, "started.json", {"preparation_sha256": approved_sha256, "started_at": now()})
    client, owns_client, transport = http_client, False, None
    inventory = {"phases": {}, "pair_available": has_pair}
    from .paired_run import native_report, unresolved_identity

    identity, plan = unresolved_identity(intake), preparation["evidence_plan"]
    report = None
    deadline = asyncio.get_running_loop().time() + options["total_timeout_seconds"]
    try:
        if needs_provider:
            import httpx

            if client is None:
                client, owns_client = httpx.AsyncClient(follow_redirects=False), True
            transport = EvaluationTransport(
                preparation, execution, RedactingClient(client, key), key, None
            )
        async with asyncio.timeout_at(deadline):
            if has_pair:
                for phase in ("identity", "evidence"):
                    phase_plan = preparation["identity_plan"] if phase == "identity" else plan
                    save(execution, phase + "-plan.json", phase_plan)
                    start = len(transport.events) if transport else 0
                    inventory["phases"][phase] = {
                        "status": "started",
                        "event_ids": [],
                        "plan": phase_plan,
                    }
                    save(execution, "inventory.json", inventory)
                    target = execution / (phase + "-snapshot")
                    if phase in cached:
                        shutil.copytree(root / "material/cache" / phase, target)
                        snapshot = load_snapshot(target, expected_plan=phase_plan)
                        inventory["phases"][phase]["status"] = "reused_verified_snapshot"
                    else:
                        if transport is None:
                            raise ValueError("Uncached paired phase requires independent transport")
                        remaining = options["max_google_sends"] - start
                        if remaining <= 0 and phase_plan["requests"]:
                            raise ValueError("Google send allowance exhausted")
                        snapshot = await acquire_snapshot(
                            phase_plan,
                            target,
                            transport.google,
                            AcquisitionPolicy(
                                max(1, remaining),
                                max_attempts=1,
                                timeout_seconds=options["timeout_seconds"],
                                retry_delay_seconds=0,
                            ),
                        )
                        inventory["phases"][phase]["status"] = "acquired"
                    inventory["phases"][phase]["event_ids"] = (
                        [event["event_id"] for event in transport.events[start:]]
                        if transport
                        else []
                    )
                    save(execution, "inventory.json", inventory)
                    if phase == "identity":
                        evidence = identity_evidence(snapshot)
                        save(execution, "identity-evidence.json", evidence)
                        identity = resolve_versioned_identities(intake, evidence).to_dict()
                        save(execution, "identity-report.json", identity)
                        route_preparation = routes(intake, identity, context, target)
                        save(execution, "route-preparation.json", route_preparation)
                        plan = route_preparation["evidence_plan"]
            else:
                save(execution, "identity-report.json", identity)
                save(execution, "inventory.json", inventory)
            edit = lineage(intake, identity, root / preparation["native_manifest"], context)
            save(execution, "edit-provenance.json", edit)
            pair = native_report(preparation, execution, identity, plan, now())
            save(execution, "pair-report.json", pair)
            usage = transport.usage() if transport else empty_usage(preparation, execution)
            report = {
                "schema_version": "rtpeval_pair_acquisition_report_1",
                "preparation_sha256": approved_sha256,
                "processing_status": "complete",
                "acquisition_status": "complete" if has_pair else "not_applicable",
                "evidence_status": capture_status(preparation, execution),
                "pair": pair,
                "usage": usage_summary(usage, preparation["prices"]),
                "generated_at": pair["generated_at"],
            }
            from .paired_run import verify

            verify(root)
            if asyncio.get_running_loop().time() >= deadline:
                raise TimeoutError("Paired reporting exceeded total deadline")
    except (
        ValueError,
        TypeError,
        KeyError,
        OSError,
        RuntimeError,
        TimeoutError,
        TransportFailure,
        asyncio.CancelledError,
        KeyboardInterrupt,
    ) as exc:
        usage = transport.usage() if transport else empty_usage(preparation, execution)
        report = {
            "schema_version": "rtpeval_pair_acquisition_report_1",
            "preparation_sha256": approved_sha256,
            "processing_status": "stopped",
            "acquisition_status": "partial",
            "evidence_status": "not_completed",
            "pair": None,
            "error_type": type(exc).__name__,
            "reason": "execution_cancelled"
            if isinstance(exc, asyncio.CancelledError)
            else "execution_interrupted"
            if isinstance(exc, KeyboardInterrupt)
            else "execution_timeout"
            if isinstance(exc, TimeoutError)
            else str(exc)
            if type(exc) is ValueError
            else exc.code
            if isinstance(exc, TransportFailure)
            else "execution_failed",
            "usage": usage_summary(usage, preparation["prices"]),
            "generated_at": now(),
        }
        for phase, record in inventory["phases"].items():
            if record["status"] == "started" and transport:
                known = {
                    i
                    for p in inventory["phases"].values()
                    if p["status"] != "started"
                    for i in p["event_ids"]
                }
                record["event_ids"] = [
                    e["event_id"] for e in transport.events if e["event_id"] not in known
                ]
                record["status"] = "stopped"
                # An interrupt may occur after HTTP persistence, before snapshot consumption.
                for event in transport.events:
                    if (
                        event["event_id"] in record["event_ids"]
                        and event.get("status_code") is not None
                    ):
                        partial = (
                            execution
                            / (phase + "-snapshot")
                            / "raw"
                            / (event["request_key"] + "-1.bin")
                        )
                        if not partial.exists():
                            partial.parent.mkdir(parents=True, exist_ok=True)
                            partial.write_bytes(
                                (execution / "http" / (event["event_id"] + ".bin")).read_bytes()
                            )
        save(execution, "inventory.json", inventory)
    finally:
        if owns_client and client is not None:
            try:
                async with asyncio.timeout_at(deadline):
                    await client.aclose()
            except (OSError, RuntimeError, asyncio.CancelledError, KeyboardInterrupt) as exc:
                if report is not None and report["processing_status"] == "complete":
                    report.update(
                        processing_status="stopped",
                        acquisition_status="partial",
                        evidence_status="not_completed",
                        pair=None,
                        error_type=type(exc).__name__,
                        reason="client_cleanup_failed",
                    )
                if report is not None:
                    report["cleanup_error_type"] = type(exc).__name__
    if report is None:
        raise ValueError("Paired execution ended without a report")
    save(execution, "usage.json", usage)
    save(execution, "report.json", report)
    write_receipt(execution, approved_sha256)
    return report


def empty_usage(preparation, execution):
    return {
        "schema_version": "rtpeval_usage_1",
        "namespace": "oracle",
        "group_id": preparation["intake"]["batch_id"],
        "run_id": str(execution),
        "version": "shared",
        "result_sha256": preparation["content_sha256"],
        "collection_status": "available",
        "coverage": {"adapter_coverage": "default_adapters"},
        "model_calls": [],
        "provider_events": [],
        "cache_events": [],
        "repair_summary": {"model_event_ids": [], "provider_event_ids": []},
        "timing": {"started_at": now(), "finished_at": now()},
        "missing_fields": ["actual_account_billing"],
    }
