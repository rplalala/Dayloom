"""Explicit fixed-scope corpus preparation, measurement and offline export."""

import argparse
import json
from pathlib import Path


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="rtpeval research corpus",
        description="Pinned eligible-entity census; no embeddings or provider/model calls.",
    )
    commands = parser.add_subparsers(dest="operation", required=True)
    for operation, help_text in (
        ("prepare", "Offline validate fixed scope, snapshot, profile and explicit limits"),
        ("measure", "Measure saved data or an explicitly authorized read-only database"),
        ("export", "Offline export an already saved, evidenced measurement"),
    ):
        command = commands.add_parser(operation, description=help_text, help=help_text)
        command.add_argument("source", type=Path)
        command.add_argument("--directory", type=Path, required=True, help="Fresh output directory")
        if operation == "measure":
            command.add_argument(
                "--database", action="store_true", help="Explicitly allow database network access"
            )
            command.add_argument(
                "--dsn-env",
                help="Environment variable containing database connection credentials; never saved",
            )
    args = parser.parse_args(argv)
    from backend.cli.collection import CollectionError
    from backend.evaluation.research.corpus import export, measure, prepare

    try:
        if args.operation == "export":
            receipt = export(args.source, args.directory)
        else:
            receipt = (
                prepare(args.source, args.directory)
                if args.operation == "prepare"
                else measure(
                    args.source, args.directory, database=args.database, dsn_env=args.dsn_env
                )
            )
        print(json.dumps(receipt, allow_nan=False))
        return 0
    except (CollectionError, OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        print(
            json.dumps(
                {"processing_status": "needs_material_correction", "diagnostics": [str(exc)]}
            )
        )
        return 2
