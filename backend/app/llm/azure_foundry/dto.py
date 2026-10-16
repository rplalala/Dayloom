"""Strict transport DTOs for Microsoft Foundry structured output."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.interpreted_requirements import (
    InputDisposition,
    InputIssueType,
    RequestField,
)


class FoundryTransportDTO(BaseModel):
    """Base contract for values returned directly by Microsoft Foundry."""

    model_config = ConfigDict(extra="forbid", strict=True)


class FoundryMoneyDTO(FoundryTransportDTO):
    """Transport representation of a monetary amount."""

    amount: str
    currency: str


class FoundryRequestedPlaceInformationDTO(FoundryTransportDTO):
    target_surface: str
    target_source_text: str
    source_text: str
    requested_facet: (
        Literal[
            "general_admission_policy",
            "admission_fee",
            "ticket_requirement",
            "advance_ticket_purchase_requirement",
            "reservation_requirement",
        ]
        | None
    )
    operational_need: (
        Literal[
            "current_operational_status",
            "date_specific_operational_exception",
            "special_date_hours",
        ]
        | None
    )
    subject_scope: Literal["whole_venue", "sub_area", "exhibition", "ticket_product"]
    scope_text: str | None
    temporal_scope: Literal["GENERAL", "CURRENT", "TRIP_DATES", "EXPLICIT_DATE"]
    date_source_text: str | None
    requested_start_date: str | None
    requested_end_date: str | None


class FoundryTransportPreferenceIntentDTO(FoundryTransportDTO):
    mode: Literal["DRIVE", "WALK", "BICYCLE", "TRANSIT"]
    source_text: str


class FoundrySourceQuoteDTO(FoundryTransportDTO):
    quote: str
    occurrence: int


class FoundrySubjectDTO(FoundryTransportDTO):
    local_key: str
    label: str
    source_refs: list[FoundrySourceQuoteDTO]


class FoundryPartyTargetDTO(FoundryTransportDTO):
    kind: Literal["party"]


class FoundrySpecifiedTargetDTO(FoundryTransportDTO):
    kind: Literal["specified"]
    first_ref: str
    additional_refs: list[str]


class FoundryUnresolvedTargetDTO(FoundryTransportDTO):
    kind: Literal["unresolved"]
    reason: str


class FoundryExperienceGoalDTO(FoundryTransportDTO):
    frequency: Literal["one_off", "continuing", "exact", "minimum"]
    count: int | None
    target: Literal["category", "named_place"]
    distinct_dates: bool
    explicit_primary_exception: bool
    trip_scope: Literal["ordinary", "exclusive"]


class FoundrySemanticDTO(FoundryTransportDTO):
    trip_focus_source: FoundrySourceQuoteDTO | None
    experience_goal: FoundryExperienceGoalDTO | None
    local_key: str
    normalized_text: str
    kind: Literal["preference", "constraint", "goal"]
    polarity: Literal["favor", "avoid"]
    strength: Literal["low", "medium", "high", "hard"]
    scope: Literal[
        "individual_poi", "selected_poi_set", "whole_trip", "itinerary_style", "transport"
    ]
    subject_target: FoundryPartyTargetDTO | FoundrySpecifiedTargetDTO | FoundryUnresolvedTargetDTO
    source_refs: list[FoundrySourceQuoteDTO]


class FoundryNamedRequirementDTO(FoundryTransportDTO):
    place_text: str
    inclusion: Literal["REQUIRED", "OPTIONAL", "EXCLUDED"]
    source_refs: list[FoundrySourceQuoteDTO]


class FoundryDiscoveryDTO(FoundryTransportDTO):
    requirement_refs: list[str]
    purpose: Literal["activity_or_category", "semantic_discovery"]
    query_text: str


class FoundryEvidenceRequestDTO(FoundryTransportDTO):
    requirement_ref: str
    dimension: Literal[
        "crowding", "walking_intensity", "accessibility", "family_friendliness", "visit_duration"
    ]
    preferred_values: list[
        Literal[
            "LOW",
            "MODERATE",
            "HIGH",
            "LIGHT",
            "ACCESSIBLE",
            "MIXED",
            "LIMITED",
            "FAMILY_FRIENDLY",
            "NOT_FAMILY_FRIENDLY",
            "SHORT",
            "MEDIUM",
            "LONG",
        ]
    ]
    avoided_values: list[
        Literal[
            "LOW",
            "MODERATE",
            "HIGH",
            "LIGHT",
            "ACCESSIBLE",
            "MIXED",
            "LIMITED",
            "FAMILY_FRIENDLY",
            "NOT_FAMILY_FRIENDLY",
            "SHORT",
            "MEDIUM",
            "LONG",
        ]
    ]


class FoundryOperationalConflictDTO(FoundryTransportDTO):
    field: Literal[
        "destination",
        "start_date",
        "end_date",
        "traveler_count",
        "budget.amount",
        "budget.currency",
    ]
    source_refs: list[FoundrySourceQuoteDTO]


class FoundryVisitRequirementDTO(FoundryTransportDTO):
    exact_visits: int | None
    distinct_dates: bool
    access_mode: Literal["venue_entry", "exterior"] | None
    place_text: str
    minimum_visits: int
    dates: list[str]
    status: Literal["executable", "unresolved"]
    reason: str | None
    source_refs: list[FoundrySourceQuoteDTO]


class FoundryTimeProtectionDTO(FoundryTransportDTO):
    full_day: bool | None
    dates: list[str]
    start_time: str | None
    end_time: str | None
    status: Literal["fixed", "unresolved"]
    reason: str | None
    source_refs: list[FoundrySourceQuoteDTO]


class FoundryPreferenceInputIssueDTO(FoundryTransportDTO):
    """Common descriptions; concrete wire branches own conditional link fields."""

    issue_type: InputIssueType
    source_refs: list[FoundrySourceQuoteDTO] = Field(
        description=(
            "Exact original quote/zero-based occurrence pairs. Located issues require sources; "
            "internal_requirement_contradiction requires both distinct conflicting sources. "
            "Unavailable structured issues must use an empty list and a valid conflict link."
        )
    )
    quote_status: Literal["located", "unavailable"]
    related_field: RequestField | None = Field(
        description=(
            "Read-only request field path, never its value. destination_scope_conflict requires "
            "destination; structured_request_conflict requires its linked conflict field. "
            "Use null when no structured field is implicated, including ordinary safety issues."
        )
    )
    operational_conflict_index: int | None = Field(
        description=(
            "Only structured_request_conflict may populate this zero-based operational_conflicts "
            "index. Every other issue type MUST return null. Linked field and exact source "
            "occurrence must correspond to the same conflict; never invent an index."
        )
    )
    scope: str = Field(description="Affected subject and conditions, at most 320 characters.")


class FoundryStructuredInputIssueDTO(FoundryPreferenceInputIssueDTO):
    issue_type: Literal["structured_request_conflict"]
    related_field: RequestField = Field(description="Field of the linked operational conflict.")


class FoundryOtherInputIssueDTO(FoundryPreferenceInputIssueDTO):
    issue_type: Literal[
        "destination_scope_conflict",
        "internal_requirement_contradiction",
        "unsupported_request_scope",
        "semantic_ambiguity",
        "non_travel_control_instruction",
        "safety_self_harm",
        "safety_serious_harm",
    ]
    operational_conflict_index: None = Field(
        description="MUST be null: only structured_request_conflict owns an operational link."
    )
    quote_status: Literal["located"] = Field(
        description="Non-structured issues require exact located source quotes."
    )


class FoundryPreferenceInputAssessmentDTO(FoundryTransportDTO):
    input_disposition: InputDisposition
    safety_disposition: Literal["CLEAR", "SAFETY_BLOCK"]
    issues: list[FoundryStructuredInputIssueDTO | FoundryOtherInputIssueDTO]


class FoundryDailyPaceDTO(FoundryTransportDTO):
    date: str | None
    profile: Literal["ordinary", "relaxed", "rich", "unresolved"]
    exact_count: int | None
    source_refs: list[FoundrySourceQuoteDTO]


class FoundryTransportConstraintDTO(FoundryTransportDTO):
    allowed_modes: list[Literal["WALK", "TRANSIT", "DRIVE", "BICYCLE"]]
    requirement_refs: list[str]
    source_refs: list[FoundrySourceQuoteDTO]


class FoundryInterpretationDTO(FoundryTransportDTO):
    daily_pace: list[FoundryDailyPaceDTO] | None
    preference_input_assessment: FoundryPreferenceInputAssessmentDTO
    visit_requirements: list[FoundryVisitRequirementDTO] | None
    time_protections: list[FoundryTimeProtectionDTO] | None
    operational_conflicts: list[FoundryOperationalConflictDTO]
    named_places: list[FoundryNamedRequirementDTO]
    requested_place_information: list[FoundryRequestedPlaceInformationDTO]
    transport_preference: FoundryTransportPreferenceIntentDTO | None
    semantic_requirements: list[FoundrySemanticDTO]
    subjects: list[FoundrySubjectDTO]
    discovery_intents: list[FoundryDiscoveryDTO]
    experience_evidence_requests: list[FoundryEvidenceRequestDTO]
    extraction_issues: list[str]
    overflow: bool


class FoundryCurrentInterpretationDTO(FoundryInterpretationDTO):
    transport_constraint: FoundryTransportConstraintDTO | None


class FoundryDailyVisitConstraintDTO(FoundryTransportDTO):
    date: str
    mode: Literal["exact", "minimum"]
    count: int
    strength: Literal["hard", "soft"]
    requirement_refs: list[str]
    source_refs: list[FoundrySourceQuoteDTO]


class FoundryDatedInterpretationDTO(FoundryCurrentInterpretationDTO):
    daily_visit_constraints: list[FoundryDailyVisitConstraintDTO]


class FoundryDateTimeDTO(FoundryTransportDTO):
    """Transport datetime split into explicit, independently required components."""

    date: str
    time: str
    utc_offset: str


class FoundryActivityDTO(FoundryTransportDTO):
    """Transport representation of one itinerary activity."""

    activity_kind: Literal["main_poi", "generic_activity", "transport", "free_time"]
    time_use: Literal["scheduled", "free_window"]
    activity_id: str
    title: str
    source_place_id: str | None
    place_name: str | None
    location: str | None
    start_time: FoundryDateTimeDTO
    end_time: FoundryDateTimeDTO
    estimated_cost: FoundryMoneyDTO | None
    notes: str | None


class FoundryTransportDeclarationDTO(FoundryTransportDTO):
    """V0 model declaration; nullable mode means unknown."""

    mode: Literal["WALK", "TRANSIT", "DRIVE"] | None
    from_activity_id: str
    to_activity_id: str


class FoundryV0ActivityDTO(FoundryActivityDTO):
    """V0 alone authors transport activities and their structured declarations."""

    transport: FoundryTransportDeclarationDTO | None


class FoundryItineraryDayDTO(FoundryTransportDTO):
    """Transport representation of one itinerary day."""

    date: str
    activities: list[FoundryV0ActivityDTO]


class FoundryReferenceRecommendationDTO(FoundryTransportDTO):
    """Model-authored reference content; provenance is assigned by the application."""

    place_name: str
    source_place_id: str | None
    reason: str
    associated_day: str | None
    area: str | None
    uncertainty: str | None


class FoundryPrimaryActivityDTO(FoundryActivityDTO):
    """Tool-backed generation leaves transport records to the application."""

    activity_kind: Literal["main_poi", "generic_activity", "free_time"]


class FoundryPrimaryItineraryDayDTO(FoundryTransportDTO):
    date: str
    activities: list[FoundryPrimaryActivityDTO]


class FoundryPrimaryItineraryDTO(FoundryTransportDTO):
    """V1 model output contains only the primary itinerary."""

    output_version: Literal["itinerary_3"]
    destination: str
    start_date: str
    end_date: str
    days: list[FoundryPrimaryItineraryDayDTO]


class FoundryItineraryDTO(FoundryPrimaryItineraryDTO):
    """V0 model output includes subordinate model-knowledge references."""

    days: list[FoundryItineraryDayDTO]
    reference_recommendations: list[FoundryReferenceRecommendationDTO]


class FoundryExperienceSignalDTO(FoundryTransportDTO):
    dimension: Literal[
        "crowding", "walking_intensity", "accessibility", "family_friendliness", "visit_duration"
    ]
    value: Literal[
        "LOW",
        "MODERATE",
        "HIGH",
        "LIGHT",
        "ACCESSIBLE",
        "MIXED",
        "LIMITED",
        "FAMILY_FRIENDLY",
        "NOT_FAMILY_FRIENDLY",
        "SHORT",
        "MEDIUM",
        "LONG",
    ]
    review_refs: list[str]


class FoundryExperienceProfileDTO(FoundryTransportDTO):
    place_id: str
    summary: str | None
    summary_review_refs: list[str]
    signals: list[FoundryExperienceSignalDTO]
    review_count_used: int
