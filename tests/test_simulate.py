"""Tests for POST /api/simulate endpoint."""
from fastapi.testclient import TestClient


def test_simulate_player_exact_contract(client: TestClient):
    """Test POST /api/simulate player policy matches contracts/api.md sample response exactly."""
    payload = {
        "order_ids": ["DEMO-ORDER-1"],
        "slot_assignments": {"S001": "DEMO-001"},
        "policy": "player",
        "speed_mps": 1.2,
    }
    response = client.post("/api/simulate", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["dataset_id"] == "sample-v1"
    assert data["policy"] == "player"
    assert data["slot_assignments"] == {"S001": "DEMO-001"}
    assert data["orders_replayed"] == 1
    assert data["distance_m"] == 3.0
    assert data["estimated_pick_time_s"] == 12.5
    assert data["average_pick_time_s"] == 12.5
    assert data["warnings"] == []
    assert data["assumptions"] == {"speed_mps": 1.2, "handling_seconds_per_line": 10.0}

    assert len(data["routes"]) == 1
    route = data["routes"][0]
    assert route["order_id"] == "DEMO-ORDER-1"
    assert route["waypoints"] == [[0, 0], [1, 0], [0, 0]]
    assert route["visits"] == [{"sku": "DEMO-001", "slot_id": "S001", "waypoint_index": 1}]


def test_simulate_policies_original_and_baseline(client: TestClient):
    """Test POST /api/simulate works for original and baseline policies."""
    for policy in ["original", "baseline"]:
        payload = {
            "order_ids": ["DEMO-ORDER-1"],
            "policy": policy,
            "speed_mps": 1.2,
        }
        response = client.post("/api/simulate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["policy"] == policy
        assert data["orders_replayed"] == 1
        assert data["distance_m"] == 3.0
        assert data["slot_assignments"] == {"S001": "DEMO-001"}


def test_simulate_route_invariants(client: TestClient):
    """Test route starts and ends at dock, steps are cardinal and walkable."""
    # Get warehouse layout for walkable cells and dock
    wh = client.get("/api/warehouse").json()
    walkable_tuples = {tuple(c) for c in wh["layout"]["walkable_cells"]}
    dock = wh["layout"]["dock"]

    payload = {
        "order_ids": ["DEMO-ORDER-1"],
        "policy": "original",
        "speed_mps": 1.2,
    }
    response = client.post("/api/simulate", json=payload)
    assert response.status_code == 200
    route = response.json()["routes"][0]
    waypoints = route["waypoints"]

    # Invariant 1: Start and end at dock
    assert waypoints[0] == dock
    assert waypoints[-1] == dock

    # Invariant 2: Every step is adjacent cardinal move in walkable cells
    for i in range(len(waypoints) - 1):
        w1 = waypoints[i]
        w2 = waypoints[i + 1]
        assert tuple(w1) in walkable_tuples
        assert tuple(w2) in walkable_tuples
        manhattan_dist = abs(w2[0] - w1[0]) + abs(w2[1] - w1[1])
        assert manhattan_dist == 1

    # Invariant 3: Visits point to valid access cells
    visits = route["visits"]
    for v in visits:
        idx = v["waypoint_index"]
        assert 0 <= idx < len(waypoints)
        assert waypoints[idx] == [1, 0]


def test_simulate_validation_errors(client: TestClient):
    """Test 422 responses on invalid request parameters."""
    # 1. Empty order_ids
    r = client.post("/api/simulate", json={"order_ids": [], "policy": "original"})
    assert r.status_code == 422

    # 2. Duplicate order_ids
    r = client.post("/api/simulate", json={"order_ids": ["DEMO-ORDER-1", "DEMO-ORDER-1"], "policy": "original"})
    assert r.status_code == 422

    # 3. Unknown order_id
    r = client.post("/api/simulate", json={"order_ids": ["NON-EXISTENT-ORDER"], "policy": "original"})
    assert r.status_code == 422
    assert "Unknown order ID" in r.json()["detail"]

    # 4. Invalid speed (<= 0)
    r = client.post("/api/simulate", json={"order_ids": ["DEMO-ORDER-1"], "speed_mps": 0})
    assert r.status_code == 422

    # 5. Invalid speed (> 10)
    r = client.post("/api/simulate", json={"order_ids": ["DEMO-ORDER-1"], "speed_mps": 15.0})
    assert r.status_code == 422

    # 6. Player policy without assignments
    r = client.post("/api/simulate", json={"order_ids": ["DEMO-ORDER-1"], "policy": "player"})
    assert r.status_code == 422

    # 7. Player policy with incomplete / invalid slots
    r = client.post(
        "/api/simulate",
        json={
            "order_ids": ["DEMO-ORDER-1"],
            "policy": "player",
            "slot_assignments": {"UNKNOWN_SLOT": "DEMO-001"},
        },
    )
    assert r.status_code == 422

    # 8. Player policy with unknown SKU
    r = client.post(
        "/api/simulate",
        json={
            "order_ids": ["DEMO-ORDER-1"],
            "policy": "player",
            "slot_assignments": {"S001": "UNKNOWN-SKU"},
        },
    )
    assert r.status_code == 422
