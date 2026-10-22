"""Tests for GET /api/demo endpoint."""
from fastapi.testclient import TestClient


def test_get_demo_contract(client: TestClient):
    """Test GET /api/demo matches exact published contract structure."""
    response = client.get("/api/demo")
    assert response.status_code == 200
    data = response.json()

    # Verify top-level keys
    assert set(data.keys()) == {"meta", "layout", "products", "orders"}

    # Verify meta
    meta = data["meta"]
    assert meta["dataset_id"] == "sample-v1"
    assert meta["source"] == "synthetic fixture"
    assert meta["month"] is None
    assert meta["real_order_data"] is False
    assert meta["synthetic_warehouse"] is True
    assert meta["cell_size_m"] == 1.5

    # Verify layout
    layout = data["layout"]
    assert layout["layout_id"] == "original"
    assert layout["width"] == 4
    assert layout["height"] == 3
    assert [0, 0] in layout["walkable_cells"]
    assert layout["dock"] == [0, 0]
    assert len(layout["slots"]) == 1
    slot = layout["slots"][0]
    assert slot["slot_id"] == "S001"
    assert slot["rack_cell"] == [1, 1]
    assert slot["access_cell"] == [1, 0]
    assert slot["sku"] == "DEMO-001"

    # Verify products
    products = data["products"]
    assert len(products) == 1
    assert products[0]["sku"] == "DEMO-001"
    assert products[0]["name"] == "Sample product"
    assert products[0]["pick_frequency"] == 1

    # Verify orders
    orders = data["orders"]
    assert len(orders) == 1
    assert orders[0]["order_id"] == "DEMO-ORDER-1"
    assert orders[0]["lines"] == [{"sku": "DEMO-001", "quantity": 2}]
