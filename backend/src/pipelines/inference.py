import mlflow
import os
import pickle
import numpy as np
import pandas as pd
from datetime import timedelta

from mlflow.tracking import MlflowClient

mlflow.set_tracking_uri(
    "http://vpp-mlflow-load-balancer-23407623.eu-central-1.elb.amazonaws.com"
)
client = MlflowClient()


from backend.src.db import (
    load_historical_data,
    save_single_forecasts_to_db,
    RENEWABLES,
    OTHER_DATASETS,
    query_source_ids,
)


import warnings

warnings.filterwarnings(
    "ignore",
    category=FutureWarning,
)


def get_datasets_list():
    """
    Returns a list of (dataset, source_id) tuples.
    For renewable datasets, we retrieve all existing source_ids in the DB.
    For non-renewable datasets (like load, market), source_id is None.
    """
    datasets_info = []

    # 1) Loop over each renewable and its source_ids
    for renewable in RENEWABLES:
        sids = query_source_ids(renewable)  # e.g., ['010780', 'XYZ', ...]
        for sid in sids:
            datasets_info.append((renewable, sid))

    # 2) Add non-renewable datasets without source_id
    for ds in OTHER_DATASETS:
        datasets_info.append((ds, None))

    return datasets_info


def inference_pipeline(
    forecast_horizon=24,
    freq="h",
    stage="None",
):
    """
    Iterates over all (dataset, source_id) pairs. For each:
      1) Loads the corresponding model from MLflow Model Registry.
      2) Loads historical data from the database.
      3) Predicts the next 'forecast_horizon' steps.
      4) (Optionally) Saves the forecast to the database.

    Parameters
    ----------
    forecast_horizon : int
        How many future steps to forecast.
    freq : str
        Frequency string for the DateTimeIndex (e.g. "H" for hourly).
    stage : str
        Model stage or version label in the MLflow Registry (e.g. "Staging", "Production", or "latest").
        Defaults to "latest".
    """

    # Get the full list of all datasets we want to forecast
    all_datasets = get_datasets_list()

    for dataset, source_id in all_datasets:
        # 1) Construct the MLflow model URI
        if source_id is not None:
            # e.g. "Best_solar_010780_Model"
            registry_name = f"Best_{dataset}_{source_id}_Model"
        else:
            # e.g. "Best_load_Model"
            registry_name = f"Best_{dataset}_Model"

        latest_version_info = client.get_latest_versions(
            registry_name, stages=["None"]
        )[0]
        latest_version = latest_version_info.version

        model_uri = f"models:/{registry_name}/{latest_version}"
        print(f"\n=== Inference for {dataset} (source_id={source_id}) ===")
        print(f"Model Registry URI: {model_uri}")

        # Attempt to download artifacts. If model not found, skip.
        try:
            local_dir = mlflow.artifacts.download_artifacts(model_uri)
        except Exception as e:
            print(f"  Could not find or download artifacts for {model_uri}. Skipping.")
            continue

        # Find the .pkl file in the downloaded artifacts
        model_file = None
        for root, dirs, files in os.walk(local_dir):
            for file in files:
                if file.endswith(".pkl"):
                    model_file = os.path.join(root, file)
                    break
            if model_file:  # once found, no need to keep searching
                break

        if not model_file:
            print("  No .pkl model file found in the artifacts. Skipping.")
            continue

        # Load the model object from the pickle file
        try:
            with open(model_file, "rb") as f:
                model = pickle.load(f)
        except Exception as e:
            print(f"  Error loading model pickle: {e}. Skipping.")
            continue

        # 2) Load historical data from DB
        df = load_historical_data(dataset, source_id)

        # revert order of df (its stored in reverse order)
        df = df.sort_index(ascending=True)

        print("Columns:", df.columns)

        if df.empty:
            print("  No historical data found in DB. Skipping forecast.")
            continue

        # 3) Predict future horizon
        try:
            forecast_series = model.predict(df, steps=forecast_horizon, freq=freq)
        except Exception as e:
            print(f"  Model prediction error: {e}. Skipping.")
            continue

        # 4) Build a DataFrame for the forecast
        df_forecast = pd.DataFrame(
            {"time": forecast_series.index, "value": forecast_series.values}
        ).set_index("time")

        print(
            f"  Forecast for next {forecast_horizon} steps:\n{df_forecast.head(10)}\n..."
        )

        # 5) (Optional) Save forecast results to DB
        save_single_forecasts_to_db(dataset, source_id, df_forecast)
        print("  (Placeholder) Forecast saved to DB.")

    print("\n=== Inference pipeline complete! ===")


if __name__ == "__main__":
    inference_pipeline(forecast_horizon=24, freq="h", stage="latest")
