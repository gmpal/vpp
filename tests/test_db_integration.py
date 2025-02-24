# tests/test_db_integration.py - Integration tests for the database schema and CRUD operations
"""
Make sure you run 
> docker run -d --name timescale-test -p 5432:5432 -e POSTGRES_PASSWORD=testpass timescale/timescaledb-ha:pg17 
before running this suite  
And stop it afterwards with 
> docker stop timescale-test
> docker rm timescale-test
"""
import pytest
import pandas as pd


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
        "wind",
        "wind_forecast",
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
    df = crud_manager.load_historical_data(
        "solar", "source123", start="2023-01-01", end="2023-01-02"
    )
    assert len(df) == 2
    assert df.index[0] == timestamp1  # Both are UTC-aware
    assert df["value"].iloc[0] == 42.0


def test_save_and_load_forecast(crud_manager, schema_manager, cleanup):
    """Test saving and loading forecast data for a renewable source."""
    forecasted_df = pd.DataFrame(
        {"value": [42.0, 43.0]},
        index=pd.to_datetime(["2023-01-01", "2023-01-02"], utc=True),  # Make UTC-aware
    )
    crud_manager.save_forecast("solar", "source123", forecasted_df)
    df = crud_manager.load_forecasted_data(
        "solar", "source123", start="2023-01-01", end="2023-01-02"
    )
    assert len(df) == 2
    assert df.index[0] == pd.Timestamp("2023-01-01", tz="UTC")  # Match UTC
    assert df["yhat"].iloc[0] == 42.0
