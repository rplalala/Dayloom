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
FILE_ALIASES = {"directory": "-o", "options": "-c", "prices": "-p"}


def _prepare(command, argv):
    parser = argparse.ArgumentParser(
        prog="rtpeval evaluate " + command,
        description="Offline source-bound evaluation preparation; no provider requests.",
    )
    positional = {
        "prepare": ("manifest",),
        "prepare-opening": ("parent_directory",),
        "prepare-pair-opening": ("manifest", "identity_report", "snapshot_directory"),
    }[command]
    for name in positional:
        parser.add_argument(name)
    for name, alias in FILE_ALIASES.items():
        parser.add_argument("--" + name, alias, required=True)
    optional = (
        ("quality-profile", "context", "occupancy-reviews", "route-reviews", "density-reviews")
        if command == "prepare"
        else ("context", "expected-plan")
        if command == "prepare-pair-opening"
        else ()
    )
    for name in optional:
        parser.add_argument("--" + name)
    args = parser.parse_args(argv)
    forwarded = [command, *(getattr(args, name) for name in positional)]
    for name in (*FILE_ALIASES, *optional):
        value = getattr(args, name.replace("-", "_"))
        if value is not None:
            forwarded.extend(("--" + name, value))
    from backend.evaluation.evaluation_run_cli import main as native

    return native(forwarded)


def _execute_opening(argv, *, http_client=None):
    parser = argparse.ArgumentParser(
        prog="rtpeval evaluate execute-opening",
        description="One explicit online opening assessment; no Google acquisition or retries.",
    )
    parser.add_argument("directory")
    parser.add_argument("--approved-sha256", "-a", required=True)
    parser.add_argument("--env-file", "-e")
    args = parser.parse_args(argv)
    forwarded = ["execute-opening", args.directory, "--approved-sha256", args.approved_sha256]
    if args.env_file is not None:
        forwarded.extend(("--env-file", args.env_file))
    from backend.evaluation.evaluation_run_cli import main as native

    return native(forwarded, http_client=http_client)


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
        "--approved-sha256", "-a", help="Exact prepared digest for the legacy execute route"
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
    parser.add_argument(
        "command",
        choices=(
            "prepare",
            "execute",
            "replay",
            "prepare-opening",
            "execute-opening",
            "replay-opening",
            "prepare-pair-opening",
        ),
    )
    parser.add_argument("arguments", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.command == "execute":
        return _execute(args.arguments, http_client=http_client)
    if args.command in ("prepare", "prepare-opening", "prepare-pair-opening"):
        return _prepare(args.command, args.arguments)
    if args.command == "execute-opening":
        return _execute_opening(args.arguments, http_client=http_client)

    from backend.evaluation.evaluation_run_cli import main as native

    return native([args.command, *args.arguments], http_client=http_client)
