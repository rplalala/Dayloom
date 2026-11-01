"""Apply Product migrations without loading research or provider settings."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402

from backend.app.product.database import migrate  # noqa: E402
from backend.app.runtime.configuration_paths import configuration_directory  # noqa: E402
from backend.app.runtime.database import DatabaseSettings  # noqa: E402

if __name__ == "__main__":
    load_dotenv(configuration_directory(PROJECT_ROOT) / ".env", override=False)
    try:
        applied = migrate(DatabaseSettings().connection_string.get_secret_value())
    except Exception as exc:
        # Connection errors can contain credentials. Never print their original representation.
        message = (
            str(exc) if type(exc) is ValueError else
            "Product migration failed; check DAYLOOM_DB_* settings and migration integrity"
        )
        raise SystemExit(message) from None
    print(f"Product migrations complete: {len(applied)} applied")
