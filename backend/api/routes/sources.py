import asyncio
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from backend.api.models import AddSourceRequest, EnergySourceWithData
from backend.src.db import CrudManager, DatabaseManager
from backend.src.dependencies import get_crud_manager, get_db_manager
from backend.src.streaming.simulator_manager import SimulatorManager
from backend.src.streaming.sources import create_new_source
from backend.src.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)

# The event loop only keeps weak references to tasks, so hold them until done.
_background_tasks: set[asyncio.Task] = set()


def _schedule(coro) -> None:
    """Run a coroutine in the background on the current event loop."""
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


@router.post("/sources", response_model=EnergySourceWithData)
async def add_source_with_location(
    request: AddSourceRequest,
    db: DatabaseManager = Depends(get_db_manager),
    crud: CrudManager = Depends(get_crud_manager),
):
    try:
        if request.community_id and not crud.get_community(request.community_id):
            raise HTTPException(status_code=404, detail="Community not found")

        _, source_id = create_new_source(
            source_type=request.source_type,
            kakfa_flag=True,
            latitude=request.latitude,
            longitude=request.longitude,
        )
        name = request.name or f"{request.source_type.capitalize()} {source_id}"
        db.execute(
            """
            INSERT INTO energy_sources (source_id, type, latitude, longitude, name, household_id, community_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (source_id) DO UPDATE
            SET latitude = EXCLUDED.latitude, longitude = EXCLUDED.longitude,
                name = EXCLUDED.name, household_id = EXCLUDED.household_id,
                community_id = EXCLUDED.community_id
        """,
            (source_id, request.source_type, request.latitude, request.longitude, name, request.household_id, request.community_id),
        )

        # Start device simulator when community_id is present
        if request.community_id:
            _schedule(
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
):
    try:
        rows = (
            db.execute(
                """
            SELECT es.source_id, es.type, es.latitude, es.longitude, es.name, es.household_id
            FROM energy_sources es
            ORDER BY es.created_at DESC
        """,
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
async def delete_source(
    source_id: str,
    db: DatabaseManager = Depends(get_db_manager),
):
    try:
        result = db.execute(
            "SELECT type FROM energy_sources WHERE source_id = %s",
            (source_id,),
            fetch=True,
        )
        if not result:
            raise HTTPException(404, "Source not found")
        source_type = result[0][0]
        db.execute(f"DELETE FROM {source_type} WHERE source_id = %s", (source_id,))
        db.execute(f"DELETE FROM {source_type}_forecast WHERE source_id = %s", (source_id,))
        db.execute("DELETE FROM energy_sources WHERE source_id = %s", (source_id,))
        # Stop simulator if running
        _schedule(SimulatorManager.stop_simulator(source_id))
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
):
    return crud.query_source_ids(source)
