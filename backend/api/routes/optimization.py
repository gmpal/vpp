from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from backend.src.optimization.optimization import optimize
from backend.src.storage.battery import Battery
from backend.src.db import CrudManager
from backend.src.dependencies import get_crud_manager
from backend.src.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.post("/optimize", response_model=List[Dict[str, Any]])
def optimize_strategy(crud: CrudManager = Depends(get_crud_manager)):
    """Optimizes dispatch using home EVs as virtual batteries."""
    home_ev_rows = crud.get_home_evs()
    if not home_ev_rows:
        raise HTTPException(
            status_code=400,
            detail="No EVs with status='home' available for optimization"
        )

    batteries = [
        Battery(
            battery_id=ev["vehicle_id"],
            capacity_kWh=ev["capacity_kwh"],
            current_soc_kWh=ev["soc_kwh"],
            max_charge_kW=ev["max_charge_kw"],
            max_discharge_kW=ev["max_discharge_kw"],
            round_trip_efficiency=ev["eta"],
        )
        for ev in home_ev_rows
    ]

    try:
        result_df = optimize(batteries=batteries)

        # Write optimized final SOC back to each EV
        for bat in batteries:
            final_soc_rows = result_df.loc[result_df["battery_id"] == bat.battery_id, "soc"]
            if not final_soc_rows.empty:
                crud.update_ev_soc(bat.battery_id, float(final_soc_rows.iloc[-1]))

        return result_df.to_dict(orient="records")
    except Exception as e:
        logger.error(f"Optimization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
