# tests/test_db_integration.py - Integration tests for the database schema and CRUD operations
"""
Requires the disposable test database: `make test-int`.
"""
import pandas as pd
import psycopg2
import pytest

pytestmark = pytest.mark.integration


def test_schema_creation(db_manager, schema_manager, cleanup):
    """Test that all expected tables and hypertables are created."""
    tables = [
        "energy_sources",
        "batteries",
        "market",
        "market_forecast",
        "load",
        "load_forecast",
        "solar",
        "solar_forecast",
    ]
    for table in tables:
        query = f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table}');"
        result = db_manager.execute(query, fetch=True)
        assert result[0][0], f"Table {table} does not exist"


def test_save_to_db_renewable(crud_manager, schema_manager, cleanup):
    """Test saving data to a renewable table (e.g., solar)."""
    timestamp = pd.Timestamp("2023-01-01", tz="UTC")  # Make UTC-aware
    crud_manager.save_to_db("solar", timestamp, "source123", 42.0)
    query = "SELECT * FROM solar WHERE source_id = %s;"
    rows = crud_manager.db.execute(query, ("source123",), fetch=True)
    assert len(rows) == 1
    assert rows[0][0] == timestamp.to_pydatetime()  # Convert to datetime for comparison
    assert rows[0][1] == "source123"
    assert rows[0][2] == 42.0


def test_load_historical_data(crud_manager, schema_manager, cleanup):
    """Test loading historical data from a renewable table."""
    timestamp1 = pd.Timestamp("2023-01-01", tz="UTC")  # Make UTC-aware
    timestamp2 = pd.Timestamp("2023-01-02", tz="UTC")  # Make UTC-aware
    crud_manager.save_to_db("solar", timestamp1, "source123", 42.0)
    crud_manager.save_to_db("solar", timestamp2, "source123", 43.0)
    rows = crud_manager.load_historical_data(
        "solar", "source123", start="2023-01-01", end="2023-01-02"
    )
    assert rows == [
        {"time": timestamp1.to_pydatetime(), "value": 42.0},
        {"time": timestamp2.to_pydatetime(), "value": 43.0},
    ]


def test_save_and_load_forecast(crud_manager, schema_manager, cleanup):
    """Test saving and loading forecast data for a renewable source."""
    forecasted_df = pd.DataFrame(
        {"value": [42.0, 43.0]},
        index=pd.to_datetime(["2023-01-01", "2023-01-02"], utc=True),  # Make UTC-aware
    )
    crud_manager.save_forecast("solar", "source123", forecasted_df)
    rows = crud_manager.load_forecasted_data(
        "solar", "source123", start="2023-01-01", end="2023-01-02"
    )
    assert rows == [
        {"time": pd.Timestamp("2023-01-01", tz="UTC").to_pydatetime(), "source_id": "source123", "yhat": 42.0},
        {"time": pd.Timestamp("2023-01-02", tz="UTC").to_pydatetime(), "source_id": "source123", "yhat": 43.0},
    ]


def _insert_ev(db_manager, vehicle_id, max_discharge_kw):
    db_manager.execute(
        "INSERT INTO electric_vehicles (vehicle_id, household_id, name, capacity_kwh, soc_kwh, "
        "max_charge_kw, max_discharge_kw, eta) VALUES (%s, 'hh_ev', 'EV', 60, 30, 11, %s, 0.95)",
        (vehicle_id, max_discharge_kw),
    )


@pytest.fixture
def ev_household(db_manager, schema_manager, cleanup):
    db_manager.execute(
        "INSERT INTO households (household_id, name, latitude, longitude) VALUES ('hh_ev', 'EV home', 50.85, 4.35)"
    )


def test_charge_only_ev_is_accepted(db_manager, ev_household):
    """EVs without vehicle-to-grid have max_discharge_kw = 0; negative stays invalid."""
    _insert_ev(db_manager, "ev_v1g", 0.0)
    assert db_manager.execute("SELECT max_discharge_kw FROM electric_vehicles", fetch=True) == [(0.0,)]

    with pytest.raises(psycopg2.errors.CheckViolation):
        _insert_ev(db_manager, "ev_negative", -1.0)


def test_charge_only_migration_relaxes_legacy_constraint(db_manager, schema_manager, ev_household):
    db_manager.execute("""
        ALTER TABLE electric_vehicles DROP CONSTRAINT electric_vehicles_max_discharge_kw_check;
        ALTER TABLE electric_vehicles ADD CONSTRAINT electric_vehicles_max_discharge_kw_check
            CHECK (max_discharge_kw > 0);
    """)
    with pytest.raises(psycopg2.errors.CheckViolation):
        _insert_ev(db_manager, "ev_v1g", 0.0)

    schema_manager._migrate_allow_charge_only_evs()
    schema_manager._migrate_allow_charge_only_evs()  # second run is a no-op
    _insert_ev(db_manager, "ev_v1g", 0.0)
    with pytest.raises(psycopg2.errors.CheckViolation):
        _insert_ev(db_manager, "ev_negative", -1.0)
