"""Local evidence inventory; availability is separate from batch qualification."""

import hashlib
import json

import numpy as np

from backend.app.tripworld.database.vectors import SPACE, SPACE_ID
from backend.app.tripworld.retrieval.embedding import validate_vectors


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json(path, diagnostics):
    try:
        return json.loads(path.read_bytes()), True
    except (OSError, ValueError) as exc:
        diagnostics.append(
            {
                "reason": "evidence_json_unavailable",
                "file": path.name,
                "error_type": type(exc).__name__,
            }
        )
        return None, False


def _valid_vectors(path, diagnostics):
    try:
        with np.load(path, allow_pickle=False) as bundle:
            metadata = json.loads(str(bundle["metadata"]))
            vectors = bundle["vectors"]
            texts = metadata["text_sha256"]
            validate_vectors(vectors, len(texts), 1536)
            if (
                metadata["version"] != "runtime_query_capture_1"
                or metadata["space"] != SPACE
                or metadata["space_id"] != SPACE_ID
                or metadata["shape"] != list(vectors.shape)
                or metadata["dtype"] != str(vectors.dtype)
                or metadata["vectors_sha256"] != hashlib.sha256(vectors.tobytes()).hexdigest()
                or not isinstance(texts, list)
                or not texts
                or any(
                    not isinstance(t, str)
                    or len(t) != 64
                    or any(c not in "0123456789abcdef" for c in t)
                    for t in texts
                )
            ):
                raise ValueError("Invalid captured query-vector metadata")
        return True
    except Exception as exc:
        diagnostics.append(
            {
                "reason": "query_vectors_unavailable",
                "file": path.name,
                "error_type": type(exc).__name__,
            }
        )
        return False


def build_evidence_index(output, manifest, raw, usage, *, adapter_coverage):
    missing = []
    if (
        not (output / "usage.json").is_file()
        or manifest.get("status") == "capture_failed"
        or manifest.get("capture_status") == "capture_failed"
    ):
        missing.append("usage")
    diagnostics = list(raw.diagnostics) if raw else [{"reason": "raw_capture_not_started"}]
    events = raw.events if raw else []
    mechanism_path = output / "mechanism.json"
    if mechanism_path.is_file():
        mechanism, available = _read_json(mechanism_path, diagnostics)
        if (
            available
            and isinstance(mechanism, dict)
            and mechanism.get("schema_version") == "rtpeval_mechanism_capture_1"
            and isinstance(mechanism.get("missing_fields"), list)
            and isinstance(mechanism.get("diagnostics"), list)
        ):
            missing.extend(f"mechanism.{name}" for name in mechanism["missing_fields"])
            diagnostics.extend(mechanism["diagnostics"])
        else:
            missing.append("mechanism")
    else:
        missing.append("mechanism")
    if adapter_coverage != "default_adapters":
        missing.append("verified_adapter_coverage")
    observed_ids = {row["event_id"] for row in events}
    for event in usage.get("provider_events", []):
        if event.get("source") == "http_request_hook" and event["event_id"] not in observed_ids:
            missing.append(f"http.{event['event_id']}")
    for row in events:
        for kind in ("request", "response"):
            if row.get(f"{kind}_body_status") != "complete":
                missing.append(f"http.{row['event_id']}.{kind}_body")
    artifacts = []
    trace_found = False
    vectors = 0
    for path in sorted(output.rglob("*")):
        if not path.is_file() or path.name in (
            "manifest.json",
            "provenance.json",
            "evidence-index.json",
        ):
            continue
        name = path.relative_to(output).as_posix()
        try:
            artifacts.append({"path": name, "sha256": sha(path)})
        except OSError as exc:
            artifacts.append({"path": name, "sha256": None, "availability": "unavailable"})
            missing.append(f"artifact.{name}")
            diagnostics.append(
                {
                    "reason": "evidence_file_unavailable",
                    "file": name,
                    "error_type": type(exc).__name__,
                }
            )
            continue
        if name.startswith("evidence/vectors/") and path.suffix == ".npz":
            if _valid_vectors(path, diagnostics):
                vectors += 1
            else:
                missing.append(f"vectors.{name}")
        if name.startswith("evidence/trace/") and path.suffix == ".json":
            value, available = _read_json(path, diagnostics)
            if not available:
                missing.append(f"trace.{name}")
                continue
            if path.name == "run.json":
                trace_found = (
                    isinstance(value, dict)
                    and bool(value.get("status"))
                    and value["status"] != "running"
                    and not value.get("truncated")
                )
            if isinstance(value, dict) and value.get("truncated"):
                missing.append(f"trace.{name}")
    if not trace_found:
        missing.append("finished_trace")
    embeddings = sum(
        row["operation"] == "embedding" and row["outcome"] == "completed"
        for row in usage.get("model_calls", [])
    )
    if vectors < embeddings:
        missing.append("query_vectors")
    result = output / "result.json"
    if not result.is_file():
        missing.append("result_sha256")
    return {
        "schema_version": "rtpeval_generation_evidence_1",
        "group_id": manifest["group_id"],
        "run_id": manifest["run_id"],
        "version": manifest["version"],
        "input_sha256": manifest["input_sha256"],
        "result_sha256": sha(result) if result.is_file() else None,
        "source_revision": manifest["source_revision"],
        "outcome": usage["outcome"],
        "runtime_policy_sha256": manifest["runtime_policy_sha256"],
        "adapter_coverage": adapter_coverage,
        "qualified_four_version_batch": False,
        "collection_status": "partial" if missing or diagnostics else "available",
        "missing_fields": missing,
        "diagnostics": diagnostics,
        "http_events": events,
        "artifacts": artifacts,
        "scope": "Credential-filtered local observations; no proof of external receipt or billing.",
    }


def finish_trace_if_running(tracer, usage):
    """Retain runner-owned finalization; optional trace IO cannot fail planning."""
    try:
        path = tracer.run_directory / "run.json"
        if path.is_file() and json.loads(path.read_bytes()).get("status") == "running":
            outcome = usage["outcome"] if usage else "incomplete"
            tracer.finish(status=outcome, requirements=None, tool_usage={}, outcome=None)
    except Exception:
        # The inventory reports a missing/unfinished trace instead of adopting false evidence.
        pass
