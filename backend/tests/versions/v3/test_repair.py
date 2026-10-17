"""Offline single-round repair behavior; no graph or real provider instances."""

import asyncio
import json
from datetime import timedelta
from time import monotonic

import pytest

from backend.app.evidence.models import RouteEvidence
from backend.app.evidence.selection_normalization import normalize_place_search_hit
from backend.app.integrations.dispatch import mark_provider_send
from backend.app.integrations.models import PlaceCandidateDTO, PlaceDetailsDTO, RouteMatrixDTO
from backend.app.runtime.cache import RequestCache
from backend.app.services.evidence_acquisition import _ProviderResult
from backend.app.versions.v3.models import ValidationPolicy
from backend.app.versions.v3.repair_acceptance import assess
from backend.app.versions.v3.repair_budget import RepairBudget, RepairLimit
from backend.app.versions.v3.repair_candidates import prepare_candidates
from backend.app.versions.v3.repair_models import RepairScope, ValidationContext
from backend.app.versions.v3.repair_routes import bind_transitions, check_transitions
from backend.app.versions.v3.repair_service import run_repair_once
from backend.tests.versions.v3.test_validation import (
    DAY,
    NOW,
    WINDOW,
    activity,
    binding,
    contract,
    draft,
    place,
)


def context(requirements=None, **changes):
    return ValidationContext(
        **{
            "contract": requirements or contract(),
            "window": WINDOW,
            "original_supply_ids": ("a", "b", "c"),
            "places": (place(), place("b"), place("c")),
            "policy": ValidationPolicy(review_targets={"coverage"}),
            **changes,
        }
    )


def overlap_draft():
    return draft([activity(end="11:00"), activity("two", "b", "10:30", "11:30")])


def scope_for(original, ctx, check="overlap", operations=("retime",), **changes):
    report = assess(original, ctx)
    targets = tuple(f.finding_id for f in report.findings if f.check == check)
    return RepairScope(
        **{
            "dates": (DAY,),
            "permissions": ({"activity_id": "two", "operations": operations},)
            if check == "overlap"
            else (),
            "target_ids": targets,
            **changes,
        }
    )


def edit(start="11:00", end="12:00", operation="retime", **changes):
    return {
        "operation": operation,
        "activity_id": "two",
        "date": str(DAY),
        "place_id": None,
        "start_time": f"{DAY}T{start}:00+00:00" if start else None,
        "end_time": f"{DAY}T{end}:00+00:00" if end else None,
        **changes,
    }


class Model:
    def __init__(self, edits=None, error=None):
        self.edits, self.error, self.calls = edits if edits is not None else [edit()], error, 0

    async def generate_repair_structured(self, **kwargs):
        self.calls += 1
        self.system_prompt = kwargs["system_prompt"]
        self.input = json.loads(kwargs["user_prompt"])
        if self.error:
            raise self.error
        return {"edits": self.edits}


def exploring_budget():
    budget = RepairBudget(monotonic() + 600)
    budget.explore_feedback = True
    return budget


def run(original=None, ctx=None, scope=None, model=None, **kwargs):
    original = original or overlap_draft()
    ctx = ctx or context()
    return asyncio.run(
        run_repair_once(
            original,
            ctx,
            scope or scope_for(original, ctx),
            model=model or Model(),
            request_deadline=kwargs.pop("request_deadline", monotonic() + 300),
            **kwargs,
        )
    )


def selection(pid):
    return normalize_place_search_hit(
        PlaceCandidateDTO(
            place_id=pid,
            display_name=pid,
            location={"latitude": 0, "longitude": 0},
            provider_rank=0,
        ),
        intent_id="intent_1",
        source_query="Museum",
        actual_result_count=1,
    )


class Places:
    observes_send_boundary = True

    def __init__(self, fail=False, before_send=False):
        self.calls, self.fail, self.before_send = 0, fail, before_send

    async def get_place_details(self, request):
        if self.before_send:
            raise RuntimeError("dependency unavailable")
        mark_provider_send()
        self.calls += 1
        if self.fail:
            raise RuntimeError("provider failed")
        return PlaceDetailsDTO(
            place_id=request.place_id,
            display_name=request.place_id,
            location={"latitude": 0, "longitude": 0},
            business_status="OPERATIONAL",
            time_zone="UTC",
            retrieved_at=NOW.isoformat(),
        )


class Routes:
    observes_send_boundary = True

    def __init__(self, duration=0, fail=False):
        self.calls, self.duration, self.fail = [], duration, fail

    async def compute_route_matrix(self, request):
        mark_provider_send()
        self.calls.append(request)
        if self.fail:
            raise RuntimeError("route unavailable")
        return RouteMatrixDTO(
            retrieved_at=NOW.isoformat(),
            elements=[
                {
                    "originIndex": 0,
                    "destinationIndex": 0,
                    "condition": "ROUTE_EXISTS",
                    "duration": f"{self.duration}s",
                    "status": {},
                }
            ],
        )


def test_time_only_repair_needs_no_new_candidates_and_preserves_protected_fields():
    original = overlap_draft()
    before = original.model_dump_json()
    provider = Places()
    result = run(original=original, places_provider=provider)
    assert result.status == "ACCEPTED_COMPLETE", result.reason
    assert result.target_progress[0].outcome == "resolved"
    assert result.target_progress[0].before == 1800
    assert result.target_progress[0].after == 0
    assert result.final.days[0].activities[0] == original.days[0].activities[0]
    assert original.model_dump_json() == before
    assert provider.calls == 0 and result.counters["model"] == 1
    assert result.original_supply_ids == ("a", "b", "c")
    assert result.final_place_ids == ("a", "b")


@pytest.mark.parametrize("strategy", ["local", "replan"])
@pytest.mark.parametrize("allow_duration_change", [False, True])
def test_two_hour_retime_exposes_duration_and_respects_permission(strategy, allow_duration_change):
    original = draft([activity(start="09:00", end="11:00"), activity("two", "b", "10:00", "12:00")])
    ctx = context()
    scope = scope_for(
        original,
        ctx,
        permissions=(
            {
                "activity_id": "two",
                "operations": ("retime",),
                "allow_duration_change": allow_duration_change,
            },
        ),
    )

    class DurationAwareModel(Model):
        async def generate_repair_structured(self, **kwargs):
            payload = json.loads(kwargs["user_prompt"])
            assert payload["editable_activities"][0]["duration_seconds"] == 7200
            assert (
                payload["scope"]["permissions"][0]["allow_duration_change"] is allow_duration_change
            )
            return await super().generate_repair_structured(**kwargs)

    end = "12:05" if allow_duration_change else "13:05"
    model = DurationAwareModel([edit("11:05", end)])
    result = run(
        original=original,
        ctx=ctx,
        scope=scope,
        model=model,
        routes_provider=Routes(duration=300),
        proposal_strategy=strategy,
    )
    assert result.status == "ACCEPTED_COMPLETE", result.reason
    assert result.target_progress[0].before == 3600
    assert result.target_progress[0].after == 0
    assert result.final.days[0].activities[0] == original.days[0].activities[0]
    before, after = original.days[0].activities[1], result.final.days[0].activities[1]
    assert (
        after.activity_id == before.activity_id and after.source_place_id == before.source_place_id
    )
    assert (after.end_time - after.start_time).total_seconds() == (
        3600 if allow_duration_change else 7200
    )
    assert original.days[0].activities[1].start_time.hour == 10
    assert model.calls == 1


def test_repair_keeps_transport_application_owned():
    model = Model()
    result = run(model=model)
    assert result.status == "ACCEPTED_COMPLETE"
    assert "Do not add transport activities" in model.system_prompt
    assert "Do not edit transfers directly" in model.system_prompt
    assert all(a.activity_kind != "transport" for d in result.final.days for a in d.activities)


@pytest.mark.parametrize("extra", [{"activity_kind": "transport"}, {"travel_mode": "DRIVE"}])
def test_repair_rejects_model_authored_transport_fields(extra):
    original = overlap_draft()
    result = run(original=original, model=Model([{**edit(), **extra}]))
    assert result.status == "REJECTED"
    assert result.final == original


def test_partial_overlap_improvement_retains_confirmed_conflict():
    result = run(model=Model([edit("10:50", "11:50")]))
    assert result.status == "ACCEPTED_PARTIAL", result.reason
    assert result.target_progress[0].outcome == "improved"
    assert result.target_progress[0].after == 600
    assert any(
        f.check == "overlap" and f.status == "CONFIRMED" for f in result.proposed_report.findings
    )


@pytest.mark.parametrize(
    "change,reason",
    [
        (edit(operation="delete", start=None, end=None), "Unauthorized operation"),
        (edit(end="11:30"), "Duration change"),
        (edit(activity_id="one"), "Unauthorized operation"),
        (edit(date=str(DAY + timedelta(days=1))), "Unauthorized date"),
        (edit(place_id="invented"), "Retime cannot change identity"),
        ({**edit(), "activity_kind": "free_time"}, "extra_forbidden"),
        ({**edit(), "notes": "Fixed"}, "extra_forbidden"),
    ],
)
def test_unauthorized_operations_rejected_before_post_routes(change, reason):
    result = run(model=Model([change]))
    assert result.status == "REJECTED"
    assert reason in result.reason
    assert result.final == result.original


def test_explicit_deletion_requires_coverage_permission_and_records_loss():
    original, ctx = overlap_draft(), context()
    scope = scope_for(original, ctx, operations=("delete",))
    model = Model([edit(operation="delete", start=None, end=None)])
    assert "Coverage regression" in run(scope=scope, model=model).reason
    scope = scope.model_copy(update={"allow_coverage_regression": True})
    result = run(scope=scope, model=Model(model.edits))
    assert result.status == "REJECTED", result.reason
    assert result.final == original
    assert result.main_visits_lost == ("two",) and result.coverage_regressions == (DAY,)
    assert any(
        f.check == "coverage" and f.status == "NEEDS_REVIEW"
        for f in result.proposed_report.findings
    )


def test_authorized_duration_change_is_possible_without_minimum_duration_rule():
    original, ctx = overlap_draft(), context()
    scope = scope_for(
        original,
        ctx,
        permissions=(
            {"activity_id": "one", "operations": ("retime",), "allow_duration_change": True},
        ),
    )
    result = run(scope=scope, model=Model([edit("10:00", "10:30", activity_id="one")]))
    assert result.status == "ACCEPTED_COMPLETE", result.reason


@pytest.mark.parametrize("edits", [[], [edit("10:30", "11:30")]])
def test_noop_and_no_improvement_rejected(edits):
    result = run(model=Model(edits))
    assert result.status == "REJECTED" and "No verifiable" in result.reason


def test_new_conflict_is_rejected():
    original = overlap_draft()
    original.days[0].activities.append(activity("three", "c", "12:00", "13:00"))
    result = run(original=original, model=Model([edit("12:00", "13:00")]))
    assert result.status == "REJECTED" and "New confirmed conflict" in result.reason


def test_optional_details_failure_and_exhaustion_do_not_abort_time_repair():
    original, ctx, provider = overlap_draft(), context(), Places(fail=True)
    scope = scope_for(original, ctx, operations=("retime", "replace"))
    result = run(
        budget=exploring_budget(),
        scope=scope,
        places_provider=provider,
        pool=tuple(selection(str(i)) for i in range(31)),
    )
    assert result.status == "ACCEPTED_COMPLETE", result.reason
    assert provider.calls == 30 and result.counters["details"] == 30
    assert result.counters["canonical"] == 30
    assert "canonical_budget_exhausted" in result.stops


def test_new_qualified_candidate_outside_original_supply_can_be_added():
    original, ctx = draft(), context()
    scope = scope_for(original, ctx, check="coverage", add_dates=(DAY,))
    result = run(
        budget=exploring_budget(),
        original=original,
        ctx=ctx,
        scope=scope,
        places_provider=Places(),
        pool=(selection("new"),),
        model=Model([edit("12:00", "13:00", operation="add", activity_id=None, place_id="new")]),
    )
    assert result.status == "ACCEPTED_COMPLETE", result.reason
    assert "new" not in result.original_supply_ids and "new" in result.final_place_ids
    assert (
        next(c for c in result.repair_whitelist if c.place.place_id == "new").origin == "discovered"
    )
    assert all(
        f.status == "UNKNOWN"
        for f in result.proposed_report.findings
        if f.check == "visitor_suitability"
    )


def test_required_visit_cannot_be_deleted_and_excluded_cannot_be_added():
    original = overlap_draft()
    ctx = context(contract("REQUIRED"), named_resolutions=(binding("b"),))
    scope = scope_for(original, ctx, operations=("delete",), allow_coverage_regression=True)
    result = run(
        ctx=ctx, scope=scope, model=Model([edit(operation="delete", start=None, end=None)])
    )
    assert result.status == "REJECTED" and "REQUIRED" in result.reason
    ctx = context(contract("EXCLUDED"), named_resolutions=(binding("c"),))
    scope = scope_for(original, ctx, operations=("replace",))
    result = run(ctx=ctx, scope=scope, model=Model([edit(operation="replace", place_id="c")]))
    assert result.status == "REJECTED" and "excluded" in result.reason


def test_model_error_no_retry_and_cancellation_propagates():
    model = Model(error=RuntimeError("bad response"))
    result = run(model=model)
    assert result.status == "REJECTED" and model.calls == 1 and result.final == result.original
    with pytest.raises(asyncio.CancelledError):
        run(model=Model(error=asyncio.CancelledError()))


def test_deadline_reserves_nearby_and_rechecks():
    model = Model()
    result = run(model=model, clock=lambda: 100, request_deadline=125)
    assert result.status == "SKIPPED" and model.calls == 0
    assert RepairBudget(1000, clock=lambda: 100).deadline == 520
    assert RepairBudget(150, clock=lambda: 100).deadline == 140


def test_budget_actual_sends_cache_failed_attempts_and_matrix_elements():
    async def scenario():
        budget = RepairBudget(monotonic() + 300)
        calls = []

        async def send():
            mark_provider_send()
            calls.append(1)
            return "value"

        args = dict(charges={"routes": 1, "elements": 16}, observed=True)
        assert await budget.call(("route", 1), send, **args) == "value"
        assert await budget.call(("route", 1), send, **args) == "value"
        assert await budget.call(("route", 2), send, **args) == "value"
        assert await budget.call(("route", 3), send, **args) is None
        assert len(calls) == 2 and budget.used["elements"] == 32 and budget.used["routes"] == 2
        assert budget.used["cache_hits"] == 1
        with pytest.raises(RepairLimit):
            budget.charge(google=7)
        assert budget.used["google"] == 0

    asyncio.run(scenario())


def test_cached_details_and_previous_failure_do_not_resend():
    async def scenario():
        budget = exploring_budget()
        provider = Places()
        original, ctx = overlap_draft(), context()
        scope = scope_for(original, ctx, operations=("replace", "retime"))
        candidates = (selection("new"), selection("new"))
        first = await prepare_candidates(
            ctx, scope, budget, original=original, pool=candidates, provider=provider
        )
        assert len(first.ledger) == 4 and provider.calls == 1
        second = await prepare_candidates(
            ctx.model_copy(update={"identity_ledger": first.ledger}),
            scope,
            budget,
            original=original,
            pool=candidates,
            provider=provider,
        )
        assert len(second.ledger) == 4 and provider.calls == 1
        assert budget.used["details"] == 1
        cache = RequestCache()
        cache._values[("cached",)] = _ProviderResult(value="existing")
        budget = RepairBudget(monotonic() + 300, cache=cache)

        async def fail():
            raise AssertionError("must not send")

        assert (
            await budget.call(("cached",), fail, charges={"details": 1}, unwrap=True) == "existing"
        )
        assert budget.used["details"] == 0

    asyncio.run(scenario())


def route(duration=60, **changes):
    return RouteEvidence(
        **{
            "travel_mode": "TRANSIT",
            "mode_reason": "test",
            "representative_departure_time": activity().end_time,
            "availability": "available",
            "retrieved_at": NOW,
            "source_ref": "route:test",
            "elements": [
                {
                    "origin_place_id": "a",
                    "destination_place_id": "b",
                    "condition": "ROUTE_EXISTS",
                    "status": "OK",
                    "duration_seconds": duration,
                    "availability": "available",
                }
            ],
            **changes,
        }
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"travel_mode": "DRIVE"},
        {"representative_departure_time": NOW},
        {"representative_departure_time": None},
        {"routing_preference": "TRAFFIC_AWARE"},
        {
            "elements": [
                {
                    "origin_place_id": "b",
                    "destination_place_id": "a",
                    "availability": "available",
                    "condition": "ROUTE_EXISTS",
                    "status": "OK",
                    "duration_seconds": 10,
                }
            ]
        },
        {
            "elements": [
                {
                    "origin_place_id": "a",
                    "destination_place_id": "b",
                    "availability": "available",
                    "condition": "ROUTE_EXISTS",
                    "status": "OK",
                    "duration_seconds": 10,
                    "evidence_type": "mirrored_reverse_estimate",
                }
            ]
        },
    ],
)
def test_route_applicability_never_assumed(changes):
    original = draft([activity(), activity("two", "b", "12:00", "13:00")])
    values = list(
        check_transitions(original, bind_transitions(original, "TRANSIT"), (route(**changes),))
    )
    assert values[0]["status"] == "UNKNOWN"


def test_route_sufficient_evidence_pass_and_conflict():
    original = draft([activity(), activity("two", "b", "12:00", "13:00")])
    bindings = bind_transitions(original, "TRANSIT")
    assert list(check_transitions(original, bindings, (route(60),)))[0]["status"] == "PASS"
    assert list(check_transitions(original, bindings, (route(7200),)))[0]["magnitude"] == 3600


def test_route_acquisition_and_reassessment_preserve_original_report():
    original, ctx = overlap_draft(), context()
    scope = scope_for(original, ctx, travel_mode="TRANSIT")
    provider = Routes(duration=60)
    result = run(scope=scope, routes_provider=provider, model=Model([edit("11:10", "12:10")]))
    assert result.status == "ACCEPTED_COMPLETE", result.reason
    assert (
        next(f for f in result.original_report.findings if f.check == "route").status == "UNKNOWN"
    )
    assert (
        next(f for f in result.reassessed_original_report.findings if f.check == "route").status
        == "CONFIRMED"
    )
    assert next(f for f in result.proposed_report.findings if f.check == "route").status == "PASS"
    assert len(provider.calls) == 1 and result.acquired_routes


def test_route_fetch_success_does_not_mean_conflict_fixed():
    original, ctx = overlap_draft(), context()
    scope = scope_for(original, ctx, travel_mode="TRANSIT")
    result = run(scope=scope, routes_provider=Routes(duration=3600))
    assert result.status == "ACCEPTED_COMPLETE", result.reason
    # Authorized overlap resolved, but route still confirmed: completeness is scoped.
    assert any(
        f.check == "route" and f.status == "CONFIRMED" for f in result.proposed_report.findings
    )


def test_candidate_limit_and_input_overflow_fail_before_model(monkeypatch):
    original, ctx = overlap_draft(), context()
    scope = scope_for(original, ctx)
    monkeypatch.setattr("backend.app.versions.v3.repair_projection.count_tokens", lambda _: 100000)
    model = Model()
    result = run(model=model, scope=scope)
    assert result.status == "SKIPPED" and model.calls == 0 and "overflow" in result.reason


def test_foundry_repair_options_are_per_call_and_primary_unchanged():
    from backend.app.llm.azure_foundry.client import AzureFoundryStructuredLLMClient

    calls = []

    class Chat:
        def with_structured_output(self, schema, **options):
            calls.append((schema, options))
            return self

        async def ainvoke(self, messages):
            return {"edits": [], "target_dispositions": []}

    client = object.__new__(AzureFoundryStructuredLLMClient)
    client._chat_model = Chat()
    result = asyncio.run(
        client.generate_repair_structured(
            system_prompt="system",
            user_prompt='{"activity_id":"original-activity","place_id":"original-place","target_id":"original-target"}',
        )
    )
    assert not result.edits
    assert len(calls) == 1
    schema, options = calls[0]
    assert schema["$defs"]["RepairEdit"]["properties"]["activity_id"]["enum"] == ["a01", None]
    assert options == {"method": "json_schema", "strict": True, "max_output_tokens": 16384}


def test_pre_send_failure_has_no_send_charge_and_is_not_retried():
    async def scenario():
        budget = RepairBudget(monotonic() + 300)
        calls = []

        async def unavailable():
            calls.append(1)
            raise RuntimeError("before transport send")

        for _ in range(2):
            assert (
                await budget.call(("details",), unavailable, charges={"details": 1}, observed=True)
                is None
            )
        assert budget.used["details"] == 0 and len(calls) == 1

    asyncio.run(scenario())


def test_repeated_provider_send_is_blocked_without_second_charge():
    async def scenario():
        budget = RepairBudget(monotonic() + 300)

        async def invalid_retry():
            mark_provider_send()
            mark_provider_send()

        assert (
            await budget.call(("retry",), invalid_retry, charges={"details": 1}, observed=True)
            is None
        )
        assert budget.used["details"] == 1

    asyncio.run(scenario())


def test_timeout_rolls_back_and_cancellation_after_send_propagates():
    async def scenario():
        budget = RepairBudget(monotonic() + 300)

        async def slow():
            mark_provider_send()
            await asyncio.sleep(1)

        assert (
            await budget.call(
                ("timeout",), slow, charges={"details": 1}, observed=True, timeout=0.001
            )
            is None
        )
        assert budget.used["details"] == 1

        async def cancelled():
            mark_provider_send()
            raise asyncio.CancelledError

        with pytest.raises(asyncio.CancelledError):
            await budget.call(("cancel",), cancelled, charges={"details": 1}, observed=True)
        assert budget.used["details"] == 2

    asyncio.run(scenario())


def test_expired_phase_after_model_never_applies_patch():
    ticks = [0]

    class ExpiringModel(Model):
        async def generate_repair_structured(self, **kwargs):
            ticks[0] = 301
            return await super().generate_repair_structured(**kwargs)

    result = run(model=ExpiringModel(), clock=lambda: ticks[0], request_deadline=300)
    assert result.status == "REJECTED" and result.reason == "phase_deadline"
    assert result.final == result.original


def test_model_timeout_uses_remaining_time_and_never_retries():
    class Slow(Model):
        async def generate_repair_structured(self, **kwargs):
            self.calls += 1
            await asyncio.sleep(1)

    model = Slow()
    from backend.tests.versions.v3.test_multiround import policy

    result = run(
        model=model,
        policy=policy(timing={"model_seconds": 0.002, "minimum_model_seconds": 0.001}),
        request_deadline=monotonic() + 600,
    )
    assert result.status == "REJECTED" and result.reason == "repair_timeout" and model.calls == 1


def test_post_patch_new_departure_fetches_second_route_from_same_ledger():
    original, ctx = overlap_draft(), context()
    scope = scope_for(
        original,
        ctx,
        travel_mode="TRANSIT",
        permissions=({"activity_id": "one", "operations": ("retime",)},),
    )
    provider = Routes(duration=60)
    result = run(
        scope=scope,
        routes_provider=provider,
        model=Model([edit("09:00", "10:00", activity_id="one")]),
    )
    assert result.status == "ACCEPTED_COMPLETE", result.reason
    assert len(provider.calls) == 2 and result.counters["routes"] == 2
    assert result.counters["elements"] == 2
    assert provider.calls[0].departure_time != provider.calls[1].departure_time


def test_invalid_patch_never_reaches_post_route_fetch():
    original, ctx = overlap_draft(), context()
    provider = Routes()
    result = run(
        scope=scope_for(original, ctx, travel_mode="TRANSIT"),
        routes_provider=provider,
        model=Model([edit(activity_id="outside")]),
    )
    assert result.status == "REJECTED" and len(provider.calls) == 1


def test_route_failure_is_optional_for_independent_overlap_improvement():
    original, ctx = overlap_draft(), context()
    result = run(
        scope=scope_for(original, ctx, travel_mode="TRANSIT"), routes_provider=Routes(fail=True)
    )
    assert result.status == "ACCEPTED_COMPLETE", result.reason
    assert (
        next(f for f in result.proposed_report.findings if f.check == "route").status == "UNKNOWN"
    )


def test_evidence_only_change_cannot_count_as_arrangement_improvement():
    original, ctx = overlap_draft(), context()
    result = run(
        scope=scope_for(original, ctx, travel_mode="TRANSIT"),
        routes_provider=Routes(),
        model=Model([]),
    )
    assert result.status == "REJECTED" and "No verifiable" in result.reason
    assert result.original_report != result.reassessed_original_report


def test_original_confirmed_route_cannot_be_weakened_by_new_conflicting_evidence():
    from backend.app.versions.v3.repair_acceptance import compare

    original, ctx = overlap_draft(), context()
    initial = assess(original, ctx)
    weakened = initial.model_copy(
        update={
            "findings": tuple(
                f.model_copy(update={"status": "UNKNOWN", "is_violation": False})
                if f.check == "overlap"
                else f
                for f in initial.findings
            )
        }
    )
    result = compare(original, original, initial, weakened, weakened, scope_for(original, ctx))
    assert not result.accepted and "weakened" in result.reason


def test_all_targets_status_is_not_reduced_to_one_accepted_patch():
    original, ctx = overlap_draft(), context()
    original.days[0].activities.extend(
        [activity("three", "c", "14:00", "15:00"), activity("four", "c", "14:30", "15:30")]
    )
    result = run(original=original, ctx=ctx)
    assert result.status == "ACCEPTED_PARTIAL"
    assert [p.outcome for p in result.target_progress] == ["resolved", "unresolved"]


def test_rag_query_reuses_intent_and_existing_google_identity_resolver():
    from backend.app.integrations.models import PlaceSearchResponse
    from backend.app.schemas.interpreted_requirements import InterpretedTripRequirements
    from backend.app.tripworld.retrieval.geography import GeographicScope
    from backend.tests.services.test_tripworld_discovery import hit

    raw = contract().model_dump()
    raw["semantic_requirements"] = [
        {
            "requirement_id": "semantic_1",
            "normalized_text": "Museums",
            "kind": "preference",
            "polarity": "favor",
            "strength": "medium",
            "scope": "individual_poi",
            "subject_refs": ["party"],
            "source_refs": [{"quote": "Museums", "occurrence": 0, "start": 0, "end": 7}],
        }
    ]
    raw["discovery_intents"] = [
        {
            "intent_id": "discovery_1",
            "requirement_refs": ["semantic_1"],
            "purpose": "semantic_discovery",
            "query_text": "Museums",
        }
    ]
    ctx = context(InterpretedTripRequirements.model_validate(raw))
    original = draft()
    scope = scope_for(original, ctx, check="coverage", add_dates=(DAY,))

    class DiscoveryPlaces(Places):
        async def search_text(self, request):
            mark_provider_send()
            return PlaceSearchResponse(
                candidates=[], actual_result_count=0, retrieved_at=NOW.isoformat()
            )

    class Rag:
        artifact_hash = "fixture"

        async def embed(self, texts):
            assert texts == ["Museums"]
            return [[0.1]]

        async def search(self, vector, scope, top_k):
            assert top_k == 10
            row = hit("new")
            row["entity"]["latitude"] = row["entity"]["longitude"] = 0
            return [row, row]

    result = run(
        budget=exploring_budget(),
        original=original,
        ctx=ctx,
        scope=scope,
        model=Model([edit("12:00", "13:00", operation="add", activity_id=None, place_id="new")]),
        places_provider=DiscoveryPlaces(),
        intent_ids=("discovery_1",),
        rag=Rag(),
        geographic_scope=GeographicScope(latitude=0, longitude=0, radius_km=15),
    )
    assert result.status == "ACCEPTED_COMPLETE", result.reason
    assert (
        result.counters["embedding"]
        == result.counters["retrieval"]
        == result.counters["details"]
        == 1
    )
    assert result.counters["canonical"] == 1
    assert next(c for c in result.repair_whitelist if c.place.place_id == "new").origin == "rag"


def test_actual_serializer_candidate_and_per_candidate_bounds():
    from backend.app.versions.v3.repair_projection import build_repair_input
    from tools.diagnostics.repair_payload import fixture

    args = fixture(10, 33)
    with pytest.raises(ValueError, match="candidate_ceiling"):
        build_repair_input(*args)
    args = list(fixture(1, 3))
    candidate = args[-1].input_candidates[0]
    replacement = (
        candidate.model_copy(
            update={"place": candidate.place.model_copy(update={"name": "x" * 13000})}
        ),
    )
    args[-1] = args[-1].model_copy(update={"input_candidates": replacement})
    with pytest.raises(ValueError, match="candidate_projection_overflow"):
        build_repair_input(*args)


def test_service_never_opens_network_or_database(monkeypatch):
    import socket

    import httpx
    import psycopg

    def forbidden(*args, **kwargs):
        pytest.fail("Unexpected network or database access")

    async def scenario():
        # Windows creates an internal loopback socketpair when the event loop starts.
        # Block every connection after that infrastructure exists, during service work.
        with monkeypatch.context() as guard:
            for target, name in [
                (socket.socket, "connect"),
                (socket.socket, "connect_ex"),
                (socket, "create_connection"),
                (httpx.Client, "send"),
                (httpx.AsyncClient, "send"),
                (psycopg, "connect"),
                (psycopg.AsyncConnection, "connect"),
            ]:
                guard.setattr(target, name, forbidden)
            original, ctx = overlap_draft(), context()
            result = await run_repair_once(
                original,
                ctx,
                scope_for(original, ctx),
                model=Model(),
                request_deadline=monotonic() + 300,
            )
            assert result.status == "ACCEPTED_COMPLETE"

    asyncio.run(scenario())


def test_cost_projection_paths_follow_retained_activities_after_authorized_deletion():
    from backend.app.schemas.itinerary_projection import EstimatedCostProjectionDiagnostic

    original, ctx = overlap_draft(), context(contract("EXCLUDED"), named_resolutions=(binding(),))
    original.set_cost_projections(
        (
            EstimatedCostProjectionDiagnostic(
                "days[0].activities[1].estimated_cost", "explicit_null"
            ),
        )
    )
    from backend.app.versions.v3.wiring import operation_scope

    scope = operation_scope(original, assess(original, ctx), context=ctx)
    result = run(
        original=original,
        ctx=ctx,
        scope=scope,
        model=Model([edit(operation="delete", activity_id="one", start=None, end=None)]),
    )
    assert result.status == "ACCEPTED_PARTIAL", result.reason
    assert result.final.cost_projections[0].field_path == "days[0].activities[0].estimated_cost"
    assert original.cost_projections[0].field_path == "days[0].activities[1].estimated_cost"


def test_partial_route_bindings_explicitly_retain_unverified_legs():
    itinerary = draft(
        [
            activity(),
            activity("two", "b", "12:00", "13:00"),
            activity("three", "c", "14:00", "15:00"),
        ]
    )
    bindings = bind_transitions(itinerary, "TRANSIT")[:1]
    rows = list(check_transitions(itinerary, bindings, (route(),)))
    assert any(
        r["reason"] == "transition_binding_missing" and r["status"] == "UNKNOWN" for r in rows
    )


def test_projection_filters_full_matrix_to_authorized_adjacencies():
    from backend.app.versions.v3.repair_projection import build_repair_input
    from tools.diagnostics.repair_payload import fixture

    args = fixture(1, 3)
    evidence = route().model_copy(
        update={
            "elements": [
                route()
                .elements[0]
                .model_copy(
                    update={"origin_place_id": f"place_{a}", "destination_place_id": f"place_{b}"}
                )
                for a in range(3)
                for b in range(3)
            ]
        }
    )
    _, user, _ = build_repair_input(*args, route_evidence=(evidence,))
    assert len(json.loads(user)["routes"][0]["elements"]) == 1


# Candidate grouping regression: every external boundary below is a fixture.
def with_hours(pid):
    from backend.app.evidence.models import OpeningHoursEvidence

    return place(
        pid,
        regular_opening_hours=OpeningHoursEvidence(
            applicability="regular_weekly_pattern", weekday_descriptions=["Fixture weekly hours"]
        ),
    )


def addition_scope(original, ctx):
    return scope_for(
        original,
        ctx,
        check="coverage",
        dates=tuple(d.date for d in original.days),
        add_dates=tuple(d.date for d in original.days),
    )


def discovery_context(**changes):
    from backend.app.schemas.interpreted_requirements import InterpretedTripRequirements

    raw = contract().model_dump()
    raw["semantic_requirements"] = [
        {
            "requirement_id": "semantic_1",
            "normalized_text": "Museums",
            "kind": "preference",
            "polarity": "favor",
            "strength": "medium",
            "scope": "individual_poi",
            "subject_refs": ["party"],
            "source_refs": [{"quote": "Museums", "occurrence": 0, "start": 0, "end": 7}],
        }
    ]
    raw["discovery_intents"] = [
        {
            "intent_id": "discovery_1",
            "requirement_refs": ["semantic_1"],
            "purpose": "semantic_discovery",
            "query_text": "Museums",
        }
    ]
    return context(InterpretedTripRequirements.model_validate(raw), **changes)


class CandidateSearch(Places):
    def __init__(self, ids=("fresh", "fresh2")):
        super().__init__()
        self.ids, self.searches = ids, 0

    async def search_text(self, request):
        from backend.app.integrations.models import PlaceSearchResponse

        mark_provider_send()
        self.searches += 1
        return PlaceSearchResponse(
            candidates=[
                PlaceCandidateDTO(
                    place_id=pid,
                    display_name=pid,
                    location={"latitude": 0, "longitude": 0},
                    provider_rank=i,
                )
                for i, pid in enumerate(self.ids)
            ],
            actual_result_count=len(self.ids),
            retrieved_at=NOW.isoformat(),
        )


def test_addition_projection_separates_context_and_stops_when_old_material_sufficient():
    ctx = discovery_context(places=(place(), with_hours("b"), with_hours("c")))
    original, model, provider = draft(), Model([]), CandidateSearch()
    result = run(
        original=original,
        ctx=ctx,
        scope=addition_scope(original, ctx),
        model=model,
        places_provider=provider,
        intent_ids=("discovery_1",),
    )
    assert provider.calls == provider.searches == 0
    assert {c["place_id"] for c in model.input["addition_candidates"]} == {"b", "c"}
    assert model.input["protected_activities"][0]["source_place_id"] == "a"
    assert not result.candidate_preparation.exploration_reasons
    assert any(
        "admission_reservation_and_special_area_unverified" in a.unknowns
        for a in result.candidate_preparation.authorizations
    )
    assert result.status == "REJECTED" and result.parsed_patch.edits == ()
    assert result.proposed.model_dump() == original.model_dump()
    assert result.comparison.business_values[0]["before_distinct_main"] == 1
    assert result.comparison.business_values[0]["after_distinct_main"] == 1


def test_scheduled_and_ledger_only_identity_cannot_be_added():
    original, ctx = draft(), context()
    result = run(
        original=original,
        ctx=ctx,
        scope=addition_scope(original, ctx),
        model=Model([edit(operation="add", activity_id=None, place_id="a")]),
    )
    assert result.status == "REJECTED" and result.final == original
    assert result.parsed_patch is not None and result.proposed is None
    assert "a" in {c.place.place_id for c in result.repair_whitelist}
    assert "a" not in {c.place.place_id for c in result.candidate_preparation.input_candidates}


def test_needed_discovery_enters_real_projection_and_acceptance_without_changing_original_supply():
    from backend.tests.services.test_poi_semantics import service

    semantic_service = service()
    original = draft()
    ctx = discovery_context(original_supply_ids=("a",), places=(place(),))
    provider = CandidateSearch(ids=("a", "fresh", "fresh2", "unused"))
    model = Model([edit("12:00", "13:00", operation="add", activity_id=None, place_id="fresh")])
    result = run(
        original=original,
        ctx=ctx,
        scope=addition_scope(original, ctx),
        model=model,
        places_provider=provider,
        intent_ids=("discovery_1",),
        semantic_service=semantic_service,
    )
    assert result.status == "ACCEPTED_COMPLETE", result.reason
    assert semantic_service.calls == 2
    assert "fresh" in semantic_service.ledger
    assert provider.searches == 1 and provider.calls == 2
    assert result.counters["original_supply_unused"] == 0
    assert result.final_place_ids == ("a", "fresh")
    assert result.reassessed_original_report.diagnostics.unused_supply == 0
    assert result.proposed_report.diagnostics.unused_supply == 0
    assert result.counters["repair_input_unused"] == 1
    assert result.candidate_preparation.exploration_slots == 2


def test_full_union_reserves_only_two_round_slots_and_keeps_ledger_separate():
    original = draft()
    places = tuple(place(pid) for pid in ["a", *(f"old{i:02}" for i in range(35))])
    ctx = discovery_context(original_supply_ids=tuple(p.place_id for p in places), places=places)
    provider, model = CandidateSearch(), Model([])
    result = run(
        budget=exploring_budget(),
        original=original,
        ctx=ctx,
        scope=addition_scope(original, ctx),
        model=model,
        places_provider=provider,
        intent_ids=("discovery_1",),
    )
    prep = result.candidate_preparation
    assert len(prep.input_candidates) == 31
    assert result.sizing["input_identity_union"] == 32
    assert {"fresh", "fresh2"} <= {c.place.place_id for c in prep.input_candidates}
    assert len(prep.ledger) == 38 and provider.calls == 2
    assert any(d.disposition == "capacity_omitted" for d in prep.decisions)
    assert not any(d.disposition == "excluded" for d in prep.decisions)
    assert result.counters["original_supply_unused"] == 35
    assert result.reassessed_original_report.diagnostics.unused_supply == 35


def test_no_new_results_refill_old_slots_and_unknown_does_not_loop():
    original = draft()
    ps = tuple(place(pid) for pid in ["a", *(f"old{i}" for i in range(30))])
    ctx = discovery_context(original_supply_ids=tuple(p.place_id for p in ps), places=ps)
    provider = CandidateSearch(ids=())
    result = run(
        budget=exploring_budget(),
        original=original,
        ctx=ctx,
        scope=addition_scope(original, ctx),
        model=Model([]),
        places_provider=provider,
        intent_ids=("discovery_1",),
    )
    assert provider.searches == 1 and provider.calls == 0
    assert len(result.candidate_preparation.input_candidates) == 30
    assert result.candidate_preparation.exploration_reasons == (
        "previous_arrangement_requires_other_options",
    )
    assert result.model_attempted


def test_no_input_room_stops_all_optional_acquisition_but_keeps_context():
    original = draft([activity(str(i), str(i)) for i in range(32)])
    # Explicitly authorized replacement keeps this test independent of coverage detection.
    ctx = discovery_context(
        original_supply_ids=tuple(str(i) for i in range(32)),
        places=tuple(place(str(i)) for i in range(32)),
    )
    scope = scope_for(original, ctx, operations=("retime", "replace"))
    from backend.app.versions.v3.repair_models import ActivityPermission

    scope = scope.model_copy(
        update={
            "permissions": (ActivityPermission(activity_id="1", operations={"replace"}),),
            "target_ids": scope.target_ids[:1],
        }
    )
    provider = CandidateSearch()
    result = run(
        original=original,
        ctx=ctx,
        scope=scope,
        model=Model([]),
        places_provider=provider,
        pool=(selection("fresh"),),
        intent_ids=("discovery_1",),
    )
    assert provider.calls == provider.searches == 0
    assert len(result.candidate_preparation.scheduled_ids) == 32
    assert result.model_attempted


def two_day_case(ps):
    from backend.app.schemas.itinerary import ItineraryDay

    original = draft()
    tomorrow = DAY + timedelta(days=1)
    original.end_date = tomorrow
    original.days.append(ItineraryDay(date=tomorrow, activities=[]))
    c = contract()
    c = c.model_copy(
        update={
            "time_protections": (),
            "requirements": c.requirements.model_copy(update={"end_date": tomorrow}),
        }
    )
    ctx = context(c, places=ps, original_supply_ids=tuple(p.place_id for p in ps))
    return original, ctx, addition_scope(original, ctx)


def test_multi_target_links_remain_but_supply_and_patch_cannot_double_count():
    from backend.app.versions.v3.repair_candidates import candidate_targets, matched_capacity

    original, ctx, scope = two_day_case((place(), place("b")))
    tomorrow = DAY + timedelta(days=1)
    edits = [
        edit("12:00", "13:00", operation="add", activity_id=None, place_id="b"),
        edit(
            "12:00",
            "13:00",
            operation="add",
            activity_id=None,
            place_id="b",
            date=str(tomorrow),
            start_time=f"{tomorrow}T12:00:00+00:00",
            end_time=f"{tomorrow}T13:00:00+00:00",
        ),
    ]
    result = run(original=original, ctx=ctx, scope=scope, model=Model(edits))
    auth = result.candidate_preparation.authorizations
    assert {(a.place_id, a.date) for a in auth} == {("b", DAY), ("b", tomorrow)}
    eligible = [a.model_copy(update={"disposition": "eligible"}) for a in auth]
    assert matched_capacity(eligible, candidate_targets(original, ctx, scope)) == 1
    assert result.status == "ACCEPTED_PARTIAL"
    assert [c["status"] for c in result.components] == ["accepted", "rejected"]
    assert "Revisit" in result.components[1]["reason"]
    assert sum(a.source_place_id == "b" for d in result.final.days for a in d.activities) == 1


def test_date_exclusion_preserves_other_date_and_unknown_is_not_excluded():
    from backend.app.evidence.selection_models import PlaceOpeningDate, RatingAcquisitionState

    original, ctx, scope = two_day_case(
        (place(), place("future", business_status="FUTURE_OPENING"), place("unknown"))
    )
    tomorrow = DAY + timedelta(days=1)
    item = selection("future").model_copy(
        update={
            "structured_evidence": place("future", business_status="FUTURE_OPENING"),
            "rating_state": RatingAcquisitionState.MISSING,
            "details_opening_date": PlaceOpeningDate(
                year=tomorrow.year, month=tomorrow.month, day=tomorrow.day
            ),
        }
    )
    result = run(original=original, ctx=ctx, scope=scope, model=Model([]), pool=(item,))
    prep = result.candidate_preparation
    assert any(
        d.place_id == "future" and d.date == DAY and d.disposition == "excluded" and d.evidence_refs
        for d in prep.decisions
    )
    assert any(a.place_id == "future" and a.date == tomorrow for a in prep.authorizations)
    assert any(a.place_id == "unknown" for a in prep.authorizations)
    assert not any(d.place_id == "unknown" and d.disposition == "excluded" for d in prep.decisions)


def test_one_alternative_is_enough_to_attempt_when_no_more_material_available():
    original, ctx = draft(), context(original_supply_ids=("a", "b"), places=(place(), place("b")))
    result = run(
        original=original,
        ctx=ctx,
        scope=addition_scope(original, ctx),
        model=Model([edit("12:00", "13:00", operation="add", activity_id=None, place_id="b")]),
    )
    assert result.status == "ACCEPTED_COMPLETE"
    assert result.candidate_preparation.preparation_reference == 2
    assert len(result.candidate_preparation.input_candidates) == 1


def test_explicit_revisit_is_required_and_keeps_other_operation_policy():
    original, ctx, scope = two_day_case((place(),))
    tomorrow = DAY + timedelta(days=1)
    scope = scope.model_copy(update={"revisits": ()})
    from backend.app.versions.v3.repair_models import RevisitPermission

    scope = scope.model_copy(update={"revisits": (RevisitPermission(place_id="a", date=tomorrow),)})
    result = run(
        original=original,
        ctx=ctx,
        scope=scope,
        model=Model(
            [
                edit(
                    operation="add",
                    activity_id=None,
                    place_id="a",
                    date=str(tomorrow),
                    start_time=f"{tomorrow}T12:00:00+00:00",
                    end_time=f"{tomorrow}T13:00:00+00:00",
                )
            ]
        ),
    )
    assert result.status == "ACCEPTED_PARTIAL", result.reason
    assert result.final.days[0] == original.days[0]


def test_audit_preserves_rejected_patch_and_bounds_proposal_in_trace():
    class Trace:
        events = []

        def event(self, name, value):
            self.events.append((name, value))

    trace = Trace()
    result = run(model=Model([]), tracer=trace, audit_max_bytes=100)
    assert result.status == "REJECTED" and result.parsed_patch is not None
    assert result.proposed is None and result.artifact_status["proposal"].startswith("truncated:")
    assert result.comparison is not None
    assert any(
        name == "v3_repair_proposal" and value["artifact_status"].startswith("truncated:")
        for name, value in trace.events
    )
    assert result.final == result.original


def test_identity_in_ledger_but_omitted_from_input_is_not_add_authorized():
    ps = tuple(with_hours(pid) for pid in ["a", *(f"old{i:02}" for i in range(35))])
    original = draft()
    ctx = context(original_supply_ids=tuple(p.place_id for p in ps), places=ps)
    model = Model([edit(operation="add", activity_id=None, place_id="old34")])
    result = run(original=original, ctx=ctx, scope=addition_scope(original, ctx), model=model)
    assert "old34" in {c.place.place_id for c in result.repair_whitelist}
    assert "old34" not in {c.place.place_id for c in result.candidate_preparation.input_candidates}
    assert result.status == "REJECTED" and result.final == original


def test_protected_context_over_union_limit_is_not_truncated_to_call_model():
    original = draft([activity(str(i), str(i)) for i in range(33)])
    ctx = context(
        original_supply_ids=tuple(str(i) for i in range(33)),
        places=tuple(place(str(i)) for i in range(33)),
    )
    report = assess(original, ctx)
    scope = RepairScope(
        dates=(DAY,),
        permissions=(),
        target_ids=tuple(t.finding_id for t in report.improvement_targets),
    )
    model = Model([])
    result = run(original=original, ctx=ctx, scope=scope, model=model)
    assert result.status == "SKIPPED" and "identity_union_ceiling" in result.reason
    assert model.calls == 0 and len(result.final.days[0].activities) == 33


def test_multiple_targets_reserve_two_total_and_stop_at_available_input_capacity():
    original, ctx, scope = two_day_case(
        tuple(place(pid) for pid in ["a", *(f"old{i}" for i in range(35))])
    )
    base = discovery_context().contract
    ctx = ctx.model_copy(
        update={
            "contract": base.model_copy(
                update={"requirements": ctx.contract.requirements, "time_protections": ()}
            )
        }
    )
    provider = CandidateSearch(ids=("fresh", "fresh2", "unused3", "unused4"))
    result = run(
        budget=exploring_budget(),
        original=original,
        ctx=ctx,
        scope=scope,
        model=Model([]),
        places_provider=provider,
        intent_ids=("discovery_1",),
    )
    assert result.candidate_preparation.preparation_reference == 4
    assert result.candidate_preparation.exploration_slots == 2
    assert provider.calls == 2 and provider.searches == 1
    assert result.sizing["input_identity_union"] == 32


def test_needed_rag_exploration_respects_prior_failure_without_retry():
    from backend.app.tripworld.retrieval.geography import GeographicScope

    class Rag:
        def allows_embedding(self, texts):
            return False

        async def embed(self, texts):
            raise AssertionError("prior failure must not retry")

    original = draft()
    ctx = discovery_context(original_supply_ids=("a", "b"), places=(place(), place("b")))
    result = run(
        original=original,
        ctx=ctx,
        scope=addition_scope(original, ctx),
        model=Model([edit("12:00", "13:00", operation="add", activity_id=None, place_id="b")]),
        places_provider=CandidateSearch(ids=()),
        intent_ids=("discovery_1",),
        rag=Rag(),
        geographic_scope=GeographicScope(latitude=0, longitude=0, radius_km=15),
    )
    assert result.status == "ACCEPTED_COMPLETE" and "previous_rag_failure" in result.stops
    assert result.counters.get("embedding", 0) == 0


def test_unparsed_model_artifact_is_explicit_and_never_becomes_a_proposal():
    result = run(model=Model([{"operation": "invented"}]))
    assert result.status == "REJECTED" and result.artifact_status["patch"] == "not_parsed"
    assert result.parsed_patch is result.proposed is result.comparison is None
    assert result.final == result.original


def test_audit_redacts_sensitive_free_text_without_changing_business_draft():
    original = overlap_draft()
    original.days[0].activities[0].notes = "password=fixture-value"
    result = run(original=original, model=Model([]))
    assert result.final.days[0].activities[0].notes == "password=fixture-value"
    assert "fixture-value" not in result.proposed.model_dump_json()


def test_old_details_preserve_discovery_opportunity_for_concrete_feedback():
    original = draft()
    ctx = discovery_context(original_supply_ids=("a",), places=(place(),))
    provider = CandidateSearch()
    result = run(
        budget=exploring_budget(),
        original=original,
        ctx=ctx,
        scope=addition_scope(original, ctx),
        model=Model([]),
        pool=tuple(selection(f"pending{i}") for i in range(12)),
        places_provider=provider,
        intent_ids=("discovery_1",),
    )
    prep = result.candidate_preparation
    assert provider.searches == 1 and provider.calls == 14
    assert result.counters["canonical"] == result.counters["details"] == 14
    assert {"fresh", "fresh2"} <= {c.place.place_id for c in prep.input_candidates}
    assert "previous_arrangement_requires_other_options" in prep.exploration_reasons
    assert result.counters["canonical"] < result.effective_policy["acquisition"]["canonical"]
