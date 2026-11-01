"""Wait for a verified database installation on every application process start."""

import re
import time

import psycopg

from backend.app.product.database import migrate
from backend.app.runtime.database import DatabaseSettings


def prepare_database(baseline_id, timeout=1800):
    if not re.fullmatch(r"[a-f0-9]{64}", baseline_id or ""):
        raise ValueError("A released baseline identity is required")
    if timeout <= 0:
        raise ValueError("Startup timeout must be positive")
    settings = DatabaseSettings()
    parameters = settings.connection_parameters()
    parameters.update(connect_timeout=3,
                      options=parameters.get("options", "")
                      + " -c default_transaction_read_only=on -c statement_timeout=5000")
    deadline = time.monotonic() + timeout
    while True:
        installed = False
        try:
            with psycopg.connect(**parameters) as connection:
                exists = connection.execute(
                    "SELECT to_regclass('app.deployment_baseline')"
                ).fetchone()[0]
                if exists:
                    rows = connection.execute(
                        "SELECT format_version,baseline_id FROM app.deployment_baseline "
                        "WHERE singleton"
                    ).fetchall()
                    if rows != [(1, baseline_id)]:
                        raise ValueError("Database installation identity does not match release")
                    installed = True
        except psycopg.OperationalError:
            pass
        if installed:
            migrate(settings.connection_string.get_secret_value())
            return
        if time.monotonic() >= deadline:
            raise TimeoutError("Database installation did not become ready")
        time.sleep(min(1, max(0, deadline - time.monotonic())))
