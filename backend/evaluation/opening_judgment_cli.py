"""Prepare or validate missing-hours access judgments without model/provider clients."""

import argparse
import json
from pathlib import Path

from .intake import _read, load_batch
from .opening import score_opening
from .opening_judgment import prepare_packet
from .snapshot import _bytes


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "import"):
        command = commands.add_parser(name)
        command.add_argument("manifest")
        command.add_argument("identity_report")
        command.add_argument("snapshot_directory")
        command.add_argument("--context")
        command.add_argument("--expected-plan")
        command.add_argument("--paired", action="store_true")
        command.add_argument("--pair-only", action="store_true")
        command.add_argument("--output", required=True)
        if name == "prepare":
            command.add_argument("--model", required=True)
        else:
            command.add_argument("--material", required=True)
    args = parser.parse_args(argv)
    try:
        intake = load_batch(args.manifest)
        identity = _read(Path(args.identity_report))[0]
        context = _read(Path(args.context))[0] if args.context else None
        expected = _read(Path(args.expected_plan))[0] if args.expected_plan else None
        if args.command == "prepare":
            value = prepare_packet(
                intake,
                identity,
                args.snapshot_directory,
                context,
                model=args.model,
                paired=args.paired,
                expected_plan=expected,
                pair_only=args.pair_only,
            )
        else:
            value = score_opening(
                intake,
                identity,
                args.snapshot_directory,
                context,
                paired=args.paired,
                expected_plan=expected,
                opening_judgment=_read(Path(args.material))[0],
            ).to_dict()
            if value["status"] != "complete":
                raise ValueError(str(value["diagnostics"]))
        Path(args.output).write_bytes(_bytes(value))
        result = {"status": "complete", "output": args.output}
        if args.command == "prepare":
            result.update(eligible_count=len(value["cases"]), packet_sha256=value["content_sha256"])
    except (ValueError, KeyError, TypeError, OSError) as exc:
        result = {"status": "needs_material_correction", "reason": str(exc)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
