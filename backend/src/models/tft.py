import pandas as pd
from sklearn.metrics import mean_squared_error

from src.models.base import BaseTimeSeriesModel
from src.feature_engineering import (
    create_time_features,
    create_future_features,
)

import optuna
from typing import Dict, Any, Tuple
from darts.models import TFTModel
from darts import TimeSeries
from darts.dataprocessing.transformers import Scaler


class TFTTimeSeriesModel(BaseTimeSeriesModel):
    """
    A time-series model using Darts' TemporalFusionTransformer (TFT).
    Optionally uses time-based features (exogenous variables)
    via create_time_features().
    """

    def __init__(self, use_hyperopt: bool = False, n_trials: int = 10):
        """
        Initialize the TFT model parameters.

        Args:
            use_hyperopt (bool): Whether to perform hyperparameter tuning.
            n_trials (int): Number of Optuna trials for tuning.
        """
        self.use_hyperopt = use_hyperopt
        self.n_trials = n_trials
        self.model = None  # Will store the trained TFT model
        self.target_scaler = None  # Scaler for target
        self.past_covariate_scaler = None  # Scaler for covariates
        self.future_covariate_scaler = None  # Scaler for future covariates
        self.best_params = None  # To store the best hyperparameters

    def _create_features(self, df: pd.DataFrame) -> Tuple[TimeSeries, TimeSeries]:
        """
        Convert DataFrame to Darts TimeSeries and create past covariates.

        Args:
            df (pd.DataFrame): Input DataFrame with DateTime index
            and 'value' column.

        Returns:
            TimeSeries: Transformed target series.
            TimeSeries: Transformed past covariates.
            TimeSeries: Transformed future covariates.

        """

        if df.index.tz is None:
            df = df.tz_localize("UTC")
        else:
            df = df.tz_convert("UTC")

        # Convert target to TimeSeries
        ts = TimeSeries.from_dataframe(df, value_cols=["value"], freq=None)

        # Create past covariates
        df_past_covariates = create_time_features(df)
        past_cov_cols = ["hour_sin", "hour_cos", "dow_sin", "dow_cos"]
        past_covariates = TimeSeries.from_dataframe(
            df_past_covariates[past_cov_cols], freq=None
        )

        # Create future covariates
        df_future_cov = create_future_features(df)  # You need to define this function
        future_cov_cols = ["holiday"]  # Example columns
        future_covariates = TimeSeries.from_dataframe(
            df_future_cov[future_cov_cols], freq=None
        )

        return ts, past_covariates, future_covariates

    def _objective(
        self,
        trial,
        ts_train: TimeSeries,
        past_covariates_train: TimeSeries,
        future_covariates_train: TimeSeries,
    ) -> float:
        """
        TODO: adapt to the interface objective() function
        Objective function for Optuna hyperparameter tuning.

        Args:
            trial: Optuna trial object.
            ts_train (TimeSeries): Training target series.
            past_covariates_train (TimeSeries): Training past covariates.
            future_covariates_train (TimeSeries): Training future covariates.

        Returns:
            float: Mean Squared Error of the backtest.
        """
        # Define hyperparameter search space
        hidden_size = trial.suggest_int("hidden_size", 16, 128, step=16)
        lstm_layers = trial.suggest_int("lstm_layers", 1, 4)
        dropout = trial.suggest_float("dropout", 0.0, 0.5)
        batch_size = trial.suggest_int("batch_size", 16, 64, step=16)

        # Instantiate the TFT model with current hyperparameters
        model = TFTModel(
            input_chunk_length=24,
            output_chunk_length=6,
            hidden_size=hidden_size,
            lstm_layers=lstm_layers,
            dropout=dropout,
            batch_size=batch_size,
            n_epochs=10,
            random_state=42,
        )

        try:
            # Fit the model
            model.fit(
                ts_train,
                past_covariates=past_covariates_train,
                future_covariates=future_covariates_train,
                verbose=False,
            )

            # Perform backtest
            backtest = model.backtest(
                series=ts_train,
                past_covariates=past_covariates_train,
                future_covariates=future_covariates_train,
                start=0.8,  # use last 20% for validation
                forecast_horizon=6,
                stride=6,
                retrain=False,
            )

            # Calculate MSE
            mse = mean_squared_error(
                ts_train.slice_intersect(backtest).values(), backtest.values()
            )

            return mse

        except Exception as e:
            # If model fitting fails, discourage this parameter set
            return float("inf"), e

    def tune(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """
        Perform hyperparameter tuning using Optuna.

        Args:
            df (pd.DataFrame): Training DataFrame with DateTime index and 'value' column.
            **kwargs: Additional keyword arguments.

        Returns:
            Dict[str, Any]: The best hyperparameters found.
        """
        ts_train, past_covariates_train, future_covariates_train = (
            self._create_features(df)
        )

        # Scale target and covariates
        self.target_scaler = Scaler()
        self.past_covariate_scaler = Scaler()
        self.future_covariate_scaler = Scaler()

        ts_train_scaled = self.target_scaler.fit_transform(ts_train)
        past_covariates_train_scaled = self.past_covariate_scaler.fit_transform(
            past_covariates_train
        )
        future_covariates_train_scaled = self.future_covariate_scaler.fit_transform(
            future_covariates_train
        )

        # Create Optuna study
        study = optuna.create_study(direction="minimize")
        study.optimize(
            lambda trial: self._objective(
                trial,
                ts_train_scaled,
                past_covariates_train_scaled,
                future_covariates_train_scaled,
            ),
            n_trials=self.n_trials,
        )

        self.best_params = study.best_params
        return self.best_params

    def train(self, df: pd.DataFrame, **kwargs) -> None:
        """
        Train the TFT model using the best hyperparameters.

        Args:
            df (pd.DataFrame): Training DataFrame with DateTime
            index and 'value' column.
            **kwargs: Additional keyword arguments.
        """
        ts_train, past_covariates_train, future_covariates_train = (
            self._create_features(df)
        )

        # Scale target and covariates
        self.target_scaler = Scaler()
        self.past_covariate_scaler = Scaler()
        self.future_covariate_scaler = Scaler()

        ts_train_scaled = self.target_scaler.fit_transform(ts_train)
        past_covariates_train_scaled = self.past_covariate_scaler.fit_transform(
            past_covariates_train
        )
        future_covariates_train_scaled = self.future_covariate_scaler.fit_transform(
            future_covariates_train
        )

        # Use best_params if available, else use defaults
        if self.use_hyperopt and self.best_params:
            hidden_size = self.best_params.get("hidden_size", 64)
            lstm_layers = self.best_params.get("lstm_layers", 1)
            dropout = self.best_params.get("dropout", 0.1)
            batch_size = self.best_params.get("batch_size", 32)
        else:
            hidden_size = 64
            lstm_layers = 1
            dropout = 0.1
            batch_size = 32

        # Instantiate the TFT model with selected hyperparameters
        self.model = TFTModel(
            input_chunk_length=24,
            output_chunk_length=6,
            hidden_size=hidden_size,
            lstm_layers=lstm_layers,
            dropout=dropout,
            batch_size=batch_size,
            n_epochs=10,
            random_state=42,
        )

        try:
            # Fit the model
            self.model.fit(
                ts_train_scaled,
                past_covariates=past_covariates_train_scaled,
                future_covariates=future_covariates_train_scaled,
                verbose=False,
            )
        except Exception as e:
            print(f"Failed to train TFT model: {e}")
            self.model = None

    def evaluate(self, df: pd.DataFrame, **kwargs) -> float:
        """
        Evaluate the trained TFT model on the test set.

        Args:
            df (pd.DataFrame): Test DataFrame with DateTime index and 'value' column.
            **kwargs: Additional keyword arguments.

        Returns:
            float: Mean Squared Error of the predictions.
        """
        if self.model is None:
            raise ValueError("Model has not been trained. Call train() first.")

        ts_test, past_covariates_test, future_covariates_test = self._create_features(
            df
        )

        # Scale test data using the same scalers
        ts_test_scaled = self.target_scaler.transform(ts_test)
        past_covariates_test_scaled = self.past_covariate_scaler.transform(
            past_covariates_test
        )
        future_covariates_test_scaled = self.future_covariate_scaler.transform(
            future_covariates_test
        )

        try:
            # Predict
            preds = self.model.predict(
                n=len(ts_test_scaled),
                series=ts_test_scaled,
                past_covariates=past_covariates_test_scaled,
                future_covariates=future_covariates_test_scaled,
            )

            # Compute MSE
            mse = mean_squared_error(ts_test_scaled.values(), preds.values())

            return mse

        except Exception as e:
            print(f"Failed to predict using TFT model: {e}")
            return float("inf")

    def predict(self, df: pd.DataFrame, forecast_horizon: int = 6) -> pd.DataFrame:
        """
        Generate a forecast from the trained TFT model on new data.

        Args:
            df (pd.DataFrame): A DataFrame with a DateTime index and 'value' column
                            (or no 'value' if purely future).
            forecast_horizon (int): How many time steps to predict forward.

        Returns:
            pd.DataFrame: A DataFrame containing the predicted values
                        (and optionally the datetime index).
        """

        if self.model is None:
            raise ValueError("Model has not been trained. Call train() first.")

        # 1) Convert df into Darts TimeSeries objects
        ts, past_covariates, future_covariates = self._create_features(df)

        # 2) Scale them using the same scalers fitted in train()
        if self.target_scaler is not None:
            ts_scaled = self.target_scaler.transform(ts)
        else:
            ts_scaled = ts

        if self.past_covariate_scaler is not None and past_covariates is not None:
            past_covariates_scaled = self.past_covariate_scaler.transform(
                past_covariates
            )
        else:
            past_covariates_scaled = None

        if self.future_covariate_scaler is not None and future_covariates is not None:
            future_covariates_scaled = self.future_covariate_scaler.transform(
                future_covariates
            )
        else:
            future_covariates_scaled = None

        # 3) Predict
        # We can specify 'n=forecast_horizon' if we want a fixed-length forecast
        # or we can do 'n=len(ts_scaled)' if the new data covers exactly that many timesteps.
        try:
            preds_scaled = self.model.predict(
                n=forecast_horizon,
                series=ts_scaled,
                past_covariates=past_covariates_scaled,
                future_covariates=future_covariates_scaled,
            )
        except Exception as e:
            print(f"Failed to forecast with TFT model: {e}")
            return pd.DataFrame()

        # 4) Inverse-transform predictions to original scale (if desired)
        if self.target_scaler is not None:
            preds = self.target_scaler.inverse_transform(preds_scaled)
        else:
            preds = preds_scaled

        # Convert Darts TimeSeries back to a pandas DataFrame
        df_preds = preds.pd_dataframe()
        df_preds.columns = ["prediction"]

        return df_preds
