"""Offline integration tests for the explicit V1-A graph."""

import asyncio
import json
from datetime import date
from uuid import UUID

import pytest

from backend.app.integrations.google.places import (
    PLACES_CANDIDATE_FIELD_MASK,
    PLACES_DESTINATION_FIELD_MASK,
    PLACES_DETAILS_FIELD_MASK,
)
from backend.app.observability.run_trace import NullRunTracer
from backend.app.policies.transport import select_transport_mode
from backend.app.runtime.budget import ToolBudget, ToolBudgetLimits
from backend.app.runtime.cache import RequestCache
from backend.app.schemas.interpreted_requirements import (
    InterpretationDraft as TripIntentExtractionResult,
)
from backend.app.schemas.planning import SystemVersion
from backend.app.services.evidence_acquisition import V1EvidenceAcquisitionService
from backend.app.services.preference_prompts import PREFERENCE_INTERPRETATION_SYSTEM_PROMPT
from backend.app.versions.v1.graph import build_v1_graph
from backend.app.versions.v1.runner import run_v1
from backend.tests.request_fixtures import make_request
from backend.tests.versions.v1.fakes import (
    FakePlacesProvider,
    FakeRoutesProvider,
    FakeWeatherProvider,
    make_itinerary,
    make_requirements,
)
from backend.tests.versions.v1.fakes import RevisedFakeLLM as FakeStructuredLLMClient
from backend.tests.versions.v1.fakes import (
    make_revised_extraction as make_extraction,
)

RUN_ID = UUID("00000000-0000-0000-0000-000000000001")


def _dependencies():
    llm = FakeStructuredLLMClient([make_extraction(), make_itinerary()])
    places = FakePlacesProvider()
    weather = FakeWeatherProvider()
    routes = FakeRoutesProvider()
    tracer = NullRunTracer(RUN_ID)
    service = V1EvidenceAcquisitionService(
        places_provider=places,
        weather_provider=weather,
        routes_provider=routes,
        budget=ToolBudget(),
        cache=RequestCache(),
        tracer=tracer,
    )
    return llm, places, weather, routes, tracer, service


def test_v1_graph_has_explicit_non_agentic_topology() -> None:
    llm, _, _, _, tracer, service = _dependencies()
    graph = build_v1_graph(llm, service, tracer).get_graph()

    assert set(graph.nodes) == {
        "__start__",
        "extract_requirements",
        "validate_trip_dates",
        "resolve_destination",
        "acquire_candidate_funnel",
        "acquire_weather",
        "acquire_routes",
        "acquire_and_resolve_official_web",
        "generate_evidence_informed_itinerary",
        "validate_itinerary_dates",
        "bind_actual_transfers",
        "discover_reference_recommendations",
        "__end__",
    }
    assert {(edge.source, edge.target) for edge in graph.edges} == {
        ("__start__", "extract_requirements"),
        ("acquire_routes", "acquire_and_resolve_official_web"),
        ("acquire_and_resolve_official_web", "generate_evidence_informed_itinerary"),
        ("acquire_weather", "acquire_routes"),
        ("acquire_candidate_funnel", "acquire_weather"),
        ("extract_requirements", "validate_trip_dates"),
        ("generate_evidence_informed_itinerary", "validate_itinerary_dates"),
        ("resolve_destination", "acquire_candidate_funnel"),
        ("validate_itinerary_dates", "bind_actual_transfers"),
        ("bind_actual_transfers", "discover_reference_recommendations"),
        ("discover_reference_recommendations", "__end__"),
        ("validate_trip_dates", "resolve_destination"),
    }


def test_offset_rejection_stops_before_post_generation_routes_and_nearby():
    from backend.app.schemas.itinerary_projection import V1Itinerary
    from backend.app.versions.v1.graph import V1StageError

    routes = FakeRoutesProvider()

    class ParisPlaces(FakePlacesProvider):
        async def get_place_details(self, request):
            result = await super().get_place_details(request)
            return result.model_copy(update={"time_zone": "Europe/Paris"})

    class Model(FakeStructuredLLMClient):
        async def generate_structured(self, **kwargs):
            if kwargs["response_schema"] is V1Itinerary:
                self.before_routes = len(routes.requests)
                self.before_searches = len(places.search_requests)
            return await super().generate_structured(**kwargs)

    places = ParisPlaces()
    model = Model([make_extraction(), make_itinerary()])
    with pytest.raises(V1StageError):
        asyncio.run(
            run_v1(
                make_request(additional_preferences="Plan two days in Sydney."),
                model,
                places,
                FakeWeatherProvider(),
                routes,
                reference_date=date(2026, 9, 11),
            )
        )
    assert len(routes.requests) == model.before_routes
    assert len(places.search_requests) == model.before_searches
    assert len(model.calls) == 2


def test_v1_full_offline_run_uses_normalized_evidence_and_fixed_masks() -> None:
    llm, places, weather, routes, tracer, _ = _dependencies()

    result = asyncio.run(
        run_v1(
            make_request(additional_preferences="Plan two days in Sydney."),
            llm,
            places,
            weather,
            routes,
            reference_date=date(2026, 9, 11),
            tracer=tracer,
        )
    )

    assert result.system_version is SystemVersion.V1
    assert len(llm.calls) == 2
    assert llm.calls[0].system_prompt == PREFERENCE_INTERPRETATION_SYSTEM_PROMPT
    assert llm.calls[0].response_schema is TripIntentExtractionResult
    assert places.search_requests[0].field_mask == PLACES_DESTINATION_FIELD_MASK
    assert places.search_requests[0].include_future_opening_businesses is False
    assert all(
        request.field_mask == PLACES_CANDIDATE_FIELD_MASK
        and request.include_future_opening_businesses
        for request in places.search_requests[1:]
    )
    assert all(
        request.field_mask == PLACES_DETAILS_FIELD_MASK for request in places.details_requests
    )
    assert len(places.search_requests) == 4
    assert len(places.details_requests) == 9
    assert len(weather.requests) == 1
    assert weather.requests[0].requested_start == date(2026, 9, 12)
    assert weather.requests[0].requested_end == date(2026, 9, 13)
    baseline = [r for r in routes.requests if r.travel_mode == "WALK"]
    assert len(baseline) == 2
    assert sum(len(r.origins) * len(r.destinations) for r in baseline) == 81
    assert len(result.planning_supply.selected_place_ids) == 9
    assert routes.requests[0].travel_mode == "WALK"
    assert routes.requests[0].routing_preference is None
    generation_prompt = llm.calls[-1].user_prompt
    generation_system_prompt = llm.calls[-1].system_prompt
    assert "Do not generate transport activities" in generation_system_prompt
    assert "transport for a transfer" not in generation_system_prompt
    assert "place_evidence" not in generation_prompt
    assert '"places"' in generation_prompt
    assert '"precipitation_probability_percent": 70' in generation_prompt
    assert '"mode": "WALK"' in generation_prompt
    assert '"directed_facts"' in generation_prompt
    assert '"projection_version": "primary_mixed_routes_1"' in generation_prompt
    assert "provider_observed" in generation_system_prompt
    assert "mirrored_reverse_estimate" in generation_system_prompt
    assert "schedule the entire visit within them" in " ".join(generation_system_prompt.split())
    assert "Never reuse another pair's measurement" in " ".join(generation_system_prompt.split())
    assert "forecastDays" not in generation_prompt
    assert "currentOpeningHours" not in generation_prompt
    assert '"rating"' not in generation_prompt
    assert "<official_current_evidence>" not in generation_prompt


def test_dated_visit_count_reaches_primary_generation_as_json():
    from backend.app.schemas.itinerary_projection import V1Itinerary
    from backend.tests.services.test_daily_visit_constraints import TEXT, counted_draft

    llm = FakeStructuredLLMClient([counted_draft(), make_itinerary()])
    result = asyncio.run(
        run_v1(
            make_request(TEXT),
            llm,
            FakePlacesProvider(),
            FakeWeatherProvider(),
            FakeRoutesProvider(),
            reference_date=date(2026, 9, 11),
        )
    )

    generation = next(call for call in llm.calls if call.response_schema is V1Itinerary)
    supply = json.loads(generation.user_prompt.split("Planning candidate supply contract:\n", 1)[1])
    assert supply["daily_visit_constraints"] == [
        {
            "constraint_id": "daily_visit_1",
            "date": "2026-09-12",
            "mode": "exact",
            "count": 1,
            "strength": "hard",
            "requirement_refs": ["semantic_1"],
        }
    ]
    assert result.system_version is SystemVersion.V1


def test_shared_generation_rejects_model_transport_before_transfer_binding():
    llm, places, weather, routes, tracer, _ = _dependencies()
    original = make_itinerary()
    original.days[0].activities[0].activity_kind = "transport"
    llm = FakeStructuredLLMClient([make_extraction(), original])
    from backend.app.versions.v1.graph import V1StageError

    with pytest.raises(V1StageError) as error:
        asyncio.run(
            run_v1(
                make_request(additional_preferences="Plan two days in Sydney."),
                llm,
                places,
                weather,
                routes,
                reference_date=date(2026, 9, 11),
                tracer=tracer,
            )
        )
    assert "transport activities" in str(error.value.__cause__)


def test_v1_weather_failure_is_explicit_and_does_not_block_generation() -> None:
    llm = FakeStructuredLLMClient([make_extraction(), make_itinerary()])
    places = FakePlacesProvider()
    weather = FakeWeatherProvider(failure=True)
    routes = FakeRoutesProvider()

    result = asyncio.run(
        run_v1(
            make_request(additional_preferences="Plan two days in Sydney."),
            llm,
            places,
            weather,
            routes,
            reference_date=date(2026, 9, 11),
            tracer=NullRunTracer(RUN_ID),
        )
    )

    assert result.system_version is SystemVersion.V1
    assert '"availability": "unavailable"' in llm.calls[-1].user_prompt
    assert "Weather unavailable" in llm.calls[-1].user_prompt


def test_v1_legacy_route_matrix_budget_does_not_bound_active_selection() -> None:
    from backend.app.runtime.config_loader import load_runtime_config
    from backend.app.runtime.config_models import AcquisitionConfig

    llm = FakeStructuredLLMClient([make_extraction(), make_itinerary()])
    places = FakePlacesProvider()
    weather = FakeWeatherProvider()
    routes = FakeRoutesProvider()

    asyncio.run(
        run_v1(
            make_request(additional_preferences="Plan two days in Sydney."),
            llm,
            places,
            weather,
            routes,
            reference_date=date(2026, 9, 11),
            runtime_config=load_runtime_config().model_copy(
                update={"acquisition": AcquisitionConfig(policy_id="conservative_1")}
            ),
            budget_limits=ToolBudgetLimits(max_route_matrix_elements=16),
            tracer=NullRunTracer(RUN_ID),
        )
    )

    assert len(places.details_requests) == 9
    assert len(routes.requests[0].origins) == 6
    assert len(routes.requests[0].origins) * len(routes.requests[0].destinations) == 36


def test_v1_captures_reference_date_once_across_midnight() -> None:
    class CrossingMidnightDateProvider:
        def __init__(self) -> None:
            self.calls = 0

        def today(self) -> date:
            self.calls += 1
            return date(2026, 9, 10 + self.calls)

    provider = CrossingMidnightDateProvider()
    llm, places, weather, routes, tracer, _ = _dependencies()

    asyncio.run(
        run_v1(
            make_request(additional_preferences="Plan two days in Sydney."),
            llm,
            places,
            weather,
            routes,
            date_provider=provider,
            tracer=tracer,
        )
    )

    assert provider.calls == 1
    assert '"reference_date": "2026-09-11"' in llm.calls[0].user_prompt
    assert "Reference date: 2026-09-11" in llm.calls[-1].user_prompt


def test_v1_rejects_trip_outside_shared_window_before_any_provider_call() -> None:
    requirements = make_requirements().model_copy(
        update={"start_date": date(2026, 9, 26), "end_date": date(2026, 9, 26)}
    )
    llm = FakeStructuredLLMClient([make_extraction(requirements)])
    places = FakePlacesProvider()

    with pytest.raises(ValueError):
        asyncio.run(
            run_v1(
                make_request(additional_preferences="Plan later.", requirements=requirements),
                llm,
                places,
                FakeWeatherProvider(),
                FakeRoutesProvider(),
                reference_date=date(2026, 9, 11),
                tracer=NullRunTracer(RUN_ID),
            )
        )

    assert places.search_requests == []


def test_v1_rejects_final_itinerary_dates_outside_requested_range() -> None:
    itinerary = make_itinerary().model_copy(update={"end_date": date(2026, 9, 14)})
    llm = FakeStructuredLLMClient([make_extraction(), itinerary])

    with pytest.raises(ValueError):
        asyncio.run(
            run_v1(
                make_request(additional_preferences="Plan two days in Sydney."),
                llm,
                FakePlacesProvider(),
                FakeWeatherProvider(),
                FakeRoutesProvider(),
                reference_date=date(2026, 9, 11),
                tracer=NullRunTracer(RUN_ID),
            )
        )

    assert len(llm.calls) == 2


def test_individual_place_details_failure_continues_with_partial_evidence() -> None:
    llm = FakeStructuredLLMClient([make_extraction(), make_itinerary()])
    places = FakePlacesProvider(details_failure_ids={"poi-0-0"})

    result = asyncio.run(
        run_v1(
            make_request(additional_preferences="Plan two days in Sydney."),
            llm,
            places,
            FakeWeatherProvider(),
            FakeRoutesProvider(),
            reference_date=date(2026, 9, 11),
            tracer=NullRunTracer(RUN_ID),
        )
    )

    assert result.system_version is SystemVersion.V1
    assert "poi-0-0" not in llm.calls[-1].user_prompt
    assert "Place Details unavailable" not in llm.calls[-1].user_prompt


def test_request_scoped_cache_deduplicates_details_weather_and_routes() -> None:
    places = FakePlacesProvider()
    weather = FakeWeatherProvider()
    routes = FakeRoutesProvider()
    budget = ToolBudget()
    service = V1EvidenceAcquisitionService(
        places_provider=places,
        weather_provider=weather,
        routes_provider=routes,
        budget=budget,
        cache=RequestCache(),
        tracer=NullRunTracer(RUN_ID),
    )
    requirements = make_requirements()

    async def scenario():
        destination = await service.resolve_destination("Sydney")
        repeated_destination = await service.resolve_destination("Sydney")
        from backend.app.evidence.normalization import normalize_place_details
        from backend.app.evidence.selection_models import PlaceSearchIntent
        from backend.app.integrations.google.places import PLACES_DETAILS_FIELD_MASK
        from backend.app.integrations.models import PlaceDetailsRequest

        intents = tuple(
            PlaceSearchIntent(intent_id=str(i), term=t, query=f"{t} in Sydney", kind="fallback")
            for i, t in enumerate(("museums", "parks", "food"))
        )
        candidates = await service.search_candidate_observations(
            requirements, destination, intents=intents
        )
        shortlist = candidates[:2]

        async def details():
            return [
                normalize_place_details(
                    (
                        await service._get_place_details(
                            PlaceDetailsRequest(
                                place_id=p.candidate.place_id, field_mask=PLACES_DETAILS_FIELD_MASK
                            )
                        )
                    ).value,
                    candidate=p.candidate,
                )
                for p in shortlist
            ]

        first_places = await details()
        second_places = await details()
        first_weather = await service.acquire_weather(
            requirements=requirements,
            destination=destination,
            reference_date=date(2026, 9, 11),
        )
        second_weather = await service.acquire_weather(
            requirements=requirements,
            destination=destination,
            reference_date=date(2026, 9, 11),
        )
        mode = select_transport_mode(
            make_request(additional_preferences="Plan Sydney."), requirements
        )
        first_routes = await service.acquire_routes(
            places=first_places,
            mode=mode,
            requirements=requirements,
        )
        second_routes = await service.acquire_routes(
            places=first_places,
            mode=mode,
            requirements=requirements,
        )
        return (
            destination,
            repeated_destination,
            first_places,
            second_places,
            first_weather,
            second_weather,
            first_routes,
            second_routes,
        )

    results = asyncio.run(scenario())

    assert results[0] == results[1]
    assert results[2] == results[3]
    assert results[4] == results[5]
    assert results[6] == results[7]
    assert len(places.search_requests) == 4
    assert len(places.details_requests) == 2
    assert len(weather.requests) == 1
    assert len(routes.requests) == 1
    assert budget.summary()["place_detail_calls"]["used"] == 2
    assert budget.summary()["weather_calls"]["used"] == 1
    assert budget.summary()["baseline_route_matrix_elements"]["used"] == 4
    assert budget.summary()["baseline_route_matrix_calls"]["used"] == 1
    assert budget.summary()["alternative_route_pairs"]["used"] == 0
    assert budget.summary()["alternative_route_matrix_calls"]["used"] == 0
