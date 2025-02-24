# tests/test_crud.py
import pytest
import pandas as pd
from unittest.mock import Mock, patch
from backend.src.db.crud import CrudManager
from backend.src.db.connection import DatabaseManager
from backend.src.battery import Battery


@pytest.fixture
def mock_db_manager():
    """Fixture to create a mocked DatabaseManager."""
    db = Mock(spec=DatabaseManager)
    db.renewables = ["solar", "wind"]  # Match the expected renewables
    db.execute = Mock()  # Mock the execute method
    return db


@pytest.fixture
def crud_manager(mock_db_manager):
    """Fixture to create a CrudManager instance with a mocked db."""
    return CrudManager(mock_db_manager)


@pytest.fixture
def mock_battery():
    """Fixture to create a mocked Battery object."""
    battery = Mock(spec=Battery)
    battery.battery_id = "bat1"
    battery.capacity_kWh = 100.0
    battery.current_soc_kWh = 50.0
    battery.max_charge_kW = 20.0
    battery.max_discharge_kW = 20.0
    battery.round_trip_efficiency = 0.9
    return battery


def test_init(crud_manager, mock_db_manager):
    """Test CrudManager initialization."""
    assert crud_manager.db == mock_db_manager
    assert crud_manager.db.renewables == ["solar", "wind"]


@patch("pandas.Timestamp")
def test_save_to_db_renewable(mock_timestamp, crud_manager):
    """Test saving data to a renewable table (e.g., solar)."""
    timestamp = pd.Timestamp("2023-01-01")
    mock_timestamp.return_value = timestamp
    crud_manager.save_to_db("solar", timestamp, "source123", 42.0)
    expected_query = "INSERT INTO solar (time, source_id, value) VALUES (%s, %s, %s)"
    crud_manager.db.execute.assert_called_once_with(
        expected_query, (timestamp, "source123", 42.0)
    )


@patch("pandas.Timestamp")
def test_save_to_db_non_renewable(mock_timestamp, crud_manager):
    """Test saving data to a non-renewable table (e.g., load)."""
    timestamp = pd.Timestamp("2023-01-01")
    mock_timestamp.return_value = timestamp
    crud_manager.save_to_db("load", timestamp, None, 42.0)
    expected_query = "INSERT INTO load (time, value) VALUES (%s, %s)"
    crud_manager.db.execute.assert_called_once_with(expected_query, (timestamp, 42.0))


@patch("pandas.Timestamp")
def test_save_battery_state(mock_timestamp, crud_manager, mock_battery):
    """Test saving battery state."""
    timestamp = pd.Timestamp("2023-01-01")
    mock_timestamp.now.return_value = timestamp

    crud_manager.save_battery_state(mock_battery)

    delete_query = "DELETE FROM batteries WHERE battery_id = %s"
    insert_query = """
        INSERT INTO batteries 
        (time, battery_id, capacity_kWh, soc_kWh, max_charge_kW, max_discharge_kW, eta)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
    expected_calls = [
        ((delete_query, ("bat1",)), {}),
        ((insert_query, (timestamp, "bat1", 100.0, 50.0, 20.0, 20.0, 0.9)), {}),
    ]
    calls = [(call[0], call[1]) for call in crud_manager.db.execute.call_args_list]
    assert crud_manager.db.execute.call_count == 2
    assert calls == expected_calls


def test_load_historical_data_full_filter(crud_manager):
    """Test loading historical data with all filters."""
    crud_manager.db.execute.return_value = [("2023-01-01", 42.0), ("2023-01-02", 43.0)]
    df = crud_manager.load_historical_data(
        "solar", "source123", "2023-01-01", "2023-01-02", 10
    )

    expected_query = "SELECT time, value FROM solar WHERE source_id = %s AND time >= %s AND time <= %s ORDER BY time LIMIT 10"
    crud_manager.db.execute.assert_called_once_with(
        expected_query, ["source123", "2023-01-01", "2023-01-02"], fetch=True
    )

    expected_df = pd.DataFrame(
        [("2023-01-01", 42.0), ("2023-01-02", 43.0)], columns=["time", "value"]
    ).set_index("time")
    expected_df.index = pd.to_datetime(expected_df.index)
    pd.testing.assert_frame_equal(df, expected_df)


def test_load_historical_data_no_filter(crud_manager):
    """Test loading historical data with no filters."""
    crud_manager.db.execute.return_value = []
    df = crud_manager.load_historical_data("load")

    expected_query = "SELECT time, value FROM load  ORDER BY time"
    crud_manager.db.execute.assert_called_once_with(expected_query, [], fetch=True)
    assert df.empty
    assert list(df.columns) == ["value"]


def test_save_forecast_with_source_id(crud_manager):
    """Test saving forecast data with source_id."""
    forecasted_df = pd.DataFrame(
        {"value": [42.0, 43.0]}, index=pd.to_datetime(["2023-01-01", "2023-01-02"])
    )

    crud_manager.save_forecast("solar", "source123", forecasted_df)

    expected_query = (
        "INSERT INTO solar_forecast (time, source_id, yhat) VALUES (%s, %s, %s)"
    )
    expected_calls = [
        ((expected_query, [pd.Timestamp("2023-01-01"), "source123", 42.0]), {}),
        ((expected_query, [pd.Timestamp("2023-01-02"), "source123", 43.0]), {}),
    ]
    calls = [(call[0], call[1]) for call in crud_manager.db.execute.call_args_list]
    assert crud_manager.db.execute.call_count == 2
    assert calls == expected_calls


def test_save_forecast_no_source_id(crud_manager):
    """Test saving forecast data without source_id."""
    forecasted_df = pd.DataFrame(
        {"value": [42.0, 43.0]}, index=pd.to_datetime(["2023-01-01", "2023-01-02"])
    )

    crud_manager.save_forecast("load", None, forecasted_df)

    expected_query = "INSERT INTO load_forecast (time, yhat) VALUES (%s, %s)"
    expected_calls = [
        ((expected_query, [pd.Timestamp("2023-01-01"), 42.0]), {}),
        ((expected_query, [pd.Timestamp("2023-01-02"), 43.0]), {}),
    ]
    calls = [(call[0], call[1]) for call in crud_manager.db.execute.call_args_list]
    assert crud_manager.db.execute.call_count == 2
    assert calls == expected_calls


def test_load_forecasted_data_renewable(crud_manager):
    """Test loading forecasted data for a renewable with filters."""
    crud_manager.db.execute.return_value = [
        ("2023-01-01", "source123", 42.0),
        ("2023-01-02", "source123", 43.0),
    ]
    df = crud_manager.load_forecasted_data(
        "solar", "source123", "2023-01-01", "2023-01-02", 10
    )

    expected_query = "SELECT time, source_id, yhat FROM solar_forecast WHERE source_id = %s AND time >= %s AND time <= %s ORDER BY time LIMIT 10"
    crud_manager.db.execute.assert_called_once_with(
        expected_query, ["source123", "2023-01-01", "2023-01-02"], fetch=True
    )

    expected_df = pd.DataFrame(
        [("2023-01-01", "source123", 42.0), ("2023-01-02", "source123", 43.0)],
        columns=["time", "source_id", "yhat"],
    ).set_index("time")
    expected_df.index = pd.to_datetime(expected_df.index)
    pd.testing.assert_frame_equal(df, expected_df)


def test_load_forecasted_data_load(crud_manager):
    """Test loading forecasted data for load with no source_id."""
    crud_manager.db.execute.return_value = [("2023-01-01", 42.0)]
    df = crud_manager.load_forecasted_data("load", None, "2023-01-01")

    expected_query = (
        "SELECT time, yhat FROM load_forecast WHERE time >= %s ORDER BY time"
    )
    crud_manager.db.execute.assert_called_once_with(
        expected_query,
        [
            "2023-01-01",
        ],
        fetch=True,
    )

    expected_df = pd.DataFrame(
        [("2023-01-01", 42.0)], columns=["time", "yhat"]
    ).set_index("time")
    expected_df.index = pd.to_datetime(expected_df.index)
    pd.testing.assert_frame_equal(df, expected_df)


def test_query_source_ids(crud_manager):
    """Test querying distinct source_ids."""
    crud_manager.db.execute.return_value = [("source123",), ("source456",)]
    source_ids = crud_manager.query_source_ids("solar")

    expected_query = "SELECT DISTINCT source_id FROM solar;"
    crud_manager.db.execute.assert_called_once_with(expected_query, fetch=True)
    assert source_ids == ["source123", "source456"]
