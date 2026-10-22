# Remaining Implementation Plan and AGY Handoff

The current public site is a static, unscored real-data preview. The frontend is in place; the main remaining work is the authoritative real-data backend and matching end-to-end replay. PS 4.2 completion requires every P0 gate below. Keep PS 1.2 analytics and visual stretch goals out of scope until then.

## Current verified boundary

- Production frontend: [https://warehouse-intelligence-twin.pages.dev](https://warehouse-intelligence-twin.pages.dev). It serves `frontend/public/demo.json`, a June 2011 preview containing 100 real products and 20 selected real invoices.
- The preview is inspectable but does not produce scored route metrics.
- Main contains PR #3's tested FastAPI and deterministic routing scaffold, but `backend/app/data/loader.py` still selects a one-product synthetic fixture (`real_order_data:false`).
- No public FastAPI origin is configured. Do not point the live UI at a temporary tunnel or claim the static preview completes PS 4.2.
- No open PR was present at the latest repository check. AGY should branch from the current `main` and open milestone PRs; Codex remains the only merge authority.

## P0 — AGY backend milestones

### 1. Reproducible one-month preprocessing and API data loader

**Owner:** AGY. **Suggested branch:** `agy/02-orders-data`.

- Select and document June 2011 from the UCI 2010–2011 worksheet. Normalize the workbook's columns and parse dates consistently.
- Exclude invoice IDs beginning with `C` (case-insensitive), non-positive/missing quantities, blank stock codes, and documented non-product/service codes before counting picks. Retain missing customer IDs for picking; never publish customer identifiers.
- Rank 100 SKUs by positive retained picking-line count (not quantity units). Create deterministic selected orders, drop orders empty after filtering, and preserve the entire month's computed product frequencies for baseline slotting.
- Export/API `meta`, the fixed 21×21 aisle layout, all SKU/slot assignments, and 10–30 selected orders under one stable `dataset_id`. Ensure the API and static preview use the same snapshot identity or replace the static file with the authoritative API export.
- Include source URL, CC BY 4.0 attribution, selected month/sheet, source hash, filters, row counts, and reproducible command in backend provenance/README.
- **Acceptance:** rerunning the command on the same source produces identical output and dataset ID; cancellation/service-code tests pass; 100 SKUs map bijectively to reachable slots; `GET /api/demo`, `/api/warehouse`, and `/api/orders` return the documented matching snapshot; tests verify counts from the actual source.
- **PR report:** commit SHA, PR URL, command, exact tests/counts, source hash, dataset ID, and any contract request. Do not edit frontend or shared contract silently.

### 2. Real-order routing and three-policy comparison

**Owner:** AGY. **Suggested branch:** `agy/03-path-and-slotting` after milestone 1 merges.

- Connect current deterministic BFS/router to the loaded real data. Keep original, frequency-ranked fast-mover baseline, and complete player permutation policies.
- Replay the exact same ordered invoice IDs, routes, speed, grid, and handling-time rule for each policy. Every route follows cardinal walkable cells, visits each line, and returns to dock.
- Preserve the API's dataset ID and response shape. Return 422 for invalid mappings/input and never return partial or invented metrics.
- **Acceptance:** meaningful tests cover cancellation filtering, baseline ordering and ties, path adjacency/walkability, dock return, deterministic output, identical order selection, assignment validation, distance and handling-time formulas, and the 100-SKU case. A comparison on real orders returns matching dataset IDs and order counts for all three policies.
- No savings claim until a real API result has been independently reproduced from the same data snapshot.

### 3. PR discipline and status

**Owner:** AGY delivers; Codex integrates.

- Create a fresh branch from latest `main` per independent milestone. Keep the first data PR small and merge before building dependent real-simulation work; do not create overlapping PRs.
- Update `STATUS.md` in each PR or include the exact status entry in the PR description. Keep this implementation plan current when scope or blockers change.
- Codex reviews every diff for contract compatibility, runs appropriate checks, and squash-merges only safe changes. AGY never pushes to or merges `main`.

## P0 — Codex integration and public runtime

### 4. Connect frontend to the matching real API

**Owner:** Codex after milestones 1 and 2 merge.

- Check the backend snapshot against `frontend/public/demo-provenance.json`; update/remove the static preview if its source data, product mapping, geometry, order selection, or dataset ID diverges.
- Configure `VITE_API_BASE_URL` at build time and backend CORS for the exact Pages origin. Remove the local preview/scoring gate only when the frontend receives a valid matching real-data bootstrap and three valid simulation responses.
- Verify the UI uses identical order IDs and speed for all three policies, renders returned routes/visits, and invalidates results after a player layout change.

### 5. Deploy and verify the API

**Owner:** AGY supplies a deployable Python service; Codex provisions/deploys after integration.

- Select a currently available Python-capable host appropriate for the event. Verify its free-plan limits and persistence/sleep behavior before choosing; Cloudflare Pages is static and does not host this FastAPI app as-is.
- Keep credentials in host secrets/environment variables. Configure Pages only with the public API origin, never a secret.
- Test production `/health`, `/api/demo`, `/api/orders`, and all three `/api/simulate` policies from the deployed Pages origin. Confirm CORS, snapshot consistency, and browser playback.
- Record both public URLs, deployment revision, and verification outcome in README and STATUS. If no durable free API host can be used, document the approved local-demo setup and demonstrate it locally; do not expose a temporary tunnel as a stable service.

## P1 — Submission preparation after P0

- Capture one honest before/after result from the deployed real-data simulation; state that layout and walking-time inputs are assumptions.
- Add the team roster (all human member names/handles), demo recording (up to five minutes), PowerPoint pitch deck, and LinkedIn/X post URLs with `#NEXAI2026` to README after they exist.
- Run final frontend/backend checks and a short production demo checklist; record exact commands and outcomes. Never fill missing evidence with estimates.
- Optional SQL analytics, multiple pickers, congestion, batching, heatmaps, and leaderboards remain deferred.

## AGY start instructions

Clone the canonical public repository, read `AGENTS.md`, `contracts/api.md`, `PROJECT_CONTEXT.md`, `RESEARCH_REPOS_AND_IDEAS.md`, `WORK_PLAN_3H.md`, this plan, and `DEV_LOG.md`. Start at the current `main` with `agy/02-orders-data`, deliver the reproducible real-data loader as a focused PR, and report the branch, SHA, PR, tests, source hash/counts, and blockers. Ask Codex for any required contract change before implementing it.
