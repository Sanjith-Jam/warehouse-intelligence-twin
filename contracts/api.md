# Warehouse Intelligence Twin API — v1

Authoritative shared contract. Codex owns edits; AGY requests changes via PR comments. This resolves naming differences in the supplied planning documents. JSON, snake_case, no authentication for this local prototype. Backend `http://localhost:8000`; frontend `http://localhost:5173`. Allow that development origin via CORS. Never send server secrets to the frontend.

## Geometry and data invariants

- Coordinates are integer grid pairs `[x,z]`, rendered on the X/Z floor plane; Y is vertical. World meters = grid coordinate multiplied by `meta.cell_size_m`.
- `layout.width` and `layout.height` are grid cell counts. Bounds are zero-inclusive, width/height-exclusive.
- `dock` and every `access_cell` belong to `walkable_cells`. Rack cells are impassable. Routes use adjacent cardinal walkable cells and include dock departure and return for each order.
- Slot IDs identify fixed geometry; SKUs identify products. One SKU per slot, one slot per SKU; every replay SKU has a reachable slot. Swapping changes assignments only.
- Data and original layout are immutable during a server run. `meta.dataset_id` identifies the preprocessed snapshot. Order selection comes from `/api/demo`; send the same ordered `order_ids` to all three simulations.
- Picking excludes case-insensitive C-prefixed invoices, non-positive quantities, blank/non-product codes. Preserve raw financial records separately for optional analytics. Document the chosen month, source sheet, exclusion list, timezone assumption, and pick-frequency definition.
- JSON examples illustrate schema only. Fixture data must say `real_order_data:false`; no fabricated real-data claims.

## GET /health

```json
{"status":"ok"}
```

## GET /api/demo — main frontend bootstrap

```json
{
  "meta":{"dataset_id":"sample-v1","source":"synthetic fixture","month":null,"real_order_data":false,"synthetic_warehouse":true,"cell_size_m":1.5},
  "layout":{"layout_id":"original","width":4,"height":3,"walkable_cells":[[0,0],[1,0],[2,0],[3,0]],"dock":[0,0],"slots":[{"slot_id":"S001","rack_cell":[1,1],"access_cell":[1,0],"sku":"DEMO-001"}]},
  "products":[{"sku":"DEMO-001","name":"Sample product","pick_frequency":1}],
  "orders":[{"order_id":"DEMO-ORDER-1","lines":[{"sku":"DEMO-001","quantity":2}]}]
}
```

With real data, `source` is `UCI Online Retail II`, `month` is `YYYY-MM`, and `real_order_data` is true. Demo orders are a deterministic small selection (10–30) from the month, filtered to retained SKUs; drop empty orders and disclose this restriction. `pick_frequency` counts retained positive picking lines in the month, not units. `orders` contains only selected demo orders; full-month preprocessing is retained server-side.

## GET /api/warehouse

Return `{"meta": <same meta>, "layout": <same layout>, "products": <same products>}`.

## GET /api/orders

Return `{"dataset_id": "<same snapshot>", "orders": <same selected orders>}`.

## POST /api/simulate

Request:

```json
{"order_ids":["DEMO-ORDER-1"],"slot_assignments":{"S001":"DEMO-001"},"policy":"player","speed_mps":1.2}
```

- `policy`: `original`, `baseline`, or `player`.
- `order_ids`: required nonempty unique known IDs; replay in given order.
- `speed_mps`: finite positive number, default 1.2, maximum 10. Handling time is 10 seconds per retained order line, independent of quantity; all policies share it.
- `player` requires a complete slot-to-SKU mapping, a permutation of the original SKU set. Reject unknown/missing/duplicate slots or SKUs. Original and baseline ignore client assignments and use server-defined mappings.
- Baseline sorts SKUs by descending monthly `pick_frequency` (tie: SKU), slots by shortest walkable distance from dock to access cell (tie: slot ID).
- Route each order deterministically through its retained lines in supplied order, then return to dock. Use the same BFS/pathfinder and tie-breaks for every policy. Do not silently optimize only one policy.

Response:

```json
{
  "dataset_id":"sample-v1",
  "policy":"player",
  "slot_assignments":{"S001":"DEMO-001"},
  "orders_replayed":1,
  "distance_m":3.0,
  "estimated_pick_time_s":12.5,
  "average_pick_time_s":12.5,
  "routes":[{"order_id":"DEMO-ORDER-1","waypoints":[[0,0],[1,0],[0,0]],"visits":[{"sku":"DEMO-001","slot_id":"S001","waypoint_index":1}]}],
  "warnings":[],
  "assumptions":{"speed_mps":1.2,"handling_seconds_per_line":10}
}
```

`visits` has one entry per retained line, in service order. Waypoint indices are zero-based. Consecutive picks at the same access cell can share an index. Every route starts and ends at the dock. Distances are the sum of grid edge lengths times cell size; total time = distance/speed + retained line count × handling seconds. Average time divides by orders replayed. Preserve full numeric precision in API responses; round only for display.

Frontend runs original/baseline/player requests with identical orders and speed, animates returned waypoints, displays returned assignments and metrics, and reports backend failures honestly. No separate comparison endpoint is required.

## POST /api/analyze — optional P1

Request: `{"question":"Top 5 products by net revenue?"}`.

```json
{"status":"answered","answer":"...","sql":"SELECT ...","columns":["stock_code","revenue_gbp"],"rows":[],"highlight_skus":[],"assumptions":[],"limited":false}
```

Rows are arrays matching column order. Money is GBP. `status` is `answered`, `clarify`, or `unavailable`. Non-answered responses retain the same fields (`sql:null`, empty columns/rows); `clarify` adds `clarification_question`. `answer` explains unavailable features. Guided SQL templates are an acceptable disclosed fallback. Show executed SQL and cleaning assumptions. No `/api/analytics/query` alias is required.

Use read-only DuckDB, SQL AST validation plus table/function allowlists, no external access or filesystem/network SQL functions, one SELECT/CTE statement only, bounded rows (100) and runtime. No DDL/DML/ATTACH/COPY/PRAGMA, arbitrary SQL execution, or browser keys.

## Failures and integration

Use HTTP 422 for invalid requests, with FastAPI's standard `detail` validation payload or `{"detail":"human-readable reason"}`. Never return partial or invented metrics for invalid assignments/unreachable routes. Use 503 with a reason if required data is not ready; `/health` may still succeed. Unknown endpoints use 404. Frontend checks HTTP status before parsing success payloads.

AGY tests determinism, all route cells/edges, dock return, mapping validation, cancellation/non-product filters, baseline placement, distance/time formulas, and optional SQL safety. Codex reviews and runs relevant checks before squash merge; AGY never merges or pushes to main.
