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
    PolicyResult,
    SimulatedOrder,
    SimulationResponse,
    DemoResponse,
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
    dock: Optional[list[int]] = None,
) -> dict[str, int]:
    """Compute shortest walkable distance (grid steps) from dock to each slot's access cell."""
    resolved_dock = dock if dock is not None else layout.dock
    distances: dict[str, int] = {}

    for slot in layout.slots:
        path = find_shortest_walkable_path(resolved_dock, slot.access_cell, walkable_set)
        if path is None:
            # Fallback to Manhattan steps if unreachable
            distances[slot.slot_id] = abs(slot.access_cell[0] - resolved_dock[0]) + abs(slot.access_cell[1] - resolved_dock[1])
        else:
            distances[slot.slot_id] = len(path) - 1

    return distances


def compute_baseline_assignments(
    layout: WarehouseLayout,
    products: list[Product],
    walkable_set: set[tuple[int, int]],
    dock: Optional[list[int]] = None,
) -> dict[str, str]:
    """
    Compute fast-mover baseline slotting.
    Sorts SKUs by descending pick_frequency (tie-break: SKU ascending).
    Sorts slots by shortest walkable distance from dock (tie-break: slot_id ascending).
    Assigns highest-frequency products to the closest slots. Spare slots remain unassigned.
    """
    dock_distances = calculate_dock_distances(layout, walkable_set, dock=dock)

    # Sort slots: shortest distance from dock, tie-break slot_id
    sorted_slots = sorted(layout.slots, key=lambda s: (dock_distances[s.slot_id], s.slot_id))

    # Sort products: descending pick_frequency, tie-break sku
    sorted_products = sorted(products, key=lambda p: (-p.pick_frequency, p.sku))

    if len(sorted_products) > len(sorted_slots):
        raise ValueError(
            f"Product count ({len(sorted_products)}) exceeds slot count ({len(sorted_slots)})"
        )

    assignments: dict[str, str] = {}
    for slot, prod in zip(sorted_slots, sorted_products):
        assignments[slot.slot_id] = prod.sku

    return assignments


def compute_baseline_layout(
    dataset: DemoResponse,
    dock: Optional[list[int]] = None,
) -> dict[str, str]:
    """
    Compute baseline fast-mover layout mapping slot_id -> sku for a dataset.
    Sorts dataset's actual products by pick_frequency descending.
    Sorts slots by shortest walkable distance to dock ascending.
    Assigns highest-frequency products to closest slots. Spare slots remain unassigned.
    """
    walkable_set = {(c[0], c[1]) for c in dataset.layout.walkable_cells}
    resolved_dock = dock if dock is not None else dataset.layout.dock
    return compute_baseline_assignments(
        dataset.layout, dataset.products, walkable_set, dock=resolved_dock
    )


def normalize_and_validate_player_permutation(
    permutation: dict[str, str],
    layout: WarehouseLayout,
    products: list[Product],
) -> dict[str, str]:
    """
    Validate and normalize player layout permutation to canonical slot_id -> sku mapping.
    Accepts:
      - slot_id -> sku (e.g. {"S001": "20724"})
      - sku -> slot_id (e.g. {"20724": "S001"})
    Validates:
      - All SKUs belong to dataset products
      - All slot IDs belong to warehouse layout
      - 1:1 bijection (no duplicate slots or SKUs)
      - All dataset products are assigned
    """
    if not permutation:
        raise ValueError("Player permutation must not be empty")

    layout_slot_ids = {s.slot_id for s in layout.slots}
    product_skus = {p.sku for p in products}

    keys = set(permutation.keys())
    values = set(permutation.values())

    # Detect orientation
    # 1. slot_id -> sku: keys are slots, values are skus
    if keys.issubset(layout_slot_ids):
        # First check slots completeness if product count matches total layout slots
        if len(product_skus) == len(layout_slot_ids) and keys != layout_slot_ids:
            missing = layout_slot_ids - keys
            extra = keys - layout_slot_ids
            raise ValueError(f"Invalid slots in player assignments. Missing: {missing}, Extra: {extra}")

        # Check unknown SKUs
        unknown_skus = values - product_skus
        if unknown_skus:
            raise ValueError(f"Invalid SKUs in player assignments. Missing: set(), Extra: {unknown_skus}")

        # Check duplicate SKUs
        if len(permutation) != len(values):
            missing_skus = product_skus - values
            raise ValueError(f"Invalid SKUs in player assignments. Missing: {missing_skus}, Extra: set()")

        # Check all products mapped
        if values != product_skus:
            missing_skus = product_skus - values
            raise ValueError(f"Invalid SKUs in player assignments. Missing: {missing_skus}, Extra: set()")

        return dict(permutation)

    # 2. sku -> slot_id: keys are skus, values are slots
    if keys.issubset(product_skus):
        unknown_slots = values - layout_slot_ids
        if unknown_slots:
            raise ValueError(f"Invalid slots in player assignments. Missing: set(), Extra: {unknown_slots}")

        if len(permutation) != len(values):
            raise ValueError("Duplicate slot assignments detected in player permutation.")

        if keys != product_skus:
            missing_skus = product_skus - keys
            raise ValueError(f"Invalid SKUs in player assignments. Missing: {missing_skus}, Extra: set()")

        # Invert to slot_id -> sku
        return {slot_id: sku for sku, slot_id in permutation.items()}

    # Invalid keys detected: identify whether keys look more like slot or sku
    invalid_keys = keys - (layout_slot_ids | product_skus)
    if any(k in layout_slot_ids for k in keys):
        raise ValueError(f"Invalid slots in player assignments. Extra: {invalid_keys}")
    raise ValueError(f"Invalid SKUs in player assignments. Extra: {invalid_keys}")


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
        effective_assignments = {s.slot_id: s.sku for s in layout.slots if s.sku}
    elif policy == "baseline":
        effective_assignments = compute_baseline_assignments(layout, products, walkable_set)
    elif policy == "player":
        if not slot_assignments:
            raise ValueError("policy 'player' requires slot_assignments")
        effective_assignments = normalize_and_validate_player_permutation(
            slot_assignments, layout, products
        )
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


def simulate_dataset_policies(
    dataset: DemoResponse,
    order_ids: Optional[list[str]] = None,
    layout_permutation: Optional[dict[str, str]] = None,
    speed_mps: float = 1.2,
    handling_seconds_per_line: float = 15.0,
    cell_size_m: Optional[float] = None,
) -> SimulationResponse:
    """
    Execute simulation across original, baseline, and player policies deterministically.
    Freezes orders and routes all policies through identical order sequence.
    """
    resolved_cell_size = cell_size_m if cell_size_m is not None else dataset.meta.cell_size_m
    resolved_dock = dataset.layout.dock

    # Determine orders to replay
    all_orders_map = {o.order_id: o for o in dataset.orders}
    if order_ids is not None:
        orders_to_replay = []
        for oid in order_ids:
            if oid not in all_orders_map:
                raise ValueError(f"Unknown order ID '{oid}' in requested order_ids")
            orders_to_replay.append(all_orders_map[oid])
    else:
        orders_to_replay = dataset.orders

    if not orders_to_replay:
        raise ValueError("No orders available to simulate")

    # 1. Original layout simulation
    sim_original = simulate_orders(
        dataset_id=dataset.meta.dataset_id,
        orders=orders_to_replay,
        layout=dataset.layout,
        products=dataset.products,
        policy="original",
        slot_assignments=None,
        speed_mps=speed_mps,
        cell_size_m=resolved_cell_size,
        handling_seconds_per_line=handling_seconds_per_line,
    )

    # 2. Baseline layout simulation
    sim_baseline = simulate_orders(
        dataset_id=dataset.meta.dataset_id,
        orders=orders_to_replay,
        layout=dataset.layout,
        products=dataset.products,
        policy="baseline",
        slot_assignments=None,
        speed_mps=speed_mps,
        cell_size_m=resolved_cell_size,
        handling_seconds_per_line=handling_seconds_per_line,
    )

    policies: dict[str, PolicyResult] = {
        "original": PolicyResult(
            policy="original",
            slot_assignments=sim_original.slot_assignments,
            orders_replayed=sim_original.orders_replayed,
            total_distance_m=sim_original.distance_m,
            total_pick_time_s=sim_original.estimated_pick_time_s,
            average_pick_time_s=sim_original.average_pick_time_s,
            distance_m=sim_original.distance_m,
            estimated_pick_time_s=sim_original.estimated_pick_time_s,
            routes=sim_original.routes,
        ),
        "baseline": PolicyResult(
            policy="baseline",
            slot_assignments=sim_baseline.slot_assignments,
            orders_replayed=sim_baseline.orders_replayed,
            total_distance_m=sim_baseline.distance_m,
            total_pick_time_s=sim_baseline.estimated_pick_time_s,
            average_pick_time_s=sim_baseline.average_pick_time_s,
            distance_m=sim_baseline.distance_m,
            estimated_pick_time_s=sim_baseline.estimated_pick_time_s,
            routes=sim_baseline.routes,
        ),
    }

    sim_player: Optional[SimulateResponse] = None
    if layout_permutation:
        canonical_player = normalize_and_validate_player_permutation(
            layout_permutation, dataset.layout, dataset.products
        )
        sim_player = simulate_orders(
            dataset_id=dataset.meta.dataset_id,
            orders=orders_to_replay,
            layout=dataset.layout,
            products=dataset.products,
            policy="player",
            slot_assignments=canonical_player,
            speed_mps=speed_mps,
            cell_size_m=resolved_cell_size,
            handling_seconds_per_line=handling_seconds_per_line,
        )
        policies["player"] = PolicyResult(
            policy="player",
            slot_assignments=sim_player.slot_assignments,
            orders_replayed=sim_player.orders_replayed,
            total_distance_m=sim_player.distance_m,
            total_pick_time_s=sim_player.estimated_pick_time_s,
            average_pick_time_s=sim_player.average_pick_time_s,
            distance_m=sim_player.distance_m,
            estimated_pick_time_s=sim_player.estimated_pick_time_s,
            routes=sim_player.routes,
        )

    # Build SimulatedOrder records
    simulated_orders: list[SimulatedOrder] = []
    for idx, ord_item in enumerate(orders_to_replay):
        r_orig = sim_original.routes[idx]
        r_base = sim_baseline.routes[idx]

        routes_dict = {"original": r_orig, "baseline": r_base}

        steps_orig = sum(
            abs(r_orig.waypoints[i + 1][0] - r_orig.waypoints[i][0])
            + abs(r_orig.waypoints[i + 1][1] - r_orig.waypoints[i][1])
            for i in range(len(r_orig.waypoints) - 1)
        )
        steps_base = sum(
            abs(r_base.waypoints[i + 1][0] - r_base.waypoints[i][0])
            + abs(r_base.waypoints[i + 1][1] - r_base.waypoints[i][1])
            for i in range(len(r_base.waypoints) - 1)
        )

        dist_orig = float(steps_orig * resolved_cell_size)
        dist_base = float(steps_base * resolved_cell_size)

        lines_count = len(ord_item.lines)
        time_orig = (dist_orig / speed_mps if speed_mps > 0 else 0.0) + lines_count * handling_seconds_per_line
        time_base = (dist_base / speed_mps if speed_mps > 0 else 0.0) + lines_count * handling_seconds_per_line

        times_dict = {"original": time_orig, "baseline": time_base}
        distances_dict = {"original": dist_orig, "baseline": dist_base}

        if sim_player:
            r_play = sim_player.routes[idx]
            routes_dict["player"] = r_play
            steps_play = sum(
                abs(r_play.waypoints[i + 1][0] - r_play.waypoints[i][0])
                + abs(r_play.waypoints[i + 1][1] - r_play.waypoints[i][1])
                for i in range(len(r_play.waypoints) - 1)
            )
            dist_play = float(steps_play * resolved_cell_size)
            time_play = (dist_play / speed_mps if speed_mps > 0 else 0.0) + lines_count * handling_seconds_per_line
            times_dict["player"] = time_play
            distances_dict["player"] = dist_play

        primary_route = routes_dict.get("player", r_base)
        primary_time = times_dict.get("player", time_base)
        primary_dist = distances_dict.get("player", dist_base)

        simulated_orders.append(
            SimulatedOrder(
                order_id=ord_item.order_id,
                lines=ord_item.lines,
                routes=routes_dict,
                picking_times=times_dict,
                picking_times_s=times_dict,
                distances_m=distances_dict,
                waypoints=primary_route.waypoints,
                visits=primary_route.visits,
                estimated_pick_time_s=primary_time,
                distance_m=primary_dist,
            )
        )

    target_policy = "player" if sim_player else "baseline"
    target_sim = sim_player if sim_player else sim_baseline

    assumptions = SimulationAssumptions(
        speed_mps=speed_mps,
        speed_m_s=speed_mps,
        handling_seconds_per_line=handling_seconds_per_line,
        handling_time_s=handling_seconds_per_line,
        dock=resolved_dock,
        dock_coordinate=resolved_dock,
    )

    return SimulationResponse(
        dataset_id=dataset.meta.dataset_id,
        warehouse=dataset.layout,
        policies=policies,
        orders=simulated_orders,
        assumptions=assumptions,
        policy=target_policy,
        slot_assignments=target_sim.slot_assignments,
        orders_replayed=target_sim.orders_replayed,
        distance_m=target_sim.distance_m,
        estimated_pick_time_s=target_sim.estimated_pick_time_s,
        average_pick_time_s=target_sim.average_pick_time_s,
        routes=target_sim.routes,
        warnings=[],
    )
