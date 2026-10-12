"""Physical evidence eligibility, separate from correctness of original claims."""

from datetime import datetime

from .identity import _candidate, _evidence_candidates, _verified_google_source
from .records import text


def associated_place_id(record):
    """Read only after whole-report replay validation; retain historical adoption rules."""
    if "place_association" in record:
        association = record["place_association"]
        return association["place_id"] if association["state"] == "verified" else None
    return record["canonical_place_id"]


def opening_place_id(check):
    """Select the physical venue of a replayed opening check, including historical rows."""
    return check.get("associated_place_id", check["canonical_place_id"])


def _result(pid, reason):
    return {"state": "verified" if pid else "UNKNOWN", "place_id": pid, "reason": reason}


def _provenance(observation):
    try:
        return datetime.fromisoformat(observation["retrieved_at"]).utcoffset() is not None
    except (KeyError, TypeError, ValueError):
        return False


def program_association(ref, observation):
    """Verify the submitted ID without substituting a searched venue or repairing a claim."""
    pid = ref["claimed_place_id"]
    details = observation.get("details") if observation else None
    if not text(pid):
        return _result(None, "missing_claimed_place_id")
    if (
        not observation
        or not _verified_google_source(observation)
        or not details
        or details["status"] != "available"
        or not _provenance(details)
    ):
        return _result(None, "independent_id_evidence_unavailable")
    candidate = _candidate(details.get("place"))
    if (
        details.get("requested_place_id") != pid
        or candidate is None
        or candidate["place_id"] != pid
    ):
        return _result(None, "independent_id_evidence_conflicting")
    return _result(pid, "independent_api_id_verified")


def v0_association(record, observation):
    """Use the existing source-bound, validated judgment, never candidate presence or rank."""
    judgment = record["model_judgment"]
    if (
        not judgment
        or judgment["decision"] != "match"
        or not text(judgment["candidate_id"])
        or judgment["destination_assessment"] != "consistent"
        or judgment["address_assessment"]
        not in ("equivalent", "different_precision", "incorrect_claim", "not_supplied")
    ):
        return _result(None, "candidate_correspondence_unverified")
    pid = judgment["candidate_id"]
    detail, search = _evidence_candidates(observation, require_provenance=True)
    candidates = [c for c in ([detail] if detail else []) + search if c["place_id"] == pid]
    if not candidates or any(c != candidates[0] for c in candidates[1:]):
        return _result(None, "candidate_evidence_missing_or_conflicting")
    # The model envelope and citations were validated before reaching this boundary.
    for kind in ("details", "search"):
        item = observation.get(kind)
        if not item or item["status"] != "available":
            continue
        if not _provenance(item):
            return _result(None, "candidate_provenance_unverified")
        if kind == "details" and (
            _candidate(item.get("place")) is None
            or item.get("requested_place_id") != item["place"]["place_id"]
        ):
            return _result(None, "candidate_id_evidence_conflicting")
    return _result(pid, "validated_v0_correspondence")
