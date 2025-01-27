import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error

from src.models.base import BaseTimeSeriesModel
from src.feature_engineering import create_regression_features, create_lag_features

class RandomForestTimeSeriesModel(BaseTimeSeriesModel):

    def __init__(self, params=None):
        self.params = params if params is not None else {}
        self.model = None

    ############### RandomForest Hyperopt ##############
    def objective(self, trial, X, y):
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
        X, y = self.create_regression_features(df)
        study = optuna.create_study(direction="minimize")
        study.optimize(lambda trial: random_forest_objective(trial, X, y), n_trials=n_trials)
        self.params.update(study.best_params)
        return study.best_params

    def train(self, df: pd.DataFrame, **kwargs) -> None:

        X,y  = create_regression_features(df)  # includes cyc features + lags
        n_estimators = self.params.get("n_estimators", 100)
        max_depth = self.params.get("max_depth", None)
        min_samples_split = self.params.get("min_samples_split", 2)

        self.model = RandomForestRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            min_samples_split=min_samples_split,
            random_state=42
        )
        self.model.fit(X, y)

    def evaluate_random_forest(model, df_test: pd.DataFrame):
        # We must recreate the same features for test
        X, y_true = create_regression_features(df_test)
        preds = model.predict(X)
        return mean_squared_error(y_true, preds)
