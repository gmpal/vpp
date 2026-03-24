from fastapi import APIRouter, HTTPException, Depends
from backend.src.db import SchemaManager, DatabaseManager, CrudManager
from backend.src.dependencies import get_schema_manager
from backend.src.utils.logger import get_logger

logger = get_logger(__name__)
from backend.src.pipelines.generation import (
    generate_synthetic_load_data,
    generate_synthetic_market_price,
)

router = APIRouter()


@router.post("/admin/init-db")
def init_db(schema_manager: SchemaManager = Depends(get_schema_manager)):
    """Creates all tables if they don't exist and seeds load/market data if those tables are empty."""
    try:
        schema_manager.init_all_tables()

        db = DatabaseManager()
        crud = CrudManager(db)

        # Seed only if tables are empty to avoid duplicating data
        load_count = 0
        market_count = 0

        existing_load = db.execute("SELECT COUNT(*) FROM load", fetch=True)
        if not existing_load or existing_load[0][0] == 0:
            load_series = generate_synthetic_load_data(num_days=100, output_path=None, freq='h')
            for timestamp, value in load_series.items():
                crud.save_to_db('load', timestamp, None, value)
                load_count += 1

        existing_market = db.execute("SELECT COUNT(*) FROM market", fetch=True)
        if not existing_market or existing_market[0][0] == 0:
            market_series = generate_synthetic_market_price(num_days=100, output_path=None, freq='h')
            for timestamp, value in market_series.items():
                crud.save_to_db('market', timestamp, None, value)
                market_count += 1

        return {
            "message": "Database initialized successfully",
            "load_points_seeded": load_count,
            "market_points_seeded": market_count,
        }
    except Exception as e:
        logger.error(f"Error in init-db endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/reset-db")
def reset_db(schema_manager: SchemaManager = Depends(get_schema_manager)):
    """Resets all database tables and seeds baseline load/market system data."""
    try:
        schema_manager.reset_all_tables()

        # Seed baseline profiles immediately so /profiles has data after a reset
        load_series = generate_synthetic_load_data(num_days=100, output_path=None, freq='h')
        market_series = generate_synthetic_market_price(num_days=100, output_path=None, freq='h')

        db = DatabaseManager()
        crud = CrudManager(db)

        load_count = 0
        for timestamp, value in load_series.items():
            crud.save_to_db('load', timestamp, None, value)
            load_count += 1

        market_count = 0
        for timestamp, value in market_series.items():
            crud.save_to_db('market', timestamp, None, value)
            market_count += 1

        return {
            "message": "Database reset successfully and baseline system data generated",
            "load_points": load_count,
            "market_points": market_count,
        }
    except Exception as e:
        logger.error(f"Error in reset-db endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))
