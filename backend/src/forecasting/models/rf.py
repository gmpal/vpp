# rf.py
import pandas as pd
import optuna
import numpy as np
from typing import Dict, Any

from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error

from backend.src.forecasting.base import BaseTimeSeriesModel
from backend.src.forecasting.feature_engineering import create_regression_features


class RandomForestTimeSeriesModel(BaseTimeSeriesModel):
    """
    A time-series forecasting wrapper around RandomForestRegressor.
    It uses a custom feature-engineering function (create_regression_features)
    and performs iterative (multi-step) forecasting by feeding predictions
    back as the 'value' for subsequent steps.
    """

    def __init__(self, params: Dict[str, Any] = None):
        """
        Parameters
        ----------
        params : dict, optional
            Dictionary of hyperparameters for the RandomForestRegressor.
            e.g. {"n_estimators": 100, "max_depth": 10}
        """
        self.params = params if params is not None else {}
        self.model = None

    def objective(self, trial, X, y):
        """
        Optuna objective function to find the best hyperparameters by minimizing MSE.
        """
        n_estimators = trial.suggest_int("n_estimators", 50, 300, step=50)
        max_depth = trial.suggest_int("max_depth", 3, 20)
        min_samples_split = trial.suggest_int("min_samples_split", 2, 10)

        model = RandomForestRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            min_samples_split=min_samples_split,
            random_state=42,
        )
        model.fit(X, y)
        preds = model.predict(X)
        return mean_squared_error(y, preds)

    def tune(self, df: pd.DataFrame, n_trials=10, **kwargs) -> dict:
        """
        Uses Optuna to tune hyperparameters on the provided DataFrame.
        """
        # Prepare features for tuning
        X, y = create_regression_features(df)
        study = optuna.create_study(direction="minimize")
        study.optimize(lambda trial: self.objective(trial, X, y), n_trials=n_trials)

        # Merge best hyperparams into self.params
        self.params.update(study.best_params)
        return study.best_params

    def train(self, df: pd.DataFrame, **kwargs) -> None:
        """
        Fit the RandomForest on single-step-ahead features (from create_regression_features).
        """
        X, y = create_regression_features(df)  # includes cyc features, lags, etc.

        n_estimators = self.params.get("n_estimators", 100)
        max_depth = self.params.get("max_depth", None)
        min_samples_split = self.params.get("min_samples_split", 2)

        self.model = RandomForestRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            min_samples_split=min_samples_split,
            random_state=42,
        )
        self.model.fit(X, y)

    def evaluate(self, df_test: pd.DataFrame) -> float:
        """
        Evaluate MSE on the given df_test by recreating the same features.
        """
        if self.model is None:
            raise ValueError("Model has not been trained. Call train() first.")

        X_test, y_true = create_regression_features(df_test)
        preds = self.model.predict(X_test)
        return mean_squared_error(y_true, preds)

    def _predict_single_step(self, df: pd.DataFrame) -> float:
        """
        Predict a single time step into the future.
        Specifically, we:
          1) Build features using the entire df (which must have 'value').
          2) Predict using the last row's features.
          3) Return just that last predicted value.
        """
        if self.model is None:
            raise ValueError("Model has not been trained. Call train() first.")

        X, _ = create_regression_features(df)
        # The last row of X corresponds to the most recent time in df
        preds = self.model.predict(X)
        return preds[-1]

    def predict(self, df: pd.DataFrame, n_steps: int = 30, **kwargs) -> pd.Series:
        """
        Iteratively forecast n_steps into the future, using the model's own
        predictions as input for the next step (rolling forward).

        Args:
            df (pd.DataFrame): The initial DataFrame (with 'value' column
                and DateTimeIndex) up to the last known time.
            n_steps (int): How many future time steps to forecast.
            freq (str): Frequency of each step (e.g. 'H' for hourly, 'D' for daily).

        Returns:
            pd.Series: A Series of length n_steps with forecasts for each step,
                       indexed by the future timestamps.
        """
        freq = kwargs.get("freq", "H")
        if self.model is None:
            raise ValueError("Model has not been trained. Call train() first.")

        # Start by making a copy of the historical data
        df_current = df.copy().sort_index()
        forecasts = []

        for step in range(n_steps):
            # 1) Single-step forecast from the last row of df_current
            step_pred = self._predict_single_step(df_current)
            forecasts.append(step_pred)

            # 2) Append the predicted value as the "next" row
            next_time = df_current.index[-1] + pd.to_timedelta(1, unit=freq)
            df_current.loc[next_time, "value"] = step_pred

        # Build a DatetimeIndex for the forecast horizon
        future_index = pd.date_range(
            start=df.index[-1] + pd.to_timedelta(1, unit=freq),
            periods=n_steps,
            freq=freq,
        )
        return pd.Series(forecasts, index=future_index)
