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

## Import Specification & Column Mapping

The system ingests tabular order workbooks in `.csv`, `.xlsx`, and `.xls` formats. Column headers are automatically detected using canonical aliases (case-insensitive, ignoring punctuation and whitespace):

- `invoice`: `["invoiceno", "invoice", "order_id", "order id", "invoicenum", "billno"]` (Required)
- `sku`: `["stockcode", "sku", "productcode", "itemcode", "product id"]` (Required)
- `description`: `["description", "productname", "item_description", "name", "title"]` (Optional)
- `quantity`: `["quantity", "qty", "units"]` (Required)
- `date`: `["invoicedate", "date", "timestamp", "order_date", "datetime"]` (Required)

Optional preprocess configuration allows specifying `sheet_name`, `target_month` (`YYYY-MM`), `top_skus` (default 100, max 1000), `max_orders` (default 20, max 100), and `column_mapping` overrides.

## POST /api/datasets/upload

Upload a raw workbook for inspection and session staging. Does not overwrite `demo.json`.

Request:
- `Content-Type: multipart/form-data`
- Body: `file: UploadFile` (CSV, XLSX, XLS; max 50MB)

Response (HTTP 200 / 201):

```json
{
  "dataset_id": "ds_a1b2c3d4e5f6",
  "filename": "online_retail_II.xlsx",
  "file_size_bytes": 45123987,
  "sheets": ["Year 2009-2010", "Year 2010-2011"],
  "detected_columns": {
    "invoice": "Invoice",
    "sku": "StockCode",
    "description": "Description",
    "quantity": "Quantity",
    "date": "InvoiceDate"
  },
  "missing_required_columns": [],
  "available_months": ["2010-12", "2011-01", "2011-02", "2011-03", "2011-04", "2011-05", "2011-06"],
  "total_rows": 541909,
  "preview_rows": [
    {
      "Invoice": "536365",
      "StockCode": "85123A",
      "Description": "WHITE HANGING HEART T-LIGHT HOLDER",
      "Quantity": 6,
      "InvoiceDate": "2010-12-01 08:26:00"
    }
  ]
}
```

Errors:
- 400 / 422: `UNSUPPORTED_FILE_TYPE`, `EMPTY_FILE`
- 413: `FILE_TOO_LARGE`

## POST /api/datasets/{id}/preprocess

Preprocesses an uploaded dataset staging file into a clean simulation snapshot.

Request:

```json
{
  "sheet_name": "Year 2010-2011",
  "target_month": "2011-06",
  "top_skus": 100,
  "max_orders": 20,
  "column_mapping": null,
  "cell_size_m": 1.5
}
```

Response (HTTP 200):

Returns `DatasetDetailResponse` matching `GET /api/datasets/{id}` below.

Errors:
- 404: `DATASET_NOT_FOUND`
- 422: `NO_DATA_IN_MONTH`, `MISSING_REQUIRED_COLUMNS`

## GET /api/datasets/{id}

Fetch complete preprocessed dataset details including metadata, data cleaning report / provenance, synthetic warehouse layout, products, and representative orders.

Response (HTTP 200):

```json
{
  "meta": {
    "dataset_id": "ds_a1b2c3d4e5f6",
    "snapshot_id": "snap_f7e8d9c0",
    "source_filename": "online_retail_II.xlsx",
    "month": "2011-06",
    "created_at": "2026-10-22T10:00:00Z",
    "top_sku_count": 100,
    "order_count": 20,
    "real_order_data": true,
    "synthetic_warehouse": true,
    "cell_size_m": 1.5
  },
  "cleaning_report": {
    "purpose": "Authoritative shared June 2011 UCI order snapshot",
    "month": "2011-06",
    "sheet": "Year 2010-2011",
    "time_assumption": "Source naive invoice dates; calendar month without timezone conversion.",
    "month_rows": 36874,
    "cancelled_month_rows": 711,
    "nonpositive_or_missing_quantity_rows": 818,
    "nonproduct_or_blank_sku_rows": 241,
    "filter_counts_overlap": true,
    "excluded_nonproduct_codes": ["POST", "DOT", "M", "D", "BANK CHARGES"],
    "valid_positive_product_lines": 35857,
    "top_sku_count": 100,
    "pick_frequency_definition": "Number of retained positive picking lines per SKU in the complete month; not units.",
    "top_sku_month_lines": 8927,
    "top_sku_month_order_count": 1284,
    "selected_order_count": 20,
    "selected_order_ids": ["555157", "555158"],
    "selection_criteria": "Deterministic selection of multi-line orders filtered to retained SKUs"
  },
  "layout": {
    "layout_id": "original",
    "width": 21,
    "height": 21,
    "walkable_cells": [[0,0], [1,0]],
    "dock": [0,0],
    "slots": [
      {"slot_id": "S001", "rack_cell": [1,1], "access_cell": [1,0], "sku": "85123A"}
    ]
  },
  "products": [
    {"sku": "85123A", "name": "WHITE HANGING HEART T-LIGHT HOLDER", "pick_frequency": 150}
  ],
  "orders": [
    {
      "order_id": "555157",
      "lines": [{"sku": "85123A", "quantity": 6}]
    }
  ]
}
```

Errors:
- 404: `DATASET_NOT_FOUND`

## GET /api/datasets/{id}/export

Export preprocessed dataset or raw data in JSON or CSV format.

Query parameters:
- `format`: `json` (default) or `csv`

Response (HTTP 200):
Returns a downloadable file or export descriptor:

```json
{
  "dataset_id": "ds_a1b2c3d4e5f6",
  "format": "json",
  "download_url": "/api/datasets/ds_a1b2c3d4e5f6/download",
  "record_count": 100,
  "file_size_bytes": 1048576
}
```

Errors:
- 404: `DATASET_NOT_FOUND`

## POST /api/datasets/{id}/simulate

Replay picking simulation against a specific preprocessed dataset snapshot. Follows identical routing and scoring rules as `POST /api/simulate`.

Request:

```json
{
  "order_ids": ["555157"],
  "slot_assignments": {"S001": "85123A"},
  "policy": "player",
  "speed_mps": 1.2
}
```

Response (HTTP 200):
Returns `SimulateResponse` identical to `POST /api/simulate`.

Errors:
- 404: `DATASET_NOT_FOUND`
- 422: `MALFORMED_ORDER`, `INVALID_SLOT_ASSIGNMENT`

## GET /api/datasets/{id}/layouts

List all saved warehouse layout configurations and slot assignments for dataset `{id}`.

Response (HTTP 200):

```json
{
  "dataset_id": "ds_a1b2c3d4e5f6",
  "layouts": [
    {
      "dataset_id": "ds_a1b2c3d4e5f6",
      "layout_id": "original",
      "name": "Original Default",
      "description": "Initial layout assignment",
      "slot_assignments": {"S001": "85123A"},
      "created_at": "2026-10-22T10:00:00Z"
    }
  ]
}
```

## POST /api/datasets/{id}/layouts

Save a customized layout or slot-to-SKU assignment permutation.

Request:

```json
{
  "layout_id": "player-experiment-1",
  "name": "Fast Movers Near Dock",
  "description": "High pick frequency items assigned to closest access cells",
  "slot_assignments": {"S001": "85123A"}
}
```

Response (HTTP 201):

```json
{
  "dataset_id": "ds_a1b2c3d4e5f6",
  "layout_id": "player-experiment-1",
  "name": "Fast Movers Near Dock",
  "description": "High pick frequency items assigned to closest access cells",
  "slot_assignments": {"S001": "85123A"},
  "created_at": "2026-10-22T10:15:00Z"
}
```

Errors:
- 404: `DATASET_NOT_FOUND`
- 422: `INVALID_SLOT_ASSIGNMENT`

## POST /api/analyze — optional P1

Request: `{"question":"Top 5 products by net revenue?"}`.

```json
{"status":"answered","answer":"...","sql":"SELECT ...","columns":["stock_code","revenue_gbp"],"rows":[],"highlight_skus":[],"assumptions":[],"limited":false}
```

Rows are arrays matching column order. Money is GBP. `status` is `answered`, `clarify`, or `unavailable`. Non-answered responses retain the same fields (`sql:null`, empty columns/rows); `clarify` adds `clarification_question`. `answer` explains unavailable features. Guided SQL templates are an acceptable disclosed fallback. Show executed SQL and cleaning assumptions. No `/api/analytics/query` alias is required.

Use read-only DuckDB, SQL AST validation plus table/function allowlists, no external access or filesystem/network SQL functions, one SELECT/CTE statement only, bounded rows (100) and runtime. No DDL/DML/ATTACH/COPY/PRAGMA, arbitrary SQL execution, or browser keys.

## Failures and integration

The API uses standardized structured error payloads matching `ErrorResponse`:

```json
{
  "detail": {
    "code": "MISSING_REQUIRED_COLUMNS",
    "message": "Workbook is missing required column: date",
    "details": {
      "missing": ["date"],
      "detected": {
        "invoice": "Invoice",
        "sku": "StockCode",
        "quantity": "Quantity"
      }
    }
  }
}
```

Legacy string detail payloads `{"detail": "human-readable reason"}` are accepted and supported for backwards compatibility.

### Stable Error Codes

| Error Code | HTTP Status | Description |
|:---|:---|:---|
| `UNSUPPORTED_FILE_TYPE` | 400 / 422 | Uploaded file is not `.csv`, `.xlsx`, or `.xls` |
| `FILE_TOO_LARGE` | 413 | Uploaded file exceeds configured limit (e.g. 50MB) |
| `EMPTY_FILE` | 400 / 422 | Uploaded file has 0 bytes |
| `MISSING_REQUIRED_COLUMNS` | 422 | File is missing one or more required columns (`invoice`, `sku`, `quantity`, `date`) |
| `NO_DATA_IN_MONTH` | 422 | Specified `target_month` contains zero valid order lines |
| `DATASET_NOT_FOUND` | 404 | Dataset identifier was not found in session cache or storage |
| `MALFORMED_ORDER` | 422 | Order contains unmapped SKUs or invalid quantities |
| `INVALID_SLOT_ASSIGNMENT` | 422 | Slot mapping is not a complete 1:1 permutation of valid SKUs and slots |

Never return partial or invented metrics for invalid assignments/unreachable routes. Use 503 with a reason if required data is not ready; `/health` may still succeed. Unknown endpoints use 404. Frontend checks HTTP status before parsing success payloads.

AGY tests determinism, all route cells/edges, dock return, mapping validation, cancellation/non-product filters, baseline placement, distance/time formulas, and optional SQL safety. Codex reviews and runs relevant checks before squash merge; AGY never merges or pushes to main.
