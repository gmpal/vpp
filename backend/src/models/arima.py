import pmdarima as pm
import optuna
from sklearn.metrics import mean_squared_error
from typing import Dict, Any
import pandas as pd
import numpy as np

from src.models.base import BaseTimeSeriesModel
from src.feature_engineering import create_time_features


class ARIMATimeSeriesModel(BaseTimeSeriesModel):
    """
    A time-series model using pmdarima's ARIMA.
    Optionally uses time-based features (exogenous variables) via create_time_features().
    """

    def __init__(self, use_exogenous: bool = True, seasonal: bool = True, m: int = 24):
        """
        Initialize the ARIMA model parameters.

        Args:
            use_exogenous (bool): Whether to include cyclical time features as exogenous variables.
            seasonal (bool): Whether to allow seasonal ARIMA.
            m (int): Season length (e.g., 24 for hourly data with daily seasonality).
        """
        self.use_exogenous = use_exogenous
        self.seasonal = seasonal
        self.m = m
        self.model = None  # Will store the fitted pmdarima ARIMA model
        self.best_params = None  # To store the best hyperparameters from tuning

    def _create_exog(self, df: pd.DataFrame) -> Any:
        """
        Create exogenous features from time-based transformations.

        Args:
            df (pd.DataFrame): The input DataFrame with a DateTime index.

        Returns:
            np.ndarray or None: Array of exogenous features or None if not used.
        """
        if not self.use_exogenous:
            return None
        df_feat = create_time_features(df)
        # Select cyclical features for exogenous variables
        exog = df_feat[["hour_sin", "hour_cos", "dow_sin", "dow_cos"]].values
        return exog

    def _objective(self, trial, y: np.ndarray, exog: Any) -> float:
        """
        Objective function for Optuna hyperparameter tuning.

        Args:
            trial: Optuna trial object.
            y (np.ndarray): The target time-series data.
            exog (Any): Exogenous variables (if any).

        Returns:
            float: Mean Squared Error of the in-sample predictions.
        """
        # Define the search space for ARIMA parameters
        p = trial.suggest_int("p", 0, 5)
        d = trial.suggest_int("d", 0, 2)
        q = trial.suggest_int("q", 0, 5)
        P = trial.suggest_int("P", 0, 2)
        D = trial.suggest_int("D", 0, 2)
        Q = trial.suggest_int("Q", 0, 2)
        seasonal = trial.suggest_categorical("seasonal", [True, False])
        m = trial.suggest_int("m", 1, 24)

        try:
            # Instantiate the ARIMA model with current trial parameters
            model = pm.ARIMA(
                order=(p, d, q),
                seasonal_order=(P, D, Q, m) if seasonal else None,
                suppress_warnings=True,
                error_action="ignore",
            )
            model.fit(y, exogenous=exog)
            preds = model.predict_in_sample(exogenous=exog)
            mse = mean_squared_error(y, preds)
            return mse
        except Exception as e:
            # If model fitting fails, rdiscourage this parameter set
            return float("inf"), e

    def tune(self, df: pd.DataFrame, n_trials: int = 20) -> Dict[str, Any]:
        """
        Perform hyperparameter tuning using Optuna.

        Args:
            df (pd.DataFrame): The training DataFrame with a DateTime index and 'value' column.
            n_trials (int): Number of Optuna trials.

        Returns:
            Dict[str, Any]: The best hyperparameters found.
        """
        y = df["value"].values
        exog = self._create_exog(df)

        study = optuna.create_study(direction="minimize")
        study.optimize(lambda trial: self._objective(trial, y, exog), n_trials=n_trials)

        self.best_params = study.best_params
        return self.best_params

    def train(self, df: pd.DataFrame, **kwargs) -> None:
        """
        Train the ARIMA model using the best hyperparameters.

        Args:
            df (pd.DataFrame): The training DataFrame with a DateTime index and 'value' column.
        """
        y = df["value"].values
        exog = self._create_exog(df)

        if self.best_params:
            p = self.best_params.get("p", 1)
            d = self.best_params.get("d", 1)
            q = self.best_params.get("q", 1)
            P = self.best_params.get("P", 0)
            D = self.best_params.get("D", 0)
            Q = self.best_params.get("Q", 0)
            seasonal = self.best_params.get("seasonal", self.seasonal)
            m = self.best_params.get("m", self.m)
        else:
            # Default ARIMA parameters if tuning was not performed
            p, d, q = 1, 1, 1
            P, D, Q = 0, 0, 0
            seasonal = self.seasonal
            m = self.m

        try:
            # Instantiate and fit the ARIMA model with the selected parameters
            self.model = pm.ARIMA(
                order=(p, d, q),
                seasonal_order=(P, D, Q, m) if seasonal else None,
                suppress_warnings=True,
            )
            self.model.fit(y, exog=exog)
            self.order_ = self.model.order
            self.seasonal_order_ = self.model.seasonal_order if seasonal else None
        except Exception as e:
            print(f"Failed to fit ARIMA model: {e}")
            self.model = None

    def evaluate(self, df: pd.DataFrame, **kwargs) -> float:
        """
        Evaluate the trained ARIMA model on the test set.

        Args:
            df (pd.DataFrame): The test DataFrame with a DateTime index and 'value' column.

        Returns:
            float: Mean Squared Error of the predictions.
        """
        if self.model is None:
            raise ValueError("Model has not been trained. Call train() first.")

        y_true = df["value"].values
        exog = self._create_exog(df)

        try:
            preds = self.model.predict(n_periods=len(y_true), exogenous=exog)
            mse = mean_squared_error(y_true, preds)
            return mse
        except Exception as e:
            print(f"Failed to predict using ARIMA model: {e}")
            return float("inf")
