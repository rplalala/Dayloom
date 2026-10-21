"""Product language policy at the provider boundary, without rewriting source data."""

import asyncio
from contextlib import asynccontextmanager
from datetime import date
from functools import partial

import pytest
from pydantic import BaseModel

from backend.app.schemas.itinerary_projection import V1Itinerary
from backend.app.services.planner_runtime import PlannerDependencies
from backend.app.services.product_language import (
    ProductEnglishClient,
    create_product_planner_dependencies,
)


class UnrelatedOutput(BaseModel):
    value: str


def test_only_new_itinerary_prose_gets_english_instruction():
    calls = []
    result = object()

    class Provider:
        async def generate_structured(self, **kwargs):
            calls.append(kwargs)
            return result

    async def scenario():
        client = ProductEnglishClient(Provider())
        for schema in (V1Itinerary, UnrelatedOutput):
            assert (
                await client.generate_structured(
                    system_prompt="Original system instructions.",
                    user_prompt='User text: "京都を歩く"; name: 清水寺; address: 京都市東山区1.',
                    response_schema=schema,
                )
                is result
            )

    asyncio.run(scenario())
    assert len(calls) == 2
    assert calls[0]["system_prompt"].startswith("Original system instructions.\n")
    assert "English" in calls[0]["system_prompt"]
    assert "verbatim" in calls[0]["system_prompt"]
    assert "do not add requirements" in calls[0]["system_prompt"]
    assert calls[1]["system_prompt"] == "Original system instructions."
    assert (
        calls[0]["user_prompt"]
        == calls[1]["user_prompt"]
        == ('User text: "京都を歩く"; name: 清水寺; address: 京都市東山区1.')
    )


def test_optional_native_calls_preserve_limits_callbacks_and_one_send():
    from backend.app.runtime.config_loader import load_runtime_config

    calls = []
    config, callback, result = load_runtime_config().main_generation, object(), object()

    class Provider:
        async def generate_structured(self, **kwargs):
            calls.append(("generic", kwargs))
            return result

        async def generate_primary_structured(self, *, generation_config, **kwargs):
            # The native primary method delegates internally to its own generic method.
            assert generation_config is config
            return await self.generate_structured(**kwargs, _generation_config=generation_config)

        async def generate_repair_structured(self, **kwargs):
            calls.append(("repair", kwargs))
            return result

    async def scenario():
        client = ProductEnglishClient(Provider())
        assert (
            await client.generate_primary_structured(
                generation_config=config,
                system_prompt="Primary",
                user_prompt="京都を歩く",
                response_schema=V1Itinerary,
            )
            is result
        )
        assert (
            await client.generate_repair_structured(
                system_prompt="Repair",
                user_prompt='{"source_evidence": "unchanged"}',
                output_tokens=4321,
                usage_callback=callback,
            )
            is result
        )

    asyncio.run(scenario())
    assert len(calls) == 2
    assert [kind for kind, _ in calls] == ["generic", "repair"]
    for _, call in calls:
        assert call["system_prompt"].count("Product writing policy:") == 1
    assert calls[0][1]["_generation_config"] is config
    assert calls[0][1]["user_prompt"] == "京都を歩く"
    assert calls[1][1]["output_tokens"] == 4321
    assert calls[1][1]["usage_callback"] is callback
    assert calls[1][1]["user_prompt"] == '{"source_evidence": "unchanged"}'


def test_absent_capabilities_and_borrowed_operations_stay_truthful():
    closed = []

    class Provider:
        model_identity = "fixture-deployment"

        async def generate_structured(self, **kwargs):
            return kwargs

        async def aclose(self):
            closed.append(True)

    client = ProductEnglishClient(Provider())
    assert not hasattr(client, "generate_primary_structured")
    assert not hasattr(client, "generate_repair_structured")
    assert client.model_identity == "fixture-deployment"
    asyncio.run(client.aclose())
    assert closed == [True]


@pytest.mark.parametrize("native_primary", [False, True])
def test_real_product_v3_and_concurrent_developer_keep_separate_prompt_policies(
    monkeypatch, native_primary
):
    from backend.app.runtime.config_loader import load_runtime_config
    from backend.app.schemas.interpreted_requirements import InterpretationDraft
    from backend.app.services.planner_runtime import RequestPlannerRuntime
    from backend.app.services.planning import DeveloperPlanningService, PlanningService
    from backend.app.services.preference_interpretation import empty_preference_draft
    from backend.app.services.product_introductions import IntroductionBatch, ProductIntroductions
    from backend.app.versions.v3 import runner
    from backend.tests.fakes import FixedDateProvider
    from backend.tests.request_fixtures import make_request
    from backend.tests.versions.v1.fakes import FakeRoutesProvider, FakeWeatherProvider
    from backend.tests.versions.v2.test_v2_runner import Places
    from backend.tests.versions.v3.test_wiring import Model, OwnedRetrieval

    models, retrievals, closed = [], [], []
    both_interpreting = None
    request = make_request("旅行を楽しむ。Keep supplied names: 清水寺, 京都市東山区1.")
    original_request = request.model_dump(mode="json")

    class RecordingModel(Model):
        def __init__(self):
            super().__init__(behavior="complete")
            self.transport_calls = []
            self.primary_limits = []
            if native_primary:
                self.generate_primary_structured = self.primary

        async def primary(self, *, generation_config, **kwargs):
            self.primary_limits.append(generation_config)
            return await self.generate_structured(**kwargs)

        async def generate_structured(self, **kwargs):
            self.transport_calls.append(("generic", kwargs))
            if kwargs["response_schema"] is InterpretationDraft:
                if len(models) == 2:
                    both_interpreting.set()
                await both_interpreting.wait()
                return empty_preference_draft()
            return await super().generate_structured(**kwargs)

        async def generate_repair_structured(self, **kwargs):
            self.transport_calls.append(("repair", kwargs))
            return await super().generate_repair_structured(**kwargs)

    def retrieval_factory(config):
        retrieval = OwnedRetrieval()
        retrievals.append(retrieval)
        return retrieval

    monkeypatch.setattr(runner, "RuntimeRetrieval", retrieval_factory)

    @asynccontextmanager
    async def dependencies(*args):
        model = RecordingModel()
        models.append(model)
        try:
            yield PlannerDependencies(
                model,
                Places(),
                FakeWeatherProvider(),
                FakeRoutesProvider(),
                llm_identity="fixture-deployment",
            )
        finally:
            closed.append(model)

    class Introductions:
        async def generate(self, places):
            return IntroductionBatch(introductions=[])

    @asynccontextmanager
    async def introductions():
        yield Introductions()

    config = load_runtime_config()
    config = config.model_copy(
        update={
            "v3_repair": config.v3_repair.model_copy(
                update={
                    "max_deletion_attempts": 0,
                    "quantity_review_enabled": False,
                }
            ),
        }
    )
    dates = FixedDateProvider(date(2026, 9, 11))
    product = PlanningService(
        RequestPlannerRuntime(
            config=config,
            dependency_factory=partial(
                create_product_planner_dependencies, dependency_factory=dependencies
            ),
        ),
        dates,
        introductions=ProductIntroductions(introductions),
    )
    developer = DeveloperPlanningService(
        RequestPlannerRuntime(config=config, dependency_factory=dependencies), dates
    )

    async def scenario():
        nonlocal both_interpreting
        both_interpreting = asyncio.Event()
        return await asyncio.gather(product.plan(request), developer.plan("v3", request))

    product_result, developer_result = asyncio.run(scenario())
    assert product_result.itinerary.days
    assert developer_result.system_version == "v3" and developer_result.v3.final_report
    assert request.model_dump(mode="json") == original_request
    assert len(closed) == len(models) == len(retrievals) == 2
    assert all(retrieval.closes == 1 for retrieval in retrievals)
    assert len(models[0].transport_calls) == len(models[1].transport_calls)
    for index, model in enumerate(models):
        interpretation = [
            call
            for stage, call in model.transport_calls
            if call.get("response_schema") is InterpretationDraft
        ]
        assert len(interpretation) == 1
        assert "Product writing policy:" not in interpretation[0]["system_prompt"]
        assert request.additional_preferences in interpretation[0]["user_prompt"]
        primary = [
            call
            for stage, call in model.transport_calls
            if call.get("response_schema") is V1Itinerary
        ]
        repair = [call for stage, call in model.transport_calls if stage == "repair"]
        assert len(primary) == 1 and 1 <= len(repair) <= 6
        for call in primary + repair:
            assert call["system_prompt"].count("Product writing policy:") == (
                1 if index == 0 else 0
            )
        assert bool(model.primary_limits) == native_primary
        if native_primary:
            assert model.primary_limits == [config.main_generation]
    assert [call["user_prompt"] for _, call in models[0].transport_calls] == [
        call["user_prompt"] for _, call in models[1].transport_calls
    ]


@pytest.mark.parametrize("identity", [None, "native-deployment"])
@pytest.mark.parametrize("termination", ["success", "failure", "cancel"])
def test_product_factory_borrows_resources_without_changing_model_identity(identity, termination):
    class Provider:
        async def generate_structured(self, **kwargs):
            return kwargs

    provider, places, config, tracer = Provider(), object(), object(), object()
    dependencies = PlannerDependencies(provider, places=places, llm_identity=identity)
    closed = []

    @asynccontextmanager
    async def factory(version, supplied_config, supplied_tracer):
        assert version == "v3" and supplied_config is config and supplied_tracer is tracer
        try:
            yield dependencies
        finally:
            closed.append(True)

    async def scenario():
        async with create_product_planner_dependencies(
            "v3", config, tracer, dependency_factory=factory
        ) as supplied:
            assert supplied.places is places
            assert supplied.llm_identity == (
                identity or f"{Provider.__module__}.{Provider.__qualname__}"
            )
            assert dependencies.llm is provider and dependencies.llm_identity is identity
            assert closed == []
            if termination == "failure":
                raise RuntimeError("fixture failure")
            if termination == "cancel":
                raise asyncio.CancelledError()

    if termination == "success":
        asyncio.run(scenario())
    else:
        with pytest.raises(RuntimeError if termination == "failure" else asyncio.CancelledError):
            asyncio.run(scenario())
    assert closed == [True]


@pytest.mark.parametrize("native_primary", [False, True])
def test_product_policy_must_fit_final_primary_input_ceiling_before_send(native_primary):
    from backend.app.runtime.config_loader import load_runtime_config
    from backend.app.services.generation_resources import (
        GenerationResourceError,
        check_primary_input,
    )

    calls = []
    config = load_runtime_config()
    system, user = "Plan itinerary.", "Preserve quoted source: 京都を歩く."
    baseline = check_primary_input(system, user, config.main_generation)
    limits = config.main_generation.model_copy(update={"input_tokens": baseline["total_tokens"]})
    config = config.model_copy(update={"main_generation": limits})
    assert check_primary_input(system, user, limits)["remaining"] == 0

    class Provider:
        async def generate_structured(self, **kwargs):
            calls.append(kwargs)
            return object()

        async def generate_primary_structured(self, *, generation_config, **kwargs):
            return await self.generate_structured(**kwargs, _generation_config=generation_config)

    client = ProductEnglishClient(Provider(), config=config)

    async def scenario():
        operation = (
            client.generate_primary_structured if native_primary else client.generate_structured
        )
        kwargs = {"generation_config": limits} if native_primary else {}
        return await operation(
            system_prompt=system, user_prompt=user, response_schema=V1Itinerary, **kwargs
        )

    with pytest.raises(GenerationResourceError, match="primary_input_resource_overflow"):
        asyncio.run(scenario())
    assert calls == []


@pytest.mark.parametrize("civil_time", [False, True])
def test_product_policy_must_fit_final_repair_input_ceiling_before_send(civil_time):
    import json

    from backend.app.llm.azure_foundry.civil_time import FoundryCivilPatchDTO
    from backend.app.llm.reference_transport import repair_references
    from backend.app.runtime.config_loader import load_runtime_config
    from backend.app.runtime.token_counting import count_tokens
    from backend.app.versions.v3.repair_projection import FoundryRepairPatchDTO, RepairInputOverflow
    from backend.model_references import INSTRUCTION

    calls = []
    config = load_runtime_config()
    system = "Propose a bounded patch."
    payload = {"editable_activities": [], "protected_activities": []}
    if civil_time:
        payload["schedule_time_context"] = {"version": "tools_civil_time_1", "places": []}
    user = json.dumps(payload)
    refs, wire_user = repair_references(user)
    schema = FoundryCivilPatchDTO if civil_time else FoundryRepairPatchDTO
    # Independent transport calculation of the previously admitted exact boundary.
    total = (
        count_tokens(system + "\n" + INSTRUCTION)
        + count_tokens(wire_user)
        + count_tokens(
            json.dumps(
                refs.constrain_schema(schema.model_json_schema()), ensure_ascii=True, sort_keys=True
            )
        )
        + config.v3_repair.input.framing_tokens
    )
    limits = config.v3_repair.input.model_copy(update={"input_tokens": total})
    config = config.model_copy(
        update={"v3_repair": config.v3_repair.model_copy(update={"input": limits})}
    )

    class Provider:
        async def generate_repair_structured(self, **kwargs):
            calls.append(kwargs)
            return object()

    client = ProductEnglishClient(Provider(), config=config)
    with pytest.raises(RepairInputOverflow) as failure:
        asyncio.run(
            client.generate_repair_structured(
                system_prompt=system, user_prompt=user, output_tokens=1234, usage_callback=object()
            )
        )
    assert failure.value.counts["total_tokens"] > limits.input_tokens
    assert failure.value.counts["input_ceiling"] == total
    assert calls == []


@pytest.mark.parametrize("native_primary", [False, True])
@pytest.mark.parametrize("enabled", [False, True])
def test_final_primary_admission_preserves_disabled_caps_and_records_effective_size(
    native_primary, enabled
):
    from backend.app.runtime.config_loader import load_runtime_config
    from backend.app.runtime.token_counting import count_tokens
    from backend.app.services.product_language import PRODUCT_WRITING_INSTRUCTION

    calls, events = [], []
    config = load_runtime_config()
    limits = config.main_generation.model_copy(
        update={"enabled": enabled, "input_tokens": 24000 if enabled else 1}
    )
    config = config.model_copy(update={"main_generation": limits})
    expected = object()

    class Provider:
        async def generate_structured(self, **kwargs):
            calls.append(kwargs)
            return expected

        async def generate_primary_structured(self, *, generation_config, **kwargs):
            assert generation_config is limits
            return await self.generate_structured(**kwargs)

    class Tracer:
        def event(self, kind, payload):
            events.append((kind, payload))

    client = ProductEnglishClient(Provider(), config=config, tracer=Tracer())
    operation = client.generate_primary_structured if native_primary else client.generate_structured
    kwargs = {"generation_config": limits} if native_primary else {}
    assert (
        asyncio.run(
            operation(
                system_prompt="Plan.",
                user_prompt="Preserve 京都.",
                response_schema=V1Itinerary,
                **kwargs,
            )
        )
        is expected
    )
    assert len(calls) == 1 and calls[0]["user_prompt"] == "Preserve 京都."
    assert len(events) == int(enabled)
    if enabled:
        assert events[0][0] == "product_primary_generation_resources"
        assert events[0][1]["system_tokens"] == count_tokens(
            "Plan.\n" + PRODUCT_WRITING_INSTRUCTION
        )
        assert events[0][1]["ceiling"] == 24000
        assert events[0][1]["remaining"] >= 0


def test_final_repair_admission_records_effective_size_and_preserves_callback():
    from backend.app.runtime.config_loader import load_runtime_config
    from backend.app.runtime.token_counting import count_tokens
    from backend.app.services.product_language import PRODUCT_WRITING_INSTRUCTION
    from backend.model_references import INSTRUCTION

    calls, events = [], []
    config, callback, expected = load_runtime_config(), object(), object()

    class Provider:
        async def generate_repair_structured(self, **kwargs):
            calls.append(kwargs)
            return expected

    class Tracer:
        def event(self, kind, payload):
            events.append((kind, payload))

    client = ProductEnglishClient(Provider(), config=config, tracer=Tracer())
    assert (
        asyncio.run(
            client.generate_repair_structured(
                system_prompt="Patch.",
                user_prompt="{}",
                output_tokens=1234,
                usage_callback=callback,
            )
        )
        is expected
    )
    assert len(calls) == 1 and calls[0]["user_prompt"] == "{}"
    assert calls[0]["output_tokens"] == 1234 and calls[0]["usage_callback"] is callback
    assert len(events) == 1 and events[0][0] == "product_repair_generation_resources"
    assert events[0][1]["system_tokens"] == count_tokens(
        "Patch.\n" + PRODUCT_WRITING_INSTRUCTION + "\n" + INSTRUCTION
    )
    assert events[0][1]["input_ceiling"] == config.v3_repair.input.input_tokens
    assert events[0][1]["total_tokens"] <= events[0][1]["input_ceiling"]
