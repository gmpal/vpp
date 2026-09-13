# tests/test_db_connection.py
from unittest.mock import MagicMock, Mock, patch

from backend.src.config import Settings, reset_settings
from backend.src.db.connection import DatabaseManager


def test_init_uses_settings_by_default():
    db = DatabaseManager()
    assert db.renewables == ["solar"]
    assert set(db.config) == {"host", "port", "database", "user", "password"}


def test_init_accepts_explicit_config():
    config = {"host": "db", "port": 1, "database": "d", "user": "u", "password": "p"}
    assert DatabaseManager(config).config is config


def test_settings_read_environment(monkeypatch):
    monkeypatch.setenv("POSTGRES_DB", "env_db")
    monkeypatch.setenv("POSTGRES_PORT", "6543")
    settings = Settings(_env_file=None)
    assert settings.database_config["database"] == "env_db"
    assert settings.database_config["port"] == 6543


def test_settings_have_defaults_without_environment(monkeypatch):
    for var in ("TIMESCALEDB_HOST", "POSTGRES_PORT", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD"):
        monkeypatch.delenv(var, raising=False)
    settings = Settings(_env_file=None)
    assert settings.database_config == {
        "host": "localhost",
        "port": 5432,
        "database": "postgres",
        "user": "postgres",
        "password": "postgres",
    }


def test_testing_environment_ignores_env_file(monkeypatch, tmp_path):
    (tmp_path / ".env").write_text("POSTGRES_DB=from_dotenv\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ENVIRONMENT", "testing")
    monkeypatch.delenv("POSTGRES_DB", raising=False)
    reset_settings()
    try:
        from backend.src.config import get_settings

        assert get_settings().postgres_db == "postgres"
    finally:
        reset_settings()


@patch("backend.src.db.connection.psycopg2.connect")
def test_connect_passes_config(mock_connect):
    mock_connect.return_value = Mock()
    db = DatabaseManager({"host": "h", "port": 1, "database": "d", "user": "u", "password": "p"})
    assert db.connect() is mock_connect.return_value
    mock_connect.assert_called_once_with(host="h", port=1, database="d", user="u", password="p")


def test_execute_commits_and_closes_connection():
    conn = MagicMock()
    cursor = conn.cursor.return_value.__enter__.return_value
    cursor.description = [("col",)]
    cursor.fetchall.return_value = [(1,)]
    db = DatabaseManager({"host": "h"})
    db.connect = Mock(return_value=conn)

    assert db.execute("SELECT 1", fetch=True) == [(1,)]
    cursor.execute.assert_called_once_with("SELECT 1", None)
    conn.__exit__.assert_called_once()  # psycopg2 commits on context exit
    conn.close.assert_called_once()
