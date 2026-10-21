"""Strict request and model contracts for optional preference polishing."""

from datetime import date
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from backend.app.schemas.request import Money


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


ExactText = Annotated[str, StringConstraints(strip_whitespace=False)]


class PolishContext(_StrictModel):
    destination: str | None = Field(default=None, max_length=200)
    start_date: date | None = None
    end_date: date | None = None
    traveler_count: int | None = Field(default=None, strict=True, ge=1)
    budget: Money | None = None


class PolishRequest(_StrictModel):
    original_text: ExactText = Field(min_length=1, max_length=4000)
    context: PolishContext = Field(default_factory=PolishContext)
    client_revision: str = Field(min_length=1, max_length=100)

    @field_validator("original_text")
    @classmethod
    def nonblank_original(cls, value):
        if not value.strip():
            raise ValueError("Preference text must not be blank")
        return value


class PolishDraft(_StrictModel):
    status: Literal["suggested", "unchanged", "needs_input"]
    suggested_text: ExactText | None = Field(default=None, max_length=4000)
    explanation: str = Field(min_length=1, max_length=500)
    questions: list[str] = Field(default_factory=list, max_length=3)

    @model_validator(mode="after")
    def only_suggestions_replace_text(self):
        if self.status == "suggested" and not (self.suggested_text or "").strip():
            raise ValueError("A suggested rewrite requires text")
        if self.status != "suggested" and self.suggested_text is not None:
            raise ValueError("Only suggestions may include replacement text")
        if any(not item or len(item) > 200 for item in self.questions):
            raise ValueError("Questions must be brief")
        if self.status == "needs_input" and not self.questions:
            raise ValueError("Clarification requires a focused question")
        return self


class PolishResponse(_StrictModel):
    status: Literal["suggested", "unchanged", "needs_input"]
    original_text: ExactText
    suggested_text: ExactText | None
    explanation: str
    questions: list[str]
    client_revision: str
