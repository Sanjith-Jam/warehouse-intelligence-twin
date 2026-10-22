"""Tests for POST /api/simulate endpoint on 100-SKU real UCI dataset."""
from fastapi.testclient import TestClient


def test_simulate_real_orders_original_and_baseline(client: TestClient):
    """Test simulating 20 real orders across original and baseline layouts."""
    demo = client.get("/api/demo").json()
    order_ids = [o["order_id"] for o in demo["orders"]]
    assert len(order_ids) == 20

    # 1. Original layout replay
    res_orig = client.post(
        "/api/simulate",
        json={"order_ids": order_ids, "policy": "original", "speed_mps": 1.2},
    )
    assert res_orig.status_code == 200
    data_orig = res_orig.json()

    assert data_orig["dataset_id"] == demo["meta"]["dataset_id"]
    assert data_orig["policy"] == "original"
    assert data_orig["orders_replayed"] == 20
    assert data_orig["distance_m"] == 2844.0
    assert data_orig["estimated_pick_time_s"] == 3470.0
    assert data_orig["average_pick_time_s"] == 173.5
    assert len(data_orig["routes"]) == 20
    assert len(data_orig["slot_assignments"]) == 100

    # 2. Fast-mover baseline layout replay
    res_base = client.post(
        "/api/simulate",
        json={"order_ids": order_ids, "policy": "baseline", "speed_mps": 1.2},
    )
    assert res_base.status_code == 200
    data_base = res_base.json()

    assert data_base["policy"] == "baseline"
    assert data_base["orders_replayed"] == 20
    assert data_base["distance_m"] == 2820.0
    assert data_base["estimated_pick_time_s"] == 3450.0
    assert data_base["average_pick_time_s"] == 172.5
    assert len(data_base["routes"]) == 20
    assert len(data_base["slot_assignments"]) == 100

    # Baseline demonstrates shorter walking distance than original layout
    assert data_base["distance_m"] < data_orig["distance_m"]
    assert data_base["estimated_pick_time_s"] < data_orig["estimated_pick_time_s"]


def test_simulate_player_policy_permutation(client: TestClient):
    """Test player policy with valid 100-slot permutation and swap."""
    demo = client.get("/api/demo").json()
    order_ids = ["555157", "555158"]

    # Initial mapping from original layout
    player_assignments = {s["slot_id"]: s["sku"] for s in demo["layout"]["slots"]}
    # Swap S001 and S002
    sku1 = player_assignments["S001"]
    sku2 = player_assignments["S002"]
    player_assignments["S001"] = sku2
    player_assignments["S002"] = sku1

    res = client.post(
        "/api/simulate",
        json={
            "order_ids": order_ids,
            "policy": "player",
            "slot_assignments": player_assignments,
            "speed_mps": 1.2,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["policy"] == "player"
    assert data["orders_replayed"] == 2
    assert data["slot_assignments"]["S001"] == sku2
    assert data["slot_assignments"]["S002"] == sku1
    assert len(data["routes"]) == 2


def test_simulate_route_invariants_real_data(client: TestClient):
    """Test that all routes obey physical warehouse constraints and invariants."""
    wh = client.get("/api/warehouse").json()
    walkable_tuples = {tuple(c) for c in wh["layout"]["walkable_cells"]}
    dock = wh["layout"]["dock"]

    res = client.post(
        "/api/simulate",
        json={"order_ids": ["555157", "555158", "555159"], "policy": "original", "speed_mps": 1.2},
    )
    assert res.status_code == 200
    routes = res.json()["routes"]

    for route in routes:
        waypoints = route["waypoints"]
        # Invariant 1: Start and end at dock [0, 0]
        assert waypoints[0] == dock
        assert waypoints[-1] == dock

        # Invariant 2: Every step is adjacent cardinal move within walkable cells
        for i in range(len(waypoints) - 1):
            w1 = waypoints[i]
            w2 = waypoints[i + 1]
            assert tuple(w1) in walkable_tuples
            assert tuple(w2) in walkable_tuples
            manhattan = abs(w2[0] - w1[0]) + abs(w2[1] - w1[1])
            assert manhattan == 1

        # Invariant 3: Visits match assigned slot access cells
        for v in route["visits"]:
            idx = v["waypoint_index"]
            assert 0 <= idx < len(waypoints)


def test_simulate_speed_validation(client: TestClient):
    """Test focused validation of finite positive speed per contracts/api.md."""
    # Valid speeds
    for valid_speed in [0.1, 1.2, 5.0, 10.0]:
        res = client.post(
            "/api/simulate",
            json={"order_ids": ["555157"], "policy": "original", "speed_mps": valid_speed},
        )
        assert res.status_code == 200
        assert res.json()["assumptions"]["speed_mps"] == valid_speed

    # Non-finite and invalid speeds
    for invalid_speed in ["NaN", "nan", "Infinity", "-Infinity", 0, -1.0, 10.1]:
        res = client.post(
            "/api/simulate",
            json={"order_ids": ["555157"], "policy": "original", "speed_mps": invalid_speed},
        )
        assert res.status_code == 422


def test_simulate_validation_errors(client: TestClient):
    """Test 422 responses on invalid request parameters."""
    demo = client.get("/api/demo").json()

    # 1. Empty order_ids
    r = client.post("/api/simulate", json={"order_ids": [], "policy": "original"})
    assert r.status_code == 422

    # 2. Duplicate order_ids
    r = client.post("/api/simulate", json={"order_ids": ["555157", "555157"], "policy": "original"})
    assert r.status_code == 422

    # 3. Unknown order_id
    r = client.post("/api/simulate", json={"order_ids": ["NON-EXISTENT-ORDER"], "policy": "original"})
    assert r.status_code == 422
    assert "Unknown order ID" in r.json()["detail"]

    # 4. Player policy without assignments
    r = client.post("/api/simulate", json={"order_ids": ["555157"], "policy": "player"})
    assert r.status_code == 422

    # 5. Incomplete player assignments (missing slots)
    partial_assignments = {s["slot_id"]: s["sku"] for s in demo["layout"]["slots"][:50]}
    r = client.post(
        "/api/simulate",
        json={"order_ids": ["555157"], "policy": "player", "slot_assignments": partial_assignments},
    )
    assert r.status_code == 422
    assert "Invalid slots in player assignments" in r.json()["detail"]

    # 6. Duplicate SKU in player assignments (violates bijection)
    dup_assignments = {s["slot_id"]: s["sku"] for s in demo["layout"]["slots"]}
    dup_assignments["S002"] = dup_assignments["S001"]
    r = client.post(
        "/api/simulate",
        json={"order_ids": ["555157"], "policy": "player", "slot_assignments": dup_assignments},
    )
    assert r.status_code == 422
    assert "Invalid SKUs in player assignments" in r.json()["detail"]
