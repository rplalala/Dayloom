"""Offline stage capacity and pre-send accounting; no external providers."""

import asyncio
from time import monotonic

import pytest

from backend.app.integrations.dispatch import mark_provider_send
from backend.app.versions.v3.repair_budget import RepairBudget


def test_google_reservation_and_cross_round_terminal_failure():
    async def scenario():
        budget = RepairBudget(monotonic() + 600)
        sends = []

        async def send():
            mark_provider_send()
            sends.append(1)
            return "ok"

        for i in range(5):
            budget.round_index = i % 3 + 1
            assert (
                await budget.call(("places_search", i), send, charges={"google": 1}, observed=True)
                == "ok"
            )
        assert (
            await budget.call(("places_search", 5), send, charges={"google": 1}, observed=True)
            is None
        )
        assert budget.stops[-1] == "google_discovery_budget_exhausted"
        assert not budget.acquisition_audit[-1]["sent"]
        assert (
            await budget.call(
                ("places_search", "fallback"),
                send,
                charges={"google": 1, "fallback": 1},
                observed=True,
            )
            == "ok"
        )
        assert budget.used["google"] == 6 and budget.used["ordinary_google"] == 5
        assert len(sends) == 6
        assert (
            await budget.call(
                ("places_search", "fallback"),
                send,
                charges={"google": 1, "fallback": 1},
                observed=True,
            )
            == "ok"
        )
        assert len(sends) == 6 and budget.used["cache_hits"] == 1
        other = RepairBudget(monotonic() + 600)

        async def fail():
            mark_provider_send()
            raise ValueError("fixture failure")

        assert (
            await other.call(
                ("places_search", "failed"), fail, charges={"google": 1}, observed=True
            )
            is None
        )
        other.round_index = 2
        assert (
            await other.call(
                ("places_search", "failed"), send, charges={"google": 1}, observed=True
            )
            is None
        )
        assert other.used["google"] == 1 and other.stops[-1] == "previous_attempt"
        assert (
            await other.call(
                ("places_search", "f1"), send, charges={"google": 1, "fallback": 1}, observed=True
            )
            == "ok"
        )
        assert (
            await other.call(
                ("places_search", "f2"), send, charges={"google": 1, "fallback": 1}, observed=True
            )
            is None
        )
        assert other.stops[-1] == "google_fallback_budget_exhausted"

    asyncio.run(scenario())


def test_routes_requests_elements_and_provider_presend_are_distinct():
    async def scenario():
        async def send():
            mark_provider_send()
            return "ok"

        b = RepairBudget(monotonic() + 600)
        for i in range(24):
            assert (
                await b.call(
                    ("routes", i), send, charges={"routes": 1, "elements": 1}, observed=True
                )
                == "ok"
            )
        assert (
            await b.call(("routes", 24), send, charges={"routes": 1, "elements": 1}, observed=True)
            is None
        )
        assert b.stops[-1] == "routes_request_budget_exhausted"
        b = RepairBudget(monotonic() + 600)
        assert (
            await b.call(("routes", 0), send, charges={"routes": 1, "elements": 32}, observed=True)
            == "ok"
        )
        assert (
            await b.call(("routes", 1), send, charges={"routes": 1, "elements": 1}, observed=True)
            is None
        )
        assert b.stops[-1] == "routes_element_budget_exhausted"

        async def presend():
            raise ValueError("adapter fixture")

        assert (
            await b.call(("details", "bad"), presend, charges={"details": 1}, observed=True) is None
        )
        assert b.stops[-1] == "provider_pre_send_error"
        assert b.used["details"] == 0 and not b.acquisition_audit[-1]["sent"]
        assert b.limits["canonical"] == 30 and b.limits["details"] == 30
        for i in range(30):
            assert await b.call(("details", i), send, charges={"details": 1}, observed=True) == "ok"
        assert await b.call(("details", 31), send, charges={"details": 1}, observed=True) is None
        assert b.stops[-1] == "details_budget_exhausted"

    asyncio.run(scenario())


def test_later_input_overflow_preserves_latest_adopted(monkeypatch):
    from backend.tests.versions.v3.test_multiround import SequenceModel, edit, stage

    class Model(SequenceModel):
        async def generate_repair_structured(self, **kwargs):
            value = await super().generate_repair_structured(**kwargs)
            # Control-flow injection only; actual-tokenizer pressure sizing is separate.
            monkeypatch.setattr(
                "backend.app.versions.v3.repair_projection.count_tokens", lambda _: 100000
            )
            return value

    model = Model([[edit("10:50", "11:50")]])
    result = stage(model)
    assert model.calls == 1
    assert result.status == "ACCEPTED_PARTIAL"
    assert result.final == result.rounds[0].adopted != result.original
    assert "overflow" in result.rounds[1].result.reason


def test_canonical_attempts_are_shared_and_not_refunded():
    import pytest

    from backend.app.versions.v3.repair_budget import RepairLimit

    budget = RepairBudget(monotonic() + 600)
    for round_index in range(4):
        budget.round_index = round_index + 1
        for _ in range((8, 8, 7, 7)[round_index]):
            budget.charge(canonical=1)
    with pytest.raises(RepairLimit, match="canonical_exhausted"):
        budget.charge(canonical=1)
    assert budget.used["canonical"] == 30


def test_four_actual_rounds_share_state_and_keep_partial_when_last_rejected():
    from backend.tests.versions.v3.test_multiround import SequenceModel, edit, policy, stage

    model = SequenceModel(
        [
            [edit("10:40", "11:40")],
            [edit("10:45", "11:45")],
            [edit("10:50", "11:50")],
            [edit("10:50", "11:50")],
        ]
    )
    result = stage(model, policy=policy(max_rounds=4, max_model_calls=4))
    assert model.calls == len(result.rounds) == 4
    assert result.counters["model"] == 4
    assert result.status == "ACCEPTED_PARTIAL"
    assert result.final == result.rounds[2].adopted != result.original
    assert result.rounds[3].result.status == "REJECTED"
    assert len({r.result.material_fingerprint for r in result.rounds}) == 4
    for index, record in enumerate(result.rounds[1:], 1):
        assert record.input_itinerary == result.rounds[index - 1].adopted
        assert len(record.result.presentation_history) >= len(
            result.rounds[index - 1].result.presentation_history
        )


def test_six_round_default_stops_at_shared_call_limit():
    from backend.tests.versions.v3.test_multiround import SequenceModel, edit, stage

    model = SequenceModel(
        [[edit(f"10:{minute}", f"11:{minute}")] for minute in (31, 35, 40, 45, 50, 55)]
    )
    result = stage(model)
    assert model.calls == len(result.rounds) == result.counters["model"] == 6
    assert result.reason == "round_or_model_limit"
    assert result.status == "ACCEPTED_PARTIAL"
    assert result.final == result.rounds[-1].adopted
    assert len({r.result.timing["stage_deadline"] for r in result.rounds}) == 1
    timing = result.rounds[0].result.timing
    assert timing["round_reference_deadline"] < timing["round_deadline"]
    assert timing["model_timeout_seconds"] <= 70


def test_four_round_allocation_uses_one_stage_clock_and_reserves_recheck():
    from backend.tests.versions.v3.test_multiround import SequenceModel, edit, policy, stage

    now = [monotonic()]

    class Timed(SequenceModel):
        async def generate_repair_structured(self, **kwargs):
            value = await super().generate_repair_structured(**kwargs)
            now[0] += 40
            return value

    model = Timed(
        [
            [edit("10:40", "11:40")],
            [edit("10:45", "11:45")],
            [edit("10:50", "11:50")],
            [edit("11:00", "12:00")],
        ]
    )
    result = stage(model, clock=lambda: now[0], policy=policy(max_rounds=4, max_model_calls=4))
    assert model.calls == 4 and result.status == "ACCEPTED_COMPLETE"
    assert result.rounds[0].result.timing["model_timeout_seconds"] == 70
    assert all(30 <= r.result.timing["model_timeout_seconds"] <= 70 for r in result.rounds)
    assert result.timing["stage_remaining_seconds"] == pytest.approx(260)
    assert len({r.result.timing["stage_deadline"] for r in result.rounds}) == 1


def test_details_thirty_actual_sends_failure_cache_and_four_rounds():
    async def scenario():
        b = RepairBudget(monotonic() + 600)

        async def sent():
            mark_provider_send()
            return "ok"

        async def failed():
            mark_provider_send()
            raise ValueError("offline sent failure")

        for i in range(30):
            b.round_index = min(4, i // 8 + 1)
            await b.call(
                ("details", i), failed if i == 0 else sent, charges={"details": 1}, observed=True
            )
        assert b.round_index == 4 and b.used["details"] == 30
        assert await b.call(("details", 1), sent, charges={"details": 1}, observed=True) == "ok"
        assert await b.call(("details", 0), sent, charges={"details": 1}, observed=True) is None
        assert await b.call(("details", 30), sent, charges={"details": 1}, observed=True) is None
        assert b.used["details"] == 30 and b.used["cache_hits"] >= 1
        assert b.stops[-1] == "details_budget_exhausted"

    asyncio.run(scenario())


def test_ordinary_and_rag_details_ownership_with_shared_cache():
    import pytest

    from backend.app.integrations.google.places import PLACES_DETAILS_FIELD_MASK
    from backend.app.integrations.models import PlaceDetailsRequest
    from backend.app.runtime.budget import ToolBudgetExceededError
    from backend.app.runtime.config_loader import load_runtime_config
    from backend.app.services.tripworld_discovery import RAGStop
    from backend.tests.services.test_tripworld_discovery import setup

    async def scenario():
        rag, _, _, _, provider, _ = setup([], config=load_runtime_config().tripworld_discovery)
        from time import perf_counter

        rag.ends = perf_counter() + 360
        provider.fail.add("ordinary-0")
        for i in range(60):
            await rag.acq._get_place_details(
                PlaceDetailsRequest(place_id=f"ordinary-{i}", field_mask=PLACES_DETAILS_FIELD_MASK)
            )
        assert len(provider.ids) == 60
        assert await rag.details("ordinary-1") is not None
        assert rag.report["details_sends"] == 0
        assert await rag.details("ordinary-0") is None
        provider.fail.add("rag-0")
        for i in range(30):
            await rag.details(f"rag-{i}")
        assert rag.report["details_sends"] == 30
        with pytest.raises(RAGStop, match="details_budget"):
            await rag.details("rag-30")
        assert await rag.details("rag-1") is not None
        assert await rag.details("rag-0") is None
        with pytest.raises(ToolBudgetExceededError):
            await rag.acq._get_place_details(
                PlaceDetailsRequest(place_id="ordinary-60", field_mask=PLACES_DETAILS_FIELD_MASK)
            )
        assert len(provider.ids) == 90
        assert rag.acq._budget.summary()["place_detail_calls"]["used"] == 60

    asyncio.run(scenario())
