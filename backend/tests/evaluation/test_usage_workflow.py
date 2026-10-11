"""Synthetic usage acceptance through actual offline module processes (Issue #49)."""

import copy
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from backend.tests.evaluation import test_route_cli as route_commands
from backend.tests.evaluation import test_routes as route_tests
from backend.tests.evaluation import test_v3_pair_report as pair_tests
from backend.tests.evaluation.controlled_fixtures import expectations, material
from backend.tests.evaluation.test_controlled_replay import case, scripted
from backend.tests.evaluation.test_controlled_report import addition_case
from backend.tests.evaluation.test_human_answers import answer, bundle
from backend.tests.evaluation.test_human_tasks import config
from backend.tests.evaluation.test_human_tasks import review as display_review
from backend.tests.versions.v3.test_b_targets import edit, visit
from backend.tests.versions.v3.test_validation import DAY

pytest_plugins = ("backend.tests.evaluation.test_intake",)
prepared_scenario = route_tests.prepared_scenario
route_case = route_tests.route_case
pair_case = pair_tests.pair_case
ROOT = Path(__file__).resolve().parents[3]
STAMP = "2026-10-04T00:00:00Z"

GUARD = """import socket
import sys

connect = socket.socket.connect
connect_ex = socket.socket.connect_ex
resolve = socket.getaddrinfo

def check(address):
    host = address[0] if isinstance(address, tuple) else address
    if host not in ("127.0.0.1", "::1", "localhost"):
        print("OFFLINE_USAGE_NETWORK_BLOCK: " + str(host), file=sys.stderr)
        raise RuntimeError("OFFLINE_USAGE_NETWORK_BLOCK: " + str(host))

def guarded_connect(self, address):
    check(address)
    return connect(self, address)

def guarded_connect_ex(self, address):
    check(address)
    return connect_ex(self, address)

def guarded_resolve(host, *args, **kwargs):
    check((host,))
    return resolve(host, *args, **kwargs)

socket.socket.connect = guarded_connect
socket.socket.connect_ex = guarded_connect_ex
socket.getaddrinfo = guarded_resolve
print("OFFLINE_USAGE_GUARD_ACTIVE", file=sys.stderr)

# Match the parent suite's synthetic tokenization; no downloaded vocabulary needed.
from backend.app.runtime import token_counting

class FixtureEncoding:
    def encode_ordinary(self, text):
        return range((len(text.encode("utf-8")) + 3) // 4)

token_counting.tokenizer = lambda: FixtureEncoding()
print("OFFLINE_USAGE_SYNTHETIC_TOKENIZER", file=sys.stderr)
"""


def save(root, name, value):
    path = root / name
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def sources(root):
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in root.rglob("*")
        if path.is_file() and "cli-output" not in path.relative_to(root).parts
    }


def cli(root, module, *args, expected_exit=0):
    """Persist real CLI stdout, stderr and argv; guard external connections."""
    output = root / "cli-output"
    guard = output / "guard"
    guard.mkdir(parents=True, exist_ok=True)
    (guard / "sitecustomize.py").write_text(GUARD, encoding="utf-8")
    before = sources(root)
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    env["PYTHONPATH"] = os.pathsep.join((str(guard), str(ROOT)))
    command = [sys.executable, "-m", "backend.evaluation" + module, *map(str, args)]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        capture_output=True,
        encoding="utf-8",
        timeout=90,
    )
    sequence = len(list(output.glob("*-command.json"))) + 1
    prefix = f"{sequence:02d}-{module.lstrip('.') or 'intake'}"
    (output / (prefix + "-stdout.json")).write_text(completed.stdout, encoding="utf-8")
    (output / (prefix + "-stderr.txt")).write_text(completed.stderr, encoding="utf-8")
    save(output, prefix + "-command.json", {"argv": command, "exit_code": completed.returncode})
    assert "OFFLINE_USAGE_GUARD_ACTIVE" in completed.stderr
    assert "OFFLINE_USAGE_NETWORK_BLOCK" not in completed.stderr
    assert completed.returncode == expected_exit, completed.stdout + completed.stderr
    assert {name: sources(root).get(name) for name in before} == before
    return json.loads(completed.stdout)


def test_four_version_quality_and_missing_usage_through_module_clis(route_case):
    packet = route_case()
    args = route_commands.arguments(packet)[1:]
    root = packet[2].parent
    assert cli(root, "", args[0])["status"] == "accepted"
    quality = cli(root, ".quality_report_cli", *args, "--generated-at", STAMP)
    assert quality["status"] == "complete"
    group = quality["groups"][0]
    assert set(group["versions"]) == {"v0", "v1", "v2", "v3"}
    assert group["versions"]["v1"]["auxiliary_total"]["score_0_100"] == 50
    assert group["versions"]["v1"]["dimensions"]["opening"]["counts"]["UNKNOWN"] == 2
    usage = cli(root, ".usage_report", *(root / (v + "-usage.json") for v in group["versions"]))
    assert usage["quality_score_contribution"] is None
    assert all(r["metrics"]["total_tokens"] is None for r in usage["groups"][0]["runs"].values())


def test_v3_retime_resolves_overlap_through_module_clis(pair_case):
    def before(itinerary):
        itinerary["days"][0]["activities"][1].update(
            start_time="2020-01-01T09:30:00Z", end_time="2020-01-01T10:30:00Z"
        )

    def after(itinerary):
        itinerary["days"][0]["activities"][1].update(
            start_time="2020-01-01T11:00:00Z", end_time="2020-01-01T12:00:00Z"
        )

    packet = pair_case(
        before=before,
        after=after,
        edits=[
            pair_tests.edit(
                "retime", "b", start_time="2020-01-01T11:00:00Z", end_time="2020-01-01T12:00:00Z"
            )
        ],
    )
    args = route_commands.arguments(packet)[1:]
    root = packet[2].parent
    provenance = cli(root, ".v3_pair_cli", "prepare", *args[:2])
    provenance_path = save(root, "edit-provenance.json", provenance)
    report = cli(
        root,
        ".v3_pair_cli",
        "report",
        *args,
        "--edit-provenance",
        provenance_path,
        "--generated-at",
        STAMP,
    )
    assert report["status"] == "complete"
    pair = report["groups"][0]
    conflict = next(c for c in pair["continuity"]["conflicts"] if c["transition"] == "resolved")
    assert conflict["before"]["state"] == "FAIL" and conflict["after"] is None
    assert any(
        r["basis"] == "validated_adopted_lineage" for r in pair["correspondence"]["relations"]
    )
    assert pair["visit_changes"]["removed_count"] == 0
    assert pair["deltas"]["dimensions"]["grounding"]["verified_score_percentage_points"] == 0
    assert pair["deltas"]["dimensions"]["grounding"]["verified_fraction_exact_delta"] == {
        "numerator": 0,
        "denominator": 1,
    }
    assert pair["deltas"]["auxiliary_total"]["percentage_points"] is None


@pytest.mark.parametrize(
    "scenario,expected",
    [
        ("overlap", "resolved"),
        ("unchanged", "valid_no_change"),
        ("addition", "lawful_change"),
        ("exclusive", "regressed"),
    ],
)
def test_controlled_outcomes_through_module_clis(tmp_path, scenario, expected):
    targets, guards = [], []
    if scenario == "overlap":
        value = case(
            [
                [
                    visit("a", "a", start="10:00", end="11:00"),
                    visit("b", "b", start="10:30", end="11:30"),
                ]
            ]
        )
        value["role"] = "target"
        value = scripted(value, {"edits": [edit("retime", "b", start="11:30", end="12:30")]})
        targets = [
            {
                "goal_id": "overlap",
                "basis": "confirmed_conflict",
                "detector": {"check": "overlap", "activity_ids": ["a", "b"]},
                "condition": {
                    "kind": "check",
                    "dimension": "conflicts",
                    "activity_ids": ["a", "b"],
                },
            }
        ]
    elif scenario == "unchanged":
        value = case()
    else:
        value = addition_case(exclusive=scenario == "exclusive")
        if scenario == "exclusive":
            guards = [
                {
                    "goal_id": "one-visit",
                    "basis": "explicit_requirement",
                    "condition": {
                        "kind": "daily_count",
                        "date": str(DAY),
                        "minimum": 1,
                        "maximum": 1,
                    },
                    "source": {
                        "field": "additional_preferences",
                        "quote": "Exactly one primary visit on this day.",
                    },
                }
            ]
    case_path = save(tmp_path, "case.json", value)
    execution = cli(tmp_path, ".controlled_cli", "replay", case_path)
    execution_path = save(tmp_path, "execution.json", execution)
    package = material(value, execution, tmp_path / "snapshot")
    paths = {
        k: save(tmp_path, k + ".json", v) for k, v in package.items() if k != "snapshot_directory"
    }
    goals = save(
        tmp_path,
        "expectations.json",
        expectations(value, execution, targets=targets, guards=guards),
    )
    prepared = cli(
        tmp_path, ".controlled_cli", "prepare", case_path, execution_path, paths["requirement_spec"]
    )
    assert prepared["status"] == "accepted"
    selected_path = save(tmp_path, "controlled-preparation.json", prepared)
    mechanisms = cli(tmp_path, ".mechanism_cli", "prepare", "--selection", selected_path)
    mechanism_path = save(tmp_path, "mechanism-preparation.json", mechanisms)
    mechanism_report = cli(tmp_path, ".mechanism_cli", "report", mechanism_path)
    assert len(mechanism_report["runs"]) == 1
    assert mechanism_report["runs"][0]["version"] == "v3"
    assert mechanism_report["runs"][0]["model_attempts"] == (0 if scenario == "unchanged" else 1)
    out = cli(
        tmp_path,
        ".controlled_cli",
        "report",
        case_path,
        execution_path,
        paths["requirement_spec"],
        goals,
        paths["identity_report"],
        package["snapshot_directory"],
        "--context",
        paths["schedule_context"],
        "--route-reviews",
        paths["route_reviews"],
        "--coordinates",
        paths["coordinate_evidence"],
        "--expected-plan",
        paths["expected_plan"],
        "--generated-at",
        STAMP,
    )
    assert out["status"] == "complete"
    actual = out["targets"][0]["independent_outcome"] if targets else out["control"]["outcome"]
    assert actual == expected
    if scenario == "exclusive":
        assert out["execution"]["repair_status"] == "ACCEPTED_COMPLETE"
        assert out["guards"][0]["before"]["state"] == "PASS"
        assert out["guards"][0]["after"]["state"] == "FAIL"


def test_mechanism_missing_observations_through_module_clis(batch):
    _, _, write, _, root = batch
    prepared = cli(root, ".mechanism_cli", "prepare", "--manifest", write())
    prepared_path = save(root, "mechanism-preparation.json", prepared)
    report = cli(root, ".mechanism_cli", "report", prepared_path)
    assert len(report["runs"]) == 4
    by_version = {run["version"]: run for run in report["runs"]}
    for version in ("v0", "v1", "v2"):
        assert by_version[version]["coverage"] == "not_applicable"
    assert by_version["v3"]["coverage"] == "unavailable"
    assert by_version["v3"]["model_attempts"] is None


def test_blinded_package_answer_import_and_report_through_module_clis(batch):
    _, _, write, _, root = batch
    cfg = save(root, "human-config.json", config())
    prepared = cli(root, ".human_cli", "prepare", write(), cfg)
    reviewed = display_review(prepared)
    reviewed["reviewer_ref"] = "synthetic-example-reviewer"
    review_path = save(root, "display-review.json", reviewed)
    js, css = root / "renderer.js", root / "renderer.css"
    js.write_text('document.body.dataset.ready="yes";', encoding="utf-8")
    css.write_text("body{color:black}", encoding="utf-8")
    # Regression tests need no npm installation. Acceptance selects the built renderer.
    if renderer_dir := os.environ.get("EVALUATION_USAGE_RENDERER_DIR"):
        js, css = Path(renderer_dir) / "review.js", Path(renderer_dir) / "review.css"
    public_dir, private_path = root / "public", root / "private.json"
    package = cli(
        root,
        ".human_cli",
        "package",
        root / "manifest.json",
        cfg,
        review_path,
        "--out",
        public_dir,
        "--private-out",
        private_path,
        "--renderer-js",
        js,
        "--renderer-css",
        css,
    )
    assert package["status"] == "complete"
    assert sorted(p.name for p in public_dir.iterdir()) == ["presentation.json", "review.html"]
    public = json.loads((public_dir / "presentation.json").read_text(encoding="utf-8"))
    assert set(public["tasks"][0]["plans"]) == {"A", "B", "C", "D"}
    answers = save(root, "synthetic-answers.json", bundle(answer(public)))
    args = (public_dir / "presentation.json", private_path, answers)
    imported = cli(root, ".human_cli", "import", *args)
    assert imported["effective"][0]["answer_revision"] == 1
    report = cli(root, ".human_cli", "report", *args, "--generated-at", STAMP)
    assert report["main_task_count"] == 1


def test_missing_and_changed_source_are_actionable_without_input_mutation(batch):
    manifest, _, write, _, root = batch
    write()
    missing = cli(root, "", root / "missing.json", expected_exit=2)
    assert missing["status"] == "needs_material_correction"
    assert missing["material_diagnostics"][0]["pointer"] == "missing.json"
    modified = root / "changed-v3.json"
    modified.write_bytes((root / "v3.json").read_bytes() + b"\n")
    changed = copy.deepcopy(manifest)
    changed["groups"][0]["selected_runs"]["v3"]["result_ref"]["path"] = modified.name
    path = save(root, "changed-manifest.json", changed)
    stale = cli(root, "", path, expected_exit=2)
    assert stale["status"] == "needs_material_correction"
    assert stale["material_diagnostics"][0]["pointer"] == "changed-v3.json"
    assert stale["material_diagnostics"][0]["explanation"] == "Artifact hash mismatch"
