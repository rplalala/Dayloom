"""One-shot interpreter smoke. CLI execution requires separate live authorization."""

import argparse
import asyncio
import copy
import hashlib
import json
import re
import time
from datetime import date
from pathlib import Path
from uuid import uuid4

from langchain_core.callbacks import BaseCallbackHandler, get_usage_metadata_callback

from backend.app.llm.azure_foundry.dto import FoundryInterpretationDTO
from backend.app.policies.preference_input import PreferenceInputBlocked
from backend.app.policies.trip_dates import SystemDateProvider
from backend.app.schemas.interpreted_requirements import InterpretationDraft
from backend.app.schemas.requirement_boundary import RequirementBoundaryError
from backend.app.services import preference_interpretation as shared
from backend.app.versions.v0.config import V0Settings
from backend.app.versions.v0.runner import create_foundry_client


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_once(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=True, indent=2, default=str)


def sanitize(value, secrets):
    """Follow development capture's exact-secret redaction, without storing credentials."""
    if isinstance(value, str):
        for secret in secrets:
            if secret:
                for representation in (secret, json.dumps(secret)[1:-1]):
                    value = value.replace(representation, "[REDACTED]")
        return value
    if isinstance(value, dict):
        return {k: sanitize(v, secrets) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitize(v, secrets) for v in value]
    return value


def preflight(manifest, output, deployment, reference):
    """Read-only checks before directory creation or client construction."""
    if output.exists():
        raise ValueError("Output directory already exists")
    if deployment != manifest["deployment"]:
        raise ValueError("Deployment changed")
    cases = manifest["cases"]
    if not 1 <= len(cases) <= 10:
        raise ValueError("Expected one to ten frozen cases")
    ids = [c["case_id"] for c in cases]
    if len(set(ids)) != len(ids) or any(not re.fullmatch(r"[\w-]+", c) for c in ids):
        raise ValueError("Invalid or duplicate case IDs")
    for group in ("source_hashes", "historical_hashes"):
        if not manifest.get(group):
            raise ValueError("Missing frozen hashes: " + group)
        for path, expected in manifest[group].items():
            if digest(path) != expected:
                raise ValueError("Frozen hash mismatch: " + path)
    for case in cases:
        if case.get("allowed_alternatives"):
            raise ValueError("This harness requires a single frozen outcome per case")
        for key in (
            "expected_input",
            "expected_safety",
            "expected_issue_types",
            "expected_source_quotes",
        ):
            if key not in case:
                raise ValueError("Missing frozen expectation: " + key)
        request = shared.validate_planning_request(case["request"], reference)
        if request.start_date <= reference or not request.additional_preferences:
            raise ValueError("Smoke requires future dates and nonempty preferences")


class Observation(BaseCallbackHandler):
    """Per-case text and usage capture; never retains internal reasoning blocks."""

    raise_error = True

    def __init__(self):
        self.current = None

    def on_llm_end(self, response, **kwargs):
        if self.current is None:
            raise RuntimeError("Response outside an active case")
        for batch in response.generations:
            for generation in batch:
                msg = getattr(generation, "message", None)
                if msg is None:
                    continue
                content = msg.content
                if isinstance(content, list):
                    content = "".join(
                        b.get("text", "")
                        for b in content
                        if isinstance(b, dict) and b.get("type") == "text"
                    )
                self.current["raw_model_response"].append(
                    {
                        "text": content,
                        "usage": getattr(msg, "usage_metadata", None),
                        "response_id": getattr(msg, "id", None),
                    }
                )

    async def on_request(self, request):
        if self.current is None or self.current["http_sends"]:
            raise RuntimeError("Additional HTTP send prohibited")
        self.current["http_sends"] += 1

    async def on_response(self, response):
        if self.current is None:
            raise RuntimeError("HTTP response outside an active case")
        self.current["http_responses"].append({"status_code": response.status_code})


def attach_observer(client, observer):
    """Attach only to the owned existing adapter; do not alter model defaults."""
    model = client._chat_model
    sdk = model.root_async_client
    if sdk.max_retries != 0:
        raise ValueError("SDK retries must remain zero")
    model.callbacks = [*(model.callbacks or []), observer]
    sdk._client.event_hooks["request"].append(observer.on_request)
    sdk._client.event_hooks["response"].append(observer.on_response)


class RecordingModel:
    def __init__(self, client, row):
        self.client, self.row = client, row

    async def generate_structured(self, **kwargs):
        if self.row["model_calls"] or kwargs["response_schema"] is not InterpretationDraft:
            raise RuntimeError("Only one preference interpretation is permitted")
        self.row["model_calls"] += 1
        draft = await self.client.generate_structured(**kwargs)
        self.row["domain_parsed_dto"] = draft.model_dump(mode="json")
        return draft

    def capture_requirement_outcome(self, draft, error=None):
        capture = getattr(self.client, "capture_requirement_outcome", None)
        if capture:
            capture(draft, error)


def capture_wire(row):
    """Audit the wire only; never replace the actual domain/application outcome."""
    messages = row["raw_model_response"]
    if len(messages) != 1:
        raise ValueError("Expected exactly one captured structured response")
    payload = json.loads(messages[0]["text"])
    version = row.get("model_metadata", {}).get("schema_version")
    if version in {"preference_draft_13", "preference_draft_14", "preference_draft_15"}:
        from backend.app.llm.azure_foundry.dto import (
            FoundryCurrentInterpretationDTO,
            FoundryDatedInterpretationDTO,
        )
        from backend.app.llm.azure_foundry.requirement_wire import (
            IndexedSourceSpans,
            SourceSpans,
            restore_current,
        )
        from backend.app.schemas.request import PlanningRequest

        original = PlanningRequest.model_validate(row["input"])
        prompt = shared.preference_prompt(original, date.fromisoformat(row["reference_date"]))
        indexed = version in {"preference_draft_14", "preference_draft_15"}
        spans = (IndexedSourceSpans if indexed else SourceSpans)(
            prompt, original.additional_preferences
        )
        binding = row["model_metadata"].get("source_request_sha256") if indexed else None
        dto = (
            FoundryDatedInterpretationDTO
            if version == "preference_draft_15"
            else FoundryCurrentInterpretationDTO
        ).model_validate(restore_current(payload, spans, request_sha256=binding))
    else:
        dto = FoundryInterpretationDTO.model_validate(payload)
    row["strict_parsed_dto"] = dto.model_dump(mode="json")
    row["parse_capture_status"] = "wire_parsed"


def matches(case, row):
    draft = row.get("domain_parsed_dto") or {}
    assessment = draft.get("preference_input_assessment")
    if assessment is None:
        return False
    issues = assessment["issues"]
    refs = [r for issue in issues for r in issue["source_refs"]]
    return (
        assessment["input_disposition"] == case["expected_input"]
        and assessment["safety_disposition"] == case["expected_safety"]
        and sorted(i["issue_type"] for i in issues) == sorted(case["expected_issue_types"])
        and sorted(r["quote"] for r in refs) == sorted(case["expected_source_quotes"])
        and all(r["occurrence"] == 0 for r in refs)
        and all(
            i["operational_conflict_index"] is None
            for i in issues
            if i["issue_type"] != "structured_request_conflict"
        )
        and all(
            i["related_field"] == "destination"
            for i in issues
            if i["issue_type"] == "destination_scope_conflict"
        )
        and (
            "expected_related_field" not in case
            or all(i["related_field"] == case["expected_related_field"] for i in issues)
        )
        and (
            "expected_operational_conflict_index" not in case
            or all(
                i["operational_conflict_index"] == case["expected_operational_conflict_index"]
                for i in issues
            )
        )
        and row["state"] == ("input_blocked" if issues else "completed")
    )


async def run_smoke(
    manifest,
    output,
    *,
    deployment,
    reference,
    client_factory,
    attach=attach_observer,
    capture=capture_wire,
    writer=write_once,
):
    """Own one client; call only the real shared interpreter, never a travel runner."""
    preflight(manifest, output, deployment, reference)
    output.mkdir(parents=True, exist_ok=False)
    summary = {
        "run_id": str(uuid4()),
        "cases": [],
        "stop_reason": None,
        "secondary_errors": [],
        "callback_total": {},
        "resources": {},
        "downstream": {
            "travel": 0,
            "primary": 0,
            "repair": 0,
            "basis": "interpreter-only entry point",
        },
    }
    client = None
    cancelled = None
    started = time.monotonic()
    observer = Observation()
    secrets = ()

    def stop(reason):
        if summary["stop_reason"] is None:
            summary["stop_reason"] = reason
        elif summary["stop_reason"] != reason:
            summary["secondary_errors"].append(reason)

    def save(name, value):
        try:
            writer(output / name, sanitize(value, secrets))
            return True
        except Exception as exc:
            stop("capture_failure:" + type(exc).__name__)
            return False

    try:
        if not save("manifest.json", manifest) or not save(
            "execution-started.json",
            {
                "run_id": summary["run_id"],
                "harness_sha256": digest(__file__),
                "deployment": deployment,
                "reference_date": str(reference),
            },
        ):
            return summary
        client = client_factory()
        secrets = getattr(client, "_capture_secrets", ())
        attach(client, observer)
        with get_usage_metadata_callback() as callback:
            try:
                for case in manifest["cases"]:
                    if summary["stop_reason"]:
                        break
                    row = {
                        "case_id": case["case_id"],
                        "reference_date": reference.isoformat(),
                        "input": case["request"],
                        "frozen_expected": {
                            k: v for k, v in case.items() if k.startswith("expected_")
                        },
                        "state": "started",
                        "model_calls": 0,
                        "http_sends": 0,
                        "http_responses": [],
                        "raw_model_response": [],
                        "strict_parsed_dto": None,
                        "domain_parsed_dto": None,
                        "parse_capture_status": "not_executed",
                    }
                    # Register before any fallible capture/call: never mislabel attempted work.
                    summary["cases"].append(row)
                    observer.current = row
                    tick = time.monotonic()
                    try:
                        result = await shared.interpret_preferences(
                            shared.validate_planning_request(case["request"], reference),
                            reference,
                            RecordingModel(client, row),
                        )
                        row.update(
                            state="completed", application_outcome=result.model_dump(mode="json")
                        )
                    except PreferenceInputBlocked as exc:
                        row.update(state="input_blocked", application_outcome=exc.as_dict())
                    except RequirementBoundaryError as exc:
                        kind = (
                            "contract_failure"
                            if exc.category == "invalid_model_contract"
                            else "provider_failure"
                        )
                        row.update(state=kind, application_outcome=exc.as_dict())
                        stop(kind + ":" + case["case_id"])
                    except asyncio.CancelledError as exc:
                        cancelled = exc
                        row["state"] = "cancelled"
                        stop("cancelled:" + case["case_id"])
                    except Exception as exc:
                        row.update(state="system_failure", error_type=type(exc).__name__)
                        stop("system_failure:" + case["case_id"])
                    finally:
                        row["elapsed_seconds"] = time.monotonic() - tick
                        row["callback_cumulative"] = copy.deepcopy(callback.usage_metadata)
                        row["model_metadata"] = copy.deepcopy(
                            getattr(client, "last_call_metadata", {})
                        )
                        row["provider_diagnostics"] = copy.deepcopy(
                            row["model_metadata"].get("provider_diagnostics", {})
                        )
                        row["secondary_errors"] = list(
                            row["model_metadata"].get("secondary_errors", [])
                        )
                        for diagnostic_error in row["secondary_errors"]:
                            stop(diagnostic_error + ":" + case["case_id"])
                        row["first_stop_reason"] = summary["stop_reason"]
                        observer.current = None
                    try:
                        capture(row)
                    except Exception as exc:
                        row["parse_capture_status"] = "unavailable_or_rejected"
                        row["capture_error_type"] = type(exc).__name__
                        # No-response provider failures keep their actual primary attribution.
                        if row["raw_model_response"] or not summary["stop_reason"]:
                            stop("capture_failure:" + case["case_id"])
                    row["frozen_expectation_match"] = matches(case, row)
                    row["quote_grounding_result"] = (
                        "application_validated"
                        if row["state"] in ("completed", "input_blocked")
                        else "failed_or_incomplete"
                    )
                    row["grounded_issue_provenance"] = row.get("application_outcome", {}).get(
                        "issues", []
                    )
                    if not row["frozen_expectation_match"] and not summary["stop_reason"]:
                        stop("expectation_mismatch:" + case["case_id"])
                    row["stop_after_case"] = summary["stop_reason"]
                    row["record_complete"] = True
                    if not save(case["case_id"] + ".json", row):
                        row["record_complete"] = False
            finally:
                summary["callback_total"] = copy.deepcopy(callback.usage_metadata)
    except asyncio.CancelledError as exc:
        cancelled = exc
        stop("cancelled")
    except Exception as exc:
        stop("harness_failure:" + type(exc).__name__)
    finally:
        if client is not None:
            try:
                await client.aclose()
                summary["resources"]["adapter_aclose_returned"] = True
            except asyncio.CancelledError as exc:
                cancelled = exc
                stop("cleanup_cancelled")
            except Exception as exc:
                summary["resources"]["close_error_type"] = type(exc).__name__
                stop("cleanup_failure:" + type(exc).__name__)
        ids = {row["case_id"] for row in summary["cases"]}
        for case in manifest["cases"]:
            if case["case_id"] not in ids:
                row = {
                    "case_id": case["case_id"],
                    "state": "NOT_ATTEMPTED",
                    "reason": summary["stop_reason"],
                    "model_calls": 0,
                    "http_sends": 0,
                    "input": case["request"],
                    "frozen_expected": {k: v for k, v in case.items() if k.startswith("expected_")},
                }
                summary["cases"].append(row)
                save(case["case_id"] + ".json", row)
        summary["model_calls"] = sum(r["model_calls"] for r in summary["cases"])
        summary["http_sends"] = sum(r["http_sends"] for r in summary["cases"])
        summary["elapsed_seconds"] = time.monotonic() - started
        for group in ("source_hashes", "historical_hashes"):
            summary[group + "_unchanged"] = {
                p: Path(p).is_file() and digest(p) == h for p, h in manifest[group].items()
            }
            if not all(summary[group + "_unchanged"].values()):
                stop("integrity_failure:" + group)
        summary["exit_code"] = 1 if summary["stop_reason"] else 0
        save("summary.json", summary)
        summary["exit_code"] = 1 if summary["stop_reason"] else 0
    if cancelled is not None:
        raise cancelled
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--execute-live", action="store_true")
    args = parser.parse_args()
    if not args.execute_live:
        parser.error("Explicit --execute-live and separate user authorization are required")
    if digest(args.manifest) != args.manifest_sha256:
        parser.error("Manifest hash mismatch")
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    settings = V0Settings()
    result = asyncio.run(
        run_smoke(
            manifest,
            args.output,
            deployment=settings.azure_openai_deployment,
            reference=SystemDateProvider(settings.app_time_zone).today(),
            client_factory=lambda: create_foundry_client(settings),
        )
    )
    return result["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
