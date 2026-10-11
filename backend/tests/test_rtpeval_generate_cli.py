"""Selected Planner delegation and explicit source registration at the public CLI."""

import json
from datetime import date
from types import SimpleNamespace

import pytest

from backend.tests.test_rtpeval_cli import installed_cli as cli_fixture

installed_cli = cli_fixture
REFERENCE = SimpleNamespace(today=lambda: date(2026, 10, 8))


def arguments(tmp_path, version="v0", execute=False):
    source = tmp_path / "input.json"
    source.write_text(
        json.dumps(
            {
                "input_version": "planning_request_2",
                "destination": "Sydney, Australia",
                "start_date": "2026-10-14",
                "end_date": "2026-10-14",
                "traveler_count": 2,
                "budget": {"amount": "1600", "currency": "AUD"},
            }
        ),
        encoding="utf-8",
    )
    return [
        "--version",
        version,
        "--input-json",
        str(source),
        "--output-directory",
        str(tmp_path / "capture"),
        "--group-id",
        "g",
        "--run-id",
        "r",
        "--env-file",
        str(tmp_path / ".env"),
    ] + (["--execute"] if execute else [])


def test_installed_generation_preparation_preserves_native_capture(installed_cli, tmp_path):
    args = arguments(tmp_path)
    current = installed_cli("generate", *args, tools_offline=True)
    assert current.returncode == 0, current.stderr
    original = (tmp_path / "capture/input.json").read_bytes()
    assert original == (tmp_path / "input.json").read_bytes()
    manifest = json.loads((tmp_path / "capture/manifest.json").read_bytes())
    assert manifest["status"] == "prepared"
    assert not (tmp_path / "capture/usage.json").exists()
    assert not (tmp_path / "capture/generation-registration.json").exists()


def test_installed_opportunity_preparation_is_offline(installed_cli, tmp_path):
    sidecar = tmp_path / "capture/opportunities.json"
    result = installed_cli(
        "generate",
        *arguments(tmp_path, version="v1"),
        "--opportunity-capture",
        sidecar,
        tools_offline=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    manifest = json.loads((tmp_path / "capture/manifest.json").read_bytes())
    assert manifest["opportunity_capture_requested"] is True
    assert "opportunity_capture_ref" not in manifest
    assert not sidecar.exists()
    assert not (tmp_path / "capture/result.json").exists()
    assert not (tmp_path / "capture/usage.json").exists()
    help_result = installed_cli("generate", "--help", tools_offline=True)
    assert "--opportunity-capture" in help_result.stdout


def registration(tmp_path, version="v0"):
    import hashlib

    source = tmp_path / "input.json"
    config = {
        "schema_version": "rtpeval_collection_1",
        "batch_id": "b",
        "revision": "1",
        "created_at": "now",
        "qualification_policy_ref": "selected_workflow_1",
        "groups": [
            {
                "group_id": "g",
                "input_ref": {
                    "path": "input.json",
                    "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                    "media_type": "application/json",
                    "availability": "available",
                },
                "selected_runs": {version: {"run_id": "r", "capture_directory": "capture"}},
            }
        ],
    }
    path = tmp_path / "selection.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    return ["--register-batch", str(path), "--registration-directory", str(tmp_path / "staging")]


class Runtime:
    async def run(self, version, request, **kwargs):
        from backend.tests.evaluation.test_planner_usage_cli import result

        return result(version, request)


@pytest.mark.parametrize(
    "fault,diagnostic",
    [
        ("wrong_run", "exactly one explicitly selected run"),
        ("wrong_group", "exactly one explicitly selected run"),
        ("wrong_version", "exactly one explicitly selected run"),
        ("capture_directory", "capture_directory differs"),
        ("escape", "escapes collection root"),
        ("input_hash", "input hash mismatch"),
        ("different_input", "differs from Planner input"),
        ("malformed", "Expecting"),
        ("duplicate_key", "Duplicate JSON key"),
        ("schema", "Expected rtpeval_collection_1"),
        ("missing_batch", "Missing collection batch_id"),
        ("invalid_slots", "selected_runs maps"),
        ("missing_run", "Missing selected run identity"),
        ("duplicate_group", "Duplicate group identity"),
        ("duplicate_run", "Duplicate run identity"),
        ("unsupported_version", "v0-v3"),
        ("input_reference", "original input reference"),
        ("result_ref", "refuses replacement"),
        ("usage_ref", "refuses replacement"),
        ("provenance_ref", "refuses replacement"),
        ("producer_declaration", "refuses replacement"),
        ("completion", "refuses replacement"),
        ("existing_directory", "destination must be fresh"),
        ("existing_file", "destination must be fresh"),
        ("output_overlap", "contains Planner output"),
    ],
)
@pytest.mark.parametrize("injected", [False, True])
def test_invalid_registration_does_not_start_planner(
    tmp_path, monkeypatch, capsys, fault, diagnostic, injected
):
    import httpx

    from backend.cli.rtpeval import main
    from backend.evaluation.tools import planner_usage_cli

    args = arguments(tmp_path, execute=True)
    selection = registration(tmp_path)
    path = tmp_path / "selection.json"
    config = json.loads(path.read_bytes())
    group = config["groups"][0]
    slot = group["selected_runs"]["v0"]
    if fault == "wrong_run":
        slot["run_id"] = "different-run"
    elif fault == "wrong_group":
        group["group_id"] = "other-group"
    elif fault == "wrong_version":
        group["selected_runs"] = {"v1": slot}
    elif fault == "capture_directory":
        slot["capture_directory"] = "other-capture"
    elif fault == "escape":
        slot["capture_directory"] = "../escape"
    elif fault == "input_hash":
        group["input_ref"]["sha256"] = "0" * 64
    elif fault == "different_input":
        alternate = tmp_path / "different-input.json"
        alternate.write_text("{}", encoding="utf-8")
        args[args.index("--input-json") + 1] = str(alternate)
    elif fault == "schema":
        config["schema_version"] = "other"
    elif fault == "missing_batch":
        del config["batch_id"]
    elif fault == "invalid_slots":
        group["selected_runs"] = []
    elif fault == "missing_run":
        del slot["run_id"]
    elif fault == "duplicate_group":
        config["groups"].append(group)
    elif fault == "duplicate_run":
        group["selected_runs"]["v1"] = {"run_id": "r", "capture_directory": "next"}
    elif fault == "unsupported_version":
        group["selected_runs"]["v4"] = {"run_id": "next"}
    elif fault == "input_reference":
        group["input_ref"] = None
    elif fault in (
        "result_ref",
        "usage_ref",
        "provenance_ref",
        "producer_declaration",
        "completion",
    ):
        slot[fault] = {}
    elif fault == "existing_directory":
        (tmp_path / "staging").mkdir()
    elif fault == "existing_file":
        (tmp_path / "staging").write_text("preserved", encoding="utf-8")
    elif fault == "output_overlap":
        selection[-1] = str(tmp_path / "capture")
    path.write_text(json.dumps(config), encoding="utf-8")
    if fault == "malformed":
        path.write_text("{", encoding="utf-8")
    elif fault == "duplicate_key":
        path.write_text('{"groups": [], "groups": []}', encoding="utf-8")
    originals = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    attempted = dict.fromkeys(("credentials", "construction", "runtime", "provider"), 0)

    def forbidden(operation):
        def fail(*args, **kwargs):
            attempted[operation] += 1
            raise AssertionError("Invalid registration must remain offline: " + operation)

        return fail

    monkeypatch.setattr(planner_usage_cli, "load_dotenv", forbidden("credentials"))
    monkeypatch.setattr(
        planner_usage_cli.RequestPlannerRuntime, "__init__", forbidden("construction")
    )
    monkeypatch.setattr(planner_usage_cli.RequestPlannerRuntime, "run", forbidden("runtime"))
    monkeypatch.setattr(httpx.Client, "send", forbidden("provider"))
    monkeypatch.setattr(httpx.AsyncClient, "send", forbidden("provider"))
    guarded_runtime = SimpleNamespace(run=forbidden("runtime")) if injected else None
    assert (
        main(["generate", *args, *selection], runtime=guarded_runtime, date_provider=REFERENCE) == 2
    )
    report = json.loads(capsys.readouterr().out)
    assert report["planner"]["status"] == "not_invoked"
    assert report["registration"]["status"] == "failed"
    assert diagnostic in report["registration"]["diagnostics"][0]
    assert attempted == {"credentials": 0, "construction": 0, "runtime": 0, "provider": 0}
    assert not (tmp_path / "capture").exists()
    assert {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()} == originals


@pytest.mark.parametrize(
    "version,fault",
    [("v0", "wrong_run"), ("v1", "directory"), ("v2", "malformed"), ("v3", "capture")],
)
def test_installed_registration_rejection_is_offline(installed_cli, tmp_path, version, fault):
    args = arguments(tmp_path, version=version, execute=True)
    selection = registration(tmp_path, version=version)
    path = tmp_path / "selection.json"
    config = json.loads(path.read_bytes())
    if fault == "wrong_run":
        config["groups"][0]["selected_runs"][version]["run_id"] = "wrong"
    elif fault == "directory":
        (tmp_path / "staging").mkdir()
    elif fault == "capture":
        config["groups"][0]["selected_runs"][version]["capture_directory"] = "other"
    path.write_text("{" if fault == "malformed" else json.dumps(config), encoding="utf-8")
    result = installed_cli("generate", *args, *selection, tools_offline=True)
    assert result.returncode == 2, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["planner"]["status"] == "not_invoked"
    assert report["registration"]["status"] == "failed"
    assert not (tmp_path / "capture").exists()


def test_completed_generation_registers_exact_originals_without_requirements(tmp_path, capsys):
    from backend.cli.rtpeval import main

    args = arguments(tmp_path, execute=True)
    selection = registration(tmp_path)
    original_selection = (tmp_path / "selection.json").read_bytes()
    assert main(["generate", *args, *selection], runtime=Runtime(), date_provider=REFERENCE) == 0
    staging = json.loads((tmp_path / "staging/staging.json").read_bytes())
    assert staging["pending_requirement_review"]
    run = staging["groups"][0]["selected_runs"]["v0"]
    assert run["completion_qualified"]
    for name in ("input.json", "result.json", "usage.json", "provenance.json"):
        assert (tmp_path / "staging/sources/capture" / name).read_bytes() == (
            tmp_path / "capture" / name
        ).read_bytes()
    assert (tmp_path / "selection.json").read_bytes() == original_selection
    assert (tmp_path / "capture/operator-selection.json").read_bytes() == original_selection
    report = json.loads(capsys.readouterr().out.splitlines()[-1])
    assert report["planner"]["status"] == "completed"
    assert report["registration"]["status"] == "incomplete"


def test_generation_without_registration_matches_native_artifacts_and_exits(
    tmp_path, monkeypatch, capsys
):
    from datetime import datetime

    from backend.cli.rtpeval import main
    from backend.evaluation.tools import planner_usage_cli

    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 10, 9, tzinfo=tz)

    from backend.app.observability import usage, usage_capture

    monkeypatch.setattr(planner_usage_cli, "datetime", FixedDatetime)
    monkeypatch.setattr(usage_capture, "datetime", FixedDatetime)
    monkeypatch.setattr(usage, "datetime", FixedDatetime)
    monkeypatch.setattr(usage.UsageLedger.__init__, "__kwdefaults__", {"clock": lambda: 1.0})
    for fail in (False, True):

        class ComparedRuntime(Runtime):
            async def run(self, *args, fail=fail, **kwargs):
                if fail:
                    raise TimeoutError("fixture")
                return await super().run(*args, **kwargs)

        root = tmp_path / str(fail)
        root.mkdir()
        args = arguments(root, execute=True)
        current = main(["generate", *args], runtime=ComparedRuntime(), date_provider=REFERENCE)
        current_text = capsys.readouterr().out
        alternate = list(args)
        alternate[alternate.index("--output-directory") + 1] = str(root / "legacy")
        legacy = planner_usage_cli.main(
            alternate, runtime=ComparedRuntime(), date_provider=REFERENCE
        )
        legacy_text = capsys.readouterr().out
        assert current == legacy == int(fail)
        assert json.loads(current_text)["status"] == json.loads(legacy_text)["status"]
        assert {p.name: p.read_bytes() for p in (root / "capture").iterdir()} == {
            p.name: p.read_bytes() for p in (root / "legacy").iterdir()
        }


def test_post_dispatch_registration_conflict_preserves_successful_planner(tmp_path, capsys):
    from backend.cli.rtpeval import main

    args = arguments(tmp_path, execute=True)
    selection = registration(tmp_path)

    class ConflictRuntime(Runtime):
        async def run(self, *args, **kwargs):
            (tmp_path / "staging").mkdir()
            return await super().run(*args, **kwargs)

    assert (
        main(["generate", *args, *selection], runtime=ConflictRuntime(), date_provider=REFERENCE)
        == 2
    )
    report = json.loads(capsys.readouterr().out.splitlines()[-1])
    assert report["planner"]["status"] == "completed"
    assert report["planner"]["exit_code"] == 0
    assert report["registration"]["status"] == "failed"
    assert (tmp_path / "capture/result.json").is_file()
    assert json.loads((tmp_path / "capture/manifest.json").read_bytes())["status"] == "completed"


@pytest.mark.parametrize("timing", ["before", "during"])
def test_registration_refuses_dangling_directory_links(tmp_path, capsys, timing):
    import os

    from backend.cli.rtpeval import main

    args = arguments(tmp_path, execute=True)
    selection = registration(tmp_path)
    target = tmp_path / "link-target"
    destination = tmp_path / "staging"
    calls = []

    def create_link():
        target.mkdir()
        if os.name == "nt":
            import _winapi

            _winapi.CreateJunction(str(target), str(destination))
        else:
            destination.symlink_to(target, target_is_directory=True)
        target.rmdir()

    if timing == "before":
        create_link()

    class LinkRuntime(Runtime):
        async def run(self, *args, **kwargs):
            calls.append(True)
            if timing == "during":
                create_link()
            return await super().run(*args, **kwargs)

    assert (
        main(["generate", *args, *selection], runtime=LinkRuntime(), date_provider=REFERENCE) == 2
    )
    report = json.loads(capsys.readouterr().out.splitlines()[-1])
    assert "destination must be fresh" in report["registration"]["diagnostics"][0]
    assert not target.exists()
    if timing == "before":
        assert calls == []
        assert report["planner"]["status"] == "not_invoked"
        assert not (tmp_path / "capture").exists()
    else:
        assert calls == [True]
        assert report["planner"]["status"] == "completed"
        assert (tmp_path / "capture/result.json").is_file()


def test_registered_failure_keeps_attempt_and_never_attests_completion(tmp_path, capsys):
    import asyncio

    from backend.cli.rtpeval import main

    args = arguments(tmp_path, execute=True)
    selection = registration(tmp_path)

    class CancelledRuntime:
        async def run(self, *args, **kwargs):
            raise asyncio.CancelledError()

    assert (
        main(["generate", *args, *selection], runtime=CancelledRuntime(), date_provider=REFERENCE)
        == 1
    )
    staging = json.loads((tmp_path / "staging/staging.json").read_bytes())
    run = staging["groups"][0]["selected_runs"]["v0"]
    assert not run["completion_qualified"]
    assert "workflow_not_completed" in run["blocking_reasons"]
    assert (tmp_path / "capture/failure.json").is_file()
    assert (tmp_path / "staging/sources/capture/failure.json").is_file()
    assert not (tmp_path / "capture/result.json").exists()


def test_registration_preserves_unstarted_explicit_slots(tmp_path):
    from backend.cli.rtpeval import main

    args = arguments(tmp_path, execute=True)
    selection = registration(tmp_path)
    path = tmp_path / "selection.json"
    config = json.loads(path.read_bytes())
    config["groups"][0]["selected_runs"]["v1"] = {"run_id": "future", "capture_directory": "future"}
    path.write_text(json.dumps(config), encoding="utf-8")
    assert main(["generate", *args, *selection], runtime=Runtime(), date_provider=REFERENCE) == 0
    staging = json.loads((tmp_path / "staging/staging.json").read_bytes())
    run = staging["groups"][0]["selected_runs"]["v1"]
    assert run["run_id"] == "future" and run["capture_directory"] == "future"
    assert run["completion"]["workflow_status"] == "not_started"
    assert not run["completion_qualified"]


def test_real_runtime_factory_keeps_native_adapter_coverage(tmp_path, monkeypatch):
    from backend.cli.rtpeval import main
    from backend.evaluation.tools import planner_usage_cli

    constructed = []

    def initialize(self, *, config):
        constructed.append(config)

    monkeypatch.setattr(planner_usage_cli.RequestPlannerRuntime, "__init__", initialize)
    monkeypatch.setattr(planner_usage_cli.RequestPlannerRuntime, "run", Runtime.run)
    args = arguments(tmp_path, execute=True)
    selection = registration(tmp_path)
    assert main(["generate", *args, *selection], date_provider=REFERENCE) == 0
    usage = json.loads((tmp_path / "capture/usage.json").read_bytes())
    assert len(constructed) == 1
    assert usage["coverage"]["adapter_coverage"] == "default_adapters"


def version_result(version, request, *, retrieval="complete", repair_status=None):
    from pydantic import Field

    from backend.app.policies.generation_diagnostics import observe_generation
    from backend.app.schemas.planning import PlanningResult
    from backend.app.versions.v3.models import ValidationReport
    from backend.app.versions.v3.repair_models import RepairResult, RepairScope
    from backend.app.versions.v3.state import V3Outcome
    from backend.tests.evaluation.test_planner_usage_cli import result

    class CapturedResult(PlanningResult):
        rag_discovery: dict = Field(default_factory=dict)
        v3: V3Outcome | None = None

    base = result(version, request)
    if version == "v2":
        return CapturedResult(**base.model_dump(), rag_discovery={"status": retrieval})
    diagnostics = observe_generation(
        base.itinerary, base.requirements, reference_date=REFERENCE.today()
    )
    report = ValidationReport(diagnostics=diagnostics, findings=())
    scope = RepairScope(dates=(), target_ids=("target",), permissions=()) if repair_status else None
    repair = (
        RepairResult(
            status=repair_status,
            reason="retained_draft",
            model_attempted=True,
            original=base.itinerary,
            final=base.itinerary,
            original_report=report,
            original_supply_ids=(),
            final_place_ids=(),
        )
        if repair_status
        else None
    )
    outcome = V3Outcome(
        quantity_review_enabled=False,
        draft=base.itinerary,
        original_report=report,
        scope=scope,
        repair=repair,
        final_primary=base.itinerary,
        final_report=report,
        final_identity_ids=(),
        final_places=(),
        original_rag_discovery={"status": retrieval},
        reason="retained_draft" if repair else "no_authorized_targets",
    )
    return CapturedResult(**base.model_dump(), rag_discovery={"status": retrieval}, v3=outcome)


def test_v3_completion_requires_final_primary_linkage(tmp_path):
    from backend.cli.rtpeval import main

    args = arguments(tmp_path, version="v3", execute=True)
    selection = registration(tmp_path, version="v3")

    class MismatchedRuntime:
        async def run(self, version, request, **kwargs):
            value = version_result(version, request)
            other = value.itinerary.model_copy(update={"destination": "Wrong City"})
            value.v3 = value.v3.model_copy(update={"final_primary": other})
            return value

    assert (
        main(["generate", *args, *selection], runtime=MismatchedRuntime(), date_provider=REFERENCE)
        == 0
    )
    staging = json.loads((tmp_path / "staging/staging.json").read_bytes())
    run = staging["groups"][0]["selected_runs"]["v3"]
    assert not run["completion_qualified"]
    assert "required_mechanism_not_completed:validation" in run["blocking_reasons"]


@pytest.mark.parametrize(
    "status", ["ACCEPTED_PARTIAL", "REJECTED", "SKIPPED", "ACCEPTED_COMPLETE", None]
)
def test_normally_finalized_v3_retained_outputs_qualify_without_quality_pass(tmp_path, status):
    from backend.cli.rtpeval import main

    args = arguments(tmp_path, version="v3", execute=True)
    selection = registration(tmp_path, version="v3")

    class PartialRuntime:
        async def run(self, version, request, **kwargs):
            return version_result(version, request, retrieval="partial", repair_status=status)

    assert (
        main(["generate", *args, *selection], runtime=PartialRuntime(), date_provider=REFERENCE)
        == 0
    )
    staging = json.loads((tmp_path / "staging/staging.json").read_bytes())
    run = staging["groups"][0]["selected_runs"]["v3"]
    assert run["completion_qualified"]
    assert run["completion"]["required_mechanisms"]["validation"] == "completed"
    result = json.loads((tmp_path / "capture/result.json").read_bytes())
    assert result["v3"]["final_report"]["diagnostics"]["policy_completion"] != "complete"


@pytest.mark.parametrize(
    "version,status,qualified",
    [
        ("v2", "complete", True),
        ("v2", "empty", True),
        ("v2", "partial", True),
        ("v2", "unavailable", False),
        ("v2", "deadline_limited", False),
        ("v2", "not_started", False),
        ("v3", "unavailable", False),
    ],
)
def test_required_retrieval_workflow_controls_completion(tmp_path, version, status, qualified):
    from backend.cli.rtpeval import main

    args = arguments(tmp_path, version=version, execute=True)
    selection = registration(tmp_path, version=version)

    class RetrievalRuntime:
        async def run(self, selected, request, **kwargs):
            return version_result(selected, request, retrieval=status)

    assert (
        main(["generate", *args, *selection], runtime=RetrievalRuntime(), date_provider=REFERENCE)
        == 0
    )
    staging = json.loads((tmp_path / "staging/staging.json").read_bytes())
    run = staging["groups"][0]["selected_runs"][version]
    assert run["completion_qualified"] is qualified
    if not qualified:
        assert "required_mechanism_not_completed:retrieval" in run["blocking_reasons"]
    assert (tmp_path / "staging/sources/capture/result.json").read_bytes() == (
        tmp_path / "capture/result.json"
    ).read_bytes()


def test_new_usage_capture_failure_cannot_become_successful_generation(tmp_path):
    from backend.cli.rtpeval import main

    args = arguments(tmp_path, execute=True)
    selection = registration(tmp_path)

    class SinkFailureRuntime(Runtime):
        async def run(self, *args, **kwargs):
            (tmp_path / "capture/usage.json").mkdir()
            return await super().run(*args, **kwargs)

    assert (
        main(["generate", *args, *selection], runtime=SinkFailureRuntime(), date_provider=REFERENCE)
        == 1
    )
    report = json.loads((tmp_path / "capture/generation-registration.json").read_bytes())
    assert report["planner"]["status"] == "capture_failed"
    run = json.loads((tmp_path / "staging/staging.json").read_bytes())["groups"][0][
        "selected_runs"
    ]["v0"]
    assert not run["completion_qualified"]
    assert "missing_material:usage_ref" in run["blocking_reasons"]
    assert (tmp_path / "capture/result.json").is_file()


@pytest.mark.parametrize("fault", ["selection_drift", "input_drift"])
def test_registration_refuses_post_dispatch_source_drift_after_preserving_capture(tmp_path, fault):
    from backend.cli.rtpeval import main

    args = arguments(tmp_path, execute=True)
    selection = registration(tmp_path)
    path = tmp_path / "selection.json"

    class DriftRuntime(Runtime):
        async def run(self, *args, **kwargs):
            if fault == "selection_drift":
                path.write_text("{}", encoding="utf-8")
            else:
                (tmp_path / "input.json").write_text("{}", encoding="utf-8")
            return await super().run(*args, **kwargs)

    assert (
        main(["generate", *args, *selection], runtime=DriftRuntime(), date_provider=REFERENCE) == 2
    )
    report = json.loads((tmp_path / "capture/generation-registration.json").read_bytes())
    assert report["planner"]["status"] == "completed"
    assert report["registration"]["status"] == "failed"
    assert (tmp_path / "capture/provenance.json").is_file()
    assert not (tmp_path / "staging").exists()


@pytest.mark.parametrize("execute", [False, True])
def test_selected_capture_directory_is_one_use(tmp_path, execute):
    from backend.cli.rtpeval import main

    args = arguments(tmp_path, execute=execute)
    assert main(["generate", *args], runtime=Runtime(), date_provider=REFERENCE) == 0
    before = (tmp_path / "capture/manifest.json").read_bytes()
    with pytest.raises(FileExistsError):
        main(["generate", *args], runtime=Runtime(), date_provider=REFERENCE)
    assert (tmp_path / "capture/manifest.json").read_bytes() == before


def test_generation_preparation_never_constructs_runtime_or_loads_credentials(
    tmp_path, monkeypatch
):
    from backend.cli.rtpeval import main
    from backend.evaluation.tools import planner_usage_cli

    attempted = []

    def forbidden(*args, **kwargs):
        attempted.append(True)
        raise RuntimeError("fixture forbids credential/runtime operations")

    monkeypatch.setattr(planner_usage_cli.RequestPlannerRuntime, "__init__", forbidden)
    monkeypatch.setattr(planner_usage_cli, "load_dotenv", forbidden)
    args = arguments(tmp_path)
    assert main(["generate", *args], date_provider=REFERENCE) == 0
    assert attempted == []


def test_installed_generate_help_exposes_registration_without_online_operations(installed_cli):
    result = installed_cli("generate", "--help", tools_offline=True)
    assert result.returncode == 0
    assert "--version {v0,v1,v2,v3}" in result.stdout
    assert "--register-batch" in result.stdout
    assert "--execute" in result.stdout


def test_later_selected_invocation_preserves_prior_capture_and_cohort(tmp_path):
    from backend.cli.rtpeval import main

    args = arguments(tmp_path, execute=True)
    selection = registration(tmp_path)
    path = tmp_path / "selection.json"
    config = json.loads(path.read_bytes())
    config["groups"][0]["selected_runs"]["v1"] = {"run_id": "next", "capture_directory": "next"}
    path.write_text(json.dumps(config), encoding="utf-8")
    assert main(["generate", *args, *selection], runtime=Runtime(), date_provider=REFERENCE) == 0
    before = {p.name: p.read_bytes() for p in (tmp_path / "capture").iterdir()}
    next_args = list(args)
    next_args[next_args.index("--version") + 1] = "v1"
    next_args[next_args.index("--run-id") + 1] = "next"
    next_args[next_args.index("--output-directory") + 1] = str(tmp_path / "next")
    next_selection = list(selection)
    next_selection[-1] = str(tmp_path / "later-staging")
    assert (
        main(["generate", *next_args, *next_selection], runtime=Runtime(), date_provider=REFERENCE)
        == 0
    )
    staging = json.loads((tmp_path / "later-staging/staging.json").read_bytes())
    runs = staging["groups"][0]["selected_runs"]
    assert set(runs) == {"v0", "v1"}
    assert all(run["completion_qualified"] for run in runs.values())
    assert {p.name: p.read_bytes() for p in (tmp_path / "capture").iterdir()} == before
    from backend.cli.collection import read_staging

    assert read_staging(tmp_path / "staging/staging.json")["status"] == "blocked"
    assert read_staging(tmp_path / "later-staging/staging.json")["status"] == "incomplete"


def test_registration_keeps_already_source_bound_other_selected_runs(tmp_path):
    import hashlib

    from backend.cli.rtpeval import main

    args = arguments(tmp_path, execute=True)
    prior_args = list(args)
    prior_args[prior_args.index("--version") + 1] = "v1"
    prior_args[prior_args.index("--run-id") + 1] = "prior"
    prior_args[prior_args.index("--output-directory") + 1] = str(tmp_path / "prior")
    assert main(["generate", *prior_args], runtime=Runtime(), date_provider=REFERENCE) == 0
    selection = registration(tmp_path)
    path = tmp_path / "selection.json"
    config = json.loads(path.read_bytes())

    def ref(name, schema=None):
        artifact = tmp_path / "prior" / name
        value = {
            "path": "prior/" + name,
            "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
            "media_type": "application/json",
            "availability": "available",
        }
        if schema:
            value["schema_version"] = schema
        return value

    config["groups"][0]["selected_runs"]["v1"] = {
        "run_id": "prior",
        "result_ref": ref("result.json"),
        "usage_ref": ref("usage.json", "rtpeval_usage_1"),
        "provenance_ref": ref("provenance.json", "rtpeval_provenance_1"),
        "completion": {
            "declared_by": "fixture",
            "declared_at": "now",
            "policy_ref": "selected_workflow_1",
            "workflow_status": "completed",
            "required_mechanisms": {"generation": "completed"},
        },
    }
    path.write_text(json.dumps(config), encoding="utf-8")
    assert main(["generate", *args, *selection], runtime=Runtime(), date_provider=REFERENCE) == 0
    staging = json.loads((tmp_path / "staging/staging.json").read_bytes())
    assert set(staging["groups"][0]["selected_runs"]) == {"v0", "v1"}


def test_producer_policy_cannot_attest_an_arbitrary_batch_policy(tmp_path):
    from backend.cli.rtpeval import main

    args = arguments(tmp_path, execute=True)
    selection = registration(tmp_path)
    path = tmp_path / "selection.json"
    config = json.loads(path.read_bytes())
    config["qualification_policy_ref"] = "unrelated_quality_policy"
    path.write_text(json.dumps(config), encoding="utf-8")
    assert main(["generate", *args, *selection], runtime=Runtime(), date_provider=REFERENCE) == 0
    run = json.loads((tmp_path / "staging/staging.json").read_bytes())["groups"][0][
        "selected_runs"
    ]["v0"]
    assert not run["completion_qualified"]
    assert "completion_policy_mismatch" in run["blocking_reasons"]
