import pytest
from unittest.mock import MagicMock
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


def test_list_households_empty(client, mock_crud):
    mock_crud.get_all_households.return_value = []
    response = client.get("/api/households")
    assert response.status_code == 200
    assert response.json() == []
    mock_crud.get_all_households.assert_called_once()


def test_list_households_with_data(client, mock_crud):
    mock_crud.get_all_households.return_value = [
        {"household_id": "hh_1", "name": "House A", "latitude": 50.85, "longitude": 4.35},
        {"household_id": "hh_2", "name": "House B", "latitude": 51.0, "longitude": 4.5},
    ]
    response = client.get("/api/households")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["name"] == "House A"


def test_create_household_returns_generated_id(client, mock_crud):
    mock_crud.create_household.return_value = None
    payload = {"name": "Test House", "latitude": 50.85, "longitude": 4.35}
    response = client.post("/api/households", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "household_id" in data
    assert data["household_id"].startswith("hh_")
    assert data["name"] == "Test House"
    assert data["latitude"] == 50.85
    assert data["longitude"] == 4.35


def test_create_household_calls_crud(client, mock_crud):
    mock_crud.create_household.return_value = None
    payload = {"name": "New House", "latitude": 51.0, "longitude": 5.0}
    response = client.post("/api/households", json=payload)
    assert response.status_code == 200
    mock_crud.create_household.assert_called_once()
    args = mock_crud.create_household.call_args[0]
    assert args[1] == "New House"
    assert args[2] == 51.0
    assert args[3] == 5.0


def test_get_household_found(client, mock_crud):
    mock_crud.get_household.return_value = {
        "household_id": "hh_abc123",
        "name": "My House",
        "latitude": 50.85,
        "longitude": 4.35,
    }
    response = client.get("/api/households/hh_abc123")
    assert response.status_code == 200
    data = response.json()
    assert data["household_id"] == "hh_abc123"
    assert data["name"] == "My House"


def test_get_household_not_found(client, mock_crud):
    mock_crud.get_household.return_value = None
    response = client.get("/api/households/nonexistent")
    assert response.status_code == 404


def test_delete_household_found(client, mock_crud):
    mock_crud.get_household.return_value = {
        "household_id": "hh_1", "name": "H1", "latitude": 50.0, "longitude": 4.0,
    }
    response = client.delete("/api/households/hh_1")
    assert response.status_code == 200
    mock_crud.delete_household.assert_called_once_with("hh_1")


def test_delete_household_not_found(client, mock_crud):
    mock_crud.get_household.return_value = None
    response = client.delete("/api/households/nonexistent")
    assert response.status_code == 404
    mock_crud.delete_household.assert_not_called()


def test_household_summary_with_evs(client, mock_crud):
    mock_crud.get_household.return_value = {
        "household_id": "hh_1", "name": "H1", "latitude": 50.0, "longitude": 4.0,
    }
    mock_crud.get_evs_by_household.return_value = [
        {"soc_kwh": 30.0, "capacity_kwh": 75.0},
        {"soc_kwh": 20.0, "capacity_kwh": 50.0},
    ]
    response = client.get("/api/households/hh_1/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["household_id"] == "hh_1"
    assert data["ev_count"] == 2
    assert data["ev_soc_kwh"] == pytest.approx(50.0)
    assert data["ev_capacity_kwh"] == pytest.approx(125.0)
    assert data["ev_soc_pct"] == pytest.approx(40.0)


def test_household_summary_no_evs(client, mock_crud):
    mock_crud.get_household.return_value = {
        "household_id": "hh_1", "name": "H1", "latitude": 50.0, "longitude": 4.0,
    }
    mock_crud.get_evs_by_household.return_value = []
    response = client.get("/api/households/hh_1/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["ev_count"] == 0
    assert data["ev_soc_kwh"] == 0
    assert data["ev_soc_pct"] == 0


def test_household_summary_not_found(client, mock_crud):
    mock_crud.get_household.return_value = None
    response = client.get("/api/households/nonexistent/summary")
    assert response.status_code == 404
