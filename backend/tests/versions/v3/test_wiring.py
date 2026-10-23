"""Actual V3 entry/graph/repair/Nearby chain with only external boundaries faked."""

import asyncio
import json
from datetime import date, timedelta
from time import monotonic

import pytest

from backend.app.schemas.itinerary_projection import EstimatedCostProjectionDiagnostic
from backend.app.versions.v3.runner import run_v3
from backend.tests.request_fixtures import make_request
from backend.tests.services.test_tripworld_discovery import Retrieval
from backend.tests.versions.v0.fakes import FakeStructuredLLMClient
from backend.tests.versions.v1.fakes import FakeRoutesProvider, FakeWeatherProvider, make_itinerary
from backend.tests.versions.v2.test_v2_runner import Places


class OwnedRetrieval(Retrieval):
    def __init__(self, **kwargs):
        super().__init__([], **kwargs)
        self.prepares = self.enters = self.closes = 0

    async def __aenter__(self):
        self.enters += 1
        return self

    async def prepare(self):
        self.prepares += 1
        return await super().prepare()

    async def __aexit__(self, *_):
        self.closes += 1
        await super().__aexit__()


class ManyPlaces(Places):
    async def search_text(self, request):
        from backend.tests.versions.v1.fakes import _candidate

        response = await super().search_text(request)
        if request.location_bias is not None:
            group = self._candidate_call - 1
            return response.model_copy(
                update={
                    "candidates": [
                        _candidate(f"poi-{group}-{i}", i, -33.86, 151.2) for i in range(10)
                    ],
                    "actual_result_count": 10,
                }
            )
        return response


def primary(overlap=True):
    draft = make_itinerary()
    a = draft.days[0].activities[0]
    a.activity_kind, a.source_place_id = "main_poi", "poi-0-0"
    a.location = "0 Sydney NSW, Australia"
    if overlap:
        draft.days[0].activities.append(
            a.model_copy(
                update={
                    "activity_id": "two",
                    "source_place_id": "poi-0-1",
                    "place_name": "Place poi-0-1",
                    "location": "1 Sydney NSW, Australia",
                    "start_time": a.end_time - timedelta(minutes=30),
                    "end_time": a.end_time + timedelta(minutes=30),
                }
            )
        )
    # This fixture tests first-day repair, not an unrelated minimum-coverage miss.
    # Use a different identity: unauthorized repetition is now an automatic product target.
    draft.days[1].activities = [
        a.model_copy(
            update={
                "activity_id": "second-day-visit",
                "source_place_id": "poi-0-2",
                "place_name": "Place poi-0-2",
                "location": "2 Sydney NSW, Australia",
                "start_time": a.start_time + timedelta(days=1),
                "end_time": a.end_time + timedelta(days=1),
            }
        )
    ]
    draft.set_cost_projections(
        (
            EstimatedCostProjectionDiagnostic(
                field_path="days[0].activities[0].estimated_cost", projection="explicit_null"
            ),
        )
    )
    return draft


class Model(FakeStructuredLLMClient):
    def __init__(self, draft=None, behavior="complete"):
        super().__init__([draft if draft is not None else primary()])
        self.behavior, self.repair_calls, self.payload = behavior, 0, None

    async def generate_structured(self, **kwargs):
        if self.behavior == "add" and kwargs["response_schema"].__name__ == "V1Itinerary":
            supply = json.loads(
                kwargs["user_prompt"].split("Planning candidate supply contract:\n", 1)[1]
            )
            for index, day in enumerate(self.responses[0].days):
                for activity in day.activities:
                    activity.source_place_id = supply["optional_canonical_ids"][index]
        return await super().generate_structured(**kwargs)

    async def generate_repair_structured(self, **kwargs):
        self.repair_calls += 1
        self.payload = json.loads(kwargs["user_prompt"])
        if self.behavior == "failure":
            raise RuntimeError("offline model failure")
        if self.behavior == "wait":
            await asyncio.sleep(10)
        if self.behavior == "cancel":
            raise asyncio.CancelledError()
        if self.behavior == "empty":
            return {"edits": []}
        if self.behavior in {"add", "existing_add", "unknown_id"}:
            candidate = (
                next(
                    c
                    for c in self.payload["addition_candidates"]
                    if next(
                        p
                        for p in self.payload["candidate_catalog"]
                        if p["place"]["place_id"] == c["place_id"]
                    )["origin"]
                    != "original_supply"
                )
                if self.behavior == "add"
                else self.payload["addition_candidates"][1]
            )
            return {
                "edits": [
                    {
                        "operation": "add",
                        "activity_id": None,
                        "date": "2026-09-12",
                        "place_id": "invented"
                        if self.behavior == "unknown_id"
                        else candidate["place_id"],
                        "start_time": "2026-09-12T14:00:00+10:00",
                        "end_time": "2026-09-12T15:00:00+10:00",
                    }
                ]
            }
        start, end = ("10:50", "11:50") if self.behavior == "partial" else ("11:30", "12:30")
        if self.behavior == "duration":
            end = "11:20"
        return {
            "edits": [
                {
                    "operation": "delete" if self.behavior == "delete" else "retime",
                    "activity_id": "two",
                    "date": "2026-09-12",
                    "place_id": None,
                    "start_time": None
                    if self.behavior == "delete"
                    else f"2026-09-12T{start}:00+10:00",
                    "end_time": None if self.behavior == "delete" else f"2026-09-12T{end}:00+10:00",
                }
            ]
        }


async def execute(model=None, places=None, runtime=None, **kwargs):
    from backend.app.runtime.config_loader import load_runtime_config

    config = kwargs.pop("runtime_config", None) or load_runtime_config()
    if not kwargs.pop("system_deletions", False):
        # These model-response fixtures exercise initialization/finalization of model edits.
        config = config.model_copy(
            update={"v3_repair": config.v3_repair.model_copy(update={"max_deletion_attempts": 0})}
        )
    model, places = model or Model(), places or Places()
    runtime = runtime or OwnedRetrieval()
    result = await run_v3(
        kwargs.pop("request", None) or make_request(),
        model,
        places,
        FakeWeatherProvider(),
        kwargs.pop("routes_provider", None) or FakeRoutesProvider(),
        reference_date=kwargs.pop("reference_date", date(2026, 9, 11)),
        retrieval_factory=lambda: runtime,
        development_timeout_seconds=kwargs.pop("development_timeout_seconds", 600),
        # Isolate existing conflict fixtures; default-policy coverage passes None explicitly.
        quantity_review_enabled=kwargs.pop("quantity_review_enabled", False),
        runtime_config=config,
        **kwargs,
    )
    return result, model, places, runtime


@pytest.mark.parametrize(
    "behavior,status",
    [
        ("complete", "ACCEPTED_COMPLETE"),
        ("partial", "ACCEPTED_PARTIAL"),
        ("empty", "REJECTED"),
        ("duration", "REJECTED"),
        ("failure", "REJECTED"),
    ],
)
def test_actual_repair_and_adopted_report(behavior, status):
    draft = primary()
    saved = draft.model_dump()
    result, model, places, runtime = asyncio.run(execute(Model(draft, behavior)))
    outcome = result.v3
    assert outcome.repair.status == status
    assert len(model.calls) == 1
    assert 1 <= model.repair_calls <= 6
    assert draft.model_dump() == saved
    assert outcome.original_report == outcome.repair.original_report
    assert result.generation_diagnostics == outcome.final_report.diagnostics
    assert result.itinerary.model_dump() == outcome.final_primary.model_dump()
    assert result.output_role_summary.scheduled_place_ids == ("poi-0-0", "poi-0-1", "poi-0-2")
    assert runtime.prepares == runtime.enters == runtime.closes == 1
    assert result.request_resources["closed"]
    assert places.nearby and len(places.nearby) <= 2
    if status == "ACCEPTED_PARTIAL":
        assert any(
            f.check == "overlap" and f.status == "CONFIRMED" for f in outcome.final_report.findings
        )
        assert outcome.repair.target_progress[0].outcome == "improved"
    if status == "REJECTED":
        assert outcome.final_primary.model_dump(
            exclude={"transfers", "route_diagnostics"}
        ) == outcome.draft.model_dump(exclude={"transfers", "route_diagnostics"})
        assert any(
            f.check == "overlap" and f.status == "CONFIRMED" for f in outcome.final_report.findings
        )
    assert outcome.draft_cost_projections == outcome.final_cost_projections


def test_quantity_explicit_off_skips_model_and_preserves_original_flow():
    result, model, places, _ = asyncio.run(execute(Model(primary(False))))
    assert not result.v3.quantity_review_enabled
    assert result.v3.scope is result.v3.repair is None
    assert model.repair_calls == 0 and len(model.calls) == 1
    assert len(places.nearby) == 1
    assert len(result.planning_supply.selected_place_ids) == 9
    assert any(
        f.check == "coverage" and f.status == "NEEDS_REVIEW"
        for f in result.v3.final_report.findings
    )


def test_quantity_yaml_default_repairs_sparse_days_without_expanding_permissions():
    result, model, _, _ = asyncio.run(
        execute(Model(primary(False), "existing_add"), quantity_review_enabled=None)
    )
    assert result.v3.quantity_review_enabled
    assert model.repair_calls > 0
    assert result.generation_diagnostics.days[0].distinct_main_poi_count == 2
    assert not result.v3.scope.permissions
    assert not result.v3.scope.revisits
    original = {a.activity_id: a for d in result.v3.draft.days for a in d.activities}
    final = {a.activity_id: a for d in result.itinerary.days for a in d.activities}
    assert all(final[aid] == activity for aid, activity in original.items())


def test_legal_identity_outside_original_supply_reaches_final_and_nearby(monkeypatch):
    from backend.app.versions.v3 import repair_transport

    original_present = repair_transport.present_transfers
    final_time_places = []

    def present(*args, places=(), **kwargs):
        final_time_places.extend(p.place_id for p in places)
        return original_present(*args, places=places, **kwargs)

    monkeypatch.setattr(repair_transport, "present_transfers", present)
    result, model, places, _ = asyncio.run(
        execute(Model(primary(False), "add"), places=ManyPlaces(), quantity_review_enabled=True)
    )
    repair = result.v3.repair
    assert repair.status == "ACCEPTED_PARTIAL", repair.reason
    added = set(repair.final_place_ids) - set(result.planning_supply.selected_place_ids)
    assert len(added) == 1
    assert added <= set(final_time_places)
    assert added <= set(result.v3.final_identity_ids)
    assert added <= set(result.output_role_summary.scheduled_place_ids)
    assert added <= {a["place_id"] for a in result.nearby_diagnostics["anchors"]}
    assert result.v3.draft.days[0].activities.__len__() == 1
    assert result.generation_diagnostics.days[0].distinct_main_poi_count == 2
    assert result.v3.original_report.diagnostics.days[0].distinct_main_poi_count == 1
    assert len(model.calls) == 1
    assert 1 <= model.repair_calls <= 6
    assert len(places.nearby) <= 2
    assert result.v3.quantity_review_enabled


def test_actual_serializer_overflow_is_repair_skip_not_invalid_input():
    draft = primary()
    draft.days[0].activities[0].notes = "large " * 260000
    result, model, places, _ = asyncio.run(execute(Model(draft)))
    assert result.v3.repair.status == "SKIPPED"
    assert "repair_input_overflow" in result.v3.reason
    assert model.repair_calls == 0 and places.nearby
    assert result.v3.final_primary.model_dump(
        exclude={"transfers", "route_diagnostics"}
    ) == result.v3.draft.model_dump(exclude={"transfers", "route_diagnostics"})


def test_model_timeout_uses_real_service_timer_and_preserves_draft(monkeypatch):
    from types import SimpleNamespace

    from backend.app.versions.v3 import repair_service

    timeout = asyncio.timeout
    monkeypatch.setattr(
        repair_service,
        "asyncio",
        SimpleNamespace(
            timeout=lambda seconds: timeout(0.01 if seconds <= 70 else seconds),
            CancelledError=asyncio.CancelledError,
        ),
    )
    result, model, places, _ = asyncio.run(execute(Model(behavior="wait")))
    assert result.v3.repair.reason == "model_failed_no_retry"
    assert result.v3.repair.rounds[-1].result.reason == "repair_timeout"
    assert (
        result.v3.final_primary.model_dump(exclude={"transfers", "route_diagnostics"})
        == result.v3.draft.model_dump(exclude={"transfers", "route_diagnostics"})
        and places.nearby
    )
    assert model.repair_calls == 1


def test_cancel_propagates_without_nearby_and_releases_owned_runtime():
    model, places, runtime = Model(behavior="cancel"), Places(), OwnedRetrieval()
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(execute(model, places, runtime))
    assert not places.nearby and runtime.closes == 1


def test_whole_request_expiry_during_primary_prevents_postwork(monkeypatch):
    clock = [monotonic()]

    class SlowModel(Model):
        primary_started = False
        primary_cancelled = False

        async def generate_structured(self, **kwargs):
            self.primary_started = True
            clock[0] += 601
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                self.primary_cancelled = True
                raise

    model, places, runtime = SlowModel(), Places(), OwnedRetrieval()

    async def scenario():
        # Freeze the monotonic time boundary so cold setup cannot choose the expiry phase.
        monkeypatch.setattr(asyncio.get_running_loop(), "time", lambda: clock[0])
        monkeypatch.setattr("backend.app.versions.v3.runner.monotonic", lambda: clock[0])
        monkeypatch.setattr("backend.app.versions.v3.resources.monotonic", lambda: clock[0])
        await execute(model, places, runtime)

    with pytest.raises(TimeoutError):
        asyncio.run(scenario())
    assert model.primary_started and model.primary_cancelled
    assert not places.nearby and model.repair_calls == 0
    assert runtime.enters == runtime.prepares == runtime.closes == 1


def test_deadline_includes_pre_graph_preparation():
    model, places = Model(), Places()

    def forbidden_factory():
        pytest.fail("An expired request must not create a retrieval runtime")

    with pytest.raises(TimeoutError):
        asyncio.run(
            run_v3(
                make_request(),
                model,
                places,
                FakeWeatherProvider(),
                FakeRoutesProvider(),
                reference_date=date(2026, 9, 11),
                retrieval_factory=forbidden_factory,
                development_timeout_seconds=600,
                request_started_at=monotonic() - 601,
            )
        )
    assert not places.search_requests and not places.nearby
    assert not model.calls and not model.semantic_calls and model.repair_calls == 0


def test_primary_failure_does_not_enter_repair_or_nearby():
    model, places, runtime = Model(), Places(), OwnedRetrieval()
    model.responses = [ValueError("invalid primary")]
    with pytest.raises(RuntimeError, match="generate_itinerary"):
        asyncio.run(execute(model, places, runtime))
    assert not places.nearby and model.repair_calls == 0 and runtime.closes == 1


def test_unresolved_required_preserves_preplanning_exit():
    from backend.app.schemas.interpreted_requirements import ClarificationRequired
    from backend.app.schemas.named_place_intent import NamedPlaceIntent
    from backend.tests.versions.v1.fakes import make_revised_extraction

    text = "Visit Missing Place."
    model, places = Model(), Places()
    model.responses = [
        make_revised_extraction(
            intents=(
                NamedPlaceIntent(
                    place_text="Missing Place",
                    inclusion="REQUIRED",
                    source_text=text,
                ),
            )
        )
    ]
    with pytest.raises(ClarificationRequired):
        asyncio.run(
            run_v3(
                make_request(text),
                model,
                places,
                FakeWeatherProvider(),
                FakeRoutesProvider(),
                reference_date=date(2026, 9, 11),
                development_timeout_seconds=600,
                retrieval_factory=lambda: pytest.fail("No retrieval before clarification"),
            )
        )
    assert not places.nearby and not model.repair_calls


def test_borrowed_runtime_is_prepared_once_and_not_closed():
    async def scenario():
        runtime = OwnedRetrieval()
        result = await run_v3(
            make_request(),
            Model(),
            Places(),
            FakeWeatherProvider(),
            FakeRoutesProvider(),
            reference_date=date(2026, 9, 11),
            development_timeout_seconds=600,
            retrieval_runtime=runtime,
        )
        assert runtime.prepares == 1 and runtime.closes == runtime.enters == 0
        assert not result.request_resources["owned"]

    asyncio.run(scenario())


@pytest.mark.parametrize("failure", [None, "prepare", "embedding", "search"])
def test_cross_phase_rag_cache_failures_and_initial_report_are_preserved(failure):
    from backend.app.schemas.interpreted_requirements import DiscoveryDraft
    from backend.tests.versions.v1.fakes import make_revised_extraction

    class Runtime(OwnedRetrieval):
        async def embed(self, texts):
            values = await super().embed(texts)
            if failure == "embedding":
                raise RuntimeError("fixture embedding failure")
            return values

        async def search(self, *args):
            rows = await super().search(*args)
            if failure == "search":
                raise TimeoutError("fixture SQL failure")
            return rows

    runtime = Runtime(fail=failure == "prepare")
    extraction = make_revised_extraction(experience=(("Museums", "crowding"),))
    extraction = extraction.model_copy(
        update={
            "time_protections": (),  # Synthetic current interpreter assessment.
            "visit_requirements": (),
            "discovery_intents": (
                DiscoveryDraft(
                    requirement_refs=("s0",), purpose="semantic_discovery", query_text="Museums"
                ),
            ),
        }
    )
    model = Model(primary(False), "existing_add")
    model.responses.insert(0, extraction)
    result, _, _, _ = asyncio.run(
        execute(
            model, runtime=runtime, request=make_request("Museums"), quantity_review_enabled=True
        )
    )
    assert result.v3.repair.status == "ACCEPTED_PARTIAL", result.v3.repair.reason
    assert len(model.calls) == 2 and 1 <= model.repair_calls <= 6
    assert runtime.prepares == runtime.enters == runtime.closes == 1
    assert runtime.embedding_sends == (0 if failure == "prepare" else 1)
    assert runtime.searches == (1 if failure in {None, "search"} else 0)
    assert result.v3.original_rag_discovery["retrieval_queries"] == (
        0 if failure in {"prepare", "embedding"} else 1
    )
    if failure:
        assert all(
            r in {"no_progress_requires_new_opportunity"}
            for r in result.v3.repair.candidate_preparation.exploration_reasons
        )
        assert result.v3.repair.counters.get("retrieval", 0) == 0
    else:
        # Structured soft-pace transport preparation may reuse a primary route.
        assert result.v3.repair.counters.get("cache_hits", 0) == 1
        assert result.v3.repair.counters.get("embedding", 0) == 0
        assert result.v3.repair.counters.get("retrieval", 0) == 0
        phases = [r["phase"] for r in result.request_resources["operations"]]
        assert phases == ["primary_discovery", "primary_discovery"]


def test_failed_details_not_reissued_and_existing_material_still_repairs():
    places = Places()
    places.details_failure_ids.add("poi-2-0")
    result, _, _, _ = asyncio.run(
        execute(Model(primary(False), "existing_add"), places=places, quantity_review_enabled=True)
    )
    assert result.v3.repair.status == "ACCEPTED_PARTIAL"
    assert [r.place_id for r in places.details_requests].count("poi-2-0") == 1
    assert result.v3.repair.counters.get("details", 0) == 0


def test_arbitrary_new_id_is_rejected_before_nearby():
    result, _, _, _ = asyncio.run(
        execute(Model(primary(False), "unknown_id"), quantity_review_enabled=True)
    )
    assert result.v3.repair.status == "REJECTED"
    assert "invented" not in result.v3.final_identity_ids
    assert "invented" not in result.output_role_summary.scheduled_place_ids
    assert result.v3.final_primary.model_dump(
        exclude={"transfers", "route_diagnostics"}
    ) == result.v3.draft.model_dump(exclude={"transfers", "route_diagnostics"})


def test_one_nearby_phase_attaches_independent_ledger_without_primary_cost_change(monkeypatch):
    from backend.app.integrations.models import PlaceCandidateDTO
    from backend.app.services.reference_discovery import ReferenceDiscoveryService

    phases = []
    actual = ReferenceDiscoveryService.discover

    async def observe(self, *args, **kwargs):
        phases.append(args[0].model_copy(deep=True))
        return await actual(self, *args, **kwargs)

    monkeypatch.setattr(ReferenceDiscoveryService, "discover", observe)

    class References(Places):
        async def search_nearby(self, request):
            response = await super().search_nearby(request)
            return response.model_copy(
                update={
                    "candidates": [
                        PlaceCandidateDTO(
                            place_id="nearby-only",
                            display_name="Nearby cafe",
                            primary_type="cafe",
                            location=request.center,
                            business_status="OPERATIONAL",
                            provider_rank=0,
                        )
                    ],
                    "actual_result_count": 1,
                }
            )

    result, _, _, _ = asyncio.run(execute(places=References()))
    assert len(phases) == 1 and phases[0] == result.v3.final_primary
    assert result.itinerary.reference_recommendations
    assert result.itinerary.model_dump(exclude={"reference_recommendations"}) == (
        result.v3.final_primary.model_dump(exclude={"reference_recommendations"})
    )
    assert "nearby-only" in result.nearby_ledger
    assert "nearby-only" not in result.v3.final_identity_ids
    assert result.output_role_summary.reference_place_ids == ("nearby-only",)
    assert result.v3.final_cost_projections == result.v3.draft_cost_projections


def test_real_task_cancellation_during_repair_stops_all_postwork():
    async def scenario():
        entered = asyncio.Event()

        class Waiting(Model):
            async def generate_repair_structured(self, **kwargs):
                entered.set()
                await asyncio.sleep(10)

        model, places, runtime = Waiting(), Places(), OwnedRetrieval()
        task = asyncio.create_task(execute(model, places, runtime))
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert not places.nearby and runtime.closes == 1

    asyncio.run(scenario())


def test_short_remaining_request_skips_repair_but_allows_nearby():
    result, model, places, _ = asyncio.run(execute(development_timeout_seconds=5))
    assert result.v3.repair.reason == "insufficient_stage_time"
    assert not model.repair_calls and places.nearby


def test_actual_v3_cli_serializes_adopted_result(tmp_path, monkeypatch, capsys):
    from backend.app.versions.v3 import runner

    runtime = OwnedRetrieval()
    monkeypatch.setattr(runner, "RuntimeRetrieval", lambda config: runtime)
    path = tmp_path / "request.json"
    path.write_text(make_request().model_dump_json(), encoding="utf-8")
    code = runner.main(
        [
            "--input-json",
            str(path),
            "--reference-date",
            "2026-09-11",
            "--development-timeout-seconds",
            "600",
            "--no-repair-quantity-review",
        ],
        llm_client=Model(),
        places_provider=Places(),
        weather_provider=FakeWeatherProvider(),
        routes_provider=FakeRoutesProvider(),
    )
    assert code == 0
    result = json.loads(capsys.readouterr().out)
    assert result["system_version"] == "v3"
    assert result["v3"]["repair"]["status"] == "ACCEPTED_PARTIAL"
    assert result["v3"]["repair"]["counters"]["deterministic_attempts"] >= 1
    assert any(r["strategy"] == "system_delete" for r in result["v3"]["repair"]["rounds"])
    assert result["v3"]["quantity_review_enabled"] is False
    assert runtime.closes == 1


def test_actual_chain_has_no_unmocked_network_or_database(monkeypatch):
    import socket

    import httpx
    import psycopg

    def forbidden(*args, **kwargs):
        pytest.fail("Unmocked network or database acquisition")

    async def scenario():
        # Windows creates its socketpair before this stricter guard is installed.
        monkeypatch.setattr(socket.socket, "connect", forbidden)
        monkeypatch.setattr(socket.socket, "connect_ex", forbidden)
        monkeypatch.setattr(httpx.AsyncClient, "send", forbidden)
        monkeypatch.setattr(psycopg.AsyncConnection, "connect", forbidden)
        result, _, _, _ = await execute()
        assert result.v3.repair.status == "ACCEPTED_COMPLETE"

    asyncio.run(scenario())


@pytest.mark.parametrize("route_failure", [False, True])
def test_actual_transit_route_rechecks_keep_original_and_augmented_reports_distinct(route_failure):
    from backend.app.schemas.trip_intent import TransportPreferenceIntent
    from backend.tests.versions.v1.fakes import make_revised_extraction

    class RetimeFirst(Model):
        async def generate_repair_structured(self, **kwargs):
            patch = await super().generate_repair_structured(**kwargs)
            patch["edits"][0].update(
                activity_id="activity-1",
                start_time="2026-09-12T08:00:00+10:00",
                end_time="2026-09-12T10:00:00+10:00",
            )
            return patch

    class Routes(FakeRoutesProvider):
        async def compute_route_matrix(self, request):
            response = await super().compute_route_matrix(request)
            if len(request.origins) == len(request.destinations) == 1:
                if route_failure:
                    raise RuntimeError("Optional route failed")
                response.elements[0]["duration"] = "600s"
            return response

    model, routes = RetimeFirst(), Routes()
    model.responses.insert(
        0,
        make_revised_extraction(
            transport=TransportPreferenceIntent(mode="TRANSIT", source_text="Use public transport.")
        ),
    )
    result, _, _, _ = asyncio.run(
        execute(model, request=make_request("Use public transport."), routes_provider=routes)
    )
    repair = result.v3.repair
    assert repair.status == "ACCEPTED_COMPLETE", repair.reason
    assert repair.counters["routes"] == repair.counters["elements"] == 2
    assert any(
        f.check == "route" and f.status == "UNKNOWN" for f in result.v3.original_report.findings
    )
    assert any(
        f.check == "route" and f.status == ("UNKNOWN" if route_failure else "PASS")
        for f in result.v3.final_report.findings
    )
    if not route_failure:
        assert any(
            f.check == "route" and f.status == "CONFIRMED"
            for f in repair.reassessed_original_report.findings
        )
    supplemental = [r for r in routes.requests if len(r.origins) == len(r.destinations) == 1]
    assert len({r.departure_time for r in supplemental}) == 2


def test_v3_outcome_trace_truncation_retains_individual_artifact_markers():
    from backend.app.runtime.config_loader import load_runtime_config

    config = load_runtime_config()
    config = config.model_copy(
        update={"trace": config.trace.model_copy(update={"max_payload_bytes": 100})}
    )
    from uuid import uuid4

    from backend.app.observability.run_trace import NullRunTracer

    class Trace(NullRunTracer):
        def __init__(self):
            super().__init__(uuid4())
            self.events = {}

        def event(self, name, value=None):
            self.events[name] = value

    tracer = Trace()
    result, _, _, _ = asyncio.run(
        execute(Model(behavior="empty"), runtime_config=config, tracer=tracer)
    )
    assert result.v3.repair.status == "REJECTED"
    assert result.v3.repair.rounds[0].result.artifact_status["proposal"].startswith("truncated:")
    assert result.v3.repair.artifact_status["proposal"] == "not_constructed"

    assert tracer.events["v3_finalized"]["truncated"]
    assert "v3_repair_patch" in tracer.events["v3_finalized"]["artifact_events"]
    assert tracer.events["v3_repair_patch"]["artifact_status"] == "not_executed"
    assert result.v3.repair.reason == "no_new_material_after_empty_proposal"
    assert tracer.events["v3_repair_proposal"]["artifact_status"] == "not_constructed"
    assert tracer.events["v3_repair_material_feedback"]["truncated"]


def test_api_route_conflict_authorizes_removal_with_unresolved_coverage_child():
    result, _, _, _ = asyncio.run(execute(Model(behavior="delete")))
    assert result.v3.repair.status == "ACCEPTED_PARTIAL"
    assert len(result.itinerary.days[0].activities) == 1
    assert any(r.status == "unresolved" for r in result.v3.repair.related_targets)


def test_mixed_drive_adoption_reaches_output_and_nearby_unchanged():
    class MixedRoutes(FakeRoutesProvider):
        async def compute_route_matrix(self, request):
            value = await super().compute_route_matrix(request)
            if request.travel_mode == "TRANSIT":
                raise RuntimeError("fixture transit unavailable")
            return value.model_copy(
                update={
                    "elements": [
                        dict(
                            e,
                            duration="4200s" if request.travel_mode == "WALK" else "1080s",
                            distanceMeters=4000,
                        )
                        for e in value.elements
                    ]
                }
            )

    routes = MixedRoutes()
    result, model, places, owner = asyncio.run(
        execute(
            Model(primary(False), "existing_add"),
            routes_provider=routes,
            quantity_review_enabled=True,
        )
    )
    assert result.v3.repair.status.startswith("ACCEPTED"), result.v3.repair.reason
    transfers = result.v3.final_primary.transfers
    assert transfers and transfers[0].mode == "DRIVE"
    assert transfers[0].provider_duration_seconds == 1080 and transfers[0].reserve_seconds == 600
    assert transfers[0].validation_state == "PASS"
    assert result.itinerary.transfers == transfers
    assert any(f.check == "route" and f.status == "PASS" for f in result.v3.final_report.findings)
    assert len(model.calls) == 1 and owner.closes == 1 and places.nearby
    assert result.request_resources["closed"]
