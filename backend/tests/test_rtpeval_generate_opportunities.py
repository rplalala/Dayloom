"""Offline selected-generation capture through real V1/V2 graphs and native readers."""

import json
from contextlib import asynccontextmanager
from datetime import date
from types import SimpleNamespace

import pytest

from backend.app.services.planner_runtime import PlannerDependencies, RequestPlannerRuntime
from backend.cli.rtpeval import main
from backend.tests.request_fixtures import make_request
from backend.tests.services.test_tripworld_discovery import Retrieval, hit
from backend.tests.test_rtpeval_cli import installed_cli as cli_fixture
from backend.tests.test_rtpeval_generate_cli import REFERENCE_BOOTSTRAP, arguments, registration
from backend.tests.versions.v0.fakes import FakeStructuredLLMClient
from backend.tests.versions.v1.fakes import FakeRoutesProvider, FakeWeatherProvider, make_itinerary
from backend.tests.versions.v2.test_opportunity_capture import stable
from backend.tests.versions.v2.test_v2_runner import Places

REFERENCE = SimpleNamespace(today=lambda: date(2026, 9, 11))
installed_cli = cli_fixture

SYNTHETIC_BOOTSTRAP = """
from pytest import MonkeyPatch
from backend.tests.test_rtpeval_generate_opportunities import synthetic_runtime, REFERENCE
from backend.evaluation.tools import planner_usage_cli
runtime, dependencies, trace_ids = synthetic_runtime(MonkeyPatch())
planner_usage_cli.RequestPlannerRuntime = lambda **kwargs: runtime
planner_usage_cli.SystemDateProvider = lambda: REFERENCE
"""


def synthetic_runtime(monkeypatch, *, llm=None, places=None):
    deps = PlannerDependencies(
        llm=llm or FakeStructuredLLMClient([make_itinerary()]),
        places=places or Places(),
        weather=FakeWeatherProvider(),
        routes=FakeRoutesProvider(),
    )
    trace_ids = []

    @asynccontextmanager
    async def factory(version, config, tracer):
        trace_ids.append(str(tracer.run_id))
        yield deps

    monkeypatch.setattr(
        "backend.app.services.tripworld_discovery.RuntimeRetrieval",
        lambda config: Retrieval([hit("aaa-rag")]),
    )
    monkeypatch.setattr(
        "backend.evaluation.tools.planner_usage_cli.load_dotenv", lambda *a, **k: None
    )
    return RequestPlannerRuntime(dependency_factory=factory), deps, trace_ids


def generate(tmp_path, version, runtime, *, capture=True, evidence=False, register=False):
    args = arguments(tmp_path, version, execute=True)
    (tmp_path / "input.json").write_text(make_request().model_dump_json(), encoding="utf-8")
    if capture:
        args += ["--opportunity-capture", str(tmp_path / "capture/opportunities.json")]
    if evidence:
        args += ["--capture-evidence"]
    if register:
        args += registration(tmp_path, version)
    code = main(["generate", *args], runtime=runtime, date_provider=REFERENCE)
    return code, json.loads((tmp_path / "capture/manifest.json").read_bytes())


@pytest.mark.parametrize("version", ["v1", "v2"])
@pytest.mark.parametrize("evidence", [False, True])
def test_selected_run_binding_and_passive_output_parity(tmp_path, monkeypatch, version, evidence):
    outputs, calls = [], []
    for enabled in (False, True):
        root = tmp_path / str(enabled)
        root.mkdir()
        runtime, deps, trace_ids = synthetic_runtime(monkeypatch)
        code, manifest = generate(root, version, runtime, capture=enabled, evidence=evidence)
        assert code == 0
        result = json.loads((root / "capture/result.json").read_bytes())
        outputs.append(stable(result))
        calls.append(
            (
                deps.llm.calls,
                deps.places.search_requests,
                deps.places.details_requests,
                deps.places.reviews_requests,
                deps.places.nearby,
                deps.weather.requests,
                deps.routes.requests,
            )
        )
        if enabled:
            captured = json.loads((root / "capture/opportunities.json").read_bytes())
            assert captured["run_id"] == "r" != trace_ids[0]
            assert captured["version"] == version
            assert set(captured["stages"]) == {"discovered", "admitted", "enriched", "supplied"}
            assert all(stage["status"] == "complete" for stage in captured["stages"].values())
            assert len(captured["stages"]["supplied"]["places"]) == (9 if version == "v1" else 10)
            assert manifest["opportunity_capture_ref"]["availability"] == "available"
        else:
            assert "opportunity_capture_ref" not in manifest
            assert not (root / "capture/opportunities.json").exists()
    assert outputs[0] == outputs[1]
    assert calls[0] == calls[1]


@pytest.mark.parametrize(
    "fault",
    ["existing", "directory", "write_failure", "missing_export", "failure", "cancelled", "partial"],
)
def test_capture_missingness_preserves_planner_outcome(tmp_path, monkeypatch, fault):
    import asyncio

    class FailingLLM(FakeStructuredLLMClient):
        async def generate_structured(self, **kwargs):
            raise asyncio.CancelledError() if fault == "cancelled" else RuntimeError("fixture")

    sidecar = tmp_path / "capture/opportunities.json"
    if fault == "existing":
        # Keep an external existing sidecar; the output directory itself stays fresh.
        sidecar = tmp_path / "existing.json"
        sidecar.write_bytes(b"caller-owned material")
    elif fault == "directory":
        sidecar = tmp_path
    elif fault == "write_failure":
        (tmp_path / "blocked").write_bytes(b"caller-owned parent file")
        sidecar = tmp_path / "blocked/opportunities.json"
    runtime, _, _ = synthetic_runtime(
        monkeypatch,
        llm=FailingLLM([]) if fault in ("failure", "cancelled") else None,
    )
    if fault == "partial":
        monkeypatch.setattr(
            "backend.app.services.tripworld_discovery.RuntimeRetrieval",
            lambda config: Retrieval([], fail=True),
        )
    if fault == "missing_export":
        from backend.tests.test_rtpeval_generate_cli import Runtime

        runtime = Runtime()
    args = arguments(tmp_path, "v2" if fault == "partial" else "v1", execute=True)
    (tmp_path / "input.json").write_text(make_request().model_dump_json(), encoding="utf-8")
    code = main(
        ["generate", *args, "--opportunity-capture", str(sidecar)],
        runtime=runtime,
        date_provider=REFERENCE,
    )
    manifest = json.loads((tmp_path / "capture/manifest.json").read_bytes())
    assert code == (1 if fault in ("failure", "cancelled") else 0)
    assert manifest["status"] == ("failed" if code else "completed")
    ref = manifest["opportunity_capture_ref"]
    if fault in ("failure", "cancelled", "partial"):
        assert ref["availability"] == "available"
        capture = json.loads(sidecar.read_bytes())
        if fault == "partial":
            assert capture["stages"]["discovered"]["status"] == "partial"
            assert "rag_unavailable" in capture["stages"]["discovered"]["reasons"]
        else:
            assert capture["outcome"] == "failed"
            assert capture["result_semantic_sha256"] is None
            assert capture["failure_type"] == manifest["failure_type"]
            assert capture["stages"]["discovered"]["places"]
    else:
        assert ref["availability"] == "unavailable"
        assert ref["reason"] == (
            "capture_path_exists"
            if fault in ("existing", "directory")
            else "capture_export_unavailable"
        )
        if fault == "existing":
            assert sidecar.read_bytes() == b"caller-owned material"
    assert (tmp_path / "capture/result.json").is_file() == (code == 0)


@pytest.mark.parametrize("version", ["v0", "v3"])
def test_unsupported_version_capture_is_rejected_before_preparation(
    installed_cli, tmp_path, version
):
    result = installed_cli(
        "generate",
        *arguments(tmp_path, version),
        "--opportunity-capture",
        tmp_path / "sidecar.json",
        tools_offline=True,
    )
    assert result.returncode == 2
    assert "only supports V1/V2" in result.stderr
    assert not (tmp_path / "capture").exists()


@pytest.mark.parametrize(
    "name", ["result.json", "usage.json", "manifest.json", "producer-completion.json"]
)
def test_capture_cannot_collide_with_generation_material(installed_cli, tmp_path, name):
    result = installed_cli(
        "generate",
        *arguments(tmp_path, "v1"),
        "--opportunity-capture",
        tmp_path / "capture" / name,
        tools_offline=True,
        bootstrap=REFERENCE_BOOTSTRAP,
    )
    assert result.returncode == 2
    assert not (tmp_path / "capture").exists()


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_installed_generation_captures_real_synthetic_graph(
    installed_cli, tmp_path_factory, version
):
    # Native trace paths need room below the Windows legacy path-length limit.
    tmp_path = tmp_path_factory.mktemp("graph")
    args = arguments(tmp_path, version, execute=True)
    (tmp_path / "input.json").write_text(make_request().model_dump_json(), encoding="utf-8")
    result = installed_cli(
        "generate",
        *args,
        *registration(tmp_path, version),
        "--capture-evidence",
        "--opportunity-capture",
        tmp_path / "capture/opportunities.json",
        tools_offline=True,
        bootstrap=SYNTHETIC_BOOTSTRAP,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    capture = json.loads((tmp_path / "capture/opportunities.json").read_bytes())
    assert capture["run_id"] == "r"
    assert capture["version"] == version
    assert capture["outcome"] == "completed"
    assert all(stage["status"] == "complete" for stage in capture["stages"].values())
    assert (tmp_path / "staging/sources/capture/opportunities.json").read_bytes() == (
        tmp_path / "capture/opportunities.json"
    ).read_bytes()


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_registered_capture_enters_explicit_research_declaration(
    tmp_path,
    monkeypatch,
    installed_cli,
    version,
):
    from backend.tests.research_native_fixtures import declare_native, file_ref
    from backend.tests.test_rtpeval_research_population_cli import save

    runtime, _, _ = synthetic_runtime(monkeypatch)
    assert generate(tmp_path, version, runtime, register=True)[0] == 0
    root = tmp_path / "staging"
    native = json.loads((root / "staging.json").read_bytes())
    captured_path = root / "sources/capture/opportunities.json"
    assert captured_path.read_bytes() == (tmp_path / "capture/opportunities.json").read_bytes()
    assert not (root / "census.json").exists()
    declaration_path = declare_native(root, native)
    profile = json.loads((root / "profile.json").read_bytes())
    census = json.loads((root / "census.json").read_bytes())
    configuration = file_ref(root, root / "sources/capture/runtime-policy.json")
    profile["configurations"][version] = configuration
    attempt = census["attempts"][0]
    attempt["configuration_sha256"] = configuration["sha256"]
    attempt["completion_ref"] = file_ref(root, root / "sources/capture/producer-completion.json")
    entry = {
        key: attempt[key]
        for key in (
            "case_id",
            "case_revision",
            "version",
            "repetition_id",
            "attempt_id",
            "run_id",
            "input_sha256",
            "configuration_sha256",
        )
    }
    entry.update(
        result_sha256=attempt["result_ref"]["sha256"], capture_ref=file_ref(root, captured_path)
    )
    declaration = json.loads(declaration_path.read_bytes())
    declaration["profile_ref"] = save(root, "profile.json", profile)
    declaration["census_ref"] = save(root, "census.json", census)
    declaration["track_refs"] = {
        "opportunities": save(
            root,
            "opportunities-input.json",
            {
                "schema_version": "rtpeval_research_opportunities_1",
                "observations": [entry],
            },
        )
    }
    save(root, "research.json", declaration)
    valid = installed_cli("research", "validate", declaration_path, "--track", "opportunities")
    assert valid.returncode == 0, valid.stdout + valid.stderr
    report = installed_cli(
        "research",
        "report",
        declaration_path,
        "--track",
        "opportunities",
        "--directory",
        tmp_path / "report",
    )
    assert report.returncode == 0, report.stdout + report.stderr
    value = json.loads((tmp_path / "report/opportunities.json").read_bytes())
    assert value["runs"][0]["stages"]["supplied"]["complete_count"] == (
        9 if version == "v1" else 10
    )
    assert value["runs"][0]["scheduled"]["status"] == "unavailable"
    original_capture = captured_path.read_bytes()
    for fault in ("foreign_run", "source_drift", "input", "configuration", "result"):
        captured_path.write_bytes(original_capture)
        changed = dict(entry)
        if fault == "foreign_run":
            capture = json.loads(original_capture)
            capture["run_id"] = "foreign"
            changed["capture_ref"] = save(root, "sources/capture/opportunities.json", capture)
        elif fault == "source_drift":
            captured_path.write_bytes(original_capture + b" ")
        else:
            changed[fault + "_sha256"] = "0" * 64
        declaration["track_refs"]["opportunities"] = save(
            root,
            "opportunities-input.json",
            {
                "schema_version": "rtpeval_research_opportunities_1",
                "observations": [changed],
            },
        )
        save(root, "research.json", declaration)
        rejected = installed_cli(
            "research", "validate", declaration_path, "--track", "opportunities"
        )
        assert rejected.returncode == 2, fault + rejected.stdout + rejected.stderr
