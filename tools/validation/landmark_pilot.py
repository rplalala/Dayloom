"""Authorized three-case V3 pilot; preparation is offline, execution is one-shot."""

import argparse
import contextlib
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

import yaml

from backend.app.policies.trip_dates import create_trip_date_window, validate_requested_trip_dates
from backend.app.schemas.request import PlanningRequest
from tools.validation.requirement_capture import DevelopmentRequirementCapture

ROOT = Path(__file__).resolve().parents[2]
INPUTS = ROOT / "tools/validation/packets/preference-landmark-balance/pilot"
OUTPUT = ROOT / "logs/preference_landmark_pilot_20260928"
CASES = ("ordinary_sydney_v3", "focus_melbourne_v3", "short_brisbane_v3")
CHILD_MODULE = "tools.validation.landmark_pilot"


def write(path, data):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, ensure_ascii=True)


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def source_hashes():
    files = set()
    for folder in ("backend/app", "scripts", "tools/validation"):
        files.update((ROOT / folder).rglob("*.py"))
    files.update((ROOT / "config").glob("*.yaml"))
    files.update(ROOT / name for name in ("pyproject.toml", "uv.lock"))
    files.update(p for p in (ROOT / ".env",) if p.is_file())
    files.update(INPUTS / f"{case}.json" for case in CASES)
    return {
        p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(files)
    }


def today_and_validate():
    today = datetime.now(ZoneInfo("Australia/Sydney")).date()
    for case in CASES:
        request = PlanningRequest.model_validate(read(INPUTS / f"{case}.json"))
        validate_requested_trip_dates(
            request.start_date, request.end_date, create_trip_date_window(today)
        )
        if request.start_date <= today:
            raise ValueError("Pilot requires future dates")
    return today.isoformat()


def local_dependencies():
    """Validate local configuration/artifacts only; never open a database or HTTP client."""
    from dotenv import load_dotenv

    from backend.app.runtime.database import DatabaseSettings
    from backend.app.tripworld.retrieval.runtime import ROOT as rag_root
    from backend.app.versions.v1.config import V1Settings

    if not (ROOT / ".env").is_file():
        raise FileNotFoundError("RAG environment missing")
    load_dotenv(ROOT / ".env", override=False)
    V1Settings()
    DatabaseSettings(_env_file=ROOT / ".env").connection_parameters()
    if not os.environ.get("OPENAI_API_KEY"):
        raise ValueError("RAG local credentials incomplete")
    if read(rag_root / "reports/phase5_embedding_run.json").get("status") != "complete":
        raise ValueError("Local corpus build incomplete")
    if not read(rag_root / "artifacts/retrieval_entities.parquet.manifest.json").get(
        "output_sha256"
    ):
        raise ValueError("Local corpus manifest incomplete")


def prepare():
    today = today_and_validate()
    local_dependencies()
    if OUTPUT.exists():
        raise FileExistsError("Pilot already prepared; never reset attempts")
    config = yaml.safe_load((ROOT / "config/runtime.yaml").read_text(encoding="utf-8"))
    assert config["development_timeout_seconds"] == 600
    assert config["landmark_nomination"]["max_calls"] == 1
    assert not config["trace"]["raw_provider_payloads"]
    config["trace"]["enabled"] = True
    config["trace"]["payload_level"] = "normalized"
    OUTPUT.mkdir(parents=True)
    runtime = OUTPUT / "runtime.yaml"
    runtime.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    write(
        OUTPUT / "manifest.json",
        dict(
            prepared_date=today,
            source_hashes=source_hashes(),
            runtime_sha256=hashlib.sha256(runtime.read_bytes()).hexdigest(),
            git_head=subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            cases=list(CASES),
            authorized_attempts_per_case=1,
            application_seconds=600,
            outer_seconds=660,
        ),
    )
    print("Prepared offline; no provider constructed or called.")


def preflight(case):
    if case not in CASES:
        raise ValueError("Unknown case")
    manifest = read(OUTPUT / "manifest.json")
    if manifest["source_hashes"] != source_hashes():
        raise ValueError("Frozen source/input mismatch")
    if (
        manifest["runtime_sha256"]
        != hashlib.sha256((OUTPUT / "runtime.yaml").read_bytes()).hexdigest()
    ):
        raise ValueError("Frozen runtime mismatch")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if head != manifest["git_head"]:
        raise ValueError("Git revision changed")
    for previous in CASES[: CASES.index(case)]:
        status = read(OUTPUT / f"{previous}.finished.json")
        if not status["continue_allowed"]:
            raise ValueError("Previous case stopped the batch")
    if (OUTPUT / f"{case}.started.json").exists() or (OUTPUT / case).exists():
        raise FileExistsError("Attempt already consumed")
    local_dependencies()
    return today_and_validate()


class PilotCapture:
    """Bounded independent normalized lineage; observation failures never change planning."""

    def __init__(self, directory, secrets=()):
        self.errors, self.stages = [], []
        self.bytes = 0
        self.capture = None
        try:
            self.capture = DevelopmentRequirementCapture(
                directory, scenario_id="landmark_pilot", secrets=secrets
            )
        except Exception as exc:
            self.errors.append("initialization:" + type(exc).__name__)

    def save(self, stage, value):
        try:
            if self.capture is None:
                raise OSError("Capture initialization unavailable")
            value = value() if callable(value) else value
            allowance = min(1024 * 1024, 4 * 1024 * 1024 - self.bytes)
            if allowance <= 0:
                raise OverflowError("Case capture capacity")
            path = self.capture.record(stage, stage, value, max_bytes=allowance)
            if path is None:
                self.bytes += allowance  # A failed write can leave a partial file.
                raise OSError("Capture unavailable")
            self.bytes += path.stat().st_size
            self.stages.append(stage)
        except Exception as exc:
            self.errors.append(stage + ":" + type(exc).__name__)

    @contextlib.contextmanager
    def observe(self):
        from backend.app.services.landmark_discovery import LandmarkDiscovery
        from backend.app.services.landmark_nomination import LandmarkNominationService
        from backend.app.services.product_evidence import ProductEvidenceCollector
        from backend.app.versions.v3 import wiring

        nominate = LandmarkNominationService.nominate
        annotate = LandmarkDiscovery.annotate
        post = wiring.V3PostPrimary.__call__
        assess = wiring.assess
        event = ProductEvidenceCollector.event
        observer = self

        async def nomination(service, destination):
            try:
                return await nominate(service, destination)
            finally:
                observer.save(
                    "nomination",
                    lambda: dict(
                        destination=destination,
                        names=list(service.names),
                        outcome=service.snapshot(),
                    ),
                )

        def annotation(service, places):
            result = annotate(service, places)
            observer.save(
                "resolution",
                lambda: dict(
                    resolutions=[
                        dict(
                            name=r.named_place_intent.place_text,
                            status=r.status.value,
                            matching_ids=list(r.matching_place_ids),
                            resolved_id=r.resolved_place_id,
                        )
                        for r in service.resolutions(places)
                    ]
                ),
            )
            return result

        async def initial(extension, state):
            from backend.app.policies.poi_semantic_output import goal_progress

            observer.save(
                "initial",
                lambda: dict(
                    coverage=goal_progress(
                        state["itinerary"],
                        state["interpreted_requirements"],
                        state["review_selection"].semantic_assessments,
                    ),
                    itinerary=state["itinerary"].model_dump(mode="json"),
                    supply=state["review_selection"].policy_result.model_dump(mode="json"),
                    admitted_ids=[
                        p.candidate.place_id for p in state["candidate_funnel"].admitted_candidates
                    ],
                    enriched_ids=[
                        p.candidate.place_id for p in state["candidate_funnel"].enriched_candidates
                    ],
                ),
            )
            return await post(extension, state)

        def assessment(*args, **kwargs):
            report = assess(*args, **kwargs)
            if "initial_validation" not in observer.stages:
                observer.save(
                    "initial_validation", lambda: dict(report=report.model_dump(mode="json"))
                )
            return report

        def events(collector, name, payload=None):
            if name in {"v3_repair_round", "v3_finalized", "landmark_discovery"}:
                observer.save(name, dict(payload=payload))
            return event(collector, name, payload)

        with (
            patch.object(LandmarkNominationService, "nominate", nomination),
            patch.object(LandmarkDiscovery, "annotate", annotation),
            patch.object(wiring.V3PostPrimary, "__call__", initial),
            patch.object(wiring, "assess", assessment),
            patch.object(ProductEvidenceCollector, "event", events),
        ):
            yield


def child(case, reference):
    from dotenv import load_dotenv

    from backend.app.versions.v1.config import V1Settings
    from tools.validation.poi_semantics_acceptance import run_case

    load_dotenv(ROOT / ".env", override=False)
    settings = V1Settings()
    secrets = (
        settings.azure_openai_api_key.get_secret_value(),
        settings.google_maps_api_key.get_secret_value(),
    )
    capture = PilotCapture(OUTPUT / f"{case}.lineage", secrets)
    with capture.observe():
        status = run_case(
            INPUTS / f"{case}.json",
            OUTPUT / case,
            version="v3",
            runtime_config=OUTPUT / "runtime.yaml",
            reference_date=reference,
            capture_requirements=True,
            capture_semantics=True,
            capture_repair=True,
        )
    if status["application_exit_code"] == 0:
        from backend.app.versions.v3.state import V3PlanningResult

        result = V3PlanningResult.model_validate(read(OUTPUT / case / "result.json"))
        capture.save(
            "final",
            lambda: dict(
                itinerary=result.v3.final_primary.model_dump(mode="json"),
                original_report=result.v3.original_report.model_dump(mode="json"),
                final_report=result.v3.final_report.model_dump(mode="json"),
                reason=result.v3.reason,
                repair=result.v3.repair.model_dump(mode="json") if result.v3.repair else None,
            ),
        )
        for stage in ("nomination", "resolution", "initial", "initial_validation", "final"):
            if stage not in capture.stages:
                capture.errors.append(stage + ":missing")
    for directory in status["trace_directories"]:
        if not (Path(directory) / "budget.json").is_file():
            capture.errors.append("budget:missing")
    if status["application_exit_code"] == 0 and not status["trace_directories"]:
        capture.errors.append("trace:missing")
    write(OUTPUT / f"{case}.capture.json", dict(errors=capture.errors, stages=capture.stages))
    complete = (
        status["application_exit_code"] == 0
        and not capture.errors
        and status["capture_status"] == "complete"
        and status["semantic_capture_status"] == "complete"
        and status["repair_capture_status"] == "complete"
    )
    return 0 if complete else 1


def execute(case):
    reference = preflight(case)
    if not (ROOT / ".env").is_file():
        raise FileNotFoundError("RAG environment missing")
    write(OUTPUT / f"{case}.started.json", dict(reference_date=reference, attempt=1))
    try:
        process = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                CHILD_MODULE,
                "child",
                "--case",
                case,
                "--reference",
                reference,
            ],
            cwd=ROOT,
            capture_output=True,
            timeout=660,
            check=False,
        )
        status = dict(
            exit_code=process.returncode,
            outer_timeout=False,
            continue_allowed=process.returncode == 0,
        )
    except subprocess.TimeoutExpired:
        status = dict(exit_code=None, outer_timeout=True, continue_allowed=False)
    write(OUTPUT / f"{case}.finished.json", status)
    print(json.dumps(status))
    return 0 if status["continue_allowed"] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "execute", "child"))
    parser.add_argument("--case", choices=CASES)
    parser.add_argument("--reference")
    args = parser.parse_args()
    if args.action == "prepare":
        prepare()
        return 0
    if not args.case:
        parser.error("Case required")
    if args.action == "child":
        if not (OUTPUT / f"{args.case}.started.json").exists():
            parser.error("Use the one-shot execute action")
        with (OUTPUT / f"{args.case}.child.lock").open("x"):
            pass
        try:
            return child(args.case, args.reference)
        except Exception as exc:
            write(OUTPUT / f"{args.case}.error.json", dict(error_type=type(exc).__name__))
            return 1
    return execute(args.case)


if __name__ == "__main__":
    raise SystemExit(main())
