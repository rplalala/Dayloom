"""Run local PostgreSQL Compose commands using the shared Dayloom deployment settings."""

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main(argv=None):
    from dotenv import load_dotenv

    from backend.app.runtime.configuration_paths import configuration_directory
    from backend.app.runtime.database import DatabaseSettings

    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args in (["--help"], ["-h"]):
        print("Usage: python scripts/run_database.py <compose arguments>")
        print("Example: python scripts/run_database.py up -d --wait postgres")
        return 0
    load_dotenv(configuration_directory(PROJECT_ROOT) / ".env", override=False)
    try:
        parameters = DatabaseSettings().connection_parameters()
        if parameters.get("host") not in {"localhost", "127.0.0.1"}:
            print("Local Compose publishes on IPv4 loopback; use database host "
                  "127.0.0.1 or localhost.", file=sys.stderr)
            return 1
        if not all(parameters.get(key) for key in ("user", "password", "dbname", "port")):
            raise ValueError("Local Compose requires explicit connection fields")
        environment = {**os.environ, **{
            "DAYLOOM_DB_" + key: str(parameters[value]) for key, value in {
                "USER": "user", "PASSWORD": "password", "NAME": "dbname", "PORT": "port",
            }.items()
        }}
        return subprocess.run(
            ["docker", "compose", "--project-directory", str(PROJECT_ROOT),
             "--file", str(PROJECT_ROOT / "compose.yaml"), *args],
            env=environment, check=False,
        ).returncode
    except Exception as error:
        # Validation and connection diagnostics can contain credentials.
        print("Database launcher failed (" + type(error).__name__ +
              "). Check product.yaml and database environment overrides.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
