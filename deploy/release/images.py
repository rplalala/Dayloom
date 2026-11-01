"""Inspect immutable release images without starting their processes or copying data."""

import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from deploy.release.baseline_artifact import SIDECARS, manifest_identity

SOURCE = "https://github.com/rplalala/Dayloom"
HEX = r"[a-f0-9]{64}"
IMAGE = rf"[a-z0-9][a-z0-9./_-]*@sha256:{HEX}"
RESOURCE_PATHS = (
    ".cache/tokenizer/fb374d419588a4632f3f557e76b4b70aebbca790",
    "data/tripworld/tokenizer_cache/9b5ad71b2ce5302211f9c61530b329a4922fc6a4",
    *("data/tripworld/" + name for name in SIDECARS),
)


class ReleaseError(ValueError):
    """A sanitized release validation failure."""


def docker(*args):
    executable = shutil.which("docker")
    if executable is None:
        raise ReleaseError("Docker is required to inspect selected immutable images")
    result = subprocess.run([executable, *args], capture_output=True, timeout=300)
    if result.returncode:
        raise ReleaseError("Docker image inspection failed; pull the exact selected digest first")
    return result.stdout.decode("utf-8").strip()


def inspect_image(reference, allow_local):
    if not re.fullmatch(IMAGE, reference):
        raise ReleaseError("Images must use immutable repository@sha256 references")
    if not allow_local and not reference.startswith("ghcr.io/rplalala/dayloom-"):
        raise ReleaseError("Public releases require repository-associated GHCR images")
    info = json.loads(docker("image", "inspect", reference))[0]
    if reference not in info.get("RepoDigests", []):
        raise ReleaseError("Selected image digest does not match Docker's inspected identity")
    if info.get("Os") != "linux" or info.get("Architecture") != "amd64":
        raise ReleaseError("Only Linux amd64 images are supported")
    labels = info.get("Config", {}).get("Labels") or {}
    if labels.get("org.opencontainers.image.source") != SOURCE and not allow_local:
        raise ReleaseError("Image is missing repository provenance")
    # Image environment must never embed runtime or registry credentials.
    for field in info.get("Config", {}).get("Env") or []:
        name, _, value = field.partition("=")
        if value and re.search(r"(?i)(password|secret|api_key|access_key|token$|db_url)", name):
            raise ReleaseError("Image embeds a prohibited runtime credential")
    return info


def copy_small_file(container, path, output):
    docker("cp", f"{container}:{path}", str(output))
    if output.stat().st_size > 2 * 1024 * 1024:
        raise ReleaseError("Image metadata exceeds the permitted size")
    return output.read_bytes()


def image_metadata(app, baseline):
    with tempfile.TemporaryDirectory(prefix="dayloom-release-") as work:
        directory = Path(work)
        baseline_container = docker("create", baseline)
        try:
            manifest = json.loads(
                copy_small_file(
                    baseline_container, "/baseline/baseline.json", directory / "baseline.json"
                )
            )
        finally:
            docker("rm", "-v", baseline_container)
        if manifest.get("format") != "dayloom-baseline-v1" or manifest.get(
            "baseline_id"
        ) != manifest_identity(manifest):
            raise ReleaseError("Embedded baseline manifest identity mismatch")
        container = docker("create", app)
        try:
            for index, name in enumerate(SIDECARS):
                content = copy_small_file(
                    container, "/opt/dayloom/data/tripworld/" + name, directory / f"sidecar-{index}"
                )
                if (
                    hashlib.sha256(content).hexdigest()
                    != manifest["files"]["runtime/" + name]["sha256"]
                ):
                    raise ReleaseError("Application retrieval resources do not match the baseline")
        finally:
            docker("rm", "-v", container)
    return manifest
