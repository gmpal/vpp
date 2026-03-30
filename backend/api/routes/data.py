from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException

from backend.api.auth import get_current_user
from backend.api.models import DataPoint, DeviceCounts
from backend.src.db import CrudManager
from backend.src.dependencies import get_crud_manager

router = APIRouter()


@router.get("/realtime-data/{source}", response_model=List[DataPoint])
def query_realtime_data(
    source: str,
    source_id: Optional[str] = None,
    since: Optional[str] = None,
    crud: CrudManager = Depends(get_crud_manager),
    current_user: dict = Depends(get_current_user),
):
    try:
        data_list = crud.load_historical_data(source, source_id, start=since, end=None, top=100)
        return [DataPoint(timestamp=item["time"].isoformat(), value=item["value"]) for item in data_list]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/forecasted/{source}", response_model=List[DataPoint])
def query_forecasted_data(
    source: str,
    source_id: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    crud: CrudManager = Depends(get_crud_manager),
    current_user: dict = Depends(get_current_user),
):
    try:
        data_list = crud.load_forecasted_data(source, source_id, start, end)
        return [DataPoint(timestamp=item["time"].isoformat(), value=item["yhat"]) for item in data_list]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/historical/{source}", response_model=List[DataPoint])
def query_historical_data(
    source: str,
    source_id: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    top: int = 50,
    crud: CrudManager = Depends(get_crud_manager),
    current_user: dict = Depends(get_current_user),
):
    try:
        data_list = crud.load_historical_data(source, source_id, start, end, top)
        return [DataPoint(timestamp=item["time"].isoformat(), value=item["value"]) for item in data_list]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/device-status", response_model=DeviceCounts)
def query_device_counts(
    crud: CrudManager = Depends(get_crud_manager),
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["user_id"]
    solar = len(crud.query_source_ids("solar", user_id=user_id))
    wind = len(crud.query_source_ids("wind", user_id=user_id))
    return DeviceCounts(solar=solar, wind=wind)
