"""Replay independent identity observations against a selected offline batch."""

import argparse
import json
from pathlib import Path

from ._identity_cli import add_identity_options, identity_command
from .intake import _read, load_batch
from .records import MaterialError


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", help="Accepted batch manifest")
    parser.add_argument("evidence", help="Independent identity observation JSON")
    parser.add_argument("audit_plan", nargs="?", help="Historical audit JSON; requires --legacy")
    add_identity_options(parser)
    args = parser.parse_args(argv)
    intake = load_batch(args.manifest)
    if intake.status != "accepted":
        print(json.dumps(intake.to_dict(), ensure_ascii=False, indent=2, allow_nan=False))
        return 2
    try:
        evidence, evidence_hash = _read(Path(args.evidence))

        def read(path):
            return _read(Path(path))[0] if path else None

        audit_plan = read(args.audit_plan)
        result = identity_command(intake, evidence, args, read, audit=audit_plan)
    except (MaterialError, ValueError, TypeError, KeyError, OSError) as exc:
        diagnostic = exc.diagnostic if isinstance(exc, MaterialError) else {"explanation": str(exc)}
        print(json.dumps({"status": "needs_evidence_correction", "diagnostic": diagnostic}))
        return 2
    if args.legacy:
        result["evidence_file_sha256"] = evidence_hash
        result["audit_plan_file_sha256"] = _read(Path(args.audit_plan))[1]
        result["review_file_sha256"] = _read(Path(args.reviews))[1] if args.reviews else None
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if args.prepare or args.prepare_subjects or result["status"] == "complete" else 3


if __name__ == "__main__":
    raise SystemExit(main())
