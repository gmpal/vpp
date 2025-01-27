import mlflow
import pandas as pd
import numpy as np
import os, pickle

# Import your models
from src.models import (
    ARIMATimeSeriesModel,
    ProphetTimeSeriesModel,
    RandomForestTimeSeriesModel,
    TFTTimeSeriesModel
)
from src.db import load_from_db

def main_pipeline():
    # 1) Load data
    df = load_from_db("solar", "010780")
    print(f"Data loaded. Shape: {df.shape}, Time range: [{df.index.min()} - {df.index.max()}]")

    # 2) Train-test split (80% / 20%)
    split_index = int(0.8 * len(df))
    df_train = df.iloc[:split_index].copy()
    df_test = df.iloc[split_index:].copy()
    print(f"Train size: {df_train.shape[0]}, Test size: {df_test.shape[0]}")

    # 3) Create model instances with some config
    model_configs = [
        {
            "name": "ARIMA",
            "instance": ARIMATimeSeriesModel(use_exogenous=True, seasonal=True, m=24),
            "tune_enabled": True,
            "artifact_method": "sklearn",  # We'll do mlflow.sklearn.log_model
        },
        {
            "name": "Prophet",
            "instance": ProphetTimeSeriesModel(),
            "tune_enabled": True,  # or False if your prophet class doesn't have tune
            "artifact_method": "sklearn",  # or 'custom'
        },
        {
            "name": "RandomForest",
            "instance": RandomForestTimeSeriesModel(),
            "tune_enabled": True,
            "artifact_method": "sklearn",
        },
        {
            "name": "TFT",
            "instance": TFTTimeSeriesModel(use_hyperopt=False, n_trials=10),
            "tune_enabled": False,  # skipping tuning for demonstration
            "artifact_method": "pickle",  # we'll do our custom pickling
        },
    ]

    # We'll store final test MSEs for each model
    results = {}

    # 4) Start MLflow experiment
    mlflow.set_experiment("Compare_All_Models")
    with mlflow.start_run(run_name="Compare_All_Models") as parent_run:
        parent_run_id = parent_run.info.run_id
        print(f"Parent run ID: {parent_run_id}")

        for config in model_configs:
            model_name = config["name"]
            model_obj = config["instance"]
            do_tune = config["tune_enabled"]
            artifact_method = config["artifact_method"]

            # 4.1 Start nested run for each model
            with mlflow.start_run(run_name=f"{model_name}_Model", nested=True):
                print(f"**** Processing {model_name} ****")

                # a) Tuning (if enabled)
                if do_tune:
                    print(f"Tuning {model_name}...")
                    best_params = model_obj.tune(df_train, n_trials=10)
                    if best_params:
                        mlflow.log_params(best_params)
                else:
                    print(f"Skipping tuning for {model_name}...")

                # b) Train
                model_obj.train(df_train)

                # c) Evaluate
                test_mse = model_obj.evaluate(df_test)
                mlflow.log_metric("test_mse", test_mse)
                results[model_name] = test_mse
                print(f"{model_name} test MSE: {test_mse:.4f}")

                # d) Log model artifacts
                if model_obj.model is not None:
                    if artifact_method == "sklearn":
                        # Some models are scikit-learn compatible or Prophet-like
                        mlflow.sklearn.log_model(
                            model_obj.model, artifact_path=f"{model_name}_model"
                        )
                    elif artifact_method == "pickle":
                        # For Darts TFT or others
                        filename = f"{model_name}_model.pkl"
                        with open(filename, "wb") as f:
                            pickle.dump(model_obj.model, f)
                        mlflow.log_artifact(filename, artifact_path=f"{model_name}_model")
                        os.remove(filename)

        # 5) Final Compare in parent run
        for model_name, mse in results.items():
            mlflow.log_metric(f"{model_name}_test_mse", mse)

        best_model_name = min(results, key=results.get)
        best_mse = results[best_model_name]
        mlflow.log_param("best_model", best_model_name)
        mlflow.log_metric("best_mse", best_mse)

        print("==========================================================")
        print("Model Results:")
        for model_name, mse in results.items():
            print(f" - {model_name}: MSE={mse:.4f}")
        print(f"Best Model: {best_model_name}, MSE={best_mse:.4f}")
        print("==========================================================")

        # 6) Example registering best model (placeholder)
        best_model_uri = f"runs:/{mlflow.active_run().info.run_id}/{best_model_name}_model"
        # mlflow.register_model(best_model_uri, "Best_TimeSeries_Model")


if __name__ == "__main__":
    main_pipeline()
