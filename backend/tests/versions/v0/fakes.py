"""Test doubles and fixtures for the V0 workflow."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import cast

from pydantic import BaseModel

from backend.app.llm.client import StructuredModelT
from backend.app.schemas.itinerary import Activity, Itinerary, ItineraryDay
from backend.app.schemas.request import TravelRequirements


@dataclass(frozen=True)
class StructuredCall:
    """One captured structured LLM invocation."""

    system_prompt: str
    user_prompt: str
    response_schema: type[BaseModel]


class FakeStructuredLLMClient:
    """Return queued models or exceptions without network access."""

    def __init__(self, responses: list[BaseModel | Exception]) -> None:
        self.responses = list(responses)
        self.calls: list[StructuredCall] = []
        self.semantic_calls = []

    async def generate_named_place_binding_structured(self, **kwargs):
        """Explicit correspondence fixture; production never falls back to lexical rules."""
        import json

        payload = json.loads(kwargs["user_prompt"])
        return {
            "decisions": [
                {
                    "requirement_ref": r["requirement_ref"],
                    "candidates": [
                        {
                            "candidate_ref": c["candidate_ref"],
                            "relation": "same_place"
                            if c["place"]["name"].casefold() == r["place_text"].casefold()
                            else "different_place",
                            "evidence_refs": [c["evidence_ref"]],
                            "reason": "Synthetic graph fixture correspondence",
                        }
                        for c in r["candidates"]
                    ],
                }
                for r in payload["requirements"]
            ]
        }

    async def generate_poi_semantics_structured(self, **kwargs):
        """Explicit synthetic role evidence for graph tests, never a production fallback."""
        import json

        payload = json.loads(kwargs["user_prompt"])
        self.semantic_calls.append(payload)
        return {
            "assessments": [
                dict(
                    candidate_ref=p["candidate_ref"],
                    visit_object=p["name"],
                    role="attraction",
                    categories=["fixture_attraction"],
                    reason="Synthetic graph fixture",
                    evidence_refs=[p["source_ref"]],
                    matches=[],
                    exception_requirement_ids=[],
                )
                for p in payload["places"]
            ]
        }

    async def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[StructuredModelT],
    ) -> StructuredModelT:
        self.calls.append(
            StructuredCall(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_schema=response_schema,
            )
        )
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        if not isinstance(response, response_schema):
            raise AssertionError(f"Fake response does not match {response_schema.__name__}")
        return cast(StructuredModelT, response)


def make_requirements() -> TravelRequirements:
    """Create complete requirements suitable for a successful V0 run."""

    return TravelRequirements(
        destination="Kyoto",
        start_date=date(2026, 9, 12),
        end_date=date(2026, 9, 12),
        traveler_count=1,
    )


def make_itinerary() -> Itinerary:
    """Create a minimal valid itinerary for V0 tests."""

    return Itinerary(
        destination="Kyoto",
        start_date=date(2026, 9, 12),
        end_date=date(2026, 9, 12),
        days=[
            ItineraryDay(
                date=date(2026, 9, 12),
                activities=[
                    Activity(
                        activity_id="activity-1",
                        title="Visit Fushimi Inari Shrine",
                        start_time=datetime.fromisoformat("2026-09-12T09:00:00+09:00"),
                        end_time=datetime.fromisoformat("2026-09-12T11:00:00+09:00"),
                    )
                ],
            )
        ],
    )
