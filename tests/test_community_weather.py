import httpx
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from backend.api.main import app
from backend.api.routes import weather
from backend.api.routes.weather import OPEN_METEO_FORECAST
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
# Weather tests — Open-Meteo is stubbed; unit tests never reach the internet
# ---------------------------------------------------------------------------

class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.text = "upstream error"

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("GET", OPEN_METEO_FORECAST)
            raise httpx.HTTPStatusError("boom", request=request, response=httpx.Response(self.status_code, request=request))


@pytest.fixture
def open_meteo(monkeypatch):
    """Route weather.httpx.AsyncClient to a canned payload; returns the list of captured requests."""
    state = {"payload": {}, "status": 200, "error": None, "requests": []}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def get(self, url, params=None):
            state["requests"].append((url, params))
            if state["error"]:
                raise state["error"]
            return _FakeResponse(state["payload"], state["status"])

    monkeypatch.setattr(weather.httpx, "AsyncClient", FakeClient)
    return state


def test_weather_current_parses_open_meteo(client, open_meteo):
    open_meteo["payload"] = {
        "current_weather": {"temperature": 21.5, "windspeed": 12.0, "winddirection": 90, "is_day": 1, "cloudcover": 5},
        "hourly": {"time": ["2026-01-01T12:00"], "shortwave_radiation": [640.0], "cloudcover": [20], "temperature_2m": [22.0]},
    }
    response = client.get("/api/weather/current?lat=50.85&lon=4.35")
    assert response.status_code == 200
    data = response.json()
    assert data["source"] == "open-meteo"
    assert data["irradiance_w_m2"] == 640.0
    assert data["clouds"] == 20
    assert data["temperature"] == 22.0
    assert open_meteo["requests"][0][1]["latitude"] == 50.85


def test_weather_current_falls_back_to_synthetic_when_unreachable(client, open_meteo):
    open_meteo["error"] = httpx.ConnectError("offline")
    data = client.get("/api/weather/current?lat=50&lon=4").json()
    assert data["source"] == "synthetic"
    assert {"temperature", "clouds", "description"} <= data.keys()


def test_weather_current_upstream_http_error_is_502(client, open_meteo):
    open_meteo["status"] = 500
    assert client.get("/api/weather/current?lat=50&lon=4").status_code == 502


def test_weather_forecast_parses_hourly_series(client, open_meteo):
    open_meteo["payload"] = {
        "hourly": {
            "time": ["2026-01-01T00:00", "2026-01-01T01:00"],
            "shortwave_radiation": [0.0, 10.0],
            "windspeed_10m": [3.0, 4.0],
            "temperature_2m": [5.0, 6.0],
            "cloudcover": [100, 90],
        }
    }
    data = client.get("/api/weather/forecast?lat=50&lon=4").json()
    assert data["source"] == "open-meteo"
    assert len(data["forecasts"]) == 2
    assert data["forecasts"][1] == {
        "time": "2026-01-01T01:00",
        "irradiance_w_m2": 10.0,
        "windspeed_10m_ms": 4.0,
        "windspeed_100m_ms": 4.0,  # falls back to 10 m wind when 100 m is absent
        "temperature_c": 6.0,
        "cloudcover_pct": 90,
    }


def test_weather_forecast_unreachable_returns_empty_with_note(client, open_meteo):
    open_meteo["error"] = httpx.ConnectError("offline")
    data = client.get("/api/weather/forecast?lat=50&lon=4").json()
    assert data["forecasts"] == []
    assert data["source"] == "error"
    assert "offline" in data["note"]


def test_weather_current_requires_lat_lon(client):
    response = client.get("/api/weather/current")
    assert response.status_code == 422  # FastAPI validation error


def test_weather_forecast_requires_lat_lon(client):
    response = client.get("/api/weather/forecast")
    assert response.status_code == 422
