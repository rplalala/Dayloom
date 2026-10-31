"""Tests for the Microsoft Foundry structured-output client."""

import asyncio
from decimal import Decimal
from typing import Any

import pytest
from pydantic import BaseModel

from backend.app.evidence.experience_models import ExperienceProfileDraft
from backend.app.llm.azure_foundry import client as client_module
from backend.app.llm.azure_foundry.client import AzureFoundryStructuredLLMClient
from backend.app.llm.azure_foundry.dto import (
    FoundryDateTimeDTO,
    FoundryExperienceProfileDTO,
    FoundryExperienceSignalDTO,
    FoundryItineraryDayDTO,
    FoundryItineraryDTO,
    FoundryMoneyDTO,
    FoundryPrimaryItineraryDTO,
    FoundryV0ActivityDTO,
)
from backend.app.llm.client import StructuredOutputError
from backend.app.schemas.itinerary import Itinerary
from backend.app.schemas.itinerary_projection import V1Itinerary
from backend.app.schemas.request import TravelRequirements


class FakeStructuredModel:
    def __init__(self, response: object) -> None:
        self.response = response
        self.messages: list[object] = []
        self.invocation_count = 0

    async def ainvoke(self, messages: list[object]) -> object:
        self.messages = messages
        self.invocation_count += 1
        return self.response


class FakeChatOpenAI:
    response: object
    init_kwargs: dict[str, Any] = {}
    schema: object = None
    structured_kwargs: dict[str, Any] = {}
    structured_model: FakeStructuredModel
    structured_output_count = 0

    def __init__(self, **kwargs: Any) -> None:
        type(self).init_kwargs = kwargs

    def bind(self, **kwargs):
        import json

        from langchain_core.messages import AIMessage

        parsed = type(self).response["parsed"]
        raw = type(self).response["raw"]
        type(self).schema = kwargs["response_format"]
        type(self).structured_kwargs = kwargs
        type(self).structured_model = FakeStructuredModel(
            AIMessage(
                content=json.dumps(parsed.model_dump(mode="json")),
                response_metadata={"status": "completed", "model_name": "fixture-model"},
                usage_metadata=getattr(raw, "usage_metadata", None),
            )
        )
        return type(self).structured_model

    def with_structured_output(
        self,
        schema: object,
        **kwargs: Any,
    ) -> FakeStructuredModel:
        type(self).schema = schema
        type(self).structured_kwargs = kwargs
        type(self).structured_output_count += 1
        type(self).structured_model = FakeStructuredModel(type(self).response)
        return type(self).structured_model


def make_activity(
    *,
    end_time: FoundryDateTimeDTO | None = None,
) -> FoundryV0ActivityDTO:
    return FoundryV0ActivityDTO(
        activity_kind="main_poi",
        atmosphere_theme=None,
        time_use="scheduled",
        source_place_id=None,
        activity_id="activity-1",
        title="Visit Fushimi Inari Shrine",
        place_name="Fushimi Inari Taisha",
        location="Kyoto, Japan",
        start_time=FoundryDateTimeDTO(
            date="2026-10-01",
            time="09:00:00",
            utc_offset="+09:00",
        ),
        end_time=end_time
        or FoundryDateTimeDTO(
            date="2026-10-01",
            time="11:00:00",
            utc_offset="+09:00",
        ),
        estimated_cost=None,
        notes=None,
        transport=None,
    )


def make_client(monkeypatch: pytest.MonkeyPatch) -> AzureFoundryStructuredLLMClient:
    FakeChatOpenAI.structured_output_count = 0
    monkeypatch.setattr(client_module, "ChatOpenAI", FakeChatOpenAI)
    return AzureFoundryStructuredLLMClient(
        endpoint="https://example.services.ai.azure.com/openai/v1",
        deployment="configured-deployment",
        api_key="test-key",
    )


def generate(client: AzureFoundryStructuredLLMClient, response_schema: type[BaseModel]):
    return asyncio.run(
        client.generate_structured(
            system_prompt="System prompt",
            user_prompt="User prompt",
            response_schema=response_schema,
        )
    )


def test_old_operational_extraction_binding_is_removed(monkeypatch):
    client = make_client(monkeypatch)
    with pytest.raises(StructuredOutputError, match="no transport DTO"):
        generate(client, TravelRequirements)


@pytest.mark.parametrize(
    "declaration",
    [
        None,
        {"mode": "TRANSIT", "from_activity_id": "a", "to_activity_id": "b"},
        {"mode": None, "from_activity_id": "a", "to_activity_id": "b"},
    ],
)
def test_client_uses_itinerary_dto_and_returns_domain_model(
    monkeypatch: pytest.MonkeyPatch,
    declaration,
) -> None:
    raw = make_activity().model_dump()
    if declaration is not None:
        raw.update(activity_kind="transport", place_name=None, transport=declaration)
    activities = [FoundryV0ActivityDTO.model_validate(raw)]
    if declaration is not None:
        for aid, start, end in (("a", "07:00:00", "08:00:00"), ("b", "12:00:00", "13:00:00")):
            visit = make_activity()
            activities.append(
                visit.model_copy(
                    update={
                        "activity_id": aid,
                        "start_time": visit.start_time.model_copy(update={"time": start}),
                        "end_time": visit.end_time.model_copy(update={"time": end}),
                    }
                )
            )
    FakeChatOpenAI.response = FoundryItineraryDTO(
        output_version="itinerary_3",
        reference_recommendations=[],
        destination="Kyoto",
        start_date="2026-10-01",
        end_date="2026-10-01",
        days=[
            FoundryItineraryDayDTO(
                date="2026-10-01",
                activities=activities,
            )
        ],
    )
    client = make_client(monkeypatch)

    result = generate(client, Itinerary)

    assert isinstance(result, Itinerary)
    assert FakeChatOpenAI.schema is FoundryItineraryDTO
    assert result.days[0].activities[0].end_time.isoformat() == ("2026-10-01T11:00:00+09:00")
    assert FakeChatOpenAI.structured_model.invocation_count == 1
    serialized = result.model_dump(mode="json")["days"][0]["activities"][0]
    assert serialized.get("transport") == declaration
    if declaration is None:
        assert "transport" not in serialized


def test_client_v1_projects_range_cost_in_one_call_without_changing_v0_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    activity = make_activity().model_copy(
        update={"estimated_cost": FoundryMoneyDTO(amount="1.00-10.00", currency="SGD")}
    )
    FakeChatOpenAI.response = FoundryPrimaryItineraryDTO(
        output_version="itinerary_3",
        destination="Kyoto",
        start_date="2026-10-01",
        end_date="2026-10-01",
        days=[{"date": "2026-10-01", "activities": [activity.model_dump(exclude={"transport"})]}],
    )
    client = make_client(monkeypatch)

    result = generate(client, V1Itinerary)

    assert isinstance(result, V1Itinerary)
    assert result.days[0].activities[0].estimated_cost is not None
    assert result.days[0].activities[0].estimated_cost.amount == Decimal("5.50")
    assert result.cost_projections[0].projection == "midpoint_from_range"
    assert FakeChatOpenAI.schema is FoundryPrimaryItineraryDTO
    assert FakeChatOpenAI.structured_model.invocation_count == 1
    with pytest.raises(StructuredOutputError):
        generate(client, Itinerary)
    assert FakeChatOpenAI.structured_output_count == 2


def test_client_uses_experience_profile_dto_without_confidence_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeChatOpenAI.response = FoundryExperienceProfileDTO(
        place_id="place-a",
        summary="Visitors describe heavy crowds.",
        summary_review_refs=["review_1"],
        signals=[
            FoundryExperienceSignalDTO(dimension="crowding", value="HIGH", review_refs=["review_1"])
        ],
        review_count_used=1,
    )
    client = make_client(monkeypatch)

    result = generate(client, ExperienceProfileDraft)

    assert result.place_id == "place-a"
    assert result.signals[0].value.value == "HIGH"
    assert FakeChatOpenAI.schema is FoundryExperienceProfileDTO
    assert "confidence" not in FoundryExperienceProfileDTO.model_json_schema()["properties"]
    assert FakeChatOpenAI.structured_model.invocation_count == 1


def test_client_rejects_invalid_experience_dimension_value_without_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeChatOpenAI.response = FoundryExperienceProfileDTO(
        place_id="place-a",
        summary=None,
        summary_review_refs=[],
        signals=[
            FoundryExperienceSignalDTO(
                dimension="crowding", value="ACCESSIBLE", review_refs=["review_1"]
            )
        ],
        review_count_used=1,
    )
    client = make_client(monkeypatch)
    with pytest.raises(StructuredOutputError):
        generate(client, ExperienceProfileDraft)
    assert FakeChatOpenAI.structured_model.invocation_count == 1


def test_client_fails_without_retry_after_mapping_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invalid_activity = make_activity(
        end_time=FoundryDateTimeDTO(
            date="2026-10-01",
            time="11:00",
            utc_offset="+09:00",
        )
    )
    FakeChatOpenAI.response = FoundryItineraryDTO(
        output_version="itinerary_3",
        reference_recommendations=[],
        destination="Kyoto",
        start_date="2026-10-01",
        end_date="2026-10-01",
        days=[FoundryItineraryDayDTO(date="2026-10-01", activities=[invalid_activity])],
    )
    client = make_client(monkeypatch)

    with pytest.raises(StructuredOutputError, match="must use exactly HH:MM:SS"):
        generate(client, Itinerary)

    assert FakeChatOpenAI.structured_model.invocation_count == 1


def test_client_rejects_unregistered_domain_schema_before_invocation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class UnsupportedDomainModel(BaseModel):
        value: str

    FakeChatOpenAI.response = {"value": "unused"}
    client = make_client(monkeypatch)

    with pytest.raises(StructuredOutputError, match="no transport DTO"):
        generate(client, UnsupportedDomainModel)

    assert FakeChatOpenAI.structured_output_count == 0
