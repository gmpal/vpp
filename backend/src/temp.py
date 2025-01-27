import mlflow
import mlflow.sklearn
import mlflow.pyfunc
from mlflow.models.signature import infer_signature

import optuna
import pandas as pd
import numpy as np
import datetime

# Prophet
from prophet import Prophet

# ARIMA - pmdarima
import pmdarima as pm

# scikit-learn
from sklearn.ensemble import RandomForestRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.metrics import mean_squared_error
from sklearn.preprocessing import StandardScaler

# Darts (for TFT and other advanced TS models)
from darts import TimeSeries
from darts.models import TFTModel

# For date/time feature engineering

#############################################
# A. Data Loading / Simulation
#############################################
def load_solar_data(source_id="010780"):
    """
    Replace this with your real data loading.
    Here we create a dummy time series for demonstration.
    We'll assume the DataFrame index is a datetime, column='value'.
    """
    dates = pd.date_range("2021-01-01", periods=1000, freq="H")
    np.random.seed(42)
    values = np.random.rand(len(dates)) * 100
    df = pd.DataFrame({"value": values}, index=dates)
    return df

#############################################


def main_compare_models():
    # 1) Load data
    df = load_solar_data("010780")

    # 2) Train/val split
    split_index = int(0.8 * len(df))
    df_train = df.iloc[:split_index].copy()
    df_test = df.iloc[split_index:].copy()

    # 3) Start MLflow experiment
    mlflow.set_experiment("Advanced_TimeSeries_Study")
    with mlflow.start_run(run_name="Compare_Prophet_ARIMA_RF_MLP_TFT") as parent_run:
        # 4) Train each model
        prophet_model, prophet_train_mse = train_prophet(
            df_train, run_name="ProphetModel", do_hyperopt=True, n_trials=10
        )
        arima_model, arima_train_mse = train_arima(df_train, run_name="ARIMAModel", use_exogenous=True)
        rf_model, rf_train_mse = train_random_forest(
            df_train, run_name="RandomForestModel", do_hyperopt=True, n_trials=10
        )
        mlp_model, mlp_scaler, mlp_train_mse = train_mlp(
            df_train, run_name="MLPModel", do_hyperopt=True, n_trials=10
        )
        tft_model, tft_target_scaler, tft_cov_scaler, tft_train_mse = train_tft_darts(
            df_train, run_name="TFTModel", do_hyperopt=True, n_trials=10
        )

        # 5) Evaluate on test set
        final_prophet_mse = evaluate_prophet(prophet_model, df_test)
        final_arima_mse = evaluate_arima(arima_model, df_test, use_exogenous=True)
        final_rf_mse = evaluate_random_forest(rf_model, df_test)
        final_mlp_mse = evaluate_mlp(mlp_model, mlp_scaler, df_test)
        final_tft_mse = evaluate_tft_darts(tft_model, tft_target_scaler, tft_cov_scaler, df_test)

        print("Prophet Test MSE:", final_prophet_mse)
        print("ARIMA Test MSE:  ", final_arima_mse)
        print("RF Test MSE:     ", final_rf_mse)
        print("MLP Test MSE:    ", final_mlp_mse)
        print("TFT Test MSE:    ", final_tft_mse)

        mlflow.log_metric("final_prophet_mse", final_prophet_mse)
        mlflow.log_metric("final_arima_mse", final_arima_mse)
        mlflow.log_metric("final_rf_mse", final_rf_mse)
        mlflow.log_metric("final_mlp_mse", final_mlp_mse)
        mlflow.log_metric("final_tft_mse", final_tft_mse)

        # 6) Choose best model
        results = {
            "Prophet": final_prophet_mse,
            "ARIMA": final_arima_mse,
            "RandomForest": final_rf_mse,
            "MLP": final_mlp_mse,
            "TFT": final_tft_mse,
        }
        best_model_name = min(results, key=results.get)
        best_mse = results[best_model_name]
        mlflow.log_param("best_model", best_model_name)
        mlflow.log_metric("best_mse", best_mse)

        print(f"Best model: {best_model_name} with MSE={best_mse:.4f}")

        # 7) (Optional) Register or Save the Best Model
        # Example if best_model_name == "Prophet":
        # model_uri = f"runs:/{mlflow.active_run().info.run_id}/prophet_model"
        # mlflow.register_model(model_uri, "ProphetSolarForecast")


def main():
    # Suppose df is your loaded time-series with index=DateTime, col='value'
    df = load_solar_data("010780")  # your own function

    # Splits
    split = int(0.8 * len(df))
    df_train = df.iloc[:split]
    df_test = df.iloc[split:]

    # 1) Prophet
    prophet_model = ProphetTimeSeriesModel()
    best_params_prophet = prophet_model.tune(df_train, n_trials=10)
    prophet_model.train(df_train)
    mse_prophet = prophet_model.evaluate(df_test)
    print("Prophet MSE:", mse_prophet)

    # 2) Random Forest
    rf_model = RandomForestTimeSeriesModel()
    best_params_rf = rf_model.tune(df_train, n_trials=10)
    rf_model.train(df_train)
    mse_rf = rf_model.evaluate(df_test)
    print("RandomForest MSE:", mse_rf)

    # Compare
    if mse_prophet < mse_rf:
        print("Prophet is best!")
    else:
        print("RF is best!")

import mlflow

def train(self, df: pd.DataFrame, **kwargs):
    with mlflow.start_run(run_name="RandomForest_Train", nested=True):
        # do training
        ...
        mlflow.log_params({...})
        mlflow.log_metric("train_mse", train_mse)
        mlflow.sklearn.log_model(self.model, artifact_path="model")


if __name__ == "__main__":
    main()


if __name__ == "__main__":
    main_compare_models()
