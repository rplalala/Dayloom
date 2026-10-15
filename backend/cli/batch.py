"""Offline producer-side material commands."""

import argparse
import json
from pathlib import Path


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="rtpeval batch", description="Offline material staging and finalization."
    )
    commands = parser.add_subparsers(dest="operation", required=True)
    collect_parser = commands.add_parser(
        "collect",
        help="Collect explicitly selected sources offline",
        description="Offline exact-byte collection into unqualified producer staging.",
    )
    collect_parser.add_argument("config", type=Path)
    collect_parser.add_argument(
        "--directory", required=True, type=Path, help="Fresh staging directory"
    )
    attach_parser = commands.add_parser(
        "attach-requirements",
        help="Attach external RequirementSpec review offline",
        description=(
            "Offline attachment of source-bound externally authored/reviewed requirements; "
            "never operates an agent."
        ),
    )
    attach_parser.add_argument("staging", type=Path)
    attach_parser.add_argument("handoff", type=Path)
    attach_parser.add_argument(
        "--directory", required=True, type=Path, help="Fresh attachment directory"
    )
    finalize_parser = commands.add_parser(
        "finalize",
        help="Finalize qualified material through native intake offline",
        description=(
            "Offline native intake gate; publishes an accepted manifest "
            "only into a fresh destination."
        ),
    )
    finalize_parser.add_argument("attachment", type=Path)
    for option in ("projection-reviews", "occupancy-reviews"):
        finalize_parser.add_argument("--" + option, type=Path)
    finalize_parser.add_argument(
        "--directory", required=True, type=Path, help="Fresh finalized directory"
    )
    preflight_parser = commands.add_parser(
        "preflight", help="Offline activity-review coverage queue"
    )
    preflight_parser.add_argument(
        "source", type=Path, help="Producer staging or native batch manifest"
    )
    args = parser.parse_args(argv)
    from backend.cli.collection import CollectionError, collect

    try:
        if args.operation == "collect":
            result = collect(args.config, args.directory)
        elif args.operation == "attach-requirements":
            from backend.cli.finalization import attach_requirements

            result = attach_requirements(args.staging, args.handoff, args.directory)
        elif args.operation == "preflight":
            from backend.cli.reviews import preflight

            result = preflight(args.source)
        else:
            from backend.cli.finalization import finalize

            result = finalize(
                args.attachment,
                args.directory,
                projection_reviews=args.projection_reviews,
                occupancy_reviews=args.occupancy_reviews,
            )
    except (CollectionError, OSError, ValueError, KeyError, TypeError, RecursionError) as exc:
        print(json.dumps({"status": "needs_material_correction", "diagnostics": [str(exc)]}))
        return 2
    print(json.dumps(result))
    return 2 if result.get("status") == "needs_semantic_review" else 0
