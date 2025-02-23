# db/connection.py
import psycopg2
import os
import configparser


class DatabaseManager:
    def __init__(self):
        self.config = self._load_config()
        self.renewables = ["solar", "wind"]

    def _load_config(self):
        config = configparser.ConfigParser()
        config.read("db-config.ini")
        return {
            "dbname": os.environ.get("POSTGRES_DB", config["TimescaleDB"]["dbname"]),
            "user": os.environ.get("POSTGRES_USER", config["TimescaleDB"]["user"]),
            "password": os.environ.get(
                "POSTGRES_PASSWORD", config["TimescaleDB"]["password"]
            ),
            "host": os.environ.get("TIMESCALEDB_HOST", config["TimescaleDB"]["host"]),
            "port": os.environ.get("POSTGRES_PORT", config["TimescaleDB"]["port"]),
        }

    def connect(self):
        """Return a new database connection."""
        return psycopg2.connect(**self.config)

    def execute(self, query: str, params=None, fetch: bool = False):
        """Execute a query and optionally fetch results."""
        with self.connect() as conn, conn.cursor() as cursor:
            cursor.execute(query, params)
            conn.commit()
            return cursor.fetchall() if fetch and cursor.description else None
