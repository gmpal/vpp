import pytest
import psycopg2
from backend.src.db import DatabaseManager, CrudManager, SchemaManager


DB_CONFIG = {
    "dbname": "postgres",
    "user": "postgres",
    "password": "testpass",
    "host": "localhost",
    "port": "5432",
}


@pytest.fixture(scope="module")
def db_connection():
    """Set up a connection to a Dockerized TimescaleDB instance."""
    conn = psycopg2.connect(**DB_CONFIG)
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
    db.connect = lambda: db_connection  # Override connect method
    return db


@pytest.fixture(scope="module")
def schema_manager(db_manager):
    """Set up the schema using SchemaManager."""
    schema_mgr = SchemaManager(db_manager)
    try:
        schema_mgr.reset_all_tables()  # Create all tables and hypertables
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
    yield  # Run the test
    tables = [
        "solar",
        "wind",
        "load",
        "market",
        "batteries",
        "solar_forecast",
        "wind_forecast",
        "load_forecast",
        "market_forecast",
        "energy_sources",
    ]
    for table in tables:
        try:
            db_manager.execute(f"DELETE FROM {table};")
        except psycopg2.errors.UndefinedTable:
            continue  # Skip if table doesn’t exist
