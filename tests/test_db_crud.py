# tests/test_db_crud.py
import pytest
import pandas as pd
from unittest.mock import MagicMock, Mock, patch
from backend.src.db.crud import CrudManager
from backend.src.exceptions import InvalidTableNameError
from backend.src.db.connection import DatabaseManager


@pytest.fixture
def mock_db_manager():
    """Fixture to create a mocked DatabaseManager."""
    db = Mock(spec=DatabaseManager)
    db.renewables = ["solar"]
    db.execute = Mock()  # Mock the execute method
    return db


@pytest.fixture
def crud_manager(mock_db_manager):
    """Fixture to create a CrudManager instance with a mocked db."""
    return CrudManager(mock_db_manager)


def test_init(crud_manager, mock_db_manager):
    """Test CrudManager initialization."""
    assert crud_manager.db == mock_db_manager
    assert crud_manager.db.renewables == ["solar"]


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


def test_create_battery(crud_manager):
    crud_manager.create_battery("bat1", "hh_1", "Home", 10.0, 5.0, 2.0, 2.0, 0.9)
    query, params = crud_manager.db.execute.call_args[0]
    assert query.startswith("INSERT INTO batteries (battery_id, household_id, name,")
    assert params == ("bat1", "hh_1", "Home", 10.0, 5.0, 2.0, 2.0, 0.9)


def test_get_battery_maps_row(crud_manager):
    crud_manager.db.execute.return_value = [("bat1", "hh_1", "Home", 10.0, 5.0, 2.0, 2.0, 0.9)]
    assert crud_manager.get_battery("bat1") == {
        "battery_id": "bat1", "household_id": "hh_1", "name": "Home", "capacity_kwh": 10.0,
        "soc_kwh": 5.0, "max_charge_kw": 2.0, "max_discharge_kw": 2.0, "eta": 0.9,
    }
    assert crud_manager.db.execute.call_args[0][1] == ("bat1",)


def test_get_battery_missing_returns_none(crud_manager):
    crud_manager.db.execute.return_value = []
    assert crud_manager.get_battery("nope") is None


def test_get_all_batteries(crud_manager):
    crud_manager.db.execute.return_value = [("b1", "h", "n", 1.0, 0.5, 1.0, 1.0, 0.95), ("b2", "h", "n", 2.0, 1.0, 1.0, 1.0, 0.95)]
    assert [b["battery_id"] for b in crud_manager.get_all_batteries()] == ["b1", "b2"]


def test_update_and_delete_battery(crud_manager):
    crud_manager.update_battery_soc("bat1", 7.5)
    crud_manager.delete_battery("bat1")
    calls = crud_manager.db.execute.call_args_list
    assert calls[0][0] == ("UPDATE batteries SET soc_kwh = %s WHERE battery_id = %s", (7.5, "bat1"))
    assert calls[1][0] == ("DELETE FROM batteries WHERE battery_id = %s", ("bat1",))


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

    assert df == [{"time": "2023-01-01", "value": 42.0}, {"time": "2023-01-02", "value": 43.0}]


def test_load_historical_data_no_filter(crud_manager):
    """Test loading historical data with no filters."""
    crud_manager.db.execute.return_value = []
    df = crud_manager.load_historical_data("load")

    expected_query = "SELECT time, value FROM load  ORDER BY time"
    crud_manager.db.execute.assert_called_once_with(expected_query, [], fetch=True)
    assert df == []


@pytest.fixture
def bulk_insert(crud_manager):
    """Capture execute_values calls; the connection and cursor are mocks."""
    conn = MagicMock()
    cursor = conn.cursor.return_value.__enter__.return_value
    conn.__enter__.return_value = conn
    crud_manager.db.connect = Mock(return_value=conn)
    with patch("backend.src.db.crud.execute_values") as execute_values:
        yield execute_values, cursor, conn


def test_save_forecast_with_source_id(crud_manager, bulk_insert):
    """Forecasts are inserted in one batch."""
    execute_values, cursor, conn = bulk_insert
    forecasted_df = pd.DataFrame(
        {"value": [42.0, 43.0]}, index=pd.to_datetime(["2023-01-01", "2023-01-02"])
    )

    crud_manager.save_forecast("solar", "source123", forecasted_df)

    execute_values.assert_called_once_with(
        cursor,
        "INSERT INTO solar_forecast (time, source_id, yhat) VALUES %s",
        [(pd.Timestamp("2023-01-01"), "source123", 42.0), (pd.Timestamp("2023-01-02"), "source123", 43.0)],
        page_size=1000,
    )
    crud_manager.db.execute.assert_not_called()
    conn.close.assert_called_once()


def test_save_forecast_no_source_id(crud_manager, bulk_insert):
    execute_values, cursor, _ = bulk_insert
    forecasted_df = pd.DataFrame(
        {"value": [42.0, 43.0]}, index=pd.to_datetime(["2023-01-01", "2023-01-02"])
    )

    crud_manager.save_forecast("load", None, forecasted_df)

    execute_values.assert_called_once_with(
        cursor,
        "INSERT INTO load_forecast (time, yhat) VALUES %s",
        [(pd.Timestamp("2023-01-01"), 42.0), (pd.Timestamp("2023-01-02"), 43.0)],
        page_size=1000,
    )


def test_save_series_batches_non_renewable_rows(crud_manager, bulk_insert):
    execute_values, cursor, conn = bulk_insert
    series = pd.Series([0.1, 0.2], index=pd.to_datetime(["2023-01-01", "2023-01-02"], utc=True))

    assert crud_manager.save_series("market", series) == 2

    cursor.execute.assert_not_called()
    execute_values.assert_called_once_with(
        cursor,
        "INSERT INTO market (time, value) VALUES %s",
        [(series.index[0], 0.1), (series.index[1], 0.2)],
        page_size=1000,
    )
    conn.close.assert_called_once()


def test_save_series_replace_deletes_in_the_same_transaction(crud_manager, bulk_insert):
    execute_values, cursor, _ = bulk_insert
    series = pd.Series([5.0], index=pd.to_datetime(["2023-01-01"], utc=True))

    crud_manager.save_series("solar", series, source_id="pv1", replace=True)

    cursor.execute.assert_called_once_with("DELETE FROM solar WHERE source_id = %s", ("pv1",))
    execute_values.assert_called_once_with(
        cursor, "INSERT INTO solar (time, source_id, value) VALUES %s", [(series.index[0], "pv1", 5.0)], page_size=1000
    )


def test_save_series_requires_source_id_for_renewables(crud_manager):
    with pytest.raises(ValueError, match="source_id is required"):
        crud_manager.save_series("solar", pd.Series(dtype=float))


def test_save_series_rejects_unknown_table(crud_manager):
    with pytest.raises(InvalidTableNameError):
        crud_manager.save_series("users", pd.Series(dtype=float))


def test_load_historical_data_top_without_start_keeps_latest(crud_manager):
    crud_manager.db.execute.return_value = []
    crud_manager.load_historical_data("market", top=50)

    expected_query = "SELECT time, value FROM (SELECT time, value FROM market  ORDER BY time DESC LIMIT 50) latest ORDER BY time"
    crud_manager.db.execute.assert_called_once_with(expected_query, [], fetch=True)


def test_load_historical_data_after_is_exclusive_and_pages_forward(crud_manager):
    crud_manager.db.execute.return_value = []
    crud_manager.load_historical_data("solar", "pv1", after="2023-01-01T00:00:00", top=100)

    expected_query = "SELECT time, value FROM solar WHERE source_id = %s AND time > %s ORDER BY time LIMIT 100"
    crud_manager.db.execute.assert_called_once_with(expected_query, ["pv1", "2023-01-01T00:00:00"], fetch=True)


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

    assert df == [
        {"time": "2023-01-01", "source_id": "source123", "yhat": 42.0},
        {"time": "2023-01-02", "source_id": "source123", "yhat": 43.0},
    ]


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

    assert df == [{"time": "2023-01-01", "yhat": 42.0}]


def test_query_source_ids(crud_manager):
    """Test querying distinct source_ids."""
    crud_manager.db.execute.return_value = [("source123",), ("source456",)]
    source_ids = crud_manager.query_source_ids("solar")

    expected_query = "SELECT DISTINCT source_id FROM solar;"
    crud_manager.db.execute.assert_called_once_with(expected_query, fetch=True)
    assert source_ids == ["source123", "source456"]
