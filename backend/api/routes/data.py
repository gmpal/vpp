from fastapi import APIRouter, HTTPException
from typing import List
from backend.api.models import DataPoint, DeviceCounts
from backend.src.db import DatabaseManager, CrudManager

router = APIRouter()
db_manager = DatabaseManager()
crud_manager = CrudManager(db_manager)


@router.get("/forecasted/{source}", response_model=List[DataPoint])
def query_forecasted_data(
    source: str, source_id: str = None, start: str = None, end: str = None
):
    """Queries forecasted data for a given source."""
    try:
        dataframe = crud_manager.load_forecasted_data(source, source_id, start, end)
        return [
            DataPoint(timestamp=idx.isoformat(), value=row["yhat"])
            for idx, row in dataframe.iterrows()
        ]
    except Exception as e:
        print(f"Error in forecasted endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/historical/{source}", response_model=List[DataPoint])
def query_historical_data(
    source: str,
    source_id: str = None,
    start: str = None,
    end: str = None,
    top: int = 50,
):
    """Queries historical data from a specified source within a given time range."""
    try:
        dataframe = crud_manager.load_historical_data(
            source, source_id, start, end, top
        )
        return [
            DataPoint(timestamp=idx.isoformat(), value=row["value"])
            for idx, row in dataframe.iterrows()
        ]
    except Exception as e:
        print(f"Error in historical_data endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/device-status", response_model=DeviceCounts)
def query_device_counts():
    """Queries the number of devices for each type."""
    solar = len(crud_manager.query_source_ids("solar"))
    wind = len(crud_manager.query_source_ids("wind"))
    return DeviceCounts(solar=solar, wind=wind)
