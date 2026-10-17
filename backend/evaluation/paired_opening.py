"""One-use V3 paired access preparation over independently frozen observations."""

import hashlib
from pathlib import Path

from .cost_report import build_cost_report, validate_prices
from .evaluation_run import _now, _options, _save
from .evaluation_transport import check_tokenizer
from .intake import _read, load_batch
from .opening import score_opening
from .opening_judgment import prepare_packet
from .records import canonical_digest, require

VERSION = "rtpeval_pair_opening_preparation_1"
COMMON_VERSION = "rtpeval_pair_opening_preparation_2"


def subject_binding(identity):
    policy = identity.get("association_policy_version")
    if policy not in ("versioned_api_identity_5", "versioned_api_identity_6"):
        return {}
    replay = identity["identity_versioned_replay"]
    return {
        "identity_policy": policy,
        "subject_policy": "requirement_subject_correspondence_2"
        if policy == "versioned_api_identity_6"
        else "requirement_subject_correspondence_1",
        "subject_evidence_sha256": canonical_digest(
            replay.get("subject_evidence", replay["evidence"])
        ),
        "subject_result_sha256": canonical_digest(replay.get("subject_result")),
    }


def prepare_pair_opening(
    manifest,
    identity_path,
    snapshot_directory,
    directory,
    *,
    options,
    prices,
    schedule_context=None,
    expected_plan=None,
):
    """Freeze a fresh packet without acquiring Google evidence or sending a model request."""
    check_tokenizer()
    options = _options(options, allow_no_google=True)
    require(options["max_google_sends"] == 0, "options", "Paired access sends no Google requests")
    validate_prices(prices)
    require(prices["currency"] == "USD", "prices", "USD reference budget required")
    intake = load_batch(manifest).to_dict()
    identity, identity_sha = _read(Path(identity_path))
    binding = subject_binding(identity)
    packet = prepare_packet(
        intake,
        identity,
        snapshot_directory,
        schedule_context,
        model=options["model"],
        paired=True,
        pair_only=True,
        expected_plan=expected_plan,
    )
    require(packet["cases"], "packet", "No eligible paired missing-hours visits")
    preparation = {
        "schema_version": COMMON_VERSION if binding else VERSION,
        **binding,
        "status": "prepared",
        "prepared_at": _now(),
        "directory": str(Path(directory).resolve()),
        "manifest": str(Path(manifest).resolve()),
        "identity_path": str(Path(identity_path).resolve()),
        "identity_sha256": identity_sha,
        "snapshot_directory": str(Path(snapshot_directory).resolve()),
        "intake": intake,
        "schedule_context": schedule_context,
        "expected_plan": expected_plan,
        "packet": packet,
        "options": options,
        "prices": prices,
        "max_model_sends": 1,
        "max_retries": 0,
        "scope": "same_run_v3_paired_access_assessment",
        "implementation_hashes": {
            str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [
                *Path(__file__).parent.glob("*.py"),
                Path(__file__).parents[1] / "pace_policy.py",
                Path(__file__).parents[1] / "app/runtime/token_counting.py",
            ]
        },
    }
    preparation["content_sha256"] = canonical_digest(preparation)
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=False)
    _save(root, "preparation.json", preparation)
    _save(root, "packet.json", packet)
    return preparation


def verify_pair_opening(preparation, *, implementation=False):
    require(
        preparation.get("schema_version") in (VERSION, COMMON_VERSION)
        and canonical_digest({k: v for k, v in preparation.items() if k != "content_sha256"})
        == preparation.get("content_sha256"),
        "preparation",
        "Paired opening digest mismatch",
    )
    root = Path(preparation["directory"])
    require(
        _read(root / "preparation.json")[0] == preparation
        and _read(root / "packet.json")[0] == preparation["packet"],
        "preparation",
        "Saved preparation differs",
    )
    require(
        load_batch(preparation["manifest"]).to_dict() == preparation["intake"],
        "manifest",
        "Paired original sources changed",
    )
    identity, digest = _read(Path(preparation["identity_path"]))
    require(digest == preparation["identity_sha256"], "identity", "Paired identity bytes changed")
    if preparation["schema_version"] == COMMON_VERSION:
        binding = subject_binding(identity)
        require(
            binding and all(preparation.get(k) == v for k, v in binding.items()),
            "identity",
            "Paired opening common-subject provenance changed",
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
    packet = prepare_packet(
        preparation["intake"],
        identity,
        preparation["snapshot_directory"],
        preparation["schedule_context"],
        model=preparation["options"]["model"],
        paired=True,
        pair_only=True,
        expected_plan=preparation["expected_plan"],
    )
    require(packet == preparation["packet"], "packet", "Paired eligibility/evidence changed")
    return (
        root,
        preparation,
        Path(preparation["snapshot_directory"]),
        identity,
        preparation["expected_plan"],
    )


def compose_pair_opening(preparation, directory, identity, plan, material, usage, generated_at):
    opening = score_opening(
        preparation["intake"],
        identity,
        directory,
        preparation["schedule_context"],
        paired=True,
        expected_plan=plan,
        opening_judgment=material,
    ).to_dict()
    require(opening["status"] == "complete", "opening", "Paired opening report did not complete")
    return {
        "schema_version": "rtpeval_execution_report_1",
        "processing_status": "complete",
        "generated_at": generated_at,
        "preparation_sha256": preparation["content_sha256"],
        "scope": preparation["scope"],
        "opening": opening,
        "usage": {
            "actual_google_sends": 0,
            "actual_model_sends": len(usage["model_calls"]),
            "retries": 0,
            "actual_billing": None,
            "raw": usage,
            "cost": build_cost_report(
                [{"sha256": canonical_digest(usage), "usage": usage}], preparation["prices"]
            ),
        },
    }
