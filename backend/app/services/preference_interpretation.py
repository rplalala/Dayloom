"""Shared input and preference boundary; never acquires external travel evidence."""

import json
from datetime import date
from pathlib import Path

from backend.app.observability.progress import observed
from backend.app.policies.interpreted_requirements import (
    assess_requirements,
    canonicalize_requirements,
    require_resolved_hard,
)
from backend.app.policies.trip_dates import create_trip_date_window, validate_requested_trip_dates
from backend.app.schemas.interpreted_requirements import (
    InterpretationDraft,
    PreferenceInputAssessment,
)
from backend.app.schemas.request import PlanningRequest
from backend.app.services.preference_prompts import PREFERENCE_INTERPRETATION_SYSTEM_PROMPT


def validate_planning_request(request, reference_date: date) -> PlanningRequest:
    """Revalidate even model_copy inputs before model or provider invocation."""
    value = request.model_dump() if isinstance(request, PlanningRequest) else request
    request = PlanningRequest.model_validate(value)
    validate_requested_trip_dates(
        request.start_date, request.end_date, create_trip_date_window(reference_date)
    )
    return request


def read_planning_request(path: str) -> PlanningRequest:
    return PlanningRequest.model_validate_json(Path(path).read_text(encoding="utf-8"))


def preference_prompt(request: PlanningRequest, reference_date: date) -> str:
    return json.dumps(
        {
            "reference_date": reference_date.isoformat(),
            "read_only_trip_facts": request.trip_requirements().model_dump(mode="json"),
            "additional_preferences": request.additional_preferences,
        },
        ensure_ascii=False,
    )


def empty_preference_draft() -> InterpretationDraft:
    return InterpretationDraft(
        preference_input_assessment=PreferenceInputAssessment(
            input_disposition="VALID", safety_disposition="CLEAR", issues=()
        ),
        visit_requirements=(),
        time_protections=(),
        daily_pace=({"date": None, "profile": "ordinary", "exact_count": None, "source_refs": ()},),
        named_places=(),
        requested_place_information=(),
        transport_preference=None,
        semantic_requirements=(),
        subjects=(),
        discovery_intents=(),
        experience_evidence_requests=(),
        extraction_issues=(),
        overflow=False,
    )


@observed("requirements")
async def interpret_preferences(
    request, reference_date, client, tracer=None, *, category_visits=False
):
    request = validate_planning_request(request, reference_date)
    if request.additional_preferences:
        draft = await client.generate_structured(
            system_prompt=PREFERENCE_INTERPRETATION_SYSTEM_PROMPT,
            user_prompt=preference_prompt(request, reference_date),
            response_schema=InterpretationDraft,
        )
    else:
        draft = empty_preference_draft()
    capture = (
        getattr(client, "capture_requirement_outcome", None)
        if request.additional_preferences
        else None
    )
    contract = None
    try:
        from pydantic import ValidationError

        from backend.app.schemas.requirement_boundary import RequirementBoundaryError

        try:
            checked = InterpretationDraft.model_validate(draft.model_dump())
        except (ValidationError, AttributeError) as exc:
            raise RequirementBoundaryError("invalid_interpretation_draft", stage="draft") from exc
        if checked.overflow:
            raise RequirementBoundaryError("extraction_overflow")
        if checked.preference_input_assessment is None:
            raise RequirementBoundaryError("missing_preference_input_assessment")
        contract = canonicalize_requirements(draft, request)
        require_resolved_hard(assess_requirements(contract, category_visits=category_visits))
    except Exception as exc:
        from backend.app.policies.requirement_feedback import attach_requirement_feedback
        from backend.app.schemas.interpreted_requirements import ClarificationRequired

        if isinstance(exc, ClarificationRequired):
            attach_requirement_feedback(exc, contract)
        if tracer:
            from backend.app.policies.preference_input import PreferenceInputBlocked

            if isinstance(exc, PreferenceInputBlocked):
                tracer.event(
                    "preference_input_blocked",
                    {
                        "assessment_version": "preference_input_2",
                        "input_disposition": exc.input_disposition,
                        "safety_disposition": exc.safety_disposition,
                        "issue_types": [i["issue_type"] for i in exc.issues],
                        "quote_statuses": [i["quote_status"] for i in exc.issues],
                        "structured_input_hash": request.structured_hash(),
                    },
                )
        if capture:
            capture(draft, exc)
        raise
    if capture:
        capture(draft)
    if tracer:
        tracer.event(
            "interpreted_requirements_validated",
            {
                "contract_version": contract.contract_version,
                "interpretation_origin": contract.interpretation_origin,
                "semantic_count": len(contract.semantic_requirements),
                "named_count": len(contract.named_places),
                "request_hash": contract.request_sha256,
                "structured_input_hash": contract.structured_input_sha256,
                "input_assessment_version": "preference_input_2",
                "input_disposition": "VALID",
                "safety_disposition": "CLEAR",
            },
        )
        tracer.set_requirements(contract.requirements)
    return contract
