"""Light releases contain only the app deployment and never inspect baseline images."""

import json
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

from backend.tests.deployment.test_release_package import (  # noqa: F401
    APP,
    ROOT,
    SHA,
    image_boundary,
)


def test_light_bundle_is_pinned_and_verifiable_without_any_baseline(tmp_path, image_boundary):  # noqa: F811
    environment, _, fixture = image_boundary
    docker = fixture.with_name("fake_docker.py")
    source = docker.read_text().replace(
        'if ref == f["app"]: labels.update',
        'labels["io.dayloom.remote-database"]="1"\n if ref == f["app"]: labels.update',
    )
    source = source.replace(
        "a = sys.argv[1:]",
        "a = sys.argv[1:]\n"
        'with pathlib.Path(__file__).with_name("docker-requests.jsonl").open("a") as log:\n'
        ' log.write(json.dumps(a)+"\\n")',
    )
    docker.write_text(source)
    command = [sys.executable, "-m", "deploy.release.light_package"]
    result = subprocess.run(
        command
        + [
            "build",
            "--version",
            "1.2.3",
            "--source-revision",
            SHA,
            "--app-image",
            APP,
            "--output",
            str(tmp_path / "release"),
        ],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    archive = Path(json.loads(result.stdout)["archive"])
    assert archive.name == "dayloom-1.2.3-light-linux-amd64.tar.gz"
    with tarfile.open(archive) as bundle:
        assert set(bundle.getnames()) == {"start.sh", "compose.yaml", ".env.example", "README.md"}
        compose = bundle.extractfile("compose.yaml").read().decode()
        assert "postgres:" not in compose and "init:" not in compose
        assert "LIGHT=1" in bundle.extractfile("start.sh").read().decode()
        defaults = bundle.extractfile(".env.example").read().decode()
        assert APP in defaults and "BASELINE" not in defaults
        guide = bundle.extractfile("README.md").read().decode()
        policy_link = f"https://github.com/rplalala/Dayloom/blob/{SHA}/config/README.md"
        assert policy_link + "#product-rag-policy" in guide
        assert "/blob/HEAD/" not in guide and "/blob/main/" not in guide
    verified = subprocess.run(
        command + ["verify", str(archive)],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert verified.returncode == 0, verified.stderr
    requests = [
        json.loads(line)
        for line in fixture.with_name("docker-requests.jsonl").read_text().splitlines()
    ]
    assert requests == [["image", "inspect", APP]]


def test_light_package_refuses_older_apps_without_remote_support(tmp_path, image_boundary):  # noqa: F811
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "deploy.release.light_package",
            "build",
            "--version",
            "1.2.3",
            "--source-revision",
            SHA,
            "--app-image",
            APP,
            "--output",
            str(tmp_path / "release"),
        ],
        cwd=ROOT,
        env=image_boundary[0],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 2
    assert "remote database support" in result.stdout
    assert not (tmp_path / "release").exists()


def test_arm64_light_bundle_binds_its_platform_and_never_reads_a_baseline(
    tmp_path, image_boundary,  # noqa: F811
):
    environment, _, fixture = image_boundary
    docker = fixture.with_name("fake_docker.py")
    source = docker.read_text().replace('"Architecture":"amd64"', '"Architecture":"arm64"')
    source = source.replace(
        'if ref == f["app"]: labels.update',
        'labels["io.dayloom.remote-database"]="1"\n if ref == f["app"]: labels.update',
    )
    # Inspecting app is the only permitted registry boundary for light packaging.
    source = source.replace('ref=a[2]; labels=', 'ref=a[2]; assert ref == f["app"]; labels=')
    docker.write_text(source)
    command = [sys.executable, "-m", "deploy.release.light_package"]
    built = subprocess.run(
        command + ["build", "--version", "1.2.3", "--source-revision", SHA,
                   "--app-image", APP, "--architecture", "arm64",
                   "--output", str(tmp_path / "release")],
        cwd=ROOT, env=environment, capture_output=True, text=True, timeout=30,
    )
    assert built.returncode == 0, built.stdout + built.stderr
    report = json.loads(built.stdout)
    archive = Path(report["archive"])
    assert archive.name == "dayloom-1.2.3-light-linux-arm64.tar.gz"
    verified = subprocess.run(
        command + ["verify", str(archive)],
        cwd=ROOT, env=environment, capture_output=True, text=True, timeout=30,
    )
    assert verified.returncode == 0, verified.stdout + verified.stderr
    assert json.loads(verified.stdout)["architecture"] == "arm64"
    with tarfile.open(archive) as bundle:
        assert "postgres:" not in bundle.extractfile("compose.yaml").read().decode()
        assert "Linux arm64" in bundle.extractfile("README.md").read().decode()
        bundle.extractall(tmp_path / "extracted", filter="data")
    boundary = tmp_path / "docker"
    boundary.write_text(
        '#!/usr/bin/env bash\ncase "$1" in\n'
        'info) [[ ${2:-} != --format ]] || echo linux/amd64 ;;\n'
        'version) echo 28.0.0 ;;\ncompose) echo --wait-timeout ;;\n'
        '*) exit 71 ;;\nesac\n',
        newline="\n",
    )
    boundary.chmod(0o755)
    git = shutil.which("git")
    windows_bash = Path(git).parent.parent / "bin/bash.exe" if git else Path("missing")
    bash = str(windows_bash) if windows_bash.is_file() else shutil.which("bash")
    if not bash:
        pytest.skip("Bash is required for the extracted bundle architecture guard")
    launched = subprocess.run(
        [bash, "start.sh", "--non-interactive"],
        cwd=tmp_path / "extracted", env=environment, capture_output=True, text=True, timeout=30,
    )
    assert launched.returncode == 1, launched.stdout + launched.stderr
    assert "bundle architecture mismatch" in launched.stderr
    assert not (tmp_path / "extracted/config").exists()


@pytest.mark.parametrize("architecture", ["amd64", "arm64"])
def test_light_bundle_refuses_an_image_for_the_other_architecture(
    tmp_path, image_boundary, architecture,  # noqa: F811
):
    docker = image_boundary[2].with_name("fake_docker.py")
    source = docker.read_text().replace(
        '"Architecture":"amd64"',
        '"Architecture":"arm64"' if architecture == "amd64" else '"Architecture":"amd64"',
    )
    source = source.replace(
        'if ref == f["app"]: labels.update',
        'labels["io.dayloom.remote-database"]="1"\n if ref == f["app"]: labels.update',
    )
    docker.write_text(source)
    result = subprocess.run(
        [sys.executable, "-m", "deploy.release.light_package", "build",
         "--version", "1.2.3", "--source-revision", SHA, "--app-image", APP,
         "--architecture", architecture, "--output", str(tmp_path / "release")],
        cwd=ROOT, env=image_boundary[0], capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 2
    assert "architecture" in result.stdout
    assert not (tmp_path / "release").exists()


def test_original_amd64_light_metadata_remains_verifiable(tmp_path):
    from deploy.release.package import write_bundle

    metadata = {"format": "dayloom-light-release-v1", "version": "0.2.0",
                "source_revision": SHA, "app_image": APP}
    files = {
        ".env.example": (
            "# DAYLOOM_LIGHT_RELEASE=" + json.dumps(metadata) + "\n"
            + f"DAYLOOM_APP_IMAGE={APP}\n"
            + "DAYLOOM_HOST_PORT=5173\nCOMPOSE_PROJECT_NAME=dayloom-light\n"
        ).encode(),
        "start.sh": b"LIGHT=1\n",
        "compose.yaml": b"services: {}\n",
        "README.md": b"Original amd64 bundle\n",
    }
    result = write_bundle(tmp_path, "dayloom-0.2.0-light-linux-amd64.tar.gz", files)
    verified = subprocess.run(
        [sys.executable, "-m", "deploy.release.light_package", "verify", result["archive"]],
        cwd=ROOT, capture_output=True, text=True, timeout=30,
    )
    assert verified.returncode == 0, verified.stdout + verified.stderr
    assert json.loads(verified.stdout) == metadata
