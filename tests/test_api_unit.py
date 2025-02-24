import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.api.main import app
from backend.api.routes.batteries import batteries
from backend.api.routes.optimization import router as optimize_router
from backend.api.routes.batteries import router as batteries_router

from backend.src.storage.battery import Battery


import pandas as pd


# TestClient fixture
@pytest.fixture(scope="module")
def client():
    return TestClient(app)


# Fixture to reset the in-memory batteries dictionary
@pytest.fixture
def reset_batteries():
    batteries.clear()
    yield


# Test /health endpoint
def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# Test GET /api/batteries with no batteries
def test_get_all_batteries_empty(client, reset_batteries):
    response = client.get("/api/batteries")
    assert response.status_code == 200
    assert response.json() == []


# Test POST /api/batteries to add a battery
def test_add_battery(client, reset_batteries):
    payload = {
        "capacity_kWh": 100.0,
        "current_soc_kWh": 50.0,
        "max_charge_kW": 20.0,
        "max_discharge_kW": 20.0,
        "eta": 0.9,
    }
    response = client.post("/api/batteries", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "battery_id" in data
    assert data["capacity_kWh"] == 100.0
    assert data["soc_kWh"] == 50.0


# Test POST /api/batteries/{battery_id}/charge
def test_charge_battery(client, reset_batteries):
    # First, add a battery
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

    charge_payload = {
        "power_kW": 20.0,  # Charging at 20 kW
        "duration_h": 1.0,  # For 1 hour
    }
    response = client.post(f"/api/batteries/{battery_id}/charge", json=charge_payload)
    assert response.status_code == 200

    data = response.json()
    assert data["soc_kWh"] == 68.0  # 50 + (20 * 0.9)


# Test GET /api/historical/{source} with mocked data
def test_query_historical_data(client, mocker):
    mock_df = pd.DataFrame(
        {"value": [42.0, 43.0]},
        index=pd.to_datetime(["2023-01-01", "2023-01-02"], utc=True),
    )
    # Mock the load_historical_data method of CrudManager
    mocker.patch(
        "backend.src.db.CrudManager.load_historical_data", return_value=mock_df
    )
    response = client.get(
        "/api/historical/solar?source_id=source123&start=2023-01-01&end=2023-01-02"
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0] == {"timestamp": "2023-01-01T00:00:00+00:00", "value": 42.0}
    assert data[1] == {"timestamp": "2023-01-02T00:00:00+00:00", "value": 43.0}


# Test GET /api/historical/{source} with error case
def test_query_historical_data_error(client, mocker):
    mocker.patch(
        "backend.src.db.CrudManager.load_historical_data",
        side_effect=Exception("Database error"),
    )
    response = client.get(
        "/api/historical/solar?source_id=source123&start=2023-01-01&end=2023-01-02"
    )
    assert response.status_code == 500  # Assuming the app returns 500 on errors


# Test POST /api/optimize with mocked optimization
# Test POST /api/optimize with mocked optimization
def test_optimize(client, reset_batteries, mocker):
    # Add a battery
    response = client.post(
        "/api/batteries",
        json={
            "capacity_kWh": 100.0,
            "current_soc_kWh": 50.0,
            "max_charge_kW": 20.0,
            "max_discharge_kW": 20.0,
            "eta": 0.9,
        },
    )
    assert response.status_code == 200
    battery_id = response.json()["battery_id"]

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

    # Mocked optimization result
    mock_result = pd.DataFrame(
        {
            "time": [pd.Timestamp("2023-01-01 00:00:00", tz="UTC")],
            "battery_id": [battery_id],
            "charge": [10.0],
            "discharge": [0.0],
            "soc": [59.0],  # 50 + (10 * 0.9)
            "grid_buy": [0.0],
            "grid_sell": [0.0],
            "status": ["Optimal"],
            "total_cost": [0.0],
        }
    )

    # Mock load_optimization_data to avoid DB calls
    mocker.patch(
        "backend.src.optimization.optimization.load_optimization_data",
        return_value=mock_optimization_data,
    )

    # Mock optimize (optional, for completeness)
    mocker.patch(
        "backend.api.routes.optimization.optimize",
        return_value=mock_result,
        side_effect=lambda *args, **kwargs: print(
            f"Mocked optimize called with args: {args}"
        )
        or mock_result,
    )

    # Make the API call
    response = client.post("/api/optimize")
    assert response.status_code == 200, f"API call failed: {response.text}"
    data = response.json()

    # Expected response
    expected_data = [
        {
            "time": "2023-01-01T00:00:00Z",
            "battery_id": battery_id,
            "charge": 10.0,
            "discharge": 0.0,
            "soc": 59.0,
            "grid_buy": 0.0,
            "grid_sell": 0.0,
            "status": "Optimal",
            "total_cost": 0.0,
        }
    ]
    assert data == expected_data


def test_remove_battery_success(client, reset_batteries):
    """Test removing an existing battery."""
    # Add a battery directly to the in-memory store
    batteries["bat_1"] = {"capacity_kWh": 100.0, "current_soc_kWh": 50.0}

    # Remove it via the API
    response = client.delete("/api/batteries/bat_1")

    # Check response
    assert response.status_code == 200
    assert response.json() == {"detail": "Battery removed successfully"}

    # Verify it’s gone
    assert "bat_1" not in batteries


def test_remove_battery_not_found(client, reset_batteries):
    """Test removing a non-existent battery raises 404."""
    # No batteries added
    response = client.delete("/api/batteries/non_existent")

    # Check response
    assert response.status_code == 404
    assert response.json() == {"detail": "Battery not found"}

    # Verify store is unchanged
    assert len(batteries) == 0


def test_charge_battery_not_found(client, reset_batteries):
    """Test charging a non-existent battery raises 404."""
    # No batteries added
    response = client.post(
        "/api/batteries/non_existent/charge", json={"power_kW": 10.0, "duration_h": 1.0}
    )

    # Check response
    assert response.status_code == 404
    assert response.json() == {"detail": "Battery not found"}

    # Verify store is unchanged
    assert len(batteries) == 0


def test_charge_battery_success(client, reset_batteries):
    """Test charging an existing battery."""
    batteries["bat_1"] = Battery("bat_1")
    response = client.post(
        "/api/batteries/bat_1/charge", json={"power_kW": 2.0, "duration_h": 1.0}
    )

    assert response.status_code == 200
    assert response.json()["soc_kWh"] == 7.0


def test_discharge_battery_success(client, reset_batteries):
    """Test discharging an existing battery."""
    # Add a battery with some charge
    batteries["bat_1"] = Battery("bat_1")

    # Discharge it
    response = client.post(
        "/api/batteries/bat_1/discharge", json={"power_kW": 2.0, "duration_h": 1.0}
    )

    # Check response
    assert response.status_code == 200
    assert response.json()["soc_kWh"] == 3.0

    # Verify state (adjust based on your discharge logic)
    # e.g., assert batteries["bat_1"]["current_soc_kWh"] == 30.0


def test_discharge_battery_not_found(client, reset_batteries):
    """Test discharging a non-existent battery raises 404."""
    # No batteries added
    response = client.post(
        "/api/batteries/non_existent/discharge",
        json={"power_kW": 10.0, "duration_h": 1.0},
    )

    # Check response
    assert response.status_code == 404
    assert response.json() == {"detail": "Battery not found"}

    # Verify store is unchanged
    assert len(batteries) == 0
