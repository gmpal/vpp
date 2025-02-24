import numpy as np
import pandas as pd


def create_future_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create future covariates based on known future events or patterns.

    Args:
        df (pd.DataFrame): Input DataFrame with DateTime index.

    Returns:
        pd.DataFrame: DataFrame with future covariates.
    """
    df_future = df.copy()
    # Example: Add a 'holiday' binary feature
    holidays = ["2025-01-01", "2025-12-25"]  # List of holiday dates
    df_future["holiday"] = (
        df_future.index.normalize().isin(pd.to_datetime(holidays)).astype(int)
    )
    # Add more future covariate features as needed
    return df_future


def create_time_features(df: pd.DataFrame):
    """
    Create cyclical time features from the index (which is assumed to be datetime).
    For example: hour-of-day, day-of-week, day-of-year, etc.
    Return a new DataFrame with these features + the original 'value'.

    We do:
      - hour_sin, hour_cos
      - dayofweek_sin, dayofweek_cos
      - dayofyear_sin, dayofyear_cos
    """
    df_feat = df.copy()
    df_feat["hour"] = df_feat.index.hour
    df_feat["dayofweek"] = df_feat.index.dayofweek
    df_feat["dayofyear"] = df_feat.index.dayofyear

    # hour of day cyclical
    df_feat["hour_sin"] = np.sin(2 * np.pi * df_feat["hour"] / 24)
    df_feat["hour_cos"] = np.cos(2 * np.pi * df_feat["hour"] / 24)

    # day of week cyclical
    df_feat["dow_sin"] = np.sin(2 * np.pi * df_feat["dayofweek"] / 7)
    df_feat["dow_cos"] = np.cos(2 * np.pi * df_feat["dayofweek"] / 7)

    # day of year cyclical
    df_feat["doy_sin"] = np.sin(2 * np.pi * df_feat["dayofyear"] / 365)
    df_feat["doy_cos"] = np.cos(2 * np.pi * df_feat["dayofyear"] / 365)

    return df_feat


def create_lag_features(df: pd.DataFrame, lags=[1, 2, 3]):
    """
    Create lag features for 'value', e.g. value(t-1), value(t-2), ...
    """
    df_lags = df.copy()
    for lag in lags:
        df_lags[f"value_lag{lag}"] = df_lags["value"].shift(lag)
    df_lags.dropna(inplace=True)
    X = df_lags.drop(columns=["value"])
    y = df_lags["value"]
    return X, y


def create_regression_features(df: pd.DataFrame, lags=[1, 2, 3]):
    """
    Combine cyclical time features + lag features into a single DF for regression models.
    """
    df_time = create_time_features(df)
    X, y = create_lag_features(df_time, lags=lags)
    return X, y
