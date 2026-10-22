# Warehouse Intelligence Twin — Full Project Context

> NEXAI 2026 hackathon · selected primary problem **4.2 Warehouse Digital Twin: 3D Picking Floor Game** · combined inspiration **1.2 Ask-Your-Data Sales Agent** · **no hardware** · **3-hour sprint**.
>
> Read this together with [`AGENTS.md`](./AGENTS.md), [`WORK_PLAN_3H.md`](./WORK_PLAN_3H.md), and [`RESEARCH_REPOS_AND_IDEAS.md`](./RESEARCH_REPOS_AND_IDEAS.md).

## 0. Hard decisions

- **Product name:** Warehouse Intelligence Twin (working name).
- **Chosen statement for submission:** PS 4.2. PS 1.2 provides the integrated conversational analytics feature; do not claim full compliance with PS 1.2 unless its separate mandatory dataset rules, SQL display, ambiguity handling, and 10-question trap suite all pass.
- **Hardware:** NO RFID, ESP32, QR scanning, sensors, or camera integrations. Remove hardware tasks entirely.
- **Stack: Option A — Lean Full-Stack:** React + Vite + TypeScript + React Three Fiber + Drei + Zustand + Tailwind CSS; Python FastAPI + pandas + DuckDB; simple BFS/A* on a warehouse walkability grid; SQLGlot for query inspection; optional LLM behind server-only endpoint. Charts via Recharts or small hand-built KPI panels.
- **Model delegation:** Sol Medium = 3D/frontend; Luna = backend data, analytics, SQL, simulation; keep low-cost coordinator for integration. Follow `AGENTS.md` if model identifiers differ in the runner.
- **Absolute priority:** Working, publicly accessible PS 4.2 demo with real orders and **correct before/after comparisons**. A decorative 3D scene plus a disconnected chatbox is not success.
- **Timebox:** 180 minutes **from execution start**, not a 12-hour roadmap. If started around 10:20 IST on 22 October 2026, target completion around 13:20 IST, before the afternoon submission window. Adjust clock to actual start.

## 1. Official challenge requirements

Source: uploaded `NEXAI_2026_Hackathon_Problem_Statements_v1.pdf`, PS 4.2 (page 13) and PS 1.2 (page 4); uploaded `NEXAI_2026_Hackathon_Instructions_v1.pdf`.

### PS 4.2 — all three mandatory deliverables (P0)

1. Preprocess **one month** of UCI Online Retail II real order lines into product pick frequencies and an order list, with around **100 top products**. Keep cancellations and non-product lines out of picking frequency.
2. Browser **3D warehouse grid** with racks, walkable aisles, dock, and **at least one animated picker**. Replay actual order lines; picker moves along walkable aisle paths (NOT through racks) and show live distance and elapsed picking time.
3. **Interactive slotting game**: user swaps / drags SKUs between shelf slots, then **replays the exact same order set**. Compare original arrangement vs automatic **fast-movers-near-dock baseline** vs player layout; show total walking distance and average pick time. Same orders, speed, pathfinder, aisle map, and scoring conventions in every comparison.

### PS 1.2 — optional secondary feature (P1)

- Use the same retail data in DuckDB or SQLite. Show explicit data-cleaning and metrics rules (cancelled invoices, negative quantities/returns, non-product codes, missing customer IDs).
- Natural-language questions -> generated SQL -> validate -> execute **read-only** -> return result **with SQL visible**. Retry on execution failure when feasible. Clarify ambiguous questions instead of guessing.
- Full PS 1.2 claims require a **team-authored 10-question trap suite**, including **at least five** involving cancellations, returns or ambiguity, with expected answers from handwritten SQL and a visible pass/fail interface.
- If only a few deterministic supported queries ship, label it **guided analytics / query prototype**, not a general-purpose agent or full PS 1.2.

### Hackathon submission / ethics

- Public GitHub repository created after kickoff; commit progress **at least hourly**; preserve evidence of actual development. Avoid a suspicious bulk commit. Framework starters, open-source libraries, and AI coding tools are allowed but **declare and attribute** them.
- Public app URL; otherwise follow stated local-demo exception with a demo video, when applicable. README covers problem, solution, architecture, stack, setup, URL, dataset and license, member roles and optional DEV_LOG.md.
- Final deliverables: public repo, app URL/local exception, **up-to-5-minute demo video**, **PowerPoint deck**, LinkedIn and X post URLs. Hashtag #NEXAI2026. Demo slot: five minutes + three minutes Q&A.
- Instructions conflict slightly on phrasing: page 1 says submission at about 3:30 PM onwards; page 2 says submit from 3:00 PM onwards on 22 Oct. **Treat 3:00 PM IST as the safer cutoff unless organizers clarify.**
- Do not fabricate measurements, write hidden data to public repos, or pretend model responses are verified outcomes.

## 2. One-sentence pitch

> An interactive 3D warehouse that replays real retail orders, lets managers compete against optimized inventory layouts, and answers grounded operational questions with transparent SQL and spatial highlights.

## 3. User experience, not just screens

1. Landing dashboard: compact KPIs (orders replayed, SKUs, distance, estimated pick time), dataset provenance tag, *simulation* tag, buttons to replay/compare.
2. Hero 3D scene: orbit controls, view presets (isometric/top), readable color-coded racks, dock, animated human picker or simple proxy, yellow/highlighted route line, current SKU and current order. Prefer smooth rendering over realistic models.
3. Side rail: **Products / Orders / Analytics**. Click a SKU to highlight its bin; hover a slot for its stock code and demand class. Search SKU.
4. Game: select two occupied slots and swap, or drag/drop if it works reliably; show diff and **Replay & Compare** action. Fast-movers-near-dock automatic baseline button.
5. Comparison: current vs baseline vs player distances and estimated times. Never invent percentage reductions: compute after path replay.
6. Analytics: type natural language question; show a short answer, executed SQL, result table, and optional highlights in 3D. Fail safely if API key absent; predefined SQL questions are a disclosed fallback.

## 4. Dataset: precise handling and limitations

**UCI Online Retail II:** https://archive.ics.uci.edu/dataset/502/online+retail+ii. Official citation: Chen, D. (2012), *Online Retail II*, UCI Machine Learning Repository, https://doi.org/10.24432/C5CG6D. License **CC BY 4.0**. Dataset has 1,067,371 transactions from Dec 2009 through Dec 2011; source workbook approx 43.5 MB.

Input variants may use `Invoice`/`Price`/`Customer ID` instead of `InvoiceNo`/`UnitPrice`/`CustomerID`. Normalize field names first. Select one complete calendar month from 2010–2011 sheet, record exact UTC/local assumption and sheet/month in metadata.

**Canonical data rules:**

- Detect `InvoiceNo` starting with `C` (case-insensitive) as cancellation. Exclude cancellations and `Quantity <= 0` from picking replay. Preserve returns/cancellations in an analytics view for correct net/gross comparisons.
- Exclude null/blank `StockCode`; drop non-product service codes (e.g., `POST`, `DOT`, `M`, `D`, `BANK CHARGES`, `AMAZONFEE`) from the picking SKU ranking using a documented exclusion list. Don't silently delete them from finance accounting.
- Missing `CustomerID`: keep order lines for picking; exclude only from distinct-customer calculations if necessary. Currency is **GBP**, not INR.
- Choose top ~100 SKUs by a defined metric: ideally **number of picking order lines** or distinct invoices (record which). Do not confuse sold units with picking frequency.
- Order replay uses actual UCI orders; warehouse geometry, storage positions, picking speed, time per pick, and travel times are **synthetic assumptions**, explicitly displayed.
- For performance, export one-month/100-SKU preprocessed `orders.json` and `products.json` or a compact DuckDB database. Browser receives only a small chosen subset of orders (e.g. 10–30 for quick animation) but backend supports replay across the selected month.

## 5. Key architecture boundaries

```
Real UCI workbook / licensed data
             |
             v
Luna data pipeline --> Parquet/DuckDB + compact demo JSON
             |                              |
             v                              v
Luna deterministic routing/simulation  --> FastAPI /api/*
             |                              |
             +----- layout / route JSON ---+
                                            |
                                     Sol React app
                                  (R3F 3D + Zustand)
                                            |
       question --> Luna SQL tool (read-only) + validated result
                                            |
                               chart + highlighted slot IDs
```

**Rule:** Simulation engine owns authoritative distance, time, order and slot mapping logic. Frontend **only animates** returned waypoints and displays backend KPIs. It does not calculate a different distance secretly. For first-hour prototyping, frontend may use sample JSON conforming to API contract; remove or label it before final demo.

### Minimum stable coordinate conventions

- Floor is an X/Z plane; Y = vertical height. Dock origin `x=0,z=0` (or documented single alternative). Grid cells represent `cell_size_m` (e.g. 1.5m). Racks occupy impassable cells; aisles are graph nodes.
- Each slot has stable `slot_id`, `grid_x`, `grid_z`, `sku`, `pick_access_cell`. The picker navigates to `pick_access_cell`, not through the rack cell. `sku` is not the slot ID; swapping products changes SKU placement, not warehouse geometry.
- `order_ids` and picked line IDs must be stable, so the **same fixed order snapshot** can be replayed for all layouts.

### Shared FastAPI contract (freeze at T+10 minutes)

`GET /api/demo` returns one lightweight object, for example:

```json
{
  "meta": {"source": "UCI Online Retail II", "month": "2011-06", "real_order_data": true,
           "synthetic_warehouse": true, "cell_size_m": 1.5},
  "layout": {"layout_id": "original", "width": 20, "height": 16,
             "walkable_cells": [[0,0],[1,0]],
             "dock": [0,0],
             "slots": [{"slot_id":"S001","rack_cell":[5,4],"access_cell":[5,3],"sku":"85123A"}]},
  "products": [{"sku":"85123A","name":"Product title","pick_frequency":93}],
  "orders": [{"order_id":"INV-001","lines":[{"sku":"85123A","quantity":2}]}]
}
```

`POST /api/simulate` request:

```json
{
  "order_ids": ["INV-001"],
  "slot_assignments": {"S001":"85123A"},
  "policy": "player",
  "speed_mps": 1.2
}
```

response:

```json
{
  "policy":"player", "orders_replayed":1,
  "distance_m": 43.5, "estimated_pick_time_s": 46.25,
  "average_pick_time_s": 46.25,
  "routes":[{"order_id":"INV-001", "waypoints":[[0,0],[1,0],[2,0]],
             "visits":[{"sku":"85123A","slot_id":"S001","waypoint_index":2}]}],
  "warnings":[], "assumptions":{"speed_mps":1.2,"handling_seconds_per_line":10}
}
```

Numbers above are **schema illustrations, not computed results**. Backend also supports `policy: "original"` and `policy: "baseline"` with server-defined assignments, ignoring arbitrary client overrides for those modes.

`POST /api/analyze` request `{ "question": "Top 5 products by net revenue?" }`; response includes:

```json
{
  "status":"answered",
  "answer":"...",
  "sql":"SELECT ...",
  "columns":["stock_code","revenue_gbp"],
  "rows":[], "highlight_skus":[], "assumptions":[], "limited":false
}
```

Return `status: "clarify"` + `clarification_question` on ambiguous requests, or `status: "unavailable"` with honest reason when no SQL/LLM access. Do not let user-supplied text trigger any filesystem, network, DDL or DML operations. Provide `/health` for deployment.

### SQL safety

- Use a **read-only DuckDB connection** with permissions limited to local shipped analytical data.
- Parse SQL using SQLGlot; require a single safe SELECT/CTE query; reject writes/DDL/ATTACH/COPY/PRAGMA, unsafe functions, external file/network access and multi-statements. SQLGlot parsing alone is **not** sufficient isolation.
- Schema/table allowlist, row cap (e.g., 100), query runtime budget, small LLM input/output budget, truncate results with a disclosure. Never expose API keys to browser.
- Define `gross_sales_gbp`, `net_sales_gbp`, `cancelled_units`, `returns`, and `unique_customers` consistently. For ambiguous phrases ask a question instead of inventing a metric.
- Any JSON code example is contract-level: edit together on both sides if contract changes, update this file immediately.

## 6. What NOT to build in three hours

- Multi-agent autonomous warehouse robots, ROS, collision physics, reinforcement learning, heavy model training, VLM/camera, inventory forecasting, user login, multiplayer, real WMS integration, OCR, complex authentication, three different backends, voice or hardware.
- Do not let LLM invent route costs. Simple ABC/velocity ordering, SKU co-occurrence as a *possible idea*, and A*/BFS/aisle graph are sufficient algorithms. No ML training is required for PS 4.2.
- Avoid lifting an entire complicated repo as the new project; study source, selectively transplant permitted scene primitives, and keep own simulation/data ownership.

## 7. Definition of done

**Core P0 (required):** real-month orders processed; ~100 products; one navigable smooth 3D warehouse; animated picker following valid aisles; live counters; user slot swapping; automatic fast-mover baseline; same orders replay; three honest KPI comparisons; README; usable app URL.

**P1 (if time):** 2–5 grounded SQL analytics examples with actual executed SQL and linked 3D highlights. **P1-complete** only with genuinely generalized validated agent and 10 trap tests as PS 1.2 specifies.

**Documentation:** proper citation/attribution, original-vs-simulated distinction, known limitations, DEV_LOG, source references, public repo/deploy/demo/pitch checklist.

## 8. Links and origin notes

- Rules: the two uploaded PDFs, which take precedence over this plan.
- UCI data: https://archive.ics.uci.edu/dataset/502/online+retail+ii
- WareTwin original: https://github.com/WayneChou-bot/WareTwin (MIT; original attribution in LICENSE).
- Related WareTwin repository: https://github.com/DoanNguyenTrong/waretwin (MIT, same project family; do not copy both blindly).
- 3D Express Warehouse: https://github.com/jiaxiantao/3d-express-warehouse (MIT).
- SI Storage showcase: https://devpost.com/software/si-storage — its linked https://github.com/Tommy-Ren/SI-Storage returned 404 when checked on 22 Oct 2026. **Do not tell agents to clone it or claim its source is available.** Use Devpost screenshots/write-up as inspiration; contact authors only if necessary.
- All further references in [`RESEARCH_REPOS_AND_IDEAS.md`](./RESEARCH_REPOS_AND_IDEAS.md).
