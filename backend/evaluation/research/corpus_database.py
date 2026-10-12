"""Read-only consistent PostgreSQL entity scan; no ranking or vector generation."""

import os
from contextlib import suppress
from math import ceil
from typing import Any

from backend.app.tripworld.database.policy import POLICY_VERSION
from backend.app.tripworld.database.vectors import SPACE, SPACE_ID
from backend.cli.collection import _require


def validate_identity(identity, request, manifest):
    _require(
        identity.get("kind") == "database"
        and identity.get("manifest") == manifest
        and identity.get("artifact_sha256") == request["snapshot_identity"]["artifact_sha256"],
        "Database corpus identity drift",
    )
    _require(
        identity.get("build") == {"manifest": manifest, "row_count": manifest["entity_count"]}
        and identity.get("embedding_space") == SPACE,
        "Database manifest/embedding compatibility mismatch",
    )
    counts = identity.get("counts", {})
    _require(
        type(counts.get("entity_count")) is int
        and counts["entity_count"] == manifest["entity_count"]
        and type(counts.get("foreign_entity_count")) is int
        and counts["foreign_entity_count"] == 0,
        "Database corpus count/policy drift",
    )
    transaction = identity.get("transaction", {})
    _require(
        transaction.get("read_only") is True
        and transaction.get("isolation_level") == "repeatable read"
        and isinstance(transaction.get("snapshot_id"), str)
        and transaction["snapshot_id"],
        "Consistent read-only observation required",
    )


class DatabaseRows:
    def __init__(self, request, manifest, dsn_env, *, timer, deadline):
        self.request, self.manifest, self.dsn_env = request, manifest, dsn_env
        self.timer, self.deadline = timer, deadline
        self.conn: Any = None
        self.cursor: Any = None
        self.identity = None

    def _remaining(self):
        remaining = self.deadline - self.timer()
        if remaining <= 0:
            raise TimeoutError("Corpus measurement deadline exhausted")
        return remaining

    def _set_timeout(self):
        milliseconds = min(
            self.request["measurement_configuration"]["statement_timeout_ms"],
            max(1, int(self._remaining() * 1000)),
        )
        self.conn.execute("SELECT set_config('statement_timeout', %s, true)", (str(milliseconds),))

    def _execute(self, sql, params=None):
        self._set_timeout()
        return self.conn.execute(sql, params)

    def __enter__(self):
        import psycopg
        from psycopg.rows import dict_row

        dsn = os.environ.get(self.dsn_env)
        if not isinstance(dsn, str) or not dsn:
            raise ValueError("Explicit database DSN environment value required")
        config = self.request["measurement_configuration"]
        try:
            connection_factory: Any = psycopg.connect
            self.conn = connection_factory(
                dsn,
                autocommit=True,
                row_factory=dict_row,
                connect_timeout=min(
                    config["connect_timeout_seconds"], max(1, ceil(self._remaining()))
                ),
                options="-c default_transaction_read_only=on "
                f"-c statement_timeout={config['statement_timeout_ms']}",
            )
            self._remaining()
            self.conn.execute("BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY")
            _require(
                self._execute("SHOW transaction_read_only").fetchone()["transaction_read_only"]
                == "on",
                "Database transaction is not read-only",
            )
            isolation = self._execute("SHOW transaction_isolation").fetchone()[
                "transaction_isolation"
            ]
            snapshot = self._execute(
                "SELECT txid_current_snapshot()::text AS snapshot_id"
            ).fetchone()["snapshot_id"]
            artifact = self.request["snapshot_identity"]["artifact_sha256"]
            build = self._execute(
                "SELECT manifest,row_count FROM tripworld.corpus_builds WHERE artifact_hash=%s",
                (artifact,),
            ).fetchone()
            space = self._execute(
                "SELECT configuration FROM tripworld.embedding_spaces WHERE space_id=%s",
                (SPACE_ID,),
            ).fetchone()
            counts = self._execute(
                "SELECT count(*) AS entity_count, count(*) FILTER "
                "(WHERE artifact_hash<>%s OR policy_version<>%s) AS foreign_entity_count "
                "FROM tripworld.entities",
                (artifact, POLICY_VERSION),
            ).fetchone()
            self.identity = {
                "kind": "database",
                "artifact_sha256": artifact,
                "manifest": self.manifest,
                "build": build,
                "embedding_space": space["configuration"] if space else None,
                "counts": counts,
                "transaction": {
                    "read_only": True,
                    "isolation_level": isolation,
                    "snapshot_id": snapshot,
                },
            }
            validate_identity(self.identity, self.request, self.manifest)
            self.cursor = self.conn.cursor(name="rtpeval_corpus_scan", row_factory=dict_row)
            self._set_timeout()
            self.cursor.execute(
                "SELECT e.metadata AS entity,e.artifact_hash,e.policy_version,e.text_hash,"
                "e.discovery_allowed, EXISTS(SELECT 1 FROM tripworld.embeddings v "
                "WHERE v.space_id=%s AND v.text_hash=e.text_hash) AS has_embedding "
                'FROM tripworld.entities e ORDER BY e.retrieval_entity_id COLLATE "C" LIMIT %s',
                (SPACE_ID, config["max_entities"] + 1),
            )
            return self
        except BaseException:
            self.__exit__()
            raise

    def __iter__(self):
        while True:
            self._set_timeout()
            rows = self.cursor.fetchmany(self.request["measurement_configuration"]["batch_size"])
            if not rows:
                break
            yield from rows

    def __exit__(self, *_):
        if self.cursor is not None:
            with suppress(Exception):
                self.cursor.close()
        if self.conn is not None:
            with suppress(Exception):
                self.conn.execute("ROLLBACK")
            with suppress(Exception):
                self.conn.close()
