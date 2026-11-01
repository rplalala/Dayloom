"""Explicit small release build inputs; never discover runtime configuration."""

import json
import re
import subprocess
import tarfile
from pathlib import Path

from deploy.release.baseline_artifact import SIDECARS, sha256
from deploy.release.images import (
    RESOURCE_PATHS,
    ReleaseError,
    copy_small_file,
    docker,
    inspect_image,
)

ROOT = Path(__file__).resolve().parents[1]


def resources(args):
    archive = Path(args.archive)
    if not re.fullmatch(r"[a-f0-9]{64}", args.sha256) or sha256(archive) != args.sha256:
        raise ReleaseError("Build-resource archive checksum mismatch")
    output = Path(args.output).resolve()
    if output.exists():
        raise ReleaseError("Resource output must be a new directory")
    with tarfile.open(archive) as bundle:
        members = bundle.getmembers()
        if (
            len(members) != len(RESOURCE_PATHS)
            or {m.name for m in members} != set(RESOURCE_PATHS)
            or any(not m.isfile() or m.size > 8 * 1024 * 1024 for m in members)
        ):
            raise ReleaseError("Build resources must contain only four approved regular files")
        contents = {m.name: bundle.extractfile(m).read() for m in members}
    output.mkdir(parents=True)
    for name, content in contents.items():
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    return {"directory": str(output), "resource_archive_sha256": args.sha256}


def check_inputs(args):
    resource_root = Path(args.resources).resolve()
    entries = {
        p.relative_to(resource_root).as_posix() for p in resource_root.rglob("*") if p.is_file()
    }
    if entries != set(RESOURCE_PATHS) or any(p.is_symlink() for p in resource_root.rglob("*")):
        raise ReleaseError("Build context contains missing or unapproved resource inputs")
    repository = ROOT.parent
    ignore = (repository / ".dockerignore").read_text().splitlines()
    if not {
        "*",
        "**/.env",
        "**/.env.*",
        "**/product.yaml",
        "**/*.pgcustom",
        "deploy/config/",
    } <= set(ignore):
        raise ReleaseError("Application context is missing required secret/data exclusions")
    tracked = (
        subprocess.run(["git", "ls-files", "-z"], cwd=repository, capture_output=True, check=True)
        .stdout.decode()
        .split("\0")
    )
    roots = ("backend/", "frontend/", "config/", "deploy/", "scripts/", "tools/")
    prohibited = re.compile(
        r"(?:\bsk-[A-Za-z0-9_-]{24,}|\bAKIA[A-Z0-9]{16}\b|"
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)"
    )
    for name in tracked:
        if (
            not name.startswith(roots)
            or name.startswith("backend/tests/")
            or Path(name).suffix not in {".py", ".yaml", ".yml", ".json", ".ts", ".tsx", ".sh"}
        ):
            continue
        path = repository / name
        if path.is_symlink():
            raise ReleaseError("Source build inputs must not be symbolic links")
        if prohibited.search(path.read_text(encoding="utf-8")):
            raise ReleaseError("Source build input contains a prohibited credential")
    inspect_image(args.baseline_image, allow_local=True)
    container = docker("create", args.baseline_image)
    # Only the small baseline manifest is copied. The dump stays inside its image.
    import tempfile

    try:
        with tempfile.TemporaryDirectory(prefix="dayloom-inputs-") as work:
            manifest = json.loads(
                copy_small_file(container, "/baseline/baseline.json", Path(work) / "baseline.json")
            )
    finally:
        docker("rm", "-v", container)
    from deploy.release.baseline_artifact import manifest_identity

    if manifest["baseline_id"] != manifest_identity(manifest):
        raise ReleaseError("Baseline manifest identity mismatch")
    for name in SIDECARS:
        if (
            sha256(resource_root / "data/tripworld" / name)
            != manifest["files"]["runtime/" + name]["sha256"]
        ):
            raise ReleaseError("Explicit build resources do not match selected baseline")
    return {
        "baseline_id": manifest["baseline_id"],
        "schema_sha256": manifest["database"]["schema_sha256"],
        "retrieval_sha256": manifest["files"]["runtime/" + SIDECARS[0]]["sha256"],
        "embedding_sha256": manifest["files"]["runtime/" + SIDECARS[1]]["sha256"],
    }
