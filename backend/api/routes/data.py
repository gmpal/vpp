import asyncio
import json
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from backend.api.auth import get_current_user
from backend.api.models import DataPoint, DeviceCounts
from backend.src.db import CrudManager
from backend.src.dependencies import get_crud_manager

router = APIRouter()


def _parse_iso(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


@router.get("/realtime-data/{source}", response_model=List[DataPoint])
def query_realtime_data(
    source: str,
    source_id: Optional[str] = None,
    since: Optional[str] = None,
    crud: CrudManager = Depends(get_crud_manager),
    current_user: dict = Depends(get_current_user),
):
    try:
        data_list = crud.load_user_historical_data(
            source,
            user_id=current_user["user_id"],
            source_id=source_id,
            start=since,
            end=None,
            top=100,
        )
        return [DataPoint(timestamp=item["time"].isoformat(), value=item["value"]) for item in data_list]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stream-data/{source}")
async def stream_data(
    source: str,
    source_id: Optional[str] = None,
    since: Optional[str] = None,
    crud: CrudManager = Depends(get_crud_manager),
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["user_id"]

    async def event_generator():
        last_seen_iso = since
        last_seen_dt = _parse_iso(since)

        while True:
            try:
                rows = crud.load_user_historical_data(
                    source,
                    user_id=user_id,
                    source_id=source_id,
                    start=last_seen_iso,
                    end=None,
                    top=100,
                )
                rows = sorted(rows, key=lambda item: item["time"])

                emitted = False
                for row in rows:
                    row_dt = row["time"]
                    if last_seen_dt and row_dt <= last_seen_dt:
                        continue

                    payload = {
                        "timestamp": row_dt.isoformat(),
                        "value": row["value"],
                    }
                    yield f"data: {json.dumps(payload)}\\n\\n"
                    emitted = True
                    last_seen_dt = row_dt
                    last_seen_iso = payload["timestamp"]

                if not emitted:
                    yield ": keep-alive\\n\\n"

                await asyncio.sleep(1.0)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                err_payload = {"message": str(exc)}
                yield f"event: error\\ndata: {json.dumps(err_payload)}\\n\\n"
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


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
        data_list = crud.load_user_historical_data(
            source,
            user_id=current_user["user_id"],
            source_id=source_id,
            start=start,
            end=end,
            top=top,
        )
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
