"""Shared opt-in database admission, evaluated before acceptance setup has effects."""

from psycopg import ProgrammingError
from psycopg.conninfo import conninfo_to_dict


def require_test_database(dsn: str) -> str:
    try:
        name = conninfo_to_dict(dsn).get("dbname", "")
    except ProgrammingError:
        raise ValueError("Acceptance requires an explicit isolated test database name") from None
    if not name or "test" not in name.lower():
        raise ValueError("Acceptance requires an explicit isolated test database name")
    return dsn
