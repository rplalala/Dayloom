"""Task-oriented installed reports preserve the native offline behavior."""

import json

import httpx
import pytest

from backend.cli.rtpeval import main as public_main
from backend.tests.evaluation import test_quality_report_cli as quality_tests
from backend.tests.evaluation import test_route_cli as route_commands
from backend.tests.evaluation import test_routes as route_tests
from backend.tests.evaluation import test_v3_pair_report as pair_tests
from backend.tests.evaluation.test_controlled_replay import case
from backend.tests.evaluation.test_cost_report import prices, source
from backend.tests.evaluation.test_human_tasks import config
from backend.tests.evaluation.test_opening_judgment import material as opening_material
from backend.tests.evaluation.test_opening_run_cli import prepare_base
from backend.tests.test_rtpeval_cli import installed_cli as cli_fixture

installed_cli = cli_fixture


def test_usage_keeps_native_missing_metrics_and_exit_status(installed_cli, tmp_path):
    paths = []
    for version in ("v0", "v1", "v2", "v3"):
        path = tmp_path / (version + "-usage.json")
        path.write_text(json.dumps(source(version=version)["usage"]), encoding="utf-8")
        paths.append(path)
    current = installed_cli("usage", *paths)
    legacy = installed_cli(*paths, legacy=True, legacy_module="backend.evaluation.usage_report")
    assert current.returncode == legacy.returncode == 0
    assert current.stdout == legacy.stdout
    assert json.loads(current.stdout)["quality_score_contribution"] is None


pytest_plugins = (
    "backend.tests.evaluation.test_intake",
    "backend.tests.evaluation.test_identity_adoption",
)
prepared_scenario = route_tests.prepared_scenario
route_case = route_tests.route_case


def test_quality_keeps_factual_unknowns_and_exact_provenance(installed_cli, route_case):
    args = quality_tests.arguments(route_case())
    current = installed_cli("quality", *args)
    legacy = installed_cli(
        *args, legacy=True, legacy_module="backend.evaluation.quality_report_cli"
    )
    assert current.returncode == legacy.returncode == 0
    assert current.stdout == legacy.stdout
    assert json.loads(current.stdout)["status"] == "complete"


def test_cost_keeps_repeatable_sources_and_output_artifact(installed_cli, tmp_path):
    usage = tmp_path / "usage.json"
    catalog = tmp_path / "prices.json"
    usage.write_text(json.dumps(source()["usage"]), encoding="utf-8")
    catalog.write_text(json.dumps(prices()), encoding="utf-8")
    output = tmp_path / "cost.json"
    args = ["--usage", usage, "--prices", catalog, "--output", output]
    current = installed_cli("cost", *args)
    original = output.read_bytes() if output.exists() else b""
    legacy = installed_cli(*args, legacy=True, legacy_module="backend.evaluation.cost_report")
    assert current.returncode == legacy.returncode == 0
    assert original == output.read_bytes()
    assert current.stdout == legacy.stdout


pair_case = pair_tests.pair_case


def test_pair_keeps_frozen_draft_final_report(installed_cli, pair_case):
    args = [
        "report",
        *route_commands.arguments(pair_case())[1:],
        "--generated-at",
        "2026-10-04T00:00:00Z",
    ]
    current = installed_cli("pair", *args)
    legacy = installed_cli(*args, legacy=True, legacy_module="backend.evaluation.v3_pair_cli")
    assert current.returncode == legacy.returncode == 0
    assert current.stdout == legacy.stdout
    assert json.loads(current.stdout)["status"] == "complete"


def test_controlled_replay_executes_frozen_v3_not_saved_evidence(installed_cli, tmp_path):
    path = tmp_path / "case.json"
    path.write_text(json.dumps(case()), encoding="utf-8")
    current = installed_cli("controlled", "replay", path, tools_offline=True)
    legacy = installed_cli(
        "replay",
        path,
        legacy=True,
        tools_offline=True,
        legacy_module="backend.evaluation.controlled_cli",
    )
    assert current.returncode == legacy.returncode == 0
    assert current.stdout == legacy.stdout
    assert json.loads(current.stdout)["schema_version"] == "rtpeval_controlled_replay_1"


def test_review_prepares_blinded_material_without_participant_submission(installed_cli, batch):
    _, _, write, _, root = batch
    cfg = root / "review-config.json"
    cfg.write_text(json.dumps(config()), encoding="utf-8")
    args = ["prepare", write(), cfg]
    current = installed_cli("review", *args)
    legacy = installed_cli(*args, legacy=True, legacy_module="backend.evaluation.human_cli")
    assert current.returncode == legacy.returncode == 0
    assert current.stdout == legacy.stdout
    assert json.loads(current.stdout)["schema_version"] == "rtpeval_human_preparation_1"


def test_mechanism_preserves_missing_observations_and_saved_destinations(installed_cli, batch):
    _, _, write, _, root = batch
    prepared = root / "mechanism.json"
    args = ["prepare", "--manifest", write(), "--output", prepared]
    current = installed_cli("mechanism", *args)
    material = prepared.read_bytes() if prepared.exists() else b""
    legacy = installed_cli(*args, legacy=True, legacy_module="backend.evaluation.mechanism_cli")
    assert current.returncode == legacy.returncode == 0
    assert material == prepared.read_bytes()
    report = installed_cli("mechanism", "report", prepared)
    original = installed_cli(
        "report", prepared, legacy=True, legacy_module="backend.evaluation.mechanism_cli"
    )
    assert report.stdout == original.stdout


@pytest.mark.parametrize(
    "command, phrases",
    [
        (
            (),
            (
                "quality",
                "usage",
                "cost",
                "pair",
                "controlled",
                "review",
                "mechanism",
                "advanced",
                "dev",
            ),
        ),
        (
            ("advanced",),
            (
                "identity",
                "snapshot",
                "schedule",
                "opening",
                "routes",
                "opening-judgment",
                "opening-run",
                "offline",
                "online",
            ),
        ),
        (
            ("dev",),
            (
                "identity-smoke",
                "route-requests",
                "planner-usage",
                "preference-smoke",
                "short-reference-packet",
                "development",
                "online",
            ),
        ),
        (("pair",), ("prepare", "report", "offline")),
        (("controlled",), ("replay", "frozen", "offline")),
        (("review",), ("prepare", "package", "import", "report", "offline")),
        (("mechanism",), ("prepare", "report", "offline")),
    ],
)
def test_task_help_is_discoverable_without_loading_evaluators(installed_cli, command, phrases):
    result = installed_cli(*command, "--help", block_intake=True)
    assert result.returncode == 0, result.stderr
    for phrase in phrases:
        assert phrase in result.stdout.lower()


@pytest.mark.parametrize(
    "path, option, mode",
    [
        (("quality",), "--opening-judgment", False),
        (("usage",), "usage_files", False),
        (("cost",), "--snapshot", False),
        (("pair", "report"), "--edit-provenance", False),
        (("controlled", "identity"), "--historical-program", True),
        (("review", "package"), "--private-out", False),
        (("advanced", "identity"), "--legacy", False),
        (("advanced", "identity-adoption"), "--historical-llm", False),
        (("advanced", "snapshot", "identity-evidence"), "--historical", False),
        (("advanced", "schedule"), "--occupancy-reviews", False),
        (("advanced", "opening"), "--opening-judgment", False),
        (("advanced", "routes", "score"), "--expected-plan", False),
        (("advanced", "opening-judgment", "import"), "--material", False),
        (("advanced", "opening-run", "prepare"), "--options", True),
        (("advanced", "opening-run", "execute"), "--approved-sha256", True),
        (("advanced", "opening-run", "replay"), "directory", True),
        (("dev", "route-requests"), "--prepared-at", False),
        (("dev", "identity-smoke", "execute"), "--approved-manifest-sha256", True),
        (("dev", "planner-usage"), "--capture-evidence", True),
        (("dev", "preference-smoke"), "--execute-live", True),
        (("dev", "short-reference-packet"), "--source-authorization", True),
        (("dev", "requirement-acceptance"), "--cases", True),
        (("dev", "poi-acceptance"), "--execute", True),
        (("dev", "repair-replay"), "--snapshot", True),
    ],
)
def test_leaf_help_retains_native_parameters_and_network_description(
    installed_cli, path, option, mode
):
    result = installed_cli(*path, "--help", tools_offline=mode)
    assert result.returncode == 0, result.stderr
    assert option in result.stdout
    assert "rtpeval " + " ".join(path) in result.stdout
    assert any(
        word in result.stdout.lower() for word in ("offline", "online", "no provider requests")
    )


@pytest.mark.parametrize(
    "task,module",
    [
        ("schedule", "backend.evaluation.requirement_schedule_cli"),
        ("opening", "backend.evaluation.opening_cli"),
        ("routes", "backend.evaluation.route_cli"),
    ],
)
def test_advanced_reports_preserve_native_evidence_statuses(
    installed_cli, route_case, task, module
):
    args = route_commands.arguments(route_case())
    if task == "schedule":
        args = args[1:3] + ["--context", args[args.index("--context") + 1]]
    elif task == "opening":
        args = args[1:4] + ["--context", args[args.index("--context") + 1]]
    current = installed_cli("advanced", task, *args)
    legacy = installed_cli(*args, legacy=True, legacy_module=module)
    assert current.returncode == legacy.returncode == 0
    assert current.stdout == legacy.stdout
    assert json.loads(current.stdout)["status"] == "complete"


@pytest.mark.parametrize(
    "path,args,module",
    [
        (
            ("quality",),
            ("missing.json", "identity.json", "snapshot", "--generated-at", "2026-10-04T00:00:00Z"),
            "backend.evaluation.quality_report_cli",
        ),
        (
            ("advanced", "identity"),
            (
                "missing.json",
                "evidence.json",
                "audit.json",
                "--legacy",
                "--reviews",
                "reviews.json",
            ),
            "backend.evaluation.identity_cli",
        ),
        (("advanced", "snapshot"), ("replay", "missing"), "backend.evaluation.snapshot_cli"),
        (
            ("advanced", "identity-adoption"),
            ("missing.json", "--historical-program"),
            "backend.evaluation.identity_adoption_cli",
        ),
    ],
)
def test_native_material_correction_exits_and_historical_switches_survive(
    installed_cli, path, args, module
):
    current = installed_cli(*path, *args)
    legacy = installed_cli(*args, legacy=True, legacy_module=module)
    assert current.returncode == legacy.returncode == 2
    assert current.stdout == legacy.stdout


@pytest.mark.parametrize(
    "operation,kind",
    [
        ("socket.getaddrinfo('example.test', 443)", "network"),
        ("socket.socket().connect(('203.0.113.1', 443))", "network"),
        ("os.environ.get('AZURE_OPENAI_API_KEY')", "credential_read"),
        ("__import__('httpx').AsyncClient()", "runtime_init"),
        ("__import__('openai').AsyncOpenAI(api_key='fixture')", "runtime_init"),
    ],
)
def test_tools_guard_records_caught_external_attempts(installed_cli, operation, kind):
    probe = "import os, socket\ntry:\n    " + operation + "\nexcept RuntimeError:\n    pass\n"
    with pytest.raises(AssertionError, match='"kind": "' + kind + '"'):
        installed_cli(probe, probe=True, tools_offline=True)


@pytest.mark.parametrize("evaluation_entry", [False, True])
def test_explicit_incremental_opening_execute_and_offline_replay_use_native_receipts(
    batch,
    capsys,
    monkeypatch,
    installed_cli,
    evaluation_entry,
):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "synthetic-google")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "synthetic-model")
    root, parent, directory, approved = prepare_base(batch, capsys)
    if evaluation_entry:
        directory = root / "public-opening"
        prepared = installed_cli(
            "evaluate",
            "prepare-opening",
            parent,
            "-o",
            directory,
            "-c",
            root / "options.json",
            "-p",
            root / "prices.json",
            tools_offline=True,
        )
        assert prepared.returncode == 0, prepared.stderr
        preparation = json.loads(prepared.stdout)
        assert preparation["eligible_count"] == 8
        approved = preparation["preparation_sha256"]
    execute_command = (
        ["evaluate", "execute-opening"]
        if evaluation_entry
        else ["advanced", "opening-run", "execute"]
    )
    replay_command = (
        ["evaluate", "replay-opening"]
        if evaluation_entry
        else ["advanced", "opening-run", "replay"]
    )
    digest_flag = "-a" if evaluation_entry else "--approved-sha256"
    calls = []

    def respond(request):
        calls.append(request)
        packet = json.loads((directory / "preparation.json").read_bytes())["packet"]
        return httpx.Response(200, json=opening_material(packet, "UNKNOWN")["response"])

    client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    assert (
        public_main(
            [*execute_command, str(directory), digest_flag, approved],
            http_client=client,
        )
        == 0
    )
    emitted = capsys.readouterr().out
    assert len(calls) == 1
    report = json.loads(emitted)
    assert report["usage"]["actual_model_sends"] == 1
    assert report["usage"]["retries"] == 0
    assert (
        sum(row["opening"]["counts"]["UNKNOWN"] for row in report["reports"]["opening"]["results"])
        == 8
    )
    current = installed_cli(*replay_command, directory, tools_offline=True)
    legacy = installed_cli(
        "replay-opening",
        directory,
        legacy=True,
        tools_offline=True,
        legacy_module="backend.evaluation.evaluation_run_cli",
    )
    assert current.returncode == legacy.returncode == 0
    assert current.stdout == legacy.stdout
    assert json.loads(current.stdout) == report
    assert (
        public_main(
            [*execute_command, str(directory), digest_flag, approved],
            http_client=client,
        )
        == 2
    )
    capsys.readouterr()
    assert len(calls) == 1


def test_review_import_and_report_keep_supplied_answer_revisions(installed_cli, batch):
    from backend.tests.evaluation.test_human_answers import answer, bundle
    from backend.tests.evaluation.test_human_tasks import package

    _, _, _, _, root = batch
    prepared = package(batch)
    values = {
        "public": prepared["public"],
        "mapping": prepared["private"],
        "answers": bundle(answer(prepared["public"])),
    }
    paths = []
    for name, value in values.items():
        path = root / (name + ".json")
        path.write_text(json.dumps(value), encoding="utf-8")
        paths.append(path)
    for operation in ("import", "report"):
        args = [operation, *paths]
        if operation == "report":
            args += ["--generated-at", "2026-10-04T00:00:00Z"]
        current = installed_cli("review", *args)
        legacy = installed_cli(*args, legacy=True, legacy_module="backend.evaluation.human_cli")
        assert current.returncode == legacy.returncode == 0
        assert current.stdout == legacy.stdout
    imported = installed_cli("review", "import", *paths)
    assert json.loads(imported.stdout)["effective"][0]["answer_revision"] == 1


def test_development_route_inventory_keeps_unknown_readiness_and_exit_three(
    installed_cli, adoption_case
):
    args = [adoption_case[2], "--legacy", "--prepared-at", "2026-10-06T10:00:00Z"]
    current = installed_cli("dev", "route-requests", *args)
    legacy = installed_cli(
        *args, legacy=True, legacy_module="backend.evaluation.tools.route_requests_cli"
    )
    assert current.returncode == legacy.returncode == 3
    assert current.stdout == legacy.stdout
    report = json.loads(current.stdout)
    assert report["counts"]["actual_sends"] == 0
    assert report["legs"][0]["verdict"] == "UNKNOWN"
