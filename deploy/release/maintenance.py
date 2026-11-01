"""Private operational backup and empty-destination recovery; never a factory export."""

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from contextlib import ExitStack
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from deploy.release.baseline_artifact import BaselineError

FORMAT = "dayloom-private-backup-v1"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def regular_files(root):
    if root.is_symlink() or not root.is_dir():
        raise BaselineError("Invalid operational backup directory")
    files = []
    for path in root.rglob("*"):
        if path.is_symlink() or not (path.is_file() or path.is_dir()):
            raise BaselineError("Operational files must be regular files, without symbolic links")
        if path.is_file():
            files.append(path)
    return sorted(files)


def verify(directory):
    root = Path(directory)
    try:
        files = regular_files(root)
        checksums = {}
        for line in (root / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
            checksum, name = line.split("  ", 1)
            path = PurePosixPath(name)
            if (
                not re.fullmatch(r"[a-f0-9]{64}", checksum)
                or path.is_absolute()
                or ".." in path.parts
                or "\\" in name
                or name in checksums
            ):
                raise ValueError
            checksums[name] = checksum
        actual = {
            p.relative_to(root).as_posix(): digest(p) for p in files if p != root / "SHA256SUMS.txt"
        }
        if actual != checksums:
            raise ValueError
        manifest = json.loads((root / "backup.json").read_text(encoding="utf-8"))
        required = {
            "config/.env",
            "config/product.yaml",
            "config/.config-access.json",
            "database.pgcustom",
            "backup.json",
        }
        if (
            manifest["format"] != FORMAT
            or not required <= actual.keys()
            or manifest["receipt"]["format_version"] != 1
            or not re.fullmatch(r"[a-f0-9]{64}", manifest["receipt"]["baseline_id"])
        ):
            raise ValueError
        return manifest
    except Exception:
        raise BaselineError(
            "Invalid operational backup: verify checksums and all private files"
        ) from None


def receipt(connection):
    rows = connection.execute("SELECT row_to_json(t) FROM app.deployment_baseline t").fetchall()
    if len(rows) != 1 or rows[0][0].get("format_version") != 1:
        raise BaselineError("A verified installed database is required")
    return rows[0][0]


def backup(directory, config, parameters, expected_id):
    from deploy.release.baseline_database import (
        LOCK_ID,
        connect,
        inventory,
        require_quiescent,
        run_tool,
    )

    root, config = Path(directory), Path(config)
    if root.exists() or root.is_symlink():
        raise BaselineError("Select a new private backup directory; existing files are preserved")
    files = regular_files(config)
    if not {".env", "product.yaml", ".config-access.json"} <= {
        p.relative_to(config).as_posix() for p in files
    }:
        raise BaselineError("A complete installed instance configuration is required")
    with (
        ExitStack() as configuration_locks,
        connect(parameters) as connection,
        connection.transaction(),
    ):
        # The supported utility runtime is Linux. Use the application's existing lock files
        # through the read-only mount; never create lock/config files during a snapshot.
        import fcntl

        for name in (".bootstrap.lock", ".env.config.lock"):
            path = config / name
            if path.exists():
                lock = configuration_locks.enter_context(path.open("rb"))
                try:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    raise BaselineError(
                        "Configuration is busy; finish the other operation first"
                    ) from None
        connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        connection.execute("SELECT pg_advisory_xact_lock(%s)", (LOCK_ID,))
        require_quiescent(connection)
        installed = receipt(connection)
        if installed.get("baseline_id") != expected_id or installed.get("singleton") is not True:
            raise BaselineError(
                "Configuration and installed database identities differ; data preserved"
            )
        database = inventory(connection)
        snapshot = connection.execute("SELECT pg_export_snapshot()").fetchone()[0]
        root.mkdir(mode=0o700)
        os.chmod(root, 0o700)
        for path in files:
            if path.name.endswith(".lock") or re.match(
                r"^\.(?:env|product\.yaml|config-access\.json)\.config-", path.name
            ):
                continue
            target = root / "config" / path.relative_to(config)
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            shutil.copyfile(path, target)
            os.chmod(target, 0o600)
        with (root / "database.pgcustom").open("xb") as stream:
            os.chmod(stream.name, 0o600)
            run_tool(
                "pg_dump",
                ["--format=custom", "--no-owner", "--no-privileges", "--snapshot=" + snapshot],
                parameters,
                output_stream=stream,
            )
        manifest = {
            "format": FORMAT,
            "captured_at": datetime.now(UTC).isoformat(),
            "receipt": installed,
            "database": database,
        }
        (root / "backup.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        (root / "SHA256SUMS.txt").write_text(
            "".join(
                digest(p) + "  " + p.relative_to(root).as_posix() + "\n"
                for p in regular_files(root)
            ),
            encoding="utf-8",
        )
        for path in regular_files(root):
            os.chmod(path, 0o600)
    verify(root)
    return {"status": "backed-up", "baseline_id": installed["baseline_id"]}


def restore_config(directory, config):
    verify(directory)
    source, target = Path(directory) / "config", Path(config)
    if target.is_symlink() or (target.exists() and any(target.iterdir())):
        raise BaselineError(
            "Restore requires an empty configuration directory; files were preserved"
        )
    target.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(target, 0o700)
    for path in regular_files(source):
        destination = target / path.relative_to(source)
        destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
        os.chmod(destination, 0o600)
    return {"status": "configuration-restored"}


def restore(directory, parameters):
    from psycopg.conninfo import make_conninfo

    from deploy.release.baseline_database import (
        LOCK_ID,
        connect,
        inventory,
        is_empty_database,
        require_compatibility,
        run_tool,
    )

    root = Path(directory)
    manifest = verify(root)
    with connect(parameters) as connection:
        connection.execute("SELECT pg_advisory_lock(%s)", (LOCK_ID,))
        if not is_empty_database(connection):
            raise BaselineError(
                "Restore requires an empty database; destination data was preserved"
            )
        require_compatibility(connection, manifest["database"])
        with (root / "database.pgcustom").open("rb") as stream:
            run_tool(
                "pg_restore",
                [
                    "--single-transaction",
                    "--exit-on-error",
                    "--no-owner",
                    "--no-privileges",
                    "--dbname=" + make_conninfo(dbname=parameters["dbname"]),
                ],
                parameters,
                input_stream=stream,
            )
        if (
            receipt(connection) != manifest["receipt"]
            or inventory(connection) != manifest["database"]
        ):
            raise BaselineError(
                "Restored identity/content mismatch; preserve target for inspection"
            )
    return {"status": "restored", "baseline_id": manifest["receipt"]["baseline_id"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("backup", "verify", "restore", "restore-config"):
        action = commands.add_parser(command)
        action.add_argument("directory")
        if command in {"backup", "restore-config"}:
            action.add_argument("--config", required=True)
        if command == "backup":
            action.add_argument("--expect-id", required=True)
        if command in {"backup", "restore"}:
            action.add_argument("--dsn-env", default="DAYLOOM_DB_URL")
    args = parser.parse_args(argv)
    try:
        if args.command == "verify":
            manifest = verify(args.directory)
            result = {"status": "verified", "baseline_id": manifest["receipt"]["baseline_id"]}
        elif args.command == "restore-config":
            result = restore_config(args.directory, args.config)
        else:
            from deploy.release.baseline_database import connection_parameters

            parameters = connection_parameters(args.dsn_env)
            result = (
                backup(args.directory, args.config, parameters, args.expect_id)
                if args.command == "backup"
                else restore(args.directory, parameters)
            )
        print(json.dumps(result))
        return 0
    except Exception as error:
        message = str(error) if isinstance(error, BaselineError) else "Operational command failed"
        print(message + ". Preserve the backup and inspect private configuration.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
