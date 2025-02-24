import pytest
from fastapi.testclient import TestClient
import psycopg2
import pandas as pd
from backend.api.main import app
from backend.api.routes.batteries import batteries
from backend.src.db.crud import CrudManager
from backend.src.db.connection import DatabaseManager


# TestClient fixture
@pytest.fixture(scope="module")
def client():
    return TestClient(app)


# Fixture to reset batteries dictionary
@pytest.fixture
def reset_batteries():
    batteries.clear()
    yield


# Test GET /api/historical/{source}
def test_query_historical_data_integration(
    client, crud_manager, schema_manager, cleanup
):
    # Insert test data
    timestamp1 = pd.Timestamp("2023-01-01", tz="UTC")
    timestamp2 = pd.Timestamp("2023-01-02", tz="UTC")
    crud_manager.save_to_db("solar", timestamp1, "source123", 42.0)
    crud_manager.save_to_db("solar", timestamp2, "source123", 43.0)

    response = client.get(
        "/api/historical/solar?source_id=source123&start=2023-01-01&end=2023-01-02"
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0] == {"timestamp": "2023-01-01T00:00:00+00:00", "value": 42.0}
    assert data[1] == {"timestamp": "2023-01-02T00:00:00+00:00", "value": 43.0}


# Test POST /api/batteries and GET /api/batteries
def test_add_and_get_batteries_integration(
    client, reset_batteries, schema_manager, cleanup
):
    payload = {
        "capacity_kWh": 100.0,
        "current_soc_kWh": 50.0,
        "max_charge_kW": 20.0,
        "max_discharge_kW": 20.0,
        "eta": 0.9,
    }
    response = client.post("/api/batteries", json=payload)
    assert response.status_code == 200
    battery_id = response.json()["battery_id"]

    response = client.get("/api/batteries")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["battery_id"] == battery_id
    assert data[0]["capacity_kWh"] == 100.0


# Test POST /api/optimize with real optimization
def test_optimize_integration(client, reset_batteries, schema_manager, mocker, cleanup):

    # Mocked data for load_optimization_data
    mock_optimization_data = pd.DataFrame(
        {
            "solar": [100.0],
            "wind": [50.0],
            "load": [120.0],
            "price": [0.1],
        },
        index=[
            pd.Timestamp("2023-01-01 00:00:00", tz="UTC"),
        ],
    )

    # Mock load_optimization_data to avoid DB calls
    mocker.patch(
        "backend.src.optimization.optimization.load_optimization_data",
        return_value=mock_optimization_data,
    )

    # Add two batteries
    client.post(
        "/api/batteries",
        json={
            "capacity_kWh": 100.0,
            "current_soc_kWh": 50.0,
            "max_charge_kW": 20.0,
            "max_discharge_kW": 20.0,
            "eta": 0.9,
        },
    )
    client.post(
        "/api/batteries",
        json={
            "capacity_kWh": 200.0,
            "current_soc_kWh": 100.0,
            "max_charge_kW": 40.0,
            "max_discharge_kW": 40.0,
            "eta": 0.85,
        },
    )

    response = client.post("/api/optimize")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert all(isinstance(item, dict) for item in data)


def test_add_new_source(client, schema_manager, mocker, cleanup):
    """Test adding a new renewable source via GET /add-source."""

    # Mock create_new_source to return a success result
    mocker.patch(
        "backend.api.routes.sources.create_new_source",
        return_value=(True, "solar_001"),
    )

    # Make the request with a source_type
    response = client.get("/api/add-source", params={"source_type": "solar"})

    # Check the response
    assert response.status_code == 200
    data = response.json()
    assert data["source_type"] == "solar"
    assert isinstance(data["source_id"], str)  # Assuming source_id is a string


def test_query_ids(client, schema_manager, cleanup):
    """Test querying source IDs for a given source type via GET /source-ids/{source}."""
    # Pre-populate the database with some test data
    db_manager = schema_manager.db
    with db_manager.connect() as conn, conn.cursor() as cursor:
        cursor.execute(
            "INSERT INTO solar (time, source_id, value) VALUES ('2023-01-01', 'solar_001', 42.0)"
        )
        conn.commit()

    # Make the request
    response = client.get("api/source-ids/solar")

    # Check the response
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert sorted(data) == ["solar_001"]


# --- Test query_forecasted_data ---
def test_query_forecasted_data_success(client, schema_manager, crud_manager, mocker):
    """Test successful retrieval of forecasted data."""
    # Mock load_forecasted_data to return a sample DataFrame
    mock_df = pd.DataFrame(
        {"yhat": [100.0, 200.0]},
        index=pd.to_datetime(["2025-01-01T00:00:00", "2025-01-01T01:00:00"]),
    )
    mocker.patch(
        "backend.src.db.crud.CrudManager.load_forecasted_data", return_value=mock_df
    )

    # Make request
    response = client.get("/api/forecasted/solar", params={"source_id": "solar_1"})

    # Check response
    assert response.status_code == 200
    data = response.json()
    print(response)
    assert len(data) == 2
    assert data[0] == {"timestamp": "2025-01-01T00:00:00", "value": 100.0}
    assert data[1] == {"timestamp": "2025-01-01T01:00:00", "value": 200.0}


def test_query_forecasted_data_error(client, crud_manager, mocker, schema_manager):
    """Test error handling in forecasted data query."""
    # Mock load_forecasted_data to raise an exception

    # Make request
    response = client.get("/api/forecasted/nonexistant")

    # Check error response
    assert response.status_code == 500


# --- Test query_device_counts ---
def test_query_device_counts_success(client, crud_manager, schema_manager):
    """Test successful retrieval of device counts."""
    # Pre-populate the energy_sources table
    with crud_manager.db.connect() as conn, conn.cursor() as cursor:
        cursor.execute(
            "INSERT INTO solar (time, source_id, value) VALUES (%s, %s, %s)",
            ("1/1/2024", "123123", 10),
        )
        conn.commit()

    # Make request
    response = client.get("/api/device-status")

    # Check response
    assert response.status_code == 200
    data = response.json()
    assert data == {"solar": 1, "wind": 0}


def test_optimize_strategy_no_batteries(client, reset_batteries):
    """Test optimization fails with no batteries."""
    # No batteries added
    response = client.post("/api/optimize")

    # Check error response
    assert response.status_code == 400
    assert response.json() == {"detail": "No batteries available for optimization"}


def test_optimize_strategy_error(client, reset_batteries, mocker, schema_manager):
    """Test optimization fails with an exception."""
    # Add a battery
    client.post(
        "/api/batteries",
        json={
            "capacity_kWh": 100.0,
            "current_soc_kWh": 50.0,
            "max_charge_kW": 20.0,
            "max_discharge_kW": 20.0,
            "eta": 0.9,
        },
    )

    mock_df = pd.DataFrame(
        {"yhat": [100.0, 200.0]},
        index=pd.to_datetime(["2025-01-01T00:00:00", "2025-01-01T01:00:00"]),
    )
    mocker.patch(
        "backend.src.db.crud.CrudManager.load_forecasted_data", return_value=mock_df
    )

    # Mock optimize to raise an exception
    mocker.patch(
        "backend.src.optimization.optimization",
        side_effect=Exception("Optimization error"),
    )

    # Make request
    response = client.post("/api/optimize")

    # Check error response
    assert response.status_code == 500
