from abc import ABC, abstractmethod
import pandas as pd
from typing import Any, Dict
import numpy as np


class BaseTimeSeriesModel(ABC):
    """
    Abstract base class for a time-series forecasting model.
    Enforces a common interface for model classes: tune, train, evaluate.
    """

    @abstractmethod
    def tune(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """
        Perform hyperparameter tuning on the given DataFrame.
        Returns a dictionary of best hyperparameters or any relevant info.
        """
        pass

    @abstractmethod
    def train(self, df: pd.DataFrame, **kwargs) -> None:
        """
        Train (fit) the model on the given DataFrame (often after tuning).
        Usually, you'll store the trained model object as an instance attribute.
        """
        pass

    @abstractmethod
    def evaluate(self, df: pd.DataFrame, **kwargs) -> float:
        """
        Evaluate the model on the given DataFrame or (X,y).
        Returns a numeric metric (e.g., MSE).
        """
        pass

    def objective(self, trial, df: pd.DataFrame) -> float:
        """
        Optional method for models that require hyperparameter optimization.
        If not implemented, the tuning will be skipped or handled differently.
        """
        raise NotImplementedError(
            "Objective method should be implemented by the model."
        )

    @abstractmethod
    def predict(self, df: pd.DataFrame, steps: int = 1, **kwargs) -> np.ndarray:
        """
        Generate a forecast from the model.

        Args:
            df (pd.DataFrame): A DataFrame containing the recent history
                            (or future exogenous features) if needed.
            steps (int): Number of future steps to forecast.

        Returns:
            np.ndarray: Model predictions for the specified horizon.
        """
        pass
