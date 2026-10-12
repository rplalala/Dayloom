"""Paired evidence: offline preparation/replay/export, explicit provider execution."""

import argparse
import asyncio
import json
from pathlib import Path


def main(argv=None, *, http_client=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser(
        "prepare", help="Offline selected-stage, review and limit preflight"
    )
    prepare.add_argument("manifest", help="Qualified original batch manifest")
    for name in ("directory", "selection", "options", "prices"):
        prepare.add_argument("--" + name, required=True)
    for name in (
        "context",
        "occupancy-reviews",
        "route-reviews",
        "density-reviews",
        "correspondence-reviews",
        "identity-snapshot",
        "snapshot",
    ):
        prepare.add_argument("--" + name)
    execute = commands.add_parser(
        "execute", help="Explicit independent acquisition; no retries or resume"
    )
    execute.add_argument("directory")
    execute.add_argument("--approved-sha256", required=True)
    execute.add_argument(
        "--env-file", help="Credentials loaded only after local execution preflight"
    )
    replay = commands.add_parser(
        "replay", help="Offline verify receipts and rebuild native pair diagnostics"
    )
    replay.add_argument("directory")
    export = commands.add_parser("export", help="Offline fresh source-bound research/suite handoff")
    export.add_argument("source", help="Completed acquisition directory")
    export.add_argument("--directory", required=True, help="Fresh output directory")
    args = parser.parse_args(argv)
    try:
        from backend.evaluation import paired_run
        from backend.evaluation.intake import _read

        if args.command == "prepare":
            result = paired_run.prepare(
                args.manifest,
                args.directory,
                selection=_read(Path(args.selection))[0],
                options=_read(Path(args.options))[0],
                prices=_read(Path(args.prices))[0],
                context={
                    name: _read(Path(getattr(args, option)))[0] if getattr(args, option) else None
                    for name, option in paired_run.CONTEXT_FILES.items()
                },
                files={
                    name: getattr(args, name.replace("-", "_"))
                    for name in (
                        "selection",
                        "options",
                        "prices",
                        "context",
                        "occupancy-reviews",
                        "route-reviews",
                        "density-reviews",
                        "correspondence-reviews",
                    )
                },
                identity_snapshot=args.identity_snapshot,
                snapshot=args.snapshot,
            )
        elif args.command == "execute":
            paired_run.preflight(args.directory, args.approved_sha256)
            from backend.evaluation.paired_execution import execute

            result = asyncio.run(
                execute(
                    args.directory,
                    approved_sha256=args.approved_sha256,
                    env_file=args.env_file,
                    http_client=http_client,
                )
            )
        elif args.command == "replay":
            result = paired_run.replay(args.directory)
        else:
            result = paired_run.export(args.source, args.directory)
    except (ValueError, TypeError, KeyError, OSError, RecursionError) as exc:
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
