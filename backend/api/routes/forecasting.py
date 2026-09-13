import subprocess
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from backend.src.db import CrudManager
from backend.src.dependencies import get_crud_manager
from backend.src.pipelines.generation import generate_synthetic_market_price
from backend.src.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)

# Store training status
training_status = {"last_training": None, "is_training": False, "last_inference": None, "is_running_inference": False}


class TrainingStatus(BaseModel):
    last_training: Optional[str] = None
    is_training: bool = False
    last_inference: Optional[str] = None
    is_running_inference: bool = False


def run_training():
    """Run the training pipeline"""
    try:
        training_status["is_training"] = True
        result = subprocess.run(["python", "/app/backend/src/pipelines/training.py"], capture_output=True, text=True, timeout=600)
        training_status["is_training"] = False
        training_status["last_training"] = datetime.now().isoformat()
        return result.returncode == 0
    except Exception as e:
        training_status["is_training"] = False
        logger.error(f"Training error: {e}")
        return False


def run_inference():
    """Run the inference pipeline"""
    try:
        training_status["is_running_inference"] = True
        result = subprocess.run(["python", "/app/backend/src/pipelines/inference.py"], capture_output=True, text=True, timeout=300)
        training_status["is_running_inference"] = False
        training_status["last_inference"] = datetime.now().isoformat()
        return result.returncode == 0
    except Exception as e:
        training_status["is_running_inference"] = False
        logger.error(f"Inference error: {e}")
        return False


@router.post("/forecasting/train")
async def trigger_training(background_tasks: BackgroundTasks):
    """Trigger model training in the background"""
    if training_status["is_training"]:
        raise HTTPException(status_code=400, detail="Training already in progress")

    background_tasks.add_task(run_training)
    return {"message": "Training started", "status": training_status}


@router.post("/forecasting/inference")
async def trigger_inference(background_tasks: BackgroundTasks):
    """Trigger inference in the background"""
    if training_status["is_running_inference"]:
        raise HTTPException(status_code=400, detail="Inference already in progress")

    background_tasks.add_task(run_inference)
    return {"message": "Inference started", "status": training_status}


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
