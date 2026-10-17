"""Bounded repair proposals and application-owned operation permissions."""

from datetime import date, datetime
from typing import Literal

from pydantic import Field, model_serializer, model_validator

from backend.app.evidence.effective_models import EffectivePlaceEvidence
from backend.app.evidence.models import PlaceEvidence, RouteEvidence
from backend.app.policies.poi_funnel import NamedPlaceResolution
from backend.app.policies.trip_dates import TripDateWindow
from backend.app.schemas.interpreted_requirements import InterpretedTripRequirements
from backend.app.schemas.itinerary import Itinerary
from backend.app.schemas.poi_semantics import POISemanticAssessment
from backend.app.versions.v3.models import ValidationModel, ValidationPolicy, ValidationReport
from backend.app.versions.v3.repair_schedule import ScheduleState

Operation = Literal["retime", "add", "replace", "delete", "move"]


class RevisitPermission(ValidationModel):
    place_id: str
    date: date


class ActivityPermission(ValidationModel):
    activity_id: str
    operations: frozenset[Literal["retime", "replace", "delete", "move"]]
    allow_duration_change: bool = False
    source_date: date | None = None
    move_dates: tuple[date, ...] = ()


class CoveragePermission(ValidationModel):
    target_id: str
    parent_id: str
    date: date
    trigger_activity_ids: tuple[str, ...]
    minimum_count: int = Field(ge=0)
    allow_partial: bool = False
    reason: Literal["review_compensation", "excluded_removal", "confirmed_visit_removal"]
    removable_place_ids: tuple[str, ...] = ()


class RelatedTarget(ValidationModel):
    permission: CoveragePermission
    activated_by: tuple[str, ...]
    affected_adjacency: tuple[tuple[str, str], ...] = ()
    before: int
    after: int
    status: Literal["resolved", "unresolved", "unknown"]


class RepairScope(ValidationModel):
    allowed_transport_modes: tuple[Literal["WALK", "TRANSIT", "DRIVE"], ...] | None = None
    deferred_review_target_ids: tuple[str, ...] = ()
    window_roots: tuple[str, ...] = ()
    coverage_permissions: tuple[CoveragePermission, ...] = ()
    active_related: tuple[RelatedTarget, ...] = ()
    daily_main_min: int = 2
    daily_main_max: int = 5
    dates: tuple[date, ...] = Field(max_length=10)
    permissions: tuple[ActivityPermission, ...]
    add_dates: tuple[date, ...] = ()
    direct_add_dates: tuple[date, ...] | None = None
    target_ids: tuple[str, ...] = Field(min_length=1)
    allow_coverage_regression: bool = False
    # Optional structured mode choice, never inferred from itinerary prose.
    travel_mode: Literal["WALK", "TRANSIT", "DRIVE"] | None = None
    revisits: tuple[RevisitPermission, ...] = ()
    routing_preference: str | None = None
    mode_source: str | None = None
    unsupported_explicit_mode: str | None = None

    @model_serializer(mode="wrap")
    def serialize_optional_modes(self, handler):
        result = handler(self)
        if self.allowed_transport_modes is None:
            result.pop("allowed_transport_modes", None)
        return result

    @model_validator(mode="after")
    def unique_scope(self):
        if len(set(self.dates)) != len(self.dates) or not set(self.add_dates) <= set(self.dates):
            raise ValueError("Invalid repair dates")
        ids = [p.activity_id for p in self.permissions]
        if any(r.date not in self.add_dates for r in self.revisits):
            raise ValueError("Revisit must belong to an authorized addition date")
        if len(ids) != len(set(ids)) or len(self.target_ids) != len(set(self.target_ids)):
            raise ValueError("Duplicate scope identity")
        return self


class RepairEdit(ValidationModel):
    # Every field is required for the strict transport schema; irrelevant fields are null.
    operation: Operation
    activity_id: str | None
    date: date
    place_id: str | None
    start_time: datetime | None
    end_time: datetime | None


REPAIR_REASON_CHARACTERS = 240


class TargetDisposition(ValidationModel):
    target_id: str
    disposition: Literal[
        "proposed", "unresolved", "needs_evidence", "competing_candidate", "not_attempted"
    ]
    reason: str = Field(max_length=REPAIR_REASON_CHARACTERS)


class RepairPatch(ValidationModel):
    edits: tuple[RepairEdit, ...] = Field(max_length=50)
    target_dispositions: tuple[TargetDisposition, ...] = Field(default=(), max_length=50)


class RepairCandidate(ValidationModel):
    place: PlaceEvidence
    origin: Literal["original_supply", "comparison_pool", "discovered", "google", "rag"]
    provenance: tuple[str, ...] = Field(min_length=1)


class CandidateDecision(ValidationModel):
    place_id: str
    target_id: str
    date: date
    operation: Literal["add", "replace"]
    disposition: Literal[
        "eligible",
        "scheduled_context",
        "excluded",
        "capacity_omitted",
        "selected",
        "details_pending",
        "fact_ineligible",
    ]
    reason: str
    evidence_refs: tuple[str, ...] = ()
    unknowns: tuple[str, ...] = ()
    # Evidence presence is not a visit feasibility judgment.
    has_date_hours: bool = False
    related_intent_ids: tuple[str, ...] = ()
    opportunity_status: Literal["TRYABLE", "UNRESOLVED", "BLOCKED"] = "UNRESOLVED"
    opportunity_reason: str = "not_preassessed"
    opportunity_windows: tuple[tuple[str, str], ...] = ()
    opportunity_signature: str = ""


class CandidatePreparation(ValidationModel):
    identity_capacity_summary: dict = Field(default_factory=dict)
    identity_free_operations: tuple[dict, ...] = ()
    target_opportunities: tuple[dict, ...] = ()
    elastic_windows: tuple[dict, ...] = ()
    discovery_opportunities: tuple[dict, ...] = ()
    ledger: tuple[RepairCandidate, ...] = ()
    input_candidates: tuple[RepairCandidate, ...] = ()
    authorizations: tuple[CandidateDecision, ...] = ()
    decisions: tuple[CandidateDecision, ...] = ()
    scheduled_ids: tuple[str, ...] = ()
    exploration_reasons: tuple[str, ...] = ()
    exploration_slots: int = 0
    preparation_reference: int = 0
    spatial_options: tuple[dict, ...] = ()


class RepairComparison(ValidationModel):
    accepted: bool
    reason: str
    progress: tuple["TargetProgress", ...] = ()
    coverage_regressions: tuple[date, ...] = ()
    business_values: tuple[dict, ...] = ()


class TransitionBinding(ValidationModel):
    from_activity_id: str
    to_activity_id: str
    travel_mode: Literal["WALK", "TRANSIT", "DRIVE"]
    departure_time: datetime
    routing_preference: str | None = None
    application_reserve_seconds: float = Field(default=0, ge=0)
    mode_source: str = "USER_EXPLICIT"


class VisitBinding(ValidationModel):
    """Application-owned visit intent; never an operating/access fact."""

    activity_id: str
    place_id: str
    mode: Literal["venue_entry", "exterior"]
    subject_scope: Literal["whole_venue"] = "whole_venue"
    source_refs: tuple[str, ...] = Field(min_length=1)


class ValidationContext(ValidationModel):
    semantic_assessments: tuple[POISemanticAssessment, ...] = ()
    visit_bindings: tuple[VisitBinding, ...] = ()
    active_related: tuple[RelatedTarget, ...] = ()
    schedule: ScheduleState | None = None
    contract: InterpretedTripRequirements
    window: TripDateWindow
    original_supply_ids: tuple[str, ...]
    places: tuple[PlaceEvidence, ...]
    named_resolutions: tuple[NamedPlaceResolution, ...] = ()
    effective_places: tuple[EffectivePlaceEvidence, ...] = ()
    route_evidence: tuple[RouteEvidence, ...] = ()
    transitions: tuple[TransitionBinding, ...] = ()
    identity_ledger: tuple[RepairCandidate, ...] = ()
    policy: ValidationPolicy = Field(default_factory=ValidationPolicy)


class TargetProgress(ValidationModel):
    finding_id: str
    check: str
    outcome: Literal["resolved", "improved", "unresolved", "unknown"]
    before: float | None
    after: float | None


class RepairResult(ValidationModel):
    # Missing fields on historical records mean the pre-search single adopted chain.
    search_version: Literal[1] | None = None
    selected_round_index: int | None = None
    selected_semantic_assessments: tuple[POISemanticAssessment, ...] | None = None
    soft_pace: dict = Field(default_factory=dict)
    pending_groups: tuple[dict, ...] = ()
    effective_patch: RepairPatch | None = None
    components: tuple[dict, ...] = ()
    acquisition_audit: tuple[dict, ...] = ()
    feedback_kind: str = "not_evaluated"
    material_fingerprint: str | None = None
    presentation_history: tuple[dict, ...] = ()
    conflict_records: tuple[dict, ...] = ()
    related_targets: tuple[RelatedTarget, ...] = ()
    schedule: ScheduleState | None = None
    window_adjustments: tuple[dict, ...] = ()
    status: Literal["SKIPPED", "REJECTED", "ACCEPTED_PARTIAL", "ACCEPTED_COMPLETE"]
    reason: str
    model_attempted: bool
    original: Itinerary
    final: Itinerary
    original_report: ValidationReport
    reassessed_original_report: ValidationReport | None = None
    proposed_report: ValidationReport | None = None
    adopted_report: ValidationReport | None = None
    acquired_routes: tuple[RouteEvidence, ...] = ()
    target_progress: tuple[TargetProgress, ...] = ()
    original_supply_ids: tuple[str, ...]
    repair_whitelist: tuple[RepairCandidate, ...] = ()
    final_place_ids: tuple[str, ...]
    main_visits_lost: tuple[str, ...] = ()
    coverage_regressions: tuple[date, ...] = ()
    counters: dict[str, int] = Field(default_factory=dict)
    stops: tuple[str, ...] = ()
    sizing: dict[str, int] = Field(default_factory=dict)
    candidate_preparation: CandidatePreparation | None = None
    scope: RepairScope | None = None
    parsed_patch: RepairPatch | None = None
    proposed: Itinerary | None = None
    comparison: RepairComparison | None = None
    usage: dict = Field(default_factory=dict)
    usage_status: str = "not_reported"
    reason_compression: dict = Field(default_factory=dict)
    timing: dict = Field(default_factory=dict)
    spatial: dict = Field(default_factory=dict)
    rounds: tuple["RepairRoundRecord", ...] = ()
    effective_policy: dict = Field(default_factory=dict)
    artifact_status: dict[str, str] = Field(default_factory=dict)


class RepairRoundRecord(ValidationModel):
    round_index: int
    strategy: str | None = None
    base_state: str | None = None
    exploration_transition: bool = False
    best_promoted: bool = False
    best_state: str | None = None
    target_links: dict[str, str] = Field(default_factory=dict)
    input_itinerary: Itinerary
    result: RepairResult
    adopted: Itinerary
    feedback: dict | None = None
    continuation_reason: str
    usage: dict = Field(default_factory=dict)


RepairResult.model_rebuild()
