"""Cancellation lineage from selected generation to source-bound research reports."""

import asyncio
import hashlib
import json

import pytest

from backend.app.observability.usage import observe_sdk
from backend.tests.test_rtpeval_cli import installed_cli as cli_fixture
from backend.tests.test_rtpeval_generate_cli import REFERENCE, Runtime, arguments, registration
from backend.tests.test_rtpeval_research_population_cli import (
    add_attempt,
)
from backend.tests.test_rtpeval_research_population_cli import (
    research_material as research_fixture,
)

installed_cli = cli_fixture
research_material = research_fixture


class InterruptedRuntime(Runtime):
    def __init__(self, error=asyncio.CancelledError, phase="before"):
        self.error = error
        self.phase = phase

    async def run(self, version, request, **kwargs):
        async def embedding(**kwargs):
            return {"usage": {"input_tokens": 1000, "total_tokens": 1000}}

        await observe_sdk(
            embedding,
            usage_provider="openai",
            usage_operation="embedding",
            model="text-embedding-3-small",
        )
        try:
            if self.phase == "before":
                raise self.error()
            return await super().run(version, request, **kwargs)
        finally:
            if self.phase == "cleanup":
                raise self.error()


BOOTSTRAP = """
from backend.evaluation.tools import planner_usage_cli
from backend.tests.test_rtpeval_generate_cancellation import InterruptedRuntime, REFERENCE
planner_usage_cli.RequestPlannerRuntime = lambda **kwargs: InterruptedRuntime()
planner_usage_cli.load_dotenv = lambda *args, **kwargs: None
planner_usage_cli.SystemDateProvider = lambda: REFERENCE
"""


@pytest.mark.parametrize("version", ["v0", "v1", "v2", "v3"])
@pytest.mark.parametrize("phase", ["before", "cleanup"])
def test_cancellation_retains_usage_and_native_completion(tmp_path, version, phase):
    from backend.cli.rtpeval import main

    args = arguments(tmp_path, version=version, execute=True)
    selection = registration(tmp_path, version=version)
    assert (
        main(
            ["generate", *args, *selection, "--capture-evidence"],
            runtime=InterruptedRuntime(phase=phase),
            date_provider=REFERENCE,
        )
        == 1
    )
    assert_cancelled(tmp_path, version)
    assert json.loads((tmp_path / "capture/mechanism.json").read_bytes())["outcome"] == "cancelled"
    assert (
        json.loads((tmp_path / "capture/evidence-index.json").read_bytes())["outcome"]
        == "cancelled"
    )


def assert_cancelled(root, version):
    capture = root / "capture"
    usage = json.loads((capture / "usage.json").read_bytes())
    assert usage["outcome"] == "cancelled"
    assert usage["result_sha256"] is None
    assert usage["model_calls"][0]["total_tokens"] == 1000
    assert json.loads((capture / "manifest.json").read_bytes())["status"] == "cancelled"
    assert json.loads((capture / "failure.json").read_bytes())["error_type"] == "CancelledError"
    assert (
        json.loads((capture / "producer-completion.json").read_bytes())["workflow_status"]
        == "cancelled"
    )
    run = json.loads((root / "staging/staging.json").read_bytes())["groups"][0]["selected_runs"][
        version
    ]
    assert not run["completion_qualified"]
    assert "workflow_not_completed" in run["blocking_reasons"]
    assert (root / "staging/sources/capture/usage.json").read_bytes() == (
        capture / "usage.json"
    ).read_bytes()
    assert not (capture / "result.json").exists()
    assert not (capture / "provenance.json").exists()
    cost = json.loads((capture / "cost-report.json").read_bytes())
    assert cost["runs"][0]["estimated_observed_subtotal"] == "0.00002"


@pytest.mark.parametrize("error", [RuntimeError, TimeoutError, KeyboardInterrupt])
def test_other_exceptions_remain_failed_with_original_error(tmp_path, error):
    from backend.cli.rtpeval import main

    args = arguments(tmp_path, execute=True)
    assert (
        main(
            ["generate", *args, *registration(tmp_path)],
            runtime=InterruptedRuntime(error),
            date_provider=REFERENCE,
        )
        == 1
    )
    for name, field in [
        ("usage.json", "outcome"),
        ("manifest.json", "status"),
        ("producer-completion.json", "workflow_status"),
    ]:
        assert json.loads((tmp_path / "capture" / name).read_bytes())[field] == "failed"
    assert (
        json.loads((tmp_path / "capture/failure.json").read_bytes())["error_type"] == error.__name__
    )
    assert not (tmp_path / "capture/result.json").exists()


def source_ref(root, path):
    value = json.loads(path.read_bytes())
    return {
        "path": path.relative_to(root).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "media_type": "application/json",
        "availability": "available",
        **({"schema_version": value["schema_version"]} if "schema_version" in value else {}),
    }


def test_installed_cancelled_generation_drives_population_and_tradeoffs(
    installed_cli, research_material, tmp_path
):
    root, population, profile, census, write = research_material
    args = arguments(root, execute=True)
    generation = installed_cli(
        "generate", *args, *registration(root), tools_offline=True, bootstrap=BOOTSTRAP
    )
    assert generation.returncode == 1, generation.stdout + generation.stderr
    assert_cancelled(root, "v0")
    population["cases"] = population["cases"][:1]
    case = population["cases"][0]
    case["input_ref"] = source_ref(root, root / "input.json")
    profile["configurations"]["v0"] = source_ref(root, root / "capture/runtime-policy.json")
    attempt = add_attempt(research_material, 0, "v0", "cancelled")
    attempt.update(
        group_id="g",
        run_id="r",
        reason_type="operator_cancelled",
        completion_ref=source_ref(root, root / "capture/producer-completion.json"),
        usage_ref=source_ref(root, root / "capture/usage.json"),
    )
    declaration = write()
    originals = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    for track in ("population", "tradeoffs"):
        valid = installed_cli("research", "validate", declaration, "--track", track)
        assert valid.returncode == 0, valid.stdout + valid.stderr
        directory = tmp_path / track
        report = installed_cli(
            "research", "report", declaration, "--track", track, "--directory", directory
        )
        assert report.returncode == 0, report.stdout + report.stderr
    pop = json.loads((tmp_path / "population/population.json").read_bytes())
    assert pop["summary"]["status_counts"]["cancelled"] == 1
    assert pop["summary"]["status_counts"]["failed"] == 0
    assert pop["slots"][0]["primary_attempt"]["attempt_id"] == attempt["attempt_id"]
    tradeoffs = json.loads((tmp_path / "tradeoffs/tradeoffs.json").read_bytes())
    row = tradeoffs["all_attempts"]["rows"][0]
    assert row["selected_primary"] is True
    assert row["elapsed_cohort"] == "failed_or_censored"
    assert row["metrics"]["total_tokens"] == 1000
    assert tradeoffs["all_attempts"]["totals"]["total_tokens"]["observed_subtotal"] == 1000
    assert originals == {p: p.read_bytes() for p in originals}


@pytest.mark.parametrize("sink_failure", ["directory", "partial_write"])
def test_cancelled_usage_sink_failure_retains_known_outcome_and_observations(
    tmp_path, monkeypatch, sink_failure
):
    from backend.cli.rtpeval import main

    partial = b'{"schema_version":'
    if sink_failure == "partial_write":
        from pathlib import Path

        write_bytes = Path.write_bytes

        def failing_write(path, data):
            if path == tmp_path / "capture/usage.json":
                write_bytes(path, partial)
                raise OSError("Synthetic interrupted artifact write")
            return write_bytes(path, data)

        monkeypatch.setattr(Path, "write_bytes", failing_write)

    class SinkRuntime(InterruptedRuntime):
        async def run(self, *args, **kwargs):
            if sink_failure == "directory":
                (tmp_path / "capture/usage.json").mkdir()
            return await super().run(*args, **kwargs)

    args = arguments(tmp_path, execute=True)
    assert (
        main(
            ["generate", *args, *registration(tmp_path), "--capture-evidence"],
            runtime=SinkRuntime(),
            date_provider=REFERENCE,
        )
        == 1
    )
    manifest = json.loads((tmp_path / "capture/manifest.json").read_bytes())
    assert manifest["status"] == "cancelled"
    assert manifest["capture_status"] == "capture_failed"
    failure = json.loads((tmp_path / "capture/failure.json").read_bytes())
    assert failure["error_type"] == "CancelledError"
    assert failure["observed_usage"]["outcome"] == "cancelled"
    assert failure["observed_usage"]["model_calls"][0]["total_tokens"] == 1000
    completion = json.loads((tmp_path / "capture/producer-completion.json").read_bytes())
    assert completion["workflow_status"] == "cancelled"
    run = json.loads((tmp_path / "staging/staging.json").read_bytes())["groups"][0][
        "selected_runs"
    ]["v0"]
    assert not run["completion_qualified"]
    assert "missing_material:usage_ref" in run["blocking_reasons"]
    assert run["usage_ref"] is None
    evidence = json.loads((tmp_path / "capture/evidence-index.json").read_bytes())
    assert evidence["outcome"] == "cancelled"
    assert "usage" in evidence["missing_fields"]
    assert (tmp_path / "staging/sources/capture/failure.json").read_bytes() == (
        tmp_path / "capture/failure.json"
    ).read_bytes()
    if sink_failure == "partial_write":
        assert (tmp_path / "capture/usage.json").read_bytes() == partial
    assert not (tmp_path / "capture/result.json").exists()
