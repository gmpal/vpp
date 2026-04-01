from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.api.auth import get_current_user
from backend.src.db import CrudManager
from backend.src.dependencies import get_crud_manager
from backend.src.optimization.optimization import optimize
from backend.src.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


class OptimizeRequest(BaseModel):
    community_id: Optional[str] = None


@router.post("/optimize", response_model=List[Dict[str, Any]])
def optimize_strategy(
    body: Optional[OptimizeRequest] = None,
    crud: CrudManager = Depends(get_crud_manager),
    current_user: dict = Depends(get_current_user),
):
    evs = crud.get_home_evs(user_id=current_user["user_id"])
    if not evs:
        raise HTTPException(400, "No EVs with status='home' available for optimization")

    # Collect stationary batteries and grid limits if a community is given
    batteries = []
    export_limit_kw = None
    import_limit_kw = None

    if body and body.community_id:
        community_id = body.community_id
        community = crud.get_community(community_id, user_id=current_user["user_id"])
        if community:
            batteries = crud.get_battery_assets_by_community(community_id)
            grid_limit = crud.get_active_grid_limit(community_id)
            if grid_limit:
                export_limit_kw = grid_limit["export_limit_kw"]
                import_limit_kw = grid_limit["import_limit_kw"]

    try:
        result_df = optimize(
            evs=evs,
            batteries=batteries,
            export_limit_kw=export_limit_kw,
            import_limit_kw=import_limit_kw,
        )
        for ev in evs:
            final_soc_rows = result_df.loc[result_df["battery_id"] == ev["vehicle_id"], "soc"]
            if not final_soc_rows.empty:
                crud.update_ev_soc(ev["vehicle_id"], float(final_soc_rows.iloc[-1]))
        # Update stationary battery SOC as well
        for bat in batteries:
            final_soc_rows = result_df.loc[result_df["battery_id"] == bat["battery_id"], "soc"]
            if not final_soc_rows.empty:
                crud.update_battery_asset_soc(bat["battery_id"], float(final_soc_rows.iloc[-1]))
        return result_df.to_dict(orient="records")
    except Exception as e:
        logger.error(f"Optimization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
