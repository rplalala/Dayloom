"""Best-effort local observations, independent of tracing and usage collection."""

import asyncio
import hashlib
import json

import pytest

from backend.app.observability.mechanism_capture import capture_attempt
from backend.app.observability.mechanism_observation import model_projection, model_submitted


def capture(invoke, rows, **kwargs):
    return capture_attempt(
        invoke,
        group_id="g",
        run_id="r",
        version="v3",
        input_sha256="a" * 64,
        serialize=lambda value: json.dumps(value).encode(),
        sink=rows.append,
        **kwargs,
    )


def test_prepared_projection_is_not_submission_and_injected_client_is_partial():
    rows = []

    async def invoke():
        with model_projection("primary", [{"source_refs": ["official_web:one"]}]):
            return "ok"

    assert asyncio.run(capture(invoke, rows)) == "ok"
    assert rows[0]["occurrences"] == []
    assert rows[0]["prepared_calls"][0]["submitted"] is False
    assert rows[0]["collection_status"] == "partial"
    assert rows[0]["result_sha256"] == hashlib.sha256(b'"ok"').hexdigest()


def test_submission_is_observed_once_per_call_without_raw_prompts():
    rows = []

    async def invoke():
        with model_projection("repair", [{"source_refs": ["official_web:one"]}], round_index=2):
            model_submitted()
            return "ok"

    asyncio.run(capture(invoke, rows))
    row = rows[0]["occurrences"][0]
    assert row["reason"] == "model_input_submission"
    assert row["round_index"] == 2
    assert row["representation"] == [{"source_refs": ["official_web:one"]}]
    assert "prompt" not in json.dumps(rows)


@pytest.mark.parametrize("error", [RuntimeError("private"), asyncio.CancelledError()])
def test_capture_preserves_primary_exception_and_context(error):
    rows = []

    async def invoke():
        raise error

    with pytest.raises(type(error)):
        asyncio.run(capture(invoke, rows))
    assert rows[0]["result_sha256"] is None
    assert rows[0]["collection_status"] == "partial"


def test_bad_sink_and_serializer_do_not_replace_result():
    async def invoke():
        return 7

    def fail(value):
        raise ValueError("local failure")

    assert (
        asyncio.run(
            capture_attempt(
                invoke,
                group_id="g",
                run_id="r",
                version="v1",
                input_sha256="a" * 64,
                serialize=fail,
                sink=fail,
            )
        )
        == 7
    )


def test_real_rule_selection_retains_exact_date_and_intervals():
    from backend.app.versions.v3.repair_acceptance import assess
    from backend.tests.versions.v3.test_repair import context, draft
    from backend.tests.versions.v3.test_validation import DAY, effective

    rows = []

    async def invoke():
        return assess(
            draft(), context(effective_places=(effective(source_ref="official_web:a"),))
        ).model_dump(mode="json")

    asyncio.run(capture(invoke, rows))
    assert rows[0]["occurrences"], rows[0]["diagnostics"]
    occurrence = rows[0]["occurrences"][0]
    assert occurrence["reason"] == "rule_selection"
    assert occurrence["representation"]["date"] == str(DAY)
    assert occurrence["representation"]["intervals"]


def test_real_adapter_submission_preserves_messages_options_and_result(monkeypatch):
    from backend.app.schemas.itinerary_projection import V1Itinerary
    from backend.tests.llm.azure_foundry.test_client import (
        FakeChatOpenAI,
        FoundryPrimaryItineraryDTO,
        make_activity,
        make_client,
    )

    rows = []
    FakeChatOpenAI.response = FoundryPrimaryItineraryDTO(
        output_version="itinerary_3",
        destination="Kyoto",
        start_date="2026-10-01",
        end_date="2026-10-01",
        days=[
            {
                "date": "2026-10-01",
                "activities": [make_activity().model_dump(exclude={"transport"})],
            }
        ],
    )

    async def invoke():
        client = make_client(monkeypatch)
        with model_projection("primary", [{"source_refs": ["official_web:one"]}]):
            result = await client.generate_structured(
                system_prompt="exact system", user_prompt="exact user", response_schema=V1Itinerary
            )
        return result.model_dump(mode="json")

    baseline = asyncio.run(invoke())
    messages = FakeChatOpenAI.structured_model.messages
    options = FakeChatOpenAI.structured_kwargs.copy()
    recorded = asyncio.run(capture(invoke, rows))
    assert recorded == baseline
    assert FakeChatOpenAI.structured_model.messages == messages
    assert FakeChatOpenAI.structured_kwargs == options
    assert FakeChatOpenAI.structured_model.invocation_count == 1
    assert rows[0]["occurrences"][0]["reason"] == "model_input_submission"


def test_real_multiround_injected_client_preserves_prompts_attempts_and_adoption():
    from time import monotonic

    from backend.app.versions.v3.repair_service import run_repair_stage
    from backend.tests.versions.v3.test_multiround import SequenceModel
    from backend.tests.versions.v3.test_repair import context, edit, overlap_draft, scope_for

    async def execute(model):
        original, ctx = overlap_draft(), context()
        return await run_repair_stage(
            original, ctx, scope_for(original, ctx), model=model, request_deadline=monotonic() + 600
        )

    off = SequenceModel([[edit("10:50", "11:50")], RuntimeError("offline failure")])
    baseline = asyncio.run(execute(off))
    on = SequenceModel([[edit("10:50", "11:50")], RuntimeError("offline failure")])
    rows = []
    recorded = asyncio.run(
        capture_attempt(
            lambda: execute(on),
            group_id="g",
            run_id="r",
            version="v3",
            input_sha256="a" * 64,
            serialize=lambda r: r.model_dump_json(),
            sink=rows.append,
        )
    )
    assert recorded.final == baseline.final
    assert recorded.status == baseline.status
    assert on.inputs == off.inputs
    assert on.calls == off.calls == 2
    assert rows[0]["occurrences"] == []
    assert len(rows[0]["prepared_calls"]) == 2
    assert rows[0]["collection_status"] == "partial"


def test_capacity_and_secret_redaction_keep_result_and_mark_capture_partial():
    rows = []

    async def invoke():
        with model_projection(
            "primary", {"source_refs": ["official_web:one"], "value_text": "Bearer credential"}
        ):
            model_submitted()
        with model_projection(
            "primary", {"source_refs": ["official_web:two"], "value_text": "x" * 200}
        ):
            model_submitted()
        return "ok"

    assert asyncio.run(capture(invoke, rows, max_bytes=100)) == "ok"
    assert rows[0]["collection_status"] == "partial"
    assert rows[0]["occurrences"] == []
    assert "credential" not in json.dumps(rows)


def test_real_v1_graph_is_unchanged_and_input_budget_abort_has_no_submission():
    from datetime import date

    from backend.app.runtime.config_loader import load_runtime_config
    from backend.app.services.generation_resources import GenerationResourceError
    from backend.app.versions.v1.runner import run_v1
    from backend.tests.request_fixtures import make_request
    from backend.tests.versions.v1.fakes import (
        FakePlacesProvider,
        FakeRoutesProvider,
        FakeWeatherProvider,
        RevisedFakeLLM,
        make_itinerary,
        make_revised_extraction,
    )

    async def execute(llm, config=None):
        return await run_v1(
            make_request(additional_preferences="Plan two days in Sydney."),
            llm,
            FakePlacesProvider(),
            FakeWeatherProvider(),
            FakeRoutesProvider(),
            reference_date=date(2026, 9, 11),
            runtime_config=config,
        )

    baseline_model = RevisedFakeLLM([make_revised_extraction(), make_itinerary()])
    baseline = asyncio.run(execute(baseline_model))
    recorded_model = RevisedFakeLLM([make_revised_extraction(), make_itinerary()])
    rows = []
    result = asyncio.run(
        capture_attempt(
            lambda: execute(recorded_model),
            group_id="g",
            run_id="r",
            version="v1",
            input_sha256="a" * 64,
            serialize=lambda r: r.model_dump_json(),
            sink=rows.append,
        )
    )
    assert result.itinerary == baseline.itinerary
    assert recorded_model.calls == baseline_model.calls
    config = load_runtime_config()
    limited = config.model_copy(
        update={
            "main_generation": config.main_generation.model_copy(
                update={"enabled": True, "input_tokens": 1}
            )
        }
    )
    aborted = RevisedFakeLLM([make_revised_extraction(), make_itinerary()])
    rows = []
    with pytest.raises(GenerationResourceError):
        asyncio.run(
            capture_attempt(
                lambda: execute(aborted, limited),
                group_id="g",
                run_id="r",
                version="v1",
                input_sha256="a" * 64,
                serialize=lambda r: r.model_dump_json(),
                sink=rows.append,
            )
        )
    assert rows[0]["occurrences"] == []
    assert rows[0]["prepared_calls"] == []


def test_typed_accepted_catalog_and_actual_rule_are_captured_without_model_or_usage_calls():
    from datetime import time

    from backend.app.evidence.official_models import OfficialCurrentEvidence
    from backend.app.observability.mechanism_observation import accepted_catalog
    from backend.app.policies.official_evidence_resolver import resolve_effective_evidence
    from backend.app.versions.v3.repair_acceptance import assess
    from backend.tests.versions.v3.test_repair import context, draft, place
    from backend.tests.versions.v3.test_validation import DAY, NOW

    claim = OfficialCurrentEvidence(
        place_id="a",
        place_name="a",
        source_key="source-revision-one",
        information_need="special_date_hours",
        claim_kind="special_hours",
        value_text="9 to 17",
        source_kind="fetched_html",
        source_url="https://venue.example/hours",
        supporting_excerpt="Open 9 to 17 on the fixture date",
        subject_scope="whole_venue",
        temporal_basis="explicit_date_or_range",
        applicable_start_date=DAY,
        applicable_end_date=DAY,
        schedule_scope="daily",
        opens_at=time(9),
        closes_at=time(17),
        authority_basis="places_first_party_website",
        retrieved_at=NOW,
        source_ref="official_web:a",
    )
    effective = resolve_effective_evidence(place(), (claim,), trip_start=DAY, trip_end=DAY)
    rows = []

    async def invoke():
        accepted_catalog((claim,))
        assess(draft(), context(effective_places=(effective,)))
        return {"system_version": "v3"}

    assert asyncio.run(capture(invoke, rows)) == {"system_version": "v3"}
    assert len(rows[0]["catalog"]) == 1
    assert rows[0]["catalog"][0]["claim"]["applicable_start_date"] == str(DAY)
    assert rows[0]["occurrences"]
    assert all(row["reason"] == "rule_selection" for row in rows[0]["occurrences"])
    assert rows[0]["prepared_calls"] == []


def test_cancelled_recording_and_failed_call_preserve_original_outcomes():
    rows = []

    async def invoke():
        with model_projection("repair", [], round_index=1):
            model_submitted()
            raise RuntimeError("private provider failure")

    with pytest.raises(RuntimeError):
        asyncio.run(capture(invoke, rows))
    assert rows[0]["prepared_calls"][0]["outcome"] == "failed"
    assert rows[0]["occurrences"][0]["reason"] == "model_input_submission"

    async def complete():
        return "ok"

    def cancelled(value):
        raise asyncio.CancelledError()

    assert (
        asyncio.run(
            capture_attempt(
                complete,
                group_id="g",
                run_id="r",
                version="v1",
                input_sha256="a" * 64,
                serialize=cancelled,
                sink=cancelled,
            )
        )
        == "ok"
    )
