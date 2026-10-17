"""Prepare, execute or replay a complete independent four-final evaluation run."""

import argparse
import asyncio
import json
import os
from pathlib import Path

from .evaluation_run import execute_run, prepare_run, replay_run
from .intake import _read


def main(argv=None, *, http_client=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare", help="Offline source, context and limit validation")
    prepare.add_argument("manifest")
    prepare.add_argument("--quality-profile", choices=["rtpeval_declared_population_1"])
    for option in ("directory", "options", "prices"):
        prepare.add_argument("--" + option, required=True)
    for option in ("context", "occupancy-reviews", "route-reviews", "density-reviews"):
        prepare.add_argument("--" + option)
    execute = commands.add_parser(
        "execute", help="Independent evidence and eligible access assessment before final scoring"
    )
    execute.add_argument("directory")
    execute.add_argument("--approved-sha256", required=True)
    execute.add_argument("--env-file")
    replay = commands.add_parser(
        "replay", help="Recompute final reports with no network or credentials"
    )
    replay.add_argument("directory")
    opening = commands.add_parser(
        "prepare-opening",
        help="Prepare incremental missing-hours model assessment from a completed run",
    )
    opening.add_argument("parent_directory")
    for option in ("directory", "options", "prices"):
        opening.add_argument("--" + option, required=True)
    opening_execute = commands.add_parser(
        "execute-opening", help="One approved opening model attempt; no Google acquisition"
    )
    opening_execute.add_argument("directory")
    opening_execute.add_argument("--approved-sha256", required=True)
    opening_execute.add_argument("--env-file")
    opening_replay = commands.add_parser(
        "replay-opening", help="Offline full report replay including opening model assessment"
    )
    opening_replay.add_argument("directory")
    pair_opening = commands.add_parser(
        "prepare-pair-opening", help="Offline V3-only paired access preparation"
    )
    pair_opening.add_argument("manifest")
    pair_opening.add_argument("identity_report")
    pair_opening.add_argument("snapshot_directory")
    for option in ("directory", "options", "prices"):
        pair_opening.add_argument("--" + option, required=True)
    for option in ("context", "expected-plan"):
        pair_opening.add_argument("--" + option)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            context = {
                "schedule_context": _read(Path(args.context))[0] if args.context else None,
                **{
                    name: _read(Path(getattr(args, name)))[0] if getattr(args, name) else None
                    for name in ("occupancy_reviews", "route_reviews", "density_reviews")
                },
            }
            result = prepare_run(
                args.manifest,
                args.directory,
                options=_read(Path(args.options))[0],
                prices=_read(Path(args.prices))[0],
                quality_profile=args.quality_profile,
                **context,
            )
            result = {
                "status": result["status"],
                "directory": result["directory"],
                "preparation_sha256": result["content_sha256"],
                "identity_request_count": len(result["identity_plan"]["requests"]),
                "max_model_sends": result["max_model_sends"],
                "assess_missing_hours": result["options"]["assess_missing_hours"],
            }
        elif args.command == "execute":
            if args.env_file:
                from dotenv import load_dotenv

                load_dotenv(args.env_file, override=False)
            preparation = _read(Path(args.directory) / "preparation.json")[0]
            result = asyncio.run(
                execute_run(
                    preparation,
                    approved_sha256=args.approved_sha256,
                    google_api_key=os.environ.get("GOOGLE_MAPS_API_KEY"),
                    model_api_key=os.environ.get("AZURE_OPENAI_API_KEY"),
                    http_client=http_client,
                )
            )
        elif args.command == "prepare-pair-opening":
            from .paired_opening import prepare_pair_opening

            preparation = prepare_pair_opening(
                args.manifest,
                args.identity_report,
                args.snapshot_directory,
                args.directory,
                options=_read(Path(args.options))[0],
                prices=_read(Path(args.prices))[0],
                schedule_context=_read(Path(args.context))[0] if args.context else None,
                expected_plan=_read(Path(args.expected_plan))[0] if args.expected_plan else None,
            )
            result = {
                "status": "prepared",
                "directory": preparation["directory"],
                "preparation_sha256": preparation["content_sha256"],
                "eligible_count": len(preparation["packet"]["cases"]),
            }
        elif args.command == "prepare-opening":
            from .opening_run import prepare_opening_run

            preparation = prepare_opening_run(
                args.parent_directory,
                args.directory,
                options=_read(Path(args.options))[0],
                prices=_read(Path(args.prices))[0],
            )
            result = {
                "status": "prepared",
                "directory": preparation["directory"],
                "preparation_sha256": preparation["content_sha256"],
                "eligible_count": len(preparation["packet"]["cases"]),
            }
        elif args.command == "execute-opening":
            from .opening_run import execute_opening_run

            if args.env_file:
                from dotenv import load_dotenv

                load_dotenv(args.env_file, override=False)
            preparation = _read(Path(args.directory) / "preparation.json")[0]
            result = asyncio.run(
                execute_opening_run(
                    preparation,
                    approved_sha256=args.approved_sha256,
                    model_api_key=os.environ.get("AZURE_OPENAI_API_KEY"),
                    http_client=http_client,
                )
            )
        elif args.command == "replay-opening":
            from .opening_run import replay_opening_run

            result = replay_opening_run(args.directory)
        else:
            result = replay_run(args.directory)
    except (ValueError, TypeError, KeyError, OSError) as exc:
        result = {
            "processing_status": "needs_material_correction",
            "error_type": type(exc).__name__,
            "reason": str(exc),
        }
        from .semantic_readiness import MissingSemanticReviews

        if isinstance(exc, MissingSemanticReviews):
            result["processing_status"] = "needs_semantic_review"
            result["semantic_readiness"] = exc.report
        from .declared_population import UnreadyPopulation

        if isinstance(exc, UnreadyPopulation):
            result["processing_status"] = "needs_population_resolution"
            result["population_readiness"] = exc.report
    print(json.dumps(result, ensure_ascii=True, indent=2, allow_nan=False))
    return (
        0
        if result.get("status") == "prepared" or result.get("processing_status") == "complete"
        else 2
    )


if __name__ == "__main__":
    raise SystemExit(main())
