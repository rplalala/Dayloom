"""Local API launcher with a Windows event loop compatible with async PostgreSQL."""

import argparse
import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def create_api_loop():
    """Retain the launcher interface for the shared PostgreSQL loop policy."""
    from backend.app.runtime.event_loop import create_api_loop as create_loop

    return create_loop()


def main(argv=None):
    import uvicorn

    from backend.app.runtime.configuration_paths import configuration_directory

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--env-file", default=str(configuration_directory(PROJECT_ROOT) / ".env"),
        help="Local environment file; defaults to the selected instance or repository .env",
    )
    args = parser.parse_args(argv)
    server = uvicorn.Server(uvicorn.Config(
        "backend.app.main:app", host=args.host, port=args.port, env_file=args.env_file,
    ))
    # Use serve(), not Server.run(), so Uvicorn cannot choose a different loop factory.
    asyncio.run(server.serve(), loop_factory=create_api_loop)


if __name__ == "__main__":
    main()
