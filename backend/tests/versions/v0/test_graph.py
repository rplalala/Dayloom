"""Tests that lock down the V0 LangGraph behavior."""

import asyncio
from datetime import date, datetime

import pytest
from pydantic import ValidationError

from backend.app.policies.trip_dates import TripDateErrorCode, TripDatePolicyError
from backend.app.schemas.interpreted_requirements import InterpretationDraft
from backend.app.schemas.itinerary import Itinerary
from backend.app.schemas.planning import SystemVersion
from backend.app.schemas.requirement_boundary import RequirementBoundaryError
from backend.app.services.preference_interpretation import empty_preference_draft
from backend.app.versions.v0.graph import (
    V0StageError,
    build_v0_graph,
)
from backend.app.versions.v0.runner import run_v0
from backend.tests.request_fixtures import make_request as shared_request
from backend.tests.versions.v0.fakes import (
    FakeStructuredLLMClient,
    make_itinerary,
    make_requirements,
)


def make_request(**kwargs):
    return shared_request(requirements=make_requirements(), **kwargs)


@pytest.mark.parametrize("mode", ["WALK", "TRANSIT", "DRIVE", None])
def test_v0_acceptance_enforces_sourced_hard_modes_without_tools(mode):
    from datetime import timedelta

    from backend.app.schemas.itinerary import Activity
    from backend.tests.services.test_hard_transport import TEXT, constrained_draft

    itinerary = make_itinerary()
    left = itinerary.days[0].activities[0]
    right = left.model_copy(
        update={
            "activity_id": "second",
            "place_name": "Another venue",
            "start_time": left.end_time + timedelta(hours=1),
            "end_time": left.end_time + timedelta(hours=2),
        }
    )
    transfer = Activity(
        activity_id="journey",
        activity_kind="transport",
        title="Estimated transfer",
        start_time=left.end_time,
        end_time=right.start_time,
        transport={
            "mode": mode,
            "from_activity_id": left.activity_id,
            "to_activity_id": right.activity_id,
        },
    )
    itinerary.days[0].activities.extend([transfer, right])
    client = FakeStructuredLLMClient([constrained_draft(), itinerary])
    invocation = run_v0(
        make_request(additional_preferences=TEXT), client, reference_date=date(2026, 9, 11)
    )
    if mode in ("WALK", "TRANSIT"):
        assert asyncio.run(invocation).itinerary == itinerary
    else:
        with pytest.raises(V0StageError) as error:
            asyncio.run(invocation)
        assert isinstance(error.value.__cause__, RequirementBoundaryError)
    assert len(client.calls) == 2


def test_v0_graph_has_exact_two_node_topology() -> None:
    graph = build_v0_graph(FakeStructuredLLMClient([])).get_graph()

    assert set(graph.nodes) == {
        "__start__",
        "extract_requirements",
        "generate_itinerary",
        "__end__",
    }
    assert {(edge.source, edge.target) for edge in graph.edges} == {
        ("__start__", "extract_requirements"),
        ("extract_requirements", "generate_itinerary"),
        ("generate_itinerary", "__end__"),
    }


def test_v0_runs_exactly_the_two_intended_structured_stages() -> None:
    client = FakeStructuredLLMClient([empty_preference_draft(), make_itinerary()])

    result = asyncio.run(
        run_v0(
            make_request(additional_preferences="Plan one day in Kyoto."),
            client,
            reference_date=date(2026, 9, 11),
        )
    )

    assert [call.response_schema for call in client.calls] == [InterpretationDraft, Itinerary]
    assert "2026-09-11" in client.calls[0].user_prompt
    assert "Kyoto" in client.calls[1].user_prompt
    assert result.system_version is SystemVersion.V0
    assert set(result.model_dump(mode="json")) == {
        "generation_diagnostics",
        "system_version",
        "requirements",
        "itinerary",
    }


@pytest.mark.parametrize("mode", ["WALK", None])
def test_v0_preserves_structured_model_transport_without_additional_stages(mode):
    raw = make_itinerary().model_dump(mode="json")
    raw["output_version"] = "itinerary_2"
    visit = raw["days"][0]["activities"][0]
    visit["activity_kind"] = "main_poi"
    visit["end_time"] = "2026-09-12T10:00:00+09:00"
    declaration = {"mode": mode, "from_activity_id": visit["activity_id"], "to_activity_id": "b"}
    travel = dict(
        visit,
        activity_id="travel",
        activity_kind="transport",
        title="Between the visits",
        start_time="2026-09-12T10:00:00+09:00",
        end_time="2026-09-12T10:20:00+09:00",
        place_name=None,
        transport=declaration,
    )
    second = dict(
        visit,
        activity_id="b",
        title="Visit another shrine",
        start_time="2026-09-12T10:30:00+09:00",
        end_time="2026-09-12T11:30:00+09:00",
    )
    raw["days"][0]["activities"] = [second, travel, visit]
    client = FakeStructuredLLMClient([empty_preference_draft(), Itinerary.model_validate(raw)])
    result = asyncio.run(
        run_v0(
            make_request(additional_preferences="Plan one day in Kyoto."),
            client,
            reference_date=date(2026, 9, 11),
        )
    )
    activities = result.model_dump(mode="json")["itinerary"]["days"][0]["activities"]
    assert [a["activity_id"] for a in activities] == [visit["activity_id"], "travel", "b"]
    assert activities[1]["transport"] == declaration
    assert result.itinerary.transfers == []
    assert result.itinerary.route_diagnostics == []
    assert [call.response_schema for call in client.calls] == [InterpretationDraft, Itinerary]
    assert client.semantic_calls == []


def test_v0_reports_missing_input_before_generation():
    client = FakeStructuredLLMClient([])
    with pytest.raises(ValidationError):
        asyncio.run(run_v0({"destination": "Kyoto"}, client, reference_date=date(2026, 9, 11)))
    assert not client.calls


def test_v0_does_not_retry_after_extraction_failure() -> None:
    client = FakeStructuredLLMClient([RuntimeError("provider failure")])

    with pytest.raises(V0StageError, match="extract_requirements") as captured:
        asyncio.run(
            run_v0(
                make_request(additional_preferences="Plan one day in Kyoto."),
                client,
                reference_date=date(2026, 9, 11),
            )
        )

    assert captured.value.stage == "extract_requirements"
    assert len(client.calls) == 1


def test_v0_does_not_retry_or_repair_after_generation_failure() -> None:
    client = FakeStructuredLLMClient([empty_preference_draft(), RuntimeError("schema failure")])

    with pytest.raises(V0StageError, match="generate_itinerary") as captured:
        asyncio.run(
            run_v0(
                make_request(additional_preferences="Plan one day in Kyoto."),
                client,
                reference_date=date(2026, 9, 11),
            )
        )

    assert captured.value.stage == "generate_itinerary"
    assert len(client.calls) == 2


def test_v0_rejects_requested_dates_outside_shared_window_before_generation() -> None:
    requirements = make_requirements().model_copy(
        update={
            "start_date": date(2026, 9, 26),
            "end_date": date(2026, 9, 26),
        }
    )
    client = FakeStructuredLLMClient([])

    with pytest.raises(TripDatePolicyError) as captured:
        asyncio.run(
            run_v0(
                shared_request(requirements=requirements),
                client,
                reference_date=date(2026, 9, 11),
            )
        )

    assert captured.value.code is TripDateErrorCode.AFTER_WINDOW
    assert len(client.calls) == 0


def test_v0_rejects_final_activity_date_outside_requested_range() -> None:
    itinerary = make_itinerary()
    activity = (
        itinerary.days[0]
        .activities[0]
        .model_copy(update={"end_time": datetime.fromisoformat("2026-09-13T01:00:00+09:00")})
    )
    day = itinerary.days[0].model_copy(update={"activities": [activity]})
    itinerary = itinerary.model_copy(update={"days": [day]})
    client = FakeStructuredLLMClient([empty_preference_draft(), itinerary])

    with pytest.raises(TripDatePolicyError) as captured:
        asyncio.run(
            run_v0(
                make_request(additional_preferences="Plan one day in Kyoto."),
                client,
                reference_date=date(2026, 9, 11),
            )
        )

    assert captured.value.code is TripDateErrorCode.ITINERARY_OUTSIDE_REQUEST
    assert len(client.calls) == 2


def test_v0_captures_the_runtime_reference_date_only_once() -> None:
    class CrossingMidnightDateProvider:
        def __init__(self) -> None:
            self.calls = 0

        def today(self) -> date:
            self.calls += 1
            return date(2026, 9, 10 + self.calls)

    date_provider = CrossingMidnightDateProvider()
    client = FakeStructuredLLMClient([empty_preference_draft(), make_itinerary()])

    result = asyncio.run(
        run_v0(
            make_request(additional_preferences="Plan one day in Kyoto."),
            client,
            date_provider=date_provider,
        )
    )

    assert result.system_version is SystemVersion.V0
    assert date_provider.calls == 1
    assert "2026-09-11" in client.calls[0].user_prompt
    assert "2026-09-11" in client.calls[1].user_prompt
