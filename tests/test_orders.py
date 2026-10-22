"""Tests for GET /api/orders endpoint."""
from fastapi.testclient import TestClient


def test_get_orders_contract(client: TestClient):
    """Test GET /api/orders returns dataset_id and immutable orders."""
    response = client.get("/api/orders")
    assert response.status_code == 200
    data = response.json()

    assert set(data.keys()) == {"dataset_id", "orders"}
    assert data["dataset_id"] == "sample-v1"
    assert isinstance(data["orders"], list)
    assert len(data["orders"]) >= 1
    first_order = data["orders"][0]
    assert "order_id" in first_order
    assert "lines" in first_order
    assert len(first_order["lines"]) >= 1
