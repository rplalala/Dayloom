"""Short transaction boundary and checksum-protected Product migrations."""

import hashlib
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from backend.app.product.settings import ProductSettings


def connect(settings: ProductSettings | None = None):
    settings = settings or ProductSettings()
    return psycopg.connect(settings.database_url.get_secret_value(), row_factory=dict_row)


def migrate(
    database_url: str, directory: Path | None = None, *, require_known_migrations: bool = False,
) -> list[str]:
    directory = directory or Path(__file__).with_name("migrations")
    applied = []
    with psycopg.connect(database_url) as connection:
        connection.execute("SELECT pg_advisory_xact_lock(198120)")
        connection.execute("CREATE SCHEMA IF NOT EXISTS app")
        connection.execute("""CREATE TABLE IF NOT EXISTS app.schema_migrations (
            name text PRIMARY KEY, sha256 text NOT NULL,
            applied_at timestamptz NOT NULL DEFAULT now()
        )""")
        paths = sorted(directory.glob("*.sql"))
        if require_known_migrations:
            recorded = {row[0] for row in connection.execute(
                "SELECT name FROM app.schema_migrations"
            )}
            if recorded - {path.name for path in paths}:
                raise ValueError("Database contains migrations from a newer application")
        for path in paths:
            content = path.read_bytes()
            digest = hashlib.sha256(content).hexdigest()
            old = connection.execute(
                "SELECT sha256 FROM app.schema_migrations WHERE name = %s", (path.name,)
            ).fetchone()
            if old:
                # Git checkouts may have stored the same SQL with Windows line endings.
                # Keep historical receipts; do not ignore any other byte differences.
                lf_content = content.replace(b"\r\n", b"\n")
                equivalent = {digest, hashlib.sha256(lf_content).hexdigest(),
                              hashlib.sha256(lf_content.replace(b"\n", b"\r\n")).hexdigest()}
                if old[0] not in equivalent:
                    raise ValueError(f"Migration checksum mismatch: {path.name}")
                continue
            connection.execute(content.decode("utf-8"))
            connection.execute(
                "INSERT INTO app.schema_migrations(name, sha256) VALUES (%s, %s)",
                (path.name, digest),
            )
            applied.append(path.name)
    return applied
