"""Run one authorized Berlin development smoke case in fixed V0–V3 order."""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from backend.app.policies.trip_dates import (  # noqa: E402
    create_trip_date_window,
    validate_requested_trip_dates,
)
from backend.app.runtime.config_loader import load_runtime_config_file  # noqa: E402
from backend.app.runtime.database import DatabaseSettings  # noqa: E402
from backend.app.schemas.request import PlanningRequest  # noqa: E402
from backend.app.versions.v0.config import V0Settings  # noqa: E402
from backend.app.versions.v1.config import V1Settings  # noqa: E402
from tools.validation.landmark_pilot import local_dependencies  # noqa: E402

PACKET = Path(__file__).resolve().parent
OUTPUT = ROOT / "logs/berlin_six_day_20260928"
REQUEST = PACKET / "request.json"
RUNTIME = ROOT / "config" / "runtime.yaml"
COPIED_RUNTIME = OUTPUT / "runtime.yaml"
MANIFEST = OUTPUT / "manifest.json"
CASES = ("v0", "v1", "v2", "v3")
EXPECTED_REQUEST = {
    "input_version": "planning_request_2",
    "destination": "Berlin, Germany",
    "start_date": "2026-10-03",
    "end_date": "2026-10-08",
    "traveler_count": 2,
    "budget": {"amount": "3000", "currency": "EUR"},
    "additional_preferences": "We want to have an enjoyable trip in this city.",
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes():
    files = {Path(__file__), REQUEST, ROOT / "pyproject.toml", ROOT / "uv.lock"}
    for folder in ("backend/app", "scripts", "tools/validation"):
        files.update((ROOT / folder).rglob("*.py"))
    files.update((ROOT / "config").glob("*.yaml"))
    files.update(p for p in (ROOT / ".env",) if p.is_file())
    files.update(
        (ROOT / "data/tripworld") / name
        for name in (
            "reports/phase5_embedding_run.json",
            "artifacts/retrieval_entities.parquet.manifest.json",
        )
    )
    return {p.relative_to(ROOT).as_posix(): sha256(p) for p in sorted(files)}


def environment_hash():
    """Freeze relevant overrides without publishing any configuration values."""
    prefixes = (
        "AZURE_",
        "OPENAI_",
        "GOOGLE_",
        "TRIPWORLD_",
        "DAYLOOM_",
        "APP_",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "NO_PROXY",
    )
    values = {k: v for k, v in os.environ.items() if k.upper().startswith(prefixes)}
    return hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()


def all_secrets():
    values = dict(os.environ)
    for name in (".env",):
        values.update({f"{name}:{k}": v for k, v in dotenv_values(ROOT / name).items()})
    return tuple(
        v
        for k, v in values.items()
        if v
        and len(v) >= 8
        and any(word in k.upper() for word in ("KEY", "TOKEN", "PASSWORD", "SECRET", "CREDENTIAL"))
    )


def inspect_budgets(directories):
    """Check recorded bounds; absent billed usage never means zero usage."""
    if not directories:
        return "missing"
    for directory in directories:
        path = Path(directory) / "budget.json"
        run_path = Path(directory) / "run.json"
        if not path.is_file() or not run_path.is_file():
            return "missing"
        data = json.loads(path.read_text(encoding="utf-8"))
        run = json.loads(run_path.read_text(encoding="utf-8"))
        if data.get("collection_status") != "complete" or not data.get("primary_tools"):
            return "incomplete"
        if run.get("truncated"):
            return "truncated"
        pending = [data]
        while pending:
            value = pending.pop()
            if isinstance(value, dict):
                used, limit = value.get("used"), value.get("limit")
                if isinstance(used, (int, float)) and isinstance(limit, (int, float)):
                    if used > limit:
                        return "exceeded"
                pending.extend(value.values())
            elif isinstance(value, list):
                pending.extend(value)
    return "available_within_recorded_limits"


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def request():
    payload = json.loads(REQUEST.read_text(encoding="utf-8"))
    if payload != EXPECTED_REQUEST:
        raise ValueError("Berlin request differs from the fixed smoke input")
    return PlanningRequest.model_validate(payload)


def current_date_and_validate(trip):
    today = datetime.now(ZoneInfo("Australia/Sydney")).date()
    validate_requested_trip_dates(trip.start_date, trip.end_date, create_trip_date_window(today))
    if today >= trip.start_date:
        raise ValueError("Trip start is no longer in the future")
    return today


def git_head():
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def credentials(version):
    if version == "v0":
        key = V0Settings().azure_openai_api_key.get_secret_value()
        return (key,)
    settings = V1Settings()
    secrets = [
        settings.azure_openai_api_key.get_secret_value(),
        settings.google_maps_api_key.get_secret_value(),
    ]
    if version in {"v2", "v3"}:
        rag_file = ROOT / ".env"
        if not rag_file.is_file():
            raise ValueError("TripWorld environment file unavailable")
        password = DatabaseSettings(_env_file=rag_file).connection_parameters().get("password")
        if not password:
            raise ValueError("TripWorld database credential unavailable")
        secrets.append(password)
    return tuple(secret for secret in secrets if secret)


def prepare():
    if MANIFEST.exists():
        raise FileExistsError("Batch already prepared; never reset an attempt")
    trip = request()
    current_date_and_validate(trip)
    local_dependencies()
    if OUTPUT.exists():
        raise FileExistsError("Evidence directory already exists")
    OUTPUT.mkdir(parents=True)
    raw = yaml.safe_load(RUNTIME.read_text(encoding="utf-8"))
    if raw["trace"]["raw_provider_payloads"]:
        raise ValueError("Raw provider payload capture must remain disabled")
    raw["trace"]["directory"] = str((OUTPUT / "trace").resolve())
    raw["trace"]["payload_level"] = "normalized"
    COPIED_RUNTIME.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    config = load_runtime_config_file(COPIED_RUNTIME)
    if (
        config.development_timeout_seconds != 600
        or config.poi_semantics.max_calls != 6
        or config.v3_repair.max_model_calls != 5
    ):
        raise ValueError("Unexpected runtime request or model budgets")
    write_json(
        MANIFEST,
        {
            "status": "prepared",
            "prepared_at": datetime.now(ZoneInfo("Australia/Sydney")).isoformat(),
            "git_head": git_head(),
            "dirty_files": subprocess.check_output(
                ["git", "status", "--short"], cwd=ROOT, text=True
            ).splitlines(),
            "request_sha256": sha256(REQUEST),
            "source_runtime_sha256": sha256(RUNTIME),
            "runtime_sha256": sha256(COPIED_RUNTIME),
            "launcher_sha256": sha256(Path(__file__)),
            "source_hashes": source_hashes(),
            "environment_sha256": environment_hash(),
            "authorized_order": list(CASES),
            "attempts_per_case": 1,
            "outer_seconds_per_case": 660,
            "cases": [],
        },
    )
    print("Prepared four-case Berlin smoke batch without external requests.")


def command_for(version, date, case_output):
    if version in {"v1", "v3"}:
        command = [
            sys.executable,
            "-m",
            "tools.validation.poi_semantics_acceptance",
            "--input-json",
            str(REQUEST),
            "--output",
            str(case_output),
            "--version",
            version,
            "--reference-date",
            date,
            "--runtime-config",
            str(COPIED_RUNTIME),
            "--capture-requirements",
            "--capture-semantics",
            "--execute",
        ]
        if version == "v3":
            command += ["--rag-env-file", str(ROOT / ".env"), "--capture-repair"]
        return command
    command = [
        sys.executable,
        str(ROOT / "scripts" / f"run_{version}.py"),
        "--input-json",
        str(REQUEST),
        "--reference-date",
        date,
    ]
    if version == "v2":
        command += [
            "--runtime-config",
            str(COPIED_RUNTIME),
            "--development-timeout-seconds",
            "600",
            "--rag-env-file",
            str(ROOT / ".env"),
        ]
    return command


def run(version):
    local_dependencies()
    batch = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if batch["status"] not in {"prepared", "running"}:
        raise ValueError("Batch is stopped")
    if len(batch["cases"]) >= len(CASES) or CASES[len(batch["cases"])] != version:
        raise ValueError("Case order or one-attempt rule violated")
    if any(item["status"] == "running" for item in batch["cases"]):
        raise ValueError("Previous case is still running")
    trip = request()
    if (
        sha256(REQUEST) != batch["request_sha256"]
        or sha256(RUNTIME) != batch["source_runtime_sha256"]
        or sha256(COPIED_RUNTIME) != batch["runtime_sha256"]
        or sha256(Path(__file__)) != batch["launcher_sha256"]
        or git_head() != batch["git_head"]
        or source_hashes() != batch["source_hashes"]
        or environment_hash() != batch["environment_sha256"]
    ):
        raise ValueError("Input, runtime policy, or code revision changed")
    today = current_date_and_validate(trip)
    secrets = credentials(version) + all_secrets()
    case_output = OUTPUT / version
    if case_output.exists():
        raise FileExistsError("Case output already exists; no rerun allowed")
    with (OUTPUT / f"{version}.attempt.lock").open("x", encoding="utf-8") as lock:
        lock.write("One authorized attempt consumed. Do not delete or retry.\n")
    if version in {"v0", "v2"}:
        case_output.mkdir()
    trace_root = OUTPUT / "trace"
    before = set(trace_root.iterdir()) if trace_root.exists() else set()
    entry = {
        "version": version,
        "reference_date": today.isoformat(),
        "started_at": datetime.now(ZoneInfo("Australia/Sydney")).isoformat(),
        "status": "running",
        "attempts": 1,
    }
    batch["cases"].append(entry)
    batch["status"] = "running"
    write_json(MANIFEST, batch)
    try:
        process = subprocess.run(
            command_for(version, today.isoformat(), case_output),
            cwd=ROOT,
            capture_output=True,
            timeout=660,
            check=False,
        )
        stdout, stderr = process.stdout, process.stderr
        entry["process_exit_code"] = process.returncode
        entry["outer_timeout"] = False
    except subprocess.TimeoutExpired as exc:
        stdout, stderr = exc.stdout or b"", exc.stderr or b""
        entry["process_exit_code"] = None
        entry["outer_timeout"] = True
    (OUTPUT / f"{version}.launcher.stdout.log").write_bytes(stdout)
    (OUTPUT / f"{version}.launcher.stderr.log").write_bytes(stderr)
    if version in {"v0", "v2"}:
        (case_output / "result.json").write_bytes(stdout)
        (case_output / "stderr.log").write_bytes(stderr)
        new_traces = sorted(set(trace_root.iterdir()) - before) if trace_root.exists() else []
        write_json(
            case_output / "execution.json",
            {
                "version": version,
                "application_exit_code": entry["process_exit_code"],
                "trace_directories": [str(path) for path in new_traces],
                "trace_status": "not_applicable"
                if version == "v0"
                else ("available" if len(new_traces) == 1 else "unavailable"),
            },
        )
    entry["finished_at"] = datetime.now(ZoneInfo("Australia/Sydney")).isoformat()
    entry["status"] = "completed" if entry["process_exit_code"] == 0 else "failed"
    execution_path = case_output / "execution.json"
    if not execution_path.exists():
        batch["status"] = "stopped_execution_evidence_missing"
    else:
        summary = json.loads(execution_path.read_text(encoding="utf-8"))
        entry["application_exit_code"] = summary["application_exit_code"]
        entry["trace_status"] = summary["trace_status"]
        if version in {"v1", "v3"}:
            entry["requirement_capture_status"] = summary["capture_status"]
            entry["semantic_capture_status"] = summary["semantic_capture_status"]
            entry["repair_capture_errors"] = summary["repair_capture_errors"]
            if (
                summary["capture_status"] != "complete"
                or summary["semantic_capture_status"] != "complete"
                or version == "v3"
                and any(
                    error != "repair_snapshot_not_reached"
                    for error in summary["repair_capture_errors"]
                )
            ):
                batch["status"] = "stopped_capture_incomplete"
        if version != "v0" and summary["trace_status"] != "available":
            batch["status"] = "stopped_capture_incomplete"
    if entry["outer_timeout"]:
        batch["status"] = "stopped_timeout"
    result_path = case_output / "result.json"
    if entry["process_exit_code"] == 0:
        try:
            result = json.loads(result_path.read_text(encoding="utf-8"))
            actual_dates = [day["date"] for day in result["itinerary"]["days"]]
            expected_dates = [
                (trip.start_date + timedelta(days=index)).isoformat() for index in range(6)
            ]
            entry["itinerary_complete"] = (
                result["system_version"] == version
                and result["itinerary"]["start_date"] == trip.start_date.isoformat()
                and result["itinerary"]["end_date"] == trip.end_date.isoformat()
                and actual_dates == expected_dates
                and all(day.get("activities") for day in result["itinerary"]["days"])
                and entry.get("application_exit_code") == 0
            )
        except (OSError, ValueError, KeyError, TypeError):
            entry["itinerary_complete"] = False
        if not entry["itinerary_complete"]:
            entry["result_contract_error"] = "missing_or_incomplete_itinerary"
    if version != "v0" and execution_path.exists():
        entry["budget_evidence"] = inspect_budgets(summary.get("trace_directories", []))
        if entry["budget_evidence"] != "available_within_recorded_limits":
            batch["status"] = "stopped_budget_evidence"
    evidence_paths = [path for path in case_output.rglob("*") if path.is_file()] + [
        OUTPUT / f"{version}.launcher.stdout.log",
        OUTPUT / f"{version}.launcher.stderr.log",
    ]
    if version == "v2" and execution_path.exists():
        for directory in summary["trace_directories"]:
            evidence_paths.extend(path for path in Path(directory).rglob("*") if path.is_file())
    leaked = [
        str(path)
        for path in evidence_paths
        if any(secret.encode() in path.read_bytes() for secret in secrets)
    ]
    if leaked:
        entry["secret_exposure_files"] = leaked
        batch["status"] = "stopped_secret_exposure"
    if batch["status"] == "running" and len(batch["cases"]) == len(CASES):
        batch["status"] = "finished"
    entry["itinerary_complete"] = entry.get("itinerary_complete", False)
    batch["blind_review_eligible"] = (
        batch["status"] == "finished"
        and len(batch["cases"]) == 4
        and all(item.get("itinerary_complete") for item in batch["cases"])
    )
    write_json(MANIFEST, batch)
    print(
        json.dumps(
            {
                "version": version,
                "case_status": entry["status"],
                "batch_status": batch["status"],
                "application_exit_code": entry.get("application_exit_code"),
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", *CASES))
    action = parser.parse_args().action
    prepare() if action == "prepare" else run(action)
