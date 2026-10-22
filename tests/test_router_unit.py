"""Unit tests for simulation router and baseline slotting algorithm."""
import pytest
from backend.app.simulation.router import (
    find_shortest_walkable_path,
    calculate_dock_distances,
    compute_baseline_assignments,
)
from backend.app.models.schemas import WarehouseLayout, Slot, Product


def test_bfs_shortest_path_simple():
    """Test BFS finds shortest cardinal path."""
    walkable = {(0, 0), (1, 0), (2, 0), (2, 1), (2, 2)}
    path = find_shortest_walkable_path([0, 0], [2, 2], walkable)
    assert path is not None
    assert path == [[0, 0], [1, 0], [2, 0], [2, 1], [2, 2]]


def test_bfs_start_equals_target():
    """Test start == target returns single cell."""
    walkable = {(0, 0), (1, 0)}
    path = find_shortest_walkable_path([0, 0], [0, 0], walkable)
    assert path == [[0, 0]]


def test_bfs_unreachable_target():
    """Test unreachable target returns None."""
    walkable = {(0, 0), (1, 0), (3, 3)}
    path = find_shortest_walkable_path([0, 0], [3, 3], walkable)
    assert path is None


def test_baseline_slotting_sort_order():
    """
    Test fast-mover baseline slotting:
    SKUs sorted by descending pick_frequency (tie-break sku asc).
    Slots sorted by shortest dock distance (tie-break slot_id asc).
    """
    layout = WarehouseLayout(
        layout_id="test-layout",
        width=5,
        height=3,
        walkable_cells=[[0, 0], [1, 0], [2, 0], [3, 0], [4, 0]],
        dock=[0, 0],
        slots=[
            Slot(slot_id="S_FAR", rack_cell=[4, 1], access_cell=[4, 0], sku="SKU_INIT_1"),
            Slot(slot_id="S_NEAR", rack_cell=[1, 1], access_cell=[1, 0], sku="SKU_INIT_2"),
            Slot(slot_id="S_MID", rack_cell=[2, 1], access_cell=[2, 0], sku="SKU_INIT_3"),
        ],
    )
    walkable_set = {(c[0], c[1]) for c in layout.walkable_cells}

    # S_NEAR dist=1, S_MID dist=2, S_FAR dist=4
    distances = calculate_dock_distances(layout, walkable_set)
    assert distances["S_NEAR"] == 1
    assert distances["S_MID"] == 2
    assert distances["S_FAR"] == 4

    products = [
        Product(sku="LOW_DEMAND", name="Low", pick_frequency=5),
        Product(sku="HIGH_DEMAND", name="High", pick_frequency=100),
        Product(sku="MED_DEMAND", name="Med", pick_frequency=50),
    ]

    assignments = compute_baseline_assignments(layout, products, walkable_set)

    # HIGH_DEMAND should get S_NEAR (closest to dock)
    # MED_DEMAND should get S_MID
    # LOW_DEMAND should get S_FAR
    assert assignments["S_NEAR"] == "HIGH_DEMAND"
    assert assignments["S_MID"] == "MED_DEMAND"
    assert assignments["S_FAR"] == "LOW_DEMAND"
