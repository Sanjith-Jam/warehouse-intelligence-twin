# Warehouse Intelligence Twin

PS 4.2: a browser warehouse picking game driven by one month of real UCI Online Retail II orders. Compare original, fast-movers-near-dock, and player layouts using exactly the same orders and aisle routing.

## Sprint handoff — current instructions

These ownership rules supersede conflicting role assignments in the four supplied planning documents, which are preserved as received. `contracts/api.md` is the authoritative API schema.

- Codex owns all `frontend/`, root configuration, `contracts/`, Git integration, and all merges to `main`.
- Antigravity (AGY) owns all `backend/`, `tests/`, and backend data-processing `scripts/`. No separate Codex backend worker will edit those paths.
- AGY clones into its own directory, branches from latest `main`, and opens small tested milestone PRs. Never push directly to `main`, merge a PR, force-push, or change frontend/contracts without agreement.
- Suggested branches: `agy/01-api-scaffold`, `agy/02-orders-data`, `agy/03-path-and-slotting`, `agy/04-analytics-sql`. Prioritize PS 4.2; analytics is optional.
- Each PR reports commit SHA, tests run, schema dependencies, and caveats. Update `STATUS.md` with milestone progress; PR comments carry integration questions. Do not assume either chat receives automatic notifications.
- Feature freeze at T+120 minutes; only blocker fixes, verification, and submission preparation after T+150.

## Start AGY now

```sh
git clone https://github.com/Sanjith-Jam/warehouse-intelligence-twin.git
cd warehouse-intelligence-twin
git switch -c agy/01-api-scaffold
```

Read the four supplied project Markdown files and `contracts/api.md`, using the ownership overrides above. Deliver `/health` and contract-shaped API scaffolding first, then real data and routing in focused PRs. Backend development origin is `http://localhost:8000`; allow frontend development origin `http://localhost:5173` via CORS. Backend setup commands will be supplied by AGY in its first PR.

## Data and metric integrity

UCI Online Retail II: Chen, D. (2012), https://doi.org/10.24432/C5CG6D, CC BY 4.0. Preprocess one complete month, normalize workbook columns, remove cancellations and non-product codes before ranking about 100 SKUs by pick frequency. Keep actual order IDs and the same immutable replay selection across all three layouts.

Warehouse geometry, rack positions, speed, and handling times are synthetic assumptions. Routes must follow aisles and return to the dock for each order. No measured KPIs exist yet; fixtures must be clearly labeled synthetic. The implementation will document its final layout and assumptions here.

## Current state

Repository scaffold and shared contract only. Frontend and backend implementation are pending. No working demo or deployment is claimed.
