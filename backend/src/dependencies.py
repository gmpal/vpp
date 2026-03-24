"""
Dependency injection providers for FastAPI.
Use these to inject database managers and other dependencies into route handlers.
"""
from typing import Generator
from backend.src.db import DatabaseManager, CrudManager, SchemaManager
from backend.src.config import get_settings


# Singleton instances (to be replaced with proper DI pattern)
_db_manager: DatabaseManager = None
_crud_manager: CrudManager = None
_schema_manager: SchemaManager = None


def get_db_manager() -> DatabaseManager:
    """
    Get or create DatabaseManager singleton.

    Usage in FastAPI routes:
        @router.get("/endpoint")
        def my_endpoint(db: DatabaseManager = Depends(get_db_manager)):
            # Use db here
    """
    global _db_manager
    if _db_manager is None:
        settings = get_settings()
        _db_manager = DatabaseManager()
    return _db_manager


def get_crud_manager() -> CrudManager:
    """
    Get or create CrudManager singleton.

    Usage in FastAPI routes:
        @router.get("/endpoint")
        def my_endpoint(crud: CrudManager = Depends(get_crud_manager)):
            # Use crud here
    """
    global _crud_manager
    if _crud_manager is None:
        db = get_db_manager()
        _crud_manager = CrudManager(db)
    return _crud_manager


def get_schema_manager() -> SchemaManager:
    """
    Get or create SchemaManager singleton.

    Usage in FastAPI routes:
        @router.get("/endpoint")
        def my_endpoint(schema: SchemaManager = Depends(get_schema_manager)):
            # Use schema here
    """
    global _schema_manager
    if _schema_manager is None:
        db = get_db_manager()
        _schema_manager = SchemaManager(db)
    return _schema_manager


def get_db_connection():
    """
    Get a database connection with proper cleanup.
    Yields a connection and ensures it's closed after use.

    Usage in FastAPI routes:
        @router.get("/endpoint")
        def my_endpoint(conn = Depends(get_db_connection)):
            # Use conn here
            # Connection will be automatically closed when done
    """
    db = get_db_manager()
    conn = db.connect()
    try:
        yield conn
    finally:
        conn.close()
