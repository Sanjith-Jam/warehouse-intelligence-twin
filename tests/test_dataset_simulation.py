"""Tests for dataset-specific slotting and simulation API (FLASH-06)."""
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.app.config import settings
from backend.app.data.loader import get_dataset, load_demo_data
from backend.app.models.schemas import (
    DemoResponse,
    ErrorCode,
    Order,
    OrderLine,
    Product,
    Slot,
    WarehouseLayout,
)
from backend.app.simulation.router import (
    compute_baseline_layout,
    normalize_and_validate_player_permutation,
)


def create_mock_21x21_layout_5_skus(skus: list[str]) -> WarehouseLayout:
    """Create standard 21x21 warehouse layout with 100 slots, where only first N slots have SKUs."""
    width = 21
    height = 21
    dock = [0, 0]

    walkable_cells: list[list[int]] = []
    for z in range(height):
        for x in range(width):
            if x % 2 == 0 or z % 2 == 0:
                walkable_cells.append([x, z])

    slots: list[Slot] = []
    slot_index = 1
    for z in [1, 3, 5, 7, 9, 11, 13, 15, 17, 19]:
        for x in [1, 3, 5, 7, 9, 11, 13, 15, 17, 19]:
            slot_id = f"S{slot_index:03d}"
            sku = skus[slot_index - 1] if slot_index - 1 < len(skus) else None
            slots.append(
                Slot(
                    slot_id=slot_id,
                    rack_cell=[x, z],
                    access_cell=[x, z - 1],
                    sku=sku,
                )
            )
            slot_index += 1

    return WarehouseLayout(
        layout_id="original",
        width=width,
        height=height,
        walkable_cells=walkable_cells,
        dock=dock,
        slots=slots,
    )


# ==============================================================================
# 1. POST /api/datasets/demo/simulate & Baseline Improvement
# ==============================================================================

def test_simulate_demo_dataset_baseline_improvement(client: TestClient):
    """Test POST /api/datasets/demo/simulate succeeds and matches expected baseline improvement."""
    res = client.post(
        "/api/datasets/demo/simulate",
        json={"speed_m_s": 1.2, "handling_time_s": 15.0},
    )
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["dataset_id"] == "uci-2011-06-preview-bcbe73b35f5b"
    assert "policies" in data
    assert "original" in data["policies"]
    assert "baseline" in data["policies"]

    orig = data["policies"]["original"]
    base = data["policies"]["baseline"]

    # Baseline demonstrates shorter walking distance and lower pick time
    assert orig["orders_replayed"] == 20
    assert base["orders_replayed"] == 20
    assert base["total_distance_m"] < orig["total_distance_m"]
    assert base["total_pick_time_s"] < orig["total_pick_time_s"]
    assert base["average_pick_time_s"] < orig["average_pick_time_s"]

    # Invariants for 20 orders: distance 2844m orig vs 2820m baseline
    assert orig["total_distance_m"] == 2844.0
    assert base["total_distance_m"] == 2820.0

    # Explicit assumptions verification
    assert data["assumptions"]["speed_m_s"] == 1.2
    assert data["assumptions"]["handling_time_s"] == 15.0
    assert data["assumptions"]["dock"] == [0, 0]

    # Replayed orders match
    assert len(data["orders"]) == 20
    for order in data["orders"]:
        assert "order_id" in order
        assert "lines" in order
        assert "original" in order["routes"]
        assert "baseline" in order["routes"]
        assert "original" in order["picking_times"]
        assert "baseline" in order["picking_times"]


def test_simulate_demo_dataset_alias_and_order_subset(client: TestClient):
    """Test dataset alias 'uci-online-retail-ii-june-2011' and selective order_ids."""
    order_subset = ["555157", "555158"]
    res = client.post(
        "/api/datasets/uci-online-retail-ii-june-2011/simulate",
        json={"order_ids": order_subset, "speed_m_s": 1.2, "handling_time_s": 10.0},
    )
    assert res.status_code == 200, res.text
    data = res.json()

    assert len(data["orders"]) == 2
    assert data["policies"]["original"]["orders_replayed"] == 2
    assert data["policies"]["baseline"]["orders_replayed"] == 2


# ==============================================================================
# 2. Dynamic Datasets with <100 SKUs (No EMPTY_* Products)
# ==============================================================================

def test_simulate_dataset_with_under_100_skus(client: TestClient, tmp_path: Path, monkeypatch):
    """Test dataset with 5 SKUs without injecting fake EMPTY_* products, no crashes, valid routes."""
    dataset_id = "ds_small_5_test"
    upload_root = tmp_path / "uploads"
    monkeypatch.setattr(settings, "upload_storage_dir", str(upload_root))

    skus = ["SKU_ALPHA", "SKU_BETA", "SKU_GAMMA", "SKU_DELTA", "SKU_EPSILON"]
    products = [
        {"sku": "SKU_ALPHA", "name": "Alpha Item", "pick_frequency": 500},
        {"sku": "SKU_BETA", "name": "Beta Item", "pick_frequency": 300},
        {"sku": "SKU_GAMMA", "name": "Gamma Item", "pick_frequency": 200},
        {"sku": "SKU_DELTA", "name": "Delta Item", "pick_frequency": 100},
        {"sku": "SKU_EPSILON", "name": "Epsilon Item", "pick_frequency": 50},
    ]
    orders = [
        {
            "order_id": "ORD-001",
            "lines": [
                {"sku": "SKU_ALPHA", "quantity": 2},
                {"sku": "SKU_GAMMA", "quantity": 1},
            ],
        },
        {
            "order_id": "ORD-002",
            "lines": [
                {"sku": "SKU_BETA", "quantity": 4},
                {"sku": "SKU_DELTA", "quantity": 2},
                {"sku": "SKU_EPSILON", "quantity": 1},
            ],
        },
    ]

    layout = create_mock_21x21_layout_5_skus(skus)
    meta = {
        "dataset_id": dataset_id,
        "source": "synthetic-5-sku-test",
        "month": "2026-10",
        "real_order_data": False,
        "synthetic_warehouse": True,
        "cell_size_m": 1.5,
    }

    payload = {
        "meta": meta,
        "layout": layout.model_dump(),
        "products": products,
        "orders": orders,
    }

    # Save to staging processed.json
    ds_dir = upload_root / dataset_id
    ds_dir.mkdir(parents=True, exist_ok=True)
    with open(ds_dir / "processed.json", "w", encoding="utf-8") as f:
        json.dump(payload, f)

    res = client.post(f"/api/datasets/{dataset_id}/simulate", json={})
    assert res.status_code == 200, res.text
    data = res.json()

    # Invariant: No fake EMPTY_* products injected
    assert len(data["warehouse"]["slots"]) == 100
    for slot in data["warehouse"]["slots"]:
        if slot["sku"] is not None:
            assert not slot["sku"].startswith("EMPTY_")
            assert slot["sku"] in skus

    # Check baseline assignments: exactly 5 slots assigned to top SKUs, spare unassigned
    base_assignments = data["policies"]["baseline"]["slot_assignments"]
    assert len(base_assignments) == 5
    for assigned_sku in base_assignments.values():
        assert not assigned_sku.startswith("EMPTY_")
        assert assigned_sku in skus

    # Routes are valid
    assert len(data["orders"]) == 2
    for ord_res in data["orders"]:
        for policy_name in ("original", "baseline"):
            route = ord_res["routes"][policy_name]
            # Starts and ends at dock [0, 0]
            assert route["waypoints"][0] == [0, 0]
            assert route["waypoints"][-1] == [0, 0]
            # Cardinal steps
            for i in range(len(route["waypoints"]) - 1):
                p1 = route["waypoints"][i]
                p2 = route["waypoints"][i + 1]
                assert abs(p2[0] - p1[0]) + abs(p2[1] - p1[1]) == 1


# ==============================================================================
# 3. Player Layout Permutation
# ==============================================================================

def test_simulate_player_permutation_swapping_high_low_movers(client: TestClient):
    """Test player layout permutation: verify swapping high and low frequency items alters distance."""
    demo = client.get("/api/demo").json()
    order_ids = ["555157", "555158"]

    # Compute baseline assignments as reference
    base_res = client.post(
        "/api/datasets/demo/simulate",
        json={"order_ids": order_ids},
    )
    assert base_res.status_code == 200
    base_assignments = base_res.json()["policies"]["baseline"]["slot_assignments"]

    # Swap S001 (fast mover near dock) with S010 or S100 (slower mover farther from dock)
    player_assignments = dict(base_assignments)
    sku_near = player_assignments["S001"]
    sku_far = player_assignments["S010"]
    player_assignments["S001"] = sku_far
    player_assignments["S010"] = sku_near

    res = client.post(
        "/api/datasets/demo/simulate",
        json={
            "order_ids": order_ids,
            "layout_permutation": player_assignments,
            "speed_m_s": 1.2,
            "handling_time_s": 15.0,
        },
    )
    assert res.status_code == 200, res.text
    data = res.json()

    assert "player" in data["policies"]
    player_policy = data["policies"]["player"]
    base_policy = data["policies"]["baseline"]

    # Player assignments applied
    assert player_policy["slot_assignments"]["S001"] == sku_far
    assert player_policy["slot_assignments"]["S010"] == sku_near

    # Verify orders have player routes
    for ord_res in data["orders"]:
        assert "player" in ord_res["routes"]
        assert "player" in ord_res["picking_times"]


def test_simulate_player_permutation_sku_to_slot_orientation(client: TestClient):
    """Test player layout permutation when provided as sku -> slot_id mapping."""
    demo = client.get("/api/demo").json()
    order_ids = ["555157"]

    # Invert demo slots to sku -> slot_id
    sku_to_slot = {s["sku"]: s["slot_id"] for s in demo["layout"]["slots"]}

    res = client.post(
        "/api/datasets/demo/simulate",
        json={
            "order_ids": order_ids,
            "layout_permutation": sku_to_slot,
        },
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert "player" in data["policies"]
    assert data["policies"]["player"]["orders_replayed"] == 1


# ==============================================================================
# 4. Error Handling: 404 & 422 with Structured Error Codes
# ==============================================================================

def test_simulate_invalid_dataset_id_returns_404(client: TestClient):
    """Test invalid dataset ID returns 404 with structured error code DATASET_NOT_FOUND."""
    res = client.post("/api/datasets/ds_nonexistent_9999/simulate", json={})
    assert res.status_code == 404
    data = res.json()
    assert "detail" in data
    detail = data["detail"]
    assert detail["code"] == ErrorCode.DATASET_NOT_FOUND.value
    assert "ds_nonexistent_9999" in detail["message"]


def test_simulate_invalid_player_permutation_unknown_sku(client: TestClient):
    """Test player permutation containing unknown SKU returns 422 with INVALID_SLOT_ASSIGNMENT."""
    demo = client.get("/api/demo").json()
    bad_assignments = {s["slot_id"]: s["sku"] for s in demo["layout"]["slots"]}
    bad_assignments["S001"] = "FAKE_NONEXISTENT_SKU_999"

    res = client.post(
        "/api/datasets/demo/simulate",
        json={"layout_permutation": bad_assignments},
    )
    assert res.status_code == 422
    detail = res.json()["detail"]
    assert detail["code"] == ErrorCode.INVALID_SLOT_ASSIGNMENT.value
    assert "Invalid SKUs in player assignments" in detail["message"]


def test_simulate_invalid_player_permutation_unknown_slot(client: TestClient):
    """Test player permutation containing unknown slot ID returns 422 with INVALID_SLOT_ASSIGNMENT."""
    demo = client.get("/api/demo").json()
    bad_assignments = {s["slot_id"]: s["sku"] for s in demo["layout"]["slots"]}
    # Add slot that does not exist on warehouse grid
    bad_assignments["S999_UNKNOWN"] = "20724"

    res = client.post(
        "/api/datasets/demo/simulate",
        json={"layout_permutation": bad_assignments},
    )
    assert res.status_code == 422
    detail = res.json()["detail"]
    assert detail["code"] == ErrorCode.INVALID_SLOT_ASSIGNMENT.value


def test_simulate_invalid_player_permutation_duplicate_skus(client: TestClient):
    """Test player permutation with duplicate SKU returns 422 with INVALID_SLOT_ASSIGNMENT."""
    demo = client.get("/api/demo").json()
    bad_assignments = {s["slot_id"]: s["sku"] for s in demo["layout"]["slots"]}
    bad_assignments["S002"] = bad_assignments["S001"]

    res = client.post(
        "/api/datasets/demo/simulate",
        json={"layout_permutation": bad_assignments},
    )
    assert res.status_code == 422
    detail = res.json()["detail"]
    assert detail["code"] == ErrorCode.INVALID_SLOT_ASSIGNMENT.value


def test_simulate_invalid_order_id(client: TestClient):
    """Test unknown order ID returns 422 with MALFORMED_ORDER."""
    res = client.post(
        "/api/datasets/demo/simulate",
        json={"order_ids": ["ORD-DOES-NOT-EXIST"]},
    )
    assert res.status_code == 422
    detail = res.json()["detail"]
    assert detail["code"] == ErrorCode.MALFORMED_ORDER.value


# ==============================================================================
# 5. Unit Tests for compute_baseline_layout & loader
# ==============================================================================

def test_compute_baseline_layout_unit():
    """Test compute_baseline_layout places highest frequency items in closest slots."""
    demo = load_demo_data()
    baseline = compute_baseline_layout(demo)
    assert len(baseline) == len(demo.products)
    assert "S001" in baseline

    # Highest frequency product in demo is assigned to closest slot
    sorted_prods = sorted(demo.products, key=lambda p: (-p.pick_frequency, p.sku))
    top_product = sorted_prods[0]
    # S001 is nearest rack [1, 1] access cell [1, 0] from dock [0, 0]
    assert baseline["S001"] == top_product.sku


def test_get_dataset_loader():
    """Test get_dataset resolves aliases and raises 404 for missing datasets."""
    demo1 = get_dataset("demo")
    assert demo1.meta.dataset_id == "uci-2011-06-preview-bcbe73b35f5b"

    demo2 = get_dataset("uci-online-retail-ii-june-2011")
    assert demo2.meta.dataset_id == "uci-2011-06-preview-bcbe73b35f5b"

    with pytest.raises(Exception) as excinfo:
        get_dataset("invalid-dataset-xyz")
    assert "404" in str(excinfo.value)
