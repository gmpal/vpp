import os
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


# ---------------------------------------------------------------------------
# Community summary tests
# ---------------------------------------------------------------------------

def test_community_summary_returns_200(client, mock_crud):
    mock_crud.get_community_summary.return_value = {
        "total_production": 10.0,
        "total_consumption": 8.0,
        "net": 2.0,
        "ev_soc_total": 50.0,
        "ev_soc_capacity": 100.0,
        "action": "selling",
        "household_count": 3,
        "ev_count": 2,
    }
    response = client.get("/api/community/summary")
    assert response.status_code == 200


def test_community_summary_shape(client, mock_crud):
    mock_crud.get_community_summary.return_value = {
        "total_production": 10.0,
        "total_consumption": 8.0,
        "net": 2.0,
        "ev_soc_total": 50.0,
        "ev_soc_capacity": 100.0,
        "action": "selling",
        "household_count": 3,
        "ev_count": 2,
    }
    response = client.get("/api/community/summary")
    data = response.json()
    assert "total_production" in data
    assert "total_consumption" in data
    assert "net" in data
    assert "ev_soc_total" in data
    assert "ev_soc_capacity" in data
    assert "action" in data
    assert "household_count" in data
    assert "ev_count" in data


def test_community_summary_values(client, mock_crud):
    mock_crud.get_community_summary.return_value = {
        "total_production": 12.5,
        "total_consumption": 9.3,
        "net": 3.2,
        "ev_soc_total": 75.0,
        "ev_soc_capacity": 150.0,
        "action": "charging_evs",
        "household_count": 5,
        "ev_count": 4,
    }
    response = client.get("/api/community/summary")
    data = response.json()
    assert data["total_production"] == pytest.approx(12.5)
    assert data["action"] == "charging_evs"
    assert data["ev_count"] == 4


def test_community_summary_calls_crud(client, mock_crud):
    mock_crud.get_community_summary.return_value = {
        "total_production": 0.0, "total_consumption": 0.0, "net": 0.0,
        "ev_soc_total": 0.0, "ev_soc_capacity": 0.0,
        "action": "self_sufficient", "household_count": 0, "ev_count": 0,
    }
    client.get("/api/community/summary")
    mock_crud.get_community_summary.assert_called_once()


# ---------------------------------------------------------------------------
# Weather endpoint tests — no API key (synthetic fallback)
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clear_owm_key():
    """Ensure OPENWEATHERMAP_API_KEY is absent for fallback tests."""
    key = os.environ.pop("OPENWEATHERMAP_API_KEY", None)
    yield
    if key is not None:
        os.environ["OPENWEATHERMAP_API_KEY"] = key


def test_weather_current_no_key_returns_200(client):
    response = client.get("/api/weather/current?lat=50&lon=4")
    assert response.status_code == 200


def test_weather_current_no_key_synthetic_response(client):
    response = client.get("/api/weather/current?lat=50&lon=4")
    data = response.json()
    assert "temperature" in data
    assert "clouds" in data
    assert "description" in data
    assert data["description"] == "synthetic (no API key)"


def test_weather_current_no_key_has_null_sunrise_sunset(client):
    response = client.get("/api/weather/current?lat=50&lon=4")
    data = response.json()
    assert data["sunrise"] is None
    assert data["sunset"] is None


def test_weather_forecast_no_key_returns_200(client):
    response = client.get("/api/weather/forecast?lat=50&lon=4")
    assert response.status_code == 200


def test_weather_forecast_no_key_returns_empty_forecasts(client):
    response = client.get("/api/weather/forecast?lat=50&lon=4")
    data = response.json()
    assert "forecasts" in data
    assert data["forecasts"] == []


def test_weather_forecast_no_key_has_note(client):
    response = client.get("/api/weather/forecast?lat=50&lon=4")
    data = response.json()
    assert "note" in data
    assert "No API key" in data["note"]


def test_weather_current_requires_lat_lon(client):
    response = client.get("/api/weather/current")
    assert response.status_code == 422  # FastAPI validation error


def test_weather_forecast_requires_lat_lon(client):
    response = client.get("/api/weather/forecast")
    assert response.status_code == 422
