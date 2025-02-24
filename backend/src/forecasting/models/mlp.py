import optuna
import pandas as pd
import numpy as np

from sklearn.neural_network import MLPRegressor
from sklearn.metrics import mean_squared_error
from sklearn.preprocessing import StandardScaler
from typing import Dict, Any

from backend.src.forecasting.base import BaseTimeSeriesModel
from backend.src.forecasting.feature_engineering import create_regression_features


class MLPTimeSeriesModel(BaseTimeSeriesModel):
    """
    An MLP-based time series model that:
      1) Creates features (e.g., time + lags) from df.
      2) Optionally runs Optuna hyperparameter tuning.
      3) Scales features using StandardScaler.
      4) Trains MLPRegressor (1-step-ahead).
      5) 'predict()' does single-step predictions on new data.
      6) 'predict_multistep()' iteratively forecasts n_steps into the future.
    """

    def __init__(self, params: Dict[str, Any] = None):
        # Default hyperparams (if user doesn't provide them)
        self.params = (
            params
            if params is not None
            else {
                "hidden_layer_sizes": (64,),
                "activation": "relu",
                "alpha": 1e-4,
                "learning_rate_init": 1e-3,
                "max_iter": 300,
            }
        )
        self.model = None
        self.scaler = None

    def _objective(self, trial, X, y):
        """
        The Optuna objective function.
        We'll define which hyperparams we want to search over.
        """
        hidden_layer_sizes_str = trial.suggest_categorical(
            "hidden_layer_sizes", ["(32,)", "(64,)", "(128,64)"]
        )
        # Convert from string -> actual tuple
        if hidden_layer_sizes_str == "(32,)":
            hidden_layer_sizes = (32,)
        elif hidden_layer_sizes_str == "(64,)":
            hidden_layer_sizes = (64,)
        else:
            hidden_layer_sizes = (128, 64)

        activation = trial.suggest_categorical("activation", ["relu", "tanh"])
        alpha = trial.suggest_float("alpha", 1e-5, 1e-1, log=True)
        learning_rate_init = trial.suggest_float(
            "learning_rate_init", 1e-5, 1e-2, log=True
        )

        # Scale inside objective so each trial is consistent
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        model = MLPRegressor(
            hidden_layer_sizes=hidden_layer_sizes,
            activation=activation,
            alpha=alpha,
            learning_rate_init=learning_rate_init,
            max_iter=300,
            random_state=42,
        )
        model.fit(X_scaled, y)
        preds = model.predict(X_scaled)
        mse = mean_squared_error(y, preds)
        return mse

    def tune(self, df: pd.DataFrame, n_trials=10, **kwargs) -> Dict[str, Any]:
        """
        Uses Optuna to find best hyperparams. Updates self.params internally.
        """
        X, y = create_regression_features(df)

        study = optuna.create_study(direction="minimize")
        study.optimize(lambda trial: self._objective(trial, X, y), n_trials=n_trials)

        # best_params from the study will contain only the sampled hyperparams
        best_params = study.best_params

        # Convert the hidden_layer_sizes from string -> tuple if needed
        if "hidden_layer_sizes" in best_params:
            hls_str = best_params["hidden_layer_sizes"]
            if hls_str == "(32,)":
                best_params["hidden_layer_sizes"] = (32,)
            elif hls_str == "(64,)":
                best_params["hidden_layer_sizes"] = (64,)
            else:
                best_params["hidden_layer_sizes"] = (128, 64)

        # Merge best_params into self.params, using the defaults for items not tuned
        self.params.update(best_params)
        return best_params

    def train(self, df: pd.DataFrame, **kwargs) -> None:
        """
        1) Create features
        2) Scale
        3) Fit final MLP model (1-step-ahead) with best (or default) hyperparams
        """
        X, y = create_regression_features(df)
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        # If user didn't call tune(), we still have default self.params
        self.model = MLPRegressor(
            hidden_layer_sizes=self.params.get("hidden_layer_sizes", (64,)),
            activation=self.params.get("activation", "relu"),
            alpha=self.params.get("alpha", 1e-4),
            learning_rate_init=self.params.get("learning_rate_init", 1e-3),
            max_iter=self.params.get("max_iter", 300),
            random_state=42,
        )
        self.model.fit(X_scaled, y)

    def evaluate(self, df: pd.DataFrame, **kwargs) -> float:
        """
        1) Recreate same features for df
        2) Scale with the already fitted scaler
        3) Predict (1-step) and compute MSE
        """
        if self.model is None or self.scaler is None:
            raise ValueError("Model has not been trained. Call train() first.")

        X, y_true = create_regression_features(df)
        X_scaled = self.scaler.transform(X)
        preds = self.model.predict(X_scaled)
        mse = mean_squared_error(y_true, preds)
        return mse

    def _predict_single_step(self, df: pd.DataFrame) -> np.ndarray:
        """
        Generate 1-step predictions from the trained MLP model on new data.

        Args:
            df (pd.DataFrame): A DataFrame containing the relevant columns
                              that create_regression_features() expects.

        Returns:
            np.ndarray: Model predictions for the given DataFrame.
        """
        if self.model is None or self.scaler is None:
            raise ValueError("Model has not been trained. Call train() first.")

        X, _ = create_regression_features(df)
        X_scaled = self.scaler.transform(X)
        preds = self.model.predict(X_scaled)
        return preds

    def predict(self, df: pd.DataFrame, n_steps: int = 30, **kwargs) -> np.ndarray:
        """
        Iteratively forecast n_steps into the future.
        This uses the model's own predictions as input for the next step.

        Args:
            df_init (pd.DataFrame): The initial DataFrame with 'value' column and
                                    a DateTime index up to the last known time.
            n_steps (int): How many steps to forecast forward.



        Returns:

            freq (str): The frequency of each step if you have a DateTime index
                        (e.g. 'H' for hourly, 'D' for daily, etc.)

        Returns:
            np.ndarray: Array of length n_steps with the forecasted values.
        """

        # freq: str = "h" from kwargs
        freq = kwargs.get("freq", "h")

        if self.model is None or self.scaler is None:
            raise ValueError("Model has not been trained. Call train() first.")

        df_current = df.copy()
        preds = []

        for step in range(n_steps):
            # 1) Build features from the current data
            X, _ = create_regression_features(df_current)
            X_scaled = self.scaler.transform(X)
            # 2) Predict only the last row's next-step value
            step_pred = self.model._predict_single_step(X_scaled)[-1]
            preds.append(step_pred)

            # 3) Append the new predicted value to df_current
            #    so the next iteration can see it
            next_time = df_current.index[-1] + pd.to_timedelta(1, unit=freq)
            df_current.loc[next_time, "value"] = step_pred

        return np.array(preds)
