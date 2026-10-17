"""Prepare selected V3 edit provenance or report independent paired diagnostics."""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from .intake import _read, load_batch
from .records import MaterialError
from .v3_correspondence import PROVENANCE_VERSION, prepare_v3_correspondence, read_v3_result_sources
from .v3_pair_report import REPORT_VERSION, build_v3_pair_report, pair_content_hash


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser(
        "prepare", help="Replay selected result bytes into edit provenance"
    )
    report = commands.add_parser("report", help="Score frozen draft/final-primary pairs")
    for command in (prepare, report):
        command.add_argument("manifest")
        command.add_argument("identity_report")
    report.add_argument("snapshot_directory", nargs="?", help="Frozen paired evidence snapshot")
    for option, help_text in (
        ("context", "Independent schedule timezone JSON"),
        ("occupancy-reviews", "Independent occupancy JSON"),
        ("route-reviews", "Route policy review JSON"),
        ("coordinates", "Reviewed independent coordinates JSON"),
        ("expected-plan", "Optional trusted paired snapshot plan JSON"),
        ("edit-provenance", "Optional preparation to verify against original result bytes"),
        ("correspondence-reviews", "Evidence-backed residual correspondence review JSON"),
        ("density-reviews", "Source-linked daily pace/count policy review JSON"),
        ("opening-judgment", "Source-bound paired missing-hours access model material JSON"),
    ):
        report.add_argument("--" + option, help=help_text)
    report.add_argument(
        "--identity-snapshot", help="Linked identity snapshot for saved coordinates"
    )
    report.add_argument("--generated-at", help="Explicit offset-aware creation time")
    args = parser.parse_args(argv)
    generated_at = getattr(args, "generated_at", None) or datetime.now(UTC).isoformat()
    try:
        intake = load_batch(args.manifest)
        identity, identity_hash = _read(Path(args.identity_report))
        sources = read_v3_result_sources(intake, args.manifest)
        if args.command == "prepare":
            result = prepare_v3_correspondence(intake, identity, sources).to_dict()
        else:
            files, hashes = {}, {"identity": identity_hash}
            for name, attribute in (
                ("schedule_context", "context"),
                ("occupancy_reviews", "occupancy_reviews"),
                ("route_reviews", "route_reviews"),
                ("coordinate_evidence", "coordinates"),
                ("expected_plan", "expected_plan"),
                ("edit_provenance", "edit_provenance"),
                ("correspondence_reviews", "correspondence_reviews"),
                ("density_reviews", "density_reviews"),
            ):
                path = getattr(args, attribute)
                files[name], hashes[attribute] = _read(Path(path)) if path else (None, None)
            if args.opening_judgment:
                files["opening_judgment"], hashes["opening_judgment"] = _read(
                    Path(args.opening_judgment)
                )
            result = build_v3_pair_report(
                intake,
                identity,
                args.snapshot_directory,
                **files,
                result_sources=sources,
                identity_snapshot_directory=args.identity_snapshot,
                generated_at=generated_at,
            ).to_dict()
            result["preparation_file_sha256"] = hashes
            result["content_hash"] = pair_content_hash(result)
    except (MaterialError, ValueError, KeyError, TypeError, OSError) as exc:
        result = {
            "schema_version": REPORT_VERSION if args.command == "report" else PROVENANCE_VERSION,
            "status": "needs_material_correction",
            "groups": [],
            "diagnostics": [
                exc.diagnostic
                if isinstance(exc, MaterialError)
                else {"reason": "material_invalid", "explanation": str(exc)}
            ],
        }
        if args.command == "report":
            result["generated_at"] = generated_at
            result["content_hash"] = pair_content_hash(result)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False))
    return 0 if result["status"] == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
