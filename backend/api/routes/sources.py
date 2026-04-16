import asyncio
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from backend.api.auth import get_current_user
from backend.api.models import AddSourceRequest, EnergySourceWithData
from backend.src.db import CrudManager, DatabaseManager
from backend.src.dependencies import get_crud_manager, get_db_manager
from backend.src.streaming.simulator_manager import SimulatorManager
from backend.src.streaming.sources import create_new_source
from backend.src.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.post("/sources", response_model=EnergySourceWithData)
def add_source_with_location(
    request: AddSourceRequest,
    db: DatabaseManager = Depends(get_db_manager),
    crud: CrudManager = Depends(get_crud_manager),
    current_user: dict = Depends(get_current_user),
):
    try:
        # Verify community ownership when community_id is provided
        if request.community_id:
            community = crud.get_community(
                community_id=request.community_id,
                manager_user_id=current_user["user_id"],
            )
            if not community:
                raise HTTPException(status_code=403, detail="Community not found or access denied")

        _, source_id = create_new_source(
            source_type=request.source_type,
            kakfa_flag=True,
            latitude=request.latitude,
            longitude=request.longitude,
        )
        name = request.name or f"{request.source_type.capitalize()} {source_id}"
        db.execute(
            """
            INSERT INTO energy_sources (source_id, type, latitude, longitude, name, household_id, user_id, community_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (source_id) DO UPDATE
            SET latitude = EXCLUDED.latitude, longitude = EXCLUDED.longitude,
                name = EXCLUDED.name, household_id = EXCLUDED.household_id,
                user_id = EXCLUDED.user_id, community_id = EXCLUDED.community_id
        """,
            (source_id, request.source_type, request.latitude, request.longitude, name, request.household_id, current_user["user_id"], request.community_id),
        )

        # Start device simulator when community_id is present
        if request.community_id:
            asyncio.create_task(
                SimulatorManager.start_simulator(
                    source_id=source_id,
                    source_type=request.source_type,
                    community_id=request.community_id,
                    latitude=request.latitude,
                    longitude=request.longitude,
                )
            )

        return EnergySourceWithData(
            source_id=source_id,
            source_type=request.source_type,
            latitude=request.latitude,
            longitude=request.longitude,
            name=name,
            household_id=request.household_id,
            status="active",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create source: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sources", response_model=List[EnergySourceWithData])
def get_all_sources(
    db: DatabaseManager = Depends(get_db_manager),
    current_user: dict = Depends(get_current_user),
):
    try:
        rows = (
            db.execute(
                """
            SELECT es.source_id, es.type, es.latitude, es.longitude, es.name, es.household_id
            FROM energy_sources es
            WHERE es.user_id = %s
            ORDER BY es.created_at DESC
        """,
                (current_user["user_id"],),
                fetch=True,
            )
            or []
        )

        sources = []
        for source_id, source_type, lat, lon, name, household_id in rows:
            latest = db.execute(
                f"SELECT value FROM {source_type} WHERE source_id = %s ORDER BY time DESC LIMIT 1",
                (source_id,),
                fetch=True,
            )
            sources.append(
                EnergySourceWithData(
                    source_id=source_id,
                    source_type=source_type,
                    latitude=lat,
                    longitude=lon,
                    name=name,
                    household_id=household_id,
                    current_value=latest[0][0] if latest else None,
                    status="active",
                )
            )
        return sources
    except Exception as e:
        logger.error(f"Failed to fetch sources: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sources/{source_id}")
def delete_source(
    source_id: str,
    db: DatabaseManager = Depends(get_db_manager),
    current_user: dict = Depends(get_current_user),
):
    try:
        result = db.execute(
            "SELECT type FROM energy_sources WHERE source_id = %s AND user_id = %s",
            (source_id, current_user["user_id"]),
            fetch=True,
        )
        if not result:
            raise HTTPException(404, "Source not found")
        source_type = result[0][0]
        db.execute(f"DELETE FROM {source_type} WHERE source_id = %s", (source_id,))
        db.execute(f"DELETE FROM {source_type}_forecast WHERE source_id = %s", (source_id,))
        db.execute("DELETE FROM energy_sources WHERE source_id = %s", (source_id,))
        # Stop simulator if running
        asyncio.create_task(SimulatorManager.stop_simulator(source_id))
        return {"detail": "Source deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete source {source_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/source-ids/{source}", response_model=list[str])
def query_ids(
    source: str,
    crud: CrudManager = Depends(get_crud_manager),
    current_user: dict = Depends(get_current_user),
):
    return crud.query_source_ids(source, user_id=current_user["user_id"])
