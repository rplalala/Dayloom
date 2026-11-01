"""Expand concise generation arguments into the unchanged native capture interface."""

import argparse
from pathlib import Path
from uuid import uuid4


def generation_arguments(argv):
    argv = list(argv)
    if not argv or argv[0].startswith("-"):
        if "--help" in argv or "-h" in argv:
            print("Short form: rtpeval generate VERSION REQUEST [-o DIRECTORY] [--execute]")
            print("Defaults: fresh artifacts/generation directory, request-stem group, unique run.")
        return argv
    parser = argparse.ArgumentParser(
        prog="rtpeval generate",
        description="Prepare one planner offline; add --execute to make provider requests.",
    )
    parser.add_argument("version", choices=("v0", "v1", "v2", "v3"))
    parser.add_argument("request", type=Path)
    parser.add_argument("-o", "--output-directory", type=Path)
    parser.add_argument("--group-id", "-g")
    parser.add_argument("--run-id", "-r")
    parser.add_argument("-c", "--runtime-config")
    parser.add_argument("-e", "--env-file")
    parser.add_argument("-b", "--register-batch")
    parser.add_argument("-s", "--registration-directory")
    parser.add_argument("--execute", action="store_true")
    args, extra = parser.parse_known_args(argv)
    if any(arg.split("=", 1)[0] in {"--version", "--input-json"} for arg in extra):
        parser.error("Use positional VERSION and REQUEST or the original flag form, not both")
    generated_id = f"{args.version}-{uuid4().hex}"
    run_id = args.run_id or generated_id
    output = args.output_directory or Path("artifacts/generation") / generated_id
    expanded = [
        "--version",
        args.version,
        "--input-json",
        str(args.request),
        "--output-directory",
        str(output),
        "--group-id",
        args.group_id or args.request.stem,
        "--run-id",
        run_id,
    ]
    for flag, value in (
        ("--runtime-config", args.runtime_config),
        ("--env-file", args.env_file),
        ("--register-batch", args.register_batch),
        ("--registration-directory", args.registration_directory),
    ):
        if value is not None:
            expanded.extend((flag, value))
    if args.execute:
        expanded.append("--execute")
    return [*expanded, *extra]
