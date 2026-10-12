"""Offline, source-linked identity preparation for independent evaluation."""

from collections.abc import Mapping
from dataclasses import dataclass

from ._addresses import (
    addresses_agree,
    components,
    destination_matches,
    location_matches,
    numbered_street,
)
from ._claims import claim_evidence, competing_title
from ._claims import normalized as _normal
from .records import IntakeResult, freeze, text, thaw
from .records import canonical_digest as _digest

IDENTITY_VERSION = "rtpeval_identity_1"
EVIDENCE_VERSION = "rtpeval_identity_evidence_1"
REVIEW_VERSION = "rtpeval_identity_reviews_1"
AUDIT_VERSION = "rtpeval_identity_audit_1"
SUBJECT_SCOPE_VERSION = "required_excluded_fixed_time_1"
ASSOCIATION_POLICY_VERSION = "structural_claims_typed_addresses_3"
VERSIONS = ("v0", "v1", "v2", "v3")


@dataclass(frozen=True)
class IdentityResult:
    """Immutable offline resolution and review preparation result."""

    status: str
    data: Mapping

    def to_dict(self):
        return {"status": self.status, **thaw(self.data)}


def _intake_dict(intake):
    value = intake.to_dict() if isinstance(intake, IntakeResult) else thaw(intake)
    if not isinstance(value, dict) or value.get("status") != "accepted":
        raise ValueError("Identity preparation requires an accepted batch intake")
    return value


def identity_references(intake):
    """Extract candidate visits and reviewed subjects without planner findings."""
    prepared = _intake_dict(intake)
    refs = []
    for group in prepared["inventory"]:
        gid = group["group_id"]
        destination = group["input"]["destination"]
        spec_hash = group["requirement_spec_sha256"]
        spec = group["requirement_spec"]
        relevant_subjects = {
            item["subject_ref"]
            for item in spec["obligations"]
            if item.get("kind") in ("required_visit", "excluded_visit", "fixed_visit_time")
            and item.get("resolution") == "resolved"
            and text(item.get("subject_ref"))
        }
        for subject in spec["subjects"]:
            if subject["subject_id"] not in relevant_subjects:
                continue
            name = subject.get("place_name") or subject.get("wording")
            locator = {
                "batch_id": prepared["batch_id"],
                "group_id": gid,
                "requirement_spec_sha256": spec_hash,
                "subject_id": subject["subject_id"],
            }
            refs.append(
                {
                    "reference_id": _digest(locator),
                    "audit_key": _digest(locator),
                    "kind": "requirement_subject",
                    "source": locator,
                    "group_id": gid,
                    "destination": destination,
                    "name": name if text(name) else None,
                    "original_title": None,
                    "name_source": "reviewed_subject" if text(name) else "missing",
                    "location": subject.get("location"),
                    "claimed_place_id": None,
                    "high_impact": True,
                    "version": None,
                    "projection": None,
                }
            )
        for version in VERSIONS:
            if version not in group["runs"]:
                continue
            run = group["runs"][version]
            projections = [("final", run["final"])]
            if version == "v3":
                projections.extend(
                    (label, projection)
                    for label, projection in run["optional"].items()
                    if projection is not None
                )
            for label, projection in projections:
                for activity in projection["activities"]:
                    if activity["evaluation_role"] != "primary_visit":
                        continue
                    original = activity["original"]
                    name = (
                        original["place_name"]
                        if text(original.get("place_name"))
                        else original.get("title")
                    )
                    refs.append(
                        {
                            "reference_id": activity["source"]["record_id"],
                            "audit_key": _digest(
                                {
                                    "batch_id": prepared["batch_id"],
                                    "group_id": gid,
                                    "input_sha256": group["input_sha256"],
                                    "version": version,
                                    "projection": label,
                                    "pointer": activity["source"]["pointer"],
                                    "name": name,
                                    "original_title": original.get("title"),
                                    "location": original.get("location"),
                                    "claimed_place_id": original.get("source_place_id"),
                                }
                            ),
                            "kind": "primary_visit",
                            "source": activity["source"],
                            "group_id": gid,
                            "destination": destination,
                            "name": name if text(name) else None,
                            "original_title": original.get("title"),
                            "name_source": "place_name"
                            if text(original.get("place_name"))
                            else "title",
                            "location": original.get("location"),
                            "claimed_place_id": original.get("source_place_id"),
                            "high_impact": False,
                            "version": version,
                            "projection": label,
                        }
                    )
    return refs


def _candidate(raw):
    if not isinstance(raw, dict):
        return None
    if not text(raw.get("place_id")) or not text(raw.get("display_name")):
        return None
    if not text(raw.get("formatted_address")):
        return None
    if "provider_rank" in raw and (
        type(raw["provider_rank"]) is not int or raw["provider_rank"] < 0
    ):
        return None
    return {
        "place_id": raw["place_id"],
        "display_name": raw["display_name"],
        "formatted_address": raw["formatted_address"],
        "business_status": raw.get("business_status"),
        **(
            {"address_components": raw["address_components"]} if "address_components" in raw else {}
        ),
    }


def _verified_google_source(record):
    if record.get("source_kind") == "independent_google_places":
        return True
    provenance = record.get("import_provenance", {})
    if not isinstance(provenance, dict):
        return False
    digest = provenance.get("snapshot_sha256")
    return (
        record.get("source_kind") == "reused_google_places"
        and provenance.get("paired") is True
        and provenance.get("current_sends") == 0
        and isinstance(digest, str)
        and len(digest) == 64
        and all(c in "0123456789abcdef" for c in digest)
    )


def _observation_index(envelope, refs, prepared, *, allow_incomplete=False):
    if not isinstance(envelope, dict) or envelope.get("schema_version") != EVIDENCE_VERSION:
        raise ValueError("Unsupported identity evidence envelope")
    if (envelope.get("batch_id"), envelope.get("batch_revision")) != (
        prepared["batch_id"],
        prepared["revision"],
    ):
        raise ValueError("Identity evidence batch/revision mismatch")
    records = envelope.get("records")
    if not isinstance(records, list):
        raise ValueError("Identity evidence records must be an array")
    allowed = {ref["reference_id"] for ref in refs}
    indexed = {}
    observation_ids = set()
    for record in records:
        if not isinstance(record, dict) or record.get("reference_id") not in allowed:
            raise ValueError("Unlinked identity evidence reference")
        rid = record["reference_id"]
        if rid in indexed:
            raise ValueError("Duplicate identity evidence reference")
        if not text(record.get("observation_id")):
            raise ValueError("Identity observation ID required")
        if record["observation_id"] in observation_ids:
            raise ValueError("Duplicate identity observation ID")
        observation_ids.add(record["observation_id"])
        if not _verified_google_source(record) and not (
            allow_incomplete and record.get("source_kind") is None
        ):
            raise ValueError("Identity observation must declare independent source")
        for key in ("details", "search"):
            observation = record.get(key)
            if observation is None:
                continue
            if not isinstance(observation, dict) or observation.get("status") not in (
                "available",
                "provider_error",
                "unavailable",
                "malformed",
            ):
                raise ValueError("Invalid identity observation state")
            if (
                not allow_incomplete
                and observation["status"] == "available"
                and not text(observation.get("retrieved_at"))
            ):
                raise ValueError("Available identity observation needs retrieval time")
            if (
                key == "search"
                and not allow_incomplete
                and observation["status"] == "available"
                and not text(observation.get("query"))
            ):
                raise ValueError("Available identity search needs query provenance")
            if key == "search" and observation["status"] == "available":
                count = observation.get("actual_result_count")
                if (
                    type(count) is not int
                    or count < 0
                    or not isinstance(observation.get("candidates"), list)
                    or len(observation["candidates"]) > count
                ):
                    raise ValueError("Search result count/candidates are malformed")
        indexed[rid] = record
    return indexed


def _evidence_candidates(record, *, require_provenance=False):
    if require_provenance and record and not _verified_google_source(record):
        return None, []
    details = record.get("details") if record else None
    search = record.get("search") if record else None
    detail_candidate = (
        _candidate(details.get("place"))
        if isinstance(details, dict)
        and details.get("status") == "available"
        and (not require_provenance or text(details.get("retrieved_at")))
        else None
    )
    search_candidates = (
        [_candidate(item) for item in search["candidates"]]
        if isinstance(search, dict)
        and search.get("status") == "available"
        and (
            not require_provenance
            or (text(search.get("retrieved_at")) and text(search.get("query")))
        )
        else []
    )
    return detail_candidate, [item for item in search_candidates if item is not None]


def _high_impact(ref, subject_refs, observation_index):
    if ref["kind"] == "requirement_subject":
        return True
    detail, search = _evidence_candidates(observation_index.get(ref["reference_id"]))
    ids = {item["place_id"] for item in search}
    if detail:
        ids.add(detail["place_id"])
    for subject in subject_refs:
        if subject["group_id"] != ref["group_id"]:
            continue
        if _normal(ref["name"]) is not None and _normal(ref["name"]) == _normal(subject["name"]):
            return True
        s_detail, s_search = _evidence_candidates(observation_index.get(subject["reference_id"]))
        subject_ids = {item["place_id"] for item in s_search}
        if s_detail:
            subject_ids.add(s_detail["place_id"])
        if not subject_ids:
            return True
        if ids & subject_ids or (
            text(ref["claimed_place_id"]) and ref["claimed_place_id"] in subject_ids
        ):
            return True
    return False


def _automatic_candidate(ref, record, high_impact):
    """Strict evidence association; provider rank never enters this rule."""
    if high_impact:
        return None, "high_impact_review"
    if not text(ref["name"]):
        return None, "missing_place_name"
    if ref["claimed_place_id"] is not None and not text(ref["claimed_place_id"]):
        return None, "malformed_claimed_id"
    if record is None:
        return None, "evidence_unavailable"
    details, search = record.get("details"), record.get("search")
    detail_candidate, search_candidates = _evidence_candidates(record)
    try:
        for item in ([detail_candidate] if detail_candidate else []) + search_candidates:
            components(item)
    except ValueError:
        return None, "malformed_address_components"
    claimed = ref["claimed_place_id"]
    if text(claimed):
        if not isinstance(details, dict) or details.get("status") != "available":
            return None, "id_details_unavailable"
        if details.get("requested_place_id") != claimed:
            return None, "id_request_mismatch"
        if detail_candidate is None:
            return None, "malformed_details"
        if detail_candidate["place_id"] != claimed:
            return None, "id_response_mismatch"
        candidate = detail_candidate
        if text(ref["location"]) and not location_matches(ref["location"], candidate):
            return None, "location_association_unverified"
        specific_location = (
            text(ref["location"])
            and numbered_street(ref["location"])
            and _normal(ref["location"]) != _normal(ref["destination"])
            and location_matches(ref["location"], candidate)
        )
        if not specific_location:
            if not isinstance(search, dict) or search.get("status") != "available":
                return None, "branch_ambiguity_unchecked"
            if (
                _normal(search.get("query")) != _normal(ref["name"])
                or search.get("requested_page_size") != 20
                or search["actual_result_count"] != 1
                or len(search_candidates) != 1
                or search_candidates[0]["place_id"] != claimed
            ):
                return None, "competing_candidate"
        if isinstance(search, dict) and search.get("status") == "available":
            if search["actual_result_count"] != len(search_candidates) or any(
                item["place_id"] != claimed for item in search_candidates
            ):
                return None, "competing_candidate"
            if any(
                _normal(item["display_name"]) != _normal(candidate["display_name"])
                or not addresses_agree(item, candidate)
                for item in search_candidates
            ):
                return None, "contradictory_search_evidence"
    else:
        if not isinstance(search, dict) or search.get("status") != "available":
            return None, "name_search_unavailable"
        if _normal(search["query"]) != _normal(ref["name"]):
            return None, "search_query_mismatch"
        if search.get("requested_page_size") != 20:
            return None, "search_scope_unverified"
        count = search["actual_result_count"]
        if count == 0:
            return None, "no_candidate_found"
        if count != 1 or len(search_candidates) != 1:
            return None, "competing_or_malformed_candidates"
        candidate = search_candidates[0]
    if _normal(candidate["display_name"]) != _normal(ref["name"]):
        return None, "name_mismatch_or_alias"
    if not destination_matches(ref["destination"], candidate):
        return None, "destination_unverified"
    if text(ref["location"]) and not location_matches(ref["location"], candidate):
        return None, "location_association_unverified"
    return candidate, "strict_association"


def _review_index(envelope, refs, observations, prepared):
    if envelope is None:
        return {}
    if not isinstance(envelope, dict) or envelope.get("schema_version") != REVIEW_VERSION:
        raise ValueError("Unsupported identity review envelope")
    if (envelope.get("batch_id"), envelope.get("batch_revision")) != (
        prepared["batch_id"],
        prepared["revision"],
    ):
        raise ValueError("Identity review batch/revision mismatch")
    records = envelope.get("records")
    if not isinstance(records, list):
        raise ValueError("Identity review records must be an array")
    allowed = {ref["reference_id"] for ref in refs}
    history = {}
    for record in records:
        if not isinstance(record, dict) or record.get("reference_id") not in allowed:
            raise ValueError("Unlinked identity review reference")
        rid = record["reference_id"]
        evidence_hash = _digest(observations.get(rid))
        if record.get("evidence_hash") != evidence_hash:
            raise ValueError("Stale identity review evidence hash")
        if (
            type(record.get("revision")) is not int
            or record["revision"] < 1
            or record.get("decision") not in ("confirm", "reject", "unresolved")
            or not text(record.get("reviewer_ref"))
            or not text(record.get("reviewed_at"))
            or not text(record.get("rationale"))
        ):
            raise ValueError("Incomplete identity review decision")
        candidate_id = record.get("canonical_place_id")
        if record["decision"] == "confirm":
            if not text(candidate_id):
                raise ValueError("Confirmed identity requires canonical place ID")
            detail, search = _evidence_candidates(observations.get(rid))
            allowed_ids = {item["place_id"] for item in search}
            if detail:
                allowed_ids.add(detail["place_id"])
            if candidate_id not in allowed_ids:
                raise ValueError("Review candidate is absent from independent evidence")
        elif candidate_id is not None:
            raise ValueError("Unresolved/rejected review cannot adopt an identity")
        history.setdefault(rid, []).append(record)
    for items in history.values():
        revisions = [item["revision"] for item in items]
        if len(revisions) != len(set(revisions)):
            raise ValueError("Duplicate identity review revision")
        items.sort(key=lambda item: item["revision"])
        if [item["revision"] for item in items] != list(range(1, len(items) + 1)):
            raise ValueError("Identity review history must be continuous from revision one")
    return history


def _audit_selection(plan, prepared, proposals):
    if not isinstance(plan, dict) or plan.get("schema_version") != AUDIT_VERSION:
        raise ValueError("A versioned identity audit plan is required")
    if (plan.get("batch_id"), plan.get("batch_revision")) != (
        prepared["batch_id"],
        prepared["revision"],
    ):
        raise ValueError("Identity audit batch/revision mismatch")
    if not text(plan.get("seed")) or type(plan.get("sample_count")) is not int:
        raise ValueError("Identity audit seed/count are required")
    if plan["sample_count"] < 1:
        raise ValueError("Identity audit count must be positive")
    ordered = sorted(
        proposals,
        key=lambda ref: (
            _digest([plan["seed"], prepared["batch_id"], prepared["revision"], ref["audit_key"]]),
            ref["audit_key"],
        ),
    )
    return {ref["reference_id"] for ref in ordered[: plan["sample_count"]]}


def _claimed_id_status(ref, observation, adopted_id):
    claimed = ref["claimed_place_id"]
    if claimed is None:
        return "absent"
    if not text(claimed):
        return "unverifiable"
    details = observation.get("details") if observation else None
    detail, _ = _evidence_candidates(observation)
    if (
        not isinstance(details, dict)
        or details.get("status") != "available"
        or details.get("requested_place_id") != claimed
        or detail is None
        or detail["place_id"] != claimed
        or adopted_id is None
    ):
        return "unverifiable"
    return "consistent" if adopted_id == claimed else "conflicting"


def _summaries(references, records, prepared):
    by_id = {record["reference_id"]: record for record in records}
    groups = []
    for group in prepared["inventory"]:
        gid = group["group_id"]
        versions = {}
        for version in VERSIONS:
            if version not in group["runs"]:
                continue
            labels = ["final"]
            if version == "v3":
                labels.extend(
                    label
                    for label, projection in group["runs"][version]["optional"].items()
                    if projection is not None
                )
            versions[version] = {}
            for label in labels:
                selected = [
                    by_id[ref["reference_id"]]
                    for ref in references
                    if ref["group_id"] == gid
                    and ref["version"] == version
                    and ref["projection"] == label
                ]
                states = {
                    state: sum(r["resolution"] == state for r in selected)
                    for state in ("resolved", "unresolved")
                }
                claims = {
                    state: sum(r["claimed_id_association"] == state for r in selected)
                    for state in ("absent", "consistent", "conflicting", "unverifiable")
                }
                unresolved_roles = sum(
                    activity["evaluation_role"] == "unresolved"
                    for activity in (
                        group["runs"][version]["final"]
                        if label == "final"
                        else group["runs"][version]["optional"][label]
                    )["activities"]
                )
                versions[version][label] = {
                    "applicable_visits": len(selected),
                    "resolved_visits": states["resolved"],
                    "unresolved_visits": states["unresolved"],
                    "grounding_fraction": states["resolved"] / len(selected) if selected else None,
                    "claimed_id_association": claims,
                    "unresolved_role_activities": unresolved_roles,
                }
        groups.append({"group_id": gid, "versions": versions})
    return groups


def resolve_identities(intake, evidence, reviews=None, audit_plan=None, *, model_result=None):
    """Dispatch V0 correspondence and deterministic independent V1-V3 checks."""
    from .identity_program import resolve_versioned_identities

    if reviews is not None or audit_plan is not None:
        raise ValueError("Human/audit inputs require explicit legacy identity replay")
    return resolve_versioned_identities(intake, evidence, model_result=model_result)


def resolve_legacy_identities(intake, evidence, reviews=None, audit_plan=None):
    """Resolve offline observations; preserve pending and unknown identity states."""
    return _resolve_identities(intake, evidence, reviews, audit_plan)


def _resolve_identities(intake, evidence, reviews=None, audit_plan=None, assistance=None):
    prepared = _intake_dict(intake)
    refs = identity_references(prepared)
    observations = _observation_index(evidence, refs, prepared)
    history = _review_index(reviews, refs, observations, prepared)
    subjects = [ref for ref in refs if ref["kind"] == "requirement_subject"]
    high_impact = {ref["reference_id"]: _high_impact(ref, subjects, observations) for ref in refs}
    proposals = {}
    reasons = {}
    for ref in refs:
        rid = ref["reference_id"]
        proposals[rid], reasons[rid] = _automatic_candidate(
            ref, observations.get(rid), high_impact[rid]
        )
    selected_audit = _audit_selection(
        audit_plan,
        prepared,
        [ref for ref in refs if proposals[ref["reference_id"]] is not None],
    )
    native_reasons = dict(reasons)
    if assistance is not None:
        for ref in refs:
            rid = ref["reference_id"]
            decision = assistance.decisions.get(rid)
            if decision is None or high_impact[rid] or proposals[rid] is not None:
                continue
            if decision["eligibility"] == "eligible":
                proposals[rid] = {"place_id": decision["candidate_id"]}
                reasons[rid] = "model_supported_association"
            else:
                reasons[rid] = decision["eligibility"]
        scoped = [
            ref
            for ref in refs
            if ref["reference_id"] in assistance.reference_ids
            and proposals[ref["reference_id"]] is not None
        ]
        if assistance.audit_frozen:
            selected_audit = (selected_audit - assistance.reference_ids) | _audit_selection(
                audit_plan, prepared, scoped
            )
    records, queue = [], []
    request_contexts = {group["group_id"]: group["input"] for group in prepared["inventory"]}
    for ref in refs:
        rid = ref["reference_id"]
        observation = observations.get(rid)
        latest = history.get(rid, [])[-1] if history.get(rid) else None
        proposed = proposals[rid]
        canonical = None
        route = None
        reason = reasons[rid]
        if latest is not None:
            if latest["decision"] == "confirm":
                canonical = latest["canonical_place_id"]
                route = "human_adjudication"
                reason = "reviewed_confirmation"
            else:
                reason = "reviewed_" + latest["decision"]
        elif (
            assistance is not None
            and rid in assistance.reference_ids
            and reason == "model_supported_association"
            and not assistance.audit_frozen
        ):
            reason = "audit_freeze_unverified"
        elif proposed is not None and rid not in selected_audit:
            canonical = proposed["place_id"]
            route = (
                "model_assisted"
                if reason == "model_supported_association"
                else "independent_id_details"
                if text(ref["claimed_place_id"])
                else "name_search"
            )
        elif rid in selected_audit:
            reason = "audit_pending"
        status = "resolved" if canonical is not None else "unresolved"
        record = {
            "reference_id": rid,
            "kind": ref["kind"],
            "source": ref["source"],
            "group_id": ref["group_id"],
            "version": ref["version"],
            "projection": ref["projection"],
            "resolution": status,
            "reason": reason,
            "canonical_place_id": canonical,
            "decision_route": route,
            "claimed_id_association": _claimed_id_status(ref, observation, canonical),
            "high_impact": high_impact[rid],
            "audit_selected": rid in selected_audit,
            "audit_key": ref["audit_key"],
            "evidence_hash": _digest(observation),
            "observation_id": observation.get("observation_id") if observation else None,
            "review_history": history.get(rid, []),
            "candidate_ids": sorted(
                {item["place_id"] for item in _evidence_candidates(observation)[1]}
                | (
                    {_evidence_candidates(observation)[0]["place_id"]}
                    if _evidence_candidates(observation)[0]
                    else set()
                )
            ),
        }
        if assistance is not None and rid in assistance.reference_ids:
            record["native_reason"] = native_reasons[rid]
            record["model_proposal"] = thaw(assistance.decisions[rid])
        competing = competing_title(ref["original_title"], ref["name"])
        if competing:
            record["competing_claim"] = claim_evidence(
                ref["original_title"], competing, ref["source"]
            )
        records.append(record)
        if latest is None and status == "unresolved":
            detail, search = _evidence_candidates(observation)
            queue.append(
                {
                    "reference_id": rid,
                    "name": ref["name"],
                    "original_title": ref["original_title"],
                    "location": ref["location"],
                    "destination": ref["destination"],
                    "claimed_place_id": ref["claimed_place_id"],
                    "original_request": request_contexts[ref["group_id"]],
                    "reason": reason,
                    **({"competing_claim": record["competing_claim"]} if competing else {}),
                    "candidates": ([detail] if detail else []) + search,
                    "observation_id": observation.get("observation_id") if observation else None,
                    "observation_context": {
                        key: {
                            field: value
                            for field, value in observation[key].items()
                            if field != "place" and field != "candidates"
                        }
                        for key in ("details", "search")
                        if observation and isinstance(observation.get(key), dict)
                    },
                    "evidence_hash": record["evidence_hash"],
                }
            )
    extra = {}
    if assistance is not None:
        from .identity_adoption import POLICY_VERSION, adoption_summary

        extra = {
            "association_policy_version": POLICY_VERSION,
            "model_assistance_provenance": thaw(assistance.provenance),
            "model_assistance_replay": {"bundle": thaw(assistance.replay), "reviews": reviews},
            **adoption_summary(prepared, records, assistance),
        }
    return IdentityResult(
        "needs_adjudication" if queue else "complete",
        freeze(
            {
                "schema_version": IDENTITY_VERSION,
                "subject_scope_version": SUBJECT_SCOPE_VERSION,
                "association_policy_version": ASSOCIATION_POLICY_VERSION,
                "reference_set_digest": _digest(refs),
                "batch_id": prepared["batch_id"],
                "batch_revision": prepared["revision"],
                "source_hashes": prepared["source_hashes"],
                "evidence_hash": _digest(evidence),
                "review_hash": _digest(reviews) if reviews is not None else None,
                "audit_plan_hash": _digest(audit_plan),
                "audit_selected_reference_ids": sorted(selected_audit),
                "records": records,
                "review_queue": queue,
                "groups": _summaries(refs, records, prepared),
                **extra,
            }
        ),
    )
