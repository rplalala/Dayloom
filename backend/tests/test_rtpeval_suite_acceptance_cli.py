"""Cross-track synthetic acceptance at installed CLI and external HTTP seams."""

import asyncio
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sysconfig
from pathlib import Path

import httpx
import pytest

from backend.cli.rtpeval import main
from backend.tests import test_rtpeval_suite_cli as suite_tests
from backend.tests import test_rtpeval_suite_external_cli as external_tests
from backend.tests import test_rtpeval_suite_pair_cli as pair_tests
from backend.tests import test_rtpeval_suite_resources_cli as resource_tests
from backend.tests.evaluation.test_cost_report import prices
from backend.tests.evaluation.test_cost_report import source as usage_source
from backend.tests.evaluation.test_evaluation_run import mock_provider

installed_cli = suite_tests.installed_cli
suite_material = suite_tests.suite_material
pair_suite = pair_tests.pair_suite
pair_case = pair_tests.pair_case
route_case = pair_tests.route_case
prepared_scenario = pair_tests.prepared_scenario
pytest_plugins = ("backend.tests.evaluation.test_intake",)


def test_integrity_stop_between_cases_replays_without_inventing_native_execution(
    suite_material, installed_cli, monkeypatch, capsys
):
    source, directory, _ = suite_material
    prepared = installed_cli(
        "suite", "prepare", source, "--directory", directory, evaluation_offline=True
    )
    assert prepared.returncode == 0, prepared.stdout + prepared.stderr
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "synthetic-google")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "synthetic-model")
    changed = source.parent / "second/options.json"
    original = changed.read_bytes()
    calls = []

    def respond(request):
        calls.append(request)
        response = mock_provider(request)
        if len(calls) == 6:
            changed.write_bytes(original + b" ")
        return response

    client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    try:
        assert (
            main(
                [
                    "suite",
                    "execute",
                    str(directory),
                    "--approved-sha256",
                    json.loads(prepared.stdout)["preparation_sha256"],
                ],
                http_client=client,
            )
            == 2
        )
    finally:
        asyncio.run(client.aclose())
    summary = json.loads(capsys.readouterr().out)
    assert [case["processing_status"] for case in summary["cases"]] == [
        "complete",
        "stopped",
        "unstarted",
    ]
    assert len(calls) == 6
    assert not (directory / "cases/0002/primary/execution").exists()
    stopped = summary["cases"][1]["tracks"]["primary"]
    assert stopped["acquisition_status"] == "not_started"
    assert stopped["report"] is None
    for case in summary["cases"]:
        assert case["tracks"]["resources"]["processing_status"] == "complete"
        assert case["tracks"]["mechanism"]["processing_status"] == "complete"
    drifted = installed_cli("suite", "replay", directory, evaluation_offline=True)
    assert drifted.returncode == 2
    assert json.loads(drifted.stdout)["processing_status"] == "needs_material_correction"
    changed.write_bytes(original)
    preserved = {path: path.read_bytes() for path in directory.rglob("*") if path.is_file()}
    replay = installed_cli("suite", "replay", directory, evaluation_offline=True)
    assert replay.returncode == 2, replay.stdout + replay.stderr
    assert json.loads(replay.stdout) == summary
    assert {path: path.read_bytes() for path in preserved} == preserved


@pytest.fixture
def multi_track_suite(suite_material, pair_suite):
    source, directory, declaration = suite_material

    def paired_without_repair(results):
        pair_tests.pair_tests.no_departure(results)
        itinerary = copy.deepcopy(results["v3"]["itinerary"])
        results["v3"]["v3"] = {
            "draft": itinerary,
            "final_primary": copy.deepcopy(itinerary),
            "original_report": {"findings": [], "improvement_targets": []},
            "scope": None,
            "repair": None,
        }

    _, _, paired, native_pair = pair_suite(source_change=paired_without_repair)
    paired["cases"][0]["case_id"] = "paired"
    declaration["cases"].append(paired["cases"][0])
    declaration["max_cost_usd"] = "40"
    root = source.parent
    usage = usage_source()["usage"]
    for name in ("group_id", "run_id", "version", "result_sha256"):
        usage.pop(name)
    usage["model_calls"][0]["total_tokens"] = 1200
    resource_tests._replace_usage(source, "v0", usage)
    partial = copy.deepcopy(usage)
    partial["collection_status"] = "partial"
    partial["model_calls"][0]["output_tokens"] = None
    partial["model_calls"][0]["total_tokens"] = None
    resource_tests._replace_usage(source, "v1", partial)
    oracle = copy.deepcopy(usage)
    oracle["namespace"] = "oracle"
    resource_tests._replace_usage(source, "v2", oracle)
    frozen = copy.deepcopy(usage)
    frozen["timing"]["scope"] = "frozen_simulation"
    resource_tests._replace_usage(source, "v3", frozen)
    (root / "generation-prices.json").write_text(json.dumps(prices()), encoding="utf-8")
    (root / "observations.json").write_text(
        json.dumps({"records": [resource_tests._observation(source)]}), encoding="utf-8"
    )
    declaration["cases"][0]["tracks"] = {
        "resources": {"prices": "generation-prices.json"},
        "mechanism": {"observations": "observations.json"},
    }
    declaration["cases"][1]["tracks"] = {"pair": {}}
    declaration["tracks"] = {
        "human": [external_tests.human(root)],
        "controlled_repair": [external_tests.controlled_missing(root)],
    }
    source.write_text(json.dumps(declaration), encoding="utf-8")
    return source, directory, declaration, native_pair


@pytest.fixture
def installed_execute(tmp_path):
    """Run the installed entry point with only the external HTTP boundary replaced."""
    executable = Path(sysconfig.get_path("scripts")) / (
        "rtpeval.exe" if os.name == "nt" else "rtpeval"
    )
    guard = tmp_path / "synthetic-provider"
    guard.mkdir()
    events = guard / "events.jsonl"
    (guard / "sitecustomize.py").write_text(
        r"""import json
import os
import socket
from pathlib import Path
import httpx
from backend.tests.evaluation.test_evaluation_run import mock_provider

events = Path(os.environ["RTPEVAL_SYNTHETIC_EVENTS"])
events.write_text("", encoding="utf-8")
def deny(*args, **kwargs):
    raise AssertionError("Synthetic suite must not use real network")
for name in ("getaddrinfo", "gethostbyname", "gethostbyname_ex", "create_connection"):
    setattr(socket, name, deny)
original_connect = socket.socket.connect
def connect(self, address):
    # Windows asyncio can use loopback sockets for its own event loop.
    if isinstance(address, tuple) and address[0] in ("127.0.0.1", "::1"):
        return original_connect(self, address)
    return deny()
socket.socket.connect = connect
socket.socket.connect_ex = deny
socket.socket.sendto = deny
models = 0
def respond(request):
    global models
    with events.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"host": request.url.host}) + "\n")
    if request.url.host == "model.example.test":
        models += 1
        if os.environ.get("RTPEVAL_SYNTHETIC_STOP") == "1" and models == 2:
            raise httpx.ConnectError("Synthetic middle-case stop", request=request)
    return mock_provider(request)
original_init = httpx.AsyncClient.__init__
def initialize(self, *args, **kwargs):
    kwargs["transport"] = httpx.MockTransport(respond)
    original_init(self, *args, **kwargs)
httpx.AsyncClient.__init__ = initialize
""",
        encoding="utf-8",
    )

    provider_guard = guard / "sitecustomize.py"
    raw_guard = provider_guard.read_text(encoding="utf-8")
    raw_guard = (
        "import os\ntry:\n"
        '    if os.environ.get("RTPEVAL_SYNTHETIC_GUARD_FAIL") == "1":\n'
        '        raise RuntimeError("Synthetic guard startup failure")\n'
        + "".join("    " + line + "\n" for line in raw_guard.splitlines())
        + "except BaseException:\n    os._exit(96)\n"
    )
    compile(raw_guard, "sitecustomize.py", "exec")
    provider_guard.write_text(raw_guard, encoding="utf-8")

    def run(directory, approved, *, stop=False, fail_startup=False):
        result = subprocess.run(
            [str(executable), "suite", "execute", str(directory), "--approved-sha256", approved],
            cwd=suite_tests.cli_tests.ROOT,
            env={
                **os.environ,
                "PYTHONPATH": str(guard),
                "PYTHONUTF8": "1",
                "GOOGLE_MAPS_API_KEY": "synthetic-google",
                "AZURE_OPENAI_API_KEY": "synthetic-model",
                "RTPEVAL_SYNTHETIC_EVENTS": str(events),
                "RTPEVAL_SYNTHETIC_STOP": "1" if stop else "0",
                "RTPEVAL_SYNTHETIC_GUARD_FAIL": "1" if fail_startup else "0",
            },
            capture_output=True,
            encoding="utf-8",
            timeout=60,
        )
        calls = (
            [json.loads(line) for line in events.read_text().splitlines()]
            if events.exists()
            else []
        )
        return result, calls

    return run


def files_under(root):
    return {path: path.read_bytes() for path in root.rglob("*") if path.is_file()}


def execute_multi_track(material, installed_cli, installed_execute, *, stop=False):
    source, directory, _, _ = material
    prepared = installed_cli(
        "suite", "prepare", source, "--directory", directory, evaluation_offline=True
    )
    assert prepared.returncode == 0, prepared.stdout + prepared.stderr
    result, calls = installed_execute(
        directory, json.loads(prepared.stdout)["preparation_sha256"], stop=stop
    )
    assert result.returncode == (2 if stop else 0), result.stdout + result.stderr
    return json.loads(result.stdout), calls


def test_installed_multi_track_workflow_refreshes_studies_without_changing_primary(
    multi_track_suite, installed_cli, installed_execute
):
    source, directory, _, _ = multi_track_suite
    original_sources = files_under(source.parent)
    summary, calls = execute_multi_track(multi_track_suite, installed_cli, installed_execute)
    assert summary["processing_status"] == "complete"
    assert [case["case_id"] for case in summary["cases"]] == ["first", "second", "third", "paired"]
    assert len(calls) == 23
    first = summary["cases"][0]["tracks"]
    assert first["resources"]["evidence_status"] == "partial"
    assert first["resources"]["cost_status"] == "partial"
    resources = json.loads((directory / first["resources"]["report"]).read_bytes())
    assert resources["groups"][0]["runs"]["v0"]["metrics"]["total_tokens"] == 1200
    assert resources["groups"][0]["runs"]["v1"]["metrics"]["total_tokens"] is None
    assert resources["groups"][0]["runs"]["v2"]["missing_fields"] == [
        "generation_usage_excluded:oracle"
    ]
    assert resources["groups"][0]["runs"]["v3"]["missing_fields"] == [
        "generation_usage_excluded:frozen_simulation"
    ]
    cost = json.loads((directory / first["resources"]["cost_report"]).read_bytes())
    assert [run["version"] for run in cost["runs"]] == ["v0", "v1"]
    assert first["mechanism"]["trace_evidence_status"] == "partial"
    pairs = [case["tracks"]["pair"] for case in summary["cases"]]
    assert [pair["processing_status"] for pair in pairs] == [
        "not_requested",
        "complete",
        "not_requested",
        "complete",
    ]
    assert [pair["evidence_status"] for pair in pairs] == [
        "unavailable",
        "unavailable",
        "unavailable",
        "available",
    ]
    paired = pairs[3]["native_report"]["groups"][0]
    assert paired["deltas"]["auxiliary_total"]["percentage_points"] == 0
    assert paired["deltas"]["auxiliary_total"]["exact_fraction"] == {
        "numerator": 0,
        "denominator": 1,
    }
    assert summary["tracks"]["human"]["studies"][0]["main_task_count"] == 1
    counts = summary["tracks"]["controlled_repair"]["studies"][0]["counts"]
    assert (
        counts["expected_cases"] == counts["expected_targets"] == counts["unavailable_cases"] == 1
    )
    primary = []
    for index, case in enumerate(summary["cases"], 1):
        path = directory / f"cases/{index:04d}/primary/execution/report.json"
        native = json.loads(path.read_bytes())
        assert case["primary_report"] == native
        assert set(native["quality"]["groups"][0]["versions"]) == {"v0", "v1", "v2", "v3"}
        primary.append(path.read_bytes())
    assert {path: path.read_bytes() for path in original_sources} == original_sources
    preserved = files_under(directory)
    attachments = source.parent / "updated-studies.json"
    attachments.write_text(
        json.dumps(
            {
                "schema_version": "rtpeval_suite_attachments_1",
                "suite_id": "synthetic",
                "tracks": {
                    "human": [external_tests.human(source.parent, revision=2)],
                    "controlled_repair": [external_tests.controlled_complete(source.parent)],
                },
            }
        ),
        encoding="utf-8",
    )
    refreshed = installed_cli(
        "suite", "report", directory, "--attachments", attachments, evaluation_offline=True
    )
    assert refreshed.returncode == 0, refreshed.stdout + refreshed.stderr
    latest = json.loads(refreshed.stdout)
    assert latest["cases"] == summary["cases"]
    assert latest["tracks"]["human"]["studies"][0]["effective_revisions"][0]["answer_revision"] == 2
    controlled = latest["tracks"]["controlled_repair"]["studies"][0]
    assert controlled["case_inventory"][0]["case_id"] == "synthetic-control"
    assert controlled["counts"]["control_cases"] == 1
    assert controlled["counts"]["unavailable_cases"] == 0
    assert {path: path.read_bytes() for path in preserved} == preserved
    assert [
        (directory / f"cases/{index:04d}/primary/execution/report.json").read_bytes()
        for index in range(1, 5)
    ] == primary
    assert (directory / "reports/0001/lineage.json").is_file()
    repeated = installed_cli("suite", "report", directory, evaluation_offline=True)
    assert repeated.returncode == 0, repeated.stdout + repeated.stderr
    assert json.loads(repeated.stdout) == latest
    assert (directory / "reports/0002/lineage.json").is_file()
    replay = installed_cli("suite", "replay", directory, evaluation_offline=True)
    assert replay.returncode == 0, replay.stdout + replay.stderr
    assert json.loads(replay.stdout) == latest
    before_invalid = files_under(directory)
    invalid = json.loads(attachments.read_bytes())
    invalid["tracks"]["human"][0]["source_context"]["rater_ref"] = "foreign-rater"
    invalid_path = source.parent / "invalid-refresh.json"
    invalid_path.write_text(json.dumps(invalid), encoding="utf-8")
    denied = installed_cli(
        "suite", "report", directory, "--attachments", invalid_path, evaluation_offline=True
    )
    assert denied.returncode == 2
    assert files_under(directory) == before_invalid
    assert {path: path.read_bytes() for path in original_sources} == original_sources


def test_stopped_multi_track_suite_keeps_independent_optional_evidence(
    multi_track_suite, installed_cli, installed_execute
):
    _, directory, _, _ = multi_track_suite
    summary, calls = execute_multi_track(
        multi_track_suite, installed_cli, installed_execute, stop=True
    )
    assert len(calls) == 9
    assert [case["processing_status"] for case in summary["cases"]] == [
        "complete",
        "stopped",
        "unstarted",
        "unstarted",
    ]
    for case in summary["cases"]:
        assert case["tracks"]["resources"]["processing_status"] == "complete"
        assert case["tracks"]["mechanism"]["processing_status"] == "complete"
    assert summary["cases"][3]["tracks"]["pair"]["evidence_status"] == "available"
    assert (
        summary["tracks"]["human"]["studies"][0]["effective_revisions"][0]["answer_revision"] == 1
    )
    assert summary["tracks"]["controlled_repair"]["studies"][0]["counts"]["unavailable_cases"] == 1
    assert not (directory / "cases/0003/primary/execution").exists()
    assert not (directory / "cases/0004/primary/execution").exists()
    report = installed_cli("suite", "report", directory, evaluation_offline=True)
    assert report.returncode == 2, report.stdout + report.stderr
    assert json.loads(report.stdout) == summary
    replay = installed_cli("suite", "replay", directory, evaluation_offline=True)
    assert replay.returncode == 2, replay.stdout + replay.stderr
    assert json.loads(replay.stdout) == summary


def test_larger_declared_synthetic_selection_keeps_explicit_order_without_execution(
    suite_material, installed_cli
):
    source, directory, declaration = suite_material
    root = source.parent
    cases = []
    for index in range(23):
        name = f"declared-{index:02d}"
        folder = root / name
        shutil.copytree(root / "first", folder)
        manifest = json.loads((folder / "manifest.json").read_bytes())
        manifest["batch_id"] = name
        for version, run in manifest["groups"][0]["selected_runs"].items():
            run["run_id"] = name + "-" + version
            for key in ("usage_ref", "provenance_ref"):
                path = folder / run[key]["path"]
                value = json.loads(path.read_bytes())
                value["run_id"] = run["run_id"]
                raw = json.dumps(value).encode()
                path.write_bytes(raw)
                run[key]["sha256"] = hashlib.sha256(raw).hexdigest()
        (folder / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        cases.append(
            {
                "case_id": name,
                "revision": "1",
                "manifest": name + "/manifest.json",
                "options": name + "/options.json",
                "prices": name + "/prices.json",
            }
        )
    declaration.update(cases=cases, max_cost_usd="230")
    source.write_text(json.dumps(declaration), encoding="utf-8")
    originals = files_under(source.parent)
    prepared = installed_cli(
        "suite", "prepare", source, "--directory", directory, evaluation_offline=True
    )
    assert prepared.returncode == 0, prepared.stdout + prepared.stderr
    result = json.loads(prepared.stdout)
    assert result["case_count"] == 23
    assert result["reserved_cost_usd"] == "230"
    inventory = json.loads((directory / "preparation.json").read_bytes())
    assert [case["case_id"] for case in inventory["cases"]] == [
        f"declared-{index:02d}" for index in range(23)
    ]
    assert [case["directory"] for case in inventory["cases"]] == [
        f"cases/{index:04d}/primary" for index in range(1, 24)
    ]
    assert len(inventory["track_configuration"]["resources"]) == 23
    assert not list(directory.rglob("started.json"))
    assert not list(directory.rglob("execution"))
    assert {path: path.read_bytes() for path in originals} == originals


@pytest.mark.parametrize(
    "changed",
    [
        "resource_report",
        "mechanism_preparation",
        "pair_report",
        "pair_snapshot_source",
        "human_mapping_source",
        "mechanism_source",
        "refresh_source",
        "refresh_lineage",
    ],
)
def test_cross_track_drift_is_rejected_by_network_denied_replay(
    multi_track_suite, installed_cli, installed_execute, changed
):
    source, directory, declaration, pair = multi_track_suite
    summary, _ = execute_multi_track(multi_track_suite, installed_cli, installed_execute)
    if changed.startswith("refresh_"):
        update = source.parent / "fresh-human.json"
        update.write_text(
            json.dumps(
                {
                    "schema_version": "rtpeval_suite_attachments_1",
                    "suite_id": "synthetic",
                    "tracks": {"human": [external_tests.human(source.parent, revision=2)]},
                }
            ),
            encoding="utf-8",
        )
        refreshed = installed_cli(
            "suite", "report", directory, "--attachments", update, evaluation_offline=True
        )
        assert refreshed.returncode == 0, refreshed.stdout + refreshed.stderr
        path = (
            directory / "reports/0001/sources/human-2-mapping.json"
            if changed == "refresh_source"
            else directory / "reports/0001/lineage.json"
        )
    else:
        first = summary["cases"][0]["tracks"]
        path = {
            "resource_report": directory / first["resources"]["report"],
            "mechanism_preparation": directory / first["mechanism"]["preparation"],
            "pair_report": directory / summary["cases"][3]["tracks"]["pair"]["report"],
            "pair_snapshot_source": next((pair[2] / "raw").glob("*")),
            "human_mapping_source": source.parent
            / declaration["tracks"]["human"][0]["mapping"]["path"],
            "mechanism_source": source.parent / "observations.json",
        }[changed]
    path.write_bytes(path.read_bytes() + b" ")
    preserved = files_under(directory)
    replay = installed_cli("suite", "replay", directory, evaluation_offline=True)
    assert replay.returncode == 2, replay.stdout + replay.stderr
    assert json.loads(replay.stdout)["processing_status"] == "needs_material_correction"
    assert files_under(directory) == preserved


@pytest.mark.parametrize(
    "adapter", ["suite_tracks.py", "suite_resources.py", "suite_pair.py", "suite_external.py"]
)
def test_registered_adapter_implementation_drift_blocks_before_provider_send_in_copy(
    suite_material, tmp_path, adapter
):
    source, directory, _ = suite_material
    isolated = tmp_path / "isolated"
    shutil.copytree(
        suite_tests.cli_tests.ROOT / "backend",
        isolated / "backend",
        ignore=shutil.ignore_patterns("__pycache__", "tests"),
    )
    guard = tmp_path / "isolated-guard"
    guard.mkdir()
    (guard / "sitecustomize.py").write_text(suite_tests.cli_tests.GUARD, encoding="utf-8")
    events = guard / "events.jsonl"
    executable = Path(sysconfig.get_path("scripts")) / (
        "rtpeval.exe" if os.name == "nt" else "rtpeval"
    )

    def run(*args):
        result = subprocess.run(
            [str(executable), *map(str, args)],
            cwd=isolated,
            env={
                **os.environ,
                "PYTHONPATH": os.pathsep.join([str(guard), str(isolated)]),
                "PYTHONUTF8": "1",
                "RTPEVAL_TEST_EVENTS": str(events),
                "RTPEVAL_TEST_EVALUATION_OFFLINE": "1",
            },
            capture_output=True,
            encoding="utf-8",
            timeout=30,
        )
        assert "OFFLINE_RTPEVAL_GUARD_ACTIVE" in result.stderr
        assert events.read_text(encoding="utf-8") == "", result.stdout + result.stderr
        return result

    prepared = run("suite", "prepare", source, "--directory", directory)
    assert prepared.returncode == 0, prepared.stdout + prepared.stderr
    copied = isolated / "backend/evaluation" / adapter
    copied.write_bytes(copied.read_bytes() + b"\n# Synthetic implementation drift\n")
    result = run(
        "suite",
        "execute",
        directory,
        "--approved-sha256",
        json.loads(prepared.stdout)["preparation_sha256"],
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert "implementation changed" in json.loads(result.stdout)["reason"].lower()
    assert not list(directory.rglob("started.json"))
    assert not list(directory.rglob("execution"))


def test_installed_synthetic_guard_failure_exits_before_native_execution(
    suite_material, installed_cli, installed_execute
):
    source, directory, _ = suite_material
    prepared = installed_cli(
        "suite", "prepare", source, "--directory", directory, evaluation_offline=True
    )
    assert prepared.returncode == 0, prepared.stdout + prepared.stderr
    preserved = files_under(directory)
    result, calls = installed_execute(
        directory, json.loads(prepared.stdout)["preparation_sha256"], fail_startup=True
    )
    assert result.returncode == 96, result.stdout + result.stderr
    assert result.stdout == ""
    assert calls == []
    assert not list(directory.rglob("started.json"))
    assert not list(directory.rglob("execution"))
    assert files_under(directory) == preserved


@pytest.mark.parametrize("interruption", [KeyboardInterrupt, asyncio.CancelledError])
def test_middle_native_interruption_closes_attempt_and_unstarted_suite_cases(
    suite_material, installed_cli, monkeypatch, capsys, interruption
):
    source, directory, _ = suite_material
    prepared = installed_cli(
        "suite", "prepare", source, "--directory", directory, evaluation_offline=True
    )
    assert prepared.returncode == 0, prepared.stdout + prepared.stderr
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "synthetic-google")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "synthetic-model")
    originals = files_under(source.parent)
    calls = []

    def respond(request):
        calls.append(request)
        if len(calls) == 9:
            raise interruption()
        return mock_provider(request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    try:
        try:
            status = main(
                [
                    "suite",
                    "execute",
                    str(directory),
                    "--approved-sha256",
                    json.loads(prepared.stdout)["preparation_sha256"],
                ],
                http_client=client,
            )
        except (KeyboardInterrupt, asyncio.CancelledError):
            pytest.fail("Interrupted native work must close receipts and suite inventory")
        assert status == 2
    finally:
        asyncio.run(client.aclose())
    summary = json.loads(capsys.readouterr().out)
    assert [case["processing_status"] for case in summary["cases"]] == [
        "complete",
        "stopped",
        "unstarted",
    ]
    assert len(calls) == 9
    middle = summary["cases"][1]["primary_report"]
    assert middle["error_type"] == interruption.__name__
    assert middle["reason"] in {"execution_interrupted", "execution_cancelled"}
    assert middle["usage"]["actual_google_sends"] == 2
    assert middle["usage"]["actual_model_sends"] == 1
    assert middle["usage"]["retries"] == 0
    attempt = directory / "cases/0002/primary/execution"
    assert (attempt / "receipt.json").is_file()
    usage = json.loads((attempt / "usage.json").read_bytes())
    assert usage["provider_events"][-1]["outcome"] == "incomplete"
    assert usage["model_calls"][0]["total_tokens"] is None
    assert not (directory / "cases/0003/primary/execution").exists()
    preserved = files_under(directory)
    for operation in ("replay", "report"):
        saved = installed_cli("suite", operation, directory, evaluation_offline=True)
        assert saved.returncode == 2, saved.stdout + saved.stderr
        assert json.loads(saved.stdout) == summary
    assert {path: path.read_bytes() for path in preserved} == preserved
    assert {path: path.read_bytes() for path in originals} == originals
    assert (
        main(
            [
                "suite",
                "execute",
                str(directory),
                "--approved-sha256",
                json.loads(prepared.stdout)["preparation_sha256"],
            ]
        )
        == 2
    )
    assert json.loads(capsys.readouterr().out)["error_type"] == "FileExistsError"


@pytest.mark.parametrize(
    "artifact,track,index",
    [
        ("tracks/0002/resources.json", "resources", 1),
        ("tracks/0002/cost.json", "resources", 1),
        ("tracks/0002/mechanism_preparation.json", "mechanism", 1),
        ("tracks/0002/mechanism.json", "mechanism", 1),
        ("tracks/0004/pair.json", "pair", 3),
        ("tracks/human/0001/human-1-report.json", "human", None),
    ],
)
def test_frozen_track_drift_closes_primary_index_and_preserves_valid_tracks(
    multi_track_suite, installed_cli, monkeypatch, capsys, artifact, track, index
):
    source, directory, _, _ = multi_track_suite
    prepared = installed_cli(
        "suite", "prepare", source, "--directory", directory, evaluation_offline=True
    )
    assert prepared.returncode == 0, prepared.stdout + prepared.stderr
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "synthetic-google")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "synthetic-model")
    pristine = files_under(directory)
    changed = directory / artifact
    calls = []

    def respond(request):
        calls.append(request)
        response = mock_provider(request)
        if len(calls) == 6:
            changed.write_bytes(b"{}")
        return response

    client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    try:
        assert (
            main(
                [
                    "suite",
                    "execute",
                    str(directory),
                    "--approved-sha256",
                    json.loads(prepared.stdout)["preparation_sha256"],
                ],
                http_client=client,
            )
            == 2
        )
    finally:
        asyncio.run(client.aclose())
    summary = json.loads(capsys.readouterr().out)
    assert [case["processing_status"] for case in summary["cases"]] == [
        "complete",
        "stopped",
        "unstarted",
        "unstarted",
    ]
    assert len(calls) == 6
    assert (directory / "summary.json").is_file()
    assert (directory / "receipt.json").is_file()
    assert (directory / "cases/0001/primary/execution/receipt.json").is_file()
    assert not (directory / "cases/0002/primary/execution").exists()
    bad = (
        summary["tracks"][track]["studies"][0]
        if index is None
        else summary["cases"][index]["tracks"][track]
    )
    assert bad["processing_status"] == "needs_material_correction"
    assert bad["reason"] == "prepared_track_artifact_changed"
    assert artifact in bad["invalid_artifacts"]
    assert bad["cost_report" if artifact.endswith("cost.json") else "report"] is None
    for case_index, case in enumerate(summary["cases"]):
        for descriptive in ("resources", "mechanism"):
            if (case_index, descriptive) != (index, track):
                assert case["tracks"][descriptive]["processing_status"] == "complete"
    assert {path: path.read_bytes() for path in pristine if path != changed} == {
        path: raw for path, raw in pristine.items() if path != changed
    }
    preserved = files_under(directory)
    for operation in ("replay", "report"):
        result = installed_cli("suite", operation, directory, evaluation_offline=True)
        assert result.returncode == 2, result.stdout + result.stderr
        assert json.loads(result.stdout)["processing_status"] == "needs_material_correction"
    assert files_under(directory) == preserved


@pytest.mark.parametrize("interruption", [KeyboardInterrupt, asyncio.CancelledError])
def test_pre_native_interruption_keeps_nonempty_stop_reason_and_no_native_receipt(
    suite_material, installed_cli, monkeypatch, capsys, interruption
):
    source, directory, _ = suite_material
    prepared = installed_cli(
        "suite", "prepare", source, "--directory", directory, evaluation_offline=True
    )
    assert prepared.returncode == 0, prepared.stdout + prepared.stderr
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "synthetic-google")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "synthetic-model")
    calls = []
    read_bytes = Path.read_bytes
    middle = directory / "cases/0002/primary/preparation.json"

    interrupted = False

    def interrupted_read(path):
        nonlocal interrupted
        if not interrupted and path == middle and len(calls) == 6:
            interrupted = True
            raise interruption()
        return read_bytes(path)

    def respond(request):
        calls.append(request)
        return mock_provider(request)

    monkeypatch.setattr(Path, "read_bytes", interrupted_read)
    client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    try:
        assert (
            main(
                [
                    "suite",
                    "execute",
                    str(directory),
                    "--approved-sha256",
                    json.loads(prepared.stdout)["preparation_sha256"],
                ],
                http_client=client,
            )
            == 2
        )
    finally:
        asyncio.run(client.aclose())
        monkeypatch.setattr(Path, "read_bytes", read_bytes)
    summary = json.loads(capsys.readouterr().out)
    assert [case["processing_status"] for case in summary["cases"]] == [
        "complete",
        "stopped",
        "unstarted",
    ]
    assert len(calls) == 6
    stopped = summary["cases"][1]
    assert stopped["primary_report"]["error_type"] == interruption.__name__
    assert stopped["primary_report"]["reason"] in {"execution_interrupted", "execution_cancelled"}
    assert stopped["tracks"]["primary"]["acquisition_status"] == "not_started"
    assert stopped["tracks"]["primary"]["report"] is None
    assert not (directory / "cases/0002/primary/execution").exists()
    for operation in ("replay", "report"):
        result = installed_cli("suite", operation, directory, evaluation_offline=True)
        assert result.returncode == 2, result.stdout + result.stderr
        assert json.loads(result.stdout) == summary
