"""One-step evaluation acceptance through public commands and synthetic HTTP."""

import asyncio
import json

import httpx
import pytest

from backend.cli.rtpeval import main
from backend.evaluation.evaluation_run_cli import main as native
from backend.evaluation.intake import load_batch
from backend.evaluation.records import canonical_digest
from backend.tests import test_rtpeval_cli as cli_tests
from backend.tests.evaluation.test_daily_density import density_reviews
from backend.tests.evaluation.test_evaluation_run import mock_provider, options, run_prices

pytest_plugins = ("backend.tests.evaluation.test_intake",)
installed_cli = cli_tests.installed_cli


@pytest.fixture
def evaluation_material(batch):
    _, _, write, _, root = batch
    manifest = write()
    configured = {**options(), "reasoning_effort": "medium"}
    (root / "options.json").write_text(json.dumps(configured), encoding="utf-8")
    (root / "prices.json").write_text(json.dumps(run_prices()), encoding="utf-8")
    directory = root / "evaluation"
    args = [
        "evaluate",
        "execute",
        str(manifest),
        "--directory",
        str(directory),
        "--options",
        str(root / "options.json"),
        "--prices",
        str(root / "prices.json"),
    ]
    return args, directory, root


def test_evaluate_help_is_discoverable_without_loading_evaluator(installed_cli):
    result = installed_cli("evaluate", "--help", block_intake=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "execute" in result.stdout
    assert "offline" in result.stdout.lower()
    assert "online" in result.stdout.lower()


@pytest.mark.parametrize("short_flags", [False, True])
def test_one_step_emits_native_report_and_replays_without_scoring_again(
    evaluation_material,
    monkeypatch,
    capsys,
    short_flags,
):
    args, directory, root = evaluation_material
    if short_flags:
        aliases = {"--directory": "-o", "--options": "-c", "--prices": "-p"}
        args = [aliases.get(arg, arg) for arg in args]
    originals = {path: path.read_bytes() for path in root.glob("*.json")}
    calls = []

    def respond(request):
        calls.append(request)
        if request.url.host == "model.example.test":
            assert json.loads(request.content)["reasoning"] == {"effort": "medium"}
        return mock_provider(request)

    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "synthetic-google")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "synthetic-model")
    client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    try:
        assert main(args, http_client=client) == 0
    finally:
        asyncio.run(client.aclose())
    report = json.loads(capsys.readouterr().out)
    assert report["processing_status"] == report["acquisition_status"] == "complete"
    assert report["unknowns"]  # Successful processing is not an all-PASS quality gate.
    assert report["evidence_status"] == "unresolved"
    assert not report["quality"]["groups"][0]["all_totals_available"]
    assert '"FAIL"' in json.dumps(report["quality"])
    assert len(report["quality"]["groups"][0]["versions"]) == 4
    assert report["usage"]["actual_google_sends"] == 5
    assert report["usage"]["actual_model_sends"] == 1
    assert report["usage"]["retries"] == 0
    assert len(calls) == 6  # Complete API schedules need no access-assessment call.
    assert json.loads((directory / "execution/report.json").read_bytes()) == report
    preparation = json.loads((directory / "preparation.json").read_bytes())
    receipt = json.loads((directory / "execution/receipt.json").read_bytes())
    assert (
        report["preparation_sha256"]
        == receipt["preparation_sha256"]
        == preparation["content_sha256"]
    )
    assert native(["replay", str(directory)]) == 0
    assert json.loads(capsys.readouterr().out) == report
    assert main(["evaluate", "replay", str(directory)]) == 0
    assert json.loads(capsys.readouterr().out) == report
    assert {path: path.read_bytes() for path in originals} == originals

    recorded = {path: path.read_bytes() for path in directory.rglob("*") if path.is_file()}
    assert main(args) == 2  # Fresh one-step packages never reuse an existing directory.
    capsys.readouterr()
    legacy = ["execute", str(directory), "--approved-sha256", preparation["content_sha256"]]
    assert main(["evaluate", *legacy]) == 2
    refusal = capsys.readouterr().out
    assert native(legacy) == 2
    assert capsys.readouterr().out == refusal
    assert {path: path.read_bytes() for path in recorded} == recorded
    assert len(calls) == 6
    del preparation["content_sha256"]
    assert canonical_digest(preparation) == receipt["preparation_sha256"]


@pytest.mark.parametrize("command", ["prepare", "execute", "replay"])
def test_leaf_help_stays_offline(installed_cli, command):
    result = installed_cli("evaluate", command, "--help", evaluation_offline=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert f"rtpeval evaluate {command}" in result.stdout


@pytest.mark.parametrize(
    "arguments,diagnostic",
    [
        ([], "required"),
        (["source"], "required"),
        (["source", "--directory", "fresh"], "requires --options and --prices"),
        (["source", "--directory", "fresh", "--approved-sha256", "digest"], "not allowed"),
        (
            ["source", "--approved-sha256", "digest", "--options", "options.json"],
            "cannot be combined",
        ),
        (
            ["source", "--directory", "", "--options", "options", "--prices", "prices"],
            "must not be empty",
        ),
    ],
)
def test_execution_modes_are_explicit_before_evaluator_import(installed_cli, arguments, diagnostic):
    result = installed_cli("evaluate", "execute", *arguments, block_intake=True)
    assert result.returncode == 2
    assert diagnostic in result.stderr
    assert result.stdout == ""


def test_installed_preparation_is_offline_and_matches_native(evaluation_material, installed_cli):
    args, directory, root = evaluation_material
    prepared = installed_cli("evaluate", "prepare", *args[2:], evaluation_offline=True)
    assert prepared.returncode == 0, prepared.stdout + prepared.stderr
    summary = json.loads(prepared.stdout)
    preparation_bytes = (directory / "preparation.json").read_bytes()
    preparation = json.loads(preparation_bytes)
    assert summary["preparation_sha256"] == preparation["content_sha256"]
    assert not (directory / "execution").exists()
    legacy = installed_cli(
        "prepare",
        *args[2:4],
        str(root / "legacy"),
        *args[5:],
        legacy=True,
        legacy_module="backend.evaluation.evaluation_run_cli",
        evaluation_offline=True,
    )
    assert legacy.returncode == 0, legacy.stdout + legacy.stderr
    native_preparation = json.loads((root / "legacy/preparation.json").read_bytes())
    # Directory, timestamp and their digests intentionally differ. Shared bindings
    # must remain exactly native, without rewriting hashes in either artifact.
    for key in ("intake", "options", "prices", "implementation_hashes", "identity_plan", "context"):
        assert preparation[key] == native_preparation[key]
    assert (directory / "preparation.json").read_bytes() == preparation_bytes


@pytest.mark.parametrize(
    "fault",
    [
        "manifest",
        "options",
        "prices",
        "context",
        "occupancy-reviews",
        "route-reviews",
        "density-reviews",
        "version",
    ],
)
def test_local_preflight_rejects_before_credentials_or_dispatch(
    evaluation_material,
    installed_cli,
    batch,
    fault,
):
    args, directory, root = evaluation_material
    if fault in {"manifest", "options", "prices"}:
        filename = {
            "manifest": "manifest.json",
            "options": "options.json",
            "prices": "prices.json",
        }[fault]
        (root / filename).write_text("{", encoding="utf-8")
    elif fault in {"context", "occupancy-reviews", "route-reviews", "density-reviews"}:
        args.extend(["--" + fault, str(root / "missing-review.json")])
    elif fault == "version":
        manifest, _, write, _, _ = batch
        del manifest["groups"][0]["selected_runs"]["v2"]
        write()
    result = installed_cli(*args, evaluation_offline=True)
    assert result.returncode == 2, result.stdout + result.stderr
    assert json.loads(result.stdout)["processing_status"] == "needs_material_correction"
    assert not directory.exists()


def test_missing_tokenizer_is_an_offline_local_refusal(evaluation_material, installed_cli):
    args, directory, _ = evaluation_material
    result = installed_cli(*args, evaluation_offline=True, missing_tokenizer=True)
    assert result.returncode == 2
    assert "Offline tokenizer unavailable" in json.loads(result.stdout)["reason"]
    assert not directory.exists()


@pytest.mark.parametrize(
    "operation", ["httpx.AsyncClient()", "RuntimeSettings()", "dotenv.load_dotenv()"]
)
def test_evaluation_offline_guard_detects_runtime_construction(installed_cli, operation):
    probe = (
        "import httpx, dotenv\nfrom backend.app.runtime import RuntimeSettings\ntry:\n    "
        + operation
        + "\nexcept RuntimeError:\n    pass\n"
    )
    with pytest.raises(AssertionError, match='"kind": "runtime_init"'):
        installed_cli(probe, probe=True, evaluation_offline=True)


@pytest.mark.parametrize("mode", ["one_step", "legacy"])
@pytest.mark.parametrize(
    "failure", ["none", "google_http", "model_connection", "cost_limit", "deadline"]
)
def test_public_execution_preserves_native_outcomes_and_one_use(
    evaluation_material,
    installed_cli,
    monkeypatch,
    capsys,
    mode,
    failure,
):
    args, directory, root = evaluation_material
    configured = json.loads((root / "options.json").read_bytes())
    if failure == "cost_limit":
        configured["max_cost_usd"] = "0.0001"
    if failure == "deadline":
        configured["total_timeout_seconds"] = 0.02
    (root / "options.json").write_text(json.dumps(configured), encoding="utf-8")
    # Actual reviewed context reaches native preparation and scoring unchanged.
    reviewed = density_reviews(load_batch(args[2]))
    (root / "density.json").write_text(json.dumps(reviewed), encoding="utf-8")
    args.extend(["--density-reviews", str(root / "density.json")])
    if mode == "legacy":
        assert main(["evaluate", "prepare", *args[2:]]) == 0
        digest = json.loads(capsys.readouterr().out)["preparation_sha256"]
        command = ["evaluate", "execute", str(directory), "--approved-sha256", digest]
    else:
        command = args
    calls = []

    async def respond(request):
        calls.append(request)
        if failure == "deadline":
            await asyncio.sleep(0.2)
        if failure == "google_http" and request.url.host == "places.googleapis.com":
            return httpx.Response(500, json={"error": "synthetic"})
        if failure == "model_connection" and request.url.host == "model.example.test":
            raise httpx.ConnectError("Synthetic provider failure", request=request)
        return mock_provider(request)

    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "synthetic-google")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "synthetic-model")
    client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    expected = 0 if failure in {"none", "google_http"} else 2
    try:
        assert main(command, http_client=client) == expected
    finally:
        asyncio.run(client.aclose())
    report = json.loads(capsys.readouterr().out)
    assert report["processing_status"] == ("complete" if expected == 0 else "stopped")
    assert report["acquisition_status"] == ("complete" if failure == "none" else "partial")
    assert report["usage"]["retries"] == 0
    assert (
        len(calls)
        == {"none": 6, "google_http": 3, "model_connection": 3, "cost_limit": 0, "deadline": 1}[
            failure
        ]
    )
    saved = {path: path.read_bytes() for path in directory.rglob("*") if path.is_file()}
    preparation = json.loads((directory / "preparation.json").read_bytes())
    assert preparation["context"]["density_reviews"] == reviewed
    assert json.loads((directory / "execution/report.json").read_bytes()) == report
    assert report["preparation_sha256"] == preparation.pop("content_sha256")
    assert canonical_digest(preparation) == report["preparation_sha256"]
    replay = installed_cli("evaluate", "replay", directory, evaluation_offline=True)
    old_replay = installed_cli(
        "replay",
        directory,
        legacy=True,
        legacy_module="backend.evaluation.evaluation_run_cli",
        evaluation_offline=True,
    )
    assert replay.returncode == old_replay.returncode == expected
    assert json.loads(replay.stdout) == json.loads(old_replay.stdout) == report
    second = [
        "evaluate",
        "execute",
        str(directory),
        "--approved-sha256",
        report["preparation_sha256"],
    ]
    assert main(second) == 2
    assert json.loads(capsys.readouterr().out)["error_type"] == "FileExistsError"
    assert {path: path.read_bytes() for path in saved} == saved


@pytest.mark.parametrize("fault", ["source", "preparation", "digest"])
def test_legacy_integrity_refusal_preserves_unconsumed_package(
    evaluation_material,
    monkeypatch,
    capsys,
    fault,
):
    args, directory, root = evaluation_material
    assert main(["evaluate", "prepare", *args[2:]]) == 0
    digest = json.loads(capsys.readouterr().out)["preparation_sha256"]
    if fault == "source":
        (root / "v0.json").write_text("{}", encoding="utf-8")
    elif fault == "preparation":
        path = directory / "preparation.json"
        changed = json.loads(path.read_bytes())
        changed["max_retries"] = 2
        path.write_text(json.dumps(changed), encoding="utf-8")
    else:
        digest = "0" * 64
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "synthetic-google")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "synthetic-model")
    calls = []
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda request: calls.append(request)))
    command = ["execute", str(directory), "--approved-sha256", digest]
    saved = (directory / "preparation.json").read_bytes()
    try:
        assert main(["evaluate", *command], http_client=client) == 2
        refusal = capsys.readouterr().out
        assert native(command, http_client=client) == 2
        assert capsys.readouterr().out == refusal
    finally:
        asyncio.run(client.aclose())
    assert not calls and not (directory / "execution").exists()
    assert (directory / "preparation.json").read_bytes() == saved


def test_explicit_env_file_is_loaded_only_after_preparation(
    evaluation_material,
    monkeypatch,
    capsys,
):
    import dotenv

    args, directory, _ = evaluation_material
    loads = []

    def load(path, *, override):
        assert (directory / "preparation.json").is_file()
        assert not (directory / "execution").exists()
        assert not override
        loads.append(path)
        monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "synthetic-google")
        monkeypatch.setenv("AZURE_OPENAI_API_KEY", "synthetic-model")

    monkeypatch.setattr(dotenv, "load_dotenv", load)
    client = httpx.AsyncClient(transport=httpx.MockTransport(mock_provider))
    try:
        assert main([*args, "--env-file", "synthetic.env"], http_client=client) == 0
    finally:
        asyncio.run(client.aclose())
    assert loads == ["synthetic.env"]
    assert json.loads(capsys.readouterr().out)["processing_status"] == "complete"


def test_missing_credentials_preserves_preparation_without_starting_attempt(
    evaluation_material,
    monkeypatch,
    capsys,
):
    args, directory, _ = evaluation_material
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)

    def no_client(*args, **kwargs):
        pytest.fail("Missing credentials must fail before HTTP client construction")

    monkeypatch.setattr(httpx, "AsyncClient", no_client)
    assert main(args) == 2
    assert json.loads(capsys.readouterr().out)["processing_status"] == "needs_material_correction"
    assert (directory / "preparation.json").is_file()
    assert not (directory / "execution").exists()


@pytest.mark.parametrize("tamper", ["during_dispatch", "after_complete"])
def test_source_changes_preserve_receipts_and_refuse_replay(
    evaluation_material,
    installed_cli,
    monkeypatch,
    capsys,
    tamper,
):
    args, directory, root = evaluation_material
    calls = []

    def respond(request):
        calls.append(request)
        if tamper == "during_dispatch":
            (root / "v0.json").write_text("{}", encoding="utf-8")
        return mock_provider(request)

    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "synthetic-google")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "synthetic-model")
    client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    try:
        assert main(args, http_client=client) == (2 if tamper == "during_dispatch" else 0)
    finally:
        asyncio.run(client.aclose())
    report = json.loads(capsys.readouterr().out)
    if tamper == "during_dispatch":
        assert report["processing_status"] == "stopped"
    else:
        (root / "v0.json").write_text("{}", encoding="utf-8")
    assert report["usage"]["retries"] == 0
    assert (directory / "execution/receipt.json").is_file()
    recorded = {path: path.read_bytes() for path in directory.rglob("*") if path.is_file()}
    replay = installed_cli("evaluate", "replay", directory, evaluation_offline=True)
    assert replay.returncode == 2
    assert "sources changed" in json.loads(replay.stdout)["reason"]
    assert {path: path.read_bytes() for path in recorded} == recorded


def test_tampered_receipt_artifact_is_refused_offline(
    evaluation_material,
    installed_cli,
    monkeypatch,
    capsys,
):
    args, directory, _ = evaluation_material
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "synthetic-google")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "synthetic-model")
    client = httpx.AsyncClient(transport=httpx.MockTransport(mock_provider))
    try:
        assert main(args, http_client=client) == 0
    finally:
        asyncio.run(client.aclose())
    capsys.readouterr()
    (directory / "execution/report.json").write_text("{}", encoding="utf-8")
    replay = installed_cli("evaluate", "replay", directory, evaluation_offline=True)
    assert replay.returncode == 2
    assert json.loads(replay.stdout)["processing_status"] == "needs_material_correction"
