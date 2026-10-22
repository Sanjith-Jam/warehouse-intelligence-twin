"""Tests for GET /api/demo endpoint with real UCI Online Retail II dataset."""
from fastapi.testclient import TestClient
from backend.app.data.loader import DataLoader


def test_get_demo_contract_real_data(client: TestClient):
    """Test GET /api/demo returns authoritative June 2011 real order dataset."""
    response = client.get("/api/demo")
    assert response.status_code == 200
    data = response.json()

    # Verify top-level keys
    assert set(data.keys()) == {"meta", "layout", "products", "orders"}

    # Verify meta
    meta = data["meta"]
    assert meta["dataset_id"].startswith("uci-2011-06")
    assert meta["source"] == "UCI Online Retail II"
    assert meta["month"] == "2011-06"
    assert meta["real_order_data"] is True
    assert meta["synthetic_warehouse"] is True
    assert meta["cell_size_m"] == 1.5

    # Verify layout: 21x21 grid with 100 shelf slots
    layout = data["layout"]
    assert layout["layout_id"] == "original"
    assert layout["width"] == 21
    assert layout["height"] == 21
    assert [0, 0] in layout["walkable_cells"]
    assert layout["dock"] == [0, 0]
    assert len(layout["slots"]) == 100
    assert len(layout["walkable_cells"]) == 341

    first_slot = layout["slots"][0]
    assert first_slot["slot_id"] == "S001"
    assert len(first_slot["rack_cell"]) == 2
    assert len(first_slot["access_cell"]) == 2

    # Verify products: 100 top products ranked by monthly pick frequency
    products = data["products"]
    assert len(products) == 100
    assert all(p["pick_frequency"] > 0 for p in products)
    assert products[0]["pick_frequency"] >= products[-1]["pick_frequency"]

    # Verify orders: 20 real selected orders
    orders = data["orders"]
    assert len(orders) == 20
    assert orders[0]["order_id"] == "555157"
    assert len(orders[0]["lines"]) >= 1


def test_fallback_fixture_demo():
    """Verify DataLoader gracefully handles fallback to sample fixture when data_path is None."""
    loader = DataLoader(data_path=None)
    demo = loader.get_demo_response()
    assert demo.meta.real_order_data is False
    assert demo.meta.dataset_id == "sample-v1"
    assert len(demo.layout.slots) == 1
    assert len(demo.products) == 1
    assert len(demo.orders) == 1
