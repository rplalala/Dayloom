"""Offline semantic boundary and input sizing; no provider construction."""

import asyncio
import json

import pytest

from backend.app.runtime.config_loader import load_runtime_config
from backend.app.schemas.poi_semantics import SemanticAssessmentError, SemanticPreparationLimit
from backend.app.services.poi_semantics import (
    POISemanticsService,
    semantic_input_tokens,
    serialize_semantic_input,
)
from backend.tests.versions.v3.test_validation import contract, place


class Model:
    def __init__(self, mutate=None):
        self.calls = 0
        self.mutate = mutate

    async def generate_poi_semantics_structured(self, **kwargs):
        self.calls += 1
        data = json.loads(kwargs["user_prompt"])
        rows = [
            dict(
                candidate_ref=p["candidate_ref"],
                visit_object=p["name"],
                role="attraction",
                categories=["museum"],
                reason="Supplied museum evidence",
                evidence_refs=[p["source_ref"]],
                matches=[],
                exception_requirement_ids=[],
            )
            for p in data["places"]
        ]
        if self.mutate:
            self.mutate(rows)
        return {"assessments": rows}


def service(model=None, **config):
    runtime = load_runtime_config()
    return POISemanticsService(
        model or Model(),
        runtime.poi_semantics.model_copy(update=config),
        runtime.main_generation.framing_tokens,
    )


def test_batch_cache_and_total_calls():
    svc = service()
    places = [place(str(i)) for i in range(64)]

    async def run():
        await svc.assess(places, contract())
        await svc.assess(list(reversed(places)), contract())

    asyncio.run(run())
    assert svc.calls == 2
    assert len(svc.ledger) == 64


@pytest.mark.parametrize(
    "elapsed,caller,request_deadline,expected,source",
    [
        (0, None, None, 45, "call"),
        (110, None, None, 10, "total"),
        (0, 113.5, 200, 13.5, "caller"),
        (0, 200, 107, 7, "request"),
    ],
)
@pytest.mark.parametrize("fails", [False, True])
def test_call_outcomes_capture_effective_timeout_and_each_remaining_allowance(
    elapsed, caller, request_deadline, expected, source, fails
):
    class ObservedModel(Model):
        def capture_poi_semantics(self, stage, payload):
            captured.append((stage, payload))

        async def generate_poi_semantics_structured(self, **kwargs):
            if fails:
                self.calls += 1
                raise TimeoutError("Controlled model timeout")
            return await super().generate_poi_semantics_structured(**kwargs)

    captured = []
    svc = service(ObservedModel())
    svc.clock = lambda: 100.0
    svc.deadline, svc.elapsed = request_deadline, elapsed
    if fails:
        with pytest.raises(SemanticAssessmentError) as error:
            asyncio.run(svc.prepare([place()], contract(), deadline=caller))
        assert isinstance(error.value.__cause__, TimeoutError)
        assert svc.failed and not svc.ledger
    else:
        assert asyncio.run(svc.prepare([place()], contract(), deadline=caller))
    outcome = captured[-1][1]
    assert outcome["timeout_seconds"] == expected
    assert outcome["limiting_deadline"] == source
    assert outcome["remaining_seconds"] == {
        "call": 45,
        "total": 120 - elapsed,
        **({"caller": caller - 100} if caller is not None else {}),
        **({"request": request_deadline - 100} if request_deadline is not None else {}),
    }
    assert outcome["status"] == ("failed" if fails else "accepted")
    if fails:
        assert outcome["error_type"] == "TimeoutError" and outcome["usage"] == {}
    assert captured[0][1]["timeout_seconds"] == expected
    assert svc.calls == 1


@pytest.mark.parametrize(
    "mutate,expected_calls",
    [
        (lambda rows: rows.pop(), 1),  # Empty output fails the domain schema.
        (lambda rows: rows.append(rows[0]), 2),
        (lambda rows: rows[0].update(candidate_ref="invented"), 2),
        (
            lambda rows: rows[0].update(
                role="exception_only", exception_requirement_ids=["invented"]
            ),
            2,
        ),
    ],
)
def test_invalid_contract_is_terminal(mutate, expected_calls):
    svc = service(Model(mutate))
    with pytest.raises(SemanticAssessmentError):
        asyncio.run(svc.assess([place()], contract()))
    with pytest.raises(SemanticAssessmentError, match="already failed"):
        asyncio.run(svc.assess([place()], contract()))
    assert svc.calls == expected_calls


def test_unknown_operations_do_not_disqualify_role():
    svc = service()
    rows = asyncio.run(svc.assess([place().model_copy(update={"opening_hours": None})], contract()))
    assert rows[place().place_id].main_eligible


def test_unknown_role_cannot_qualify():
    svc = service(Model(lambda rows: rows[0].update(role="unresolved")))
    assert not asyncio.run(svc.assess([place()], contract()))[place().place_id].main_eligible


@pytest.mark.parametrize("frequency", ["exact", "minimum"])
def test_explicit_category_count_has_supply_before_ordinary_diversification(frequency):
    from backend.app.policies.planning_supply import SupplyCandidate, select_planning_supply
    from backend.app.schemas.interpreted_requirements import DiscoveryIntent
    from backend.tests.versions.v3.test_b_targets import setup, visit
    from backend.tests.versions.v3.test_semantic_repair import category_goal

    _, ctx, _, _ = setup([[visit("a", "a")]], reviews=())
    ctx = category_goal(ctx, frequency=frequency, matched_ids=("a", "b"))
    current = ctx.contract.model_copy(
        update={
            "discovery_intents": (
                DiscoveryIntent(
                    intent_id="discovery_1",
                    requirement_refs=("semantic_1",),
                    purpose="activity_or_category",
                    query_text="zoos",
                ),
            )
        }
    )
    candidates = [
        SupplyCandidate(
            place_id=pid,
            primary_type=category,
            rating=None,
            latitude=0,
            longitude=0,
            intent_ids=("discovery_1",) if pid in {"a", "b"} else (),
        )
        for pid, category in [
            ("a", "zoo"),
            ("b", "zoo"),
            ("c", "art"),
            ("d", "history"),
            ("e", "park"),
        ]
    ]
    result = select_planning_supply(
        candidates,
        current,
        required_ids=(),
        excluded_ids=(),
        capacity=4,
        hard_capacity=4,
        destination_coordinates=(0, 0),
        semantic_assessments={r.place_id: r for r in ctx.semantic_assessments},
        semantic_config=load_runtime_config().poi_semantics,
    )
    assert {"a", "b"} <= set(result.selected_place_ids)
    assert len(result.selected_place_ids) == 4


def test_london_historical_search_lanes_retain_exploration_before_details():
    from math import ceil
    from pathlib import Path
    from types import SimpleNamespace

    from backend.app.policies.acquisition_opportunities import opportunity_order
    from backend.app.schemas.interpreted_requirements import InterpretedTripRequirements

    saved = json.loads(
        (Path(__file__).parents[1] / "fixtures/poi_semantics_london.json").read_text()
    )
    rows = [
        SimpleNamespace(
            candidate=SimpleNamespace(**r),
            discovery_intent_ids=r["intent_ids"],
            landmark_nomination=None,
        )
        for r in saved["candidates"]
    ]
    general = {
        r.candidate.place_id
        for r in rows
        if not set(r.discovery_intent_ids) & {"discovery_1", "discovery_2"}
    }
    order = opportunity_order(
        rows,
        set(),
        InterpretedTripRequirements.model_validate(saved["contract"]),
        SimpleNamespace(latitude=51.5072, longitude=-0.1276),
        exploration_fraction=load_runtime_config().poi_semantics.exploration_fraction,
    )
    assert len(set(order)) == len(rows)
    for capacity in (16, 32, 48):
        assert len(set(order[:capacity]) & general) >= min(len(general), ceil(capacity / 3))
    # The raw Google lane is not the later merged Google/RAG association ledger.
    assert set(saved["historical_selection_reasons"]) == {"discovery_opportunity"}


def test_overflow_is_presend_failure():
    svc = service(input_tokens=1)
    with pytest.raises(SemanticPreparationLimit, match="overflow"):
        asyncio.run(svc.assess([place()], contract()))
    assert svc.calls == 0


def test_call_budget_is_shared_across_batches():
    svc = service(max_calls=1, batch_size=1)
    with pytest.raises(SemanticPreparationLimit, match="budget"):
        asyncio.run(svc.assess([place(), place("b")], contract()))
    assert svc.calls == 1


@pytest.mark.parametrize("change", ["missing", "zero", "timeout"])
def test_semantic_config_cannot_silently_disable_service(change):
    from backend.app.runtime.config_models import RuntimeConfig

    data = load_runtime_config().model_dump()
    if change == "missing":
        data.pop("poi_semantics")
    elif change == "zero":
        data["poi_semantics"]["max_calls"] = 0
    else:
        data["poi_semantics"]["call_timeout_seconds"] = data["poi_semantics"]["total_seconds"] + 1
    with pytest.raises(ValueError):
        RuntimeConfig.model_validate(data)


def test_cancel_propagates():
    class Cancel:
        async def generate_poi_semantics_structured(self, **kwargs):
            raise asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(service(Cancel()).assess([place()], contract()))


@pytest.mark.parametrize("count", [1, 16, 32])
def test_real_serializer_size(count):
    payload = serialize_semantic_input([place(str(i)) for i in range(count)], contract())
    size = semantic_input_tokens(payload, load_runtime_config().main_generation.framing_tokens)
    assert size < load_runtime_config().poi_semantics.input_tokens


@pytest.mark.parametrize("bound", ["a", "other", None])
def test_named_exception_requires_application_identity_binding(bound):
    def exception(rows):
        rows[0].update(
            role="exception_only",
            exception_requirement_ids=["named_1"],
            matches=[dict(requirement_id="named_1", relation="supported", evidence_refs=["e01"])],
        )

    svc = service(Model(exception))
    svc.named_bindings = {"named_1": bound} if bound else {}
    if bound == "a":
        assert asyncio.run(svc.assess([place()], contract("REQUIRED")))["a"].main_eligible
    else:
        with pytest.raises(SemanticAssessmentError):
            asyncio.run(svc.assess([place()], contract("REQUIRED")))


def test_details_continue_same_queue_after_semantic_rejection():
    from datetime import date

    from backend.app.services.candidate_details import acquire_candidate_details
    from backend.tests.services.test_quality_first import acquisition

    async def run():
        acq, rows, provider, requirements, _ = acquisition(32)
        from backend.tests.services.test_tripworld_discovery import details

        rejected = {details(p.candidate.place_id).display_name for p in rows[:24]}

        def classify(items):
            for item in items:
                item["role"] = "non_main" if item["visit_object"] in rejected else "attraction"

        svc = service(Model(classify))

        async def adequate(items, deadline):
            judgments = await svc.prepare(
                [p.structured_evidence for p in items], requirements, deadline=deadline
            )
            return sum(r.main_eligible for r in judgments.values()) >= 8

        rich, _, _ = await acquire_candidate_details(
            acq, rows, date(2026, 9, 23), 24, adequate=adequate
        )
        await svc.prepare([p.structured_evidence for p in rich], requirements)
        assert len(rich) == len(provider.ids) == len(set(provider.ids)) == 32
        assert svc.calls == 2
        assert sum(r.main_eligible for r in svc.ledger.values()) == 8
        assert not provider.searches

    asyncio.run(run())


def test_exploration_supply_uses_judgment_not_search_origin():
    from types import SimpleNamespace

    from backend.app.schemas.poi_semantics import POISemanticAssessment
    from backend.tests.policies.test_planning_supply import candidate, select
    from backend.tests.policies.test_planning_supply import contract as make_contract

    req = make_contract()
    ref = req.semantic_requirements[0].requirement_id
    req = req.model_copy(
        update={"discovery_intents": (SimpleNamespace(intent_id="zoo", requirement_refs=(ref,)),)}
    )
    candidates = [candidate(str(i), intents=("zoo",)) for i in range(12)]
    rows = {
        p.place_id: POISemanticAssessment(
            place_id=p.place_id,
            visit_object=p.place_id,
            role="attraction",
            categories=["museum"],
            reason="Synthetic assessment",
            evidence_refs=[f"places:{p.place_id}"],
            matches=[
                dict(
                    requirement_id=ref,
                    relation="supported" if int(p.place_id) < 8 else "mismatch",
                    evidence_refs=[f"places:{p.place_id}"],
                )
            ],
            exception_requirement_ids=[],
        )
        for p in candidates
    }
    result = select(
        candidates,
        req,
        semantic_assessments=rows,
        semantic_config=load_runtime_config().poi_semantics,
    )
    assert sum(int(pid) >= 8 for pid in result.selected_place_ids) >= 3


def test_exception_alternatives_share_allowance_and_incomplete_output():
    from backend.app.policies.poi_semantic_output import semantic_policy_issues
    from backend.app.schemas.interpreted_requirements import ExperienceGoal
    from backend.app.schemas.poi_semantics import POISemanticAssessment
    from backend.tests.policies.test_planning_supply import candidate, select
    from backend.tests.policies.test_planning_supply import contract as make_contract
    from backend.tests.versions.v3.test_validation import activity, draft

    req = make_contract()
    goal = ExperienceGoal(
        frequency="one_off",
        target="category",
        explicit_primary_exception=True,
        distinct_dates=False,
        trip_scope="ordinary",
        count=None,
    )
    ref = req.semantic_requirements[0].requirement_id
    req = req.model_copy(
        update={
            "semantic_requirements": (
                req.semantic_requirements[0].model_copy(update={"experience_goal": goal}),
            )
        }
    )
    rows = {
        str(i): POISemanticAssessment(
            place_id=str(i),
            visit_object="Meal",
            role="exception_only",
            categories=["dining"],
            reason="Explicit fixture request",
            evidence_refs=[f"places:{i}"],
            matches=[dict(requirement_id=ref, relation="supported", evidence_refs=[f"places:{i}"])],
            exception_requirement_ids=[ref],
        )
        for i in range(5)
    }
    result = select(
        [candidate(str(i)) for i in range(5)],
        req,
        semantic_assessments=rows,
        semantic_config=load_runtime_config().poi_semantics,
    )
    assert len(result.selected_place_ids) == 2
    itinerary = draft([activity("a", "0"), activity("b", "1", "12:00", "13:00")])
    assert any(
        r["reason"] == "primary_exception_allowance_exceeded"
        for r in semantic_policy_issues(itinerary, req, tuple(rows.values()))
    )


class CorrectingModel(Model):
    def __init__(self, *, always_invalid=False):
        super().__init__()
        self.inputs = []
        self.captures = []
        self.always_invalid = always_invalid

    def capture_poi_semantics(self, stage, payload):
        self.captures.append((stage, payload))

    async def generate_poi_semantics_structured(self, **kwargs):
        self.inputs.append(json.loads(kwargs["user_prompt"]))
        result = await super().generate_poi_semantics_structured(**kwargs)
        if self.calls == 1 or self.always_invalid:
            result["assessments"][0]["evidence_refs"] = ["places:invented"]
        return result


def test_reference_failure_is_corrected_once_then_cached():
    model = CorrectingModel()
    svc = service(model)

    async def run():
        assert (await svc.assess([place()], contract()))["a"].main_eligible
        assert (await svc.assess([place()], contract()))["a"].main_eligible

    asyncio.run(run())
    assert model.calls == 2
    assert model.inputs[0]["places"] == model.inputs[1]["places"]
    feedback = model.inputs[1]["contract_correction"]
    assert feedback["error"] == "Invalid semantic evidence references"
    assert feedback["details"]["allowed_refs"] == ["e01"]
    assert feedback["details"]["offending_refs"] == ["places:invented"]
    records = svc.snapshot()["records"]
    assert [r["status"] for r in records] == ["failed", "accepted"]
    assert records[1]["correction_of"] == records[0]["call_id"]
    assert [stage for stage, _ in model.captures] == [
        "input",
        "output",
        "outcome",
        "input",
        "output",
        "outcome",
    ]
    assert not svc.snapshot()["failed"]


def test_exhausted_correction_budget_is_captured_and_never_becomes_partial_success():
    model = CorrectingModel()
    svc = service(model, max_calls=1)
    with pytest.raises(SemanticAssessmentError, match="correction unavailable"):
        asyncio.run(svc.prepare([place()], contract()))
    assert model.calls == 1
    assert svc.snapshot()["assessments"] == []
    assert svc.snapshot()["failed"]
    outcome = model.captures[-1][1]
    assert outcome["status"] == "correction_unavailable"
    assert outcome["reason"] == "poi_semantics_call_budget_exhausted"
    assert outcome["correction_of"] == svc.records[0]["call_id"]


@pytest.mark.parametrize("boundary", ["deadline", "service_deadline", "total", "input"])
def test_correction_respects_remaining_time_and_input_budget(monkeypatch, boundary):
    import backend.app.services.poi_semantics as module

    clock = [0.0]
    monkeypatch.setattr(module, "perf_counter", lambda: clock[0])

    class SlowInvalid(CorrectingModel):
        async def generate_poi_semantics_structured(self, **kwargs):
            result = await super().generate_poi_semantics_structured(**kwargs)
            clock[0] = 121.0 if boundary == "total" else 11.0
            return result

    model = SlowInvalid()
    svc = service(model)
    if boundary == "service_deadline":
        svc.deadline = 10.0
    if boundary == "input":
        from backend.app.services.poi_semantics_projection import SemanticProjection

        svc = service(
            model,
            input_tokens=semantic_input_tokens(
                SemanticProjection(
                    [place()], serialize_semantic_input([place()], contract())
                ).payload,
                svc.framing,
            ),
        )
    with pytest.raises(SemanticAssessmentError, match="correction unavailable"):
        asyncio.run(
            svc.prepare([place()], contract(), deadline=10 if boundary == "deadline" else None)
        )
    assert model.calls == 1 and not svc.snapshot()["assessments"]
    expected = "poi_semantics_input_overflow" if boundary == "input" else "poi_semantics_deadline"
    assert svc.records[-1]["reason"] == expected


@pytest.mark.parametrize("failure", ["cancel", "provider", "invalid"])
def test_failed_correction_never_retries_or_caches(failure):
    class Failure(CorrectingModel):
        async def generate_poi_semantics_structured(self, **kwargs):
            if self.calls == 1 and failure != "invalid":
                self.calls += 1
                if failure == "cancel":
                    raise asyncio.CancelledError()
                raise OSError("Synthetic provider failure")
            return await super().generate_poi_semantics_structured(**kwargs)

    model = Failure(always_invalid=True)
    svc = service(model)
    expected = asyncio.CancelledError if failure == "cancel" else SemanticAssessmentError
    with pytest.raises(expected):
        asyncio.run(svc.assess([place()], contract()))
    assert model.calls == 2 and not svc.cache and not svc.ledger
    with pytest.raises(SemanticAssessmentError, match="already failed"):
        asyncio.run(svc.assess([place()], contract()))
    assert model.calls == 2


def test_correction_stop_uses_real_capture_writer(tmp_path):
    from tools.validation.poi_semantics_acceptance import CapturedSemantics

    errors = []
    svc = service(CapturedSemantics(CorrectingModel(), tmp_path, {}, errors), max_calls=1)
    with pytest.raises(SemanticAssessmentError):
        asyncio.run(svc.prepare([place()], contract()))
    assert errors == []
    saved = [json.loads(p.read_text()) for p in tmp_path.glob("*.json")]
    assert any(r.get("status") == "correction_unavailable" for r in saved)


def test_smoke_match_typo_corrects_without_changing_canonical_identity():
    pid = "ChIJJaaNKsZd1moRj_JPUiCyQDE"
    source = "google_places:" + pid
    invalid = "google_places:ChIJJaaNKsZd1moRj_J_PUiCyQDE"

    class MatchModel(Model):
        async def generate_poi_semantics_structured(self, **kwargs):
            result = await super().generate_poi_semantics_structured(**kwargs)
            result["assessments"][0]["matches"] = [
                dict(
                    requirement_id="named_1",
                    relation="supported",
                    evidence_refs=[invalid if self.calls == 1 else "e01"],
                )
            ]
            return result

    svc = service(MatchModel())
    row = place(pid).model_copy(update={"source_ref": source})
    result = asyncio.run(svc.assess([row], contract("REQUIRED")))
    assert result[pid].matches[0].evidence_refs == [source]
    assert svc.calls == 2
    assert svc.records[0]["error_details"]["offending_refs"] == [invalid]


def test_later_batch_correction_preserves_accepted_batch_and_shared_budget():
    class LaterFailure(Model):
        async def generate_poi_semantics_structured(self, **kwargs):
            result = await super().generate_poi_semantics_structured(**kwargs)
            if self.calls == 2:
                result["assessments"][0]["evidence_refs"] = ["wrong"]
            return result

    model = LaterFailure()
    svc = service(model, batch_size=1, max_calls=3)

    async def run():
        result = await svc.assess([place("a"), place("b")], contract())
        assert set(result) == {"a", "b"}
        assert set(await svc.assess([place("a"), place("b")], contract())) == {"a", "b"}
        assert await svc.prepare([place("c")], contract()) == {}

    asyncio.run(run())
    assert model.calls == 3
    assert [r["status"] for r in svc.records] == ["accepted", "failed", "accepted", "pre_send_stop"]


def test_provider_failure_before_validation_is_not_corrected():
    class Broken(Model):
        async def generate_poi_semantics_structured(self, **kwargs):
            self.calls += 1
            raise OSError("Synthetic transport error")

    model = Broken()
    with pytest.raises(SemanticAssessmentError, match="system_failure"):
        asyncio.run(service(model).assess([place()], contract()))
    assert model.calls == 1
