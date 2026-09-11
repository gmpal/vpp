import os

import dotenv
import pytest

# Load .env from repo root so test DB config matches the running instance
dotenv.load_dotenv()

# These imports are only needed for integration tests (live DB).
# Guard them so unit tests can be collected without any infrastructure.
try:
    import psycopg2
    from backend.src.db import DatabaseManager, CrudManager, SchemaManager
    _DB_AVAILABLE = True
except ImportError:
    _DB_AVAILABLE = False

DB_CONFIG = {
    "dbname": os.environ.get("POSTGRES_DB", "postgres"),
    "user": os.environ.get("POSTGRES_USER", "postgres"),
    "password": os.environ.get("POSTGRES_PASSWORD", "testpass"),
    "host": os.environ.get("TIMESCALEDB_HOST", "localhost"),
    "port": os.environ.get("POSTGRES_PORT", "5432"),
}


@pytest.fixture(scope="module")
def db_connection():
    """Set up a connection to a Dockerized TimescaleDB instance."""
    if not _DB_AVAILABLE:
        pytest.skip("psycopg2 / backend DB modules not installed")
    try:
        conn = psycopg2.connect(**DB_CONFIG)
    except psycopg2.OperationalError as e:
        pytest.skip(f"Database not accessible: {e}")
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
    """Provide a DatabaseManager instance using the test connection."""
    db = DatabaseManager()
    db.connect = lambda: db_connection
    return db


@pytest.fixture(scope="module")
def schema_manager(db_manager):
    """Set up the schema using SchemaManager."""
    schema_mgr = SchemaManager(db_manager)
    try:
        schema_mgr.reset_all_tables()
    except Exception as e:
        print(f"Schema setup failed: {e}")
        raise
    return schema_mgr


@pytest.fixture
def crud_manager(db_manager):
    """Provide a CrudManager instance for CRUD operations."""
    return CrudManager(db_manager)


@pytest.fixture
def cleanup(db_manager):
    """Clean up all tables after each test."""
    yield
    tables = [
        "solar", "load", "market", "solar_forecast", "load_forecast",
        "market_forecast", "energy_sources", "electric_vehicles",
        "households", "household_load",
    ]
    for table in tables:
        try:
            db_manager.execute(f"DELETE FROM {table};")
        except Exception:
            continue
