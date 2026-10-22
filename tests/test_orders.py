"""Tests for GET /api/orders endpoint."""
from fastapi.testclient import TestClient


def test_get_orders_contract(client: TestClient):
    """Test GET /api/orders returns dataset_id and 20 real UCI orders."""
    response = client.get("/api/orders")
    assert response.status_code == 200
    data = response.json()

    assert set(data.keys()) == {"dataset_id", "orders"}
    assert data["dataset_id"].startswith("uci-2011-06")
    assert isinstance(data["orders"], list)
    assert len(data["orders"]) == 20
    first_order = data["orders"][0]
    assert first_order["order_id"] == "555157"
    assert len(first_order["lines"]) >= 1
    assert first_order["lines"][0]["sku"] == "22423"
    assert first_order["lines"][0]["quantity"] == 4
