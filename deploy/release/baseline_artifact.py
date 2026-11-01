"""Integrity and format validation for a complete database baseline."""

import hashlib
import json
import re
from pathlib import Path

FORMAT = "dayloom-baseline-v1"
SIDECARS = (
    "artifacts/retrieval_entities.parquet.manifest.json",
    "reports/phase5_embedding_run.json",
)


class BaselineError(ValueError):
    """An actionable error whose message contains no database credentials."""


def sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def manifest_identity(manifest):
    content = {key: value for key, value in manifest.items() if key != "baseline_id"}
    return hashlib.sha256(canonical(content).encode()).hexdigest()


def verify_release(directory, expected_id=None):
    root = Path(directory).resolve()
    entries = {}
    for line in (root / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            digest, name = line.split(maxsplit=1)
        except ValueError:
            raise BaselineError("Invalid checksum manifest") from None
        if not re.fullmatch("[a-f0-9]{64}", digest) or name in entries:
            raise BaselineError("Invalid or duplicate checksum entry")
        path = (root / name).resolve()
        if (not path.is_relative_to(root) or not path.is_file()
                or any(part == ".." for part in Path(name).parts)):
            raise BaselineError("Invalid baseline file path")
        if sha256(path) != digest:
            raise BaselineError("Baseline checksum mismatch")
        entries[name] = digest
    required = {"database.pgcustom", "baseline.json", *("runtime/" + p for p in SIDECARS)}
    if not required <= entries.keys():
        raise BaselineError("Checksum manifest omits required baseline files")
    if not any(name.startswith("notices/") for name in entries):
        raise BaselineError("Baseline provenance notices are required")
    manifest = json.loads((root / "baseline.json").read_text(encoding="utf-8"))
    if manifest.get("format") != FORMAT:
        raise BaselineError("Unsupported baseline format")
    if manifest.get("baseline_id") != manifest_identity(manifest):
        raise BaselineError("Baseline manifest identity mismatch")
    if expected_id is not None and manifest.get("baseline_id") != expected_id:
        raise BaselineError("Baseline identity mismatch")
    files = manifest.get("files", {})
    if set(files) != set(entries) - {"baseline.json"}:
        raise BaselineError("Baseline file inventory mismatch")
    for name, record in files.items():
        if (record.get("sha256") != entries[name]
                or record.get("bytes") != (root / name).stat().st_size):
            raise BaselineError("Baseline file identity mismatch")
    actual_files = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    if actual_files != set(entries) | {"SHA256SUMS.txt"}:
        raise BaselineError("Unlisted files in baseline directory")
    if any(p.is_symlink() for p in root.rglob("*")):
        raise BaselineError("Symlinks are not baseline artifacts")
    build = json.loads((root / "runtime" / SIDECARS[1]).read_text(encoding="utf-8"))
    if build.get("status") != "complete":
        raise BaselineError("Baseline requires complete retrieval metadata")
    return manifest
