import pytest
import psycopg2
from backend.src.db import DatabaseManager, CrudManager, SchemaManager
from backend.api.main import app
from backend.api.auth import get_current_user

import os

from pydantic import BaseModel
import uuid

@pytest.fixture(scope="session", autouse=True)
def bypass_auth():
    """Globally bypass authentication for tests by overriding get_current_user dependency."""
    user_id = "test_user_global_id"
    app.dependency_overrides[get_current_user] = lambda: {"user_id": user_id, "id": user_id, "username": "test_user"}
    yield
    app.dependency_overrides.clear()

@pytest.fixture(scope="session", autouse=True)
def setup_test_user(schema_manager, db_manager, bypass_auth):
    """Ensure the test_user exists in the users table."""
    try:
        schema_manager._create_users_table()
    except Exception:
        pass

    try:
        # Our auth.py and DB schema expect `user_id`, not `id`
        db_manager.execute(
            "INSERT INTO users (user_id, username, hashed_password) VALUES ('test_user_global_id', 'test_user', 'fake_hash') ON CONFLICT (user_id) DO NOTHING;"
        )
        conn = db_manager.connect()
        conn.commit()
    except Exception as e:
        print(f"Test user insert failed: {e}")
    yield

DB_CONFIG = {
    "dbname": os.environ.get("POSTGRES_DB", "postgres"),
    "user": os.environ.get("POSTGRES_USER", "gmpal"),
    "password": os.environ.get("POSTGRES_PASSWORD", "postgresso"),
    "host": os.environ.get("TIMESCALEDB_HOST", "localhost"),
    "port": os.environ.get("POSTGRES_PORT", "5432"),
}


@pytest.fixture(scope="session")
def db_connection():
    """Set up a connection to a Dockerized TimescaleDB instance."""
    conn = psycopg2.connect(**DB_CONFIG)
    # Use a separate autocommit connection for DDL to avoid deadlocks
    try:
        ddl_conn = psycopg2.connect(**DB_CONFIG)
        ddl_conn.autocommit = True
        with ddl_conn.cursor() as cursor:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
        ddl_conn.close()
    except Exception as e:
        print(f"Extension creation skipped (likely already exists): {e}")
    yield conn
    conn.close()


@pytest.fixture(scope="session", autouse=True)
def db_manager(db_connection):
    """Provide a DatabaseManager instance using the test connection."""
    db = DatabaseManager()
    db.connect = lambda: db_connection  # Override connect method
    return db


@pytest.fixture(scope="session", autouse=True)
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
        "load",
        "market",
        "solar_forecast",
        "load_forecast",
        "market_forecast",
        "energy_sources",
        "electric_vehicles",
        "households",
        "household_load",
    ]
    for table in tables:
        try:
            db_manager.execute(f"DELETE FROM {table};")
        except psycopg2.errors.UndefinedTable:
            continue  # Skip if table doesn’t exist
