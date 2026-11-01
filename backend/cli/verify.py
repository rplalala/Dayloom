"""Verify the twelve published cases using the retained offline verifiers."""

import argparse
import runpy
from pathlib import Path


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="rtpeval verify",
        description="Verify saved results for all 12 cases offline; no database or provider keys.",
    )
    parser.parse_args(argv)
    root = Path(__file__).resolve().parents[2]
    failed = False
    for name in ("verify_automatic.py", "verify_blinded.py"):
        try:
            runpy.run_path(str(root / "benchmark" / name), run_name="__main__")
        except Exception as exc:
            print(f"FAIL {name}: {type(exc).__name__}: {exc}")
            failed = True
    return 2 if failed else 0
