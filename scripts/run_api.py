"""Local API launcher with a Windows event loop compatible with async PostgreSQL."""

import argparse
import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def create_api_loop():
    """Keep request resources on one loop; psycopg does not support Windows Proactor."""
    if sys.platform == "win32":
        return asyncio.SelectorEventLoop()
    return asyncio.new_event_loop()


def main(argv=None):
    import uvicorn

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--env-file", default=str(PROJECT_ROOT / ".env"),
        help="Local environment file; defaults to the repository .env; never committed",
    )
    args = parser.parse_args(argv)
    server = uvicorn.Server(uvicorn.Config(
        "backend.app.main:app", host=args.host, port=args.port, env_file=args.env_file,
    ))
    # Use serve(), not Server.run(), so Uvicorn cannot choose a different loop factory.
    asyncio.run(server.serve(), loop_factory=create_api_loop)


if __name__ == "__main__":
    main()
