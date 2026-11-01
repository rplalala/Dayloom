"""Explicit local resource preparation, separate from planner/provider execution."""

import hashlib
import subprocess
from pathlib import Path
from uuid import uuid4

SIDECARS = (
    "artifacts/retrieval_entities.parquet.manifest.json",
    "reports/phase5_embedding_run.json",
)


def verify_release(release):
    release = Path(release).resolve()
    manifest = release / "SHA256SUMS.txt"
    verified = set()
    for line in manifest.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        expected, name = line.split(maxsplit=1)
        name = name.removeprefix("*")
        path = (release / name).resolve()
        if not path.is_relative_to(release) or not path.is_file():
            raise ValueError(f"Missing or invalid release file: {name}")
        with path.open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        if actual != expected.lower():
            raise ValueError(f"Checksum mismatch: {name}")
        verified.add(name)
    required = {"tripworld.pgcustom", *("runtime/" + name for name in SIDECARS)}
    if not required.issubset(verified):
        raise ValueError("Release manifest must include the dump and both runtime sidecars")
    return release


def prepare_release(release, root):
    release = verify_release(release)
    copies = [(release / "runtime" / name, root / "data/tripworld" / name) for name in SIDECARS]
    for source, target in copies:
        if target.exists() and target.read_bytes() != source.read_bytes():
            raise ValueError(f"Existing resource differs: {target.relative_to(root)}")
    for source, target in copies:
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            with target.open("xb") as stream:
                stream.write(source.read_bytes())
    print("Release checksums verified; both retrieval sidecars are ready.")


def prepare_tokenizers(root, *, offline=False):
    import httpx

    from backend.app.runtime.token_counting import VOCAB_SHA256, VOCAB_URL
    from backend.app.tripworld.retrieval.query_tokens import SHA256, URL

    pending = []
    for directory, url, expected in (
        (root / ".cache/tokenizer", VOCAB_URL, VOCAB_SHA256),
        (root / "data/tripworld/tokenizer_cache", URL, SHA256),
    ):
        target = directory / hashlib.sha1(url.encode()).hexdigest()
        if target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest() == expected:
            continue
        if offline:
            raise ValueError(f"Missing or invalid vocabulary: {target.relative_to(root)}")
        response = httpx.get(url, timeout=30)
        response.raise_for_status()
        if hashlib.sha256(response.content).hexdigest() != expected:
            raise ValueError("Downloaded vocabulary checksum mismatch")
        pending.append((target, response.content))
    for target, content in pending:
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.name + "." + uuid4().hex + ".tmp")
        try:
            temporary.write_bytes(content)
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
    print("Both tokenizer vocabularies verified; no model or embedding calls.")


def restore_database(release):
    from backend.app.runtime.database import DatabaseSettings

    release = verify_release(release)
    settings = DatabaseSettings()
    parameters = settings.connection_parameters()
    if parameters.get("host") not in {"127.0.0.1", "localhost"}:
        raise ValueError("The Docker restore command requires the local Compose database")
    target = ["docker", "exec", "-i", "postgres"]
    identity = ["--username", str(parameters["user"]), "--dbname", str(parameters["dbname"])]
    inspection = subprocess.run(
        [
            *target,
            "psql",
            *identity,
            "--no-psqlrc",
            "--tuples-only",
            "--no-align",
            "--command",
            "SELECT EXISTS (SELECT 1 FROM pg_namespace "
            "WHERE nspname NOT IN ('public', 'information_schema') AND nspname !~ '^pg_') "
            "OR EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p', 'v', 'm', 'S', 'f'))",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if inspection.returncode or inspection.stdout.strip() not in {"f", "t"}:
        raise ValueError(
            "Cannot inspect the local Compose database; check its settings and startup"
        )
    if inspection.stdout.strip() == "t":
        raise ValueError("Restore requires an empty database; existing data was preserved")
    with (release / "tripworld.pgcustom").open("rb") as stream:
        result = subprocess.run(
            [
                *target,
                "pg_restore",
                "--exit-on-error",
                "--single-transaction",
                "--no-owner",
                "--no-privileges",
                *identity,
            ],
            stdin=stream,
            check=False,
        )
    if result.returncode:
        raise ValueError("Database restore failed; inspect the pg_restore output")
    print("TripWorld restored into the local database; stored vectors were retained.")
