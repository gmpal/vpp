import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from unittest.mock import Mock
from backend.src.pipelines.generation import (
    read_generation_config,
    generate_weather_data,
    generate_wind_data,
    generate_pv_data,
    generate_synthetic_load_data,
    generate_synthetic_market_price,
)


# --- Test read_generation_config ---
def test_read_generation_config(mocker):
    """Test reading generation config from config.ini."""
    mock_config = mocker.patch("configparser.ConfigParser")
    mock_config.return_value.get.side_effect = [
        "./backend/data/",
        "10",
        "h",
        "100",
        "1",  # output_path, num_sources, freq, num_days, sleeping_time
    ]

    config = read_generation_config("test_config.ini")

    assert config["output_path"] == "./backend/data/"
    assert config["num_sources"] == 10
    assert config["freq"] == "h"
    assert config["num_days"] == 100
    assert config["sleeping_time"] == 1


# --- Test generate_weather_data ---
def test_generate_weather_data(mocker):
    """Test generating synthetic weather data."""
    mocker.patch("numpy.random.seed")  # Mock seed for reproducibility
    mock_to_csv = mocker.patch("pandas.DataFrame.to_csv")

    df = generate_weather_data(
        starting_date="2025-01-01 00:00",
        num_days=1,
        freq="h",
        output_path="../data/",
        source_id="1",
    )

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 24  # 24 hours
    assert list(df.columns) == [
        ("ghi", ""),
        ("dni", ""),
        ("dhi", ""),
        ("wind_speed", 100),
        ("temperature", 2),
        ("pressure", 0),
    ]
    assert df.index[0] == pd.Timestamp("2025-01-01 00:00:00")
    assert (df["ghi"] >= 0).all() and (df["ghi"] <= 1000).all()
    mock_to_csv.assert_called_once_with("../data/1_weather_data.csv")


# --- Test generate_wind_data ---
def test_generate_wind_data_with_df(mocker):
    """Test wind data generation with provided weather DataFrame."""

    weather_df = pd.DataFrame(
        {
            ("wind_speed", 100): [5.0, 6.0],
            ("temperature", 2): [10.0, 11.0],
            ("pressure", 0): [101325, 101325],
        },
        index=pd.to_datetime(["2025-01-01 00:00", "2025-01-01 01:00"]),
    )

    power_output = generate_wind_data(
        weather_data=weather_df, output_path=None, source_id="1"
    )

    assert isinstance(power_output, pd.Series)
    assert len(power_output) == 2
    assert power_output.index[0] == pd.Timestamp("2025-01-01 00:00:00")


def test_generate_wind_data_no_input(mocker):
    """Test wind data generation raises ValueError with no input."""
    with pytest.raises(
        ValueError, match="Either weather_data_path or weather_data must be provided."
    ):
        generate_wind_data()


# --- Test generate_pv_data ---
def test_generate_pv_data_with_df(mocker):
    """Test PV data generation with provided weather DataFrame."""
    # Mock to_csv
    mock_to_csv = mocker.patch("pandas.Series.to_csv")

    weather_df = pd.DataFrame(
        {
            ("ghi", ""): [500, 600, 700],
            ("dni", ""): [400, 480, 560],
            ("dhi", ""): [100, 120, 140],
            ("temperature", 2): [10.0, 11.0, 12.0],
            ("wind_speed", 100): [5.0, 6.0, 7.0],
            ("pressure", 0): [101325, 101325, 101325],
        },
        index=pd.to_datetime(
            ["2025-01-01 00:00", "2025-01-01 01:00", "2025-01-01 02:00"]
        ),
    )

    ac_power = generate_pv_data(
        weather_data=weather_df, output_path=None, source_id="1"
    )

    assert isinstance(ac_power, pd.Series)
    assert len(ac_power) == 2
    assert ac_power.index[0] == pd.Timestamp("2025-01-01 01:00:00")
    mock_to_csv.assert_not_called()  # output_path is None


def test_generate_pv_data_no_input(mocker):
    """Test PV data generation raises ValueError with no input."""
    with pytest.raises(
        ValueError, match="You need to provide either weather_data or weather_data_path"
    ):
        generate_pv_data()


# --- Test generate_synthetic_load_data ---
def test_generate_synthetic_load_data(mocker):
    """Test generating synthetic load data."""
    mocker.patch(
        "numpy.random.rand", side_effect=lambda: 0.5
    )  # Fixed noise for reproducibility
    mock_to_csv = mocker.patch("pandas.Series.to_csv")

    load_series = generate_synthetic_load_data(
        starting_date="2025-01-01 00:00", num_days=1, freq="h", output_path="../data/"
    )

    assert isinstance(load_series, pd.Series)
    assert len(load_series) == 24
    assert load_series.name == "Load_kW"
    assert load_series.index[0] == pd.Timestamp("2025-01-01 00:00:00")
    # Check ranges: night (0-6h), day (6-17h), evening (17-24h)
    assert (load_series[0:6] >= 4.0).all() and (
        load_series[0:6] <= 5.0
    ).all()  # 0.4 * 10 + 0.2 * 0.5
    assert (load_series[6:17] >= 8.0).all() and (
        load_series[6:17] <= 9.5
    ).all()  # 0.8 * 10 + 0.3 * 0.5
    assert (load_series[17:24] >= 15.0).all() and (
        load_series[17:24] <= 17.5
    ).all()  # 1.5 * 10 + 0.5 * 0.5
    mock_to_csv.assert_called_once_with("../data/synthetic_load_data.csv", header=True)


# --- Test generate_synthetic_market_price ---
def test_generate_synthetic_market_price(mocker):
    """Test generating synthetic market price data."""
    mocker.patch(
        "numpy.random.randn", side_effect=lambda: 0.0
    )  # Fixed noise for reproducibility
    mock_to_csv = mocker.patch("pandas.Series.to_csv")

    price_series = generate_synthetic_market_price(
        starting_date="2025-01-01 00:00", num_days=1, freq="h", output_path="../data/"
    )

    assert isinstance(price_series, pd.Series)
    assert len(price_series) == 24
    assert price_series.name == "MarketPrice"
    assert price_series.index[0] == pd.Timestamp("2025-01-01 00:00:00")
    # Check sinusoidal pattern: base=50, amplitude=20, no noise
    assert price_series[0] == pytest.approx(50.0, abs=1e-6)  # sin(0) = 0
    assert price_series[6] == pytest.approx(70.0, abs=1e-6)  # sin(pi/2) = 1, 50 + 20
    assert price_series[12] == pytest.approx(50.0, abs=1e-6)  # sin(pi) = 0
    mock_to_csv.assert_called_once_with(
        "../data/synthetic_market_price.csv", header=True
    )
