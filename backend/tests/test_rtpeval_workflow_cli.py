"""Public CLI workflow acceptance with preserved synthetic material."""

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path

import httpx

from backend.cli.rtpeval import main
from backend.tests import test_rtpeval_cli as cli_tests
from backend.tests import test_rtpeval_collect_cli as collect_tests
from backend.tests import test_rtpeval_finalize_cli as finalize_tests
from backend.tests import test_rtpeval_generate_cli as generate_tests
from backend.tests.evaluation.test_evaluation_run import mock_provider, options, run_prices

pytest_plugins = ("backend.tests.evaluation.test_intake",)
installed_cli = cli_tests.installed_cli
collection = collect_tests.collection
handoff = finalize_tests.handoff
ROOT = Path(__file__).resolve().parents[2]


def test_documented_primary_workflows_use_accepted_cli_arguments(installed_cli):
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    primary = readme.split("## Command line", 1)[1].split("## Current application", 1)[0]
    guide = (ROOT / "backend/evaluation/README.md").read_text(encoding="utf-8")
    material = guide.split("## Installed batch validation", 1)[1].split(
        "## Contract and module navigation", 1
    )[0]
    commands = re.findall(r"^uv run rtpeval (.+)$", primary + material, flags=re.MULTILINE)
    commands.extend(re.findall(r"^uv run rtpeval (pair acquire .+)$", guide, flags=re.MULTILINE))
    for required in (
        "generate ",
        "batch collect ",
        "batch attach-requirements ",
        "batch finalize ",
        "evaluate execute ",
        "evaluate replay ",
        "suite prepare ",
        "suite execute ",
        "suite report ",
        "suite replay ",
        "research validate ",
        "research report ",
        "research corpus prepare ",
        "research corpus measure ",
        "research corpus export ",
        "pair acquire prepare ",
        "pair acquire execute ",
        "pair acquire replay ",
        "pair acquire export ",
    ):
        assert any(command.startswith(required) for command in commands), required
    help_outputs = {}
    for command in commands:
        words = command.split()
        # Read the leaf's help without executing placeholder sources. Generate's
        # registration options are documented by its wrapper before native help.
        if words[:2] in (["research", "corpus"], ["pair", "acquire"]):
            leaf = words[:3] if len(words) > 2 and not words[2].startswith("--") else words[:2]
        elif (
            words[0] in {"batch", "evaluate", "suite", "research"}
            and len(words) > 1
            and not words[1].startswith("--")
        ):
            leaf = words[:2]
        else:
            leaf = words[:1] if not words[0].startswith("--") else []
        key = tuple(leaf)
        if key not in help_outputs:
            result = installed_cli(*leaf, "--help", tools_offline=True)
            assert result.returncode == 0, command + result.stdout + result.stderr
            help_outputs[key] = result.stdout
        for flag in (word for word in words if word.startswith("--")):
            assert flag in help_outputs[key], command + ": " + flag


def test_existing_collection_reaches_native_report_and_exact_offline_replay(
    installed_cli, handoff, monkeypatch, capsys
):
    _, write, save, root = handoff
    source, handoff_path = save(), write()
    originals = {path: path.read_bytes() for path in root.glob("*.json")}
    staging, attached, finalized = (root / name for name in ("staging", "attached", "finalized"))
    collected = installed_cli("batch", "collect", source, "--directory", staging)
    assert collected.returncode == 0, collected.stdout + collected.stderr
    pending = json.loads(collected.stdout)
    assert pending["status"] == "pending_review"
    assert pending["pending_requirement_review"] is True
    assert pending["qualified_four_version_batch"] is False
    assert not (staging / "manifest.json").exists()
    attachment = installed_cli(
        "batch",
        "attach-requirements",
        staging / "staging.json",
        handoff_path,
        "--directory",
        attached,
    )
    assert attachment.returncode == 0, attachment.stdout + attachment.stderr
    assert json.loads(attachment.stdout)["status"] == "attached_pending_finalization"
    accepted = installed_cli(
        "batch", "finalize", attached / "attachment.json", "--directory", finalized
    )
    assert accepted.returncode == 0, accepted.stdout + accepted.stderr
    manifest = finalized / "manifest.json"
    native_intake = installed_cli("validate", manifest)
    assert native_intake.returncode == 0, native_intake.stdout + native_intake.stderr
    intake = json.loads(native_intake.stdout)
    assert intake["status"] == "accepted"
    inventory = intake["inventory"][0]["runs"]
    selected = json.loads(manifest.read_bytes())["groups"][0]["selected_runs"]
    assert set(inventory) == {"v0", "v1", "v2", "v3"}
    assert {version: run["run_id"] for version, run in selected.items()} == {
        "v0": "run-v0",
        "v1": "run-v1",
        "v2": "run-v2",
        "v3": "run-v3",
    }
    for binding in pending["artifact_bindings"]:
        assert (finalized / binding["path"]).read_bytes() == (
            staging / binding["path"]
        ).read_bytes()
    assert (finalized / "requirement-handoff.json").read_bytes() == originals[handoff_path]
    for name in (
        "authored-requirements.json",
        "requirements.json",
        "authoring-execution.json",
        "authoring-transcript.json",
        "review-execution.json",
        "review-transcript.json",
    ):
        assert (finalized / "requirements" / name).read_bytes() == originals[root / name]
    for version in inventory:
        run = selected[version]
        usage = json.loads((finalized / run["usage_ref"]["path"]).read_bytes())
        assert usage["collection_status"] == "unavailable"

    (root / "options.json").write_text(json.dumps(options()), encoding="utf-8")
    (root / "prices.json").write_text(json.dumps(run_prices()), encoding="utf-8")
    directory = root / "evaluation"
    calls = []

    def respond(request):
        calls.append(request)
        return mock_provider(request)

    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 10, 9, tzinfo=tz)

    from backend.evaluation import evaluation_run

    monkeypatch.setattr(evaluation_run, "datetime", FixedDatetime)
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "synthetic-google")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "synthetic-model")
    client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    try:
        assert (
            main(
                [
                    "evaluate",
                    "execute",
                    str(manifest),
                    "--directory",
                    str(directory),
                    "--options",
                    str(root / "options.json"),
                    "--prices",
                    str(root / "prices.json"),
                ],
                http_client=client,
            )
            == 0
        )
    finally:
        asyncio.run(client.aclose())
    report = json.loads(capsys.readouterr().out)
    assert report["generated_at"] == "2026-10-09T00:00:00+00:00"
    assert report["processing_status"] == report["acquisition_status"] == "complete"
    assert report["evidence_status"] == "unresolved"
    assert report["unknowns"] and '"FAIL"' in json.dumps(report["quality"])
    assert report["usage"]["actual_google_sends"] == 5
    assert report["usage"]["actual_model_sends"] == 1
    assert report["usage"]["retries"] == 0
    assert len(calls) == 6  # Independent identity and evidence only; no opening supplement.
    preparation = json.loads((directory / "preparation.json").read_bytes())
    receipt = json.loads((directory / "execution/receipt.json").read_bytes())
    assert (
        report["preparation_sha256"]
        == preparation["content_sha256"]
        == receipt["preparation_sha256"]
    )
    saved = {path: path.read_bytes() for path in directory.rglob("*") if path.is_file()}
    replay = installed_cli("evaluate", "replay", directory, evaluation_offline=True)
    assert replay.returncode == 0, replay.stdout + replay.stderr
    assert json.loads(replay.stdout) == report
    assert {path: path.read_bytes() for path in saved} == saved
    assert {path: path.read_bytes() for path in originals} == originals


def test_selected_generation_registration_is_recollectable_and_pending_review(
    installed_cli, tmp_path, capsys
):
    args = generate_tests.arguments(tmp_path, version="v3", execute=True)
    registration = generate_tests.registration(tmp_path, version="v3")
    selection = (tmp_path / "selection.json").read_bytes()
    original_input = (tmp_path / "input.json").read_bytes()

    class SelectedRuntime:
        async def run(self, version, request, **kwargs):
            assert version == "v3"
            return generate_tests.version_result(
                version, request, retrieval="partial", repair_status="ACCEPTED_PARTIAL"
            )

    assert (
        main(
            ["generate", *args, *registration],
            runtime=SelectedRuntime(),
            date_provider=generate_tests.REFERENCE,
        )
        == 0
    )
    report = json.loads(capsys.readouterr().out.splitlines()[-1])
    assert report["planner"]["status"] == "completed"
    assert report["registration"]["status"] == "incomplete"
    assert report["registration"]["pending_requirement_review"] is True
    staging = json.loads((tmp_path / "staging/staging.json").read_bytes())
    run = staging["groups"][0]["selected_runs"]["v3"]
    assert run["completion_qualified"] is True
    assert set(staging["groups"][0]["missing_versions"]) == {"v0", "v1", "v2"}
    captures = {
        path: path.read_bytes() for path in (tmp_path / "capture").rglob("*") if path.is_file()
    }
    config = next(tmp_path.glob("generation-collection-*.json"))
    collected = installed_cli("batch", "collect", config, "--directory", tmp_path / "recollected")
    assert collected.returncode == 0, collected.stdout + collected.stderr
    recollected = json.loads(collected.stdout)
    assert recollected["groups"] == staging["groups"]
    assert recollected["status"] == "incomplete"
    for name in ("input.json", "result.json", "usage.json", "provenance.json"):
        assert (tmp_path / "recollected/sources/capture" / name).read_bytes() == captures[
            tmp_path / "capture" / name
        ]
    assert not (tmp_path / "recollected/manifest.json").exists()
    assert {path: path.read_bytes() for path in captures} == captures
    assert (tmp_path / "selection.json").read_bytes() == selection
    assert (tmp_path / "input.json").read_bytes() == original_input
