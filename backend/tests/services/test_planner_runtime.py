"""Offline dispatch, input admission and request resource ownership checks."""

import asyncio
from contextlib import asynccontextmanager
from datetime import date
from types import SimpleNamespace

import pytest

from backend.app.runtime.config_loader import load_runtime_config
from backend.app.schemas.planning import PlanningResult, SystemVersion
from backend.app.services import planner_runtime as module
from backend.tests.request_fixtures import make_request
from backend.tests.versions.v0.fakes import make_itinerary, make_requirements

REFERENCE = date(2026, 9, 11)


def test_real_sdk_transports_are_isolated_across_request_cleanup(monkeypatch):
    from pydantic import SecretStr

    monkeypatch.setattr(module, "V0Settings", lambda: SimpleNamespace(
        azure_openai_endpoint="https://example.invalid/v1",
        azure_openai_deployment="fixture",
        azure_openai_api_key=SecretStr("fixture-not-a-secret"),
    ))

    async def scenario():
        config = load_runtime_config()
        tracer = module.NullRunTracer(None)
        factory = module.create_planner_dependencies
        async with factory(SystemVersion.V0, config, tracer) as first:
            async with factory(SystemVersion.V0, config, tracer) as second:
                a, b = first.llm._chat_model, second.llm._chat_model
                assert a.root_async_client._client is not b.root_async_client._client
                assert a.root_client._client is not b.root_client._client
            assert b.root_async_client.is_closed()
            assert b.root_client.is_closed()
            assert not a.root_async_client.is_closed()
            assert not a.root_client.is_closed()
        async with factory(SystemVersion.V0, config, tracer) as third:
            assert not third.llm._chat_model.root_async_client.is_closed()
            assert not third.llm._chat_model.root_client.is_closed()

    asyncio.run(scenario())


def result(version):
    return PlanningResult(
        system_version=version,
        requirements=make_requirements(),
        itinerary=make_itinerary(),
    )


@pytest.mark.parametrize("version", list(SystemVersion))
def test_dispatch_uses_programmatic_runner_with_owned_dependencies(monkeypatch, version):
    events = []
    deps = module.PlannerDependencies(
        llm=object(), places=object(), weather=object(), routes=object()
    )

    @asynccontextmanager
    async def factory(selected, config, tracer):
        events.append(("open", selected, tracer.run_id))
        try:
            yield deps
        finally:
            events.append(("close", selected))

    async def runner(request, llm, *providers, **kwargs):
        assert llm is deps.llm
        assert kwargs["reference_date"] == REFERENCE
        if version != SystemVersion.V0:
            assert providers == (deps.places, deps.weather, deps.routes)
            assert kwargs["development_timeout_seconds"] == 600
            assert kwargs["runtime_config"] is config
        if version == SystemVersion.V3:
            assert kwargs["request_started_at"] <= module.monotonic()
        return result(version)

    config = load_runtime_config()
    monkeypatch.setattr(module, f"run_{version}", runner)
    runtime = module.RequestPlannerRuntime(config=config, dependency_factory=factory)
    output = asyncio.run(runtime.run(version, make_request(), reference_date=REFERENCE))
    assert output.system_version == version
    assert events[0][0] == "open" and events[-1] == ("close", version)


def test_invalid_dates_do_not_construct_dependencies():
    def forbidden(*args):
        pytest.fail("Invalid input reached provider construction")

    runtime = module.RequestPlannerRuntime(dependency_factory=forbidden)
    with pytest.raises(ValueError):
        asyncio.run(
            runtime.run(
                SystemVersion.V3,
                make_request(start_date="2027-01-01", end_date="2027-01-03"),
                reference_date=REFERENCE,
            )
        )


def test_four_concurrent_runs_have_independent_clients_and_cleanup(monkeypatch):
    opened, closed, seen = {}, [], []

    @asynccontextmanager
    async def factory(version, config, tracer):
        deps = module.PlannerDependencies(llm=object())
        opened[version] = (deps.llm, tracer.run_id)
        try:
            yield deps
        finally:
            closed.append(version)

    async def scenario():
        all_started = asyncio.Event()

        def make_runner(version):
            async def runner(*args, **kwargs):
                seen.append(version)
                if len(seen) == 4:
                    all_started.set()
                await all_started.wait()
                if version == SystemVersion.V1:
                    raise RuntimeError("One run exhausted its allowance")
                return result(version)

            return runner

        for version in SystemVersion:
            monkeypatch.setattr(module, f"run_{version}", make_runner(version))
        runtime = module.RequestPlannerRuntime(dependency_factory=factory)
        return await asyncio.gather(
            *(
                runtime.run(version, make_request(), reference_date=REFERENCE)
                for version in SystemVersion
            ),
            return_exceptions=True,
        )

    outputs = asyncio.run(scenario())
    assert isinstance(outputs[1], RuntimeError)
    assert all(isinstance(outputs[i], PlanningResult) for i in (0, 2, 3))
    assert len({id(item[0]) for item in opened.values()}) == 4
    assert len({item[1] for item in opened.values()}) == 4
    assert set(closed) == set(SystemVersion)


@pytest.mark.parametrize("termination", ["cancel", "timeout", "failure"])
def test_cleanup_on_terminal_failure(monkeypatch, termination):
    closed = []

    @asynccontextmanager
    async def factory(*args):
        try:
            yield module.PlannerDependencies(llm=object())
        finally:
            closed.append(True)

    async def scenario():
        entered = asyncio.Event()

        async def runner(*args, **kwargs):
            entered.set()
            if termination == "failure":
                raise RuntimeError("failed")
            await asyncio.Event().wait()

        monkeypatch.setattr(module, "run_v0", runner)
        # A tiny injected allowance keeps this lifecycle test fast; production config is unchanged.
        config = SimpleNamespace(
            generation_spend_usd=None,
            development_timeout_seconds=0.02 if termination == "timeout" else 5
        )
        runtime = module.RequestPlannerRuntime(config=config, dependency_factory=factory)
        task = asyncio.create_task(runtime.run("v0", make_request(), reference_date=REFERENCE))
        await entered.wait()
        if termination == "cancel":
            task.cancel()
        await task

    expected = {"cancel": asyncio.CancelledError, "timeout": TimeoutError, "failure": RuntimeError}
    with pytest.raises(expected[termination]):
        asyncio.run(scenario())
    assert closed == [True]


def test_production_factory_closes_partially_constructed_clients(monkeypatch):
    closed = []

    class Client:
        async def aclose(self):
            await asyncio.sleep(0.02)
            closed.append(True)

    settings = SimpleNamespace(
        google_maps_api_key=SimpleNamespace(get_secret_value=lambda: "fake"),
        azure_openai_api_key=SimpleNamespace(get_secret_value=lambda: "fake"),
        azure_openai_endpoint="https://example.invalid",
        azure_openai_deployment="fake",
    )
    monkeypatch.setattr(module, "V1Settings", lambda: settings)
    monkeypatch.setattr(module, "AzureFoundryStructuredLLMClient", lambda **_: Client())

    def broken(**kwargs):
        raise RuntimeError("setup failed")

    monkeypatch.setattr(module, "AzureFoundryWebEvidenceProvider", broken)

    async def scenario():
        async with module.create_planner_dependencies("v3", load_runtime_config(), None):
            pytest.fail("Incomplete dependency bundle was yielded")

    with pytest.raises(RuntimeError, match="setup failed"):
        asyncio.run(scenario())
    assert closed == [True]


def test_successful_execution_keeps_result_when_cleanup_crosses_deadline(monkeypatch):
    closed = []

    @asynccontextmanager
    async def factory(*args):
        try:
            yield module.PlannerDependencies(llm=object())
        finally:
            await asyncio.sleep(0.08)
            closed.append(True)

    async def runner(*args, **kwargs):
        return result("v0")

    monkeypatch.setattr(module, "run_v0", runner)
    runtime = module.RequestPlannerRuntime(
        config=SimpleNamespace(development_timeout_seconds=0.02, generation_spend_usd=None),
        dependency_factory=factory,
    )
    output = asyncio.run(runtime.run("v0", make_request(), reference_date=REFERENCE))
    assert output.system_version == "v0"
    assert closed == [True]


@pytest.mark.parametrize("termination", ["timeout", "failure", "cancel"])
def test_async_cleanup_finishes_before_propagating_original_outcome(monkeypatch, termination):
    closed = []

    @asynccontextmanager
    async def factory(*args):
        try:
            yield module.PlannerDependencies(llm=object())
        finally:
            await asyncio.sleep(0.03)
            closed.append(True)

    async def runner(*args, **kwargs):
        if termination == "failure":
            raise RuntimeError("original failure")
        if termination == "cancel":
            raise asyncio.CancelledError()
        await asyncio.Event().wait()

    monkeypatch.setattr(module, "run_v0", runner)
    runtime = module.RequestPlannerRuntime(
        config=SimpleNamespace(development_timeout_seconds=0.02, generation_spend_usd=None),
        dependency_factory=factory,
    )
    expected = {"timeout": TimeoutError, "failure": RuntimeError, "cancel": asyncio.CancelledError}
    with pytest.raises(expected[termination]):
        asyncio.run(runtime.run("v0", make_request(), reference_date=REFERENCE))
    assert closed == [True]


def test_repeated_cancellation_during_client_close_waits_and_closes_once():
    async def scenario():
        entered, release = asyncio.Event(), asyncio.Event()
        closed = []

        class Client:
            async def aclose(self):
                entered.set()
                await release.wait()
                closed.append(True)

        task = asyncio.create_task(module._close_client(Client()))
        await entered.wait()
        task.cancel()
        await asyncio.sleep(0)
        task.cancel()
        await asyncio.sleep(0)
        assert not task.done()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert closed == [True]

    asyncio.run(scenario())


def test_partial_setup_closes_all_clients_even_when_one_close_fails(monkeypatch):
    closed = []

    class Client:
        def __init__(self, name):
            self.name = name

        async def aclose(self):
            await asyncio.sleep(0)
            closed.append(self.name)
            if self.name == "web":
                raise RuntimeError("close failure")

    settings = SimpleNamespace(
        google_maps_api_key=SimpleNamespace(get_secret_value=lambda: "fake"),
        azure_openai_api_key=SimpleNamespace(get_secret_value=lambda: "fake"),
        azure_openai_endpoint="https://example.invalid",
        azure_openai_deployment="fake",
    )
    monkeypatch.setattr(module, "V1Settings", lambda: settings)
    monkeypatch.setattr(module, "AzureFoundryStructuredLLMClient", lambda **_: Client("llm"))
    monkeypatch.setattr(module, "AzureFoundryWebEvidenceProvider", lambda **_: Client("web"))

    def broken(*args):
        raise RuntimeError("original setup failure")

    monkeypatch.setattr(module, "SafeHTMLPageRetriever", broken)

    async def run():
        async with module.create_planner_dependencies("v3", load_runtime_config(), None):
            pytest.fail("Partial setup cannot yield dependencies")

    with pytest.raises(RuntimeError, match="original setup failure"):
        asyncio.run(run())
    assert closed == ["web", "llm"]
