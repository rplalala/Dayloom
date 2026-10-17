"""Explicit current/historical bundles keep schema, prompt and source readers aligned."""

from collections.abc import Callable
from dataclasses import dataclass

from pydantic import BaseModel

from backend.app.llm.azure_foundry.dto import (
    FoundryCurrentInterpretationDTO,
    FoundryDatedInterpretationDTO,
    FoundryInterpretationDTO,
)
from backend.app.llm.azure_foundry.requirement_wire import (
    IndexedSourceSpans,
    SourceSpans,
    current_prompt,
    dated_prompt,
    indexed_prompt,
)
from backend.app.schemas.requirement_boundary import RequirementBoundaryError

CURRENT_REQUIREMENT_PROFILE = "preference_draft_15"


@dataclass(frozen=True)
class RequirementProfile:
    schema_version: str
    schema_name: str
    prompt_version: str
    dto: type[BaseModel]
    source_type: type[SourceSpans] | None = None
    project_prompt: Callable[[str], str] = lambda text: text
    compact_json: bool = False


PROFILES = {
    p.schema_version: p
    for p in (
        RequirementProfile(
            "preference_draft_12",
            "PreferenceDraftV10",
            "preference_prompt_19",
            FoundryInterpretationDTO,
        ),
        RequirementProfile(
            "preference_draft_13",
            "PreferenceDraftV13",
            "preference_prompt_20",
            FoundryCurrentInterpretationDTO,
            SourceSpans,
            current_prompt,
        ),
        RequirementProfile(
            "preference_draft_14",
            "PreferenceDraftV14",
            "preference_prompt_21",
            FoundryCurrentInterpretationDTO,
            IndexedSourceSpans,
            indexed_prompt,
        ),
        RequirementProfile(
            "preference_draft_15",
            "PreferenceDraftV15",
            "preference_prompt_22",
            FoundryDatedInterpretationDTO,
            IndexedSourceSpans,
            dated_prompt,
            True,
        ),
    )
}


def requirement_profile(version):
    if version not in PROFILES:
        raise RequirementBoundaryError(
            "unknown_requirement_profile", stage="configuration", category="configuration_failure"
        )
    return PROFILES[version]
