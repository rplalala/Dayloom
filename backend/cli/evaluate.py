"""Explicit automatic evaluation; preparation and replay remain offline."""

import argparse
import io
import json
from collections.abc import Sequence
from contextlib import redirect_stdout

PREPARATION_FILES = (
    "options",
    "prices",
    "context",
    "occupancy-reviews",
    "route-reviews",
    "density-reviews",
)


def _execute(argv: Sequence[str], *, http_client=None) -> int:
    parser = argparse.ArgumentParser(
        prog="rtpeval evaluate execute",
        description="Online automatic evaluation; emits the native report and preserves stops.",
        epilog="One-step mode requires --directory, --options and --prices. The internal digest "
        "proves integrity, not independent authorization. Missing-hours access assessment "
        "precedes final scoring under the prepared limits. No retries or resume.",
    )
    parser.add_argument(
        "source", help="Qualified batch manifest, or a prepared directory in legacy mode"
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--directory", "-o", help="Fresh output directory for one-step preparation/execution"
    )
    mode.add_argument(
        "--approved-sha256", help="Exact prepared digest for the legacy execute route"
    )
    aliases = {"options": "-c", "prices": "-p"}
    for option in PREPARATION_FILES:
        flags = ["--" + option] + ([aliases[option]] if option in aliases else [])
        parser.add_argument(*flags)
    parser.add_argument(
        "--env-file", "-e", help="Credential file loaded only by explicit execution"
    )
    args = parser.parse_args(argv)
    if args.directory is not None:
        if not args.directory:
            parser.error("--directory must not be empty")
        if not args.options or not args.prices:
            parser.error("one-step execution requires --options and --prices")
    elif any(getattr(args, name.replace("-", "_")) is not None for name in PREPARATION_FILES):
        parser.error("preparation options cannot be combined with --approved-sha256")

    from backend.evaluation.evaluation_run_cli import main as native

    if args.directory is not None:
        prepare = ["prepare", args.source, "--directory", args.directory]
        for name in PREPARATION_FILES:
            value = getattr(args, name.replace("-", "_"))
            if value is not None:
                prepare.extend(["--" + name, value])
        # Native preparation owns validation and source/implementation binding. Only its
        # small summary is captured; the execution report remains the public stdout.
        summary = io.StringIO()
        with redirect_stdout(summary):
            status = native(prepare)
        if status:
            print(summary.getvalue(), end="")
            return status
        directory = args.directory
        digest = json.loads(summary.getvalue())["preparation_sha256"]
    else:
        directory, digest = args.source, args.approved_sha256
    execute = ["execute", directory, "--approved-sha256", digest]
    if args.env_file is not None:
        execute.extend(["--env-file", args.env_file])
    return native(execute, http_client=http_client)


def main(argv: Sequence[str] | None = None, *, http_client=None) -> int:
    parser = argparse.ArgumentParser(
        prog="rtpeval evaluate",
        description="Automatic evaluation: prepare/replay are offline; execute is online.",
        epilog="execute accepts a qualified manifest or an explicitly approved prepared directory.",
    )
    parser.add_argument("command", choices=("prepare", "execute", "replay"))
    parser.add_argument("arguments", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.command == "execute":
        return _execute(args.arguments, http_client=http_client)

    from backend.evaluation.evaluation_run_cli import main as native

    return native([args.command, *args.arguments], http_client=http_client)
