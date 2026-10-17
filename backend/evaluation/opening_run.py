"""One incremental missing-hours model attempt over an immutable completed evaluator run."""

import asyncio
import hashlib
from pathlib import Path

import httpx

from .cost_report import build_cost_report, validate_prices
from .evaluation_run import VERSION as PRIMARY_VERSION
from .evaluation_run import _now, _options, _report, _save, _verify, verify_receipt
from .evaluation_transport import EvaluationTransport, check_tokenizer, model_usage, usage_event
from .identity_program import resolve_versioned_identities
from .intake import _read
from .opening_judgment import MATERIAL_VERSION, prepare_packet, validate_material
from .records import canonical_digest, require
from .snapshot import TransportFailure, _decode, identity_evidence, load_snapshot

VERSION = "rtpeval_opening_execution_preparation_1"


def _parent(directory):
    preparation = _read(Path(directory) / "preparation.json")[0]
    root = _verify(preparation)
    execution = root / "execution"
    receipt_hash = verify_receipt(execution, preparation["content_sha256"])
    saved = _read(execution / "report.json")[0]
    require(
        saved["processing_status"] == "complete",
        "parent",
        "Completed automatic evaluation required",
    )
    evidence = identity_evidence(
        load_snapshot(execution / "identity-snapshot", expected_plan=preparation["identity_plan"])
    )
    common_subjects = preparation["schema_version"] == PRIMARY_VERSION
    subject_material = None
    if common_subjects:
        from .primary_subjects import replay_subjects

        journal = [_read(p)[0] for p in (execution / "http").glob("*.json")]
        subject_material = replay_subjects(
            preparation, execution, evidence, journal, _read(execution / "usage.json")[0]
        )
    model_material = (
        _read(execution / "model-result.json")[0]
        if (execution / "model-result.json").exists()
        else None
    )
    identity = resolve_versioned_identities(
        preparation["intake"],
        evidence,
        model_result=model_material,
        common_subjects=common_subjects,
        subject_result=subject_material,
    ).to_dict()
    require(
        identity == _read(execution / "identity-report.json")[0],
        "parent.identity",
        "Independent identity replay differs",
    )
    plan = _read(execution / "evidence-plan.json")[0]
    return preparation, execution, identity, plan, receipt_hash


def prepare_opening_run(parent_directory, directory, *, options, prices):
    check_tokenizer()
    parent, execution, identity, plan, receipt_hash = _parent(parent_directory)
    options = _options(options, allow_no_google=True)
    require(
        options["max_google_sends"] == 0, "options", "Opening fallback sends no Google requests"
    )
    validate_prices(prices)
    require(prices["currency"] == "USD", "prices", "USD reference budget required")
    packet = prepare_packet(
        parent["intake"],
        identity,
        execution / "evidence-snapshot",
        parent["context"]["schedule_context"],
        model=options["model"],
        expected_plan=plan,
    )
    paths = [
        *Path(__file__).parent.glob("*.py"),
        Path(__file__).parents[1] / "model_references.py",
        Path(__file__).parents[1] / "pace_policy.py",
        Path(__file__).parents[1] / "app" / "runtime" / "token_counting.py",
    ]
    preparation = {
        "schema_version": VERSION,
        "status": "prepared",
        "prepared_at": _now(),
        "directory": str(Path(directory).resolve()),
        "parent_directory": str(Path(parent_directory).resolve()),
        "parent_preparation_sha256": parent["content_sha256"],
        "parent_receipt_sha256": receipt_hash,
        "intake": parent["intake"],
        "packet": packet,
        "options": options,
        "prices": prices,
        "max_model_sends": 1,
        "max_retries": 0,
        "scope": "incremental_missing_hours_access_assessment",
        "implementation_hashes": {
            str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths
        },
    }
    preparation["content_sha256"] = canonical_digest(preparation)
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=False)
    _save(root, "preparation.json", preparation)
    _save(root, "packet.json", packet)
    return preparation


def _verify_opening(preparation, *, implementation=False):
    from .paired_opening import VERSION as PAIR_VERSION
    from .paired_opening import verify_pair_opening

    if preparation.get("schema_version") == PAIR_VERSION:
        return verify_pair_opening(preparation, implementation=implementation)
    require(
        preparation.get("schema_version") == VERSION
        and canonical_digest({k: v for k, v in preparation.items() if k != "content_sha256"})
        == preparation.get("content_sha256"),
        "preparation",
        "Opening preparation digest mismatch",
    )
    root = Path(preparation["directory"])
    require(
        _read(root / "preparation.json")[0] == preparation
        and _read(root / "packet.json")[0] == preparation["packet"],
        "preparation",
        "Saved preparation differs",
    )
    if implementation:
        require(
            all(
                hashlib.sha256(Path(p).read_bytes()).hexdigest() == sha
                for p, sha in preparation["implementation_hashes"].items()
            ),
            "implementation",
            "Implementation changed after preparation",
        )
    parent, execution, identity, plan, receipt = _parent(preparation["parent_directory"])
    require(
        parent["content_sha256"] == preparation["parent_preparation_sha256"]
        and receipt == preparation["parent_receipt_sha256"]
        and parent["intake"] == preparation["intake"],
        "parent",
        "Parent execution/source binding changed",
    )
    packet = prepare_packet(
        parent["intake"],
        identity,
        execution / "evidence-snapshot",
        parent["context"]["schedule_context"],
        model=preparation["options"]["model"],
        expected_plan=plan,
    )
    require(packet == preparation["packet"], "packet", "Opening eligibility/evidence changed")
    return root, parent, execution, identity, plan


def _compose(preparation, parent, execution, identity, plan, material, usage, generated_at):
    from .paired_opening import VERSION as PAIR_VERSION
    from .paired_opening import compose_pair_opening

    if preparation.get("schema_version") == PAIR_VERSION:
        return compose_pair_opening(
            preparation, execution, identity, plan, material, usage, generated_at
        )
    report = _report(
        {**parent, "prices": preparation["prices"]},
        execution,
        identity,
        plan,
        usage,
        generated_at,
        opening_judgment=material,
    )
    require(report["processing_status"] == "complete", "report", "Opening report did not complete")
    report["preparation_sha256"] = preparation["content_sha256"]
    report["scope"] = preparation["scope"]
    report["parent_execution"] = {
        "preparation_sha256": preparation["parent_preparation_sha256"],
        "receipt_sha256": preparation["parent_receipt_sha256"],
        "usage": (
            "Original Google/identity costs remain in the parent report; "
            "this report records incremental opening usage only."
        ),
    }
    return report


def _receipt(root, preparation):
    files = {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in root.rglob("*")
        if p.is_file() and p.name != "receipt.json"
    }
    _save(
        root, "receipt.json", {"preparation_sha256": preparation["content_sha256"], "files": files}
    )


async def execute_opening_run(preparation, *, approved_sha256, model_api_key, http_client=None):
    require(
        approved_sha256 == preparation["content_sha256"],
        "approval",
        "Explicit opening digest approval required",
    )
    root, parent, execution, identity, plan = _verify_opening(preparation, implementation=True)
    require(preparation["packet"]["cases"], "packet", "No eligible missing-hours visits")
    require(bool(model_api_key), "credentials", "Model credential required")
    attempt = root / "execution"
    attempt.mkdir(exist_ok=False)
    owns_client = http_client is None
    client = http_client if http_client is not None else httpx.AsyncClient()
    transport = EvaluationTransport(preparation, attempt, client, None, model_api_key)
    try:
        async with asyncio.timeout(preparation["options"]["total_timeout_seconds"]):
            raw, event = await transport.model(
                preparation["packet"], operation="opening_access", reasoning_effort="medium"
            )
            material = {
                "schema_version": MATERIAL_VERSION,
                "packet": preparation["packet"],
                "provider": "azure_foundry",
                "request": event["request"]["json"],
                "response": raw,
                "requested_at": event["requested_at"],
                "retrieved_at": event["retrieved_at"],
            }
            _save(attempt, "model-result.json", material)
            validate_material(material, preparation["packet"])
            usage = transport.usage()
            report = _compose(
                preparation, parent, execution, identity, plan, material, usage, _now()
            )
            _verify_opening(preparation, implementation=True)
    except (
        ValueError,
        KeyError,
        TypeError,
        OSError,
        TimeoutError,
        RuntimeError,
        TransportFailure,
    ) as exc:
        usage = transport.usage()
        report = {
            "schema_version": "rtpeval_execution_report_1",
            "processing_status": "stopped",
            "preparation_sha256": preparation["content_sha256"],
            "scope": preparation["scope"],
            "reason": exc.code if isinstance(exc, TransportFailure) else str(exc),
            "usage": {
                "actual_google_sends": 0,
                "actual_model_sends": len(transport.model_calls),
                "retries": 0,
                "actual_billing": None,
                "raw": usage,
                "cost": build_cost_report(
                    [{"sha256": canonical_digest(usage), "usage": usage}], preparation["prices"]
                ),
            },
        }
    finally:
        if owns_client:
            await client.aclose()
    _save(attempt, "usage.json", usage)
    _save(attempt, "report.json", report)
    _receipt(attempt, preparation)
    return report


def replay_opening_run(directory):
    preparation = _read(Path(directory) / "preparation.json")[0]
    root, parent, execution, identity, plan = _verify_opening(preparation)
    attempt = root / "execution"
    verify_receipt(attempt, preparation["content_sha256"])
    saved = _read(attempt / "report.json")[0]
    usage = _read(attempt / "usage.json")[0]
    journal = [
        _read(p)[0] for p in sorted((attempt / "http").glob("*.json"), key=lambda p: int(p.stem))
    ]
    require(
        [usage_event(e) for e in journal] == usage["provider_events"],
        "usage",
        "HTTP journal differs from usage",
    )
    if saved["processing_status"] == "stopped":
        require(saved["usage"]["raw"] == usage, "usage", "Stopped report usage mismatch")
        return saved
    material = _read(attempt / "model-result.json")[0]
    validate_material(material, preparation["packet"])
    require(
        len(journal) == 1 and len(usage["model_calls"]) == 1,
        "receipt",
        "Exactly one model attempt required",
    )
    event = journal[0]
    require(
        event["request"]
        == {
            "method": "POST",
            "url": preparation["options"]["model_endpoint"] + "responses",
            "json": material["request"],
        }
        and event["status_code"] == 200
        and _decode((attempt / "http" / (event["event_id"] + ".bin")).read_bytes())
        == material["response"]
        and event["requested_at"] == material["requested_at"]
        and event["retrieved_at"] == material["retrieved_at"],
        "receipt",
        "Model HTTP provenance mismatch",
    )
    require(
        all(
            usage["model_calls"][0][k] == v
            for k, v in model_usage(material["response"], preparation["options"]).items()
        ),
        "usage",
        "Actual token counts differ from model response",
    )
    report = _compose(
        preparation, parent, execution, identity, plan, material, usage, saved["generated_at"]
    )
    require(report == saved, "report", "Opening evaluation replay differs")
    return report
