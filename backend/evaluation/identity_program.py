"""Version-scoped evaluation from original claims and independent API observations."""

from ._addresses import compare_address_claim, destination_matches, strict_destination_matches
from .identity import (
    IDENTITY_VERSION,
    SUBJECT_SCOPE_VERSION,
    IdentityResult,
    _candidate,
    _claimed_id_status,
    _evidence_candidates,
    _intake_dict,
    _observation_index,
    _summaries,
    identity_references,
)
from .place_association import program_association, v0_association
from .records import canonical_digest as digest
from .records import freeze, text

LEGACY_POLICY_VERSION = "versioned_api_identity_1"
PREVIOUS_POLICY_VERSION = "versioned_api_identity_2"
EXACT_POLICY_VERSION = "versioned_api_identity_3"
POLICY_VERSION = "versioned_api_identity_4"
PREVIOUS_COMMON_POLICY_VERSION = "versioned_api_identity_5"
COMMON_POLICY_VERSION = "versioned_api_identity_6"
VERSIONED_TARGET_POLICIES = (
    PREVIOUS_POLICY_VERSION,
    EXACT_POLICY_VERSION,
    POLICY_VERSION,
    PREVIOUS_COMMON_POLICY_VERSION,
    COMMON_POLICY_VERSION,
)


def subject_bindings(intake):
    """Retained requirement IDs are claims; independent Details must verify them."""
    return {
        (g["group_id"], s["subject_id"]): s.get("source_place_id")
        for g in _intake_dict(intake)["inventory"]
        for s in g["requirement_spec"]["subjects"]
    }


def _subject_search(ref, search, *, equivalent_addresses=False, address_comparisons=None):
    if "next_page_token" in search and not text(search["next_page_token"]):
        return "UNKNOWN", "subject_pagination_malformed", None
    if search["actual_result_count"] != len(search["candidates"]) or (
        search["actual_result_count"] >= search["requested_page_size"]
        or search.get("next_page_token")
    ):
        return "UNKNOWN", "subject_search_incomplete", None
    matches, facts, comparisons = {}, {}, {}
    for raw in search["candidates"]:
        candidate = _candidate(raw)
        if candidate is None:
            return "UNKNOWN", "malformed_subject_candidate", None
        pid = candidate["place_id"]
        identity_facts = {
            key: candidate.get(key)
            for key in ("display_name", "formatted_address", "address_components")
        }
        if pid in facts and facts[pid] != identity_facts:
            return "UNKNOWN", "subject_candidate_facts_conflicting", None
        facts[pid] = identity_facts
        try:
            destination_verified = strict_destination_matches(ref["destination"], candidate)
        except ValueError:
            return "UNKNOWN", "subject_destination_evidence_malformed", None
        if ref["name"] != candidate["display_name"] or not destination_verified:
            continue
        if text(ref["location"]):
            if equivalent_addresses:
                comparisons[pid] = {
                    "place_id": pid,
                    **compare_address_claim(ref["location"], candidate),
                }
                if comparisons[pid]["verdict"] == "FAIL":
                    continue
            elif ref["location"] != candidate["formatted_address"]:
                continue
        matches[pid] = candidate
    if address_comparisons is not None:
        address_comparisons.extend(comparisons[pid] for pid in sorted(comparisons))
    if equivalent_addresses and not matches and len(comparisons) == 1:
        return "FAIL", "api_address_mismatch", None
    if len(matches) != 1:
        return "UNKNOWN", "subject_search_ambiguous" if matches else "subject_search_no_match", None
    return "PASS", "independent_api_exact_match", next(iter(matches))


def _check(
    ref,
    observation,
    binding=None,
    *,
    historical=False,
    equivalent_addresses=False,
    address_comparisons=None,
):
    claimed = ref["claimed_place_id"] if ref["kind"] == "primary_visit" else binding
    candidate = None
    if ref["kind"] == "primary_visit" and not text(claimed):
        return "FAIL", "missing_claimed_place_id", None
    if ref["kind"] == "primary_visit" and ref["name_source"] != "place_name":
        return "FAIL", "missing_claimed_place_name", None
    if ref["kind"] == "primary_visit" and not text(ref["location"]):
        return "FAIL", "missing_claimed_address", None
    if binding is not None and not text(binding):
        return "UNKNOWN", "subject_binding_invalid", None
    if not historical and observation and observation.get("source_kind") is None:
        return "UNKNOWN", "independent_source_missing", None
    if text(claimed):
        details = observation.get("details") if observation else None
        if not details or details["status"] != "available":
            return "UNKNOWN", "id_details_unavailable", None
        if not historical and not text(details.get("retrieved_at")):
            return "UNKNOWN", "id_details_provenance_missing", None
        if details.get("requested_place_id") != claimed:
            return "UNKNOWN", "id_request_mismatch", None
        candidate = _candidate(details.get("place"))
        if candidate is None:
            return "UNKNOWN", "malformed_details", None
        if candidate["place_id"] != claimed:
            return "UNKNOWN", "id_response_mismatch", None
    else:
        search = observation.get("search") if observation else None
        if not search or search["status"] != "available":
            return "UNKNOWN", "subject_search_unavailable", None
        if not historical and not text(search.get("retrieved_at")):
            return "UNKNOWN", "subject_search_provenance_missing", None
        if search.get("query") != ref["name"] or search.get("requested_page_size") != 20:
            return "UNKNOWN", "subject_search_scope_unverified", None
        if not historical:
            return _subject_search(
                ref,
                search,
                equivalent_addresses=equivalent_addresses,
                address_comparisons=address_comparisons,
            )
        if search["actual_result_count"] != 1 or len(search["candidates"]) != 1:
            return "UNKNOWN", "subject_search_ambiguous", None
        candidate = _candidate(search["candidates"][0])
        if candidate is None:
            return "UNKNOWN", "malformed_subject_candidate", None
        try:
            destination_verified = destination_matches(ref["destination"], candidate)
        except ValueError:
            return "UNKNOWN", "subject_destination_evidence_malformed", None
        if not destination_verified:
            return "UNKNOWN", "subject_destination_unverified", None
    if ref["name"] != candidate["display_name"]:
        return "FAIL", "api_name_mismatch", None
    if text(ref["location"]):
        if equivalent_addresses:
            comparison = compare_address_claim(ref["location"], candidate)
            if comparison["verdict"] == "FAIL":
                return "FAIL", "api_address_mismatch", None
            if comparison["basis"] != "exact":
                return "PASS", "independent_api_address_equivalent", candidate["place_id"]
        elif ref["location"] != candidate["formatted_address"]:
            return "FAIL", "api_address_mismatch", None
    return "PASS", "independent_api_exact_match", candidate["place_id"]


def resolve_versioned_identities(
    intake,
    evidence,
    *,
    model_result=None,
    historical=False,
    previous=False,
    exact_addresses=False,
    common_subjects=False,
    subject_result=None,
    subject_policy=None,
    subject_evidence=None,
):
    """V0 model results never decide targets or visits of another version."""
    prepared = _intake_dict(intake)
    if sum((historical, previous, exact_addresses, common_subjects)) > 1:
        raise ValueError("Choose one historical identity policy")
    if (
        subject_result is not None or subject_policy is not None or subject_evidence is not None
    ) and not common_subjects:
        raise ValueError("Common subject results require their declared policy")
    targets, subject_provenance = {}, None
    if common_subjects:
        from .subject_correspondence import LEGACY_POLICY_VERSION as LEGACY_SUBJECT_POLICY
        from .subject_correspondence import POLICY_VERSION as SUBJECT_POLICY
        from .subject_correspondence import resolve_subjects

        if subject_policy is None:
            subject_policy = SUBJECT_POLICY
        targets, subject_provenance = resolve_subjects(
            prepared,
            subject_evidence if subject_evidence is not None else evidence,
            subject_result,
            policy_version=subject_policy,
        )
        common_policy = (
            PREVIOUS_COMMON_POLICY_VERSION
            if subject_policy == LEGACY_SUBJECT_POLICY
            else COMMON_POLICY_VERSION
        )
    refs = identity_references(prepared)
    observed = _observation_index(evidence, refs, prepared) if historical else {}
    if not historical:
        from .identity_targets import versioned_observations, versioned_references

        refs = versioned_references(prepared)
        observed = versioned_observations(prepared, evidence, refs)
    bindings = subject_bindings(prepared)
    subject_observations = (
        _observation_index(
            subject_evidence, identity_references(prepared), prepared, allow_incomplete=True
        )
        if subject_evidence is not None
        else {}
    )
    v0_refs = [
        r
        for r in refs
        if r["version"] == "v0" and (not common_subjects or r["kind"] == "primary_visit")
    ]
    model_records, provenance = {}, None
    if v0_refs:
        from .identity_llm import resolve_llm_identities

        model = resolve_llm_identities(
            prepared,
            evidence,
            model_result=model_result,
            v0_only=True,
            legacy_v0=historical,
            visits_only=common_subjects,
        ).to_dict()
        model_records = {r["reference_id"]: r for r in model["records"]}
        provenance = model["model_judgment_provenance"]
    elif model_result is not None:
        raise ValueError("Model results require eligible V0 references")
    records = []
    for ref in refs:
        rid = ref["reference_id"]
        if rid in model_records:
            record = model_records[rid]
            if not historical and not previous and ref["kind"] == "primary_visit":
                record["place_association"] = v0_association(record, observed.get(rid))
            records.append(record)
            continue
        observation = observed.get(rid)
        binding = bindings.get((ref["group_id"], ref["source"].get("subject_id")))
        candidate_comparisons = []
        target = targets.get(ref.get("evidence_reference_id"))
        if target is not None:
            if subject_evidence is not None:
                observation = subject_observations.get(ref["evidence_reference_id"])
            canonical, reason = target["canonical_place_id"], target["reason"]
            verdict = "PASS" if canonical else "UNKNOWN"
        else:
            verdict, reason, canonical = _check(
                ref,
                observation,
                binding,
                historical=historical,
                equivalent_addresses=not (historical or previous or exact_addresses),
                address_comparisons=candidate_comparisons,
            )
        detail, search = _evidence_candidates(observation)
        compared = detail or next((c for c in search if c["place_id"] == canonical), None)
        comparison = (
            compare_address_claim(ref["location"], compared)
            if target is None
            and not (historical or previous or exact_addresses)
            and compared
            and reason
            in {
                "api_address_mismatch",
                "independent_api_exact_match",
                "independent_api_address_equivalent",
            }
            and text(ref["location"])
            and ref["name"] == compared["display_name"]
            else None
        )
        if comparison is None and len(candidate_comparisons) == 1:
            comparison = {k: v for k, v in candidate_comparisons[0].items() if k != "place_id"}
        records.append(
            {
                **(
                    {"evidence_reference_id": ref["evidence_reference_id"]}
                    if "evidence_reference_id" in ref
                    else {}
                ),
                **{
                    k: ref[k]
                    for k in (
                        "reference_id",
                        "kind",
                        "source",
                        "group_id",
                        "version",
                        "projection",
                        "audit_key",
                    )
                },
                "resolution": "resolved" if canonical else "unresolved",
                "reason": reason,
                "canonical_place_id": canonical,
                "grounding_verdict": verdict,
                "decision_route": "independent_subject_correspondence"
                if target and canonical
                else (
                    "independent_api_address_equivalent"
                    if canonical and comparison and comparison["basis"] != "exact"
                    else "independent_api_exact"
                    if canonical
                    else None
                ),
                "claimed_id_association": _claimed_id_status(ref, observation, canonical),
                "high_impact": ref["high_impact"],
                "audit_selected": False,
                "evidence_hash": digest(observation),
                "observation_id": observation.get("observation_id") if observation else None,
                "review_history": [],
                "candidate_ids": sorted(
                    {c["place_id"] for c in ([detail] if detail else []) + search}
                ),
                "original_claim": {
                    "place_name": ref["name"],
                    "destination": ref["destination"],
                    "location": ref["location"],
                },
                "programmatic_judgment": {"verdict": verdict, "reason": reason},
                **({"common_subject_resolution": target} if target is not None else {}),
                **({"address_comparison": comparison} if comparison else {}),
                **(
                    {"candidate_address_comparisons": candidate_comparisons}
                    if candidate_comparisons
                    else {}
                ),
                **(
                    {"place_association": program_association(ref, observation)}
                    if not historical and not previous and ref["kind"] == "primary_visit"
                    else {}
                ),
            }
        )
    queue = [
        {"reference_id": r["reference_id"], "reason": r["reason"]}
        for r in records
        if r["grounding_verdict"] == "UNKNOWN"
    ]
    return IdentityResult(
        "needs_evidence" if queue else "complete",
        freeze(
            {
                "schema_version": IDENTITY_VERSION,
                "subject_scope_version": SUBJECT_SCOPE_VERSION,
                "association_policy_version": LEGACY_POLICY_VERSION
                if historical
                else PREVIOUS_POLICY_VERSION
                if previous
                else EXACT_POLICY_VERSION
                if exact_addresses
                else common_policy
                if common_subjects
                else POLICY_VERSION,
                "reference_set_digest": digest(refs),
                "batch_id": prepared["batch_id"],
                "batch_revision": prepared["revision"],
                "source_hashes": prepared["source_hashes"],
                "evidence_hash": digest(evidence),
                "review_hash": None,
                "audit_plan_hash": None,
                "audit_selected_reference_ids": [],
                "records": records,
                "review_queue": [],
                "judgment_queue": queue,
                "model_judgment_provenance": provenance,
                **({"subject_judgment_provenance": subject_provenance} if common_subjects else {}),
                "groups": _summaries(refs, records, prepared),
                "identity_versioned_replay": {
                    "evidence": evidence,
                    "model_result": model_result,
                    **({"subject_result": subject_result} if common_subjects else {}),
                    **(
                        {"subject_evidence": subject_evidence}
                        if subject_evidence is not None
                        else {}
                    ),
                },
            }
        ),
    )


def needs_versioned_replay(report):
    if not isinstance(report, dict):
        return False
    records = report.get("records")
    records = records if isinstance(records, list) else []
    return (
        report.get("association_policy_version")
        in (*VERSIONED_TARGET_POLICIES, LEGACY_POLICY_VERSION)
        or "identity_versioned_replay" in report
        or any(
            isinstance(r, dict) and ("programmatic_judgment" in r or "place_association" in r)
            for r in records
        )
    )


def verify_versioned_report(intake, report):
    """Recompute the complete report; stamps alone never certify programmatic verdicts."""
    try:
        replay = report["identity_versioned_replay"]
        policy = report.get("association_policy_version")
        return policy in (*VERSIONED_TARGET_POLICIES, LEGACY_POLICY_VERSION) and (
            resolve_versioned_identities(
                intake,
                replay["evidence"],
                model_result=replay["model_result"],
                historical=policy == LEGACY_POLICY_VERSION,
                previous=policy == PREVIOUS_POLICY_VERSION,
                exact_addresses=policy == EXACT_POLICY_VERSION,
                common_subjects=policy in (COMMON_POLICY_VERSION, PREVIOUS_COMMON_POLICY_VERSION),
                subject_policy=(
                    "requirement_subject_correspondence_1"
                    if policy == PREVIOUS_COMMON_POLICY_VERSION
                    else "requirement_subject_correspondence_2"
                    if policy == COMMON_POLICY_VERSION
                    else None
                ),
                subject_result=replay.get("subject_result"),
                subject_evidence=replay.get("subject_evidence"),
            ).to_dict()
            == report
        )
    except (ValueError, KeyError, TypeError, AttributeError):
        return False
