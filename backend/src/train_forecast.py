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

# Random Forest
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error

# Darts for deep learning / pretrained models
# e.g. NBEATS, TFT, etc.
from darts import TimeSeries
from darts.models import NBEATSModel  # as an example
from darts.utils.timeseries_generation import datetime_attribute_timeseries
from darts.dataprocessing.transformers import Scaler

# Evidently for drift detection
from evidently import ColumnMapping
from evidently.report import Report
from evidently.metric_preset import DataDriftPreset, RegressionPreset


#############################################
# 1. Load Data from DB (example)
#############################################
def load_solar_data(source_id="010780"):
    """
    Example function to load your solar time-series data.
    Expects the returned DataFrame to have index=timestamp, column='value'.
    """
    # Replace this with your own logic or DB call
    # Here we create a dummy time series for illustration
    dates = pd.date_range("2021-01-01", periods=500, freq="H")
    np.random.seed(42)
    values = np.random.rand(len(dates)) * 100
    df = pd.DataFrame({"value": values}, index=dates)
    return df

#############################################
# 2. Hyperparameter Tuning - Prophet Example
#############################################
def prophet_objective(trial, df_prophet):
    # Example objective function for Prophet hyperparam tuning with Optuna
    params = {
        "seasonality_mode": trial.suggest_categorical(
            "seasonality_mode", ["additive", "multiplicative"]
        ),
        "changepoint_prior_scale": trial.suggest_float(
            "changepoint_prior_scale", 0.001, 0.5, log=True
        ),
        "seasonality_prior_scale": trial.suggest_float(
            "seasonality_prior_scale", 0.1, 10.0, log=True
        ),
    }
    model = Prophet(**params)
    model.fit(df_prophet)
    forecast = model.predict(df_prophet)
    mse = mean_squared_error(df_prophet["y"], forecast["yhat"])
    return mse

def tune_prophet(df: pd.DataFrame, n_trials=10):
    """
    Runs an Optuna study to find best Prophet hyperparams.
    Returns best_params.
    """
    # Convert df => ds, y
    df_prophet = df.reset_index()
    df_prophet.columns = ["ds", "y"]
    df_prophet["ds"] = df_prophet["ds"].dt.tz_localize(None)

    study = optuna.create_study(direction="minimize")
    study.optimize(lambda trial: prophet_objective(trial, df_prophet), n_trials=n_trials)
    return study.best_params

#############################################
# 3. Model Training Functions
#############################################

def train_prophet(
    df: pd.DataFrame,
    run_name="ProphetModel",
    do_hyperopt=False,
    n_trials=10,
):
    """
    Train a Prophet model, optionally with hyperparameter tuning (Optuna).
    Logs params, metrics, artifact to MLflow.
    Returns (model, mse) on the training set for illustration.
    """
    with mlflow.start_run(run_name=run_name, nested=True):
        # Prepare data
        df_prophet = df.reset_index()
        df_prophet.columns = ["ds", "y"]
        df_prophet["ds"] = df_prophet["ds"].dt.tz_localize(None)

        if do_hyperopt:
            best_params = tune_prophet(df, n_trials)
        else:
            best_params = {
                "seasonality_mode": "multiplicative",
                "changepoint_prior_scale": 0.05,
                "seasonality_prior_scale": 1.0,
            }

        mlflow.log_params(best_params)

        model = Prophet(**best_params)
        model.fit(df_prophet)

        # Simple in-sample MSE
        forecast = model.predict(df_prophet)
        train_mse = mean_squared_error(df_prophet["y"], forecast["yhat"])
        mlflow.log_metric("train_mse", train_mse)

        mlflow.sklearn.log_model(model, artifact_path="prophet_model")
        return model, train_mse

def train_arima(df: pd.DataFrame, run_name="ARIMAModel"):
    """
    Train ARIMA using pmdarima's auto_arima for demonstration.
    Returns (model, mse).
    Logs to MLflow.
    """
    with mlflow.start_run(run_name=run_name, nested=True):
        y = df["value"].values

        model = pm.auto_arima(
            y,
            start_p=1,
            start_q=1,
            test="adf",
            max_p=5,
            max_q=5,
            m=1,
            d=None,
            seasonal=False,
            trace=False,
            error_action="ignore",
            suppress_warnings=True,
            stepwise=True,
        )

        mlflow.log_param("order", model.order)
        preds = model.predict_in_sample()
        train_mse = mean_squared_error(y, preds)
        mlflow.log_metric("train_mse", train_mse)

        mlflow.sklearn.log_model(model, artifact_path="arima_model")
        return model, train_mse

def train_random_forest(df: pd.DataFrame, run_name="RandomForestModel"):
    """
    Simple time-lag feature approach for RandomForest.
    """
    with mlflow.start_run(run_name=run_name, nested=True):
        df_rf = df.copy()
        df_rf["lag1"] = df_rf["value"].shift(1)
        df_rf["lag2"] = df_rf["value"].shift(2)
        df_rf["lag3"] = df_rf["value"].shift(3)
        df_rf.dropna(inplace=True)

        X = df_rf[["lag1", "lag2", "lag3"]]
        y = df_rf["value"]

        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(X, y)
        preds = model.predict(X)
        train_mse = mean_squared_error(y, preds)

        mlflow.log_metric("train_mse", train_mse)
        mlflow.log_param("n_estimators", 100)
        mlflow.sklearn.log_model(model, artifact_path="rf_model")

        return model, train_mse

def train_nbeats_darts(df: pd.DataFrame, run_name="NBeatsDartsModel", past_covariates=False):
    """
    Example of using the Darts library for a deep learning model (N-BEATS).
    We can load a 'pretrained' model or specify 'load_from_checkpoint' if you have a checkpoint.
    For demonstration, we train from scratch or partially from a known architecture.
    """
    with mlflow.start_run(run_name=run_name, nested=True):
        # Prepare Darts TimeSeries
        df_series = TimeSeries.from_dataframe(df, value_cols=["value"], freq=None)
        # We can scale the series
        scaler = Scaler()
        ts_transformed = scaler.fit_transform(df_series)

        # Create model
        model = NBEATSModel(
            input_chunk_length=24,  # number of past time steps you feed in
            output_chunk_length=6,  # how many future time steps you want to forecast at once
            n_epochs=10,
            random_state=42,
        )
        # If you had a pretrained model:
        # model = NBEATSModel.load_from_checkpoint("my_checkpoint_path")

        # Fit on entire series for demonstration
        model.fit(ts_transformed)

        # In-sample predictions
        pred = model.predict(n=0, series=ts_transformed)  # n=0 => in-sample recon
        # In Darts, that sometimes yields just the last segment; or we can do a backtest
        # For simplicity:
        # let's do a quick backtest, forecasting one step at a time over the entire series
        backtest = model.backtest(
            series=ts_transformed,
            start=0.8,  # 80% split
            forecast_horizon=6,  # forecast horizon
            stride=6,
            retrain=False
        )
        # Evaluate MSE
        # backtest is the TimeSeries of forecasts aligned with the same time index as the validation
        mse = np.mean((ts_transformed.slice_intersect(backtest).values() - backtest.values())**2)

        mlflow.log_metric("train_mse", mse)
        # Log the model - we can store the model files or a custom pyfunc wrapper
        # For a quick approach, let's do mlflow.pyfunc.log_model with a custom wrapper
        # but here we demonstrate simple pickle approach:
        mlflow.sklearn.log_model(model, artifact_path="nbeats_model")

        return model, mse

#############################################
# 4. Evaluation Functions
#############################################

def evaluate_prophet(model: Prophet, df_test: pd.DataFrame):
    df_reset = df_test.reset_index()
    df_reset.columns = ["ds", "y"]
    df_reset["ds"] = df_reset["ds"].dt.tz_localize(None)
    forecast = model.predict(df_reset)
    mse = mean_squared_error(df_reset["y"], forecast["yhat"])
    return mse

def evaluate_arima(model, df_test: pd.DataFrame):
    y_test = df_test["value"].values
    preds = model.predict(n_periods=len(y_test))
    mse = mean_squared_error(y_test, preds)
    return mse

def evaluate_rf(model: RandomForestRegressor, df_test: pd.DataFrame):
    df_copy = df_test.copy()
    df_copy["lag1"] = df_copy["value"].shift(1)
    df_copy["lag2"] = df_copy["value"].shift(2)
    df_copy["lag3"] = df_copy["value"].shift(3)
    df_copy.dropna(inplace=True)
    X = df_copy[["lag1", "lag2", "lag3"]]
    y_true = df_copy["value"]
    preds = model.predict(X)
    mse = mean_squared_error(y_true, preds)
    return mse

def evaluate_nbeats_darts(model, df_test: pd.DataFrame):
    # Convert test data to Darts series
    df_series = TimeSeries.from_dataframe(df_test, value_cols=["value"])
    # For a quick measure, let's do a naive approach: predict in full from last known.
    # Usually you'd fit the same scaler or load from the same pipeline used in training:
    # but for simplicity here, we skip scaling or replicate the same approach:
    # If you used a Scaler in training, you must transform df_series before predict.
    # We'll do a short approach:
    #  - Possibly just do model.backtest on the test portion. For example:
    #  (We assume the model was fit on the entire training set)
    forecast = model.predict(n=len(df_series))  # forecast next len(df_test) points
    # This might not align exactly with df_test timestamps, but let's keep it simple
    # You could do a more rigorous approach with Darts train/val splitting
    # For an approximate MSE:
    n = min(len(forecast), len(df_series))
    mse = mean_squared_error(df_series.values()[:n], forecast.values()[:n])
    return mse

#############################################
# 5. Drift Detection with Evidently
#############################################

def detect_data_drift(df_ref: pd.DataFrame, df_new: pd.DataFrame, 
                      target_col: str = "value", 
                      significance=0.05):
    """
    Use Evidently to detect if new data distribution is drifting from reference data.
    Returns a dictionary with drift metrics and boolean flags.
    """
    # ColumnMapping to let Evidently know about the target, prediction, etc.
    column_mapping = ColumnMapping()
    column_mapping.target = target_col

    report = Report(metrics=[
        DataDriftPreset(),  # data drift detection on the features
        RegressionPreset()  # for reg target distribution
    ])
    report.run(
        reference_data=df_ref.reset_index(drop=True),
        current_data=df_new.reset_index(drop=True),
        column_mapping=column_mapping
    )
    results = report.as_dict()

    # We can parse the dictionary to get the data_drift overall result:
    # e.g. 'data_drift' => 'data' => 'metrics' => 'dataset_drift'
    data_drift_result = results["metrics"][0]["result"]["dataset_drift"]
    # or we can get p_value, etc. For demonstration, let's just log a summary
    drift_detected = data_drift_result is True

    return {
        "data_drift_detected": drift_detected,
        "full_report": results,
    }

#############################################
# 6. Orchestrate main
#############################################

def main_compare_models():
    # 6.1 Load data
    df = load_solar_data("010780")

    # 6.2 Split into train / test
    split_index = int(0.8 * len(df))
    df_train = df.iloc[:split_index].copy()
    df_test = df.iloc[split_index:].copy()

    # 6.3 Optionally detect drift between train and test (just as an example)
    drift_info = detect_data_drift(df_train, df_test, target_col="value")
    if drift_info["data_drift_detected"]:
        print("Warning: Data drift detected between train and test!")
        # We might trigger additional steps if needed

    # 6.4 Start a main MLflow run
    mlflow.set_experiment("ComplexTimeSeriesStudy")
    with mlflow.start_run(run_name="Compare_Multiple_Models") as parent_run:
        # 6.5 Train each candidate model
        prophet_model, prophet_train_mse = train_prophet(
            df_train, run_name="ProphetModel", do_hyperopt=True, n_trials=10
        )
        arima_model, arima_train_mse = train_arima(df_train, run_name="ARIMAModel")
        rf_model, rf_train_mse = train_random_forest(df_train, run_name="RandomForestModel")
        nbeats_model, nbeats_train_mse = train_nbeats_darts(df_train, run_name="NBeatsDartsModel")

        # 6.6 Evaluate on test
        final_prophet_mse = evaluate_prophet(prophet_model, df_test)
        final_arima_mse = evaluate_arima(arima_model, df_test)
        final_rf_mse = evaluate_rf(rf_model, df_test)
        final_nbeats_mse = evaluate_nbeats_darts(nbeats_model, df_test)

        print("Prophet MSE:", final_prophet_mse)
        print("ARIMA MSE:  ", final_arima_mse)
        print("RF MSE:     ", final_rf_mse)
        print("NBeats MSE: ", final_nbeats_mse)

        mlflow.log_metric("final_prophet_mse", final_prophet_mse)
        mlflow.log_metric("final_arima_mse", final_arima_mse)
        mlflow.log_metric("final_rf_mse", final_rf_mse)
        mlflow.log_metric("final_nbeats_mse", final_nbeats_mse)

        # 6.7 Determine best model
        results = {
            "Prophet": final_prophet_mse,
            "ARIMA": final_arima_mse,
            "RandomForest": final_rf_mse,
            "NBeatsDarts": final_nbeats_mse,
        }
        best_model_name = min(results, key=results.get)
        best_mse = results[best_model_name]
        mlflow.log_param("best_model", best_model_name)
        mlflow.log_metric("best_mse", best_mse)

        print(f"Best model is {best_model_name} with MSE={best_mse:.4f}")

        # 6.8 Optionally register the best model
        # (Example only if you want to push the final artifact to the model registry)
        # This will vary depending on how you manage your model artifacts.
        # Example for Prophet:
        # if best_model_name == "Prophet":
        #     model_uri = f"runs:/{mlflow.active_run().info.run_id}/prophet_model"
        #     mlflow.register_model(model_uri, "ProphetSolarForecast")

    # 6.9 Suppose we want to do DRIFT DETECTION over time once the model is in production.
    # We'll do a small example where "df_test" is our "new incoming data."
    production_drift = detect_data_drift(df_train, df_test)
    if production_drift["data_drift_detected"]:
        print("Data drift in production! Consider triggering re-training.")
    # You could log drift metrics to MLflow or to your monitoring system.
    # For example, the "production_drift['full_report']" dict has detailed stats.

if __name__ == "__main__":
    main_compare_models()