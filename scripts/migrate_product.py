"""Apply Product migrations without loading research or provider settings."""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402

from backend.app.product.database import migrate  # noqa: E402

if __name__ == "__main__":
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    database_url = os.environ.get("PRODUCT_DATABASE_URL")
    if not database_url:
        raise SystemExit("Set PRODUCT_DATABASE_URL before running Product migrations")
    try:
        applied = migrate(database_url)
    except Exception as exc:
        # Connection errors can contain credentials. Never print their original representation.
        message = str(exc) if isinstance(exc, ValueError) else "Product migration failed"
        raise SystemExit(message) from None
    print(f"Product migrations complete: {len(applied)} applied")
