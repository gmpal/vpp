from fastapi import APIRouter, HTTPException, Depends
from typing import List
from backend.api.models import AddSourceRequest, EnergySourceWithData
from backend.src.streaming.sources import create_new_source
from backend.src.db import DatabaseManager, CrudManager
from backend.src.dependencies import get_db_manager, get_crud_manager
from backend.src.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.post("/sources", response_model=EnergySourceWithData)
def add_source_with_location(
    request: AddSourceRequest,
    db: DatabaseManager = Depends(get_db_manager),
    crud: CrudManager = Depends(get_crud_manager)
):
    """Add a new solar source, optionally linked to a household."""
    try:
        _, source_id = create_new_source(
            source_type=request.source_type,
            kakfa_flag=True,
            latitude=request.latitude,
            longitude=request.longitude
        )

        name = request.name or f"{request.source_type.capitalize()} {source_id}"
        insert_query = """
        INSERT INTO energy_sources (source_id, type, latitude, longitude, name, household_id)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (source_id) DO UPDATE
        SET latitude = EXCLUDED.latitude,
            longitude = EXCLUDED.longitude,
            name = EXCLUDED.name,
            household_id = EXCLUDED.household_id
        """
        db.execute(insert_query, (source_id, request.source_type, request.latitude,
                                  request.longitude, name, request.household_id))

        logger.info(f"Created {request.source_type} source {source_id} at ({request.latitude}, {request.longitude})")

        return EnergySourceWithData(
            source_id=source_id,
            source_type=request.source_type,
            latitude=request.latitude,
            longitude=request.longitude,
            name=name,
            household_id=request.household_id,
            status="active"
        )
    except Exception as e:
        logger.error(f"Failed to create source: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sources", response_model=List[EnergySourceWithData])
def get_all_sources(
    db: DatabaseManager = Depends(get_db_manager),
    crud: CrudManager = Depends(get_crud_manager)
):
    """Get all energy sources with their locations and current production."""
    try:
        query = """
        SELECT es.source_id, es.type, es.latitude, es.longitude, es.name, es.household_id
        FROM energy_sources es
        ORDER BY es.created_at DESC
        """
        rows = db.execute(query, fetch=True) or []

        sources = []
        for row in rows:
            source_id, source_type, lat, lon, name, household_id = row

            latest_query = f"""
            SELECT value FROM {source_type}
            WHERE source_id = %s
            ORDER BY time DESC
            LIMIT 1
            """
            latest = db.execute(latest_query, (source_id,), fetch=True)
            current_value = latest[0][0] if latest and len(latest) > 0 else None

            sources.append(EnergySourceWithData(
                source_id=source_id,
                source_type=source_type,
                latitude=lat,
                longitude=lon,
                name=name,
                household_id=household_id,
                current_value=current_value,
                status="active"
            ))

        return sources
    except Exception as e:
        logger.error(f"Failed to fetch sources: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sources/{source_id}")
def delete_source(
    source_id: str,
    db: DatabaseManager = Depends(get_db_manager)
):
    """Delete an energy source and all its data."""
    try:
        type_query = "SELECT type FROM energy_sources WHERE source_id = %s"
        result = db.execute(type_query, (source_id,), fetch=True)

        if not result:
            raise HTTPException(status_code=404, detail="Source not found")

        source_type = result[0][0]

        db.execute(f"DELETE FROM {source_type} WHERE source_id = %s", (source_id,))
        db.execute(f"DELETE FROM {source_type}_forecast WHERE source_id = %s", (source_id,))
        db.execute("DELETE FROM energy_sources WHERE source_id = %s", (source_id,))

        logger.info(f"Deleted source {source_id}")
        return {"detail": "Source deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete source {source_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/source-ids/{source}", response_model=list[str])
def query_ids(source: str, crud: CrudManager = Depends(get_crud_manager)):
    """Query the database to retrieve available source IDs for the given source type."""
    return crud.query_source_ids(source)
