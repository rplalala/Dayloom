"""Offline quality-first work limits, reuse, deadline and SDK boundaries."""

import asyncio
from datetime import date, timedelta
from pathlib import Path

import pytest

from backend.app.integrations.google.places import PLACES_DETAILS_FIELD_MASK
from backend.app.integrations.models import PlaceDetailsRequest
from backend.app.policies.acquisition_opportunities import opportunity_order
from backend.app.policies.poi_capacity import quality_capacities
from backend.app.policies.trip_dates import create_trip_date_window
from backend.app.runtime.budget import ToolBudget, ToolBudgetKey
from backend.app.runtime.config_loader import load_runtime_config_file, tool_limits
from backend.app.schemas.interpreted_requirements import ClarificationRequired
from backend.app.services.candidate_details import acquire_candidate_details
from backend.app.services.evidence_acquisition import _ProviderResult
from backend.app.services.generation_resources import GenerationResourceError, check_primary_input
from backend.app.services.planning_supply_pipeline import PlanningCandidateSupplyPipeline
from backend.tests.services.test_tripworld_discovery import details, hit, setup


def config():
    return load_runtime_config_file(Path("config/runtime.yaml"))


@pytest.mark.parametrize("days", range(1, 11))
def test_all_duration_values_and_required_expansion(days):
    start = date(2026, 9, 20)
    window = create_trip_date_window(start)
    end = start + timedelta(days=days - 1)
    c = quality_capacities(start, end, window)
    k = min(16, max(8, 2 * days + 6))
    assert (c.c_raw, c.r_pool, c.k_final, c.review_pool_cap) == (
        max(48, 4 * k),
        2 * k,
        max(k, 2 * days),
        (k + 1) // 2,
    )
    expanded = quality_capacities(start, end, window, 16)
    assert (expanded.c_raw, expanded.r_pool, expanded.k_final, expanded.review_pool_cap) == (
        64,
        32,
        max(16, 2 * days),
        8,
    )
    with pytest.raises(ClarificationRequired):
        quality_capacities(start, end, window, 17)


def acquisition(n=48):
    service, contract, dest, merged, places, runtime = setup([], n=n)
    acq = service.acq
    acq.runtime_config = config()
    limits = tool_limits(config()).model_copy(update={"max_place_detail_calls": 32})
    acq._budget = ToolBudget(limits)
    return acq, list(merged.places), places, contract, dest


@pytest.mark.parametrize(
    "failure_count,expected_sends,expected_success", [(0, 24, 24), (8, 32, 24), (20, 32, 12)]
)
def test_new_success_target_and_actual_failed_send_cap(
    failure_count, expected_sends, expected_success
):
    async def run():
        acq, rows, places, *_ = acquisition()
        places.fail = {p.candidate.place_id for p in rows[:failure_count]}
        rich, _, _ = await acquire_candidate_details(acq, rows, date(2026, 9, 23), 24)
        assert len(places.ids) == expected_sends
        assert len(rich) == expected_success
        assert acq.details_report["new_successes"] == expected_success
        assert acq.details_report["ordinary_sends"] == expected_sends

    asyncio.run(run())


def test_all_admitted_cache_is_reused_before_new_acquisition():
    async def run():
        acq, rows, places, *_ = acquisition()
        for row in rows[-16:]:
            request = PlaceDetailsRequest(
                place_id=row.candidate.place_id, field_mask=PLACES_DETAILS_FIELD_MASK
            )

            async def saved(pid=request.place_id):
                return _ProviderResult(value=details(pid))

            await acq._cache.get_or_create(acq._place_details_cache_key(request), saved)
        rich, _, _ = await acquire_candidate_details(acq, rows, date(2026, 9, 23), 24)
        assert len(rich) == 40 and len(places.ids) == 24
        assert acq.details_report["cache_qualified"] == 16
        assert not set(places.ids) & {p.candidate.place_id for p in rows[-16:]}

    asyncio.run(run())


def test_candidate_exhaustion_never_adds_queries():
    async def run():
        acq, rows, places, *_ = acquisition(15)
        rich, _, _ = await acquire_candidate_details(acq, rows, date(2026, 9, 23), 24)
        assert len(rich) == len(places.ids) == 15
        assert not places.searches

    asyncio.run(run())


def test_order_permutation_and_duplicate_links_do_not_change_opportunities():
    _, rows, _, contract, dest = acquisition(48)
    required = {rows[-1].candidate.place_id}
    expected = opportunity_order(rows, required, contract, dest)
    assert expected[0] == rows[-1].candidate.place_id
    assert expected == opportunity_order(list(reversed(rows)), required, contract, dest)
    duplicate = [r.model_copy(update={"query_hits": r.query_hits * 3}) for r in rows]
    assert expected == opportunity_order(duplicate, required, contract, dest)


def test_quality_pipeline_profile_precedes_supply_and_uses_injected_limits():
    async def run():
        acq, rows, places, contract, dest = acquisition(48)
        acq._budget = ToolBudget(tool_limits(config()))
        from backend.app.schemas.interpreted_requirements import ExperienceEvidenceRequest

        contract = contract.model_copy(
            update={
                "experience_evidence_requests": (
                    ExperienceEvidenceRequest(
                        requirement_id=contract.semantic_requirements[0].requirement_id,
                        dimension="crowding",
                    ),
                )
            }
        )

        async def observations(*args, **kwargs):
            from backend.app.services.evidence_acquisition import SearchIntentExecution

            kwargs["intent_executions"].extend(
                SearchIntentExecution(i.intent_id, "provider_success") for i in kwargs["intents"]
            )
            return rows

        acq.search_candidate_observations = observations
        from backend.tests.versions.v0.fakes import FakeStructuredLLMClient

        pipeline = PlanningCandidateSupplyPipeline(
            acq, FakeStructuredLLMClient([]), acq._tracer, "fixture"
        )
        seen = []

        async def profile(pid):
            seen.append(pid)
            from backend.app.evidence.experience_models import unavailable_profile

            return unavailable_profile(pid, "fixture")

        pipeline.candidate_acquisition.review.acquire_profile = profile
        original = pipeline.select

        async def select(*args, **kwargs):
            assert len(seen) == 6
            return await original(*args, **kwargs)

        pipeline.select = select
        # Existing fixture has directional evidence requirements.
        funnel, selection = await pipeline.run(
            contract, dest, create_trip_date_window(date(2026, 9, 19))
        )
        assert len(funnel.enriched_candidates) == 24
        assert len(selection.selected_place_ids) == 12
        assert acq._budget.limits.max_place_detail_calls == 60

    asyncio.run(run())


def test_pre_send_deadline_is_not_a_terminal_attempt(monkeypatch):
    async def run():
        acq, rows, places, *_ = acquisition(1)
        ticks = iter([0, 121, 121, 121])
        monkeypatch.setattr(
            "backend.app.services.candidate_details.perf_counter", lambda: next(ticks, 121)
        )
        rich, _, _ = await acquire_candidate_details(acq, rows, date(2026, 9, 23), 24)
        assert not rich and not places.ids and not acq._cache.attempts
        assert acq.details_report["stop"] == "deadline"

    asyncio.run(run())


def test_cancelled_sent_key_cannot_repeat_in_main_stage():
    async def run():
        acq, rows, places, *_ = acquisition(2)
        places.delay = 10
        task = asyncio.create_task(acquire_candidate_details(acq, rows, date(2026, 9, 23), 24))
        while not places.ids:
            await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert places.cancelled and "sent_incomplete" in acq._cache.attempts.values()
        places.delay = 0
        await acquire_candidate_details(acq, rows, date(2026, 9, 23), 24)
        assert places.ids.count(rows[0].candidate.place_id) == 1

    asyncio.run(run())


def test_budget_rejection_does_not_block_later_legal_send():
    async def run():
        acq, rows, places, *_ = acquisition(1)
        acq._budget.consume(ToolBudgetKey.PLACE_DETAIL_CALLS, 32)
        await acquire_candidate_details(acq, rows, date(2026, 9, 23), 24)
        assert not places.ids and not any(
            acq._cache.terminal_attempt(k) for k in acq._cache.attempts
        )
        acq._budget.set_limits(acq._budget.limits.model_copy(update={"max_place_detail_calls": 33}))
        rich, _, _ = await acquire_candidate_details(acq, rows, date(2026, 9, 23), 24)
        assert len(rich) == 1

    asyncio.run(run())


def test_resource_overflow_does_not_truncate():
    with pytest.raises(GenerationResourceError):
        check_primary_input("system", "large" * 200000, config().main_generation)


def test_rag_twenty_unique_hits_and_single_batch():
    async def run():
        service, contract, dest, merged, places, runtime = setup(
            [hit(f"rag{i}", rank=i + 1) for i in range(20)], config=config().tripworld_discovery
        )
        await service.extend(contract, dest, merged, set())
        assert service.report["resolution_attempts"] == 20
        assert service.report["details_sends"] == 20
        assert runtime.embedding_sends == 1
        assert service.report["returned_positions"] == 20 * len(service.report["queries"])

    asyncio.run(run())


def test_primary_generation_actual_sdk_parameter_and_session_capture(tmp_path):
    from backend.app.schemas.itinerary_projection import V1Itinerary
    from backend.tests.llm.azure_foundry.test_requirement_acceptance_harness import (
        ModelTransport,
        itinerary,
        settings,
    )
    from tools.validation.runtime_acceptance import AcceptanceSession

    async def run():
        transport = ModelTransport([itinerary("v1")])
        async with AcceptanceSession(
            settings=settings(), transport=transport, directory=tmp_path
        ) as session:
            session.begin_case("quality-primary")
            await session.generate_primary_structured(
                generation_config=config().main_generation,
                system_prompt="fixture",
                user_prompt="fixture",
                response_schema=V1Itinerary,
            )
            assert len(transport.requests) == 1
            assert transport.requests[0]["max_output_tokens"] == 16384
            assert len(session.calls) == 1
            assert not session.capture_errors
            assert list(tmp_path.rglob("*.json"))

    asyncio.run(run())


def test_real_transport_pre_send_failure_is_not_charged_or_cached(monkeypatch):
    import httpx

    from backend.app.integrations.google.places import GooglePlacesProvider
    from backend.app.integrations.http import HttpxJSONTransport

    real_client = httpx.AsyncClient
    sends = []

    async def handler(request):
        sends.append(request)
        return httpx.Response(503, json={"error": "fixture"})

    def broken(**kwargs):
        raise RuntimeError("dependency not ready")

    async def run():
        acq, rows, _, *_ = acquisition(1)
        acq._places = GooglePlacesProvider(
            api_key="fixture", transport=HttpxJSONTransport(), tracer=acq._tracer
        )
        monkeypatch.setattr(httpx, "AsyncClient", broken)
        rich, failures, _ = await acquire_candidate_details(acq, rows, date(2026, 9, 23), 24)
        assert not rich and not failures and not sends
        assert acq.details_report["ordinary_sends"] == 0
        assert not any(acq._cache.terminal_attempt(k) for k in acq._cache.attempts)
        monkeypatch.setattr(
            httpx,
            "AsyncClient",
            lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs),
        )
        await acquire_candidate_details(acq, rows, date(2026, 9, 23), 24)
        assert len(sends) == 1 and acq.details_report["ordinary_sends"] == 1
        assert "sent_failed" in acq._cache.attempts.values()
        await acquire_candidate_details(acq, rows, date(2026, 9, 23), 24)
        assert len(sends) == 1 and acq.details_report["ordinary_sends"] == 0

    asyncio.run(run())


def test_stage_deadline_retains_first_success_without_next_send(monkeypatch):
    async def run():
        acq, rows, places, *_ = acquisition(3)
        now = [0.0]
        monkeypatch.setattr("backend.app.services.candidate_details.perf_counter", lambda: now[0])
        original = places.get_place_details

        async def timed(request):
            result = await original(request)
            now[0] = 121
            return result

        places.get_place_details = timed
        rich, _, _ = await acquire_candidate_details(acq, rows, date(2026, 9, 23), 24)
        assert len(rich) == len(places.ids) == 1
        assert acq.details_report["stop"] == "deadline"
        assert len(acq.details_report["unprocessed_ids"]) == 2

    asyncio.run(run())


def test_quality_four_queries_and_eighty_positions_no_hidden_ten_slice():
    from backend.app.schemas.interpreted_requirements import DiscoveryIntent

    async def run():
        service, contract, dest, merged, places, runtime = setup(
            [hit(f"rag{i}", rank=i + 1) for i in range(20)], config=config().tripworld_discovery
        )
        intents = tuple(
            DiscoveryIntent(
                intent_id=f"discovery_{i + 1}",
                requirement_refs=(contract.semantic_requirements[0].requirement_id,),
                purpose="semantic_discovery",
                query_text=f"Fixture cultural discovery {i}",
            )
            for i in range(4)
        )
        contract = type(contract).model_validate(
            {**contract.model_dump(), "discovery_intents": intents}
        )
        result = await service.extend(contract, dest, merged, set())
        assert len(service.report["queries"]) == runtime.searches == 4
        assert service.report["returned_positions"] == 80
        assert service.report["resolution_attempts"] == 20
        assert len(places.ids) == 20
        assert len(result.places) == len(merged.places) + 20
        assert max(len(p.discovery_origins) for p in result.places) == 4

    asyncio.run(run())


def test_quality_routes_actual_elements_and_mirrors_are_separate():
    from backend.tests.services.test_transport_evidence import (
        PolicyRoutesProvider,
        _default_mode,
        _place,
        _requirements,
        _service,
    )

    async def run():
        ids = [chr(97 + i) for i in range(16)]
        routes = PolicyRoutesProvider(
            walk_values={(a, b): (12000, 7200, "ROUTE_EXISTS") for a in ids for b in ids if a != b}
        )
        acq, budget = _service(routes, budget_limits=tool_limits(config()))
        kwargs = dict(
            places=[_place(i) for i in ids], mode=_default_mode(), requirements=_requirements()
        )
        result = await acq.acquire_routes(**kwargs)
        baseline = [r for r in routes.requests if r.travel_mode == "WALK"]
        alternate = [r for r in routes.requests if r.travel_mode == "TRANSIT"]
        assert (
            len(baseline) == 4
            and sum(len(r.origins) * len(r.destinations) for r in baseline) == 256
        )
        elements = sum(len(r.origins) * len(r.destinations) for r in alternate)
        assert elements == 32
        assert budget.summary()["alternative_route_elements"]["used"] == elements
        assert budget.summary()["alternative_route_pairs"]["used"] == 32
        assert (
            len(
                [
                    e
                    for r in result.alternatives
                    for e in r.elements
                    if e.evidence_type == "mirrored_reverse_estimate"
                ]
            )
            == 32
        )
        before = len(routes.requests)
        await acq.acquire_routes(**kwargs)
        assert len(routes.requests) == before

    asyncio.run(run())


def test_alternative_budget_reservation_is_atomic():
    from backend.app.runtime.budget import ToolBudgetExceededError

    b = ToolBudget(tool_limits(config()))
    b.consume(
        ToolBudgetKey.ALTERNATIVE_ROUTE_ELEMENTS,
        b.limits.max_alternative_route_elements - 1,
    )
    before = b.summary()
    with pytest.raises(ToolBudgetExceededError):
        b.consume_many(
            (
                (ToolBudgetKey.ALTERNATIVE_ROUTE_PAIRS, 2),
                (ToolBudgetKey.ALTERNATIVE_ROUTE_MATRIX_CALLS, 1),
                (ToolBudgetKey.ALTERNATIVE_ROUTE_ELEMENTS, 2),
            )
        )
    assert b.summary() == before


def test_payload_fixtures_validate_under_current_guard():
    from backend.app.versions.v1.prompts import ITINERARY_GENERATION_SYSTEM_PROMPT
    from tools.diagnostics.itinerary_payload import fixtures, measure

    for d, k, long, overflow in [
        (3, 12, False, False),
        (10, 20, False, False),
        (10, 20, True, False),
    ]:
        prompt, meta = fixtures(d, k, long)
        measured = measure(
            ITINERARY_GENERATION_SYSTEM_PROMPT, prompt, config().main_generation, meta
        )
        assert measured["overflow"] == overflow
        assert measured["baseline_elements"] == k * k
        assert measured["P"] == min(8, k // 2)


def test_v1_quality_runner_injects_one_config_without_rag(monkeypatch):
    from backend.app.versions.v1.runner import run_v1
    from backend.tests.request_fixtures import make_request
    from backend.tests.services.test_transport_evidence import RecordingTracer
    from backend.tests.versions.v1.fakes import (
        FakePlacesProvider,
        FakeRoutesProvider,
        FakeWeatherProvider,
        RevisedFakeLLM,
        make_itinerary,
        make_revised_extraction,
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("V1 must not initialize RAG")

    monkeypatch.setattr("backend.app.services.tripworld_discovery.RuntimeRetrieval", forbidden)

    async def run():
        tracer = RecordingTracer()

        class Model(RevisedFakeLLM):
            async def generate_primary_structured(self, *, generation_config, **kwargs):
                assert generation_config is selected.main_generation
                return await self.generate_structured(**kwargs)

        selected = config()
        result = await run_v1(
            make_request("Plan a trip."),
            Model([make_revised_extraction(), make_itinerary()]),
            FakePlacesProvider(),
            FakeWeatherProvider(),
            FakeRoutesProvider(),
            reference_date=date(2026, 9, 11),
            runtime_config=selected,
            tracer=tracer,
            development_timeout_seconds=600,
        )
        policy = next(p for e, p in tracer.events if e == "effective_acquisition_policy")
        started = next(p for e, p in tracer.events if e == "run_started")
        assert result.generation_diagnostics.days[0].count_basis == "canonical_id"
        diagnostics_events = [p for e, p in tracer.events if e == "generation_diagnostics"]
        assert diagnostics_events == [result.generation_diagnostics.model_dump(mode="json")]
        assert policy["policy_id"] == "quality_first_1"
        assert started["runtime_config"]["tripworld_discovery"]["deadline_seconds"] == 360
        assert result.system_version.value == "v1"

    asyncio.run(run())


def test_v2_quality_runtime_receives_same_config_and_cache_reuse():
    from backend.app.versions.v2.runner import run_v2
    from backend.tests.request_fixtures import make_request
    from backend.tests.versions.v0.fakes import FakeStructuredLLMClient
    from backend.tests.versions.v1.fakes import (
        FakeRoutesProvider,
        FakeWeatherProvider,
        make_itinerary,
    )
    from backend.tests.versions.v2.test_v2_runner import Places, Retrieval

    async def run():
        selected = config()

        class Model(FakeStructuredLLMClient):
            async def generate_primary_structured(self, *, generation_config, **kwargs):
                assert generation_config is selected.main_generation
                return await self.generate_structured(**kwargs)

        llm, places = Model([make_itinerary()]), Places()
        retrieval = Retrieval([hit("aaa-rag")])
        result = await run_v2(
            make_request(),
            llm,
            places,
            FakeWeatherProvider(),
            FakeRoutesProvider(),
            reference_date=date(2026, 9, 11),
            runtime_config=selected,
            retrieval_factory=lambda: retrieval,
            development_timeout_seconds=600,
        )
        assert result.rag_discovery["config"] == selected.tripworld_discovery.model_dump()
        assert result.rag_discovery["details_sends"] == 1
        assert result.planning_supply.acquisition_diagnostics["cache_qualified"] == 1
        assert len([r for r in places.details_requests if r.place_id == "aaa-rag"]) == 1
        assert result.generation_diagnostics.days[0].count_basis == "canonical_id"
        assert result.rag_discovery["retrieval_queries"] == 1
        assert len(llm.calls) == 1

    asyncio.run(run())


def test_rag_failure_attempts_fallback_four_and_details_twenty():
    async def run():
        rows = [hit(f"bad{i}", rank=i + 1) for i in range(20)]
        service, contract, dest, merged, places, _ = setup(
            rows, config=config().tripworld_discovery
        )
        places.fail = {f"bad{i}" for i in range(20)}
        await service.extend(contract, dest, merged, set())
        assert service.report["resolution_attempts"] == 20
        assert service.report["details_sends"] == 20
        assert service.report["fallback_sends"] == 4
        assert len(places.searches) == 4
        assert len(set(places.ids)) == len(places.ids)

    asyncio.run(run())


def test_quality_rejects_incoherent_matrix():
    from backend.app.runtime.config_models import RuntimeConfig

    document = config().model_dump()
    document["budget"]["routes"]["baseline_elements_per_request"] = 32
    with pytest.raises(ValueError, match="complete initial route matrix"):
        RuntimeConfig.model_validate(document)


def test_required_extension_retains_normal_and_effective_supply_diagnostics():
    from backend.app.evidence.selection_normalization import normalize_place_details_for_selection

    async def run():
        acq, rows, _, contract, dest = acquisition(16)
        from backend.tests.versions.v0.fakes import FakeStructuredLLMClient

        pipeline = PlanningCandidateSupplyPipeline(
            acq, FakeStructuredLLMClient([]), acq._tracer, "fixture"
        )
        normal = pipeline.capacities(
            contract.requirements, create_trip_date_window(date(2026, 9, 19))
        )
        expanded = pipeline.required_capacities(normal, 16)
        rich = [
            normalize_place_details_for_selection(row, details(row.candidate.place_id))
            for row in rows
        ]
        required = {p.candidate.place_id for p in rich}
        await acq.poi_semantics.assess([p.structured_evidence for p in rich], contract)
        selected = await pipeline.select(
            contract, (), rich, required, set(), expanded, dest, {}, set(), {}, {}
        )
        assert selected.policy_result.normal_capacity == normal.k_final
        assert selected.policy_result.effective_capacity == 16
        assert len(selected.selected_place_ids) == 16

    asyncio.run(run())


def test_rag_twenty_hits_include_four_distinct_fallback_details():
    from backend.app.integrations.models import LatLng, PlaceCandidateDTO, PlaceSearchResponse

    async def run():
        service, contract, dest, merged, places, _ = setup(
            [hit(f"bad{i}", rank=i + 1) for i in range(20)], config=config().tripworld_discovery
        )
        places.fail = {f"bad{i}" for i in range(20)}

        async def fallback(request):
            places.searches.append(request)
            candidate = PlaceCandidateDTO(
                place_id=f"fallback{len(places.searches)}",
                display_name="Alias",
                provider_rank=0,
                location=LatLng(latitude=-33.86, longitude=151.2),
            )
            return PlaceSearchResponse(
                candidates=[candidate], actual_result_count=1, retrieved_at="2026-09-19T00:00:00Z"
            )

        places.search_text = fallback
        await service.extend(contract, dest, merged, set())
        assert service.report["resolution_attempts"] == 20
        assert service.report["details_sends"] == 24
        assert service.report["fallback_sends"] == 4
        assert len(set(places.ids)) == len(places.ids) == 24

    asyncio.run(run())


def test_default_input_guard_preserves_quality_limits(monkeypatch):
    from backend.app.runtime.config_loader import load_runtime_config
    from backend.app.runtime.config_models import MainGenerationConfig

    assert config().main_generation.input_tokens == 252000
    assert load_runtime_config().main_generation.input_tokens == 252000
    assert MainGenerationConfig().input_tokens == 96000
    assert config().main_generation.output_tokens == 16384
    assert config().main_generation.framing_tokens == 2048
    with pytest.raises(ValueError):
        MainGenerationConfig(input_tokens=252001)
    monkeypatch.setattr(
        "backend.app.services.generation_resources.count_tokens", lambda text: len(text)
    )
    sizing = check_primary_input("", "", config().main_generation)
    boundary = "x" * (252000 - sizing["total_tokens"])
    assert check_primary_input("", boundary, config().main_generation)["remaining"] == 0
    with pytest.raises(GenerationResourceError):
        check_primary_input("", boundary + "x", config().main_generation)
