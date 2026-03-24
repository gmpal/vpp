import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from backend.api.main import app
from backend.src.dependencies import get_crud_manager


@pytest.fixture
def mock_crud():
    return MagicMock()


@pytest.fixture
def client(mock_crud):
    app.dependency_overrides[get_crud_manager] = lambda: mock_crud
    yield TestClient(app)
    app.dependency_overrides.clear()


def make_ev_data(overrides=None):
    ev = {
        "vehicle_id": "ev_test1",
        "household_id": "hh_1",
        "name": "Test EV",
        "capacity_kwh": 75.0,
        "soc_kwh": 50.0,
        "max_charge_kw": 11.0,
        "max_discharge_kw": 7.0,
        "eta": 0.9,
        "status": "home",
        "latitude": None,
        "longitude": None,
    }
    if overrides:
        ev.update(overrides)
    return ev


def test_list_vehicles_empty(client, mock_crud):
    mock_crud.get_all_evs.return_value = []
    response = client.get("/api/vehicles")
    assert response.status_code == 200
    assert response.json() == []


def test_list_vehicles_with_data(client, mock_crud):
    mock_crud.get_all_evs.return_value = [make_ev_data()]
    response = client.get("/api/vehicles")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_create_vehicle(client, mock_crud):
    ev = make_ev_data()
    mock_crud.create_ev.return_value = None
    mock_crud.get_ev.return_value = ev
    payload = {
        "household_id": "hh_1",
        "name": "Test EV",
        "capacity_kwh": 75.0,
        "soc_kwh": 50.0,
        "max_charge_kw": 11.0,
        "max_discharge_kw": 7.0,
        "eta": 0.9,
        "status": "home",
    }
    response = client.post("/api/vehicles", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test EV"
    mock_crud.create_ev.assert_called_once()


def test_get_vehicle_found(client, mock_crud):
    mock_crud.get_ev.return_value = make_ev_data()
    response = client.get("/api/vehicles/ev_test1")
    assert response.status_code == 200
    assert response.json()["vehicle_id"] == "ev_test1"


def test_get_vehicle_not_found(client, mock_crud):
    mock_crud.get_ev.return_value = None
    response = client.get("/api/vehicles/nonexistent")
    assert response.status_code == 404


def test_delete_vehicle_found(client, mock_crud):
    mock_crud.get_ev.return_value = make_ev_data()
    response = client.delete("/api/vehicles/ev_test1")
    assert response.status_code == 200
    mock_crud.delete_ev.assert_called_once_with("ev_test1")


def test_delete_vehicle_not_found(client, mock_crud):
    mock_crud.get_ev.return_value = None
    response = client.delete("/api/vehicles/nonexistent")
    assert response.status_code == 404
    mock_crud.delete_ev.assert_not_called()


def test_charge_vehicle_applies_eta(client, mock_crud):
    ev = make_ev_data({"soc_kwh": 50.0, "max_charge_kw": 11.0, "eta": 0.9, "capacity_kwh": 75.0})
    mock_crud.get_ev.return_value = ev
    mock_crud.update_ev_soc.return_value = None

    response = client.post("/api/vehicles/ev_test1/charge", json={"power_kw": 5.0, "duration_h": 1.0})
    assert response.status_code == 200
    data = response.json()
    # energy_in = min(5.0, 11.0) * 1.0 * 0.9 = 4.5
    # new_soc = min(50.0 + 4.5, 75.0) = 54.5
    assert data["new_soc_kwh"] == pytest.approx(54.5)
    assert data["actual_power_kw"] == pytest.approx(5.0)
    mock_crud.update_ev_soc.assert_called_once_with("ev_test1", pytest.approx(54.5))


def test_charge_vehicle_clamped_to_capacity(client, mock_crud):
    ev = make_ev_data({"soc_kwh": 74.0, "max_charge_kw": 11.0, "eta": 0.9, "capacity_kwh": 75.0})
    mock_crud.get_ev.return_value = ev
    mock_crud.update_ev_soc.return_value = None

    response = client.post("/api/vehicles/ev_test1/charge", json={"power_kw": 11.0, "duration_h": 1.0})
    assert response.status_code == 200
    data = response.json()
    # energy_in = 11.0 * 1.0 * 0.9 = 9.9; 74.0 + 9.9 = 83.9 → clamped to 75.0
    assert data["new_soc_kwh"] == pytest.approx(75.0)


def test_charge_vehicle_respects_max_charge_kw(client, mock_crud):
    ev = make_ev_data({"soc_kwh": 50.0, "max_charge_kw": 3.0, "eta": 0.9, "capacity_kwh": 75.0})
    mock_crud.get_ev.return_value = ev
    mock_crud.update_ev_soc.return_value = None

    response = client.post("/api/vehicles/ev_test1/charge", json={"power_kw": 11.0, "duration_h": 1.0})
    assert response.status_code == 200
    data = response.json()
    # max_charge = min(11.0, 3.0) = 3.0; energy_in = 3.0 * 1.0 * 0.9 = 2.7
    assert data["actual_power_kw"] == pytest.approx(3.0)
    assert data["new_soc_kwh"] == pytest.approx(52.7)


def test_charge_vehicle_not_found(client, mock_crud):
    mock_crud.get_ev.return_value = None
    response = client.post("/api/vehicles/nonexistent/charge", json={"power_kw": 5.0, "duration_h": 1.0})
    assert response.status_code == 404


def test_discharge_vehicle_applies_eta(client, mock_crud):
    ev = make_ev_data({"soc_kwh": 50.0, "max_discharge_kw": 7.0, "eta": 0.9})
    mock_crud.get_ev.return_value = ev
    mock_crud.update_ev_soc.return_value = None

    response = client.post("/api/vehicles/ev_test1/discharge", json={"power_kw": 5.0, "duration_h": 1.0})
    assert response.status_code == 200
    data = response.json()
    # energy_out = min(5.0, 7.0) * 1.0 = 5.0
    # new_soc = max(50.0 - 5.0/0.9, 0) = 50.0 - 5.556 ≈ 44.444
    assert data["new_soc_kwh"] == pytest.approx(50.0 - 5.0 / 0.9)
    assert data["actual_power_kw"] == pytest.approx(5.0)


def test_discharge_vehicle_clamped_to_zero(client, mock_crud):
    ev = make_ev_data({"soc_kwh": 2.0, "max_discharge_kw": 7.0, "eta": 0.9})
    mock_crud.get_ev.return_value = ev
    mock_crud.update_ev_soc.return_value = None

    response = client.post("/api/vehicles/ev_test1/discharge", json={"power_kw": 7.0, "duration_h": 1.0})
    assert response.status_code == 200
    data = response.json()
    # 2.0 - 7.0/0.9 = 2.0 - 7.78 = -5.78 → clamped to 0
    assert data["new_soc_kwh"] == pytest.approx(0.0)


def test_discharge_vehicle_respects_max_discharge_kw(client, mock_crud):
    ev = make_ev_data({"soc_kwh": 50.0, "max_discharge_kw": 4.0, "eta": 0.9})
    mock_crud.get_ev.return_value = ev
    mock_crud.update_ev_soc.return_value = None

    response = client.post("/api/vehicles/ev_test1/discharge", json={"power_kw": 7.0, "duration_h": 1.0})
    assert response.status_code == 200
    data = response.json()
    # max_discharge = min(7.0, 4.0) = 4.0
    assert data["actual_power_kw"] == pytest.approx(4.0)


def test_discharge_vehicle_not_found(client, mock_crud):
    mock_crud.get_ev.return_value = None
    response = client.post("/api/vehicles/nonexistent/discharge", json={"power_kw": 5.0, "duration_h": 1.0})
    assert response.status_code == 404
