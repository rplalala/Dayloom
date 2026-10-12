"""Installed offline research declaration validation and fresh reports."""

import argparse
import json
from pathlib import Path


def main(argv=None):
    from backend.evaluation.research.registry import TRACKS

    parser = argparse.ArgumentParser(
        prog="rtpeval research",
        description="Offline research over declared original inputs and saved artifacts.",
    )
    commands = parser.add_subparsers(dest="operation", required=True)
    export = commands.add_parser(
        "export-census",
        help="Offline export from an explicit ordered producer-source inventory",
        description="Copy exact selected sources into a fresh validated census bundle. "
        "Historical runs require traceable dispatch metadata; no Planner/evaluator calls.",
    )
    export.add_argument("inventory", type=Path)
    export.add_argument("--directory", type=Path, required=True, help="Fresh export directory")
    for operation in ("validate", "report"):
        command = commands.add_parser(operation)
        command.add_argument("declaration", type=Path)
        command.add_argument("--track", choices=tuple(TRACKS), required=True)
        if operation == "report":
            command.add_argument(
                "--directory", type=Path, required=True, help="Fresh report directory"
            )
    args = parser.parse_args(argv)
    from backend.cli.collection import CollectionError
    from backend.evaluation.research.context import load_context
    from backend.evaluation.research.registry import build_report
    from backend.evaluation.research.rendering import render_markdown

    try:
        if args.operation == "export-census":
            from backend.evaluation.research.census_export import export_census

            print(json.dumps(export_census(args.inventory, args.directory)))
            return 0
        context = load_context(args.declaration)
        report, render = build_report(context, args.track)
        if args.operation == "report":
            directory = args.directory.resolve()
            if directory.exists():
                raise ValueError("Report directory must be fresh")
            directory.mkdir(parents=True, exist_ok=False)
            (directory / (args.track + ".json")).write_text(
                json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                encoding="utf-8",
            )
            markdown_path = directory / (args.track + ".md")
            markdown_path.write_text(
                render_markdown(
                    report, render, source_root=context.root, output_path=markdown_path
                ),
                encoding="utf-8",
            )
        print(
            json.dumps(
                {
                    "processing_status": "completed",
                    "track": args.track,
                    "semantic_sha256": report["semantic_sha256"],
                    "source_digest": report["source_digest"],
                }
            )
        )
        return 0
    except (CollectionError, OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        print(
            json.dumps(
                {"processing_status": "needs_material_correction", "diagnostics": [str(exc)]}
            )
        )
        return 2
