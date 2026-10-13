"""Task inventory and lazy native adapters, outside evaluator preparation hashes."""

import argparse
import io
import sys
from contextlib import redirect_stdout
from dataclasses import dataclass, field
from importlib import import_module


@dataclass(frozen=True)
class Task:
    description: str
    module: str = ""
    prefix: tuple[str, ...] = ()
    children: dict[str, "Task"] = field(default_factory=dict)
    accepts_argv: bool = True
    http_client: bool = False


def _leaf(module, description, *prefix, accepts_argv=True, http_client=False):
    return Task(description, module, prefix, accepts_argv=accepts_argv, http_client=http_client)


def _group(module, description, operations):
    return Task(
        description,
        children={name: _leaf(module, detail, name) for name, detail in operations.items()},
    )


TASKS = {
    "quality": _leaf(
        "backend.evaluation.quality_report_cli",
        "Offline quality report from frozen independent material; JSON to stdout.",
    ),
    "usage": _leaf(
        "backend.evaluation.usage_report",
        ("Offline descriptive resource report from four-version usage files; JSON to stdout."),
    ),
    "cost": _leaf(
        "backend.evaluation.cost_report",
        (
            "Offline explicit-price accounting from saved usage/snapshots and "
            "optional bills; --output JSON."
        ),
    ),
    "pair": Task(
        "V3 paired diagnostics and explicit acquisition; prepare/replay/export are offline.",
        children={
            "prepare": _leaf(
                "backend.evaluation.v3_pair_cli",
                "Offline source-linked edit provenance preparation.",
                "prepare",
            ),
            "report": _leaf(
                "backend.evaluation.v3_pair_cli",
                "Offline report from frozen draft/final evidence; preserves missing values.",
                "report",
            ),
            "acquire": Task(
                "Source-bound paired acquisition; execution requires explicit limits.",
                children={
                    name: _leaf("backend.cli.pair_acquire", detail, name, http_client=True)
                    for name, detail in {
                        "import": "Offline labelled reuse; missing observations stay unavailable.",
                        "prepare": "Offline validate stages, reviews, prices and destination.",
                        "execute": "Explicit acquisition; preserve failures and stopped attempts.",
                        "replay": "Offline source, implementation, snapshot and receipt checks.",
                        "export": "Offline evidence handoff for research and suite pairs.",
                    }.items()
                },
            ),
        },
    ),
    "controlled": _group(
        "backend.evaluation.controlled_cli",
        (
            "Offline specialized Controlled V3; replay executes the real V3 chain"
            " with frozen ports, distinct from saved-evidence replay."
        ),
        {
            "replay": (
                "Offline execution of frozen real V3 post-primary chain; no provider requests."
            ),
            "prepare": "Offline projection of executed V3 sources.",
            "identity-references": "Offline independent identity reference inventory.",
            "identity-plan": "Offline independent identity request planning.",
            "identity": (
                "Offline identity preparation or saved observation/model import; "
                "--legacy preserves historical rules."
            ),
            "evidence-plan": "Offline independent evidence request planning.",
            "report": "Offline independent controlled outcome report.",
            "batch": "Offline report over an explicitly declared controlled batch.",
        },
    ),
    "review": _group(
        "backend.evaluation.human_cli",
        ("Offline specialized local blinded review; participant collection remains separate."),
        {
            "prepare": "Offline blinded display material preparation.",
            "package": "Offline reviewed public HTML/presentation and private mapping outputs.",
            "import": "Offline supplied answer import.",
            "report": "Offline supplied answer report.",
        },
    ),
    "mechanism": _group(
        "backend.evaluation.mechanism_cli",
        ("Offline selected-source mechanism reports; missing capture remains unavailable."),
        {
            "prepare": "Offline selected source and optional supplied observation preparation.",
            "report": "Offline mechanism report; stdout or --output JSON.",
        },
    ),
    "advanced": Task(
        (
            "Advanced individual evidence interfaces; offline except explicit "
            "opening-run execute. Historical switches retain their native "
            "meaning."
        ),
        children={
            "identity": _leaf(
                "backend.evaluation.identity_cli",
                (
                    "Offline independent observations and saved model material; --legacy "
                    "selects historical reproduction."
                ),
            ),
            "identity-adoption": _leaf(
                "backend.evaluation.identity_adoption_cli",
                "Offline frozen V0 candidate/model packet reproduction.",
            ),
            "snapshot": _group(
                "backend.evaluation.snapshot_cli",
                (
                    "Offline snapshot request planning and saved-evidence replay; no "
                    "acquisition command."
                ),
                {
                    "identity-plan": "Offline independent identity request plan.",
                    "evidence-plan": "Offline independent evidence request plan.",
                    "replay": "Offline frozen snapshot replay.",
                    "identity-evidence": (
                        "Offline saved identity evidence; --historical reproduces the "
                        "original wire."
                    ),
                },
            ),
            "schedule": _leaf(
                "backend.evaluation.requirement_schedule_cli",
                "Offline requirement and schedule report from independent local material.",
            ),
            "opening": _leaf(
                "backend.evaluation.opening_cli",
                (
                    "Offline opening report from frozen snapshot and optional saved "
                    "opening judgment."
                ),
            ),
            "routes": _group(
                "backend.evaluation.route_cli",
                ("Offline same-day route preparation and scoring from independent local material."),
                {
                    "prepare": "Offline route request preparation.",
                    "score": "Offline route score from frozen evidence.",
                },
            ),
            "opening-judgment": _group(
                "backend.evaluation.opening_judgment_cli",
                (
                    "Offline explicit missing-hours access packet preparation/import; "
                    "never calls a model."
                ),
                {
                    "prepare": "Offline source-bound access judgment packet; --output JSON.",
                    "import": "Offline source-bound access model material; --output opening JSON.",
                },
            ),
            "opening-run": Task(
                (
                    "Explicit incremental opening assessment; prepare/replay offline, "
                    "execute online. Never implicit in primary evaluation."
                ),
                children={
                    "prepare": _leaf(
                        "backend.evaluation.evaluation_run_cli",
                        "Offline parent-bound opening preparation; fresh --directory required.",
                        "prepare-opening",
                        http_client=True,
                    ),
                    "execute": _leaf(
                        "backend.evaluation.evaluation_run_cli",
                        (
                            "Online one-use opening assessment; exact --approved-sha256 and "
                            "applicable authorization required."
                        ),
                        "execute-opening",
                        http_client=True,
                    ),
                    "replay": _leaf(
                        "backend.evaluation.evaluation_run_cli",
                        "Offline saved opening evidence/receipt replay.",
                        "replay-opening",
                        http_client=True,
                    ),
                },
            ),
        },
    ),
    "dev": Task(
        (
            "Development tools, distinct from normal evaluation and historical "
            "session-specific pilots. Online execution requires its own approved "
            "scope."
        ),
        children={
            "route-requests": _leaf(
                "backend.evaluation.tools.route_requests_cli",
                "Offline frozen V0 request inventory/budget; never acquires evidence.",
            ),
            "planner-usage": _leaf(
                "backend.evaluation.tools.planner_usage_cli",
                (
                    "Offline preparation by default; --execute runs one selected Planner "
                    "online with opt-in capture."
                ),
            ),
            "identity-smoke": _group(
                "tools.validation.identity_judgment_smoke",
                (
                    "Development identity smoke: offline prepare, explicitly authorized "
                    "online execute."
                ),
                {
                    "prepare": "Offline one-call identity smoke preparation.",
                    "execute": (
                        "Online one-call development identity smoke; exact approved manifest "
                        "digest required."
                    ),
                },
            ),
            "preference-smoke": _leaf(
                "tools.validation.preference_gate_smoke",
                (
                    "Online one-shot development interpreter smoke; requires "
                    "--execute-live and separate authorization."
                ),
                accepts_argv=False,
            ),
            "short-reference-packet": _leaf(
                "tools.validation.short_reference_packet",
                (
                    "Development short-reference packet: prepare/preflight make no "
                    "provider requests but load runtime settings; execute is online and "
                    "separately authorized."
                ),
                accepts_argv=False,
            ),
            "requirement-acceptance": _leaf(
                "tools.validation.requirement_acceptance",
                (
                    "Development requirement acceptance: freeze makes no model requests "
                    "but initializes runtime/client; execute is online and separately "
                    "authorized."
                ),
                accepts_argv=False,
            ),
            "poi-acceptance": _leaf(
                "tools.validation.poi_semantics_acceptance",
                (
                    "Online one-case development POI acceptance; --execute and separate "
                    "authorization required."
                ),
                accepts_argv=False,
            ),
            "repair-replay": _leaf(
                "tools.validation.repair_replay",
                "Offline development snapshot and frozen Repair preparation; no providers.",
                accepts_argv=False,
            ),
        },
    ),
}


def main(command, arguments, *, http_client=None):
    task = TASKS[command]
    installed = "rtpeval " + command
    while task.children:
        parser = argparse.ArgumentParser(
            prog=installed,
            description=task.description,
            epilog="\n".join(
                f"{name}: {child.description}" for name, child in task.children.items()
            ),
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        parser.add_argument("command", choices=tuple(task.children))
        parser.add_argument("arguments", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)
        args = parser.parse_args(arguments)
        task = task.children[args.command]
        installed += " " + args.command
        arguments = args.arguments

    native = import_module(task.module).main
    program, original_argv = sys.argv[0], sys.argv
    # Native subparsers append their own operation to the program name.
    native_program = installed.rsplit(" ", 1)[0] if task.prefix else installed
    try:
        sys.argv = [native_program, *task.prefix, *arguments]
        kwargs = {"http_client": http_client} if task.http_client else {}
        if any(flag in arguments for flag in ("--help", "-h")):
            output = io.StringIO()
            try:
                with redirect_stdout(output):
                    result = (
                        native([*task.prefix, *arguments], **kwargs)
                        if task.accepts_argv
                        else native()
                    )
            finally:
                print(task.description)
                print(
                    output.getvalue().replace(" ".join((native_program, *task.prefix)), installed),
                    end="",
                )
            return result
        return native([*task.prefix, *arguments], **kwargs) if task.accepts_argv else native()
    finally:
        sys.argv = original_argv
        sys.argv[0] = program
