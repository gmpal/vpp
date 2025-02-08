import optuna
import pandas as pd
import numpy as np
from prophet import Prophet
from sklearn.metrics import mean_squared_error

from src.models.base import BaseTimeSeriesModel


class ProphetTimeSeriesModel(BaseTimeSeriesModel):
    """
    A minimal Prophet model with optional hyperparameter tuning via Optuna.
    No extra regressors (covariates).
    """

    def __init__(self, params=None):
        """
        params can store default or user-specified hyperparameters, e.g.:
        {
          'seasonality_mode': 'multiplicative',
          'changepoint_prior_scale': 0.05,
          'seasonality_prior_scale': 5.0,
          ...
        }
        """
        self.params = params if params is not None else {}
        self.model = None

    def _objective(self, trial, df_prophet) -> float:
        """
        Objective function for Prophet hyperparam tuning with Optuna.
        Minimizes in-sample MSE on df_prophet.
        """
        # Example hyperparams to tune:
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

    def tune(self, df: pd.DataFrame, n_trials=10) -> dict:
        """
        Runs an Optuna study to find best Prophet hyperparams. Updates self.params.
        """
        # Convert df => [ds, y], drop timezones if present
        df_prophet = self._prepare_df_for_prophet(df)

        study = optuna.create_study(direction="minimize")
        study.optimize(
            lambda trial: self._objective(trial, df_prophet), n_trials=n_trials
        )

        self.params.update(study.best_params)
        return study.best_params

    def _prepare_df_for_prophet(self, df):
        # 1) Reset index
        df_prophet = df.reset_index()
        # 2) Rename the first column to "ds", second to "y"
        df_prophet.columns = ["ds", "y"]
        df_prophet["ds"] = df_prophet["ds"].dt.tz_localize(None)
        return df_prophet

    def train(self, df: pd.DataFrame) -> None:
        """
        Fit a Prophet model on the entire DataFrame.
        """
        df_prophet = self._prepare_df_for_prophet(df)
        self.model = Prophet(**self.params)
        self.model.fit(df_prophet)

    def evaluate(self, df: pd.DataFrame) -> float:
        """
        Compute MSE on df (in-sample or a holdout).
        """
        if self.model is None:
            raise ValueError("Model is not trained. Call train() first.")

        df_prophet = self._prepare_df_for_prophet(df)
        forecast = self.model.predict(df_prophet)
        mse = mean_squared_error(df_prophet["y"], forecast["yhat"])
        return mse

    def predict(self, df: pd.DataFrame = None, steps: int = 0, **kwargs) -> np.ndarray:
        """
        Unified prediction method:
          - If df is provided, Prophet will forecast for those timestamps.
          - If periods > 0 (and df is None), Prophet will forecast
            that many future steps past the last trained date.

        Args:
            df (pd.DataFrame, optional): Time-indexed data with 'value' col
                or a DataFrame with a 'ds' column. If present, we forecast
                exactly those dates. Default is None.
            periods (int, optional): How many future time steps to forecast
                beyond the training horizon. Only used if df is None.
                Default is 0 (no future steps).
            freq (str, optional): Frequency of the future steps
                (e.g. 'D' for daily, 'H' for hourly). Default is 'D'.

        Returns:
            pd.DataFrame: Prophet forecast with columns: ds, yhat, yhat_lower, yhat_upper, ...
        """

        freq = kwargs.get(
            "freq", "D"
        )  # TODO: check frequencies mathcing between models

        if self.model is None:
            raise ValueError("Model is not trained. Call train() first.")

        # Case 1: Predict on a custom df
        if df is not None:
            df_prophet = self._prepare_df_for_prophet(df)
            forecast = self.model.predict(df_prophet)
            return forecast

        # Case 2: Predict future beyond training horizon
        if steps <= 0:
            raise ValueError("Please specify 'periods' > 0 or provide 'df'.")

        # make_future_dataframe starts from the last date used in .fit()
        future_df = self.model.make_future_dataframe(periods=steps, freq=freq)
        forecast = self.model.predict(future_df)

        # return ndarray
        return forecast["yhat"].values
