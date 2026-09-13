from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException

from backend.src.db import CrudManager
from backend.src.dependencies import get_crud_manager
from backend.src.optimization.optimization import OptimizationDataError, optimize
from backend.src.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.post("/optimize", response_model=List[Dict[str, Any]])
def optimize_strategy(
    crud: CrudManager = Depends(get_crud_manager),
):
    evs = crud.get_home_evs()
    if not evs:
        raise HTTPException(400, "No EVs with status='home' available for optimization")

    try:
        result_df = optimize(evs=evs, crud=crud)
        for ev in evs:
            final_soc_rows = result_df.loc[result_df["battery_id"] == ev["vehicle_id"], "soc"]
            if not final_soc_rows.empty:
                crud.update_ev_soc(ev["vehicle_id"], float(final_soc_rows.iloc[-1]))
        return result_df.to_dict(orient="records")
    except OptimizationDataError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Optimization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
