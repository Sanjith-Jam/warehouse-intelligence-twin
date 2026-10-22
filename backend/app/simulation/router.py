"""Deterministic BFS routing and slotting logic."""
from collections import deque
from typing import Optional
from backend.app.models.schemas import (
    WarehouseLayout,
    Slot,
    Product,
    Order,
    OrderRoute,
    RouteVisit,
    SimulationAssumptions,
    SimulateResponse,
)

# Cardinal directions in fixed deterministic order: North, East, South, West
CARDINAL_DIRECTIONS = [(0, 1), (1, 0), (0, -1), (-1, 0)]


def find_shortest_walkable_path(
    start: list[int],
    target: list[int],
    walkable_set: set[tuple[int, int]],
) -> Optional[list[list[int]]]:
    """
    Find shortest deterministic walkable path between start and target cells using BFS.
    Returns list of [x, z] coordinates from start to target inclusive, or None if unreachable.
    """
    start_tuple = (start[0], start[1])
    target_tuple = (target[0], target[1])

    if start_tuple == target_tuple:
        return [[start[0], start[1]]]

    if start_tuple not in walkable_set or target_tuple not in walkable_set:
        return None

    queue: deque[tuple[tuple[int, int], list[list[int]]]] = deque([
        (start_tuple, [[start[0], start[1]]])
    ])
    visited: set[tuple[int, int]] = {start_tuple}

    while queue:
        current, path = queue.popleft()
        cx, cz = current

        for dx, dz in CARDINAL_DIRECTIONS:
            neighbor = (cx + dx, cz + dz)
            if neighbor == target_tuple:
                return path + [[neighbor[0], neighbor[1]]]

            if neighbor in walkable_set and neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, path + [[neighbor[0], neighbor[1]]]))

    return None


def calculate_dock_distances(
    layout: WarehouseLayout,
    walkable_set: set[tuple[int, int]],
) -> dict[str, int]:
    """Compute shortest walkable distance (grid steps) from dock to each slot's access cell."""
    dock = layout.dock
    distances: dict[str, int] = {}

    for slot in layout.slots:
        path = find_shortest_walkable_path(dock, slot.access_cell, walkable_set)
        if path is None:
            raise ValueError(f"Access cell {slot.access_cell} for slot {slot.slot_id} is unreachable from dock")
        # Number of steps = len(path) - 1
        distances[slot.slot_id] = len(path) - 1

    return distances


def compute_baseline_assignments(
    layout: WarehouseLayout,
    products: list[Product],
    walkable_set: set[tuple[int, int]],
) -> dict[str, str]:
    """
    Compute fast-mover baseline slotting.
    Sorts SKUs by descending pick_frequency (tie-break: SKU ascending).
    Sorts slots by shortest walkable distance from dock (tie-break: slot_id ascending).
    """
    dock_distances = calculate_dock_distances(layout, walkable_set)

    # Sort slots: shortest distance from dock, tie-break slot_id
    sorted_slots = sorted(layout.slots, key=lambda s: (dock_distances[s.slot_id], s.slot_id))

    # Sort products: descending pick_frequency, tie-break sku
    sorted_products = sorted(products, key=lambda p: (-p.pick_frequency, p.sku))

    if len(sorted_slots) != len(sorted_products):
        raise ValueError(
            f"Slot count ({len(sorted_slots)}) does not match product count ({len(sorted_products)})"
        )

    assignments: dict[str, str] = {}
    for slot, prod in zip(sorted_slots, sorted_products):
        assignments[slot.slot_id] = prod.sku

    return assignments


def route_order(
    order: Order,
    layout: WarehouseLayout,
    sku_to_slot: dict[str, Slot],
    walkable_set: set[tuple[int, int]],
) -> OrderRoute:
    """
    Route an order deterministically through its lines in given order and return to dock.
    """
    dock = layout.dock
    current_pos = dock
    waypoints: list[list[int]] = [[dock[0], dock[1]]]
    visits: list[RouteVisit] = []

    for line in order.lines:
        slot = sku_to_slot.get(line.sku)
        if not slot:
            raise ValueError(f"SKU '{line.sku}' in order '{order.order_id}' has no assigned slot")

        access_cell = slot.access_cell

        # If already at access cell, record visit at current waypoint index
        if current_pos[0] == access_cell[0] and current_pos[1] == access_cell[1]:
            visits.append(
                RouteVisit(
                    sku=line.sku,
                    slot_id=slot.slot_id,
                    waypoint_index=len(waypoints) - 1,
                )
            )
        else:
            path = find_shortest_walkable_path(current_pos, access_cell, walkable_set)
            if path is None:
                raise ValueError(
                    f"Access cell {access_cell} for SKU '{line.sku}' is unreachable from {current_pos}"
                )
            # Append steps excluding starting step (which matches current waypoint)
            for step in path[1:]:
                waypoints.append(step)

            visits.append(
                RouteVisit(
                    sku=line.sku,
                    slot_id=slot.slot_id,
                    waypoint_index=len(waypoints) - 1,
                )
            )
            current_pos = access_cell

    # Return to dock
    if not (current_pos[0] == dock[0] and current_pos[1] == dock[1]):
        return_path = find_shortest_walkable_path(current_pos, dock, walkable_set)
        if return_path is None:
            raise ValueError(f"Dock {dock} is unreachable from {current_pos}")
        for step in return_path[1:]:
            waypoints.append(step)

    return OrderRoute(
        order_id=order.order_id,
        waypoints=waypoints,
        visits=visits,
    )


def simulate_orders(
    dataset_id: str,
    orders: list[Order],
    layout: WarehouseLayout,
    products: list[Product],
    policy: str,
    slot_assignments: Optional[dict[str, str]],
    speed_mps: float,
    cell_size_m: float = 1.5,
    handling_seconds_per_line: float = 10.0,
) -> SimulateResponse:
    """
    Execute deterministic order simulation across specified policy and slotting configuration.
    """
    walkable_set = {(c[0], c[1]) for c in layout.walkable_cells}

    # Verify dock is walkable
    if (layout.dock[0], layout.dock[1]) not in walkable_set:
        raise ValueError(f"Dock coordinate {layout.dock} is not in walkable_cells")

    # Determine slot assignments based on policy
    effective_assignments: dict[str, str] = {}

    if policy == "original":
        effective_assignments = {s.slot_id: s.sku for s in layout.slots}
    elif policy == "baseline":
        effective_assignments = compute_baseline_assignments(layout, products, walkable_set)
    elif policy == "player":
        if not slot_assignments:
            raise ValueError("policy 'player' requires slot_assignments")

        # Validate that slot_assignments is a complete bijection (permutation)
        layout_slot_ids = {s.slot_id for s in layout.slots}
        layout_skus = {s.sku for s in layout.slots}

        provided_slots = set(slot_assignments.keys())
        provided_skus = set(slot_assignments.values())

        if provided_slots != layout_slot_ids:
            missing = layout_slot_ids - provided_slots
            extra = provided_slots - layout_slot_ids
            raise ValueError(f"Invalid slots in player assignments. Missing: {missing}, Extra: {extra}")

        if provided_skus != layout_skus:
            missing = layout_skus - provided_skus
            extra = provided_skus - layout_skus
            raise ValueError(f"Invalid SKUs in player assignments. Missing: {missing}, Extra: {extra}")

        if len(slot_assignments) != len(layout.slots):
            raise ValueError("Duplicate slot assignments detected")

        effective_assignments = slot_assignments
    else:
        raise ValueError(f"Unsupported policy: '{policy}'. Must be original, baseline, or player.")

    # Build slot map: slot_id -> Slot
    slot_map = {s.slot_id: s for s in layout.slots}

    # Build sku -> Slot based on effective assignments
    sku_to_slot: dict[str, Slot] = {}
    for s_id, sku in effective_assignments.items():
        base_slot = slot_map[s_id]
        # Create virtual slot reference with current assigned SKU
        sku_to_slot[sku] = Slot(
            slot_id=base_slot.slot_id,
            rack_cell=base_slot.rack_cell,
            access_cell=base_slot.access_cell,
            sku=sku,
        )

    # Route each order
    routes: list[OrderRoute] = []
    total_grid_steps = 0
    total_lines_picked = 0

    for order in orders:
        route = route_order(order, layout, sku_to_slot, walkable_set)
        routes.append(route)

        # Sum Manhattan steps between consecutive waypoints
        for i in range(len(route.waypoints) - 1):
            w1 = route.waypoints[i]
            w2 = route.waypoints[i + 1]
            total_grid_steps += abs(w2[0] - w1[0]) + abs(w2[1] - w1[1])

        total_lines_picked += len(order.lines)

    # Calculate metrics
    distance_m = float(total_grid_steps * cell_size_m)
    # Travel time + handling time
    travel_time_s = distance_m / speed_mps if speed_mps > 0 else 0.0
    handling_time_s = total_lines_picked * handling_seconds_per_line
    estimated_pick_time_s = travel_time_s + handling_time_s

    orders_replayed = len(orders)
    average_pick_time_s = estimated_pick_time_s / orders_replayed if orders_replayed > 0 else 0.0

    return SimulateResponse(
        dataset_id=dataset_id,
        policy=policy,
        slot_assignments=effective_assignments,
        orders_replayed=orders_replayed,
        distance_m=distance_m,
        estimated_pick_time_s=estimated_pick_time_s,
        average_pick_time_s=average_pick_time_s,
        routes=routes,
        warnings=[],
        assumptions=SimulationAssumptions(
            speed_mps=speed_mps,
            handling_seconds_per_line=handling_seconds_per_line,
        ),
    )
