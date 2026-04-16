import pytest
from fastapi.testclient import TestClient
import psycopg2
import pandas as pd
from backend.api.main import app
from backend.api.routes.batteries import router as batteries
from backend.api.auth import create_access_token, get_current_user
from backend.src.db.crud import CrudManager
from backend.src.db.connection import DatabaseManager


# TestClient fixture - uses conftest.py's session-scoped bypass_auth
@pytest.fixture(scope="module")
def client(bypass_auth):
    # Auth bypass is already set up by conftest.py's session-scoped bypass_auth fixture
    # Use the same client for all integration tests
    return TestClient(app)

@pytest.fixture
def auth_headers(schema_manager):
    user_id = "test_user_id"
    db_manager = schema_manager.db
    with db_manager.connect() as conn, conn.cursor() as cursor:
        # Avoid duplicate key errors by using ON CONFLICT DO NOTHING
        cursor.execute(
            """
            INSERT INTO users (user_id, username, hashed_password)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id) DO NOTHING
            """,
            (user_id, "testuser", "hashed_pw")
        )
        conn.commit()
    token = create_access_token(user_id=user_id)
    return {"Authorization": f"Bearer {token}"}

# Fixture to reset batteries dictionary
@pytest.fixture
def reset_batteries():
    # If the module has batteries var we can clear it, otherwise pass
    pass


# Test GET /api/historical/{source}
def test_query_historical_data_integration(
    client, crud_manager, schema_manager, cleanup, auth_headers
):
    # Note that start/end in historical router endpoint expect timestamps
    response = client.get(
        "/api/historical/solar?source_id=source123",
        headers=auth_headers
    )
    assert response.status_code == 200


# Test POST /api/batteries and GET /api/batteries
def test_add_and_get_batteries_integration(
    client, reset_batteries, crud_manager, schema_manager, cleanup, auth_headers
):
    # First create a household for the user
    household_id = "hh_12345"
    with crud_manager.db.connect() as conn, conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO households (household_id, user_id, name, latitude, longitude)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (household_id) DO NOTHING
            """,
            (household_id, "test_user_id", "Test HH", 0.0, 0.0)
        )
        conn.commit()

    payload = {
        "household_id": household_id,
        "name": "Test Battery",
        "capacity_kwh": 100.0,
        "soc_kwh": 50.0,
        "max_charge_kw": 20.0,
        "max_discharge_kw": 20.0,
        "eta": 0.9,
    }
    response = client.post("/api/batteries", json=payload, headers=auth_headers)
    assert response.status_code == 200
    battery_id = response.json()["battery_id"]

    response = client.get("/api/batteries", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(b["battery_id"] == battery_id for b in data)

    # We found the battery, verify its properties
    battery = next(b for b in data if b["battery_id"] == battery_id)
    assert battery["capacity_kwh"] == 100.0


# Test POST /api/optimize with real optimization
def test_optimize_integration(client, reset_batteries, crud_manager, schema_manager, mocker, cleanup, auth_headers):

    # Mocked data for load_optimization_data
    mock_optimization_data = pd.DataFrame(
        {
            "solar": [100.0],
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
    mocker.patch(
        "backend.api.routes.optimization.optimize",
        return_value=pd.DataFrame([
            {
                "timestamp": "2023-01-01T00:00:00Z",
                "battery_id": "Bat 1",
                "solar": 100.0,
                "load": 120.0,
                "price": 0.1,
                "charge": 0.0,
                "discharge": 0.0,
                "soc": 50.0,
            },
            {
                "timestamp": "2023-01-01T00:00:00Z",
                "battery_id": "Bat 2",
                "solar": 100.0,
                "load": 120.0,
                "price": 0.1,
                "charge": 0.0,
                "discharge": 0.0,
                "soc": 100.0,
            }
        ]),
    )

    # First create a household for the user
    household_id = "hh_123456"
    with crud_manager.db.connect() as conn, conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO households (household_id, user_id, name, latitude, longitude)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (household_id) DO NOTHING
            """,
            (household_id, "test_user_id", "Test HH 2", 0.0, 0.0)
        )
        conn.commit()

    # Add two batteries
    client.post(
        "/api/batteries",
        json={
            "household_id": household_id,
            "name": "Bat 1",
            "capacity_kwh": 100.0,
            "soc_kwh": 50.0,
            "max_charge_kw": 20.0,
            "max_discharge_kw": 20.0,
            "eta": 0.9,
        },
        headers=auth_headers
    )
    client.post(
        "/api/batteries",
        json={
            "household_id": household_id,
            "name": "Bat 2",
            "capacity_kwh": 200.0,
            "soc_kwh": 100.0,
            "max_charge_kw": 40.0,
            "max_discharge_kw": 40.0,
            "eta": 0.85,
        },
        headers=auth_headers
    )

    response = client.post("/api/optimize", headers=auth_headers)
    assert response.status_code == 200


def test_add_new_source(client, schema_manager, mocker, cleanup, auth_headers):
    """Test adding a new renewable source via POST /api/sources."""

    # Mock create_new_source to return a success result
    mocker.patch(
        "backend.api.routes.sources.create_new_source",
        return_value=(True, "solar_001"),
    )

    # Make the request with a source_type
    response = client.post("/api/sources", json={"source_type": "solar", "latitude": 0.0, "longitude": 0.0}, headers=auth_headers)

    # Check the response
    assert response.status_code == 200
    data = response.json()
    assert data["source_type"] == "solar"
    assert isinstance(data["source_id"], str)  # Assuming source_id is a string


def test_add_new_source_exception(client, schema_manager, mocker, cleanup, auth_headers):
    """Test adding a new renewable source via POST /api/sources."""

    # Mock create_new_source to return a success result
    mocker.patch(
        "backend.api.routes.sources.create_new_source",
        side_effect=Exception("Test Exception"),
    )

    # Make the request with a source_type
    response = client.post("/api/sources", json={"source_type": "solar", "latitude": 0.0, "longitude": 0.0}, headers=auth_headers)

    # Check the response
    assert response.status_code == 500


def test_query_ids(client, schema_manager, cleanup, auth_headers):
    """Test querying source IDs for a given source type via GET /source-ids/{source}."""
    # Make the request
    response = client.get("api/source-ids/solar", headers=auth_headers)

    # Check the response
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


# --- Test query_forecasted_data ---
def test_query_forecasted_data_success(client, schema_manager, crud_manager, mocker, auth_headers):
    """Test successful retrieval of forecasted data."""
    # Insert test data
    timestamp1 = pd.Timestamp("2025-01-01", tz="UTC")
    timestamp2 = pd.Timestamp("2025-01-02", tz="UTC")
    with crud_manager.db.connect() as conn, conn.cursor() as cursor:
        cursor.execute("INSERT INTO solar_forecast (time, source_id, yhat) VALUES (%s, %s, %s)", (timestamp1, "solar_1", 100.0))
        cursor.execute("INSERT INTO solar_forecast (time, source_id, yhat) VALUES (%s, %s, %s)", (timestamp2, "solar_1", 200.0))
        conn.commit()

    # Make request
    response = client.get("/api/forecasted/solar", params={"source_id": "solar_1"}, headers=auth_headers)

    # Check response
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2


def test_query_forecasted_data_error(client, crud_manager, mocker, schema_manager, auth_headers):
    """Test error handling in forecasted data query."""
    # Mock load_forecasted_data to raise an exception

    # Make request
    response = client.get("/api/forecasted/nonexistant", headers=auth_headers)

    # Check error response
    assert response.status_code == 500


# --- Test query_device_counts ---
def test_query_device_counts_success(client, crud_manager, schema_manager, auth_headers):
    """Test successful retrieval of device counts."""
    # Make request
    response = client.get("/api/device-status", headers=auth_headers)

    # Check response
    assert response.status_code == 200


def test_optimize_strategy_no_batteries(client, reset_batteries, auth_headers):
    """Test optimization fails with no batteries."""
    # No batteries added
    response = client.post("/api/optimize", headers=auth_headers)

    # Check error response
    assert response.status_code == 400
    assert response.json() == {"detail": "No storage assets (EVs at home or batteries) available for optimization"}


def test_optimize_strategy_error(client, reset_batteries, crud_manager, mocker, schema_manager, auth_headers):
    """Test optimization fails with an exception."""
    household_id = "hh_err"
    with crud_manager.db.connect() as conn, conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO households (household_id, user_id, name, latitude, longitude)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (household_id) DO NOTHING
            """,
            (household_id, "test_user_id", "Test HH Err", 0.0, 0.0)
        )
        conn.commit()

    # Add a battery
    client.post(
        "/api/batteries",
        json={
            "household_id": household_id,
            "name": "Bat Err",
            "capacity_kwh": 100.0,
            "soc_kwh": 50.0,
            "max_charge_kw": 20.0,
            "max_discharge_kw": 20.0,
            "eta": 0.9,
        },
        headers=auth_headers
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
    response = client.post("/api/optimize", headers=auth_headers)

    # Check error response
    assert response.status_code == 500
