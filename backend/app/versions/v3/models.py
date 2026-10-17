"""Application-owned read-only findings, separate from generation observations."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.app.schemas.generation_diagnostics import GenerationDiagnostics


class ValidationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Finding(ValidationModel):
    finding_id: str
    check: Literal[
        "coverage",
        "overfull",
        "repetition",
        "overlap",
        "named_requirement",
        "opening",
        "visitor_suitability",
        "route",
        "budget",
        "semantic_requirements",
        "primary_policy",
        "soft_pace",
        "daily_visit_count",
    ]
    status: Literal["PASS", "CONFIRMED", "NEEDS_REVIEW", "UNKNOWN"]
    reason: str
    dates: tuple[date, ...] = ()
    activity_ids: tuple[str, ...] = ()
    place_ids: tuple[str, ...] = ()
    requirement_ids: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    is_violation: bool = False
    magnitude: float | None = None
    adopted_evidence: dict[str, object] = Field(default_factory=dict)

    @model_validator(mode="after")
    def confirmed_is_violation(self):
        if self.is_violation != (self.status == "CONFIRMED"):
            raise ValueError("Only CONFIRMED findings are violations")
        if self.is_violation and not self.evidence_refs:
            raise ValueError("Confirmed findings require traceable evidence")
        return self


class ImprovementTarget(ValidationModel):
    """A policy proposal, never permission to edit a date or waive a requirement."""

    finding_id: str
    basis: Literal["confirmed_conflict", "review_policy"]


class PlaceUseObservation(ValidationModel):
    """Provider classification, not a public-access or tourist-suitability verdict."""

    place_id: str
    primary_type: str | None
    source_ref: str


class ValidationReport(ValidationModel):
    contract_version: Literal["v3_validation_1"] = "v3_validation_1"
    diagnostics: GenerationDiagnostics
    findings: tuple[Finding, ...]
    place_use_observations: tuple[PlaceUseObservation, ...] = ()
    improvement_targets: tuple[ImprovementTarget, ...] = ()
    # The report never represents whole-trip PASS or successful repair.
    scope: Literal["read_only_partial_validation"] = "read_only_partial_validation"

    @model_validator(mode="after")
    def valid_target_links(self):
        by_id = {finding.finding_id: finding for finding in self.findings}
        if len(by_id) != len(self.findings):
            raise ValueError("Finding IDs must be unique")
        target_ids = [target.finding_id for target in self.improvement_targets]
        if len(target_ids) != len(set(target_ids)):
            raise ValueError("Improvement targets must be unique")
        for target in self.improvement_targets:
            finding = by_id.get(target.finding_id)
            expected = "CONFIRMED" if target.basis == "confirmed_conflict" else "NEEDS_REVIEW"
            if finding is None or finding.status != expected:
                raise ValueError("Improvement target must preserve the linked finding status")
        return self


class ValidationPolicy(ValidationModel):
    """Opt-in review targets retain uncertainty; defaults propose confirmed conflicts only."""

    daily_main_min: int = 2
    daily_main_max: int = 5
    review_targets: frozenset[Literal["coverage", "opening", "overfull", "soft_pace"]] = Field(
        default_factory=frozenset
    )
