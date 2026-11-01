"""Local preparation keeps release integrity and existing resources intact."""

import hashlib
import subprocess
from types import SimpleNamespace

import pytest


def release_at(root):
    release = root / "release"
    files = {
        "tripworld.pgcustom": b"dump fixture",
        "runtime/artifacts/retrieval_entities.parquet.manifest.json": b'{"source":"fixture"}',
        "runtime/reports/phase5_embedding_run.json": b'{"status":"fixture"}',
    }
    checksums = []
    for name, content in files.items():
        target = release / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        checksums.append(hashlib.sha256(content).hexdigest() + "  " + name)
    (release / "SHA256SUMS.txt").write_text("\n".join(checksums))
    return release


def test_corrupt_release_is_rejected_before_installation(tmp_path, capsys):
    from backend.cli.dayloom import main

    release = release_at(tmp_path)
    (release / "tripworld.pgcustom").write_bytes(b"corrupt")
    source = tmp_path / "source"
    assert main(["prepare", str(release)], root=source) == 2
    assert "Checksum mismatch" in capsys.readouterr().err
    assert not source.exists()


def test_verified_sidecars_install_once_and_conflicts_are_preserved(tmp_path):
    from backend.cli.dayloom import main

    release = release_at(tmp_path)
    source = tmp_path / "source"
    for _ in range(2):
        assert main(["prepare", str(release)], root=source) == 0
    target = source / "data/tripworld/reports/phase5_embedding_run.json"
    assert target.read_bytes() == b'{"status":"fixture"}'
    target.write_bytes(b"existing installation")
    assert main(["prepare", str(release)], root=source) == 2
    assert target.read_bytes() == b"existing installation"
    assert (release / "tripworld.pgcustom").read_bytes() == b"dump fixture"


def test_offline_tokenizer_preparation_never_downloads(tmp_path, monkeypatch, capsys):
    import httpx

    from backend.cli.dayloom import main

    def blocked(*args, **kwargs):
        raise AssertionError("Offline preparation must not download vocabularies")

    monkeypatch.setattr(httpx, "get", blocked)
    assert main(["tokenizers", "--offline"], root=tmp_path) == 2
    assert "vocabulary" in capsys.readouterr().err.lower()
    assert not list(tmp_path.rglob("*.tmp"))


def test_database_restore_refuses_existing_data(tmp_path, monkeypatch, capsys):
    from backend.cli.dayloom import main

    def existing(command, **kwargs):
        assert "pg_restore" not in command, "An existing database must not receive a dump"
        return SimpleNamespace(returncode=0, stdout="t\n")

    monkeypatch.setenv("DAYLOOM_DB_URL", "postgresql://review:fixture@127.0.0.1:55432/review")
    monkeypatch.setattr(subprocess, "run", existing)
    release = release_at(tmp_path)
    assert main(["restore", str(release)], root=tmp_path) == 2
    assert "empty database" in capsys.readouterr().err


def test_restore_checks_and_imports_the_same_container_database(tmp_path, monkeypatch):
    from backend.cli.dayloom import main

    operations = []

    def docker(command, **kwargs):
        operations.append(command)
        if "psql" in command:
            return SimpleNamespace(returncode=0, stdout="f\n")
        assert kwargs["stdin"].read() == b"dump fixture"
        assert "--single-transaction" in command
        assert "--clean" not in command
        return SimpleNamespace(returncode=0)

    monkeypatch.setenv("DAYLOOM_DB_URL", "postgresql://review:fixture@127.0.0.1:55432/review")
    monkeypatch.setattr(subprocess, "run", docker)
    assert main(["restore", str(release_at(tmp_path))], root=tmp_path) == 0
    assert len(operations) == 2
    for command in operations:
        assert command[:4] == ["docker", "exec", "-i", "postgres"]
        assert command[command.index("--dbname") + 1] == "review"
        assert command[command.index("--username") + 1] == "review"


def test_launcher_forwards_database_arguments_and_exit_status(tmp_path, capfd):
    from backend.cli.dayloom import main

    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "run_database.py").write_text(
        "import sys\nprint('|'.join(sys.argv[1:]))\nraise SystemExit(17)\n"
    )
    assert main(["db", "up", "-d", "--wait", "postgres"], root=tmp_path) == 17
    assert capfd.readouterr().out.strip() == "up|-d|--wait|postgres"


@pytest.mark.parametrize("name", ["../private.txt", "runtime/../../private.txt"])
def test_release_manifest_cannot_read_outside_its_directory(tmp_path, name, capsys):
    from backend.cli.dayloom import main

    release = release_at(tmp_path)
    private = tmp_path / "private.txt"
    private.write_bytes(b"private fixture")
    with (release / "SHA256SUMS.txt").open("a") as stream:
        stream.write("\n" + hashlib.sha256(private.read_bytes()).hexdigest() + "  " + name)
    source = tmp_path / "source"
    assert main(["prepare", str(release)], root=source) == 2
    assert "invalid release file" in capsys.readouterr().err
    assert not source.exists()


def test_downloaded_vocabulary_is_checked_before_replacing_a_cache(tmp_path, monkeypatch):
    import httpx

    from backend.cli.dayloom import main

    existing = tmp_path / ".cache/tokenizer/fb374d419588a4632f3f557e76b4b70aebbca790"
    existing.parent.mkdir(parents=True)
    existing.write_bytes(b"original cache")
    response = httpx.Response(
        200, content=b"invalid download", request=httpx.Request("GET", "https://fixture.test")
    )
    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: response)
    assert main(["tokenizers"], root=tmp_path) == 2
    assert existing.read_bytes() == b"original cache"
    assert not list(tmp_path.rglob("*.tmp"))
