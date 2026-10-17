"""Small numeric budget metadata, independent of large trace payloads."""

import math
import re

from backend.app.runtime.budget_limits import ToolBudgetKey


def number(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def select(value, keys):
    if not isinstance(value, dict):
        return {}
    return {k: value[k] for k in keys if number(value.get(k))}


USAGE_KEYS = ("input_tokens", "output_tokens", "total_tokens")
LIMITS = {
    "landmark_nomination": (
        "landmark_nomination",
        "max_calls max_names input_tokens output_tokens "
        "call_timeout_seconds supplementary_searches",
    ),
    "primary_generation": ("main_generation", "input_tokens output_tokens framing_tokens"),
    "semantics": (
        "poi_semantics",
        "max_calls batch_size input_tokens output_tokens call_timeout_seconds total_seconds",
    ),
    "rag": (
        "tripworld_discovery",
        "max_queries max_positions total_query_tokens details_calls fallback_calls "
        "resolution_entities deadline_seconds",
    ),
    "nearby": ("reference_discovery", "max_requests deadline_seconds request_timeout_seconds"),
}
RAG_KEYS = (
    "embedding_sends retrieval_queries returned_positions unique_entities details_sends "
    "fallback_sends cache_hits elapsed_seconds resolution_attempts"
)
REPAIR_KEYS = (
    "google fallback embedding retrieval canonical details routes elements preparation_routes "
    "model cache_hits qualified_reuse duplicate_hits"
)


def reported_usage(value):
    """Sum models within one invocation, never cumulative stage snapshots."""
    if not isinstance(value, dict) or not value:
        return {}, "missing"
    models = list(value.values())
    totals = {
        key: sum(row[key] for row in models)
        for key in USAGE_KEYS
        if all(isinstance(row, dict) and number(row.get(key)) for row in models)
    }
    return totals, "reported" if len(totals) == len(
        USAGE_KEYS
    ) else "partial" if totals else "missing"


class BudgetSummary:
    def __init__(self, context):
        self.context = context
        config = context.runtime_config or {}
        self.stages = {
            name: {
                "limits": {},
                "observed": {},
                "observed_status": "missing",
                "usage_status": "missing",
                "calls": {},
            }
            for name in (
                "requirements",
                "primary_generation",
                "semantics",
                "landmark_nomination",
                "rag",
                "repair",
                "nearby",
            )
        }
        self.incomplete = False
        for name, (section, keys) in LIMITS.items():
            self.stages[name]["limits"] = select(config.get(section), keys.split())
        repair = config.get("v3_repair") or {}
        self.stages["repair"]["limits"] = {
            **select(repair, ("max_rounds", "max_model_calls")),
            **select(
                repair.get("acquisition"), REPAIR_KEYS.split() + ["post_proposal_route_reserve"]
            ),
            **select(repair.get("timing"), ("stage_seconds", "round_seconds", "model_seconds")),
            **select(repair.get("input"), ("input_tokens", "output_tokens")),
        }

    def observe(self, event, payload):
        if not isinstance(payload, dict):
            return
        if event in {"landmark_nomination", "landmark_discovery"}:
            name = "landmark_nomination"
            if event == name and payload.get("calls"):
                self.call(name, payload.get("call_id"), payload)
            self.stages[name]["observed"].update(
                select(
                    payload,
                    (
                        "calls",
                        "elapsed_seconds",
                        "engineering_tokens",
                        "nominated",
                        "resolved",
                        "unresolved",
                        "reused",
                        "supplementary_sends",
                        "candidate_search_sends",
                        "qualified",
                        "selected",
                    ),
                )
            )
            self.stages[name]["observed_status"] = "recorded"
            for key in ("status", "nomination_status", "general_status", "supplementary_stop"):
                if payload.get(key) in {
                    "not_started",
                    "completed",
                    "empty",
                    "input_limit",
                    "deadline",
                    "unavailable",
                    "cancelled",
                    "timeout",
                    "failed",
                    "started",
                    "interrupted",
                    "degraded",
                    "not_attempted",
                    "provider_success",
                    "provider_failed",
                    "budget_not_attempted",
                    "supplementary_limit",
                    "shared_search_limit",
                }:
                    self.stages[name][key] = payload[key]
        elif event == "poi_semantic_assessment":
            self.call("semantics", payload.get("call_id"), payload)
        elif event == "v3_repair_round":
            index = payload.get("round_index")
            if type(index) is int and index > 0:
                self.call("repair", str(index), payload)
            self.snapshot("repair", payload.get("cumulative_counters"), REPAIR_KEYS.split())
        elif event in ("rag_discovery_completed", "rag_final_fate", "rag_cancelled"):
            self.snapshot("rag", payload, RAG_KEYS.split())
            usage = select(payload.get("embedding_usage"), ("prompt_tokens", "total_tokens"))
            if usage:
                self.stages["rag"]["embedding_usage"] = usage
                self.stages["rag"]["usage_status"] = (
                    "reported" if "total_tokens" in usage else "partial"
                )
        elif event == "reference_discovery_completed":
            self.snapshot("nearby", payload, ("requests_sent", "cache_hits", "elapsed_seconds"))
        elif event == "primary_generation_resources":
            self.snapshot(
                "primary_generation",
                payload,
                (
                    "total_tokens",
                    "user_tokens",
                    "schema_tokens",
                    "system_tokens",
                    "framing_tokens",
                    "ceiling",
                ),
            )

    def snapshot(self, name, value, keys):
        observed = select(value, keys)
        if observed:
            self.stages[name]["observed"] = observed
            self.stages[name]["observed_status"] = "recorded"

    def call(self, name, identity, value):
        if not isinstance(identity, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", identity):
            self.incomplete = True
            return
        stage = self.stages[name]
        if identity not in stage["calls"] and len(stage["calls"]) >= 32:
            self.incomplete = True
            return
        usage, status = reported_usage(value.get("usage"))
        stage["calls"][identity] = {
            "id": identity,
            "usage": usage,
            "usage_status": status,
            **select(value, ("elapsed_seconds", "engineering_tokens", "round_index")),
        }
        if name == "semantics":
            call = stage["calls"][identity]
            call.update(select(value, ("timeout_seconds",)))
            deadline_keys = ("call", "total", "caller", "request")
            if value.get("limiting_deadline") in deadline_keys:
                call["limiting_deadline"] = value["limiting_deadline"]
            remaining = select(value.get("remaining_seconds"), deadline_keys)
            if remaining:
                call["remaining_seconds"] = remaining
            if value.get("error_type") == "TimeoutError":
                call["error_type"] = "TimeoutError"
        statuses = {r["usage_status"] for r in stage["calls"].values()}
        stage["usage_status"] = (
            "reported"
            if statuses == {"reported"}
            else "missing"
            if statuses == {"missing"}
            else "partial"
        )
        stage["observed_status"] = "recorded"

    def finish(self, status, tool_usage):
        return {
            "schema_version": 1,
            "run_id": str(self.context.run_id),
            "status": status if status in ("completed", "failed", "cancelled") else "unknown",
            "runtime_config_sha256": self.context.runtime_config_sha256
            if isinstance(self.context.runtime_config_sha256, str)
            and re.fullmatch(r"[a-f0-9]{64}", self.context.runtime_config_sha256)
            else None,
            "collection_status": "incomplete" if self.incomplete else "complete",
            "scope": "Application counters only; missing usage is not zero or a provider invoice.",
            "primary_tools": {
                key.value: {k: row[k] for k in ("used", "limit")}
                for key in ToolBudgetKey
                if isinstance(row := tool_usage.get(key.value), dict)
                and all(number(row.get(k)) for k in ("used", "limit"))
            },
            "stages": {
                name: {**stage, "calls": list(stage["calls"].values())}
                for name, stage in self.stages.items()
            },
        }
