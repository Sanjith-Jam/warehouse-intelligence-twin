"""Tests for GET /api/warehouse endpoint."""
from fastapi.testclient import TestClient


def test_get_warehouse_contract(client: TestClient):
    """Test GET /api/warehouse returns meta, layout, and products."""
    response = client.get("/api/warehouse")
    assert response.status_code == 200
    data = response.json()

    assert set(data.keys()) == {"meta", "layout", "products"}
    assert data["meta"]["dataset_id"] == "sample-v1"
    assert data["layout"]["layout_id"] == "original"
    assert len(data["layout"]["slots"]) >= 1
    assert len(data["products"]) >= 1
