"""Offline acceptance guards must fail before migrations or database connections."""

import pytest


@pytest.mark.parametrize(
    "dsn",
    [
        "postgresql://postgres@127.0.0.1/dayloom?application_name=test",
        "postgresql://postgres@127.0.0.1/dayloom?options=test",
        "host=127.0.0.1 dbname=dayloom application_name=test",
        "host=127.0.0.1 user=test",
    ],
)
@pytest.mark.parametrize("fixture_name", ["client", "browser_app"])
def test_unsafe_database_is_rejected_before_any_side_effect(monkeypatch, dsn, fixture_name):
    import subprocess

    import psycopg

    from backend.tests.product.test_accounts import client
    from backend.tests.product.test_browser import browser_app

    def forbidden(*args, **kwargs):
        pytest.fail("Unsafe acceptance setup reached a connection or process")

    monkeypatch.setenv("DAYLOOM_DB_TEST_URL", dsn)
    monkeypatch.setenv("PRODUCT_BROWSER_TESTS", "1")
    monkeypatch.setattr(psycopg, "connect", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    fixture = (
        client.__wrapped__(monkeypatch) if fixture_name == "client" else browser_app.__wrapped__()
    )
    with pytest.raises(ValueError, match="database name"):
        next(fixture)


@pytest.mark.parametrize(
    "dsn",
    [
        "postgresql://postgres@127.0.0.1/dayloom_test?application_name=acceptance",
        "host=127.0.0.1 dbname=dayloom_test user=postgres",
        "postgresql://postgres@127.0.0.1/dayloom?dbname=actual_test",
    ],
)
def test_actual_explicit_test_database_supports_url_and_conninfo(dsn):
    from backend.tests.product.database_safety import require_test_database

    assert require_test_database(dsn) == dsn
