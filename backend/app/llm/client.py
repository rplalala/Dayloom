"""Provider-independent interfaces for structured LLM calls."""

from typing import Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel

StructuredModelT = TypeVar("StructuredModelT", bound=BaseModel)


class StructuredOutputError(RuntimeError):
    """Raised when a provider response cannot be parsed into the requested schema."""


@runtime_checkable
class StructuredLLMClient(Protocol):
    """Generate a Pydantic model without exposing provider details to callers."""

    async def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[StructuredModelT],
    ) -> StructuredModelT:
        """Return one provider-native structured response."""

        ...


class LandmarkNominationLLMClient(Protocol):
    async def generate_landmark_nomination_structured(
        self, *, system_prompt: str, user_prompt: str, output_tokens: int, usage_callback=None
    ) -> BaseModel:
        """One destination-only nomination; caller owns limits and cancellation."""
        ...


class POISemanticLLMClient(Protocol):
    async def generate_poi_semantics_structured(
        self, *, system_prompt: str, user_prompt: str, output_tokens: int, usage_callback=None
    ) -> BaseModel:
        """One short-reference wire batch; the caller owns resolution and retry limits."""
        ...


class NamedPlaceBindingLLMClient(Protocol):
    async def generate_named_place_binding_structured(
        self, *, system_prompt: str, user_prompt: str, output_tokens: int, usage_callback=None
    ) -> BaseModel:
        """Evidence-bound named correspondence; caller owns admission and cancellation."""
        ...
