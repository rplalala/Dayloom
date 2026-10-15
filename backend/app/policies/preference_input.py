"""Application-owned input decisions; no NLP, travel facts, or external operations."""

from backend.app.schemas.interpreted_requirements import ClarificationRequired
from backend.app.schemas.requirement_boundary import RequirementBoundaryError

MESSAGES = {
    "destination_scope_conflict": (
        "This preference requests a physical visit outside the stated trip scope.",
        "Update the destination or revise the requested visit.",
    ),
    "structured_request_conflict": (
        "This preference conflicts with a structured trip field.",
        "Update that field or revise the conflicting preference.",
    ),
    "internal_requirement_contradiction": (
        "These explicit requirements conflict for the same subject and scope.",
        "Clarify which requirement should apply, or distinguish their conditions.",
    ),
    "unsupported_request_scope": (
        "The requested scope needs clarification for this planner.",
        "Clarify the intended trip scope or submit separate requests.",
    ),
    "semantic_ambiguity": (
        "An ambiguity affects the trip scope or interpretation of a hard requirement.",
        "Clarify the subject, scope, or condition of this requirement.",
    ),
    "non_travel_control_instruction": (
        "This text asks to change the system task rather than describe a trip.",
        "Replace it with travel preferences or itinerary presentation requirements.",
    ),
    "safety_self_harm": (
        "Your safety matters. Travel planning has been paused.",
        "If you may act on thoughts of self-harm, contact local emergency services or someone "
        "you trust who can stay with you. You do not have to face this alone.",
    ),
    "safety_serious_harm": (
        "Travel planning has been paused because this request indicates a serious safety risk.",
        "If anyone is in immediate danger, contact local emergency services and seek support.",
    ),
}
REWRITE_TYPES = {
    "destination_scope_conflict",
    "structured_request_conflict",
    "internal_requirement_contradiction",
    "non_travel_control_instruction",
}
SAFETY_TYPES = {"safety_self_harm", "safety_serious_harm"}


class PreferenceInputBlocked(ClarificationRequired):
    """Reuse non-success plumbing while preserving a dedicated safety disposition."""

    def __init__(self, input_disposition, safety_disposition, issues):
        super().__init__("preference_input_blocked")
        self.input_disposition = input_disposition
        self.safety_disposition = safety_disposition
        self.issues = issues

    def as_dict(self):
        safety = self.safety_disposition == "SAFETY_BLOCK"
        return {
            "status": "safety_blocked" if safety else "clarification_required",
            "category": "SAFETY_BLOCK" if safety else "USER_INPUT_ISSUE",
            "code": self.code,
            "assessment_version": "preference_input_2",
            "input_disposition": self.input_disposition,
            "safety_disposition": self.safety_disposition,
            "issues": self.issues,
        }


def exact_sources(refs, text):
    # Reuse the occurrence mapper, but disallow its historical casefold compatibility.
    from backend.app.policies.interpreted_requirements import locate_source

    result = []
    for ref in refs:
        if ref.quote not in text:
            raise RequirementBoundaryError("invalid_input_issue_quote")
        source = locate_source(text, ref)
        if source.match_mode != "exact":
            raise RequirementBoundaryError("invalid_input_issue_quote")
        result.append(source.model_dump())
    return result


def check_preference_input(draft, request):
    """Validate every issue before choosing safety > rewrite > clarification > continue."""
    assessment = draft.preference_input_assessment
    if assessment is None:
        raise RequirementBoundaryError("missing_preference_input_assessment")
    text = request.additional_preferences
    # A blocked assessment must not hide fabricated provenance elsewhere in the same DTO.
    from backend.app.policies.interpreted_requirements import locate_source

    for field, group in (
        ("semantic_requirements", draft.semantic_requirements),
        ("named_places", draft.named_places),
        ("subjects", draft.subjects),
        ("time_protections", draft.time_protections or ()),
        ("visit_requirements", draft.visit_requirements or ()),
    ):
        for i, item in enumerate(group):
            for j, source in enumerate(item.source_refs):
                try:
                    locate_source(text, source)
                except RequirementBoundaryError as exc:
                    raise RequirementBoundaryError(
                        exc.code, errors=({"loc": (field, i, "source_refs", j), "type": exc.code},)
                    ) from exc
    conflicts = [exact_sources(c.source_refs, text) for c in draft.operational_conflicts]
    rows = []
    represented = set()
    fields = request.model_dump(mode="json")
    for issue in assessment.issues:
        refs = exact_sources(issue.source_refs, text)
        index = issue.operational_conflict_index
        if index is not None:
            if (
                index >= len(conflicts)
                or draft.operational_conflicts[index].field != issue.related_field
            ):
                raise RequirementBoundaryError("invalid_input_issue_conflict_link")
            # A field match alone must not link an unrelated sentence/occurrence.
            if refs and any(
                not any(r["start"] < b["end"] and b["start"] < r["end"] for b in conflicts[index])
                for r in refs
            ):
                raise RequirementBoundaryError("unrelated_input_issue_conflict_sources")
            represented.add(index)
        if (
            issue.issue_type == "internal_requirement_contradiction"
            and len({(r["start"], r["end"]) for r in refs}) < 2
        ):
            raise RequirementBoundaryError("duplicate_contradiction_sources")
        value = fields
        if issue.related_field:
            for key in issue.related_field.split("."):
                value = value[key]
        reason, action = MESSAGES[issue.issue_type]
        rows.append(
            {
                "issue_type": issue.issue_type,
                "source_refs": refs,
                "quote_status": issue.quote_status,
                "related_field": issue.related_field,
                "current_value": value if issue.related_field else None,
                "reason": reason,
                "action": action,
                "scope": issue.scope,
                "basis_refs": conflicts[index] if index is not None else [],
            }
        )
    types = {r["issue_type"] for r in rows}
    expected_input = (
        "REWRITE_REQUIRED"
        if types & REWRITE_TYPES
        else "CLARIFICATION_REQUIRED"
        if types - SAFETY_TYPES
        else "VALID"
    )
    expected_safety = "SAFETY_BLOCK" if types & SAFETY_TYPES else "CLEAR"
    if (assessment.input_disposition, assessment.safety_disposition) != (
        expected_input,
        expected_safety,
    ):
        raise RequirementBoundaryError("inconsistent_preference_input_assessment")
    # Legacy structured conflicts keep their established code; do not duplicate mapped issues.
    for index, conflict in enumerate(draft.operational_conflicts):
        if index not in represented:
            reason, action = MESSAGES["structured_request_conflict"]
            value = fields
            for key in conflict.field.split("."):
                value = value[key]
            rows.append(
                {
                    "issue_type": "structured_request_conflict",
                    "source_refs": conflicts[index],
                    "quote_status": "located",
                    "related_field": conflict.field,
                    "current_value": value,
                    "reason": reason,
                    "action": action,
                    "scope": "structured_request",
                    "basis_refs": [],
                }
            )
            expected_input = "REWRITE_REQUIRED"
    if rows:
        raise PreferenceInputBlocked(expected_input, expected_safety, tuple(rows))
    # Historical free-text extraction issues retain the existing clarification boundary.
    # New responses should use typed semantic_ambiguity issues for sourced user feedback.
