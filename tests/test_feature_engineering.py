import pytest
import pandas as pd
import numpy as np
from backend.src.forecasting.feature_engineering import (
    create_future_features,
    create_time_features,
    create_lag_features,
    create_regression_features,
)


# Sample DataFrame fixture
@pytest.fixture
def sample_df():
    dates = pd.to_datetime(
        [
            "2025-01-01 00:00:00",  # Holiday
            "2025-01-01 01:00:00",
            "2025-01-02 00:00:00",
            "2025-12-25 12:00:00",  # Holiday
        ]
    )
    return pd.DataFrame({"value": [10.0, 20.0, 30.0, 40.0]}, index=dates)


# --- Tests for create_future_features ---
def test_create_future_features_holidays(sample_df):
    """Test holiday feature is correctly added."""
    df_future = create_future_features(sample_df)

    # Check columns
    assert list(df_future.columns) == ["value", "holiday"]

    # Check holiday values
    assert df_future["holiday"].tolist() == [1, 1, 0, 1]  # Jan 1, Jan 1, Jan 2, Dec 25
    assert df_future["value"].equals(sample_df["value"])  # Original data preserved


def test_create_future_features_empty_df():
    """Test empty DataFrame handling."""
    df_empty = pd.DataFrame(index=pd.to_datetime([]))
    df_future = create_future_features(df_empty)
    assert df_future.empty
    assert list(df_future.columns) == ["holiday"]


# --- Tests for create_time_features ---
def test_create_time_features_cyclical(sample_df):
    """Test cyclical time features are correctly calculated."""
    df_time = create_time_features(sample_df)

    # Check columns
    expected_cols = [
        "value",
        "hour",
        "dayofweek",
        "dayofyear",
        "hour_sin",
        "hour_cos",
        "dow_sin",
        "dow_cos",
        "doy_sin",
        "doy_cos",
    ]
    assert list(df_time.columns) == expected_cols

    # Check specific values
    # Hour 0 (midnight) -> sin(0) = 0, cos(0) = 1
    assert df_time["hour_sin"].iloc[0] == pytest.approx(0.0, abs=1e-6)
    assert df_time["hour_cos"].iloc[0] == pytest.approx(1.0, abs=1e-6)

    # Day of week (Wednesday, Jan 1, 2025 = 2) -> sin(2 * pi * 2 / 7), cos(2 * pi * 2 / 7)
    assert df_time["dow_sin"].iloc[0] == pytest.approx(
        np.sin(2 * np.pi * 2 / 7), abs=1e-6
    )
    assert df_time["dow_cos"].iloc[0] == pytest.approx(
        np.cos(2 * np.pi * 2 / 7), abs=1e-6
    )

    # Day of year (Jan 1 = 1) -> sin(2 * pi * 1 / 365), cos(2 * pi * 1 / 365)
    assert df_time["doy_sin"].iloc[0] == pytest.approx(
        np.sin(2 * np.pi * 1 / 365), abs=1e-6
    )
    assert df_time["doy_cos"].iloc[0] == pytest.approx(
        np.cos(2 * np.pi * 1 / 365), abs=1e-6
    )


def test_create_time_features_empty_df():
    """Test empty DataFrame handling."""
    df_empty = pd.DataFrame(index=pd.to_datetime([]))
    df_time = create_time_features(df_empty)
    assert df_time.empty
    assert list(df_time.columns) == [
        "hour",
        "dayofweek",
        "dayofyear",
        "hour_sin",
        "hour_cos",
        "dow_sin",
        "dow_cos",
        "doy_sin",
        "doy_cos",
    ]


# --- Tests for create_lag_features ---
def test_create_lag_features_default_lags(sample_df):
    """Test lag features with default lags [1, 2, 3]."""
    X, y = create_lag_features(sample_df, lags=[1, 2, 3])

    # Check shapes (4 rows -> 1 row after dropping NaNs with lag 3)
    assert X.shape == (1, 3)  # 1 row, 3 lag columns
    assert y.shape == (1,)

    # Check columns
    assert list(X.columns) == ["value_lag1", "value_lag2", "value_lag3"]

    # Check values (last row: t-1=30, t-2=20, t-3=10, y=40)
    assert X["value_lag1"].iloc[0] == 30.0
    assert X["value_lag2"].iloc[0] == 20.0
    assert X["value_lag3"].iloc[0] == 10.0
    assert y.iloc[0] == 40.0


def test_create_lag_features_custom_lags(sample_df):
    """Test lag features with custom lags [1, 2]."""
    X, y = create_lag_features(sample_df, lags=[1, 2])

    # Check shapes (4 rows -> 2 rows after dropping NaNs with lag 2)
    assert X.shape == (2, 2)
    assert y.shape == (2,)

    # Check values
    assert X["value_lag1"].iloc[0] == 20.0  # t-1 for 3rd row
    assert X["value_lag2"].iloc[0] == 10.0  # t-2 for 3rd row
    assert y.iloc[0] == 30.0


def test_create_lag_features_insufficient_data():
    """Test with fewer rows than max lag."""
    df_short = pd.DataFrame({"value": [1.0]}, index=pd.to_datetime(["2025-01-01"]))
    X, y = create_lag_features(df_short, lags=[1, 2])
    assert X.empty
    assert y.empty


# --- Tests for create_regression_features ---
def test_create_regression_features(sample_df):
    """Test combined time and lag features."""
    X, y = create_regression_features(sample_df, lags=[1, 2])

    # Check shapes (4 rows -> 2 rows after lag 2)
    assert X.shape == (
        2,
        11,
    )  # 8 features: hour, dayofweek, dayofyear, 5 cyclical, 2 lags
    assert y.shape == (2,)

    # Check columns
    expected_cols = [
        "hour",
        "dayofweek",
        "dayofyear",
        "hour_sin",
        "hour_cos",
        "dow_sin",
        "dow_cos",
        "doy_sin",
        "doy_cos",
        "value_lag1",
        "value_lag2",
    ]
    assert sorted(X.columns) == sorted(expected_cols)  # Order might vary

    # Check lag values
    assert X["value_lag1"].iloc[0] == 20.0
    assert X["value_lag2"].iloc[0] == 10.0
    assert y.iloc[0] == 30.0


def test_create_regression_features_empty_df():
    """Test empty DataFrame handling."""
    df_empty = pd.DataFrame(columns=["value"], index=pd.to_datetime([]))
    X, y = create_regression_features(df_empty, lags=[1])
    assert X.empty
    assert y.empty
