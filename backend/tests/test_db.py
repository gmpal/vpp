import os
import pandas as pd
from unittest.mock import patch, Mock
import pytest
from src.db import _connect, reset_tables, load_energy_sources, save_to_db


# Fixture for mocking database connection
@pytest.fixture
def mock_connect():
    with patch("db.psycopg2.connect") as mock:
        yield mock


# Fixture for mocking environment variables
@pytest.fixture
def mock_env():
    with patch.dict(
        os.environ,
        {
            "POSTGRES_DB": "test_db",
            "POSTGRES_USER": "test_user",
            "POSTGRES_PASSWORD": "test_pass",
            "TIMESCALEDB_HOST": "timescaledb",
            "POSTGRES_PORT": "5432",
        },
    ):
        yield


# Test database connection
def test_connect(mock_connect, mock_env):
    conn = _connect()
    mock_connect.assert_called_once_with(
        dbname="test_db",
        user="test_user",
        password="test_pass",
        host="timescaledb",
        port="5432",
    )
    assert conn == mock_connect.return_value


# Test table reset
def test_reset_tables(mock_connect):
    mock_conn = mock_connect.return_value
    mock_cursor = Mock()
    mock_conn.cursor.return_value = mock_cursor

    reset_tables()

    expected_tables = ["energy_sources", "solar", "wind", "load"]
    executed_queries = [call[0][0] for call in mock_cursor.execute.call_args_list]
    for table in expected_tables:
        assert any(f"CREATE TABLE {table}" in query for query in executed_queries)
    mock_conn.commit.assert_called()
    mock_cursor.close.assert_called()
    mock_conn.close.assert_called()


# Test loading energy sources
def test_load_energy_sources(mock_connect):
    mock_conn = mock_connect.return_value
    mock_cursor = Mock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchall.return_value = [
        ("source1", "solar", 40.7128, -74.0060, "Solar 1")
    ]

    result = load_energy_sources()

    mock_cursor.execute.assert_called_once()
    expected = [
        {
            "source_id": "source1",
            "type": "solar",
            "latitude": 40.7128,
            "longitude": -74.0060,
            "name": "Solar 1",
        }
    ]
    assert result == expected


# Test saving data to the database
def test_save_to_db(mock_connect):
    mock_conn = mock_connect.return_value
    mock_cursor = Mock()
    mock_conn.cursor.return_value = mock_cursor

    timestamp = pd.Timestamp("2023-01-01 00:00:00+00")
    save_to_db("solar", timestamp, "source1", 100.5)

    mock_cursor.execute.assert_called_once_with(
        "INSERT INTO solar (time, source_id, value) VALUES (%s, %s, %s)",
        (timestamp, "source1", 100.5),
    )
    mock_conn.commit.assert_called()
