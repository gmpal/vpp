import optuna
import mlflow
import pandas as pd
from prophet import Prophet
from sklearn.metrics import mean_squared_error
from src.model.base import BaseTimeSeriesModel

class ProphetTimeSeriesModel(BaseTimeSeriesModel):
    def __init__(self, params=None):
    """
    params can store default or user-specified hyperparameters, e.g.
    {'seasonality_mode': 'multiplicative', 'changepoint_prior_scale': 0.05, ...}
    """
    self.params = params if params is not None else {}
    self.model = None  # Will store the fitted Prophet model


    def objective(self, trial, df_prophet) -> float:
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

    def tune(self, df: pd.DataFrame, n_trials=10, **kwargs) -> dict:
        """
        Runs an Optuna study to find best Prophet hyperparams.
        Returns best_params.
        """
        # Convert df => ds, y
        df_prophet = df.reset_index()
        df_prophet.columns = ["ds", "y"]
        df_prophet["ds"] = df_prophet["ds"].dt.tz_localize(None)

        study = optuna.create_study(direction="minimize")
        study.optimize(lambda trial: self.objective(trial, df_prophet), n_trials=n_trials)

        self.params.update(study.best_params)  # Store best params internally

        return study.best_params

    #############################################
    # 3. Model Training Functions
    #############################################

    def train(self, df: pd.DataFrame, **kwargs) -> None:
        """
        Train a Prophet model, optionally with hyperparameter tuning (Optuna).
        Logs params, metrics, artifact to MLflow.
        Returns (model, mse) on the training set for illustration.
        """

        #TODO: decide what to do with these
        # run_name="ProphetModel" 

        # with mlflow.start_run(run_name=run_name, nested=True):
            # Prepare data
        df_prophet = df.reset_index()
        df_prophet.columns = ["ds", "y"]
        df_prophet["ds"] = df_prophet["ds"].dt.tz_localize(None)

        self.model = Prophet(**self.params)
        self.model.fit(df_prophet)

        # Simple in-sample MSE TODO: decide what to do with this
        # forecast = model.predict(df_prophet)
        # train_mse = mean_squared_error(df_prophet["y"], forecast["yhat"])
        # mlflow.log_metric("train_mse", train_mse)
        # mlflow.sklearn.log_model(model, artifact_path="prophet_model")


    def evaluate(self, df: pd.DataFrame, **kwargs) -> float:
        """
        Compute MSE on df.
        """
        df_reset = df.reset_index()
        df_reset.columns = ["ds", "y"]
        df_reset["ds"] = df_reset["ds"].dt.tz_localize(None)
        forecast = self.model.predict(df_reset)
        mse = mean_squared_error(df_reset["y"], forecast["yhat"])
        return mse
