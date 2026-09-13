"""Smoke tests for the FastAPI application."""
from fastapi.testclient import TestClient
from backend.api.main import app


def test_health_check():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_add_source_rejects_unsupported_type():
    """Only solar sources exist; wind is rejected by validation instead of failing in the database."""
    client = TestClient(app)
    response = client.post("/api/sources", json={"source_type": "wind", "latitude": 50.85, "longitude": 4.35})
    assert response.status_code == 422
