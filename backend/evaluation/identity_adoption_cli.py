"""Replay a frozen V0 candidate/model packet; never call a model or provider."""

import argparse
import json
from pathlib import Path

from ._identity_cli import add_identity_options, identity_command
from .identity_adoption import load_v0_material, resolve_legacy_v0_identities
from .intake import _read
from .records import MaterialError, thaw


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", help="Versioned source-linked V0 material manifest")
    add_identity_options(parser)
    args = parser.parse_args(argv)
    try:

        def read(path):
            return _read(Path(path))[0] if path else None

        material = load_v0_material(
            None,
            args.bundle,
            historical=args.legacy or args.historical_llm or args.historical_program,
        )
        result = identity_command(
            thaw(material.intake),
            thaw(material.evidence),
            args,
            read,
            legacy=lambda reviews: resolve_legacy_v0_identities(None, args.bundle, reviews),
        )
    except (ValueError, TypeError, KeyError, OSError, StopIteration) as exc:
        diagnostic = exc.diagnostic if isinstance(exc, MaterialError) else {"explanation": str(exc)}
        print(json.dumps({"status": "needs_evidence_correction", "diagnostic": diagnostic}))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if args.prepare or args.prepare_subjects or result["status"] == "complete" else 3


if __name__ == "__main__":
    raise SystemExit(main())
