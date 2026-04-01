from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException

from backend.api.auth import get_current_user
from backend.src.db import CrudManager
from backend.src.dependencies import get_crud_manager
from backend.src.optimization.optimization import optimize
from backend.src.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.post("/optimize", response_model=List[Dict[str, Any]])
def optimize_strategy(
    crud: CrudManager = Depends(get_crud_manager),
    current_user: dict = Depends(get_current_user),
):
    evs = crud.get_home_evs(user_id=current_user["user_id"])
    batteries = crud.get_home_batteries(user_id=current_user["user_id"])
    storage_assets = evs + batteries
    if not storage_assets:
        raise HTTPException(400, "No storage assets (EVs at home or batteries) available for optimization")

    try:
        result_df = optimize(evs=storage_assets)
        for ev in evs:
            final_soc_rows = result_df.loc[result_df["battery_id"] == ev["vehicle_id"], "soc"]
            if not final_soc_rows.empty:
                crud.update_ev_soc(ev["vehicle_id"], float(final_soc_rows.iloc[-1]))
        for bat in batteries:
            final_soc_rows = result_df.loc[result_df["battery_id"] == bat["vehicle_id"], "soc"]
            if not final_soc_rows.empty:
                crud.update_battery_soc(bat["vehicle_id"], float(final_soc_rows.iloc[-1]))
        return result_df.to_dict(orient="records")
    except Exception as e:
        logger.error(f"Optimization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
