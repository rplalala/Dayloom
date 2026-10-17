"""Common requirement targets from reviewed source and independent candidates only."""

import json

from ._addresses import (
    compare_address_claim,
    components,
    location_matches,
    strict_destination_matches,
)
from ._claims import normalized
from .identity import _candidate, _intake_dict, _observation_index, identity_references
from .identity_llm import IdentityJudgmentPacket, _correspondence_schema, _decisions, _packet
from .records import canonical_digest as digest
from .records import freeze, text

LEGACY_POLICY_VERSION = "requirement_subject_correspondence_1"
POLICY_VERSION = "requirement_subject_correspondence_2"
POLICIES = (LEGACY_POLICY_VERSION, POLICY_VERSION)


def validate_policy(policy_version):
    if policy_version not in POLICIES:
        raise ValueError("Unsupported requirement-subject policy")
    return policy_version


INSTRUCTIONS = """Resolve original user-requested venues against their own independent Google facts.
These are common requirement targets, not planner visits or V0 judgments. Use only the
supplied original request, reviewed subject/obligations and this case's candidates.
Provider rank, a unique result and spelling similarity alone never establish identity.
Consider multilingual names, abbreviations, branches, entrances, shops and competing venues.
Select only a supplied owned candidate when the complete evidence uniquely identifies the
requested venue. Ambiguity or insufficient facts requires unknown, candidate_id null.
Never invent aliases, candidate facts, coordinates or planner claims. Do not use memory.
Destination context describes a geographic area, not a complete street address. The raw
reviewed location and its derived purpose remain in location_context. Explicit constraints
remain in claim.location and must be met at their supplied precision; never drop them.
Return every supplied reference exactly once in the decisions object, with reference_id
equal to its key. A match requires consistent destination, equivalent explicit location
(or not_supplied when claim.location is null), and citations claim.place_name,
claim.destination, candidate.display_name, candidate.formatted_address and claim.location
when supplied. Cite only real nonempty fields of this case and selected candidate.
No factual opening/route or itinerary compliance judgment is requested."""


def _candidates(ref, observation, binding):
    """Reject untrusted or incomplete acquisition before exposing any candidate to a model."""
    if not observation or observation.get("source_kind") != "independent_google_places":
        return [], "subject_independent_source_missing"
    if binding is not None:
        details = observation.get("details") or {}
        candidate = _candidate(details.get("place"))
        if (
            not text(binding)
            or details.get("status") != "available"
            or not text(details.get("retrieved_at"))
            or details.get("requested_place_id") != binding
            or not candidate
            or candidate["place_id"] != binding
        ):
            return [], "subject_details_unverified"
        raw = [details["place"]]
    else:
        search = observation.get("search") or {}
        raw = search.get("candidates")
        count = search.get("actual_result_count")
        if (
            search.get("status") != "available"
            or not text(search.get("retrieved_at"))
            or search.get("query") != ref["name"]
            or search.get("requested_page_size") != 20
            or not isinstance(raw, list)
            or type(count) is not int
            or count != len(raw)
            or count >= 20
            or "next_page_token" in search
        ):
            return [], "subject_search_unverified_or_incomplete"
    candidates = {}
    for item in raw:
        candidate = _candidate(item)
        if candidate is None:
            return [], "malformed_subject_candidate"
        # Rank is acquisition metadata, never identity evidence or a selection shortcut.
        candidate.pop("provider_rank", None)
        pid = candidate["place_id"]
        if pid in candidates and candidates[pid] != candidate:
            return [], "subject_candidate_facts_conflicting"
        try:
            components(candidate, hierarchical=True)
        except ValueError:
            return [], "subject_destination_evidence_malformed"
        candidates[pid] = candidate
    return [candidates[k] for k in sorted(candidates)], "independent_candidates"


def subject_cases(intake, evidence):
    """One source-bound case per reviewed subject; never expose submitted runs."""
    prepared = _intake_dict(intake)
    refs = identity_references(prepared)
    observations = _observation_index(evidence, refs, prepared, allow_incomplete=True)
    groups = {g["group_id"]: g for g in prepared["inventory"]}
    cases = []
    for ref in refs:
        if ref["kind"] != "requirement_subject":
            continue
        group = groups[ref["group_id"]]
        spec = group["requirement_spec"]
        subject = next(
            s for s in spec["subjects"] if s["subject_id"] == ref["source"]["subject_id"]
        )
        candidates, reason = _candidates(
            ref, observations.get(ref["reference_id"]), subject.get("source_place_id")
        )
        location = ref["location"]
        purpose = (
            "destination_context"
            if text(location) and normalized(location) == normalized(ref["destination"])
            else "explicit_constraint"
            if text(location)
            else "not_supplied"
        )
        cases.append(
            {
                "reference_id": ref["reference_id"],
                "claim": {
                    "place_name": ref["name"],
                    "destination": ref["destination"],
                    "location": location if purpose == "explicit_constraint" else None,
                    "claimed_place_id": None,
                },
                "source": ref["source"],
                "original_request": group["input"],
                "reviewed_subject": subject,
                "reviewed_obligations": [
                    o for o in spec["obligations"] if o.get("subject_ref") == subject["subject_id"]
                ],
                "location_context": {"purpose": purpose, "original": location},
                "acquisition_reason": reason,
                "independent_observation_sha256": digest(observations.get(ref["reference_id"])),
                "candidates": candidates,
            }
        )
    return cases


def prepare_subject_judgment(intake, evidence, *, model, policy_version=POLICY_VERSION):
    """Freeze the independent common-subject request; return None for an empty scope."""
    if not text(model):
        raise ValueError("An explicit subject judgment model is required")
    validate_policy(policy_version)
    cases = subject_cases(intake, evidence)
    if not cases:
        return None
    packet = _packet(cases)
    request = {
        "model": model,
        "instructions": INSTRUCTIONS + "\n" + packet.payload["instructions"],
        "input": json.dumps(
            {"cases": packet.payload["cases"]},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ),
        "tools": [],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "RequirementSubjects",
                "strict": True,
                "schema": _correspondence_schema(packet),
            }
        },
    }
    if policy_version == POLICY_VERSION:
        request["instructions"] += (
            "\npostal_town is typed city evidence. Conflicting city/country evidence remains "
            "unresolved; a unique candidate is not sufficient correspondence evidence."
        )
    return IdentityJudgmentPacket(
        freeze(
            {
                "schema_version": "rtpeval_subject_judgment_packet_1"
                if policy_version == LEGACY_POLICY_VERSION
                else "rtpeval_subject_judgment_packet_2",
                "association_policy_version": policy_version,
                "source_cases_sha256": digest(cases),
                "reference_maps": packet.manifest,
                "request": request,
                "request_sha256": digest(request),
            }
        )
    )


def resolve_subjects(intake, evidence, material=None, *, policy_version=POLICY_VERSION):
    """Import only owned semantic decisions; factual compatibility still gates adoption."""
    validate_policy(policy_version)
    cases = subject_cases(intake, evidence)
    if not cases:
        if material is not None:
            raise ValueError("Subject results require named subjects")
        return {}, None
    decisions, provenance = _decisions(
        intake,
        evidence,
        cases,
        material,
        historical=False,
        subject_only=True,
        subject_policy=policy_version,
    )
    targets = {}
    for case in cases:
        judgment = decisions.get(case["reference_id"])
        candidate = next(
            (
                c
                for c in case["candidates"]
                if judgment and c["place_id"] == judgment["candidate_id"]
            ),
            None,
        )
        reason, canonical = case["acquisition_reason"], None
        if reason == "independent_candidates":
            reason = (
                "subject_judgment_missing" if not judgment else "subject_" + judgment["decision"]
            )
        if candidate and judgment["decision"] == "match":
            location = case["claim"]["location"]
            compatible = (
                not text(location)
                or location_matches(
                    location, candidate, postal_town=policy_version == POLICY_VERSION
                )
                or compare_address_claim(location, candidate)["verdict"] == "PASS"
            )
            if (
                strict_destination_matches(
                    case["claim"]["destination"],
                    candidate,
                    postal_town=policy_version == POLICY_VERSION,
                )
                and compatible
                and judgment["destination_assessment"] == "consistent"
                and judgment["address_assessment"] in ("equivalent", "not_supplied")
            ):
                canonical, reason = candidate["place_id"], "independent_subject_correspondence"
            else:
                reason = "subject_geographic_constraint_unverified"
        targets[case["reference_id"]] = {
            "canonical_place_id": canonical,
            "reason": reason,
            "model_judgment": judgment,
            "location_context": case["location_context"],
            "candidate_ids": [c["place_id"] for c in case["candidates"]],
            "subject_case_sha256": digest(case),
        }
    return targets, provenance
