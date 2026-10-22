"""Tests for GET /api/warehouse endpoint."""
from fastapi.testclient import TestClient


def test_get_warehouse_contract(client: TestClient):
    """Test GET /api/warehouse returns meta, layout, and products for 100-SKU real dataset."""
    response = client.get("/api/warehouse")
    assert response.status_code == 200
    data = response.json()

    assert set(data.keys()) == {"meta", "layout", "products"}
    assert data["meta"]["real_order_data"] is True
    assert data["meta"]["month"] == "2011-06"
    assert data["layout"]["layout_id"] == "original"
    assert len(data["layout"]["slots"]) == 100
    assert len(data["layout"]["walkable_cells"]) == 341
    assert len(data["products"]) == 100
