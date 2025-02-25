from backend.src.pipelines.inference import inference_pipeline
from backend.src.db import reset_all_forecast_tables

if __name__ == "__main__":
    reset_all_forecast_tables()
    inference_pipeline()
