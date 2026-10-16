"""Versioned open requirements; model drafts cannot author enforcement results."""

from datetime import date, time
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PrivateAttr,
    StringConstraints,
    model_serializer,
    model_validator,
)

from backend.app.evidence.experience_models import (
    ALLOWED_VALUES,
    ExperienceDimension,
    ExperienceValue,
)
from backend.app.schemas.request import TravelRequirements
from backend.app.schemas.trip_intent import (
    RequestedPlaceInformation,
    TransportPreferenceIntent,
    TravelMode,
)

CONTRACT_VERSION = "interpreted_requirements_6"
DRAFT_HANDLE_LIMIT = 256
TemporaryHandle = Annotated[str, StringConstraints(min_length=1, max_length=DRAFT_HANDLE_LIMIT)]
Strength = Literal["low", "medium", "high", "hard"]
Scope = Literal["individual_poi", "selected_poi_set", "whole_trip", "itinerary_style", "transport"]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SourceQuote(ContractModel):
    quote: str = Field(min_length=1, max_length=320)
    occurrence: int = Field(ge=0)


class SourceReference(SourceQuote):
    start: int
    end: int
    match_mode: Literal["exact", "casefold_equivalent"] = "exact"

    @model_validator(mode="after")
    def valid_offsets(self):
        if self.start < 0 or self.end <= self.start or self.end - self.start != len(self.quote):
            raise ValueError("Invalid source offsets")
        return self


class Subject(ContractModel):
    local_key: TemporaryHandle
    label: str = Field(min_length=1, max_length=100)
    source_refs: tuple[SourceQuote, ...] = Field(min_length=1, max_length=3)


class CanonicalSubject(ContractModel):
    subject_id: str = Field(min_length=1, max_length=40)
    label: str = Field(min_length=1, max_length=100)
    source_refs: tuple[SourceReference, ...] = Field(min_length=1, max_length=3)


class PartyTarget(ContractModel):
    kind: Literal["party"]


class SpecifiedTarget(ContractModel):
    kind: Literal["specified"]
    first_ref: TemporaryHandle
    additional_refs: tuple[TemporaryHandle, ...] = Field(max_length=7)


class UnresolvedTarget(ContractModel):
    kind: Literal["unresolved"]
    reason: str = Field(min_length=1, max_length=320)


SubjectTarget = PartyTarget | SpecifiedTarget | UnresolvedTarget


class ExperienceGoal(ContractModel):
    """Sourced interpretation, not a claim about candidate suitability."""

    frequency: Literal["one_off", "continuing", "exact", "minimum"]
    count: int | None = Field(default=None, ge=1, le=10)
    target: Literal["category", "named_place"]
    distinct_dates: bool
    explicit_primary_exception: bool
    trip_scope: Literal["ordinary", "exclusive"]

    @model_validator(mode="after")
    def counts(self):
        if (self.frequency in {"exact", "minimum"}) != (self.count is not None):
            raise ValueError("Only exact/minimum experience goals carry a count")
        if self.explicit_primary_exception and self.frequency == "continuing":
            raise ValueError("A primary exception needs a bounded experience request")
        return self


class SemanticDraft(ContractModel):
    trip_focus_source: SourceQuote | None = None
    experience_goal: ExperienceGoal | None = None
    local_key: TemporaryHandle
    normalized_text: str = Field(min_length=1, max_length=320)
    kind: Literal["preference", "constraint", "goal"]
    polarity: Literal["favor", "avoid"]
    strength: Strength
    scope: Scope
    subject_target: SubjectTarget
    source_refs: tuple[SourceQuote, ...] = Field(min_length=1, max_length=3)


class SoftCoverageTarget(ContractModel):
    """Product guidance, never a user-authored quantity or verified fact."""

    target: Literal[1, 2] = 1
    origin: Literal["ordinary_preference", "current_trip_focus"] = "ordinary_preference"
    focus_source: SourceReference | None = None

    @model_validator(mode="after")
    def consistent_origin(self):
        focus = self.origin == "current_trip_focus"
        if self.target != (2 if focus else 1) or focus != (self.focus_source is not None):
            raise ValueError("Soft coverage target must agree with its origin and focus source")
        if self.focus_source and self.focus_source.match_mode != "exact":
            raise ValueError("Trip focus requires exact original source text")
        return self


def soft_coverage_eligible(requirement):
    goal = requirement.experience_goal
    return bool(
        goal
        and goal.target == "category"
        and goal.frequency in {"continuing", "one_off"}
        and not goal.explicit_primary_exception
        and requirement.polarity == "favor"
        and requirement.strength != "hard"
        and requirement.scope in {"individual_poi", "selected_poi_set", "whole_trip"}
    )


class SemanticRequirement(ContractModel):
    soft_coverage: SoftCoverageTarget | None = None
    experience_goal: ExperienceGoal | None = None
    requirement_id: str = Field(min_length=1, max_length=40)
    normalized_text: str = Field(min_length=1, max_length=320)
    kind: Literal["preference", "constraint", "goal"]
    polarity: Literal["favor", "avoid"]
    strength: Strength
    scope: Scope
    subject_refs: tuple[str, ...] = Field(min_length=1, max_length=9)
    source_refs: tuple[SourceReference, ...] = Field(min_length=1, max_length=3)

    @model_validator(mode="after")
    def valid_soft_coverage(self):
        if self.soft_coverage and not soft_coverage_eligible(self):
            raise ValueError("Only soft positive POI interests may carry coverage guidance")
        return self


class NamedRequirementDraft(ContractModel):
    place_text: str = Field(min_length=1, max_length=160)
    inclusion: Literal["REQUIRED", "OPTIONAL", "EXCLUDED"]
    source_refs: tuple[SourceQuote, ...] = Field(min_length=1, max_length=3)


class NamedRequirement(ContractModel):
    requirement_id: str = Field(min_length=1, max_length=40)
    place_text: str = Field(min_length=1, max_length=160)
    inclusion: Literal["REQUIRED", "OPTIONAL", "EXCLUDED"]
    source_refs: tuple[SourceReference, ...] = Field(min_length=1, max_length=3)


class DiscoveryIntent(ContractModel):
    intent_id: str = Field(min_length=1, max_length=40)
    requirement_refs: tuple[str, ...] = Field(min_length=1, max_length=4)
    purpose: Literal["activity_or_category", "semantic_discovery"]
    query_text: str = Field(min_length=1, max_length=200)


class DiscoveryDraft(ContractModel):
    requirement_refs: tuple[TemporaryHandle, ...] = Field(min_length=1, max_length=4)
    purpose: Literal["activity_or_category", "semantic_discovery"]
    query_text: str = Field(min_length=1, max_length=200)


class ExperienceEvidenceRequest(ContractModel):
    requirement_id: str = Field(min_length=1, max_length=40)
    dimension: ExperienceDimension
    preferred_values: tuple[ExperienceValue, ...] = Field(default=(), max_length=3)
    avoided_values: tuple[ExperienceValue, ...] = Field(default=(), max_length=3)

    @model_validator(mode="after")
    def valid_targets(self):
        preferred, avoided = set(self.preferred_values), set(self.avoided_values)
        if not (preferred | avoided) <= ALLOWED_VALUES[self.dimension]:
            raise ValueError("Evidence targets must belong to the requested dimension")
        if preferred & avoided:
            raise ValueError("Evidence targets cannot be both preferred and avoided")
        if len(preferred) != len(self.preferred_values) or len(avoided) != len(self.avoided_values):
            raise ValueError("Evidence targets must be unique")
        return self


class EvidenceRequestDraft(ContractModel):
    requirement_ref: TemporaryHandle
    dimension: ExperienceDimension
    preferred_values: tuple[ExperienceValue, ...] = Field(default=(), max_length=3)
    avoided_values: tuple[ExperienceValue, ...] = Field(default=(), max_length=3)

    @model_validator(mode="after")
    def valid_targets(self):
        ExperienceEvidenceRequest(
            requirement_id="validation",
            dimension=self.dimension,
            preferred_values=self.preferred_values,
            avoided_values=self.avoided_values,
        )
        return self


class OperationalConflict(ContractModel):
    field: Literal[
        "destination",
        "start_date",
        "end_date",
        "traveler_count",
        "budget.amount",
        "budget.currency",
    ]
    source_refs: tuple[SourceQuote, ...] = Field(min_length=1, max_length=3)


class VisitRequirementDraft(ContractModel):
    """Sourced visit count/date/access intention, never operating or admission evidence."""

    place_text: str = Field(min_length=1, max_length=200)
    access_mode: Literal["venue_entry", "exterior"] | None = None
    minimum_visits: int = Field(ge=1, le=10)
    exact_visits: int | None = Field(default=None, ge=1, le=10)
    distinct_dates: bool | None = None
    dates: tuple[date, ...] = Field(max_length=10)
    status: Literal["executable", "unresolved"]
    reason: str | None = Field(max_length=320)
    source_refs: tuple[SourceQuote, ...] = Field(min_length=1, max_length=3)

    @model_validator(mode="after")
    def exact_count(self):
        if self.exact_visits is not None and self.exact_visits != self.minimum_visits:
            raise ValueError("Exact visits and minimum visits must agree")
        return self

    @model_validator(mode="after")
    def valid_scope(self):
        if len(set(self.dates)) != len(self.dates) or self.minimum_visits < len(self.dates):
            raise ValueError("Visit count must cover unique mandatory dates")
        if self.status == "unresolved" and not self.reason:
            raise ValueError("Unresolved visit requirement needs a reason")
        return self


class VisitRequirement(VisitRequirementDraft):
    requirement_id: str
    source_refs: tuple[SourceReference, ...] = Field(min_length=1, max_length=3)


class TimeProtectionDraft(ContractModel):
    """Destination-local fixed time, or a scoped restriction not yet executable."""

    dates: tuple[date, ...] = Field(max_length=10)
    full_day: bool | None = None
    start_time: time | None
    end_time: time | None
    status: Literal["fixed", "unresolved"]
    reason: str | None = Field(max_length=320)
    source_refs: tuple[SourceQuote, ...] = Field(min_length=1, max_length=3)

    @model_validator(mode="after")
    def valid_interval(self):
        if len(set(self.dates)) != len(self.dates):
            raise ValueError("Duplicate protection date")
        if self.full_day is True and self.status == "fixed":
            if self.start_time is not None or self.end_time is not None:
                raise ValueError("Full-day protection must not also specify clock times")
        elif self.status == "fixed":
            if (
                self.start_time is None
                or self.end_time is None
                or self.start_time.tzinfo is not None
                or self.end_time.tzinfo is not None
                or self.start_time >= self.end_time
            ):
                raise ValueError("Fixed protection requires a same-day local interval")
        elif not self.reason:
            raise ValueError("Unresolved protection requires a reason")
        return self


class TimeProtection(TimeProtectionDraft):
    source_refs: tuple[SourceReference, ...] = Field(min_length=1, max_length=3)


InputIssueType = Literal[
    "destination_scope_conflict",
    "structured_request_conflict",
    "internal_requirement_contradiction",
    "unsupported_request_scope",
    "semantic_ambiguity",
    "non_travel_control_instruction",
    "safety_self_harm",
    "safety_serious_harm",
]
InputDisposition = Literal["VALID", "CLARIFICATION_REQUIRED", "REWRITE_REQUIRED"]
RequestField = Literal[
    "destination", "start_date", "end_date", "traveler_count", "budget.amount", "budget.currency"
]


class PreferenceInputIssue(ContractModel):
    """Model classification with exact grounding; never provider evidence or UI prose."""

    issue_type: InputIssueType
    source_refs: tuple[SourceQuote, ...] = Field(max_length=3)
    quote_status: Literal["located", "unavailable"]
    related_field: RequestField | None
    operational_conflict_index: int | None = Field(ge=0, le=5)
    scope: str = Field(min_length=1, max_length=320)

    @model_validator(mode="after")
    def grounded_shape(self):
        if (
            self.operational_conflict_index is not None
            and self.issue_type != "structured_request_conflict"
        ):
            raise ValueError("Only structured issues may consume an operational conflict link")
        if (self.quote_status == "located") != bool(self.source_refs):
            raise ValueError("Quote status must match supplied sources")
        if self.quote_status == "unavailable" and (
            self.issue_type != "structured_request_conflict"
            or self.operational_conflict_index is None
        ):
            raise ValueError("Unavailable quote requires a sourced operational conflict")
        if self.issue_type == "internal_requirement_contradiction" and len(self.source_refs) < 2:
            raise ValueError("Contradiction requires both conflicting sources")
        if self.issue_type == "destination_scope_conflict" and self.related_field != "destination":
            raise ValueError("Destination conflict requires destination field")
        if self.issue_type == "structured_request_conflict" and self.related_field is None:
            raise ValueError("Structured conflict requires a request field")
        return self


class PreferenceInputAssessment(ContractModel):
    """VALID is input readiness only, never feasibility or capability certification."""

    input_disposition: InputDisposition
    safety_disposition: Literal["CLEAR", "SAFETY_BLOCK"]
    issues: tuple[PreferenceInputIssue, ...] = Field(max_length=8)


class DailyPaceDraft(ContractModel):
    """Interpreter-owned style/count assessment; null date is the default."""

    date: date | None
    profile: Literal["ordinary", "relaxed", "rich", "unresolved"]
    exact_count: int | None = Field(ge=0)
    source_refs: tuple[SourceQuote, ...] = Field(max_length=8)


class DailyPace(DailyPaceDraft):
    source_refs: tuple[SourceReference, ...] = Field(max_length=8)


class DailyVisitConstraintDraft(ContractModel):
    """One sourced count of all primary visit occurrences on a requested date."""

    date: date
    mode: Literal["exact", "minimum"]
    count: int = Field(ge=0, strict=True)
    strength: Literal["hard", "soft"]
    requirement_refs: tuple[TemporaryHandle, ...] = Field(min_length=1, max_length=24)
    source_refs: tuple[SourceQuote, ...] = Field(min_length=1, max_length=3)


class DailyVisitConstraint(DailyVisitConstraintDraft):
    constraint_id: str
    source_refs: tuple[SourceReference, ...] = Field(min_length=1, max_length=3)


class TransportConstraintDraft(ContractModel):
    allowed_modes: tuple[TravelMode, ...] = Field(min_length=1, max_length=4)
    requirement_refs: tuple[TemporaryHandle, ...] = Field(min_length=1, max_length=24)
    source_refs: tuple[SourceQuote, ...] = Field(min_length=1, max_length=3)

    @model_validator(mode="after")
    def unique_modes(self):
        if len(set(self.allowed_modes)) != len(self.allowed_modes):
            raise ValueError("Duplicate allowed mode")
        if len(set(self.requirement_refs)) != len(self.requirement_refs):
            raise ValueError("Duplicate transport requirement")
        return self


class TransportConstraint(TransportConstraintDraft):
    source_refs: tuple[SourceReference, ...] = Field(min_length=1, max_length=3)


class InterpretationDraft(ContractModel):
    """One interpreter result. Local links are replaced with application IDs."""

    _diagnostic_call_id: str | None = PrivateAttr(default=None)
    transport_constraint: TransportConstraintDraft | None = None
    daily_visit_constraints: tuple[DailyVisitConstraintDraft, ...] | None = None

    @model_serializer(mode="wrap")
    def serialize_transport_constraint(self, handler):
        result = handler(self)
        if self.transport_constraint is None:
            result.pop("transport_constraint", None)
        if self.daily_visit_constraints is None:
            result.pop("daily_visit_constraints", None)
        return result

    # None is historical/unassessed. Current model entry requires an explicit assessment.
    preference_input_assessment: PreferenceInputAssessment | None = None
    daily_pace: tuple[DailyPaceDraft, ...] | None = Field(default=None, max_length=32)

    visit_requirements: tuple[VisitRequirementDraft, ...] | None = Field(
        default=None, max_length=24
    )
    time_protections: tuple[TimeProtectionDraft, ...] | None = Field(default=None, max_length=24)
    operational_conflicts: tuple[OperationalConflict, ...] = Field(default=(), max_length=6)
    named_places: tuple[NamedRequirementDraft, ...] = Field(max_length=24)
    requested_place_information: tuple[RequestedPlaceInformation, ...] = Field(max_length=32)
    transport_preference: TransportPreferenceIntent | None
    semantic_requirements: tuple[SemanticDraft, ...] = Field(max_length=24)
    subjects: tuple[Subject, ...] = Field(max_length=8)
    discovery_intents: tuple[DiscoveryDraft, ...] = Field(max_length=8)
    experience_evidence_requests: tuple[EvidenceRequestDraft, ...] = Field(max_length=120)
    extraction_issues: tuple[str, ...] = Field(max_length=8)
    overflow: bool

    @model_validator(mode="after")
    def bounded_content(self) -> "InterpretationDraft":
        if len(self.model_dump_json()) > 180000:
            raise ValueError("draft_resource_overflow")
        if sum(len(r.normalized_text) for r in self.semantic_requirements) > 6000:
            raise ValueError("semantic_text_overflow")
        sources = [
            s
            for group in (
                self.semantic_requirements,
                self.named_places,
                self.subjects,
                self.operational_conflicts,
                (self.transport_constraint,) if self.transport_constraint else (),
                self.preference_input_assessment.issues if self.preference_input_assessment else (),
            )
            for item in group
            for s in item.source_refs
        ]
        information_sources = [
            text
            for i in self.requested_place_information
            for text in (
                i.source_text,
                i.target_source_text,
                i.date_source_text or "",
                i.scope_text or "",
            )
        ]
        transport_length = (
            len(self.transport_preference.source_text) if self.transport_preference else 0
        )
        if (
            sum(len(s.quote) for s in sources)
            + sum(
                len(r.trip_focus_source.quote)
                for r in self.semantic_requirements
                if r.trip_focus_source
            )
            + sum(map(len, information_sources))
            + transport_length
        ) > 12000:
            raise ValueError("source_text_overflow")
        if sum(len(i.query_text) for i in self.discovery_intents) > 1200:
            raise ValueError("discovery_text_overflow")
        if any(len(i) > 320 for i in self.extraction_issues):
            raise ValueError("extraction_issue_overflow")
        if len({c.field for c in self.operational_conflicts}) != len(self.operational_conflicts):
            raise ValueError("duplicate_operational_conflicts")
        return self


class InterpretedTripRequirements(ContractModel):
    contract_version: Literal[
        "interpreted_requirements_3",
        "interpreted_requirements_4",
        "interpreted_requirements_5",
        "interpreted_requirements_6",
    ] = CONTRACT_VERSION
    transport_constraint: TransportConstraint | None = None
    daily_visit_constraints: tuple[DailyVisitConstraint, ...] | None = None

    @model_serializer(mode="wrap")
    def serialize_transport_constraint(self, handler):
        result = handler(self)
        if self.transport_constraint is None:
            result.pop("transport_constraint", None)
        if self.daily_visit_constraints is None:
            result.pop("daily_visit_constraints", None)
        return result

    request_sha256: str
    daily_pace: tuple[DailyPace, ...] | None = Field(default=None, max_length=32)
    input_version: Literal["planning_request_2"] = "planning_request_2"
    structured_input_sha256: str
    structured_field_paths: tuple[str, ...] = (
        "destination",
        "start_date",
        "end_date",
        "traveler_count",
        "budget.amount",
        "budget.currency",
    )
    visit_requirements: tuple[VisitRequirement, ...] | None = Field(default=None, max_length=24)
    time_protections: tuple[TimeProtection, ...] | None = Field(default=None, max_length=24)
    interpretation_origin: Literal["model", "skipped_empty"]
    requirements: TravelRequirements
    named_places: tuple[NamedRequirement, ...]
    requested_place_information: tuple[RequestedPlaceInformation, ...]
    transport_preference: TransportPreferenceIntent | None
    semantic_requirements: tuple[SemanticRequirement, ...]
    subjects: tuple[CanonicalSubject, ...]
    discovery_intents: tuple[DiscoveryIntent, ...]
    experience_evidence_requests: tuple[ExperienceEvidenceRequest, ...]
    extraction_issues: tuple[str, ...]

    @model_validator(mode="after")
    def canonical_graph(self):
        groups = (
            (self.subjects, "subject_id", "subject", 8),
            (self.semantic_requirements, "requirement_id", "semantic", 24),
            (self.named_places, "requirement_id", "named", 24),
            (self.discovery_intents, "intent_id", "discovery", 8),
        )
        for items, field, prefix, maximum in groups:
            if len(items) > maximum:
                raise ValueError("Canonical collection overflow")
            if [getattr(i, field) for i in items] != [
                f"{prefix}_{i + 1}" for i in range(len(items))
            ]:
                raise ValueError("Canonical IDs must be application allocated")
        subjects = {s.subject_id for s in self.subjects} | {"party"}
        semantics = {s.requirement_id for s in self.semantic_requirements}
        if any(not set(r.subject_refs) <= subjects for r in self.semantic_requirements):
            raise ValueError("Dangling canonical subject reference")
        if any(not set(d.requirement_refs) <= semantics for d in self.discovery_intents):
            raise ValueError("Dangling canonical discovery reference")
        if any(r.requirement_id not in semantics for r in self.experience_evidence_requests):
            raise ValueError("Dangling canonical evidence reference")
        keys = [(r.requirement_id, r.dimension) for r in self.experience_evidence_requests]
        if len(keys) != len(set(keys)) or len(keys) > 120:
            raise ValueError("Duplicate or excessive canonical evidence requests")
        if len(self.requested_place_information) > 32 or self.extraction_issues:
            raise ValueError("Invalid canonical information or unresolved extraction issues")
        if sum(len(r.normalized_text) for r in self.semantic_requirements) > 6000:
            raise ValueError("Canonical semantic text overflow")
        return self


class RequirementAssessment(ContractModel):
    """Application-owned only; not part of the interpreter/selector response schema."""

    requirement_id: str
    capability: Literal[
        "registered_predicate", "evidence_assessment", "semantic_only", "unsupported"
    ]
    predicate_id: str | None = None
    predicate_version: str | None = None
    evaluation_scope: Scope
    evidence_refs: tuple[str, ...] = ()
    evidence_state: Literal["available", "partial", "missing", "conflicting", "not_acquired"]
    check_result: Literal["pass", "fail", "unknown", "not_applicable"]
    disposition: Literal["enforce", "advise", "acquire", "clarify"]


class ClarificationRequired(ValueError):
    """Typed non-success outcome; no accepted candidate set or itinerary exists."""

    def __init__(
        self, code: str, requirement_ids: tuple[str, ...] = (), *, conflicts: tuple[dict, ...] = ()
    ) -> None:
        self.conflicts = conflicts
        self.code = code
        self.requirement_ids = requirement_ids
        super().__init__(code)

    def as_dict(self) -> dict[str, object]:
        return {
            "status": "clarification_required",
            "code": self.code,
            "conflicts": self.conflicts,
            "requirement_ids": self.requirement_ids,
        }
