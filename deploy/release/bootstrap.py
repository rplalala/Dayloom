"""Build the initial baseline from an explicit verified local artifact; never publish."""

import argparse
import json
import re
import subprocess
from pathlib import Path

from deploy.release.baseline_artifact import verify_release


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--source-revision", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,80}", args.version):
        parser.error("Use an explicit immutable baseline version")
    if not re.fullmatch(r"[a-f0-9]{40}", args.source_revision):
        parser.error("Use an exact source revision")
    try:
        manifest = verify_release(Path(args.artifact))
        tag = f"ghcr.io/rplalala/dayloom-baseline:{args.version}"
        command = [
            "docker",
            "buildx",
            "build",
            "--platform",
            "linux/amd64",
            "--load",
            "--provenance=false",
            "--target",
            "baseline",
            "-f",
            "deploy/docker/baseline.Dockerfile",
            "--build-context",
            f"baseline-data={Path(args.artifact).resolve()}",
            "--build-arg",
            f"SOURCE_REVISION={args.source_revision}",
            "--build-arg",
            f"BASELINE_VERSION={args.version}",
            "--build-arg",
            f"BASELINE_ID={manifest['baseline_id']}",
            "-t",
            tag,
            ".",
        ]
        subprocess.run(command, check=True, cwd=Path(__file__).resolve().parents[2])
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        parser.exit(
            2, "Baseline preparation failed; inspect the explicit artifact and Docker build.\n"
        )
    print(
        json.dumps(
            {
                "image_tag": tag,
                "baseline_id": manifest["baseline_id"],
                "publication_command": ["docker", "push", tag],
            }
        )
    )


if __name__ == "__main__":
    main()
