import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from backend.src.db import CrudManager
from backend.src.dependencies import get_crud_manager
from backend.src.pipelines.generation import generate_synthetic_market_price
from backend.src.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
ERROR_TAIL_CHARS = 2000

# name -> (status key prefix, module, timeout in seconds)
PIPELINES = {
    "training": ("training", "backend.src.pipelines.training", 600),
    "inference": ("inference", "backend.src.pipelines.inference", 300),
}

# In-process status of the last pipeline runs (reset on restart).
training_status = {
    "last_training": None,
    "is_training": False,
    "last_training_ok": None,
    "last_training_error": None,
    "last_inference": None,
    "is_running_inference": False,
    "last_inference_ok": None,
    "last_inference_error": None,
}
_RUNNING_KEY = {"training": "is_training", "inference": "is_running_inference"}


class TrainingStatus(BaseModel):
    last_training: Optional[str] = None
    is_training: bool = False
    last_training_ok: Optional[bool] = None
    last_training_error: Optional[str] = None
    last_inference: Optional[str] = None
    is_running_inference: bool = False
    last_inference_ok: Optional[bool] = None
    last_inference_error: Optional[str] = None


def _run_pipeline(name: str) -> bool:
    """Run a pipeline module in a subprocess and record whether it succeeded.

    ``last_<name>`` is the finish time (UTC), ``last_<name>_ok`` the outcome and
    ``last_<name>_error`` the tail of stderr (or the exception) when it failed.
    """
    prefix, module, timeout = PIPELINES[name]
    ok, error = False, None
    try:
        result = subprocess.run(
            [sys.executable, "-m", module], cwd=REPO_ROOT, capture_output=True, text=True, timeout=timeout
        )
        ok = result.returncode == 0
        if not ok:
            output = (result.stderr or result.stdout or "").strip()
            error = f"exit code {result.returncode}: {output[-ERROR_TAIL_CHARS:]}"
    except subprocess.TimeoutExpired:
        error = f"timed out after {timeout} s"
    except Exception as e:
        error = str(e)
    finally:
        training_status[_RUNNING_KEY[name]] = False
        training_status[f"last_{prefix}"] = datetime.now(timezone.utc).isoformat()
        training_status[f"last_{prefix}_ok"] = ok
        training_status[f"last_{prefix}_error"] = error

    if ok:
        logger.info("%s pipeline finished successfully", name)
    else:
        logger.error("%s pipeline failed: %s", name, error)
    return ok


def run_training():
    """Run the training pipeline."""
    return _run_pipeline("training")


def run_inference():
    """Run the inference pipeline."""
    return _run_pipeline("inference")


def _start(name: str, task, background_tasks: BackgroundTasks) -> dict:
    running_key = _RUNNING_KEY[name]
    if training_status[running_key]:
        raise HTTPException(status_code=400, detail=f"{name.capitalize()} already in progress")
    # Mark as running before scheduling so a second request cannot start a parallel run.
    training_status[running_key] = True
    background_tasks.add_task(task)
    return {"message": f"{name.capitalize()} started", "status": training_status}


@router.post("/forecasting/train")
async def trigger_training(background_tasks: BackgroundTasks):
    """Trigger model training in the background"""
    return _start("training", run_training, background_tasks)


@router.post("/forecasting/inference")
async def trigger_inference(background_tasks: BackgroundTasks):
    """Trigger inference in the background"""
    return _start("inference", run_inference, background_tasks)


@router.get("/forecasting/status", response_model=TrainingStatus)
async def get_training_status():
    """Get current training/inference status"""
    return TrainingStatus(**training_status)


@router.post("/data/generate-system-data")
def generate_system_data(crud: CrudManager = Depends(get_crud_manager)):
    """Regenerate synthetic market prices and rebuild the aggregate load table.

    Load is not generated here: it is the sum of household consumption, so the
    ``load`` table is rebuilt from ``household_load`` instead of receiving synthetic
    rows that the next household change would wipe. Market prices replace the
    existing ones, so calling this twice does not duplicate data.
    """
    try:
        market_series = generate_synthetic_market_price(num_days=100, output_path=None, freq="h")
        market_count = crud.save_series("market", market_series, replace=True)
        crud.rebuild_aggregated_load()
        load_count = crud.db.execute("SELECT COUNT(*) FROM load", fetch=True)[0][0]
        return {
            "message": "Market prices regenerated and load rebuilt from households",
            "market_points": market_count,
            "load_points": load_count,
        }
    except Exception as e:
        logger.error(f"Error generating system data: {e}")
        raise HTTPException(status_code=500, detail=str(e))
