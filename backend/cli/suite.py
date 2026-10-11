"""Explicit suite preparation/execution and offline replay/report commands."""

import argparse
import json
from collections.abc import Sequence


def main(argv: Sequence[str] | None = None, *, http_client=None) -> int:
    parser = argparse.ArgumentParser(
        prog="rtpeval suite",
        description="Multi-case evaluation: prepare/replay/report offline; execute online.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser(
        "prepare", description="Offline complete source and budget preflight"
    )
    prepare.add_argument("declaration")
    prepare.add_argument("--directory", required=True, help="Fresh suite output directory")
    execute = commands.add_parser(
        "execute", description="Online one-use sequential native execution"
    )
    execute.add_argument("directory")
    execute.add_argument("--approved-sha256", required=True)
    execute.add_argument("--env-file")
    for name in ("replay", "report"):
        command = commands.add_parser(
            name, description="Offline saved-source and evidence validation"
        )
        command.add_argument("directory")
        if name == "report":
            command.add_argument(
                "--attachments", help="Offline explicit study report refresh declaration"
            )
    args = parser.parse_args(argv)
    from backend.evaluation import suite

    try:
        if args.command == "prepare":
            result = suite.prepare_suite(args.declaration, args.directory)
        elif args.command == "execute":
            result = suite.execute_suite(
                args.directory,
                approved_sha256=args.approved_sha256,
                env_file=args.env_file,
                http_client=http_client,
            )
        elif args.command == "replay":
            result = suite.replay_suite(args.directory)
        else:
            result = suite.report_suite(args.directory, attachments=args.attachments)
    except (ValueError, TypeError, KeyError, OSError) as exc:
        result = {
            "processing_status": "needs_material_correction",
            "error_type": type(exc).__name__,
            "reason": str(exc),
        }
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return (
        0
        if result.get("status") == "prepared" or result.get("processing_status") == "complete"
        else 2
    )
