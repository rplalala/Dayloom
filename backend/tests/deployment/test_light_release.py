"""Light releases contain only the app deployment and never inspect baseline images."""

import json
import subprocess
import sys
import tarfile
from pathlib import Path

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
