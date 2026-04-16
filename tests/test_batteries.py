"""Unit tests for the new DB-backed batteries route."""
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from backend.api.auth import get_current_user
from backend.api.main import app
from backend.src.dependencies import get_crud_manager

_TEST_USER = {"user_id": "test_user_global_id", "id": "test_user_global_id", "username": "test_user"}


@pytest.fixture
def mock_crud():
    return MagicMock()


@pytest.fixture
def client(mock_crud):
    app.dependency_overrides[get_crud_manager] = lambda: mock_crud
    app.dependency_overrides[get_current_user] = lambda: _TEST_USER
    yield TestClient(app)
    app.dependency_overrides.pop(get_crud_manager, None)
    app.dependency_overrides.pop(get_current_user, None)


def _battery(overrides=None):
    base = {
        "battery_id": "bat_abc123",
        "household_id": "hh_1",
        "name": "Home Battery",
        "capacity_kwh": 10.0,
        "soc_kwh": 5.0,
        "max_charge_kw": 2.0,
        "max_discharge_kw": 2.0,
        "eta": 0.95,
    }
    if overrides:
        base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# GET /api/batteries
# ---------------------------------------------------------------------------

def test_list_batteries_empty(client, mock_crud):
    mock_crud.get_all_batteries.return_value = []
    response = client.get("/api/batteries")
    assert response.status_code == 200
    assert response.json() == []


def test_list_batteries_returns_user_batteries(client, mock_crud):
    mock_crud.get_all_batteries.return_value = [_battery(), _battery({"battery_id": "bat_xyz", "name": "Garage"})]
    response = client.get("/api/batteries")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["name"] == "Home Battery"


def test_list_batteries_scoped_to_user(client, mock_crud):
    mock_crud.get_all_batteries.return_value = []
    client.get("/api/batteries")
    mock_crud.get_all_batteries.assert_called_once_with(user_id="test_user_global_id")


# ---------------------------------------------------------------------------
# POST /api/batteries
# ---------------------------------------------------------------------------

def test_create_battery_verifies_household_ownership(client, mock_crud):
    mock_crud.get_household.return_value = None  # household not found
    payload = {"household_id": "hh_1", "name": "Test", "capacity_kwh": 10.0,
               "soc_kwh": 5.0, "max_charge_kw": 2.0, "max_discharge_kw": 2.0}
    response = client.post("/api/batteries", json=payload)
    assert response.status_code == 404


def test_create_battery_success(client, mock_crud):
    mock_crud.get_household.return_value = {"household_id": "hh_1"}
    mock_crud.get_battery.return_value = _battery()
    payload = {"household_id": "hh_1", "name": "Test Battery", "capacity_kwh": 10.0,
               "soc_kwh": 5.0, "max_charge_kw": 2.0, "max_discharge_kw": 2.0}
    response = client.post("/api/batteries", json=payload)
    assert response.status_code == 200
    mock_crud.create_battery.assert_called_once()


# ---------------------------------------------------------------------------
# DELETE /api/batteries/{battery_id}
# ---------------------------------------------------------------------------

def test_delete_battery_not_found_returns_404(client, mock_crud):
    mock_crud.get_battery.return_value = None
    response = client.delete("/api/batteries/nonexistent")
    assert response.status_code == 404


def test_delete_battery_wrong_user_returns_404(client, mock_crud):
    mock_crud.get_battery.return_value = _battery()
    mock_crud.get_household.return_value = None  # household not owned by user
    response = client.delete("/api/batteries/bat_abc123")
    assert response.status_code == 404


def test_delete_battery_success(client, mock_crud):
    mock_crud.get_battery.return_value = _battery()
    mock_crud.get_household.return_value = {"household_id": "hh_1"}
    response = client.delete("/api/batteries/bat_abc123")
    assert response.status_code == 200
    mock_crud.delete_battery.assert_called_once_with("bat_abc123")


# ---------------------------------------------------------------------------
# POST /api/batteries/{battery_id}/charge
# ---------------------------------------------------------------------------

def test_charge_battery_not_found_returns_404(client, mock_crud):
    mock_crud.get_battery.return_value = None
    response = client.post("/api/batteries/nonexistent/charge", json={"power_kw": 1.0})
    assert response.status_code == 404


def test_charge_battery_updates_soc(client, mock_crud):
    bat = _battery({"soc_kwh": 5.0, "max_charge_kw": 2.0, "capacity_kwh": 10.0, "eta": 0.95})
    mock_crud.get_battery.return_value = bat
    mock_crud.get_household.return_value = {"household_id": "hh_1"}
    response = client.post("/api/batteries/bat_abc123/charge", json={"power_kw": 2.0, "duration_h": 1.0})
    assert response.status_code == 200
    data = response.json()
    assert data["new_soc_kwh"] == pytest.approx(5.0 + 2.0 * 1.0 * 0.95)
    mock_crud.update_battery_soc.assert_called_once()


def test_charge_battery_respects_capacity_limit(client, mock_crud):
    bat = _battery({"soc_kwh": 9.5, "max_charge_kw": 2.0, "capacity_kwh": 10.0, "eta": 0.95})
    mock_crud.get_battery.return_value = bat
    mock_crud.get_household.return_value = {"household_id": "hh_1"}
    response = client.post("/api/batteries/bat_abc123/charge", json={"power_kw": 2.0, "duration_h": 1.0})
    assert response.status_code == 200
    assert response.json()["new_soc_kwh"] == pytest.approx(10.0)


# ---------------------------------------------------------------------------
# POST /api/batteries/{battery_id}/discharge
# ---------------------------------------------------------------------------

def test_discharge_battery_updates_soc(client, mock_crud):
    bat = _battery({"soc_kwh": 5.0, "max_discharge_kw": 2.0, "eta": 0.95})
    mock_crud.get_battery.return_value = bat
    mock_crud.get_household.return_value = {"household_id": "hh_1"}
    response = client.post("/api/batteries/bat_abc123/discharge", json={"power_kw": 2.0, "duration_h": 1.0})
    assert response.status_code == 200
    data = response.json()
    expected_soc = max(5.0 - 2.0 * 1.0 / 0.95, 0.0)
    assert data["new_soc_kwh"] == pytest.approx(expected_soc)


def test_discharge_battery_respects_zero_floor(client, mock_crud):
    bat = _battery({"soc_kwh": 0.5, "max_discharge_kw": 2.0, "eta": 0.95})
    mock_crud.get_battery.return_value = bat
    mock_crud.get_household.return_value = {"household_id": "hh_1"}
    response = client.post("/api/batteries/bat_abc123/discharge", json={"power_kw": 2.0, "duration_h": 1.0})
    assert response.status_code == 200
    assert response.json()["new_soc_kwh"] == pytest.approx(0.0)
