import mlflow
from mlflow.tracking import MlflowClient
from backend.src.db import DatabaseManager, CrudManager, SchemaManager
import os
import pickle
import pandas as pd
import warnings

warnings.filterwarnings(
    "ignore",
    category=FutureWarning,
)

mlflow.set_tracking_uri("http://mlflow:5000")
print(f"MLflow tracking URI set to: {mlflow.get_tracking_uri()}")

client = MlflowClient()
db_manager = DatabaseManager()
crud_manager = CrudManager(db_manager)
schema_manager = SchemaManager(db_manager)


def get_datasets_list():
    """
    Returns a list of (dataset, source_id) tuples.
    For renewable datasets, we retrieve all existing source_ids in the DB.
    For non-renewable datasets (like load, market), source_id is None.
    """
    datasets_info = []

    # 1) Loop over each renewable and its source_ids
    for renewable in db_manager.renewables:
        sids = crud_manager.query_source_ids(renewable)  # e.g., ['010780', 'XYZ', ...]
        for sid in sids:
            datasets_info.append((renewable, sid))

    # 2) Add non-renewable datasets without source_id
    for ds in ["load", "market"]:
        datasets_info.append((ds, None))

    return datasets_info


def _load_model_from_registry(dataset, source_id):
    """
    Load a model from the registry based on the dataset and source ID.
    This function constructs a registry name based on the provided dataset and source ID,
    retrieves the latest version of the model from the registry, and attempts to download
    the model artifacts. It looks for a .pkl file in the downloaded artifacts and loads
    the model using pickle.
    Args:
        dataset (str): The name of the dataset.
        source_id (str or None): The source identifier. If None, the registry name will not include the source ID.
    Returns:
        model: The loaded model object if successful, or None if the model could not be loaded.
    """

    registry_name = (
        f"Best_{dataset}_{source_id}_Model" if source_id else f"Best_{dataset}_Model"
    )

    latest_version_info = client.get_latest_versions(registry_name, stages=["None"])[
        0
    ].version

    model_uri = f"models:/{registry_name}/{latest_version_info}"

    # Attempt to download artifacts. If model not found, skip.
    try:
        local_dir = mlflow.artifacts.download_artifacts(model_uri)

        # Find the .pkl file in the downloaded artifacts
        model_file = None
        for root, _, files in os.walk(local_dir):
            for file in files:
                if file.endswith(".pkl"):
                    model_file = os.path.join(root, file)
                    break
            if model_file:  # once found, no need to keep searching
                break

        if not model_file:
            print("  No .pkl model file found in the artifacts. Skipping.")
            return None

        with open(model_file, "rb") as f:
            model = pickle.load(f)
    except Exception as e:
        print(f"  Error loading model pickle: {e}. Skipping.")
        return None

    return model


def _load_historical_data(dataset, source_id):
    """
    Load historical data from the database for a given dataset and source ID.
    This function retrieves historical data from the database using the provided
    dataset and source ID. The data is then sorted in ascending order based on
    the index, as it is stored in reverse order in the database. If no historical
    data is found, the function prints a message and returns None.
    Args:
        dataset (str): The name of the dataset to load historical data for.
        source_id (str): The identifier of the data source.
    Returns:
        pandas.DataFrame: A DataFrame containing the historical data sorted in
        ascending order by index. Returns None if no historical data is found.
    """

    df = crud_manager.load_historical_data(dataset, source_id)

    # revert order of df (its stored in reverse order)
    df = df.sort_index(ascending=True)

    if df.empty:
        print("  No historical data found in DB. Skipping forecast.")
        return None

    return df


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
    print(f"=== Starting inference pipeline for {len(all_datasets)} datasets ===\n")
    for dataset, source_id in all_datasets:
        # 1) Construct the MLflow model URI
        model = _load_model_from_registry(dataset, source_id)
        if model is None:  # skip if model not found
            continue
        print(f"  Model loaded for {dataset} ({source_id})")
        # 2) Load historical data from DB
        df = _load_historical_data(dataset, source_id)
        if df is None:  # skip if no historical data
            continue
        print(f"  Historical data loaded for {dataset} ({source_id})")
        # 3) Predict future horizon
        try:
            forecast_series = model.predict(df, steps=forecast_horizon, freq=freq)
        except Exception as e:
            print(f"  Model prediction error: {e}. Skipping.")
            continue
        print(f"  Forecast completed for {dataset} ({source_id})")
        # 4) Build a DataFrame for the forecast
        df_forecast = pd.DataFrame(
            {"time": forecast_series.index, "value": forecast_series.values}
        ).set_index("time")
        print(f"  Forecast DataFrame created for {dataset} ({source_id})")
        # 5) (Optional) Save forecast results to DB
        crud_manager.save_forecast(dataset, source_id, df_forecast)
        print("  (Placeholder) Forecast saved to DB.")

    print("\n=== Inference pipeline complete! ===")


if __name__ == "__main__":
    schema_manager.reset_forecast_tables()
    inference_pipeline()
