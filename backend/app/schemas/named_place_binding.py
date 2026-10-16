"""Provider wire for evidence-based correspondence, not canonical identity authority."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class NamedCandidateJudgment(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    candidate_ref: str
    relation: Literal["same_place", "different_place", "unresolved"]
    evidence_refs: list[str]
    reason: str


class NamedIntentJudgment(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    requirement_ref: str
    candidates: list[NamedCandidateJudgment]


class NamedBindingBatch(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    decisions: list[NamedIntentJudgment]
