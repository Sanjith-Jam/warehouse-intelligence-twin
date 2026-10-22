"""Tests for /health endpoint."""
from fastapi.testclient import TestClient


def test_health_check(client: TestClient):
    """Test GET /health returns exact status ok payload."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
