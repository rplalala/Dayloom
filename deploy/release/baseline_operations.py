"""Snapshot export and guarded first-install restoration."""

import json
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path

from psycopg.conninfo import make_conninfo

from deploy.release.baseline_artifact import (
    FORMAT,
    SIDECARS,
    BaselineError,
    manifest_identity,
    sha256,
    verify_release,
)
from deploy.release.baseline_database import (
    LOCK_ID,
    RECEIPT_TABLE,
    connect,
    inventory,
    require_compatibility,
    require_quiescent,
    run_tool,
    server_identity,
)


def _copy_runtime(root, runtime_root, notices):
    for name in SIDECARS:
        source = runtime_root / name
        if source.is_symlink() or not source.is_file():
            raise BaselineError("Required retrieval metadata is missing")
        target = root / "runtime" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    if not notices:
        raise BaselineError("Supply the baseline's provenance notices")
    for source in map(Path, notices):
        if source.is_symlink() or not source.is_file():
            raise BaselineError("Invalid provenance notice")
        target = root / "notices" / source.name
        target.parent.mkdir(exist_ok=True)
        if target.exists():
            raise BaselineError("Provenance notice filenames must be distinct")
        shutil.copyfile(source, target)


def _require_runtime_identity(connection, runtime_root):
    manifest = json.loads((runtime_root / SIDECARS[0]).read_text(encoding="utf-8"))
    build = json.loads((runtime_root / SIDECARS[1]).read_text(encoding="utf-8"))
    if build.get("status") != "complete":
        raise BaselineError("Baseline requires complete retrieval metadata")
    row = connection.execute(
        "SELECT manifest,row_count FROM tripworld.corpus_builds WHERE artifact_hash=%s",
        (manifest.get("output_sha256"),),
    ).fetchone()
    if not row or row != (manifest, manifest.get("entity_count")):
        raise BaselineError("Baseline retrieval metadata does not match the source corpus")


def export_baseline(output, runtime_root, revision, notices, parameters):
    if not re.fullmatch("[a-f0-9]{7,64}", revision):
        raise BaselineError("Provide the exact source revision")
    output = Path(output)
    if output.exists():
        raise BaselineError("Export destination already exists; existing files were preserved")
    with connect(parameters) as connection, connection.transaction():
        connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        require_quiescent(connection)
        _require_runtime_identity(connection, Path(runtime_root))
        database = inventory(connection)
        if database["server_major"] != 17 or not any(
            ext["name"] == "vector" for ext in database["extensions"]
        ):
            raise BaselineError("Export requires PostgreSQL 17 with vector installed")
        if not {"app", "tripworld"} <= set(database["schemas"]):
            raise BaselineError("Export requires both Product and TripWorld schemas")
        captured_at = connection.execute("SELECT transaction_timestamp()").fetchone()[0].isoformat()
        snapshot = connection.execute("SELECT pg_export_snapshot()").fetchone()[0]
        output.mkdir(mode=0o700, parents=True)
        _copy_runtime(output, Path(runtime_root), notices)
        _require_runtime_identity(connection, output / "runtime")
        with (output / "database.pgcustom").open("xb") as stream:
            run_tool("pg_dump", [
                "--format=custom", "--no-owner", "--no-privileges", "--snapshot=" + snapshot,
                "--exclude-table=app." + RECEIPT_TABLE,
            ], parameters, output_stream=stream)
    manifest = {
        "format": FORMAT, "source_revision": revision, "captured_at": captured_at,
        "database": database,
        "files": {path.relative_to(output).as_posix(): {
            "sha256": sha256(path), "bytes": path.stat().st_size,
        } for path in sorted(output.rglob("*")) if path.is_file()},
    }
    manifest["baseline_id"] = manifest_identity(manifest)
    (output / "baseline.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    paths = sorted(p for p in output.rglob("*") if p.is_file())
    (output / "SHA256SUMS.txt").write_text("".join(
        sha256(path) + "  " + path.relative_to(output).as_posix() + "\n" for path in paths
    ), encoding="utf-8")
    verify_release(output, manifest["baseline_id"])
    return {"baseline_id": manifest["baseline_id"],
            "dump_bytes": manifest["files"]["database.pgcustom"]["bytes"], "status": "exported"}


def _receipt(connection):
    if connection.execute("SELECT to_regclass('app.deployment_baseline')").fetchone()[0] is None:
        return None
    rows = connection.execute(
        "SELECT format_version,baseline_id FROM app.deployment_baseline WHERE singleton"
    ).fetchall()
    if len(rows) != 1:
        raise BaselineError("Invalid installation metadata; existing data was preserved")
    return rows[0]


def _record_installation(connection, manifest):
    connection.execute("""CREATE TABLE app.deployment_baseline (
        singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
        format_version integer NOT NULL CHECK (format_version=1),
        baseline_id text NOT NULL CHECK (baseline_id ~ '^[a-f0-9]{64}$'),
        installed_at timestamptz NOT NULL
    )""")
    connection.execute(
        "INSERT INTO app.deployment_baseline(singleton,format_version,baseline_id,installed_at) "
        "VALUES (true,1,%s,%s)",
        (manifest["baseline_id"], datetime.now(UTC)),
    )


def _empty(connection):
    return not connection.execute(
        "SELECT 1 FROM pg_namespace WHERE nspname !~ '^pg_' "
        "AND nspname NOT IN ('information_schema','public') "
        "UNION ALL SELECT 1 FROM pg_depend d JOIN pg_namespace n ON n.oid=d.refobjid "
        "WHERE d.refclassid='pg_namespace'::regclass AND n.nspname='public' "
        "UNION ALL SELECT 1 FROM pg_extension WHERE extname <> 'plpgsql' LIMIT 1"
    ).fetchone()


def restore_baseline(directory, parameters, expected_id=None):
    manifest = verify_release(directory, expected_id)
    with connect(parameters) as connection:
        connection.execute("SELECT pg_advisory_lock(%s)", (LOCK_ID,))
        require_compatibility(connection, manifest["database"])
        receipt = _receipt(connection)
        if receipt:
            if receipt != (1, manifest["baseline_id"]):
                raise BaselineError("Installed baseline differs; existing data was preserved")
            if server_identity(connection) != {
                key: manifest["database"][key] for key in ("server_major", "extensions")
            }:
                raise BaselineError("Installed database extension compatibility mismatch")
            return {"status": "reused", "baseline_id": receipt[1]}
        restored = False
        if _empty(connection):
            with (Path(directory) / "database.pgcustom").open("rb") as stream:
                run_tool("pg_restore", [
                    "--single-transaction", "--exit-on-error", "--no-owner", "--no-privileges",
                    "--dbname=" + make_conninfo(dbname=parameters["dbname"]),
                ], parameters, input_stream=stream)
            restored = True
        with connection.transaction():
            connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
            actual = inventory(connection)
            if actual != manifest["database"]:
                raise BaselineError("Destination baseline mismatch; existing data was preserved")
            # Exact content/schema identity recognizes the committed-restore/registration gap.
            _record_installation(connection, manifest)
        return {"status": "installed" if restored else "recovered",
                "baseline_id": manifest["baseline_id"]}
