"""Build a digest-pinned app-only deployment; no baseline image is inspected or pulled."""

import argparse
import json
import re
import tarfile
from pathlib import Path

from deploy.release.images import IMAGE, ReleaseError, inspect_image
from deploy.release.package import ROOT, read_bundle, write_bundle


def validate(metadata):
    fields = {"format", "version", "source_revision", "app_image"}
    if isinstance(metadata, dict) and metadata.get("format") == "dayloom-light-release-v2":
        fields.add("architecture")
    if (
        not isinstance(metadata, dict)
        or set(metadata) != fields
        or metadata.get("format") not in {"dayloom-light-release-v1", "dayloom-light-release-v2"}
        or any(not isinstance(value, str) for value in metadata.values())
    ):
        raise ReleaseError("Invalid light release metadata")
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(-[a-z0-9.-]+)?", metadata["version"]):
        raise ReleaseError("Invalid light release version")
    if not re.fullmatch(r"[a-f0-9]{40}", metadata["source_revision"]):
        raise ReleaseError("Invalid light source revision")
    if not re.fullmatch(IMAGE, metadata["app_image"]):
        raise ReleaseError("Light releases require an immutable app digest")
    if metadata.get("architecture", "amd64") not in {"amd64", "arm64"}:
        raise ReleaseError("Unsupported light release architecture")


def build(args):
    metadata = {
        "format": "dayloom-light-release-v2",
        "version": args.version,
        "source_revision": args.source_revision,
        "app_image": args.app_image,
        "architecture": args.architecture,
    }
    validate(metadata)
    image = inspect_image(args.app_image, args.allow_local_images, args.architecture)
    labels = image.get("Config", {}).get("Labels") or {}
    if (
        labels.get("org.opencontainers.image.revision") != args.source_revision
        or labels.get("io.dayloom.remote-database") != "1"
        or (
            not args.allow_local_images
            and labels.get("org.opencontainers.image.version") != args.version
        )
    ):
        raise ReleaseError("App revision, version or remote database support is incompatible")
    launcher = (ROOT / "start.sh").read_text(encoding="utf-8")
    if launcher.count("LIGHT=0\n") != 1:
        raise ReleaseError("Light launcher selection marker is missing")
    launcher = launcher.replace("LIGHT=0\n", "LIGHT=1\n")
    marker = "PROJECT=$(pick COMPOSE_PROJECT_NAME)\n"
    if launcher.count(marker) != 1:
        raise ReleaseError("Light image guard marker is missing")
    launcher = launcher.replace(
        marker,
        marker
        + f"[[ $ARCH == '{args.architecture}' ]] || fail 'Light bundle architecture mismatch.'\n"
        + f"[[ $APP_IMAGE == \"{args.app_image}\" ]] || fail 'Light app digest mismatch.'\n",
    )
    defaults = (ROOT / "light.env.example").read_text(encoding="utf-8")
    defaults = re.sub(
        r"^DAYLOOM_APP_IMAGE=.*$",
        f"DAYLOOM_APP_IMAGE={args.app_image}",
        defaults,
        flags=re.MULTILINE,
    )
    files = {
        "start.sh": launcher,
        "compose.yaml": (ROOT / "compose.light.yaml").read_text(encoding="utf-8"),
        ".env.example": "# DAYLOOM_LIGHT_RELEASE="
        + json.dumps(metadata, sort_keys=True)
        + "\n"
        + defaults,
        "README.md": f"# Dayloom {args.version} light deployment\n\n"
        f"Source revision: `{args.source_revision}`. Linux {args.architecture}. "
        f"App: `{args.app_image}`.\n\n"
        + (ROOT / "README.light.md").read_text(encoding="utf-8").replace(
            "https://github.com/rplalala/Dayloom/blob/main/",
            f"https://github.com/rplalala/Dayloom/blob/{args.source_revision}/",
        ),
    }
    return {
        **metadata,
        **write_bundle(
            args.output,
            f"dayloom-{args.version}-light-linux-{args.architecture}.tar.gz",
            {name: value.encode("utf-8") for name, value in files.items()},
        ),
        "app_image_bytes": image["Size"],
    }


def verify(args):
    content = read_bundle(args.archive, args.checksum)
    text = content[".env.example"].decode()
    metadata = json.loads(
        next(
            line.removeprefix("# DAYLOOM_LIGHT_RELEASE=")
            for line in text.splitlines()
            if line.startswith("# DAYLOOM_LIGHT_RELEASE=")
        )
    )
    validate(metadata)
    architecture = metadata.get("architecture", "amd64")
    expected_name = f"dayloom-{metadata['version']}-light-linux-{architecture}.tar.gz"
    if Path(args.archive).name != expected_name:
        raise ReleaseError("Light archive filename and metadata version/architecture mismatch")
    # Only instance-independent public scalars belong in the downloadable template.
    values = {}
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator or key in values:
            raise ReleaseError("Invalid light public defaults")
        values[key] = value
    if set(values) != {"DAYLOOM_APP_IMAGE", "DAYLOOM_HOST_PORT", "COMPOSE_PROJECT_NAME"}:
        raise ReleaseError("Light defaults must not include baseline or private settings")
    if values["DAYLOOM_APP_IMAGE"] != metadata["app_image"]:
        raise ReleaseError("Light metadata and app image mismatch")
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build_parser = commands.add_parser("build")
    for name in ("version", "source-revision", "app-image", "output"):
        build_parser.add_argument("--" + name, required=True)
    build_parser.add_argument("--allow-local-images", action="store_true")
    build_parser.add_argument("--architecture", choices=("amd64", "arm64"), default="amd64")
    verify_parser = commands.add_parser("verify")
    verify_parser.add_argument("archive")
    verify_parser.add_argument("--checksum")
    args = parser.parse_args()
    try:
        print(json.dumps(build(args) if args.command == "build" else verify(args), sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, StopIteration, tarfile.TarError) as error:
        print(str(error) if isinstance(error, ReleaseError) else "Invalid light deployment bundle.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
