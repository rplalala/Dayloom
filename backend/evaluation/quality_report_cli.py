"""Build final multimetric quality reports from frozen local material."""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from .intake import _read, load_batch
from .quality_report import REPORT_VERSION, build_quality_report, quality_content_hash
from .records import MaterialError


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest")
    parser.add_argument("identity_report")
    parser.add_argument("snapshot_directory")
    parser.add_argument("--quality-profile", choices=["rtpeval_declared_population_1"])
    parser.add_argument("--context", help="Reviewed IANA time context JSON")
    parser.add_argument("--occupancy-reviews", help="Independent occupancy review JSON")
    parser.add_argument("--route-reviews", help="Source-linked route policy review JSON")
    parser.add_argument("--coordinates", help="Independent canonical coordinate evidence JSON")
    parser.add_argument(
        "--density-reviews", help="Source-linked daily pace/count policy review JSON"
    )
    parser.add_argument(
        "--identity-snapshot", help="Linked identity snapshot for automatic coordinates"
    )
    parser.add_argument("--expected-plan", help="Optional trusted full snapshot plan JSON")
    parser.add_argument(
        "--opening-judgment", help="Source-bound missing-hours access model material"
    )
    parser.add_argument("--generated-at", help="Explicit offset-aware report creation timestamp")
    args = parser.parse_args(argv)
    generated_at = (
        args.generated_at if args.generated_at is not None else datetime.now(UTC).isoformat()
    )
    try:
        intake = load_batch(args.manifest)
        identity, identity_hash = _read(Path(args.identity_report))
        files, hashes = {}, {"identity": identity_hash}
        for name, attribute in (
            ("schedule_context", "context"),
            ("occupancy_reviews", "occupancy_reviews"),
            ("route_reviews", "route_reviews"),
            ("coordinate_evidence", "coordinates"),
            ("expected_plan", "expected_plan"),
            ("density_reviews", "density_reviews"),
            ("opening_judgment", "opening_judgment"),
        ):
            path = getattr(args, attribute)
            files[name], hashes[attribute] = _read(Path(path)) if path else (None, None)
        if args.identity_snapshot is not None:
            files["identity_snapshot_directory"] = args.identity_snapshot
        result = build_quality_report(
            intake,
            identity,
            args.snapshot_directory,
            **files,
            generated_at=generated_at,
            quality_profile=args.quality_profile,
        ).to_dict()
        result["preparation_file_sha256"] = hashes
    except MaterialError as exc:
        result = {
            "schema_version": REPORT_VERSION,
            "generated_at": generated_at,
            "status": "needs_material_correction",
            "groups": [],
            "diagnostics": [exc.diagnostic],
        }
    result["content_hash"] = quality_content_hash(result)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False))
    return 0 if result["status"] == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
