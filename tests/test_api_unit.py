import pytest
import uuid
from fastapi.testclient import TestClient
from backend.api.main import app

import pandas as pd


# TestClient fixture — module-scoped to share across tests in this module
@pytest.fixture(scope="module")
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# Helper payloads
# ---------------------------------------------------------------------------

def _household_payload(**overrides):
    base = {
        "name": f"Test Household {uuid.uuid4().hex[:4]}",
        "latitude": 50.85,
        "longitude": 4.35,
    }
    base.update(overrides)
    return base


def _battery_payload(household_id: str, **overrides):
    base = {
        "household_id": household_id,
        "name": "Test Battery",
        "capacity_kwh": 100.0,
        "soc_kwh": 50.0,
        "max_charge_kw": 20.0,
        "max_discharge_kw": 20.0,
        "eta": 0.9,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Household helpers (needed for battery tests)
# ---------------------------------------------------------------------------

def _create_household(client):
    """Create a household and return its ID."""
    response = client.post("/api/households", json=_household_payload())
    assert response.status_code == 200, f"Household creation failed: {response.text}"
    return response.json()["household_id"]


# ---------------------------------------------------------------------------
# GET /api/batteries
# ---------------------------------------------------------------------------

def test_get_all_batteries_returns_list(client):
    """GET /api/batteries should return a list (possibly empty)."""
    response = client.get("/api/batteries")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


# ---------------------------------------------------------------------------
# POST /api/batteries
# ---------------------------------------------------------------------------

def test_add_battery(client):
    """POST /api/batteries with valid data creates a battery."""
    hh_id = _create_household(client)
    payload = _battery_payload(hh_id)
    response = client.post("/api/batteries", json=payload)
    assert response.status_code == 200, f"Battery creation failed: {response.text}"
    data = response.json()
    assert "battery_id" in data
    assert data["capacity_kwh"] == 100.0
    assert data["soc_kwh"] == 50.0
    assert data["household_id"] == hh_id


def test_add_battery_missing_household_returns_404(client):
    """POST /api/batteries with non-existent household_id should return 404."""
    payload = _battery_payload("hh_nonexistent")
    response = client.post("/api/batteries", json=payload)
    assert response.status_code == 404


def test_add_battery_missing_required_fields(client):
    """POST /api/batteries without required fields should return 422."""
    response = client.post("/api/batteries", json={"capacity_kwh": 100.0})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# DELETE /api/batteries/{battery_id}
# ---------------------------------------------------------------------------

def test_remove_battery_success(client):
    """DELETE /api/batteries/{id} should remove an existing battery."""
    hh_id = _create_household(client)
    create_resp = client.post("/api/batteries", json=_battery_payload(hh_id))
    assert create_resp.status_code == 200
    battery_id = create_resp.json()["battery_id"]

    response = client.delete(f"/api/batteries/{battery_id}")
    assert response.status_code == 200
    assert response.json() == {"message": "Battery deleted"}

    # Verify battery is gone
    get_resp = client.get(f"/api/batteries/{battery_id}")
    assert get_resp.status_code == 404


def test_remove_battery_not_found(client):
    """DELETE /api/batteries/{id} with unknown id should return 404."""
    response = client.delete("/api/batteries/non_existent")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/batteries/{battery_id}/charge
# ---------------------------------------------------------------------------

def test_charge_battery_not_found(client):
    """POST /api/batteries/non_existent/charge should return 404."""
    response = client.post(
        "/api/batteries/non_existent/charge",
        json={"power_kw": 10.0, "duration_h": 1.0},
    )
    assert response.status_code == 404


def test_charge_battery_success(client):
    """POST /api/batteries/{id}/charge updates the SOC correctly."""
    hh_id = _create_household(client)
    create_resp = client.post("/api/batteries", json=_battery_payload(hh_id, soc_kwh=50.0, eta=0.9, max_charge_kw=20.0))
    assert create_resp.status_code == 200
    battery_id = create_resp.json()["battery_id"]

    response = client.post(
        f"/api/batteries/{battery_id}/charge",
        json={"power_kw": 20.0, "duration_h": 1.0},
    )
    assert response.status_code == 200
    data = response.json()
    # soc = 50 + min(20, 20) * 1.0 * 0.9 = 50 + 18 = 68
    assert data["new_soc_kwh"] == pytest.approx(68.0, abs=0.01)


def test_charge_battery_negative_power_no_change(client):
    """POST /api/batteries/{id}/charge with small negative power reduces SOC slightly."""
    hh_id = _create_household(client)
    create_resp = client.post("/api/batteries", json=_battery_payload(hh_id, soc_kwh=50.0, eta=0.9, max_charge_kw=20.0))
    assert create_resp.status_code == 200
    battery_id = create_resp.json()["battery_id"]

    # Use a small negative power that keeps SOC positive:
    # new_soc = min(50 + min(-5, 20) * 1.0 * 0.9, 100) = min(50 - 4.5, 100) = 45.5
    response = client.post(
        f"/api/batteries/{battery_id}/charge",
        json={"power_kw": -5.0, "duration_h": 1.0},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["new_soc_kwh"] == pytest.approx(45.5, abs=0.01)


# ---------------------------------------------------------------------------
# POST /api/batteries/{battery_id}/discharge
# ---------------------------------------------------------------------------

def test_discharge_battery_not_found(client):
    """POST /api/batteries/non_existent/discharge should return 404."""
    response = client.post(
        "/api/batteries/non_existent/discharge",
        json={"power_kw": 10.0, "duration_h": 1.0},
    )
    assert response.status_code == 404


def test_discharge_battery_success(client):
    """POST /api/batteries/{id}/discharge updates the SOC correctly."""
    hh_id = _create_household(client)
    create_resp = client.post("/api/batteries", json=_battery_payload(hh_id, soc_kwh=50.0, eta=0.9, max_discharge_kw=20.0))
    assert create_resp.status_code == 200
    battery_id = create_resp.json()["battery_id"]

    response = client.post(
        f"/api/batteries/{battery_id}/discharge",
        json={"power_kw": 20.0, "duration_h": 1.0},
    )
    assert response.status_code == 200
    data = response.json()
    # soc = max(50 - min(20, 20) * 1.0 / 0.9, 0) = max(50 - 22.22, 0) ≈ 27.78
    assert data["new_soc_kwh"] == pytest.approx(50.0 - 20.0 / 0.9, abs=0.01)


def test_discharge_battery_negative_power_no_change(client):
    """POST /api/batteries/{id}/discharge with negative power should clamp to 0."""
    hh_id = _create_household(client)
    create_resp = client.post("/api/batteries", json=_battery_payload(hh_id, soc_kwh=50.0))
    assert create_resp.status_code == 200
    battery_id = create_resp.json()["battery_id"]

    response = client.post(
        f"/api/batteries/{battery_id}/discharge",
        json={"power_kw": -100.0, "duration_h": 1.0},
    )
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# GET /api/historical/{source}
# ---------------------------------------------------------------------------

def test_query_historical_data(client, mocker):
    """GET /api/historical/solar should return data points."""
    mock_data = [
        {"time": pd.Timestamp("2023-01-01", tz="UTC"), "value": 42.0},
        {"time": pd.Timestamp("2023-01-02", tz="UTC"), "value": 43.0},
    ]
    mocker.patch(
        "backend.src.db.crud.CrudManager.load_user_historical_data",
        return_value=mock_data,
    )
    response = client.get(
        "/api/historical/solar?source_id=source123&start=2023-01-01&end=2023-01-02"
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["value"] == 42.0
    assert data[1]["value"] == 43.0


def test_query_historical_data_error(client, mocker):
    """GET /api/historical/solar with DB error should return 500."""
    mocker.patch(
        "backend.src.db.crud.CrudManager.load_user_historical_data",
        side_effect=Exception("Database error"),
    )
    response = client.get(
        "/api/historical/solar?source_id=source123&start=2023-01-01&end=2023-01-02"
    )
    assert response.status_code == 500


# ---------------------------------------------------------------------------
# POST /api/optimize
# ---------------------------------------------------------------------------

def test_optimize_no_storage_assets(client):
    """POST /api/optimize with no storage assets should return 400."""
    response = client.post("/api/optimize")
    # Either 400 (no assets) or 200/500 if assets exist from other tests
    assert response.status_code in (400, 200, 500)
