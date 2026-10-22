# Development Log: Stack, Decisions, and AI Assistance

This log contains the technical stack, key decisions, AI assistance, and rejected approaches. Current delivery state, live URLs, validation evidence, and remaining tasks are maintained in [README.md](README.md), [STATUS.md](STATUS.md), and [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md). Do not treat this file as a chronological record or add unverified claims.

## Technology stack

- **Frontend:** React 19, TypeScript, Vite 7, Three.js, React Three Fiber, Drei, and CSS. Original primitive meshes are used for racks, cartons, floor, and picker.
- **Backend:** Python, FastAPI, Pydantic, and pandas. The simulation uses deterministic breadth-first search on a walkable cardinal-cell grid.
- **Data:** UCI Online Retail II, June 2011 from the 2010–2011 worksheet. The committed backend pipeline reproduces a top-100 product and deterministic 20-order snapshot. The workbook is not included in the repository.
- **Hosting:** Cloudflare Pages Direct Upload for the frontend. The current backend is exposed through a Cloudflare Quick Tunnel attached to a running local FastAPI process.
- **Shared API:** `contracts/api.md` defines `/health`, `/api/demo`, `/api/warehouse`, `/api/orders`, and `/api/simulate`.
- **Optional analytics:** DuckDB/SQLGlot text-to-SQL is deferred and not part of the current PS 4.2 implementation.

## Technical decisions

- PS 4.2 is the primary target. Complete real-data preprocessing, aisle-respecting replay, and original/baseline/player evaluation before adding PS 1.2 analytics or stretch goals.
- Filter case-insensitive cancellation invoice IDs, missing/non-positive quantities, blank stock codes, and documented service codes before ranking products. Rank by retained positive order lines, not units. Keep missing customer IDs in picking orders, but do not expose customer identifiers.
- Use a stable dataset ID, deterministic selection of 20 eligible orders, stable slot IDs, and a complete slot-to-SKU permutation for player layouts.
- UCI transactions contain no warehouse topology. The 21×21 grid, 100 rack slots, 1.5 m cell pitch, picker speed, and 10-second line handling time are explicit simulation assumptions.
- Run the same selected order IDs, warehouse geometry, routing method, speed, and handling rule for original, baseline, and player layouts. The baseline places high-frequency products in the nearest reachable slots, with deterministic tie breaks.
- Routes move between cardinally adjacent walkable cells, visit items in their retained order sequence, and return to the dock. The frontend animates returned API waypoints and validates responses before showing metrics.
- Use Cloudflare Pages for static frontend delivery. A static Pages project cannot run the Python API, so scoring requires a separate backend service/origin.
- Codex owns `main`, frontend, shared contracts, integration, deployment, and all merges. AGY owns backend, tests, and preprocessing scripts and delivers through milestone PRs.

## AI assistance

- **Codex:** repository setup, shared contract, frontend integration, review/merge, UCI preview/provenance, Pages deployment, and current documentation. Exact model identity is not asserted for every Codex turn.
- **Sol Medium (`gpt-6-sol`):** frontend scene and operations interface within the frontend ownership boundary.
- **Antigravity / AGY:** API scaffold, deterministic backend simulation, real UCI preprocessing, real-data integration, and backend tests. PR #6 was reported as Gemini Flash; PR #8 identified Claude Sonnet 4.6. The actual model used for every earlier backend change was not independently verified.
- **Reference research:** WareTwin and 3D Express Warehouse source and MIT license files were inspected; visual references were reviewed and documented in `THIRD_PARTY_NOTICES.md`. No reference code or assets were copied.
- Human contributors are responsible for understanding and reviewing all AI-assisted code. The README identifies the known repository owner; other human member details were not present in the supplied materials.

## Rejected and deferred approaches

- **Using transaction totals as walking savings:** rejected because UCI has no rack coordinates or travel distances. Only the route simulator may produce the application's walking/time metrics.
- **Showing fixture or static-preview KPIs as real results:** rejected. Simulation results must match the real dataset ID and the same orders across all policies.
- **Moving the picker in a straight line between products:** rejected because it can cross rack obstacles. Playback follows the backend's validated aisle waypoints.
- **Copying warehouse reference source or assets:** rejected; original meshes avoid provenance and license integration risk.
- **Running FastAPI on static Pages:** rejected; use a Python-capable host or an explicit tunnel with its availability limitation.
- **Starting optional SQL analytics, multi-picker congestion, batching, heatmaps, or leaderboard work before PS 4.2:** deferred to preserve scope and time.
- **Treating a Cloudflare Quick Tunnel as a durable backend address:** rejected; the current live tunnel depends on the local API and tunnel processes. A stable backend endpoint remains a deployment follow-up.
