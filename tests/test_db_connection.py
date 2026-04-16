# tests/test_db_connection.py
import pytest
import psycopg2
from unittest.mock import patch, Mock
from backend.src.db.connection import DatabaseManager


def test_init():
    """Test DatabaseManager initialization with default renewables."""
    db = DatabaseManager()
    assert db.renewables == ["solar", "wind"]
    assert isinstance(db.config, dict)


def test_config_has_required_keys():
    """Test that the config dict contains expected database connection keys."""
    db = DatabaseManager()
    config = db.config
    # DatabaseManager.config comes from settings.database_config
    assert "host" in config
    assert "port" in config
    assert "user" in config
    assert "password" in config


def test_config_override():
    """Test DatabaseManager initialization with explicit config override."""
    custom_config = {
        "host": "testhost",
        "port": 5432,
        "database": "testdb",
        "user": "testuser",
        "password": "testpass",
    }
    db = DatabaseManager(config=custom_config)
    assert db.config == custom_config
    assert db.config["host"] == "testhost"
    assert db.config["user"] == "testuser"


@patch("psycopg2.connect")
def test_connect(mock_connect):
    """Test database connection creation."""
    mock_connect.return_value = Mock()
    db = DatabaseManager()
    conn = db.connect()
    assert mock_connect.called
    assert conn is not None
