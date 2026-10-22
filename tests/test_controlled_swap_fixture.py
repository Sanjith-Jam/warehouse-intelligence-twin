"""Comprehensive deterministic API & fixture tests for controlled geometry and order placement (FLASH-08).

Verifies controlled warehouse geometry where a bad placement and subsequent swap
produce predictably different walking distances, baseline policy matches or beats player,
and all policies evaluate an identical frozen order list with exact mathematical calculations.
"""
import json
import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.app.config import settings
from backend.app.main import app
from backend.app.models.schemas import (
    CleaningReport,
    DatasetMeta,
    DemoResponse,
    Order,
    OrderLine,
    Product,
    Slot,
    WarehouseLayout,
)
from backend.app.simulation.router import (
    calculate_dock_distances,
    compute_baseline_assignments,
    simulate_dataset_policies,
    simulate_orders,
)


# ==============================================================================
# Helper Builders & Fixtures
# ==============================================================================

def create_orthogonal_walkable_cells(width: int = 21, height: int = 21) -> list[list[int]]:
    """Generate orthogonal grid aisles where either x or z is even."""
    return [[x, z] for z in range(height) for x in range(width) if x % 2 == 0 or z % 2 == 0]


def build_focused_2_slot_layout(dock: list[int] = None) -> WarehouseLayout:
    """
    Construct a focused 21x21 warehouse layout with exactly two slots:
    - S001: near slot (rack [1, 1], access cell [1, 0])
    - S050: far slot (rack [19, 9], access cell [19, 8])
    """
    resolved_dock = dock or [0, 0]
    walkable = create_orthogonal_walkable_cells(21, 21)

    slots = [
        Slot(slot_id="S001", rack_cell=[1, 1], access_cell=[1, 0], sku="SKU-COLD"),
        Slot(slot_id="S050", rack_cell=[19, 9], access_cell=[19, 8], sku="SKU-HOT"),
    ]

    return WarehouseLayout(
        layout_id="focused_2_slots",
        width=21,
        height=21,
        walkable_cells=walkable,
        dock=resolved_dock,
        slots=slots,
    )


def build_standard_21x21_100_slot_layout(
    dock: list[int] = None,
    s001_sku: str = "SKU-COLD",
    s050_sku: str = "SKU-HOT",
) -> WarehouseLayout:
    """
    Construct full 21x21 grid with 100 rack slots on odd coordinates.
    Only S001 and S050 have assigned SKUs by default.
    """
    resolved_dock = dock or [0, 0]
    walkable = create_orthogonal_walkable_cells(21, 21)

    slots: list[Slot] = []
    slot_idx = 1
    for z in [1, 3, 5, 7, 9, 11, 13, 15, 17, 19]:
        for x in [1, 3, 5, 7, 9, 11, 13, 15, 17, 19]:
            sid = f"S{slot_idx:03d}"
            sku = None
            if sid == "S001":
                sku = s001_sku
            elif sid == "S050":
                sku = s050_sku
            slots.append(
                Slot(
                    slot_id=sid,
                    rack_cell=[x, z],
                    access_cell=[x, z - 1],
                    sku=sku,
                )
            )
            slot_idx += 1

    return WarehouseLayout(
        layout_id="standard_100_slots",
        width=21,
        height=21,
        walkable_cells=walkable,
        dock=resolved_dock,
        slots=slots,
    )


def build_controlled_products() -> list[Product]:
    """Define two SKUs with stark velocity disparity: 50 picks vs 1 pick."""
    return [
        Product(sku="SKU-HOT", name="Hot Velocity Item", pick_frequency=50),
        Product(sku="SKU-COLD", name="Cold Slow Mover", pick_frequency=1),
    ]


def build_controlled_orders() -> list[Order]:
    """
    Generate 51 orders:
    - 50 single-line orders picking SKU-HOT
    - 1 single-line order picking SKU-COLD
    """
    orders = [
        Order(order_id=f"ORD-HOT-{i:02d}", lines=[OrderLine(sku="SKU-HOT", quantity=1)])
        for i in range(1, 51)
    ]
    orders.append(
        Order(order_id="ORD-COLD-01", lines=[OrderLine(sku="SKU-COLD", quantity=1)])
    )
    return orders


# ==============================================================================
# 1. Focused 2-Slot Layout: Exact Analytical Distance & Time Verification
# ==============================================================================

def test_controlled_swap_focused_2_slot_layout():
    """
    Verify focused 2-slot geometry with dock at [0, 0]:
    - S001 access cell [1, 0] is 1 step from dock (round-trip = 2 steps = 3.0m).
    - S050 access cell [19, 8] is 27 steps from dock (round-trip = 54 steps = 81.0m).
    - Bad initial layout: SKU-HOT in S050 (far), SKU-COLD in S001 (near).
      Original Distance = 50 * 81.0m + 1 * 3.0m = 4,053.0m.
    - Player swap: SKU-HOT in S001 (near), SKU-COLD in S050 (far).
      Player Distance = 50 * 3.0m + 1 * 81.0m = 231.0m.
    - Baseline policy: assigns highest frequency SKU-HOT to S001, SKU-COLD to S050.
      Baseline Distance = 231.0m == Player Distance.
    """
    layout = build_focused_2_slot_layout(dock=[0, 0])
    products = build_controlled_products()
    orders = build_controlled_orders()

    speed_mps = 1.2
    cell_size_m = 1.5
    handling_time_s = 10.0

    # 1. Simulate Original (Bad Layout)
    sim_orig = simulate_orders(
        dataset_id="controlled_test",
        orders=orders,
        layout=layout,
        products=products,
        policy="original",
        slot_assignments=None,
        speed_mps=speed_mps,
        cell_size_m=cell_size_m,
        handling_seconds_per_line=handling_time_s,
    )

    # Theoretical values
    expected_orig_dist = 50 * (54 * 1.5) + 1 * (2 * 1.5)  # 4050.0 + 3.0 = 4053.0
    expected_travel_time_orig = expected_orig_dist / speed_mps  # 4053.0 / 1.2 = 3377.5
    expected_handling_time = 51 * handling_time_s  # 510.0
    expected_total_time_orig = expected_travel_time_orig + expected_handling_time  # 3887.5

    assert sim_orig.distance_m == expected_orig_dist == 4053.0
    assert pytest.approx(sim_orig.estimated_pick_time_s, rel=1e-5) == expected_total_time_orig == 3887.5
    assert pytest.approx(sim_orig.average_pick_time_s, rel=1e-5) == expected_total_time_orig / 51

    # 2. Simulate Player Layout (Swapped)
    player_perm = {"S001": "SKU-HOT", "S050": "SKU-COLD"}
    sim_player = simulate_orders(
        dataset_id="controlled_test",
        orders=orders,
        layout=layout,
        products=products,
        policy="player",
        slot_assignments=player_perm,
        speed_mps=speed_mps,
        cell_size_m=cell_size_m,
        handling_seconds_per_line=handling_time_s,
    )

    expected_player_dist = 50 * (2 * 1.5) + 1 * (54 * 1.5)  # 150.0 + 81.0 = 231.0
    expected_travel_time_player = expected_player_dist / speed_mps  # 231.0 / 1.2 = 192.5
    expected_total_time_player = expected_travel_time_player + expected_handling_time  # 702.5

    assert sim_player.distance_m == expected_player_dist == 231.0
    assert pytest.approx(sim_player.estimated_pick_time_s, rel=1e-5) == expected_total_time_player == 702.5
    assert pytest.approx(sim_player.average_pick_time_s, rel=1e-5) == expected_total_time_player / 51

    # Invariant: Player distance strictly lower than original
    assert sim_player.distance_m < sim_orig.distance_m
    assert sim_orig.distance_m - sim_player.distance_m == 3822.0  # Exactly 3,822m walking saved!

    # 3. Simulate Baseline Policy
    sim_base = simulate_orders(
        dataset_id="controlled_test",
        orders=orders,
        layout=layout,
        products=products,
        policy="baseline",
        slot_assignments=None,
        speed_mps=speed_mps,
        cell_size_m=cell_size_m,
        handling_seconds_per_line=handling_time_s,
    )

    # In this 2-slot setup, player swap found the optimal configuration, so baseline matches player
    assert sim_base.slot_assignments == {"S001": "SKU-HOT", "S050": "SKU-COLD"}
    assert sim_base.distance_m == sim_player.distance_m == 231.0
    assert sim_base.estimated_pick_time_s == sim_player.estimated_pick_time_s == 702.5


# ==============================================================================
# 2. Standard 21x21 Grid (100 Slots): Baseline Outperforms Player
# ==============================================================================

def test_controlled_swap_standard_100_slot_baseline_beats_player():
    """
    Verify full 21x21 warehouse with 100 slots:
    - Bad initial layout: S001 has SKU-COLD, S050 has SKU-HOT.
    - Player swap: swaps S001 and S050 (SKU-HOT in S001, SKU-COLD in S050).
      Distance = 231.0m.
    - Baseline policy:
      Finds closest slot to dock: S001 (distance 1 step). Assigns SKU-HOT.
      Finds second closest slot to dock: S002 (distance 3 steps). Assigns SKU-COLD.
      Baseline Distance = 50 * (2 * 1.5) + 1 * (6 * 1.5) = 150.0 + 9.0 = 159.0m.
    - Baseline beats player layout: 159.0m < 231.0m < 4,053.0m.
    """
    layout = build_standard_21x21_100_slot_layout(dock=[0, 0])
    products = build_controlled_products()
    orders = build_controlled_orders()

    speed_mps = 1.2
    cell_size_m = 1.5
    handling_time_s = 10.0

    # 1. Original
    sim_orig = simulate_orders(
        dataset_id="controlled_test_100",
        orders=orders,
        layout=layout,
        products=products,
        policy="original",
        slot_assignments=None,
        speed_mps=speed_mps,
        cell_size_m=cell_size_m,
        handling_seconds_per_line=handling_time_s,
    )
    assert sim_orig.distance_m == 4053.0

    # 2. Player swap between S001 and S050
    player_perm = {"S001": "SKU-HOT", "S050": "SKU-COLD"}
    sim_player = simulate_orders(
        dataset_id="controlled_test_100",
        orders=orders,
        layout=layout,
        products=products,
        policy="player",
        slot_assignments=player_perm,
        speed_mps=speed_mps,
        cell_size_m=cell_size_m,
        handling_seconds_per_line=handling_time_s,
    )
    assert sim_player.distance_m == 231.0
    assert sim_player.distance_m < sim_orig.distance_m

    # 3. Baseline policy
    sim_base = simulate_orders(
        dataset_id="controlled_test_100",
        orders=orders,
        layout=layout,
        products=products,
        policy="baseline",
        slot_assignments=None,
        speed_mps=speed_mps,
        cell_size_m=cell_size_m,
        handling_seconds_per_line=handling_time_s,
    )

    # Baseline slots SKU-HOT into S001 (1 step), and SKU-COLD into S002 (3 steps)
    assert sim_base.slot_assignments == {"S001": "SKU-HOT", "S002": "SKU-COLD"}
    expected_base_dist = 50 * (2 * 1.5) + 1 * (6 * 1.5)  # 150.0 + 9.0 = 159.0
    assert sim_base.distance_m == expected_base_dist == 159.0

    # Strict ordering: Baseline < Player < Original
    assert sim_base.distance_m < sim_player.distance_m < sim_orig.distance_m
    assert sim_base.estimated_pick_time_s < sim_player.estimated_pick_time_s < sim_orig.estimated_pick_time_s


# ==============================================================================
# 3. Center Dock [10, 0] Warehouse Layout
# ==============================================================================

def test_controlled_swap_center_dock_layout():
    """
    Verify behavior when dock is at center [10, 0]:
    - S001 access cell [1, 0]: 9 steps from [10, 0] (round-trip = 18 steps = 27.0m).
    - S050 access cell [19, 8]: |19-10| + |8-0| = 17 steps (round-trip = 34 steps = 51.0m).
    - Bad initial layout (HOT in S050, COLD in S001):
      Distance = 50 * 51.0m + 1 * 27.0m = 2,550.0 + 27.0 = 2,577.0m.
    - Player swap (HOT in S001, COLD in S050):
      Distance = 50 * 27.0m + 1 * 51.0m = 1,350.0 + 51.0 = 1,401.0m.
    - Player distance strictly lower than original.
    - Baseline places SKU-HOT in slot closest to [10, 0] (e.g. rack [9, 1] access [9, 0], 1 step).
    """
    center_dock = [10, 0]
    layout = build_focused_2_slot_layout(dock=center_dock)
    products = build_controlled_products()
    orders = build_controlled_orders()

    speed_mps = 1.2
    cell_size_m = 1.5
    handling_time_s = 10.0

    # 1. Original simulation
    sim_orig = simulate_orders(
        dataset_id="test_center_dock",
        orders=orders,
        layout=layout,
        products=products,
        policy="original",
        slot_assignments=None,
        speed_mps=speed_mps,
        cell_size_m=cell_size_m,
        handling_seconds_per_line=handling_time_s,
    )
    expected_orig_dist = 50 * (34 * 1.5) + 1 * (18 * 1.5)  # 2550.0 + 27.0 = 2577.0
    assert sim_orig.distance_m == expected_orig_dist == 2577.0

    # 2. Player swap
    player_perm = {"S001": "SKU-HOT", "S050": "SKU-COLD"}
    sim_player = simulate_orders(
        dataset_id="test_center_dock",
        orders=orders,
        layout=layout,
        products=products,
        policy="player",
        slot_assignments=player_perm,
        speed_mps=speed_mps,
        cell_size_m=cell_size_m,
        handling_seconds_per_line=handling_time_s,
    )
    expected_player_dist = 50 * (18 * 1.5) + 1 * (34 * 1.5)  # 1350.0 + 51.0 = 1401.0
    assert sim_player.distance_m == expected_player_dist == 1401.0
    assert sim_player.distance_m < sim_orig.distance_m

    # 3. Baseline simulation matches player on 2-slot layout
    sim_base = simulate_orders(
        dataset_id="test_center_dock",
        orders=orders,
        layout=layout,
        products=products,
        policy="baseline",
        slot_assignments=None,
        speed_mps=speed_mps,
        cell_size_m=cell_size_m,
        handling_seconds_per_line=handling_time_s,
    )
    assert sim_base.distance_m == sim_player.distance_m == 1401.0


# ==============================================================================
# 4. Multi-SKU Velocity Ranking (3 SKUs: HOT, WARM, COLD)
# ==============================================================================

def test_controlled_swap_3_skus_velocity_slotting():
    """
    Test 3 SKUs with distinct pick velocities:
    - SKU-HOT: 100 picks
    - SKU-WARM: 20 picks
    - SKU-COLD: 1 pick
    Three slots at increasing distances from dock [0, 0]:
    - S001 (access [1, 0], 1 step = 1.5m)
    - S002 (access [3, 0], 3 steps = 4.5m)
    - S050 (access [19, 8], 27 steps = 40.5m)
    Initial bad layout: S001=COLD, S002=WARM, S050=HOT.
    Sub-optimal player layout: S001=HOT, S002=COLD, S050=WARM.
    Optimal baseline layout: S001=HOT, S002=WARM, S050=COLD.
    Verifies: Baseline < Player < Original.
    """
    walkable = create_orthogonal_walkable_cells(21, 21)
    slots = [
        Slot(slot_id="S001", rack_cell=[1, 1], access_cell=[1, 0], sku="SKU-COLD"),
        Slot(slot_id="S002", rack_cell=[3, 1], access_cell=[3, 0], sku="SKU-WARM"),
        Slot(slot_id="S050", rack_cell=[19, 9], access_cell=[19, 8], sku="SKU-HOT"),
    ]
    layout = WarehouseLayout(
        layout_id="3_slot_layout",
        width=21,
        height=21,
        walkable_cells=walkable,
        dock=[0, 0],
        slots=slots,
    )

    products = [
        Product(sku="SKU-HOT", name="Hot Product", pick_frequency=100),
        Product(sku="SKU-WARM", name="Warm Product", pick_frequency=20),
        Product(sku="SKU-COLD", name="Cold Product", pick_frequency=1),
    ]

    orders = []
    for i in range(100):
        orders.append(Order(order_id=f"ORD-HOT-{i:03d}", lines=[OrderLine(sku="SKU-HOT", quantity=1)]))
    for i in range(20):
        orders.append(Order(order_id=f"ORD-WARM-{i:03d}", lines=[OrderLine(sku="SKU-WARM", quantity=1)]))
    orders.append(Order(order_id="ORD-COLD-001", lines=[OrderLine(sku="SKU-COLD", quantity=1)]))

    # 1. Original (Bad)
    sim_orig = simulate_orders("3sku_test", orders, layout, products, "original", None, 1.2, 1.5, 10.0)
    # HOT at S050 (54 steps), WARM at S002 (6 steps), COLD at S001 (2 steps)
    expected_orig = 100 * (54 * 1.5) + 20 * (6 * 1.5) + 1 * (2 * 1.5)  # 8100 + 180 + 3 = 8283.0m
    assert sim_orig.distance_m == expected_orig == 8283.0

    # 2. Sub-optimal player swap (puts WARM in S050 and COLD in S002)
    suboptimal_player = {"S001": "SKU-HOT", "S002": "SKU-COLD", "S050": "SKU-WARM"}
    sim_player = simulate_orders("3sku_test", orders, layout, products, "player", suboptimal_player, 1.2, 1.5, 10.0)
    # HOT at S001 (2 steps), COLD at S002 (6 steps), WARM at S050 (54 steps)
    expected_player = 100 * (2 * 1.5) + 1 * (6 * 1.5) + 20 * (54 * 1.5)  # 300 + 9 + 1620 = 1929.0m
    assert sim_player.distance_m == expected_player == 1929.0
    assert sim_player.distance_m < sim_orig.distance_m

    # 3. Baseline policy: automatically sorts HOT->S001, WARM->S002, COLD->S050
    sim_base = simulate_orders("3sku_test", orders, layout, products, "baseline", None, 1.2, 1.5, 10.0)
    assert sim_base.slot_assignments == {"S001": "SKU-HOT", "S002": "SKU-WARM", "S050": "SKU-COLD"}
    expected_base = 100 * (2 * 1.5) + 20 * (6 * 1.5) + 1 * (54 * 1.5)  # 300 + 180 + 81 = 561.0m
    assert sim_base.distance_m == expected_base == 561.0

    # Baseline strictly beats sub-optimal player
    assert sim_base.distance_m < sim_player.distance_m < sim_orig.distance_m


# ==============================================================================
# 5. Frozen Order List & Route Invariants
# ==============================================================================

def test_controlled_swap_frozen_order_list_and_routes_invariants():
    """
    Verify that all 3 policies simulate the exact same frozen order list
    and obey physical warehouse constraints:
    - Exactly 51 orders replayed in each policy.
    - Waypoints start and end at the dock [0, 0].
    - Every movement step is a cardinal move (Manhattan distance == 1).
    - Every visit matches the assigned slot access cell.
    - Mathematical formula consistency:
      total_distance_m == total_steps * cell_size_m
      estimated_pick_time_s == (total_distance_m / speed_mps) + (lines * handling_seconds_per_line)
      average_pick_time_s == estimated_pick_time_s / orders_replayed
    """
    layout = build_focused_2_slot_layout(dock=[0, 0])
    products = build_controlled_products()
    orders = build_controlled_orders()

    meta = DatasetMeta(dataset_id="frozen_order_test", cell_size_m=1.5)
    dataset = DemoResponse(
        meta=meta,
        cleaning_report=CleaningReport(),
        layout=layout,
        products=products,
        orders=orders,
    )

    player_perm = {"S001": "SKU-HOT", "S050": "SKU-COLD"}
    speed_mps = 1.2
    handling_s = 10.0
    cell_size = 1.5

    sim_res = simulate_dataset_policies(
        dataset=dataset,
        layout_permutation=player_perm,
        speed_mps=speed_mps,
        handling_seconds_per_line=handling_s,
        cell_size_m=cell_size,
    )

    walkable_set = {(c[0], c[1]) for c in layout.walkable_cells}

    # Verify all 3 policies simulated
    assert set(sim_res.policies.keys()) == {"original", "baseline", "player"}

    # Verify order count and frozen order identities
    assert len(sim_res.orders) == 51
    for idx, ord_item in enumerate(sim_res.orders):
        assert ord_item.order_id == orders[idx].order_id
        assert len(ord_item.lines) == len(orders[idx].lines)

        for pol_name in ("original", "baseline", "player"):
            route = ord_item.routes[pol_name]
            waypoints = route.waypoints
            # Invariant: Start and end at dock
            assert waypoints[0] == [0, 0]
            assert waypoints[-1] == [0, 0]

            # Invariant: Cardinal moves only
            step_count = 0
            for i in range(len(waypoints) - 1):
                p1, p2 = waypoints[i], waypoints[i + 1]
                assert (p1[0], p1[1]) in walkable_set
                assert (p2[0], p2[1]) in walkable_set
                assert abs(p2[0] - p1[0]) + abs(p2[1] - p1[1]) == 1
                step_count += 1

            # Invariant: Distance and pick time formula per order
            expected_dist = float(step_count * cell_size)
            assert ord_item.distances_m[pol_name] == expected_dist
            expected_time = (expected_dist / speed_mps) + len(ord_item.lines) * handling_s
            assert pytest.approx(ord_item.picking_times[pol_name], rel=1e-5) == expected_time

            # Invariant: Visit waypoint matches assigned slot access cell
            for visit in route.visits:
                assigned_slot_id = visit.slot_id
                target_slot = next(s for s in layout.slots if s.slot_id == assigned_slot_id)
                visit_coord = waypoints[visit.waypoint_index]
                assert visit_coord == target_slot.access_cell

    # Verify overall policy aggregates match exact sums
    for pol_name, pol_data in sim_res.policies.items():
        assert pol_data.orders_replayed == 51
        sum_dist = sum(o.distances_m[pol_name] for o in sim_res.orders)
        sum_time = sum(o.picking_times[pol_name] for o in sim_res.orders)
        assert pytest.approx(pol_data.total_distance_m, rel=1e-5) == sum_dist
        assert pytest.approx(pol_data.total_pick_time_s, rel=1e-5) == sum_time
        assert pytest.approx(pol_data.average_pick_time_s, rel=1e-5) == sum_time / 51


# ==============================================================================
# 6. Permutation Orientation & Reversibility
# ==============================================================================

def test_controlled_swap_permutation_orientations_and_reversibility():
    """
    Test player permutation normalization and swap reversibility:
    1. slot_id -> sku orientation: {"S001": "SKU-HOT", "S050": "SKU-COLD"}
    2. sku -> slot_id orientation: {"SKU-HOT": "S001", "SKU-COLD": "S050"}
    Both orientations yield bitwise identical simulation results.
    3. Reversing the swap (putting SKU-HOT back to S050) reproduces original bad layout metrics.
    """
    layout = build_focused_2_slot_layout(dock=[0, 0])
    products = build_controlled_products()
    orders = build_controlled_orders()

    # Orientation 1: slot_id -> sku
    perm_slot_to_sku = {"S001": "SKU-HOT", "S050": "SKU-COLD"}
    sim1 = simulate_orders("orient_test", orders, layout, products, "player", perm_slot_to_sku, 1.2, 1.5, 10.0)

    # Orientation 2: sku -> slot_id
    perm_sku_to_slot = {"SKU-HOT": "S001", "SKU-COLD": "S050"}
    sim2 = simulate_orders("orient_test", orders, layout, products, "player", perm_sku_to_slot, 1.2, 1.5, 10.0)

    assert sim1.distance_m == sim2.distance_m == 231.0
    assert sim1.estimated_pick_time_s == sim2.estimated_pick_time_s == 702.5
    assert sim1.slot_assignments == sim2.slot_assignments == perm_slot_to_sku

    # Reversibility test: swapping back
    perm_reverse = {"S001": "SKU-COLD", "S050": "SKU-HOT"}
    sim_rev = simulate_orders("orient_test", orders, layout, products, "player", perm_reverse, 1.2, 1.5, 10.0)
    assert sim_rev.distance_m == 4053.0
    assert pytest.approx(sim_rev.estimated_pick_time_s, rel=1e-5) == 3887.5


# ==============================================================================
# 7. End-to-End API Integration via TestClient
# ==============================================================================

def test_controlled_swap_api_endpoint_integration(client: TestClient, tmp_path: Path, monkeypatch):
    """
    Test end-to-end HTTP integration via POST /api/datasets/{dataset_id}/simulate:
    - Stage controlled dataset snapshot into upload storage.
    - Invoke POST endpoint with player permutation.
    - Verify HTTP 200 response structure, policy comparisons, and distance invariants.
    """
    monkeypatch.setattr(settings, "upload_storage_dir", str(tmp_path / "uploads"))

    dataset_id = "ds_controlled_fixture_api_test"
    ds_dir = tmp_path / "uploads" / dataset_id
    ds_dir.mkdir(parents=True, exist_ok=True)

    layout = build_standard_21x21_100_slot_layout(dock=[0, 0])
    products = build_controlled_products()
    orders = build_controlled_orders()

    meta = DatasetMeta(
        dataset_id=dataset_id,
        source="controlled-swap-fixture",
        cell_size_m=1.5,
    )
    dataset = DemoResponse(
        meta=meta,
        cleaning_report=CleaningReport(),
        layout=layout,
        products=products,
        orders=orders,
    )

    with open(ds_dir / "processed.json", "w", encoding="utf-8") as f:
        json.dump(dataset.model_dump(), f)

    # Call API endpoint
    resp = client.post(
        f"/api/datasets/{dataset_id}/simulate",
        json={
            "layout_permutation": {"S001": "SKU-HOT", "S050": "SKU-COLD"},
            "speed_m_s": 1.2,
            "handling_time_s": 10.0,
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["dataset_id"] == dataset_id
    assert "policies" in data
    assert "original" in data["policies"]
    assert "player" in data["policies"]
    assert "baseline" in data["policies"]

    orig = data["policies"]["original"]
    player = data["policies"]["player"]
    base = data["policies"]["baseline"]

    assert orig["total_distance_m"] == 4053.0
    assert player["total_distance_m"] == 231.0
    assert base["total_distance_m"] == 159.0

    # Invariants
    assert base["total_distance_m"] < player["total_distance_m"] < orig["total_distance_m"]
    assert base["total_pick_time_s"] < player["total_pick_time_s"] < orig["total_pick_time_s"]
    assert orig["orders_replayed"] == player["orders_replayed"] == base["orders_replayed"] == 51
    assert len(data["orders"]) == 51
