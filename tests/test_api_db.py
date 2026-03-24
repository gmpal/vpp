"""
API-to-DB integration tests.

Verifies that each API call produces the expected database state.

Prerequisites:
    docker run -d --name timescale-test -p 5432:5432 \
        -e POSTGRES_PASSWORD=testpass timescale/timescaledb-ha:pg17

Or against the dev container:
    conda run -n vpp --no-capture-output env \\
        TIMESCALEDB_HOST=localhost POSTGRES_USER=gmpal POSTGRES_PASSWORD=postgresso POSTGRES_DB=postgres \\
        pytest tests/test_api_db.py -v
"""
import pytest
import pandas as pd
from fastapi.testclient import TestClient
from unittest.mock import patch

from backend.api.main import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# Helper: direct DB query shortcut
# ---------------------------------------------------------------------------

def db_query(db_manager, sql, params=None):
    return db_manager.execute(sql, params, fetch=True) or []


# ---------------------------------------------------------------------------
# POST /api/admin/reset-db
# ---------------------------------------------------------------------------

def test_reset_db_creates_tables_and_seeds_data(client, db_manager, schema_manager):
    """reset-db must (re)create all tables and seed load + market rows."""
    response = client.post("/api/admin/reset-db")
    assert response.status_code == 200
    body = response.json()
    assert body["load_points"] == 2400   # 100 days * 24 h
    assert body["market_points"] == 2400

    expected_tables = [
        "energy_sources", "load", "load_forecast",
        "market", "market_forecast", "solar", "solar_forecast",
        "households", "electric_vehicles", "household_load",
    ]
    for table in expected_tables:
        rows = db_query(
            db_manager,
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = %s)",
            (table,),
        )
        assert rows[0][0], f"Table '{table}' missing after reset-db"

    load_count = db_query(db_manager, "SELECT COUNT(*) FROM load")[0][0]
    market_count = db_query(db_manager, "SELECT COUNT(*) FROM market")[0][0]
    assert load_count == 2400
    assert market_count == 2400


# ---------------------------------------------------------------------------
# Sources  (POST / GET / DELETE)
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_create_source():
    with patch(
        "backend.api.routes.sources.create_new_source",
        return_value=(None, "test_src_01"),
    ) as m:
        yield m


def test_post_source_inserts_db_row(client, db_manager, schema_manager, cleanup, mock_create_source):
    """POST /api/sources must insert a row into energy_sources."""
    payload = {"source_type": "solar", "latitude": 48.2, "longitude": 16.37, "name": "Test Solar"}
    response = client.post("/api/sources", json=payload)
    assert response.status_code == 200

    rows = db_query(db_manager, "SELECT source_id, type, latitude, longitude, name, household_id FROM energy_sources")
    assert len(rows) == 1
    source_id, stype, lat, lon, name, hh_id = rows[0]
    assert source_id == "test_src_01"
    assert stype == "solar"
    assert abs(lat - 48.2) < 1e-6
    assert abs(lon - 16.37) < 1e-6
    assert name == "Test Solar"
    assert hh_id is None


def test_post_source_with_household_id(client, db_manager, schema_manager, cleanup, mock_create_source):
    """POST /api/sources with household_id must persist the FK."""
    # Create a household first
    hh_resp = client.post("/api/households", json=HOUSEHOLD_PAYLOAD)
    assert hh_resp.status_code == 200
    hh_id = hh_resp.json()["household_id"]

    payload = {
        "source_type": "solar", "latitude": 48.2, "longitude": 16.37,
        "name": "Rooftop Solar", "household_id": hh_id,
    }
    response = client.post("/api/sources", json=payload)
    assert response.status_code == 200
    assert response.json()["household_id"] == hh_id

    rows = db_query(db_manager, "SELECT household_id FROM energy_sources WHERE source_id = 'test_src_01'")
    assert rows[0][0] == hh_id


def test_get_sources_returns_inserted_rows(client, db_manager, schema_manager, cleanup, mock_create_source):
    client.post("/api/sources", json={"source_type": "solar", "latitude": 1.0, "longitude": 2.0})
    response = client.get("/api/sources")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["source_id"] == "test_src_01"
    assert data[0]["source_type"] == "solar"


def test_delete_source_removes_db_rows(client, db_manager, schema_manager, cleanup, mock_create_source):
    client.post("/api/sources", json={"source_type": "solar", "latitude": 1.0, "longitude": 2.0})
    response = client.delete("/api/sources/test_src_01")
    assert response.status_code == 200
    rows = db_query(db_manager, "SELECT source_id FROM energy_sources WHERE source_id = 'test_src_01'")
    assert len(rows) == 0


def test_delete_source_also_removes_time_series_data(client, db_manager, crud_manager, schema_manager, cleanup, mock_create_source):
    client.post("/api/sources", json={"source_type": "solar", "latitude": 1.0, "longitude": 2.0})
    crud_manager.save_to_db("solar", pd.Timestamp("2024-01-01", tz="UTC"), "test_src_01", 100.0)
    crud_manager.save_forecast(
        "solar", "test_src_01",
        pd.DataFrame({"value": [50.0]}, index=pd.to_datetime(["2024-01-02"], utc=True)),
    )
    client.delete("/api/sources/test_src_01")
    assert len(db_query(db_manager, "SELECT * FROM solar WHERE source_id = 'test_src_01'")) == 0
    assert len(db_query(db_manager, "SELECT * FROM solar_forecast WHERE source_id = 'test_src_01'")) == 0


def test_delete_nonexistent_source_returns_404(client, schema_manager):
    response = client.delete("/api/sources/does_not_exist")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Households  (POST / GET / DELETE + load profile generation)
# ---------------------------------------------------------------------------

HOUSEHOLD_PAYLOAD = {
    "name": "Test House",
    "latitude": 48.2,
    "longitude": 16.37,
    "solar_panels": 4,
    "building_type": "household",
    "num_people": 3,
    "num_evs": 1,
}


def test_post_household_inserts_db_row(client, db_manager, schema_manager, cleanup):
    response = client.post("/api/households", json=HOUSEHOLD_PAYLOAD)
    assert response.status_code == 200
    hh_id = response.json()["household_id"]
    rows = db_query(
        db_manager,
        "SELECT household_id, name, solar_panels, num_people FROM households WHERE household_id = %s",
        (hh_id,),
    )
    assert len(rows) == 1
    assert rows[0][1] == "Test House"
    assert rows[0][2] == 4
    assert rows[0][3] == 3


def test_post_household_generates_load_profile(client, db_manager, schema_manager, cleanup):
    """POST /api/households must generate 30 days of hourly load in household_load."""
    response = client.post("/api/households", json=HOUSEHOLD_PAYLOAD)
    assert response.status_code == 200
    hh_id = response.json()["household_id"]

    rows = db_query(
        db_manager,
        "SELECT COUNT(*) FROM household_load WHERE household_id = %s",
        (hh_id,),
    )
    assert rows[0][0] == 720  # 30 days * 24 h


def test_get_household_returns_correct_row(client, db_manager, schema_manager, cleanup):
    post_resp = client.post("/api/households", json=HOUSEHOLD_PAYLOAD)
    hh_id = post_resp.json()["household_id"]
    get_resp = client.get(f"/api/households/{hh_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["household_id"] == hh_id
    assert data["name"] == "Test House"
    assert data["solar_panels"] == 4


def test_get_nonexistent_household_returns_404(client, schema_manager):
    response = client.get("/api/households/hh_doesnotexist")
    assert response.status_code == 404


def test_delete_household_removes_db_row(client, db_manager, schema_manager, cleanup):
    post_resp = client.post("/api/households", json=HOUSEHOLD_PAYLOAD)
    hh_id = post_resp.json()["household_id"]
    del_resp = client.delete(f"/api/households/{hh_id}")
    assert del_resp.status_code == 200
    rows = db_query(db_manager, "SELECT household_id FROM households WHERE household_id = %s", (hh_id,))
    assert len(rows) == 0


# ---------------------------------------------------------------------------
# Electric Vehicles  (POST / GET / charge / discharge / DELETE)
# ---------------------------------------------------------------------------

EV_PAYLOAD_TEMPLATE = {
    "name": "Test EV",
    "capacity_kwh": 60.0,
    "soc_kwh": 30.0,
    "max_charge_kw": 11.0,
    "max_discharge_kw": 11.0,
    "eta": 0.9,
    "status": "home",
}


@pytest.fixture
def household_id(client, schema_manager, cleanup):
    resp = client.post("/api/households", json=HOUSEHOLD_PAYLOAD)
    return resp.json()["household_id"]


def test_post_vehicle_inserts_db_row(client, db_manager, household_id):
    payload = {**EV_PAYLOAD_TEMPLATE, "household_id": household_id}
    response = client.post("/api/vehicles", json=payload)
    assert response.status_code == 200
    vehicle_id = response.json()["vehicle_id"]
    rows = db_query(
        db_manager,
        "SELECT vehicle_id, household_id, name, soc_kwh FROM electric_vehicles WHERE vehicle_id = %s",
        (vehicle_id,),
    )
    assert len(rows) == 1
    assert rows[0][1] == household_id
    assert rows[0][2] == "Test EV"
    assert rows[0][3] == 30.0


def test_ev_status_home_appears_in_get_home_evs(client, db_manager, household_id):
    """An EV with status='home' must appear in get_home_evs result (used by optimization)."""
    payload = {**EV_PAYLOAD_TEMPLATE, "household_id": household_id, "status": "home"}
    post_resp = client.post("/api/vehicles", json=payload)
    vehicle_id = post_resp.json()["vehicle_id"]

    rows = db_query(
        db_manager,
        "SELECT vehicle_id FROM electric_vehicles WHERE vehicle_id = %s AND status = 'home'",
        (vehicle_id,),
    )
    assert len(rows) == 1


def test_ev_status_away_excluded_from_home_evs(client, db_manager, household_id):
    """An EV with status='away' must NOT appear in home EV queries."""
    payload = {**EV_PAYLOAD_TEMPLATE, "household_id": household_id, "status": "away"}
    post_resp = client.post("/api/vehicles", json=payload)
    vehicle_id = post_resp.json()["vehicle_id"]

    rows = db_query(
        db_manager,
        "SELECT vehicle_id FROM electric_vehicles WHERE vehicle_id = %s AND status = 'home'",
        (vehicle_id,),
    )
    assert len(rows) == 0


def test_get_vehicle_returns_correct_row(client, db_manager, household_id):
    payload = {**EV_PAYLOAD_TEMPLATE, "household_id": household_id}
    post_resp = client.post("/api/vehicles", json=payload)
    vehicle_id = post_resp.json()["vehicle_id"]
    get_resp = client.get(f"/api/vehicles/{vehicle_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["vehicle_id"] == vehicle_id
    assert data["soc_kwh"] == 30.0
    assert data["capacity_kwh"] == 60.0


def test_charge_vehicle_updates_soc_in_db(client, db_manager, household_id):
    """charge: energy_in = 10 * 1 * 0.9 = 9 kWh → new SOC = 39 kWh"""
    payload = {**EV_PAYLOAD_TEMPLATE, "household_id": household_id}
    post_resp = client.post("/api/vehicles", json=payload)
    vehicle_id = post_resp.json()["vehicle_id"]

    charge_resp = client.post(f"/api/vehicles/{vehicle_id}/charge", json={"power_kw": 10.0, "duration_h": 1.0})
    assert charge_resp.status_code == 200
    assert abs(charge_resp.json()["new_soc_kwh"] - 39.0) < 0.01

    rows = db_query(db_manager, "SELECT soc_kwh FROM electric_vehicles WHERE vehicle_id = %s", (vehicle_id,))
    assert abs(rows[0][0] - 39.0) < 0.01


def test_discharge_vehicle_updates_soc_in_db(client, db_manager, household_id):
    """discharge: energy_out = 10/0.9 ≈ 11.11 kWh → new SOC ≈ 18.89 kWh"""
    payload = {**EV_PAYLOAD_TEMPLATE, "household_id": household_id}
    post_resp = client.post("/api/vehicles", json=payload)
    vehicle_id = post_resp.json()["vehicle_id"]

    discharge_resp = client.post(f"/api/vehicles/{vehicle_id}/discharge", json={"power_kw": 10.0, "duration_h": 1.0})
    assert discharge_resp.status_code == 200
    expected_soc = 30.0 - (10.0 / 0.9)
    assert abs(discharge_resp.json()["new_soc_kwh"] - expected_soc) < 0.01

    rows = db_query(db_manager, "SELECT soc_kwh FROM electric_vehicles WHERE vehicle_id = %s", (vehicle_id,))
    assert abs(rows[0][0] - expected_soc) < 0.01


def test_delete_vehicle_removes_db_row(client, db_manager, household_id):
    payload = {**EV_PAYLOAD_TEMPLATE, "household_id": household_id}
    post_resp = client.post("/api/vehicles", json=payload)
    vehicle_id = post_resp.json()["vehicle_id"]
    del_resp = client.delete(f"/api/vehicles/{vehicle_id}")
    assert del_resp.status_code == 200
    rows = db_query(db_manager, "SELECT vehicle_id FROM electric_vehicles WHERE vehicle_id = %s", (vehicle_id,))
    assert len(rows) == 0


def test_delete_household_cascades_to_vehicles(client, db_manager, schema_manager, cleanup):
    hh_resp = client.post("/api/households", json=HOUSEHOLD_PAYLOAD)
    hh_id = hh_resp.json()["household_id"]
    ev_resp = client.post("/api/vehicles", json={**EV_PAYLOAD_TEMPLATE, "household_id": hh_id})
    vehicle_id = ev_resp.json()["vehicle_id"]

    client.delete(f"/api/households/{hh_id}")

    rows = db_query(db_manager, "SELECT vehicle_id FROM electric_vehicles WHERE vehicle_id = %s", (vehicle_id,))
    assert len(rows) == 0
