"""Release integrity is checked through the public deployment command."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def run_cli(*args, **kwargs):
    return subprocess.run(
        [sys.executable, "-m", "deploy.release.baseline", *map(str, args)],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
        env={**os.environ, "PYTHONPATH": str(ROOT)}, **kwargs,
    )


def test_invalid_release_fails_without_exposing_a_database_secret(tmp_path):
    (tmp_path / "SHA256SUMS.txt").write_text("0" * 64 + "  database.pgcustom\n")
    (tmp_path / "database.pgcustom").write_bytes(b"corrupt backup")
    result = run_cli("verify", tmp_path)
    assert result.returncode == 2
    assert "checksum" in result.stderr.lower()
    assert "Traceback" not in result.stderr


def release_at(root):
    files = {
        "database.pgcustom": b"controlled archive",
        "runtime/artifacts/retrieval_entities.parquet.manifest.json": (
            b'{"output_sha256":"fixture"}'
        ),
        "runtime/reports/phase5_embedding_run.json": b'{"status":"complete"}',
        "notices/NOTICE.txt": b"Controlled test baseline",
    }
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    manifest = {
        "format": "dayloom-baseline-v1", "source_revision": "1" * 40,
        "captured_at": "2026-11-02T00:00:00+00:00",
        "database": {"server_major": 17, "extensions": [{
            "name": "vector", "version": "0.8.2", "schema": "tripworld",
        }], "schemas": ["app", "public", "tripworld"], "tables": {},
            "schema_sha256": "a" * 64},
        "files": {name: {"sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)}
                  for name, content in files.items()},
    }
    encoded = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    manifest["baseline_id"] = hashlib.sha256(encoded.encode()).hexdigest()
    (root / "baseline.json").write_text(json.dumps(manifest), encoding="utf-8")
    write_checksums(root)
    return manifest


def write_checksums(root):
    paths = sorted(p for p in root.rglob("*") if p.is_file() and p.name != "SHA256SUMS.txt")
    (root / "SHA256SUMS.txt").write_text("".join(
        hashlib.sha256(path.read_bytes()).hexdigest() + "  " + path.relative_to(root).as_posix()
        + "\n" for path in paths
    ), encoding="utf-8")


def test_verified_release_reports_immutable_identity(tmp_path):
    manifest = release_at(tmp_path)
    result = run_cli("verify", tmp_path, "--expect-id", manifest["baseline_id"])
    assert result.returncode == 0
    assert json.loads(result.stdout)["baseline_id"] == manifest["baseline_id"]


def test_changed_manifest_is_rejected_even_if_file_checksums_are_updated(tmp_path):
    manifest = release_at(tmp_path)
    manifest["source_revision"] = "2" * 40
    (tmp_path / "baseline.json").write_text(json.dumps(manifest), encoding="utf-8")
    write_checksums(tmp_path)
    result = run_cli("verify", tmp_path)
    assert result.returncode == 2
    assert "identity" in result.stderr.lower()
