"""Deployment release CLI behavior using a controlled Docker process boundary."""

import hashlib
import io
import json
import os
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SHA = "a" * 40
APP = "ghcr.io/rplalala/dayloom-app@sha256:" + "1" * 64
BASE = "ghcr.io/rplalala/dayloom-baseline@sha256:" + "2" * 64
SIDECARS = (
    "artifacts/retrieval_entities.parquet.manifest.json",
    "reports/phase5_embedding_run.json",
)


def cli(*args, environment=None):
    return subprocess.run(
        [sys.executable, "-m", "deploy.release.package", *map(str, args)],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )


@pytest.fixture
def image_boundary(tmp_path):
    resources = {name: b'{"status":"complete"}\n' for name in SIDECARS}
    manifest = {
        "format": "dayloom-baseline-v1",
        "source_revision": SHA,
        "database": {"schema_sha256": "c" * 64},
        "files": {
            "runtime/" + name: {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
            for name, data in resources.items()
        },
    }
    # Independent fixture identity of the exact manifest supplied to the image boundary.
    manifest["baseline_id"] = hashlib.sha256(
        json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()
    fixture = tmp_path / "images.json"
    fixture.write_text(
        json.dumps(
            {
                "manifest": manifest,
                "resources": {key: value.decode() for key, value in resources.items()},
                "app": APP,
                "baseline": BASE,
            }
        )
    )
    script = tmp_path / "fake_docker.py"
    script.write_text("""import json, pathlib, sys
f = json.loads(pathlib.Path(__file__).with_name("images.json").read_text())
a = sys.argv[1:]
if a[:2] == ["image", "inspect"]:
 ref=a[2]; labels={"org.opencontainers.image.source":"https://github.com/rplalala/Dayloom",
                  "org.opencontainers.image.version":"baseline-20261102",
                  "io.dayloom.baseline.id":f["manifest"]["baseline_id"]}
 if ref == f["app"]: labels.update({"org.opencontainers.image.revision":"a"*40,
                                   "org.opencontainers.image.version":"1.2.3"})
 print(json.dumps([{"RepoDigests":[ref],"Os":"linux","Architecture":"amd64","Size":12345,"Config":{"Labels":labels,"Env":[]}}]))
elif a[0] == "create": print("app" if a[-1] == f["app"] else "baseline")
elif a[0] == "cp":
 target=pathlib.Path(a[2]); path=a[1].split(":",1)[1]
 if path == "/baseline/baseline.json": target.write_text(json.dumps(f["manifest"]))
 else:
  key=path.split("/data/tripworld/")[1]; target.write_bytes(f["resources"][key].encode())
elif a[0] != "rm": sys.exit(3)
""")
    executable = tmp_path / ("docker.cmd" if os.name == "nt" else "docker")
    if os.name == "nt":
        executable.write_text(f'@"{sys.executable}" "{script}" %*\n')
    else:
        executable.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{script}" "$@"\n')
        executable.chmod(0o755)
    allowed = {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "COMSPEC", "PATHEXT"}
    environment = {k: v for k, v in os.environ.items() if k.upper() in allowed}
    environment["PATH"] = str(tmp_path) + os.pathsep + os.environ["PATH"]
    environment["PYTHONPATH"] = str(ROOT)
    environment["TEMP"] = environment["TMP"] = str(tmp_path)
    return environment, manifest, fixture


def build(tmp_path, image_boundary, *extra):
    environment, manifest, _ = image_boundary
    return cli(
        "build",
        "--version",
        "1.2.3",
        "--source-revision",
        SHA,
        "--app-image",
        APP,
        "--baseline-image",
        BASE,
        "--baseline-id",
        manifest["baseline_id"],
        "--output",
        tmp_path / "release",
        *extra,
        environment=environment,
    )


def test_release_archive_is_reproducible_four_files_and_verified_without_checkout(
    tmp_path, image_boundary
):
    result = build(tmp_path, image_boundary)
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    archive = Path(report["archive"])
    with tarfile.open(archive) as bundle:
        assert set(bundle.getnames()) == {"compose.yaml", ".env.example", "start.sh", "README.md"}
        defaults = bundle.extractfile(".env.example").read().decode()
        assert f"DAYLOOM_APP_IMAGE={APP}" in defaults
        assert "1.2.3" in bundle.extractfile("README.md").read().decode()
        assert all(member.isfile() for member in bundle.getmembers())
    verified = cli("verify", archive, environment=image_boundary[0])
    assert verified.returncode == 0, verified.stderr
    assert json.loads(verified.stdout)["baseline_id"] == image_boundary[1]["baseline_id"]
    repeated = build(tmp_path, image_boundary, "--output", tmp_path / "release-again")
    assert repeated.returncode == 0, repeated.stderr
    assert archive.read_bytes() == Path(json.loads(repeated.stdout)["archive"]).read_bytes()
    assert build(tmp_path, image_boundary).returncode == 2


@pytest.mark.parametrize("change", ["revision", "resource", "digest", "secret", "baseline_label"])
def test_release_rejects_mismatched_or_secret_image_inputs(tmp_path, image_boundary, change):
    _, _, fixture = image_boundary
    data = json.loads(fixture.read_text())
    if change == "resource":
        data["resources"][SIDECARS[0]] = "tampered"
    script = fixture.with_name("fake_docker.py")
    source = script.read_text()
    if change == "revision":
        source = source.replace(
            '"org.opencontainers.image.revision":"a"*40',
            '"org.opencontainers.image.revision":"b"*40',
        )
    if change == "digest":
        source = source.replace('"RepoDigests":[ref]', '"RepoDigests":["other@sha256:"+"3"*64]')
    if change == "baseline_label":
        source = source.replace(
            '"io.dayloom.baseline.id":f["manifest"]["baseline_id"]',
            '"io.dayloom.baseline.id":"8"*64',
        )
    if change == "secret":
        source = source.replace('"Env":[]', '"Env":["OPENAI_API_KEY=controlled-secret"]')
    script.write_text(source)
    fixture.write_text(json.dumps(data))
    result = build(tmp_path, image_boundary)
    assert result.returncode == 2
    assert "controlled-secret" not in result.stdout + result.stderr
    assert not (tmp_path / "release").exists()


def test_release_verification_rejects_tampering_and_traversal_even_with_rewritten_checksums(
    tmp_path, image_boundary
):
    result = build(tmp_path, image_boundary)
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    archive = Path(report["archive"])
    with archive.open("ab") as stream:
        stream.write(b"tampered")
    assert cli("verify", archive).returncode == 2
    with tarfile.open(archive, "w:gz") as bundle:
        member = tarfile.TarInfo("../escaped")
        member.size = 1
        bundle.addfile(member, io.BytesIO(b"x"))
    checksums = Path(report["checksum"])
    lines = checksums.read_text().splitlines()
    lines[0] = hashlib.sha256(archive.read_bytes()).hexdigest() + "  " + archive.name
    checksums.write_text("\n".join(lines) + "\n")
    assert cli("verify", archive).returncode == 2
    assert not (tmp_path / "escaped").exists()


def test_explicit_resource_archive_rejects_extra_private_inputs_before_extract(tmp_path):
    archive = tmp_path / "resources.tar.gz"
    with tarfile.open(archive, "w:gz") as bundle:
        member = tarfile.TarInfo(".env")
        member.size = 23
        bundle.addfile(member, io.BytesIO(b"OPENAI_API_KEY=not-real\n"))
    result = cli(
        "resources",
        "--archive",
        archive,
        "--sha256",
        hashlib.sha256(archive.read_bytes()).hexdigest(),
        "--output",
        tmp_path / "out",
    )
    assert result.returncode == 2
    assert "not-real" not in result.stdout + result.stderr
    assert not (tmp_path / "out").exists()


def test_resource_archive_is_verified_and_extracted_as_an_explicit_build_context(tmp_path):
    archive = tmp_path / "resources.tar.gz"
    names = [
        ".cache/tokenizer/fb374d419588a4632f3f557e76b4b70aebbca790",
        "data/tripworld/tokenizer_cache/9b5ad71b2ce5302211f9c61530b329a4922fc6a4",
        *("data/tripworld/" + name for name in SIDECARS),
    ]
    with tarfile.open(archive, "w:gz") as bundle:
        for name in names:
            member = tarfile.TarInfo(name)
            member.size = 2
            bundle.addfile(member, io.BytesIO(b"{}"))
    result = cli(
        "resources",
        "--archive",
        archive,
        "--sha256",
        hashlib.sha256(archive.read_bytes()).hexdigest(),
        "--output",
        tmp_path / "out",
    )
    assert result.returncode == 0, result.stderr
    assert {
        p.relative_to(tmp_path / "out").as_posix()
        for p in (tmp_path / "out").rglob("*")
        if p.is_file()
    } == set(names)


def test_explicit_input_check_compares_resources_with_selected_baseline(tmp_path, image_boundary):
    environment, _, _ = image_boundary
    resources = tmp_path / "resources"
    names = [
        ".cache/tokenizer/fb374d419588a4632f3f557e76b4b70aebbca790",
        "data/tripworld/tokenizer_cache/9b5ad71b2ce5302211f9c61530b329a4922fc6a4",
        *("data/tripworld/" + name for name in SIDECARS),
    ]
    for name in names:
        target = resources / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b'{"status":"complete"}\n')
    result = cli(
        "check-inputs", "--resources", resources, "--baseline-image", BASE, environment=environment
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["baseline_id"] == image_boundary[1]["baseline_id"]
    floating = cli(
        "check-inputs",
        "--resources",
        resources,
        "--baseline-image",
        "dayloom-baseline:latest",
        environment=environment,
    )
    assert floating.returncode == 2
    (resources / names[-1]).write_bytes(b"changed")
    assert (
        cli(
            "check-inputs",
            "--resources",
            resources,
            "--baseline-image",
            BASE,
            environment=environment,
        ).returncode
        == 2
    )


def test_extracted_entry_rejects_mixed_release_before_creating_private_configuration(
    tmp_path, image_boundary
):
    import shutil

    git = shutil.which("git")
    windows_bash = Path(git).parent.parent / "bin/bash.exe" if git else Path("missing")
    bash = str(windows_bash) if windows_bash.is_file() else shutil.which("bash")
    if not bash:
        pytest.skip("Bash is required for the extracted-entry seam")
    result = build(tmp_path, image_boundary)
    assert result.returncode == 0, result.stderr
    extracted = tmp_path / "extracted"
    with tarfile.open(json.loads(result.stdout)["archive"]) as bundle:
        bundle.extractall(extracted, filter="data")
    boundary = tmp_path / "docker"
    boundary.write_text(
        """#!/usr/bin/env bash
case "$1" in
 info) if [[ ${2:-} == --format ]]; then echo linux/amd64; fi ;;
 version) echo 28.0.0 ;;
 compose) echo --wait-timeout ;;
 *) echo 'Unexpected Docker operation' >&2; exit 71 ;;
esac
""",
        newline="\n",
    )
    boundary.chmod(0o755)
    environment = dict(
        image_boundary[0], DAYLOOM_APP_IMAGE="ghcr.io/rplalala/dayloom-app@sha256:" + "7" * 64
    )
    run = subprocess.run(
        [bash, str(extracted / "start.sh"), "--non-interactive"],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert run.returncode == 1, run.stderr
    assert "Release identity mismatch" in run.stderr
    assert not (extracted / "config").exists()


def test_release_verifier_rejects_private_configuration_even_with_consistent_checksums(
    tmp_path, image_boundary
):
    result = build(tmp_path, image_boundary)
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    archive = Path(report["archive"])
    with tarfile.open(archive) as bundle:
        files = {member.name: bundle.extractfile(member).read() for member in bundle}
    files[".env.example"] += b"OPENAI_API_KEY=controlled-private-value\n"
    with tarfile.open(archive, "w:gz") as bundle:
        for name, content in files.items():
            member = tarfile.TarInfo(name)
            member.size = len(content)
            bundle.addfile(member, io.BytesIO(content))
    checksums = {
        archive.name: hashlib.sha256(archive.read_bytes()).hexdigest(),
        **{name: hashlib.sha256(value).hexdigest() for name, value in files.items()},
    }
    Path(report["checksum"]).write_text(
        "".join(f"{value}  {name}\n" for name, value in checksums.items())
    )
    verified = cli("verify", archive)
    assert verified.returncode == 2
    assert "controlled-private-value" not in verified.stdout + verified.stderr


def test_archive_filename_must_match_the_embedded_release_version(tmp_path, image_boundary):
    result = build(tmp_path, image_boundary)
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    original = Path(report["archive"])
    renamed = original.with_name("dayloom-9.9.9-linux-amd64.tar.gz")
    original.rename(renamed)
    checksum = Path(report["checksum"])
    checksum.write_text(checksum.read_text().replace(original.name, renamed.name))
    assert cli("verify", renamed, "--checksum", checksum).returncode == 2
