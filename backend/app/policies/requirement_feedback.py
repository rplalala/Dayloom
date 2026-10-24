"""Allowlisted requirement failure explanations shared by durable and immediate Product APIs."""

MESSAGES = {
    "unsupported_hard_requirements": (
        "This planner cannot verify this non-negotiable requirement with its current capabilities.",
        "Your requirement has been kept; it has not been treated as optional.",
    ),
    "unsupported_transport_modes": (
        "The required transport modes are not supported by this planner.",
        "Choose supported transport only if it meets your needs.",
    ),
    "structured_input_conflict": (
        "A preference conflicts with a trip field.",
        "Choose which trip detail should apply.",
    ),
    "extraction_ambiguity": (
        "The planner could not resolve the meaning of a requirement.",
        "Clarify the intended experience, subject or condition.",
    ),
    "unresolved_subject_attribution": (
        "The planner could not determine who a requirement applies to.",
        "Specify the traveler or group this requirement applies to.",
    ),
    "unresolved_named_identity": (
        "The requested place could not be identified unambiguously.",
        "Provide the place's full name or location.",
    ),
    "required_excluded_conflict": (
        "The same place is both required and excluded.",
        "Choose whether to include this place.",
    ),
    "daily_visit_constraint_conflict": (
        "Required visit totals conflict on the same date.",
        "Choose the intended visit total.",
    ),
    "daily_visit_protected_day_conflict": (
        "A required visit falls on a day reserved entirely for another commitment.",
        "Resolve the conflicting date commitments.",
    ),
    "no_eligible_candidates": (
        "The search did not find eligible places for this request.",
        "Your requirements have been kept. A later search may find more options.",
    ),
    "no_eligible_details": (
        "The search found no places with sufficient usable details for planning.",
        "Your requirements have been kept. You can retry when more evidence is available.",
    ),
    "no_qualified_candidates": (
        "Available place information did not establish any eligible visits.",
        "Your requirements have been kept. More evidence is needed before planning can continue.",
    ),
    "required_place_details_unusable": (
        "Usable planning details were unavailable for a required place.",
        "Your required visit has been kept; missing evidence cannot confirm it is feasible.",
    ),
    "required_place_ineligible": (
        "A required place did not meet the available planning checks.",
        "Your requirement has been kept; the planner cannot confirm a suitable visit.",
    ),
    "required_capacity_conflict": (
        "The planner could not fit all required places within its planning capacity.",
        "Your requirements have been kept. The planner has not completed this request.",
    ),
}

ACQUISITION_FAILURES = frozenset(
    {
        "no_eligible_candidates",
        "no_eligible_details",
        "no_qualified_candidates",
        "required_place_details_unusable",
        "required_place_ineligible",
        "required_capacity_conflict",
    }
)


def feedback_rows(code, *, contract=None, requirement_ids=(), conflicts=()):
    reason, action = MESSAGES.get(
        code,
        (
            "The planner could not resolve a requirement for this request.",
            "Your original requirements have been kept.",
        ),
    )
    sources = []
    if contract is not None:
        sources = [
            [s.model_dump() for s in r.source_refs]
            for r in (*contract.semantic_requirements, *contract.named_places)
            if r.requirement_id in requirement_ids
        ]
    if not sources:
        sources = [c["source_refs"] for c in conflicts if c.get("source_refs")]
    return tuple(
        {
            "issue_type": code if code in MESSAGES else "requirement_unresolved",
            "reason": reason,
            "action": action,
            "source_refs": refs,
        }
        for refs in sources or [[]]
    )


def attach_requirement_feedback(error, contract=None):
    """Only source-validated application requirements enter the public explanation."""
    if error.code in MESSAGES:
        error.details = feedback_rows(
            error.code,
            contract=contract,
            requirement_ids=error.requirement_ids,
            conflicts=error.conflicts,
        )
