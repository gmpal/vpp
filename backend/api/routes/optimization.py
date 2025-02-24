from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from backend.src.optimization.optimization import optimize  # TODO: cleaner path
from backend.api.routes.batteries import batteries  # Import batteries store

router = APIRouter()


@router.post("/optimize", response_model=List[Dict[str, Any]])
def optimize_strategy():
    """Optimizes the dispatch strategy."""
    if not batteries:
        raise HTTPException(
            status_code=400, detail="No batteries available for optimization"
        )
    try:
        result_df = optimize(list(batteries.values()))
        return result_df.to_dict(orient="records")
    except Exception as e:
        print(f"Optimization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
