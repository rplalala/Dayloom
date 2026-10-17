"""Offline V0 candidate correspondence and explicit historical identity replay."""

import json
from dataclasses import dataclass
from datetime import datetime

from .identity import (
    IDENTITY_VERSION,
    SUBJECT_SCOPE_VERSION,
    IdentityResult,
    _claimed_id_status,
    _evidence_candidates,
    _high_impact,
    _intake_dict,
    _observation_index,
    _summaries,
    identity_references,
)
from .identity_assistance import IdentityAssistancePacket
from .intake import _constant, _float, _pairs
from .records import canonical_digest as digest
from .records import freeze, text, thaw

POLICY_VERSION = "llm_identity_judgment_2"
LEGACY_V0_POLICY_VERSION = "v0_identity_correspondence_2"
V0_POLICY_VERSION = "v0_identity_correspondence_3"
PACKET_VERSION = "rtpeval_identity_judgment_packet_1"
RESULT_VERSION = "rtpeval_identity_model_result_1"
ADDRESS_STATES = (
    "equivalent",
    "different_precision",
    "incorrect_claim",
    "different_place",
    "unknown",
    "not_supplied",
)
DESTINATION_STATES = ("consistent", "contradictory", "unknown")
CITATION_PATHS = (
    "claim.place_name",
    "claim.destination",
    "claim.location",
    "claim.claimed_place_id",
    "claim.original_title",
    "candidate.display_name",
    "candidate.formatted_address",
    "candidate.address_components",
    "candidate.observations",
    "case.candidates",
)
INSTRUCTIONS = """Judge every supplied identity reference using only independent candidate facts.
Original planner claims are comparison inputs, not evidence. Provider rank is not confidence.
Select a supplied candidate only when it represents the intended venue; otherwise return
unknown or no_supported_match with candidate_id null. Do not invent candidates or facts.
Compare name, destination, location, supplied ID, and all conflicting provider observations.
High-impact subjects and visits need the same judgment as ordinary visits, without humans.
For address_assessment distinguish equivalent wording, different_precision, incorrect_claim
(the intended venue is identifiable but the original address is wrong), different_place,
unknown, and not_supplied. A match must not have different_place or unknown address assessment.
Different branches/cities are different_place, not harmless spelling differences. Insufficient
facts mean unknown. An incorrect original address may coexist with an identified venue,
but incorrect_claim and different_place are failures of the delivered claim: neither may
be adopted or replaced with candidate facts for downstream checks. Preserve the original
claim. Destination must be consistent for a match. Cite the original
claim fields and independent candidate name/address supporting each match. Explain all
judgments. An address failure requires claim.place_name, claim.destination, claim.location
and independent candidate support. Without a selected candidate, cite case.candidates (the
complete supplied independent set); without that support, use unknown. Do not certify opening
hours, routes, or factual accuracy of model judgments."""
V0_INSTRUCTIONS = """Correspond every original V0 claim to its supplied independent API candidates.
Return match only for a supplied candidate representing the intended venue; otherwise use
unknown or no_supported_match with candidate_id null. Matching and original-claim correctness
are separate: recognizing a candidate never repairs an incorrect address or different venue.
Use only supplied facts; do not invent candidates, coordinates, opening/route evidence or
corrected planner output. Original claims are comparison inputs, not independent evidence.
Compare name, destination, supplied ID and all conflicting provider observations. Provider
rank is not confidence. Destination must be consistent for adoption. Explain every judgment.
An independently supported contradictory destination is a delivered-claim failure even
when no original address was supplied. It requires claim.place_name, claim.destination and
candidate.display_name/candidate.formatted_address, or the complete nonempty case.candidates
without a selected candidate. Without that support use unknown, not contradictory.
Use only the evidence_fields schema enum, citing actual nonempty fields of this case and
its selected candidate. A match requires claim.place_name, claim.destination,
candidate.display_name and candidate.formatted_address; also cite claim.location and
claim.claimed_place_id when supplied. Do not invent or rename citation paths.
For every decision, if claim.location is absent/null/blank, address_assessment MUST be
not_supplied and claim.location MUST NOT be cited. Missing addresses alone are not errors.
If an original address is supplied, not_supplied is forbidden. Assess equivalent wording,
different_precision, incorrect_claim (recognized venue but wrong original address),
different_place or unknown according to available evidence. Insufficient support is unknown.
An address failure requires claim.place_name, claim.destination, claim.location and independent
candidate.display_name/candidate.formatted_address; without a selected candidate cite the
complete nonempty case.candidates instead. Such supported failures stay FAIL without adoption.
Do not certify opening hours, routes or factual accuracy of model judgments."""


@dataclass(frozen=True)
class IdentityJudgmentPacket:
    data: object

    def to_dict(self):
        return thaw(self.data)


def _packet(cases):
    return IdentityAssistancePacket(
        cases,
        additional_fields={
            "claimed_place_id": "p",
            "requested_place_id": "p",
        },
    )


def judgment_schema(*, historical=True):
    """Strict portable model output schema; no provider-specific runtime dependency."""
    properties = {
        "reference_id": {"type": "string"},
        "decision": {"type": "string", "enum": ["match", "unknown", "no_supported_match"]},
        "candidate_id": {"anyOf": [{"type": "string"}, {"type": "null"}]},
        "rationale": {"type": "string"},
        "evidence_fields": {"type": "array", "items": {"type": "string"}},
        "address_assessment": {"type": "string", "enum": list(ADDRESS_STATES)},
        "destination_assessment": {"type": "string", "enum": list(DESTINATION_STATES)},
    }
    if not historical:
        properties["evidence_fields"]["items"]["enum"] = list(CITATION_PATHS)
        properties["evidence_fields"]["description"] = (
            "Cite only actual nonempty fields owned by this case and selected candidate. "
            "Never cite claim.location when absent/null/blank."
        )
        properties["address_assessment"]["description"] = (
            "For every decision, absent/null/blank claim.location requires not_supplied; "
            "a supplied original location forbids not_supplied. Absence alone is not an error."
        )
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["decisions"],
        "properties": {
            "decisions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": properties,
                    "required": list(properties),
                },
            }
        },
    }


def _cases(prepared, evidence, *, v0_only=False, legacy_v0=False, visits_only=False):
    refs = identity_references(prepared)
    observed = _observation_index(evidence, refs, prepared) if not v0_only or legacy_v0 else {}
    if v0_only:
        if not legacy_v0:
            from .identity_targets import versioned_observations, versioned_references

            refs = versioned_references(prepared)
            observed = versioned_observations(prepared, evidence, refs)
        refs = [r for r in refs if r["version"] == "v0"]
    if visits_only:
        refs = [r for r in refs if r["kind"] == "primary_visit"]
    cases = []
    for ref in refs:
        detail, search = _evidence_candidates(
            observed.get(ref["reference_id"]), require_provenance=v0_only and not legacy_v0
        )
        candidates = {}
        for candidate in ([detail] if detail else []) + search:
            pid = candidate["place_id"]
            if pid not in candidates:
                candidates[pid] = {**candidate, "observations": []}
            candidates[pid]["observations"].append(candidate)
        cases.append(
            {
                "reference_id": ref["reference_id"],
                "kind": ref["kind"],
                "version": ref["version"],
                "projection": ref["projection"],
                "source": ref["source"],
                "claim": {
                    "place_name": ref["name"],
                    "original_title": ref["original_title"],
                    "destination": ref["destination"],
                    "location": ref["location"],
                    "claimed_place_id": ref["claimed_place_id"],
                },
                "observation": observed.get(ref["reference_id"]),
                "candidates": list(candidates.values()),
            }
        )
    return refs, observed, cases


def _correspondence_schema(packet, *, complete_coverage=True):
    """Require one owned decision per case using portable required object fields."""
    schema = packet.constrain_schema(judgment_schema(historical=False))
    item = schema["properties"]["decisions"]["items"]
    decisions = {}
    definitions = {}
    for supplied in (False, True):
        references = [
            case["reference_id"]
            for case in packet.payload["cases"]
            if text(case["claim"]["location"]) == supplied
        ]
        if not references:
            continue
        variant = json.loads(json.dumps(item))
        properties = variant["properties"]
        properties["reference_id"]["enum"] = references
        properties["address_assessment"]["enum"] = (
            [state for state in ADDRESS_STATES if state != "not_supplied"]
            if supplied
            else ["not_supplied"]
        )
        if not supplied:
            properties["evidence_fields"]["items"]["enum"].remove("claim.location")
        name = "WithAddress" if supplied else "WithoutAddress"
        definitions[name] = variant
        for reference in references:
            decisions[reference] = {"$ref": "#/$defs/" + name}
    references = [case["reference_id"] for case in packet.payload["cases"]]
    if not complete_coverage:
        schema["properties"]["decisions"]["items"] = {"anyOf": list(definitions.values())}
        return schema
    schema["$defs"] = definitions
    schema["properties"]["decisions"] = {
        "type": "object",
        "additionalProperties": False,
        "required": references,
        "properties": {reference: decisions[reference] for reference in references},
    }
    return schema


def prepare_identity_judgment(
    intake, evidence, *, model, historical=False, legacy_v0=False, visits_only=False
):
    """Freeze a complete model request without executing a model or provider."""
    if not text(model):
        raise ValueError("An explicit judgment model is required")
    prepared = _intake_dict(intake)
    refs, _, cases = _cases(
        prepared, evidence, v0_only=not historical, legacy_v0=legacy_v0, visits_only=visits_only
    )
    if not refs:
        if visits_only:
            return None
        raise ValueError("No applicable identity references")
    packet = _packet(cases)
    request = {
        "model": model,
        "instructions": (INSTRUCTIONS if historical else V0_INSTRUCTIONS)
        + "\n"
        + packet.payload["instructions"],
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
                "name": "IdentityJudgments",
                "strict": True,
                "schema": packet.constrain_schema(judgment_schema())
                if historical
                else _correspondence_schema(packet, complete_coverage=not legacy_v0),
            }
        },
    }
    if not historical and not legacy_v0 and not visits_only:
        request["instructions"] += (
            "\nV0 requirement_subject cases represent the original user-requested venue, "
            "not a planner visit. Resolve them only against their own independent candidates. "
            "Their judgments belong to V0 only. Do not borrow another case's decision."
        )
    if not historical and not legacy_v0:
        references = [case["reference_id"] for case in packet.payload["cases"]]
        request["instructions"] += (
            f"\nReturn exactly {len(references)} decisions in the decisions object, keyed by "
            + ", ".join(references)
            + ". Every supplied reference must appear exactly once, including visits and "
            "requirement subjects. Each value's reference_id must equal its key. "
            "If facts are insufficient, return an explicit unknown decision for that case; "
            "never omit it or substitute another case. Do not return a decisions array."
        )
    policy = LEGACY_V0_POLICY_VERSION if legacy_v0 else V0_POLICY_VERSION
    if visits_only:
        if historical or legacy_v0:
            raise ValueError("Visit-only packets require the common-subject policy")
        policy = "v0_visit_correspondence_1"
    scope = {} if historical else {"association_policy_version": policy}
    return IdentityJudgmentPacket(
        freeze(
            {
                "schema_version": PACKET_VERSION,
                **scope,
                "batch_id": prepared["batch_id"],
                "batch_revision": prepared["revision"],
                "intake_sha256": digest(prepared),
                "evidence_sha256": digest(evidence),
                "reference_set_digest": digest(refs),
                "reference_maps": packet.manifest,
                "request": request,
                "request_sha256": digest(request),
            }
        )
    )


def _decisions(
    intake,
    evidence,
    cases,
    material,
    *,
    historical=True,
    legacy_v0=False,
    visits_only=False,
    subject_only=False,
    subject_policy=None,
):
    if material is None:
        return {}, None
    from .identity_binding import RESULT_VERSION as BOUND_RESULT_VERSION
    from .identity_binding import reference_mapping

    if not isinstance(material, dict) or material.get("schema_version") not in (
        RESULT_VERSION,
        BOUND_RESULT_VERSION,
    ):
        raise ValueError("Invalid identity model result envelope")
    saved = material["packet"]
    model = saved["request"]["model"]
    if subject_only:
        from .subject_correspondence import prepare_subject_judgment

        expected = prepare_subject_judgment(
            intake, evidence, model=model, policy_version=subject_policy
        ).to_dict()
    else:
        expected = prepare_identity_judgment(
            intake,
            evidence,
            model=model,
            historical=historical,
            legacy_v0=legacy_v0,
            visits_only=visits_only,
        ).to_dict()
    response_cases, mapping = cases, None
    if material["schema_version"] == BOUND_RESULT_VERSION:
        if historical or legacy_v0 or subject_only:
            raise ValueError("Bound judgments require current V0 policy")
        source = material["binding_source"]
        original = prepare_identity_judgment(
            source["intake"], source["evidence"], model=model, visits_only=visits_only
        ).to_dict()
        if saved != original:
            raise ValueError("Identity model original packet/source mismatch")
        _, _, response_cases = _cases(
            source["intake"], source["evidence"], v0_only=True, visits_only=visits_only
        )
        mapping = reference_mapping(source["intake"], response_cases, intake, cases)
    elif saved != expected:
        raise ValueError("Identity model packet/source mismatch")
    start = datetime.fromisoformat(material["requested_at"])
    end = datetime.fromisoformat(material["retrieved_at"])
    if start.utcoffset() is None or end.utcoffset() is None or end < start:
        raise ValueError("Invalid identity model response chronology")
    response = material["response"]
    if (
        not isinstance(response, dict)
        or response.get("status") != "completed"
        or not text(response.get("id"))
        or response.get("model") != model
        or digest(response) != material.get("response_sha256")
        or not isinstance(response.get("output"), list)
        or any(
            not isinstance(m, dict) or m.get("type") not in ("message", "reasoning")
            for m in response["output"]
        )
    ):
        raise ValueError("Invalid identity model response/provenance")
    messages = [m for m in response["output"] if m["type"] == "message"]
    if any(
        m.get("role") != "assistant"
        or not isinstance(m.get("content"), list)
        or any(
            not isinstance(c, dict) or c.get("type") != "output_text" or not text(c.get("text"))
            for c in m["content"]
        )
        for m in messages
    ):
        raise ValueError("Malformed identity model message content")
    texts = [
        c["text"]
        for m in messages
        if m.get("type") == "message" and m.get("role") == "assistant"
        for c in m["content"]
        if c.get("type") == "output_text"
    ]
    if len(texts) != 1 or not text(texts[0]):
        raise ValueError("One bounded identity model output required")
    wire = json.loads(
        texts[0], object_pairs_hook=_pairs, parse_constant=_constant, parse_float=_float
    )
    if not historical and not legacy_v0:
        references = [case["reference_id"] for case in _packet(response_cases).payload["cases"]]
        if (
            not isinstance(wire, dict)
            or set(wire) != {"decisions"}
            or not isinstance(wire["decisions"], dict)
            or set(wire["decisions"]) != set(references)
            or any(
                not isinstance(row, dict) or row.get("reference_id") != key
                for key, row in wire["decisions"].items()
            )
        ):
            raise ValueError("Identity decisions must cover every owned reference exactly once")
        wire = {"decisions": [wire["decisions"][reference] for reference in references]}
    if (
        not isinstance(wire, dict)
        or set(wire) != {"decisions"}
        or not isinstance(wire["decisions"], list)
    ):
        raise ValueError("Invalid identity judgment response schema")
    fields = set(judgment_schema()["properties"]["decisions"]["items"]["properties"])
    for row in wire["decisions"]:
        if (
            not isinstance(row, dict)
            or set(row) != fields
            or not text(row["reference_id"])
            or not isinstance(row["decision"], str)
            or row["candidate_id"] is not None
            and not text(row["candidate_id"])
            or row["address_assessment"] not in ADDRESS_STATES
            or row["destination_assessment"] not in DESTINATION_STATES
        ):
            raise ValueError("Invalid identity judgment fields")
    canonical = _packet(response_cases).resolve(wire)
    if mapping is not None:
        for row in canonical["decisions"]:
            row["reference_id"] = mapping[row["reference_id"]]
    by_ref = {c["reference_id"]: c for c in cases}
    decisions = {}
    for row in canonical["decisions"]:
        case = by_ref[row["reference_id"]]
        candidate = next(
            (c for c in case["candidates"] if c["place_id"] == row["candidate_id"]), None
        )
        has_location = text(case["claim"]["location"])
        if not historical and (row["address_assessment"] == "not_supplied") == has_location:
            raise ValueError("Address assessment contradicts original location presence")
        cited = set(row["evidence_fields"])
        for field in cited:
            if field not in CITATION_PATHS:
                raise ValueError("Unsupported identity judgment citation")
            owner, key = field.split(".")
            value = (
                case["claim"] if owner == "claim" else case if owner == "case" else candidate or {}
            ).get(key)
            if not value or isinstance(value, str) and not text(value):
                raise ValueError("Empty identity judgment citation")
            if key == "address_components" and (
                not isinstance(value, list)
                or any(
                    not isinstance(c, dict)
                    or not text(c.get("longText"))
                    or "shortText" in c
                    and not isinstance(c["shortText"], str)
                    or "types" in c
                    and (not isinstance(c["types"], list) or not all(text(t) for t in c["types"]))
                    for c in value
                )
            ):
                raise ValueError("Malformed cited address components")
        address_failure = row["address_assessment"] in ("incorrect_claim", "different_place")
        destination_failure = not historical and row["destination_assessment"] == "contradictory"
        if address_failure or destination_failure:
            required = {"claim.place_name", "claim.destination"}
            if address_failure:
                required.add("claim.location")
            required.update(
                {"candidate.display_name", "candidate.formatted_address"}
                if candidate
                else {"case.candidates"}
            )
            if not required <= cited:
                failure = "Address" if address_failure else "Destination"
                raise ValueError(
                    f"{failure} failure requires original and independent evidence citations"
                )
        if row["decision"] == "match":
            required = {
                "claim.place_name",
                "claim.destination",
                "candidate.display_name",
                "candidate.formatted_address",
            }
            if has_location:
                required.add("claim.location")
            if text(case["claim"]["claimed_place_id"]):
                required.add("claim.claimed_place_id")
            if not required <= cited:
                raise ValueError("Independent and original identity support citations required")
            if historical and (row["address_assessment"] == "not_supplied") == has_location:
                raise ValueError("Address assessment contradicts original location presence")
        decisions[row["reference_id"]] = row
    return decisions, {
        **(
            {"association_policy_version": expected["association_policy_version"]}
            if not historical
            else {}
        ),
        "model": model,
        "response_id": response["id"],
        "request_sha256": saved["request_sha256"],
        **(
            {"binding": "verified_v0_case_facts", "applied_packet_sha256": digest(expected)}
            if mapping is not None
            else {}
        ),
        "response_sha256": material["response_sha256"],
        "material_sha256": digest(material),
        "requested_at": material["requested_at"],
        "retrieved_at": material["retrieved_at"],
        "origin": "llm",
    }


def resolve_llm_identities(
    intake, evidence, *, model_result=None, v0_only=False, legacy_v0=False, visits_only=False
):
    """Keep missing judgments unresolved; no human or automatic-name fallback."""
    prepared = _intake_dict(intake)
    refs, observed, cases = _cases(
        prepared, evidence, v0_only=v0_only, legacy_v0=legacy_v0, visits_only=visits_only
    )
    decisions, provenance = _decisions(
        prepared,
        evidence,
        cases,
        model_result,
        historical=not v0_only,
        legacy_v0=legacy_v0,
        visits_only=visits_only,
    )
    subjects = [r for r in refs if r["kind"] == "requirement_subject"]
    records = []
    for ref in refs:
        observation = observed.get(ref["reference_id"])
        detail, search = _evidence_candidates(observation)
        judgment = decisions.get(ref["reference_id"])
        canonical = None
        verdict = "UNKNOWN"
        reason = "model_judgment_missing"
        if judgment:
            reason = "model_" + judgment["decision"]
            if judgment["address_assessment"] in ("incorrect_claim", "different_place"):
                verdict = "FAIL"
                reason = "model_address_" + judgment["address_assessment"]
            elif v0_only and judgment["destination_assessment"] == "contradictory":
                verdict = "FAIL"
                reason = "model_destination_contradictory"
            elif judgment["decision"] == "match":
                if judgment["destination_assessment"] != "consistent" or judgment[
                    "address_assessment"
                ] in ("different_place", "unknown"):
                    reason = "model_conflicting_assessment"
                else:
                    canonical = judgment["candidate_id"]
                    verdict = "PASS"
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
                "decision_route": "llm_judgment" if canonical else None,
                "claimed_id_association": _claimed_id_status(
                    ref, observation, judgment["candidate_id"] if judgment else None
                ),
                "high_impact": _high_impact(ref, subjects, observed),
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
                "model_judgment": judgment,
                **(
                    {
                        "candidate_correspondence": {
                            "decision": judgment["decision"] if judgment else "unknown",
                            "candidate_id": judgment["candidate_id"] if judgment else None,
                        }
                    }
                    if v0_only
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
        "needs_model_judgment" if queue else "complete",
        freeze(
            {
                "schema_version": IDENTITY_VERSION,
                "subject_scope_version": SUBJECT_SCOPE_VERSION,
                "association_policy_version": POLICY_VERSION,
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
                "groups": _summaries(refs, records, prepared),
                "identity_llm_replay": {"evidence": evidence, "model_result": model_result},
            }
        ),
    )


def needs_llm_replay(report):
    """Identify structured model markers even if a policy stamp was substituted."""
    if not isinstance(report, dict):
        return False
    records = report.get("records")
    records = records if isinstance(records, list) else []
    return (
        report.get("association_policy_version") == POLICY_VERSION
        or "identity_llm_replay" in report
        or "model_judgment_provenance" in report
        or any(
            isinstance(r, dict)
            and ("model_judgment" in r or r.get("decision_route") == "llm_judgment")
            for r in records
        )
    )


def verify_llm_report(intake, report):
    """Recompute every field from the original intake, evidence and saved model result."""
    try:
        replay = report["identity_llm_replay"]
        return (
            report.get("association_policy_version") == POLICY_VERSION
            and resolve_llm_identities(
                intake, replay["evidence"], model_result=replay["model_result"]
            ).to_dict()
            == report
        )
    except (ValueError, KeyError, TypeError, AttributeError):
        return False
