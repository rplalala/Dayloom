"""Bounded local SELECT diagnostics; never embeds, migrates or changes production policy.

Run sequentially with the same output directory: at most eight executed searches,
including EXPLAIN ANALYZE. A plain EXPLAIN/catalog read does not execute retrieval.
"""

import argparse
import asyncio
import hashlib
import ipaddress
import json
from pathlib import Path
from time import perf_counter

import numpy as np
from dotenv import load_dotenv

from backend.app.runtime.config_loader import load_runtime_config
from backend.app.runtime.database import PROJECT_ROOT, DatabaseSettings
from backend.app.tripworld.database.policy import POLICY_VERSION
from backend.app.tripworld.database.search import search_query
from backend.app.tripworld.retrieval.geography import GeographicScope
from backend.app.tripworld.retrieval.runtime import RuntimeRetrieval


def saved_vector(path):
    with np.load(path, allow_pickle=False) as archive:
        vectors = archive["vectors"]
        metadata = json.loads(str(archive["metadata"]))
    digest = hashlib.sha256(vectors.tobytes()).hexdigest()
    if metadata["response_model"] != "text-embedding-3-small":
        raise ValueError("Incompatible model")
    if vectors.shape != (1, 1536) or not np.isfinite(vectors).all():
        raise ValueError("Expected one finite 1536-dimensional vector")
    if digest != metadata["vectors_sha256"]:
        raise ValueError("Saved vector checksum mismatch")
    if not np.allclose(np.linalg.norm(vectors, axis=1), 1, atol=1e-5):
        raise ValueError("Saved vector is not normalized")
    return vectors[0], metadata


def reserve(directory, mode):
    directory.mkdir(parents=True, exist_ok=True)
    ledger = directory / "executions.json"
    entries = json.loads(ledger.read_text()) if ledger.exists() else []
    if len(entries) >= 8:
        raise ValueError("Eight-search diagnostic limit reached")
    entries.append({"attempt": len(entries) + 1, "mode": mode, "status": "reserved"})
    ledger.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    return len(entries)


def error_chain(exc):
    result, seen = [], set()
    while exc is not None and id(exc) not in seen:
        seen.add(id(exc))
        result.append({"type": type(exc).__name__, "sqlstate": getattr(exc, "sqlstate", None)})
        exc = exc.__cause__ or exc.__context__
    return result


class TimedConnection:
    def __init__(self, conn, timings):
        self.conn, self.timings = conn, timings

    async def execute(self, *args, **kwargs):
        start = perf_counter()
        try:
            cursor = await self.conn.execute(*args, **kwargs)
        finally:
            self.timings["execute_seconds"] = perf_counter() - start
        timings = self.timings

        class TimedCursor:
            async def fetchall(self):
                start = perf_counter()
                try:
                    return await cursor.fetchall()
                finally:
                    timings["fetch_decode_seconds"] = perf_counter() - start

        return TimedCursor()


async def observe_waits(config, pid, samples):
    """Sample only the diagnostic backend; never cancel or alter the observed query."""
    async with RuntimeRetrieval(config) as monitor:
        await monitor.prepare()
        for _ in range(150):
            row = await (
                await monitor.conn.execute(
                    "SELECT state,wait_event_type,wait_event,pg_blocking_pids(pid) AS blockers "
                    "FROM pg_stat_activity WHERE pid=%s",
                    (pid,),
                )
            ).fetchone()
            samples.append(row)
            await asyncio.sleep(0.1)


async def diagnose(args):
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    host = DatabaseSettings().connection_parameters().get("host", "127.0.0.1")
    if host != "localhost" and not ipaddress.ip_address(host).is_loopback:
        raise ValueError("Diagnostics require a loopback database")
    vector, metadata = saved_vector(args.vector)
    scope = GeographicScope(latitude=args.latitude, longitude=args.longitude, radius_km=15)
    config = load_runtime_config().tripworld_discovery
    if args.mode != "runtime3":
        config = config.model_copy(update={"sql_timeout": 15.0})
    report = {
        "mode": args.mode,
        "scope": scope.model_dump(),
        "vector": metadata,
        "exact_live_replay": False,
        "timings": {},
        "external_api_calls": 0,
    }
    async with RuntimeRetrieval(config) as runtime:
        start = perf_counter()
        await runtime.prepare()
        report["prepare_seconds"] = perf_counter() - start
        conn = runtime.conn
        sql, params = search_query(scope, vector, 10)
        sql = sql.replace(
            "WHERE discovery_allowed AND",
            "WHERE discovery_allowed AND "
            "policy_version=%(runtime_policy)s "
            "AND artifact_hash=%(runtime_artifact)s AND",
        )
        params.update(runtime_policy=POLICY_VERSION, runtime_artifact=runtime.artifact_hash)
        report["sql"] = sql
        report["parameters"] = {k: v for k, v in params.items() if k != "vector"}
        if args.mode == "plan":
            report["settings"] = await (
                await conn.execute(
                    "SELECT name,setting,unit FROM pg_settings WHERE name IN "
                    "('statement_timeout','work_mem','shared_buffers','effective_cache_size',"
                    "'max_parallel_workers_per_gather','default_transaction_read_only')"
                )
            ).fetchall()
            report["indexes"] = await (
                await conn.execute(
                    "SELECT tablename,indexname,indexdef FROM pg_indexes "
                    "WHERE schemaname='tripworld'"
                )
            ).fetchall()
            report["statistics"] = await (
                await conn.execute(
                    "SELECT relname,n_live_tup,n_dead_tup,last_analyze,last_autoanalyze "
                    "FROM pg_stat_user_tables WHERE schemaname='tripworld'"
                )
            ).fetchall()
            report["plan"] = await (
                await conn.execute("EXPLAIN (FORMAT JSON) " + sql, params)
            ).fetchall()
            attempt = "plan"
        else:
            attempt = reserve(args.output, args.mode)
            report["wait_samples"] = []
            watcher = asyncio.create_task(
                observe_waits(config, conn.info.backend_pid, report["wait_samples"])
            )
            start = perf_counter()
            try:
                async with asyncio.timeout(config.sql_timeout):
                    if args.mode == "runtime3":
                        runtime.conn = TimedConnection(conn, report["timings"])
                        try:
                            rows = await runtime.search(vector, scope, 10)
                        finally:
                            runtime.conn = conn
                    else:
                        measured = TimedConnection(conn, report["timings"])
                        prefix = (
                            "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) "
                            if args.mode == "analyze15"
                            else ""
                        )
                        rows = await (await measured.execute(prefix + sql, params)).fetchall()
                    report["rows"] = rows
                    report["status"] = "completed"
            except Exception as exc:
                report.update(status="failed", errors=error_chain(exc))
            finally:
                report["elapsed_seconds"] = perf_counter() - start
                watcher.cancel()
                try:
                    await watcher
                except asyncio.CancelledError:
                    pass
                except Exception as exc:
                    report["monitor_error"] = error_chain(exc)
            report["transaction_status"] = conn.info.transaction_status.name
            report["connection_closed_before_cleanup"] = conn.closed
            report["post_query_probe"] = await (
                await conn.execute("SELECT 1 AS healthy")
            ).fetchone()
        args.output.mkdir(parents=True, exist_ok=True)
    report["connection_closed_after_cleanup"] = conn.closed
    target = args.output / f"{attempt}_{args.mode}.json"
    target.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(
        json.dumps(
            {
                k: report.get(k)
                for k in [
                    "mode",
                    "status",
                    "elapsed_seconds",
                    "timings",
                    "errors",
                    "transaction_status",
                    "connection_closed_after_cleanup",
                ]
            }
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vector", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--latitude", type=float, required=True)
    parser.add_argument("--longitude", type=float, required=True)
    parser.add_argument(
        "--mode",
        choices=["plan", "runtime3", "normal15", "analyze15"],
        required=True,
    )
    asyncio.run(diagnose(parser.parse_args()), loop_factory=asyncio.SelectorEventLoop)


if __name__ == "__main__":
    main()
