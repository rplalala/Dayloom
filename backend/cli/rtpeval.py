"""Discover repository evaluation commands without initializing online runtimes."""

import argparse
import sys
from collections.abc import Sequence

from backend.cli.tools import TASKS


def main(
    argv: Sequence[str] | None = None,
    *,
    http_client=None,
    runtime=None,
    date_provider=None,
    clock=None,
) -> int:
    parser = argparse.ArgumentParser(
        prog="rtpeval",
        description="RTPEval: offline validation, preparation/replay and online evaluation.",
        epilog="validate: offline source-bound batch intake; JSON to stdout.\n"
        "evaluate: automatic evaluation; prepare/replay offline, execute online.\n"
        "suite: source-bound multi-case execution and offline replay/report.\n"
        "research: offline source-bound research reports.\n"
        "batch: offline explicitly selected material collection.\n"
        "generate: selected-version Planner preparation or explicit execution.\n"
        + "\n".join(f"{name}: {task.description}" for name, task in TASKS.items()),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "command",
        choices=("validate", "evaluate", "batch", "generate", "suite", "research", *TASKS),
        help="Evaluation task group",
    )
    parser.add_argument("arguments", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    if args.command == "validate":
        from backend.evaluation.__main__ import main as command
    elif args.command == "batch":
        from backend.cli.batch import main as command
    elif args.command == "generate":
        from backend.cli.generate import main as command
    elif args.command == "suite":
        from backend.cli.suite import main as command
    elif args.command == "research":
        from backend.cli.research import main as command
    elif args.command == "evaluate":
        from backend.cli.evaluate import main as command
    else:
        from backend.cli.tools import main as tools_main

        return tools_main(args.command, args.arguments, http_client=http_client)

    # The native parser derives usage from argv[0]; retain the installed subcommand.
    program = sys.argv[0]
    try:
        sys.argv[0] = f"{parser.prog} {args.command}"
        if args.command in ("evaluate", "suite"):
            return command(args.arguments, http_client=http_client)
        if args.command == "generate":
            from backend.cli.generate import main as generate_command

            return generate_command(
                args.arguments, runtime=runtime, date_provider=date_provider, clock=clock
            )
        return command(args.arguments)
    finally:
        sys.argv[0] = program
