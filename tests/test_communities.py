from datetime import datetime, timezone
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


def _community(overrides=None):
    base = {
        "community_id": "00000000-0000-0000-0000-000000000001",
        "manager_user_id": "test_user_global_id",
        "name": "Green Valley",
        "location_lat": 50.85,
        "location_lon": 4.35,
        "created_at": datetime(2025, 1, 1, tzinfo=timezone.utc),
    }
    if overrides:
        base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# POST /api/communities
# ---------------------------------------------------------------------------

def test_create_community_returns_201_shape(client, mock_crud):
    mock_crud.create_community.return_value = _community()
    payload = {"name": "Green Valley", "location_lat": 50.85, "location_lon": 4.35}
    response = client.post("/api/communities", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Green Valley"
    assert data["manager_user_id"] == "test_user_global_id"
    assert "community_id" in data


def test_create_community_minimal_payload(client, mock_crud):
    """Only name is required; lat/lon default to None."""
    mock_crud.create_community.return_value = _community({"location_lat": None, "location_lon": None})
    response = client.post("/api/communities", json={"name": "Bare"})
    assert response.status_code == 200


def test_create_community_calls_crud_with_user_id(client, mock_crud):
    mock_crud.create_community.return_value = _community()
    client.post("/api/communities", json={"name": "Test"})
    mock_crud.create_community.assert_called_once()
    kwargs = mock_crud.create_community.call_args[1]
    assert kwargs["manager_user_id"] == "test_user_global_id"
    assert kwargs["name"] == "Test"


# ---------------------------------------------------------------------------
# GET /api/communities
# ---------------------------------------------------------------------------

def test_list_communities_empty(client, mock_crud):
    mock_crud.list_communities.return_value = []
    response = client.get("/api/communities")
    assert response.status_code == 200
    assert response.json() == []


def test_list_communities_returns_all_for_user(client, mock_crud):
    mock_crud.list_communities.return_value = [_community(), _community({"community_id": "00000000-0000-0000-0000-000000000002", "name": "Solar Peak"})]
    response = client.get("/api/communities")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[1]["name"] == "Solar Peak"


def test_list_communities_scoped_to_current_user(client, mock_crud):
    mock_crud.list_communities.return_value = []
    client.get("/api/communities")
    mock_crud.list_communities.assert_called_once_with(manager_user_id="test_user_global_id")


# ---------------------------------------------------------------------------
# GET /api/communities/{community_id}
# ---------------------------------------------------------------------------

def test_get_community_found(client, mock_crud):
    community = _community()
    mock_crud.get_community.return_value = community
    response = client.get(f"/api/communities/{community['community_id']}")
    assert response.status_code == 200
    assert response.json()["name"] == "Green Valley"


def test_get_community_not_found_returns_404(client, mock_crud):
    mock_crud.get_community.return_value = None
    response = client.get("/api/communities/nonexistent-id")
    assert response.status_code == 404


def test_get_community_verifies_manager_ownership(client, mock_crud):
    mock_crud.get_community.return_value = _community()
    community_id = "00000000-0000-0000-0000-000000000001"
    client.get(f"/api/communities/{community_id}")
    mock_crud.get_community.assert_called_once_with(
        community_id=community_id,
        manager_user_id="test_user_global_id",
    )


# ---------------------------------------------------------------------------
# GET /api/community/summary (existing endpoint must still work)
# ---------------------------------------------------------------------------

def test_community_summary_still_works(client, mock_crud):
    mock_crud.get_community_summary.return_value = {
        "total_production": 10.0,
        "total_consumption": 8.0,
        "net": 2.0,
        "ev_soc_total": 5.0,
        "ev_soc_capacity": 20.0,
        "battery_soc_total": 0.0,
        "battery_soc_capacity": 0.0,
        "action": "selling",
        "household_count": 1,
        "ev_count": 1,
        "battery_count": 0,
    }
    response = client.get("/api/community/summary")
    assert response.status_code == 200
    assert response.json()["action"] == "selling"
