"""Explanation-only recovery through the real Repair service, without network access."""

import asyncio
import copy
import json

import pytest

from backend.app.versions.v3.repair_models import RepairEdit
from backend.app.versions.v3.repair_service import run_repair_once
from backend.tests.versions.v3.test_repair import Routes, context, edit, overlap_draft, scope_for


class ReasonModel:
    def __init__(self, patch):
        self.patch = patch
        self.calls = self.compressions = 0

    async def generate_repair_structured(self, **kwargs):
        self.calls += 1
        kwargs["usage_callback"].usage_metadata["fixture"] = {
            "input_tokens": 100,
            "output_tokens": 50,
            "total_tokens": 150,
        }
        return copy.deepcopy(self.patch)

    async def compress_repair_reasons_structured(self, **kwargs):
        self.compressions += 1
        self.compression_input = json.loads(kwargs["user_prompt"])
        kwargs["usage_callback"].usage_metadata["fixture"] = {
            "input_tokens": 70,
            "output_tokens": 30,
            "total_tokens": 100,
        }
        return {
            "reasons": [
                {"reason_ref": r["reason_ref"], "reason": "Route evidence remains unavailable."}
                for r in self.compression_input["reasons"]
            ]
        }


def setup(reasons):
    original, ctx = overlap_draft(), context()
    scope = scope_for(original, ctx)
    patch = {
        "edits": [edit()],
        "target_dispositions": [
            {"target_id": scope.target_ids[0], "disposition": "unresolved", "reason": reason}
            for reason in reasons
        ],
    }
    return original, ctx, scope, patch


def run(model, fixture, **kwargs):
    original, ctx, scope, _ = fixture
    return asyncio.run(
        run_repair_once(
            original,
            ctx,
            scope,
            model=model,
            routes_provider=Routes(),
            request_deadline=kwargs.pop("request_deadline", 1000),
            clock=kwargs.pop("clock", lambda: 100),
            **kwargs,
        )
    )


def test_only_overlong_reasons_use_one_batch_and_keep_edits_dispositions_and_originals():
    fixture = setup(["x" * 255, "y" * 300, "z" * 240])
    model = ReasonModel(fixture[-1])
    result = run(model, fixture)
    assert result.status == "ACCEPTED_COMPLETE", result.reason
    assert model.calls == model.compressions == 1
    assert result.counters["model"] == result.counters["reason_compression"] == 1
    assert len(model.compression_input["reasons"]) == 2
    assert result.parsed_patch.edits[0] == RepairEdit.model_validate(fixture[-1]["edits"][0])
    assert [d.disposition for d in result.parsed_patch.target_dispositions] == ["unresolved"] * 3
    assert result.parsed_patch.target_dispositions[2].reason == "z" * 240
    assert result.reason_compression["original_patch"] == fixture[-1]
    assert model.patch == fixture[-1]
    assert result.reason_compression["status"] == "accepted"
    assert result.reason_compression["usage"]["fixture"]["total_tokens"] == 100
    assert result.usage["fixture"]["total_tokens"] == 250


def test_exactly_240_unicode_characters_do_not_call_compression():
    fixture = setup(["🌏" * 240])
    model = ReasonModel(fixture[-1])
    result = run(model, fixture)
    assert result.status == "ACCEPTED_COMPLETE", result.reason
    assert model.compressions == 0
    assert result.reason_compression == {}


@pytest.mark.parametrize(
    "bad",
    [
        {"reasons": [{"reason_ref": "r01", "reason": "x" * 241}]},
        {"reasons": [{"reason_ref": "other", "reason": "No route."}]},
        {"reasons": []},
        {"reasons": [{"reason_ref": "r01", "reason": ""}]},
        {"reasons": [{"reason_ref": "r01", "reason": 5}]},
        {"reasons": [{"reason_ref": "r01", "reason": "No route.", "disposition": "proposed"}]},
        {"reasons": [{"reason_ref": "r01", "reason": "No route."}] * 2},
        RuntimeError("provider failure"),
        TimeoutError("provider deadline"),
    ],
)
def test_failed_compression_is_not_retried_or_truncated_and_keeps_usage(bad):
    fixture = setup(["x" * 255])

    class BadModel(ReasonModel):
        async def compress_repair_reasons_structured(self, **kwargs):
            await super().compress_repair_reasons_structured(**kwargs)
            if isinstance(bad, BaseException):
                raise bad
            return bad

    model = BadModel(fixture[-1])
    result = run(model, fixture)
    assert result.status == "REJECTED"
    assert result.final == fixture[0] and result.parsed_patch is None
    assert model.compressions == result.counters["reason_compression"] == 1
    assert result.reason == (
        "reason_compression_timeout"
        if isinstance(bad, TimeoutError)
        else "reason_compression_failed"
    )
    assert result.reason_compression["original_patch"] == fixture[-1]
    assert result.usage["fixture"]["total_tokens"] == 250
    assert result.reason_compression["actual_cost_usd"] is None


@pytest.mark.parametrize(
    "change", ["bad_edit", "extra", "unauthorized_target", "invalid_disposition"]
)
def test_other_patch_errors_never_trigger_compression(change):
    fixture = setup(["x" * 255])
    patch = fixture[-1]
    if change == "bad_edit":
        patch["edits"][0]["operation"] = "invent"
    elif change == "extra":
        patch["extra"] = True
    elif change == "unauthorized_target":
        patch["target_dispositions"][0]["target_id"] = "unauthorized"
    else:
        patch["target_dispositions"][0]["disposition"] = "invent"
    model = ReasonModel(patch)
    result = run(model, fixture)
    assert result.status == "REJECTED" and model.compressions == 0


@pytest.mark.parametrize(
    "limits,reason",
    [
        ({"max_calls": 0}, "reason_compression_budget_exhausted"),
        ({"input_tokens": 1}, "reason_compression_input_overflow"),
    ],
)
def test_compression_denial_occurs_before_a_charge_or_send(limits, reason):
    from backend.tests.versions.v3.test_multiround import policy

    fixture = setup(["x" * 255])
    model = ReasonModel(fixture[-1])
    result = run(model, fixture, policy=policy(reason_compression=limits))
    assert result.reason == reason and model.compressions == 0
    assert result.counters.get("reason_compression", 0) == 0
    assert result.reason_compression["usage_status"] == "not_called"


def test_only_one_compression_is_available_across_rounds_and_proposal_budget_is_separate():
    from backend.app.versions.v3.repair_service import run_repair_stage
    from backend.tests.versions.v3.test_multiround import policy

    fixture = setup(["x" * 255])
    fixture[-1]["edits"] = []
    model = ReasonModel(fixture[-1])
    result = asyncio.run(
        run_repair_stage(
            *fixture[:3],
            model=model,
            routes_provider=Routes(),
            request_deadline=1000,
            clock=lambda: 100,
            policy=policy(max_rounds=2, max_model_calls=2),
        )
    )
    assert model.calls == 2 and model.compressions == 1
    assert result.counters["model"] == 2 and result.counters["reason_compression"] == 1
    assert (
        result.reason
        == result.rounds[-1].continuation_reason
        == "reason_compression_budget_exhausted"
    )
    assert result.rounds[0].result.parsed_patch.edits == ()
    assert result.final == fixture[0] and result.status == "REJECTED"


def test_failed_later_compression_preserves_the_best_retained_result():
    from backend.app.versions.v3.repair_service import run_repair_stage

    fixture = setup(["x" * 255])

    class PartialModel(ReasonModel):
        async def generate_repair_structured(self, **kwargs):
            raw = await super().generate_repair_structured(**kwargs)
            if self.calls == 1:
                raw["edits"] = [edit("10:50", "11:50")]
                raw["target_dispositions"] = []
            return raw

        async def compress_repair_reasons_structured(self, **kwargs):
            await super().compress_repair_reasons_structured(**kwargs)
            raise TimeoutError("failed later compression")

    model = PartialModel(fixture[-1])
    result = asyncio.run(
        run_repair_stage(
            *fixture[:3],
            model=model,
            routes_provider=Routes(),
            request_deadline=1000,
            clock=lambda: 100,
        )
    )
    assert result.status == "ACCEPTED_PARTIAL" and result.selected_round_index == 1
    assert result.final == result.rounds[0].adopted != fixture[0]
    assert result.reason == "reason_compression_timeout"
    assert model.calls == 2 and model.compressions == 1


@pytest.mark.parametrize(
    "elapsed,expected_timeout,reason",
    [
        (69, 30, None),
        (115, 15, None),
        (131, None, "insufficient_time_for_rechecks"),
    ],
)
def test_compression_uses_remaining_round_time_without_resetting_deadlines(
    elapsed, expected_timeout, reason
):
    now = [100.0]
    fixture = setup(["x" * 255])

    class TimedModel(ReasonModel):
        async def generate_repair_structured(self, **kwargs):
            raw = await super().generate_repair_structured(**kwargs)
            now[0] += elapsed
            return raw

    model = TimedModel(fixture[-1])
    result = run(model, fixture, clock=lambda: now[0])
    if expected_timeout is None:
        assert result.reason == reason and model.compressions == 0
    else:
        assert result.status == "ACCEPTED_COMPLETE", result.reason
        assert result.reason_compression["timeout_seconds"] == expected_timeout
        assert result.timing["round_deadline"] == 250


def test_late_compression_cannot_spend_the_recheck_reserve():
    fixture = setup(["x" * 255])
    now = [100.0]

    class LateModel(ReasonModel):
        async def compress_repair_reasons_structured(self, **kwargs):
            raw = await super().compress_repair_reasons_structured(**kwargs)
            now[0] += 131
            return raw

    model = LateModel(fixture[-1])
    result = run(model, fixture, clock=lambda: now[0])
    assert result.reason == "reason_compression_deadline" and result.final == fixture[0]
    assert model.compressions == 1 and result.reason_compression["elapsed_seconds"] == 131


def test_cancellation_propagates_with_a_terminal_attempt_record():
    fixture = setup(["x" * 255])

    class CancelModel(ReasonModel):
        async def compress_repair_reasons_structured(self, **kwargs):
            await super().compress_repair_reasons_structured(**kwargs)
            raise asyncio.CancelledError()

    class Trace:
        def __init__(self):
            self.events = []

        def event(self, name, value):
            self.events.append((name, value))

    trace = Trace()
    model = CancelModel(fixture[-1])
    with pytest.raises(asyncio.CancelledError):
        run(model, fixture, tracer=trace)
    record = next(
        v["value"] for n, v in trace.events if n == "v3_repair_reason_compression_attempt"
    )
    assert record["status"] == "cancelled" and record["attempted"]
    assert record["usage"]["fixture"]["total_tokens"] == 100
    assert model.compressions == 1


def test_missing_compression_usage_is_explicit_and_does_not_become_zero_cost():
    fixture = setup(["x" * 255])

    class MissingUsageModel(ReasonModel):
        async def compress_repair_reasons_structured(self, **kwargs):
            raw = await super().compress_repair_reasons_structured(**kwargs)
            kwargs["usage_callback"].usage_metadata.clear()
            return raw

    result = run(MissingUsageModel(fixture[-1]), fixture)
    assert result.status == "ACCEPTED_COMPLETE"
    assert result.reason_compression["usage_status"] == "unavailable"
    assert result.reason_compression["actual_cost_usd"] is None
    assert result.usage_status == "partial"
    assert result.usage["fixture"]["total_tokens"] == 150


@pytest.mark.parametrize("missing_usage", [False, True])
@pytest.mark.parametrize("malformed", [False, True])
def test_real_client_compression_is_a_separate_native_usage_and_cost_event(
    monkeypatch, missing_usage, malformed
):
    from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
    from langchain_core.messages import AIMessage
    from langchain_core.runnables import RunnableLambda

    from backend.app.observability.usage_capture import capture_attempt
    from backend.evaluation.cost_report import build_cost_report
    from backend.tests.evaluation.test_cost_report import prices
    from backend.tests.llm.azure_foundry.test_client import make_client

    fixture = setup(["x" * 255])
    raw = {
        "edits": [],
        "target_dispositions": [
            {"target_id": "t01", "disposition": "unresolved", "reason": "x" * 255}
        ],
    }
    compressed = {"reasons": [{"reason_ref": "r01", "reason": "No supported route."}]}
    if malformed:
        compressed["reasons"][0]["disposition"] = "proposed"

    class Port(FakeMessagesListChatModel):
        @property
        def _identifying_params(self):
            return {"model": "test"}

        def with_structured_output(self, *args, **kwargs):
            return self | RunnableLambda(lambda message: json.loads(message.content))

    client = make_client(monkeypatch)
    client._chat_model = Port(
        responses=[
            AIMessage(
                content=json.dumps(raw),
                response_metadata={"model_name": "test"},
                usage_metadata={
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "total_tokens": 150,
                    "input_token_details": {"cache_read": 0},
                },
            ),
            AIMessage(
                content=json.dumps(compressed),
                response_metadata={"model_name": "test"},
                usage_metadata=None
                if missing_usage
                else {
                    "input_tokens": 70,
                    "output_tokens": 30,
                    "total_tokens": 100,
                    "input_token_details": {"cache_read": 0},
                },
            ),
        ]
    )
    rows = []

    async def invoke():
        return await run_repair_once(
            *fixture[:3],
            model=client,
            routes_provider=Routes(),
            request_deadline=1000,
            clock=lambda: 100,
        )

    result = asyncio.run(
        capture_attempt(
            invoke,
            group_id="g",
            run_id="r",
            version="v3",
            sink=rows.append,
            serialize=lambda value: value.model_dump_json().encode(),
            adapter_coverage="default_adapters",
        )
    )
    usage = rows[0]
    assert len(usage["model_calls"]) == 2
    assert [m["model"] for m in usage["model_calls"]] == ["test", "test"]
    assert [m["stage"] for m in usage["model_calls"]] == [
        "repair_model",
        "repair_reason_compression",
    ]
    assert len(usage["repair_summary"]["model_event_ids"]) == 2
    assert result.reason_compression["response"] == compressed
    if malformed:
        assert result.reason == "reason_compression_failed" and result.parsed_patch is None
        assert result.final == fixture[0]
    else:
        assert result.parsed_patch.target_dispositions[0].reason == "No supported route."
    assert usage["model_calls"][1]["total_tokens"] == (None if missing_usage else 100)
    catalog = prices()
    catalog["rows"] = [catalog["rows"][0]]
    catalog["rows"][0].update(valid_from="2000-01-01", valid_until="2100-01-01")
    catalog["rows"][0]["match"].update(provider="langchain", operation="chat_model")
    # Synthetic known rates: (170 input * 2 + 80 output * 4) / 1e6 = .00066.
    report = build_cost_report([{"sha256": "a" * 64, "usage": usage}], catalog)["runs"][0]
    assert report["best_available_total"] == (None if missing_usage else "0.00066"), json.dumps(
        report["events"]
    )
    assert report["unpriced_event_count"] == (1 if missing_usage else 0)
    if missing_usage:
        assert report["best_available_observed_subtotal"] == "0.0004"


def test_failed_compression_budget_and_timeout_survive_truncated_trace(tmp_path):
    from dataclasses import replace

    from backend.app.observability.run_trace import FileRunTracer, TracePayloadMode
    from backend.app.runtime.config_loader import load_runtime_config, runtime_config_snapshot
    from backend.tests.observability.test_run_trace import _context

    fixture = setup(["x" * 255])

    class TimeoutModel(ReasonModel):
        async def compress_repair_reasons_structured(self, **kwargs):
            await super().compress_repair_reasons_structured(**kwargs)
            raise TimeoutError("controlled timeout")

    snapshot, digest = runtime_config_snapshot(load_runtime_config())
    tracer = FileRunTracer(
        replace(_context(), runtime_config=snapshot, runtime_config_sha256=digest),
        root=tmp_path,
        payload_mode=TracePayloadMode.METADATA,
        max_payload_bytes=100,
    )
    result = run(TimeoutModel(fixture[-1]), fixture, tracer=tracer, audit_max_bytes=100)
    assert result.reason == "reason_compression_timeout"
    tracer.finish(status="completed", requirements=None, tool_usage={}, outcome=None)
    summary = json.loads((tracer.run_directory / "budget.json").read_text())
    compression = summary["stages"]["repair_reason_compression"]
    assert compression["limits"]["max_calls"] == 1
    assert compression["observed"]["attempts"] == 1
    assert compression["calls"][0]["timeout_seconds"] == 30
    assert compression["calls"][0]["usage"]["total_tokens"] == 100
    assert compression["calls"][0]["outcome"] == "failed"


def test_compression_timeout_cancels_the_pending_call_without_retry():
    from backend.tests.versions.v3.test_multiround import policy

    fixture = setup(["x" * 255])
    cancelled = []

    class WaitingModel(ReasonModel):
        async def compress_repair_reasons_structured(self, **kwargs):
            await super().compress_repair_reasons_structured(**kwargs)
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.append(True)

    model = WaitingModel(fixture[-1])
    result = run(model, fixture, policy=policy(reason_compression={"timeout_seconds": 0.01}))
    assert result.reason == "reason_compression_timeout"
    assert model.compressions == len(cancelled) == 1
    assert result.reason_compression["timeout_seconds"] == 0.01
    assert result.reason_compression["usage"]["fixture"]["total_tokens"] == 100


@pytest.mark.parametrize(
    "compression",
    [
        {"max_calls": 2},
        {"input_tokens": 64001},
        {"output_tokens": 16385},
        {"timeout_seconds": 61},
    ],
)
def test_configuration_cannot_expand_the_approved_compression_limits(compression):
    from pydantic import ValidationError

    from backend.tests.versions.v3.test_multiround import policy

    with pytest.raises(ValidationError):
        policy(reason_compression=compression)
