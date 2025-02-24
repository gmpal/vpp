# tests/test_db_connection.py
import pytest
import psycopg2
from unittest.mock import patch, Mock, mock_open
from backend.src.db.connection import DatabaseManager

# Sample config content for testing
with open("db-config.ini", "w") as config_file:
    config_file.write(
        """
        [TimescaleDB]
        dbname=test_db
        user=test_user
        password=test_pass
        host=localhost
        port=5432
        """
    )


@pytest.fixture
def db_manager():
    """Fixture to create a fresh DatabaseManager instance for each test."""
    return DatabaseManager()


def test_init():
    """Test DatabaseManager initialization with default renewables."""
    db = DatabaseManager()
    assert db.renewables == ["solar", "wind"]
    assert isinstance(db.config, dict)


@patch("os.environ", {"POSTGRES_DB": "env_db"})
def test_load_config_with_env_vars(db_manager):
    """Test config loading with environment variables overriding config file."""
    config = db_manager._load_config()
    assert config["dbname"] == "env_db"  # Env var takes precedence
    assert config["user"] == "test_user"  # From config file
    assert config["password"] == "test_pass"
    assert config["host"] == "localhost"
    assert config["port"] == "5432"


@patch("os.environ", {})
def test_load_config_without_env_vars(db_manager):
    """Test config loading without environment variables."""
    config = db_manager._load_config()
    assert config["dbname"] == "test_db"  # From config file
    assert config["user"] == "test_user"
    assert config["password"] == "test_pass"
    assert config["host"] == "localhost"
    assert config["port"] == "5432"


@patch("psycopg2.connect")
def test_connect(mock_connect, db_manager):
    """Test database connection creation."""
    mock_connect.return_value = Mock()
    conn = db_manager.connect()
    assert mock_connect.called_once_with(**db_manager.config)
    assert conn is not None
