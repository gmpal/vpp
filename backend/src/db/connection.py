# db/connection.py
import psycopg2

from backend.src.config import get_settings


class DatabaseManager:
    def __init__(self, config=None):
        """
        Initialize DatabaseManager with optional config override.

        Args:
            config: Optional dict with database config (for testing).
                   If None, uses centralized settings from config.py.
        """
        if config is None:
            settings = get_settings()
            self.config = settings.database_config
        else:
            self.config = config

        self.renewables = ["solar", "wind"]

    def connect(self):
        """Return a new database connection."""
        return psycopg2.connect(**self.config)

    def execute(self, query: str, params=None, fetch: bool = False):
        """Execute a query and optionally fetch results."""
        with self.connect() as conn, conn.cursor() as cursor:
            cursor.execute(query, params)
            conn.commit()
            return cursor.fetchall() if fetch and cursor.description else None
