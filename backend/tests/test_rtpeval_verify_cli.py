"""Published verification through the command boundary, with network denied."""

import shutil
from pathlib import Path

import pytest

from backend.tests.test_rtpeval_cli import installed_cli as cli_fixture

installed_cli = cli_fixture

ROOT = Path(__file__).resolve().parents[2]


def test_published_benchmark_verifies_offline(installed_cli):
    result = installed_cli("verify")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Verified 12 cases, 48 finals" in result.stdout
    assert "24 confirmed answers" in result.stdout


@pytest.mark.parametrize(
    "case,change,expected_status,diagnostic",
    [
        ("case-01", "append", 2, "public byte length mismatch"),
        ("case-07", "same_length", 2, "public sha256 mismatch"),
        ("case-01", "crlf", 0, "Verified 12 cases"),
    ],
)
def test_published_reader_integrity(
    installed_cli, tmp_path, case, change, expected_status, diagnostic
):
    shutil.copytree(
        ROOT / "benchmark",
        tmp_path / "benchmark",
        ignore=shutil.ignore_patterns("scratch", "__pycache__"),
    )
    command = tmp_path / "backend/cli/verify.py"
    command.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / "backend/cli/verify.py", command)
    report = tmp_path / "benchmark" / case / "report.md"
    original = report.read_bytes()
    if change == "append":
        report.write_bytes(original + b"\nChanged public reader.\n")
    elif change == "same_length":
        assert b"Paris" in original
        report.write_bytes(original.replace(b"Paris", b"PARIS", 1))
    else:
        report.write_bytes(original.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
    result = installed_cli(
        "import runpy; raise SystemExit(runpy.run_path(" + repr(str(command)) + ')["main"]([]))',
        probe=True,
    )
    assert result.returncode == expected_status, result.stdout + result.stderr
    assert diagnostic in result.stdout
    if expected_status:
        assert "FAIL verify_automatic.py" in result.stdout
        assert case in result.stdout
    assert "24 confirmed answers" in result.stdout
