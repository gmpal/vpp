from fastapi import APIRouter, HTTPException
from backend.api.models import Source, DataPoint
from backend.src.streaming.sources import create_new_source
from backend.src.db import DatabaseManager, CrudManager

router = APIRouter()


@router.get("/add-source")
def add_new_source(source_type: str):
    """Endpoint to add a new renewable source."""
    try:
        _, source_id = create_new_source(source_type=source_type, kakfa_flag=True)
        return Source(source_type=source_type, source_id=source_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/source-ids/{source}", response_model=list[str])
def query_ids(source: str):
    """Query the database to retrieve available source IDs for the given source type."""
    db_manager = DatabaseManager()
    crud_manager = CrudManager(db_manager)
    return crud_manager.query_source_ids(source)
