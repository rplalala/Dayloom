"""Exercise the Bash installer with controlled download and launcher boundaries."""

import hashlib
import io
import os
import shutil
import subprocess
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def installation(tmp_path):
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    commands = tmp_path / "bin"
    commands.mkdir()
    files = {
        "start.sh": b'#!/usr/bin/env bash\nprintf "%s\\n" "$PWD" "$*" > launched.txt\n',
        "compose.yaml": b"services: {}\n",
        ".env.example": b"PUBLIC=value\n",
        "README.md": b"Controlled deployment bundle\n",
    }
    archive = fixtures / "dayloom-2.7.3-linux-amd64.tar.gz"
    with tarfile.open(archive, "w:gz") as bundle:
        for name, data in files.items():
            member = tarfile.TarInfo(name)
            member.size = len(data)
            bundle.addfile(member, io.BytesIO(data))
    entries = {archive.name: archive.read_bytes(), **files}
    archive.with_name(archive.name + ".sha256").write_bytes(
        "".join(
            f"{hashlib.sha256(data).hexdigest()}  {name}\n" for name, data in entries.items()
        ).encode()
    )
    curl = commands / "curl"
    curl.write_text("""#!/usr/bin/env bash
set -eu
output=
url=
while (($#)); do
  case "$1" in
    --output) output=$2; shift 2 ;;
    https://*) url=$1; shift ;;
    *) shift ;;
  esac
done
if [[ $url == https://github.com/rplalala/Dayloom/releases/latest ]]; then
  printf '%s' "${LATEST_URL:-https://github.com/rplalala/Dayloom/releases/tag/dayloom-v2.7.3}"
elif [[ $url == https://github.com/rplalala/Dayloom/releases/download/dayloom-v2.7.3/* ]]; then
  [[ ${FAIL_DOWNLOAD:-0} == 0 ]] || exit 22
  cp "$FIXTURE_DIR/${url##*/}" "$output"
else
  exit 99
fi
""")
    curl.chmod(0o755)
    work = tmp_path / "install space"
    work.mkdir()
    env = {
        k: v
        for k, v in os.environ.items()
        if k.upper() in {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "COMSPEC", "PATHEXT"}
    }
    env["TEST_COMMAND_DIR"] = (
        "/" + commands.drive[0].lower() + commands.as_posix()[2:]
        if os.name == "nt"
        else str(commands)
    )
    env["FIXTURE_DIR"] = fixtures.as_posix()
    return work, fixtures, env


def install(installation):
    work, _, env = installation
    git = shutil.which("git")
    windows_bash = Path(git).parent.parent / "bin/bash.exe" if git else Path("missing")
    bash = str(windows_bash) if windows_bash.is_file() else shutil.which("bash")
    if not bash:
        pytest.skip("Bash is required for the installer entry point")
    return subprocess.run(
        [bash, "-s", "--"],
        input='export PATH="$TEST_COMMAND_DIR:$PATH"\n' + (ROOT / "deploy/install.sh").read_text(),
        cwd=work,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )


def test_latest_install_from_piped_script_preserves_bundle_and_starts(installation):
    work, _, _ = installation
    result = install(installation)
    assert result.returncode == 0, result.stdout + result.stderr
    destination = work / "dayloom"
    assert (destination / "compose.yaml").read_text() == "services: {}\n"
    assert (destination / "launched.txt").read_text().splitlines()[-1] == "--non-interactive"
    assert "2.7.3" in result.stdout


def test_existing_instance_is_not_overwritten(installation):
    work, _, _ = installation
    existing = work / "dayloom"
    existing.mkdir()
    config = existing / ".env"
    config.write_text("Keep installed credentials")
    result = install(installation)
    assert result.returncode != 0
    assert "already exists" in result.stderr
    assert config.read_text() == "Keep installed credentials"
    assert sorted(p.name for p in existing.iterdir()) == [".env"]


@pytest.mark.parametrize("corruption", ["archive", "extracted_file"])
def test_checksum_failure_never_starts_the_application(installation, corruption):
    work, fixtures, _ = installation
    archive = fixtures / "dayloom-2.7.3-linux-amd64.tar.gz"
    if corruption == "archive":
        archive.write_bytes(archive.read_bytes() + b"corrupt")
    else:
        checksum = archive.with_name(archive.name + ".sha256")
        checksum.write_bytes(
            checksum.read_bytes().replace(
                hashlib.sha256(b"services: {}\n").hexdigest().encode(), b"0" * 64
            )
        )
    result = install(installation)
    assert result.returncode != 0
    assert not (work / "dayloom/launched.txt").exists()
    assert "FAILED" in result.stdout + result.stderr
    if corruption == "archive":
        assert not (work / "dayloom/start.sh").exists()


def test_failed_download_never_extracts_or_starts(installation):
    work, _, env = installation
    env["FAIL_DOWNLOAD"] = "1"
    result = install(installation)
    assert result.returncode != 0
    assert not (work / "dayloom/start.sh").exists()


def test_unexpected_latest_tag_creates_no_installation(installation):
    work, _, env = installation
    env["LATEST_URL"] = "https://github.com/rplalala/Dayloom/releases/tag/unrelated"
    result = install(installation)
    assert result.returncode != 0
    assert "supported Dayloom version" in result.stderr
    assert not (work / "dayloom").exists()
