import mlflow
import os
import pickle
import numpy as np
from sklearn.model_selection import TimeSeriesSplit
import warnings

# Suppress the FutureIncompatibilityWarning from holidays
warnings.filterwarnings(
    "ignore",
    category=FutureWarning,
)
# Import models
from src.models import (
    ARIMATimeSeriesModel,
    ProphetTimeSeriesModel,
    RandomForestTimeSeriesModel,
    MLPTimeSeriesModel,
    # TFTTimeSeriesModel,
)
from src.db import RENEWABLES, OTHER_DATASETS, load_historical_data, query_source_ids


def get_datasets_list():
    """
    Returns a list of (dataset, source_id) tuples.
    For renewable datasets, we retrieve all existing source_ids in the DB.
    For non-renewable datasets (like load, market), source_id is None.
    """
    datasets_info = []

    # 1) Loop over each renewable and its source_ids
    for renewable in RENEWABLES:
        sids = query_source_ids(renewable)  # e.g., ['010780', '0XYZ', ...]
        for sid in sids:
            datasets_info.append((renewable, sid))

    # 2) Add non-renewable datasets without source_id
    for ds in OTHER_DATASETS:
        datasets_info.append((ds, None))

    return datasets_info


def train_pipeline():
    """
    For each dataset in DATASETS:
      1. Load the entire historical dataset.
      2. Run time-series cross-validation for each candidate model.
      3. Pick the best model based on average CV MSE.
      4. Retrain the best model on the full dataset.
      5. Log & register the final model in MLflow.
    """
    mlflow.set_experiment("VPP_Training_Pipeline")

    model_configs = [
        # {
        #     "name": "ARIMA",
        #     "instance": ARIMATimeSeriesModel(seasonal=True, m=24, use_exogenous=False),
        #     "artifact_method": "sklearn",
        #     "hyperopt": False,
        # },
        # {
        #     "name": "Prophet",
        #     "instance": ProphetTimeSeriesModel(),
        #     "artifact_method": "sklearn",
        #     "hyperopt": False,
        # },
        {
            "name": "RandomForest",
            "instance": RandomForestTimeSeriesModel(),
            "artifact_method": "sklearn",
            "hyperopt": False,
        },
        # {
        #     "name": "MLP",
        #     "instance": MLPTimeSeriesModel(),
        #     "artifact_method": "sklearn",
        #     "hyperopt": False,
        # },
        # {
        #     "name": "TFT",
        #     "instance": TFTTimeSeriesModel(use_hyperopt=False, n_trials=10),
        #     "artifact_method": "pickle",
        #     "hyperopt": True,
        # },
    ]

    with mlflow.start_run(run_name="Timeseries_CV_Train"):

        all_datasets = get_datasets_list()

        for dataset, source_id in all_datasets:
            # 1) Load the entire historical datasets
            df = load_historical_data(dataset, source_id)
            if df.empty:
                print(
                    f"No data found for dataset={dataset}, source_id={source_id}, skipping..."
                )
                continue

            print(
                f"\n[DATASET: {dataset}, Source: {source_id}] loaded. Shape: {df.shape}, [{df.index.min()} - {df.index.max()}]"
            )

            # 2) TimeSeriesSplit CV for each model
            tscv = TimeSeriesSplit(n_splits=3)
            best_model_name = None
            best_model_obj = None
            best_avg_mse = 10e10  # Start with a high value

            run_name = f"{dataset}_{source_id}" if source_id else dataset

            # Start a nested run for each dataset
            with mlflow.start_run(run_name=run_name, nested=True):
                for cfg in model_configs:
                    model_name = cfg["name"]
                    model_obj = cfg["instance"]
                    hyperopt = cfg["hyperopt"]

                    fold_mses = []

                    # first 10 percent of data for hyperopt
                    hyperopt_data = df.iloc[: int(len(df) * 0.1)].copy()
                    full_values = df.iloc[int(len(df) * 0.1) :].copy()

                    if hyperopt:
                        print(f"Hyperparameter tuning for {model_name}...")
                        best_params = model_obj.tune(hyperopt_data)
                        # Log best params
                        for k, v in best_params.items():
                            mlflow.log_param(f"{model_name}_{k}", v)
                        print(f"Best params: {best_params}")

                    for fold_idx, (train_idx, val_idx) in enumerate(
                        tscv.split(full_values)
                    ):
                        df_train = full_values.iloc[train_idx]
                        df_val = full_values.iloc[val_idx]

                        model_obj.train(df_train)
                        val_mse = model_obj.evaluate(df_val)
                        fold_mses.append(val_mse)

                        mlflow.log_metric(
                            f"{dataset}_{model_name}_fold_{fold_idx}_mse", val_mse
                        )

                    avg_mse = np.mean(fold_mses)
                    mlflow.log_metric(f"{dataset}_{model_name}_avg_cv_mse", avg_mse)

                    print(f"   - {model_name} CV MSEs={fold_mses}, Avg={avg_mse:.4f}")

                    # Track best model
                    if avg_mse < best_avg_mse:
                        best_avg_mse = avg_mse
                        best_model_name = model_name
                        best_model_obj = cfg[
                            "instance"
                        ]  # Keep the config's model class

                print(
                    f"\n[DATASET: {dataset}] Best Model: {best_model_name} (Avg CV={best_avg_mse:.4f})"
                )

                # 3) Retrain best model on full data
                best_model_obj.train(df)

                # 4) Log final model
                if best_model_obj.model:
                    filename = f"{dataset}_{best_model_name}_final.pkl"
                    with open(filename, "wb") as f:
                        pickle.dump(best_model_obj, f)
                    mlflow.log_artifact(
                        filename, artifact_path=f"{dataset}_{best_model_name}_final"
                    )
                    os.remove(filename)

                # 5) Register model in Model Registry
                # Use a unique name per (dataset, source_id)
                if source_id is not None:
                    registry_name = f"Best_{dataset}_{source_id}_Model"
                else:
                    registry_name = f"Best_{dataset}_Model"

                final_model_uri = f"runs:/{mlflow.active_run().info.run_id}/{dataset}_{best_model_name}_final"
                result = mlflow.register_model(final_model_uri, registry_name)
                print(f"Registered {registry_name} => version {result.version}")


if __name__ == "__main__":
    train_pipeline()
