"""Short commands for local Dayloom installation and operation."""

import argparse
import subprocess
import sys
from pathlib import Path


def main(argv=None, *, root=None):
    root = Path(root) if root is not None else Path(__file__).resolve().parents[2]
    launchers = {
        "start": "run_product.py",
        "check": "run_product.py",
        "db": "run_database.py",
        "migrate": "migrate_product.py",
    }
    parser = argparse.ArgumentParser(
        prog="dayloom",
        description=__doc__,
        epilog="prepare RELEASE: verify data and install sidecars\n"
        "tokenizers [--offline]: prepare or verify both vocabularies\n"
        "restore RELEASE: import into an empty local Compose database\n"
        "migrate: apply Product migrations\n"
        "start / check: launch Product or check local readiness\n"
        "db ARGS: forward Docker Compose lifecycle arguments",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("command", choices=("prepare", "tokenizers", "restore", *launchers))
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    if args.command in launchers:
        if args.command == "migrate":
            argparse.ArgumentParser(prog="dayloom migrate").parse_args(args.arguments)
        forwarded = (["--check"] if args.command == "check" else []) + args.arguments
        return subprocess.run(
            [sys.executable, str(root / "scripts" / launchers[args.command]), *forwarded],
            cwd=root,
            check=False,
        ).returncode
    selected = argparse.ArgumentParser(prog=f"dayloom {args.command}")
    if args.command in ("prepare", "restore"):
        selected.add_argument("release", type=Path)
    else:
        selected.add_argument(
            "--offline", action="store_true", help="Verify caches without downloads"
        )
    options = selected.parse_args(args.arguments)
    try:
        from backend.cli.resources import prepare_release, prepare_tokenizers, restore_database

        if args.command == "prepare":
            prepare_release(options.release, root)
        elif args.command == "restore":
            restore_database(options.release)
        else:
            prepare_tokenizers(root, offline=options.offline)
        return 0
    except (ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except Exception as exc:
        print(
            f"Local preparation failed ({type(exc).__name__}); check local settings.",
            file=sys.stderr,
        )
        return 2
