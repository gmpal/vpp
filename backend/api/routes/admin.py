import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from backend.src.db import CrudManager, DatabaseManager, SchemaManager
from backend.src.dependencies import get_schema_manager
from backend.src.pipelines.generation import generate_synthetic_market_price
from backend.src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post("/admin/init-db")
def init_db(schema_manager: SchemaManager = Depends(get_schema_manager)):
    """Creates all tables if they don't exist and seeds market data if the table is empty.
    Load data is not seeded here — it is derived from household consumption."""
    try:
        schema_manager.init_all_tables()

        db = DatabaseManager()
        crud = CrudManager(db)

        market_count = 0
        existing_market = db.execute("SELECT COUNT(*) FROM market", fetch=True)
        if not existing_market or existing_market[0][0] == 0:
            market_series = generate_synthetic_market_price(num_days=100, output_path=None, freq="h")
            for timestamp, value in market_series.items():
                crud.save_to_db("market", timestamp, None, value)
                market_count += 1

        return {
            "message": "Database initialized successfully",
            "market_points_seeded": market_count,
        }
    except Exception as e:
        logger.error(f"Error in init-db endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/reset-db")
def reset_db(schema_manager: SchemaManager = Depends(get_schema_manager)):
    """Resets all database tables and seeds market data.
    Load data is not seeded — it is derived from household consumption."""
    try:
        schema_manager.reset_all_tables()

        db = DatabaseManager()
        crud = CrudManager(db)

        market_series = generate_synthetic_market_price(num_days=100, output_path=None, freq="h")
        market_count = 0
        for timestamp, value in market_series.items():
            crud.save_to_db("market", timestamp, None, value)
            market_count += 1

        return {
            "message": "Database reset successfully",
            "market_points": market_count,
        }
    except Exception as e:
        logger.error(f"Error in reset-db endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _event(step: str, status: str, **kwargs) -> str:
    return f"data: {json.dumps({'step': step, 'status': status, **kwargs})}\n\n"


@router.post("/admin/init-db-stream")
def init_db_stream(schema_manager: SchemaManager = Depends(get_schema_manager)):
    """SSE endpoint that streams init-db progress step by step."""

    def generate():
        try:
            yield _event("Creating database tables", "running")
            schema_manager.init_all_tables()
            yield _event("Creating database tables", "done")

            db = DatabaseManager()
            crud = CrudManager(db)

            yield _event("Seeding market data", "running")
            market_count = 0
            existing_market = db.execute("SELECT COUNT(*) FROM market", fetch=True)
            if not existing_market or existing_market[0][0] == 0:
                market_series = generate_synthetic_market_price(num_days=100, output_path=None, freq="h")
                for timestamp, value in market_series.items():
                    crud.save_to_db("market", timestamp, None, value)
                    market_count += 1
            yield _event("Seeding market data", "done", count=market_count)

            yield _event("complete", "done")
        except Exception as e:
            logger.error(f"Error in init-db-stream: {e}")
            yield _event("error", "error", message=str(e))

    return StreamingResponse(generate(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
