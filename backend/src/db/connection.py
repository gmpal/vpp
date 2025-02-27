# db/connection.py
import psycopg2
import os
from configparser import ConfigParser, NoSectionError


class DatabaseManager:
    def __init__(self):
        self.config = self._load_config()
        self.renewables = ["solar", "wind"]

    def _load_config(self):
        # Start with defaults from environment variables
        config = {
            "host": os.environ.get("TIMESCALEDB_HOST", "localhost"),
            "port": os.environ.get("POSTGRES_PORT", "5432"),
            "dbname": os.environ.get("POSTGRES_DB", "postgres"),
            "user": os.environ.get("POSTGRES_USER", "postgres"),
            "password": os.environ.get("POSTGRES_PASSWORD", "password"),
        }

        # Optionally load from config file if it exists
        config_parser = ConfigParser()
        config_file = "/app/config.ini"  # Adjust path as needed
        if os.path.exists(config_file):
            config_parser.read(config_file)
            try:
                timescale_config = config_parser["TimescaleDB"]
                # Update config with file values only if they exist
                config.update(
                    {
                        "host": timescale_config.get("host", config["host"]),
                        "port": timescale_config.get("port", config["port"]),
                        "dbname": timescale_config.get("dbname", config["dbname"]),
                        "user": timescale_config.get("user", config["user"]),
                        "password": timescale_config.get(
                            "password", config["password"]
                        ),
                    }
                )
            except NoSectionError:
                # Ignore if TimescaleDB section is missing
                pass

        return config

    def connect(self):
        """Return a new database connection."""
        return psycopg2.connect(**self.config)

    def execute(self, query: str, params=None, fetch: bool = False):
        """Execute a query and optionally fetch results."""
        with self.connect() as conn, conn.cursor() as cursor:
            cursor.execute(query, params)
            conn.commit()
            return cursor.fetchall() if fetch and cursor.description else None
