"""Independent TripWorld database lifecycle, ingestion, embedding and retrieval CLI."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def run():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    parser.add_argument("--root", type=Path, default=ROOT / "data/tripworld")
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("migrate", "ingest", "preflight", "embed", "status", "validate", "audit"):
        commands.add_parser(command)
    query = commands.add_parser("query")
    query.add_argument("text")
    query.add_argument("--latitude", type=float, required=True)
    query.add_argument("--longitude", type=float, required=True)
    query.add_argument("--radius-km", type=float, required=True)
    query.add_argument("--country")
    query.add_argument("--top-k", type=int, default=10)
    query.add_argument("--lexical", action="store_true")
    args = parser.parse_args()
    if args.env_file:
        from dotenv import load_dotenv

        load_dotenv(args.env_file, override=False)
    from tools.data.tripworld.artifact_persistence import write_json_if_changed
    from tools.data.tripworld.database_connection import connection, migrate

    with connection() as conn:
        if args.command == "migrate":
            result = {"applied": migrate(conn)}
        elif args.command == "ingest":
            from tools.data.tripworld.database_ingestion import ingest

            result = ingest(conn, args.root / "artifacts/retrieval_entities.parquet")
            write_json_if_changed(args.root / "reports/phase5_ingestion.json", result)
        elif args.command == "preflight":
            from tools.data.tripworld.database_build import preflight

            result = preflight(conn, args.root)
        elif args.command == "embed":
            from tools.data.tripworld.database_build import build

            result = build(conn, args.root)
        elif args.command == "audit":
            from tools.data.tripworld.database_audit import audit

            result = audit(conn, args.root)
        elif args.command == "status":
            result = {
                "postgres": conn.execute("SELECT version() AS value").fetchone()["value"],
                "pgvector": conn.execute(
                    "SELECT extversion FROM pg_extension WHERE extname='vector'"
                ).fetchone()["extversion"],
                "entities": conn.execute("SELECT count(*) AS n FROM tripworld.entities").fetchone()[
                    "n"
                ],
                "vectors": conn.execute(
                    "SELECT count(*) AS n FROM tripworld.embeddings"
                ).fetchone()["n"],
                "database_bytes": conn.execute(
                    "SELECT pg_database_size(current_database()) AS n"
                ).fetchone()["n"],
            }
        elif args.command == "validate":
            from tools.validation.retrieval_validation import validate_database

            result = validate_database(conn, args.root)
        else:
            from backend.app.tripworld.retrieval.geography import GeographicScope
            from tools.diagnostics.retrieval_service import RetrievalService

            service = RetrievalService(conn, args.root)
            result = service.retrieve(
                args.text,
                GeographicScope(
                    latitude=args.latitude,
                    longitude=args.longitude,
                    radius_km=args.radius_km,
                    country=args.country,
                ),
                args.top_k,
                lexical=args.lexical,
            )
    print(json.dumps(result, ensure_ascii=True, indent=2, default=str))


if __name__ == "__main__":
    run()
