"""Render and verify a four-file, digest-pinned Dayloom deployment release."""

import argparse
import gzip
import hashlib
import io
import json
import re
import subprocess
import tarfile
from pathlib import Path

from deploy.release.baseline_artifact import SIDECARS, sha256
from deploy.release.images import HEX, IMAGE, ReleaseError, image_metadata, inspect_image

ROOT = Path(__file__).resolve().parents[1]
FILES = ("compose.yaml", ".env.example", "start.sh", "README.md")


def validate_metadata(metadata):
    fields = {
        "format",
        "version",
        "source_revision",
        "app_image",
        "baseline_image",
        "baseline_id",
        "schema_sha256",
        "retrieval_sha256",
        "embedding_sha256",
    }
    if (
        not isinstance(metadata, dict)
        or set(metadata) != fields
        or any(not isinstance(value, str) for value in metadata.values())
    ):
        raise ReleaseError("Invalid release metadata fields")
    if metadata.get("format") != "dayloom-release-v1":
        raise ReleaseError("Unsupported release format")
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:-[a-z0-9.-]+)?", metadata["version"]):
        raise ReleaseError("Version must be an exact semantic version without a v prefix")
    if not re.fullmatch(r"[a-f0-9]{40}", metadata["source_revision"]):
        raise ReleaseError("Source revision must be an exact Git commit")
    for field in ("baseline_id", "schema_sha256", "retrieval_sha256", "embedding_sha256"):
        if not re.fullmatch(HEX, metadata[field]):
            raise ReleaseError("Invalid release compatibility identity")
    for field in ("app_image", "baseline_image"):
        if not re.fullmatch(IMAGE, metadata[field]):
            raise ReleaseError("Images must use immutable repository@sha256 references")


def release_guard(metadata):
    return f"""
# Fresh installation must use the version-matched, inspected release selection.
# Existing instances retain their installed baseline through maintenance upgrades.
if [[ ! -f $CONFIG_DIR/.env ]]; then
  if [[ $APP_IMAGE != '{metadata["app_image"]}' ||
        $BASELINE_IMAGE != '{metadata["baseline_image"]}' ||
        $BASELINE_ID != '{metadata["baseline_id"]}' ]]; then
    fail 'Release identity mismatch; use the matching complete deployment bundle.'
  fi
fi
for image in "$APP_IMAGE" "$BASELINE_IMAGE"; do
  [[ $image =~ @sha256:[a-f0-9]{{64}}$ ]] || fail 'Immutable image digests are required.'
done
if [[ ${{OPERATION:-launch}} == upgrade ]]; then
  [[ ${{OPERATION_ARGS[0]:-}} =~ @sha256:[a-f0-9]{{64}}$ ]] ||
    fail 'Immutable upgrade image digest is required.'
fi
"""


def public_defaults(text):
    fields = {}
    allowed = {
        "DAYLOOM_APP_IMAGE",
        "DAYLOOM_BASELINE_IMAGE",
        "DAYLOOM_BASELINE_ID",
        "DAYLOOM_HOST_PORT",
        "COMPOSE_PROJECT_NAME",
        "DAYLOOM_DB_NAME",
        "DAYLOOM_DB_USER",
    }
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        name, separator, value = line.partition("=")
        if not separator or name not in allowed or name in fields:
            raise ReleaseError("Release template must contain only approved public configuration")
        fields[name] = value
    if set(fields) != allowed:
        raise ReleaseError("Release template omits required public configuration")
    return fields


def render(metadata):
    result = {name: (ROOT / name).read_text(encoding="utf-8") for name in FILES}
    defaults = result[".env.example"]
    public_defaults(defaults)
    for key, value in (
        ("DAYLOOM_APP_IMAGE", metadata["app_image"]),
        ("DAYLOOM_BASELINE_IMAGE", metadata["baseline_image"]),
        ("DAYLOOM_BASELINE_ID", metadata["baseline_id"]),
    ):
        defaults = re.sub(rf"^{key}=.*$", f"{key}={value}", defaults, flags=re.MULTILINE)
    result[".env.example"] = (
        "# DAYLOOM_RELEASE="
        + json.dumps(metadata, sort_keys=True, separators=(",", ":"))
        + "\n"
        + defaults
    )
    marker = "BASELINE_ID=$(pick DAYLOOM_BASELINE_ID)\n"
    if result["start.sh"].count(marker) != 1:
        raise ReleaseError("Launcher release injection marker is missing or ambiguous")
    result["start.sh"] = result["start.sh"].replace(marker, marker + release_guard(metadata))
    version = metadata["version"]
    asset = f"dayloom-{version}-linux-amd64.tar.gz"
    download = (
        "## Download this exact version\n\n"
        "After this version is publicly released:\n\n```bash\n"
        f"mkdir dayloom-{version} && cd dayloom-{version}\n"
        f"url=https://github.com/rplalala/Dayloom/releases/download/dayloom-v{version}\n"
        f'curl --fail --location "$url/{asset}" -o {asset}\n'
        f'curl --fail --location "$url/{asset}.sha256" -o {asset}.sha256\n'
        f"sha256sum --check --ignore-missing {asset}.sha256\n"
        f"tar -xzf {asset}\n"
        f"sha256sum --check {asset}.sha256\n"
        "bash start.sh\n```\n\n"
        "Checksums detect corruption; trust the selected repository Release and its image digests. "
        "Preparation and local builds do not establish public availability.\n\n"
    )
    source_only = (
        "The source checkout template deliberately uses local image tags and an unpublished\n"
        "baseline placeholder. For local development select `DAYLOOM_APP_IMAGE`,\n"
        "`DAYLOOM_BASELINE_IMAGE` and the verified `DAYLOOM_BASELINE_ID` before launching.\n"
        "Release packaging replaces those defaults with exact release identities.\n\n"
    )
    result["README.md"] = result["README.md"].replace(source_only, "")
    result["README.md"] = (
        f"# Dayloom {metadata['version']}\n\n"
        f"Source revision: `{metadata['source_revision']}`. Linux amd64.\n\n"
        f"Application: `{metadata['app_image']}`.\n\n"
        f"Factory baseline: `{metadata['baseline_image']}`; identity "
        f"`{metadata['baseline_id']}`.\n\n"
        "Application and baseline images are independently versioned. Existing installations "
        "keep their installed baseline; follow the maintenance commands below for upgrades.\n\n"
        + download
        + result["README.md"]
    )
    return {name: content.encode("utf-8") for name, content in result.items()}


def build(args):
    metadata = {
        "format": "dayloom-release-v1",
        "version": args.version,
        "source_revision": args.source_revision,
        "app_image": args.app_image,
        "baseline_image": args.baseline_image,
        "baseline_id": args.baseline_id,
        "schema_sha256": "0" * 64,
        "retrieval_sha256": "0" * 64,
        "embedding_sha256": "0" * 64,
    }
    validate_metadata(metadata)
    app = inspect_image(args.app_image, args.allow_local_images)
    baseline = inspect_image(args.baseline_image, args.allow_local_images)
    labels = app.get("Config", {}).get("Labels") or {}
    if labels.get("org.opencontainers.image.revision") != args.source_revision:
        raise ReleaseError("Application source revision label does not match the release")
    if (
        not args.allow_local_images
        and labels.get("org.opencontainers.image.version") != args.version
    ):
        raise ReleaseError("Application version label does not match the release")
    manifest = image_metadata(args.app_image, args.baseline_image)
    if manifest["baseline_id"] != args.baseline_id:
        raise ReleaseError("Selected baseline identity does not match its image")
    baseline_labels = baseline.get("Config", {}).get("Labels") or {}
    if not args.allow_local_images and (
        baseline_labels.get("io.dayloom.baseline.id") != args.baseline_id
        or baseline_labels.get("org.opencontainers.image.version") in {None, "", "unreleased"}
    ):
        raise ReleaseError("Baseline version/identity labels do not match the release")
    metadata.update(
        schema_sha256=manifest["database"]["schema_sha256"],
        retrieval_sha256=manifest["files"]["runtime/" + SIDECARS[0]]["sha256"],
        embedding_sha256=manifest["files"]["runtime/" + SIDECARS[1]]["sha256"],
    )
    validate_metadata(metadata)
    files = render(metadata)
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    archive = output / f"dayloom-{args.version}-linux-amd64.tar.gz"
    checksum = archive.with_name(archive.name + ".sha256")
    if archive.exists() or checksum.exists():
        raise ReleaseError("Release output already exists; never overwrite a version")
    # Stable timestamps, permissions and ordering make equivalent releases byte reproducible.
    with (
        archive.open("xb") as stream,
        gzip.GzipFile(fileobj=stream, mode="wb", mtime=0, filename="") as compressed,
    ):
        with tarfile.open(fileobj=compressed, mode="w") as bundle:
            for name in FILES:
                entry = tarfile.TarInfo(name)
                entry.size = len(files[name])
                entry.mode = 0o755 if name == "start.sh" else 0o644
                bundle.addfile(entry, io.BytesIO(files[name]))
    entries = [
        (archive.name, sha256(archive)),
        *((name, hashlib.sha256(files[name]).hexdigest()) for name in FILES),
    ]
    checksum.write_text(
        "".join(f"{digest}  {name}\n" for name, digest in entries), encoding="utf-8", newline="\n"
    )
    return {
        **metadata,
        "archive": str(archive),
        "checksum": str(checksum),
        "archive_bytes": archive.stat().st_size,
        "app_image_bytes": app["Size"],
        "baseline_image_bytes": baseline["Size"],
    }


def verify(args):
    archive = Path(args.archive)
    checksum = Path(args.checksum) if args.checksum else archive.with_name(archive.name + ".sha256")
    entries = {}
    for line in checksum.read_text(encoding="utf-8").splitlines():
        digest, name = line.split("  ", 1)
        if not re.fullmatch(HEX, digest) or name in entries:
            raise ReleaseError("Invalid or duplicate release checksum entry")
        entries[name] = digest
    if set(entries) != {*FILES, archive.name} or sha256(archive) != entries[archive.name]:
        raise ReleaseError("Release archive checksum mismatch")
    content = {}
    with tarfile.open(archive) as bundle:
        members = bundle.getmembers()
        if (
            len(members) != 4
            or {m.name for m in members} != set(FILES)
            or any(not m.isfile() or m.size > 1024 * 1024 for m in members)
        ):
            raise ReleaseError("Release archive must contain only four regular deployment files")
        for member in members:
            content[member.name] = bundle.extractfile(member).read()
            if hashlib.sha256(content[member.name]).hexdigest() != entries[member.name]:
                raise ReleaseError("Release file checksum mismatch")
    lines = content[".env.example"].decode().splitlines()
    metadata = json.loads(
        next(
            line.removeprefix("# DAYLOOM_RELEASE=")
            for line in lines
            if line.startswith("# DAYLOOM_RELEASE=")
        )
    )
    validate_metadata(metadata)
    if archive.name != f"dayloom-{metadata['version']}-linux-amd64.tar.gz":
        raise ReleaseError("Archive filename and release version mismatch")
    defaults = public_defaults(content[".env.example"].decode())
    for key, field in (
        ("DAYLOOM_APP_IMAGE", "app_image"),
        ("DAYLOOM_BASELINE_IMAGE", "baseline_image"),
        ("DAYLOOM_BASELINE_ID", "baseline_id"),
    ):
        if defaults.get(key) != metadata[field]:
            raise ReleaseError("Release metadata and image selection mismatch")
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build_parser = commands.add_parser("build")
    for name in (
        "version",
        "source-revision",
        "app-image",
        "baseline-image",
        "baseline-id",
        "output",
    ):
        build_parser.add_argument("--" + name, required=True)
    build_parser.add_argument("--allow-local-images", action="store_true")
    verify_parser = commands.add_parser("verify")
    verify_parser.add_argument("archive")
    verify_parser.add_argument("--checksum")
    resources_parser = commands.add_parser("resources")
    for name in ("archive", "sha256", "output"):
        resources_parser.add_argument("--" + name, required=True)
    inputs_parser = commands.add_parser("check-inputs")
    inputs_parser.add_argument("--resources", required=True)
    inputs_parser.add_argument("--baseline-image", required=True)
    args = parser.parse_args()
    try:
        if args.command in {"resources", "check-inputs"}:
            from deploy.release.inputs import check_inputs, resources

            result = resources(args) if args.command == "resources" else check_inputs(args)
        else:
            result = build(args) if args.command == "build" else verify(args)
    except ReleaseError as error:
        parser.exit(2, f"Release validation failed: {error}.\n")
    except (
        OSError,
        ValueError,
        KeyError,
        IndexError,
        StopIteration,
        tarfile.TarError,
        subprocess.SubprocessError,
    ):
        # Never echo Docker output, image environment or arbitrary file contents.
        parser.exit(
            2, "Release validation failed; check immutable identities, resources and inputs.\n"
        )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
