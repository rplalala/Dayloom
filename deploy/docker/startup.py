"""Wait for a verified database installation on every application process start."""

import re
import time

import psycopg

from backend.app.product.database import migrate
from backend.app.runtime.database import DatabaseSettings


class InstallationError(ValueError):
    """Credential-free, actionable startup diagnostic safe for operator logs."""


def prepare_database(baseline_id, timeout=1800):
    if not re.fullmatch(r"[a-f0-9]{64}", baseline_id or ""):
        raise InstallationError("A released baseline identity is required")
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
                        raise InstallationError(
                            "Database installation identity does not match release; "
                            "use the installed baseline identity. Existing data was preserved."
                        )
                    installed = True
        except psycopg.OperationalError:
            pass
        if installed:
            try:
                migrate(settings.connection_string.get_secret_value(),
                        require_known_migrations=True)
            except ValueError:
                raise InstallationError(
                    "Database migration checksum or newer application history is incompatible; "
                    "use a matching application or restore a pre-upgrade backup."
                ) from None
            return
        if time.monotonic() >= deadline:
            raise InstallationError(
                "Database installation did not become ready; inspect postgres/init logs and "
                "retry after resolving the failure. Existing data was preserved."
            )
        time.sleep(min(1, max(0, deadline - time.monotonic())))
