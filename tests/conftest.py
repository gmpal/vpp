"""Shared pytest configuration for the backend test suite.

The suite is self-contained: it never reads the repository ``.env`` and never
talks to the frontend. Two tiers exist.

* **unit** (default): no database, no Kafka, no internet. Outbound network
  connections and ``psycopg2.connect`` raise immediately, so a test that
  silently depends on infrastructure fails loudly instead of flaking.
* **integration**: needs the disposable TimescaleDB from
  ``docker-compose.test.yaml`` (``make test-db-up``). A test is integration if
  it carries ``@pytest.mark.integration`` or uses any database fixture below.
  When the database is unreachable those tests are skipped with a hint.

The test database location comes from ``VPP_TEST_DB_*`` variables and
defaults to ``localhost:55432``, deliberately not the dev port, because the
fixtures drop every table in the ``public`` schema.
"""

import os
import socket

import pytest

# ---------------------------------------------------------------------------
# Environment: must be set before any backend module is imported.
# ---------------------------------------------------------------------------

TEST_DB = {
    "host": os.environ.get("VPP_TEST_DB_HOST", "localhost"),
    "port": int(os.environ.get("VPP_TEST_DB_PORT", "55432")),
    "dbname": os.environ.get("VPP_TEST_DB_NAME", "postgres"),
    "user": os.environ.get("VPP_TEST_DB_USER", "postgres"),
    "password": os.environ.get("VPP_TEST_DB_PASSWORD", "testpass"),
}

os.environ["ENVIRONMENT"] = "testing"
os.environ["TIMESCALEDB_HOST"] = TEST_DB["host"]
os.environ["POSTGRES_PORT"] = str(TEST_DB["port"])
os.environ["POSTGRES_DB"] = TEST_DB["dbname"]
os.environ["POSTGRES_USER"] = TEST_DB["user"]
os.environ["POSTGRES_PASSWORD"] = TEST_DB["password"]

import psycopg2  # noqa: E402

from backend.src.db import CrudManager, DatabaseManager, SchemaManager  # noqa: E402

DB_FIXTURES = {"db_connection", "db_manager", "schema_manager", "crud_manager", "cleanup"}

_REAL_PG_CONNECT = psycopg2.connect
_REAL_SOCKET_CONNECT = socket.socket.connect
_db_reachable = None


def _database_reachable() -> bool:
    global _db_reachable
    if _db_reachable is None:
        try:
            _REAL_PG_CONNECT(connect_timeout=3, **TEST_DB).close()
            _db_reachable = True
        except psycopg2.OperationalError:
            _db_reachable = False
    return _db_reachable


# ---------------------------------------------------------------------------
# Tier assignment
# ---------------------------------------------------------------------------


def _uses_real_db_fixture(item) -> bool:
    """True if the test resolves a database fixture defined here (not a same-named local mock)."""
    for name in DB_FIXTURES & set(item.fixturenames):
        defs = item._fixtureinfo.name2fixturedefs.get(name)
        if defs and getattr(defs[-1].func, "__module__", None) == __name__:
            return True
    return False


def pytest_collection_modifyitems(config, items):
    for item in items:
        if item.get_closest_marker("integration") is None and _uses_real_db_fixture(item):
            item.add_marker(pytest.mark.integration)
        if item.get_closest_marker("integration") is None:
            item.add_marker(pytest.mark.unit)


@pytest.fixture(autouse=True)
def _enforce_tier(request, monkeypatch):
    """Skip integration tests without a database; isolate unit tests from infrastructure."""
    if request.node.get_closest_marker("integration") is not None:
        if not _database_reachable():
            pytest.skip(
                f"test database not reachable at {TEST_DB['host']}:{TEST_DB['port']} "
                "(start it with `make test-db-up`)"
            )
        return

    def _blocked_pg_connect(*args, **kwargs):
        raise RuntimeError("unit test attempted a database connection; mark it integration or mock it")

    def _guarded_socket_connect(sock, address):
        host = address[0] if isinstance(address, tuple) else address
        if host in ("127.0.0.1", "::1", "localhost") or sock.family == getattr(socket, "AF_UNIX", None):
            return _REAL_SOCKET_CONNECT(sock, address)
        raise RuntimeError(f"unit test attempted a network connection to {address!r}; mock it")

    monkeypatch.setattr(psycopg2, "connect", _blocked_pg_connect)
    monkeypatch.setattr(socket.socket, "connect", _guarded_socket_connect)


# ---------------------------------------------------------------------------
# Database fixtures (integration tier only)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def db_connection():
    """A connection to the disposable test database. Drops all public tables on teardown."""
    if not _database_reachable():
        pytest.skip("test database not reachable (start it with `make test-db-up`)")
    conn = _REAL_PG_CONNECT(**TEST_DB)
    with conn.cursor() as cursor:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS timescaledb;")
    conn.commit()
    yield conn
    with conn.cursor() as cursor:
        cursor.execute(
            """
            DO $$
            DECLARE tbl record;
            BEGIN
                FOR tbl IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
                    EXECUTE format('DROP TABLE IF EXISTS public.%I CASCADE;', tbl.tablename);
                END LOOP;
            END $$;
            """
        )
    conn.commit()
    conn.close()


@pytest.fixture(scope="module")
def db_manager(db_connection):
    """A DatabaseManager pointed at the test database, opening real connections per query."""
    return DatabaseManager(
        {"host": TEST_DB["host"], "port": TEST_DB["port"], "database": TEST_DB["dbname"],
         "user": TEST_DB["user"], "password": TEST_DB["password"]}
    )


@pytest.fixture(scope="module")
def schema_manager(db_manager):
    """A freshly reset schema."""
    schema_mgr = SchemaManager(db_manager)
    schema_mgr.reset_all_tables()
    return schema_mgr


@pytest.fixture
def crud_manager(db_manager):
    return CrudManager(db_manager)


@pytest.fixture
def cleanup(db_manager):
    """Empty the data tables after each test."""
    yield
    tables = [
        "solar", "load", "market", "solar_forecast", "load_forecast", "market_forecast",
        "batteries", "electric_vehicles", "household_load", "energy_sources", "households", "communities",
    ]
    for table in tables:
        try:
            db_manager.execute(f"DELETE FROM {table};")
        except Exception:
            continue
