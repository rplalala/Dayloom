"""Closed independent Primary subject material, separate from paired visit evidence."""

from pathlib import Path

from .intake import _read
from .records import canonical_digest

VERSION = "rtpeval_paired_subject_source_1"
IDENTITY_POLICY = "versioned_api_identity_6"
SUBJECT_POLICY = "requirement_subject_correspondence_2"


def load_primary_subjects(directory, intake):
    """Validate closed facts and the real subject-model receipt without scoring Primary."""
    from .evaluation_transport import usage_event
    from .identity import identity_references
    from .paired_run import file_inventory
    from .primary_subjects import replay_subjects
    from .snapshot import build_identity_plan, identity_evidence, load_snapshot
    from .snapshot_import import _primary

    root = Path(directory).resolve()
    preparation = _read(root / "preparation.json")[0]
    if (
        preparation.get("schema_version") != "rtpeval_execution_preparation_3"
        or preparation.get("subject_policy") != SUBJECT_POLICY
        or preparation.get("intake") != intake
    ):
        raise ValueError("Paired common-subject Primary policy/intake mismatch")
    inventory = file_inventory(root)
    source = {
        "files": {
            name.replace("\\", "/"): {"path": name, "sha256": sha}
            for name, sha in inventory.items()
        }
    }
    plan = {"intake_hash": canonical_digest(intake)}
    # Validate both closed provider phases and their raw HTTP/usage attribution.
    for phase in ("identity", "evidence"):
        _primary(root, source, plan, phase)
    execution = root / "execution"
    snapshot = load_snapshot(
        execution / "identity-snapshot", expected_plan=build_identity_plan(intake)
    )
    evidence = identity_evidence(snapshot)
    journal = [
        _read(p)[0] for p in sorted((execution / "http").glob("*.json"), key=lambda p: int(p.stem))
    ]
    usage = _read(execution / "usage.json")[0]
    report = _read(execution / "report.json")[0]
    if (
        report.get("preparation_sha256") != preparation["content_sha256"]
        or report.get("usage", {}).get("raw") != usage
        or report.get("reports", {}).get("identity", {}).get("association_policy_version")
        != IDENTITY_POLICY
    ):
        raise ValueError("Paired common-subject Primary report binding mismatch")
    if [usage_event(e) for e in journal] != usage["provider_events"]:
        raise ValueError("Paired subject source journal/usage mismatch")
    result = replay_subjects(preparation, execution, evidence, journal, usage)
    selected = {
        r["reference_id"] for r in identity_references(intake) if r["kind"] == "requirement_subject"
    }
    subject_evidence = {
        **evidence,
        "records": [r for r in evidence["records"] if r["reference_id"] in selected],
    }
    if file_inventory(root) != inventory:
        raise ValueError("Paired common-subject source changed during validation")
    return {
        "schema_version": VERSION,
        "identity_policy": IDENTITY_POLICY,
        "subject_policy": SUBJECT_POLICY,
        "source_intake_sha256": canonical_digest(intake),
        "source_preparation_sha256": preparation["content_sha256"],
        "source_files": inventory,
        "evidence": subject_evidence,
        "subject_result": result,
    }


def resolve_pair_identity(intake, evidence, subject_source=None):
    from .identity_program import resolve_versioned_identities

    if subject_source is None:
        return resolve_versioned_identities(intake, evidence).to_dict()
    if (
        subject_source.get("schema_version") != VERSION
        or subject_source.get("identity_policy") != IDENTITY_POLICY
        or subject_source.get("subject_policy") != SUBJECT_POLICY
        or subject_source.get("source_intake_sha256") != canonical_digest(intake)
    ):
        raise ValueError("Paired common-subject material/policy binding mismatch")
    return resolve_versioned_identities(
        intake,
        evidence,
        common_subjects=True,
        subject_policy=SUBJECT_POLICY,
        subject_result=subject_source["subject_result"],
        subject_evidence=subject_source["evidence"],
    ).to_dict()
