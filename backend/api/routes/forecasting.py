from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
import subprocess
import os
from datetime import datetime
from backend.src.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)

# Store training status
training_status = {
    "last_training": None,
    "is_training": False,
    "last_inference": None,
    "is_running_inference": False
}

class TrainingStatus(BaseModel):
    last_training: Optional[str] = None
    is_training: bool = False
    last_inference: Optional[str] = None
    is_running_inference: bool = False

def run_training():
    """Run the training pipeline"""
    try:
        training_status["is_training"] = True
        result = subprocess.run(
            ["python", "/app/backend/src/pipelines/training.py"],
            capture_output=True,
            text=True,
            timeout=600
        )
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
        result = subprocess.run(
            ["python", "/app/backend/src/pipelines/inference.py"],
            capture_output=True,
            text=True,
            timeout=300
        )
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
async def generate_system_data():
    """Generate load and market data and write directly to database"""
    try:
        from backend.src.pipelines.generation import generate_synthetic_load_data, generate_synthetic_market_price
        from backend.src.db import DatabaseManager, CrudManager
        import pandas as pd

        # Generate data
        load_series = generate_synthetic_load_data(num_days=100, output_path=None, freq='h')
        market_series = generate_synthetic_market_price(num_days=100, output_path=None, freq='h')

        # Write directly to database
        db = DatabaseManager()
        crud = CrudManager(db)

        # Convert to format expected by save_to_db
        load_count = 0
        for timestamp, value in load_series.items():
            crud.save_to_db('load', timestamp, None, value)
            load_count += 1

        market_count = 0
        for timestamp, value in market_series.items():
            crud.save_to_db('market', timestamp, None, value)
            market_count += 1

        return {
            "message": "System data generated and saved to database",
            "load_points": load_count,
            "market_points": market_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
