# Remaining Work and AGY Handoff

The mandatory PS 4.2 implementation is now on `main`: real UCI preprocessing, a 100-SKU/20-order snapshot, aisle routing, and original/baseline/player scoring. The frontend and API are connected on the live Pages deployment. Follow-up work is about reliable availability, reproducibility from a clean checkout, and submission packaging.

## Current verified state

- **Frontend:** https://warehouse-intelligence-twin.pages.dev
- **Latest release:** https://2b7a47d7.warehouse-intelligence-twin.pages.dev
- **Durable API origin:** https://warehouse-intelligence-twin-api.warehouse-intelligence-twin-frontend.workers.dev
- The API responds via a durable Cloudflare Workers VPC Gateway backed by a dedicated Cloudflare Named Tunnel (`wit-backend`). Survives clean process restarts without changing URLs; no dependency on ephemeral Quick Tunnels remains.
- Verified live simulation on 20 June 2011 invoices, 1.2 m/s, 10 seconds per retained order line, and the synthetic 21×21 layout:
  - Original: 2,844.0 m and 3,470.0 s.
  - Fast-mover baseline: 2,820.0 m and 3,450.0 s.
  - Player with original assignment: 2,844.0 m and 3,470.0 s.
- CORS preflight from the Pages origin returned 200. Live API responses carried the same dataset ID and 20 order routes for all three policies.
- PRs #6, #8, #10, #11, and #12 are merged into `main`.

## P0 — Stabilize and make the backend reproducible (COMPLETED)

### AGY: portable preprocessing invocation — COMPLETED
- Delivered in PR #12: `scripts/preprocess_retail.py` resolves `--input`, `UCI_DATASET_PATH`, or standard candidate paths, with strict checksum validation and `--allow-hash-mismatch` override.
- Automated tests in `tests/test_preprocess.py` (22/22 pytest passing) assert byte-for-byte identity between backend and frontend `demo.json` and `demo-provenance.json`, as well as full reproduction against the source workbook.
- Reproduction documentation and invariants published in `docs/DATA_REPRODUCIBILITY.md`.

### AGY + Codex: durable public API — COMPLETED
- Delivered in PR #11: Permanent stable origin at `https://warehouse-intelligence-twin-api.warehouse-intelligence-twin-frontend.workers.dev` via Cloudflare Workers VPC Gateway and Named Tunnel on operator account.
- Multi-platform deployment configurations added: `Dockerfile`, `Procfile`, `render.yaml`, `requirements.txt`, and `backend/DEPLOYMENT.md`.
- Pages frontend rebuilt (`index-Cu3St36S.js`) and deployed with the durable origin. Controlled backend restart tested and verified.

## P1 — Submission package

- Add all human team members' names and public handles. Only the repository owner identity was supplied in the project files; do not infer teammates from agent names.
- Record a demo of up to five minutes showing the 3D floor, product-slot swaps, identical-order replay, and measured results. State synthetic geometry/speed/handling assumptions.
- Create the PowerPoint pitch deck and add its repository path/link.
- Publish the required LinkedIn and X posts with `#NEXAI2026`, repository URL, deployment URL, and teammates; add the post URLs after publication.
- Run final frontend/backend checks and a browser smoke test against the durable production API. Record exact commands/results in `STATUS.md`.

## Deferred

Text-to-SQL analytics, multiple pickers, congestion, batching, heatmaps, leaderboard, and advanced visual effects remain out of scope until the stable deployed PS 4.2 demo and required submission assets are ready.

## AGY handoff instructions

AGY owns `backend/`, `tests/`, and preprocessing scripts; Codex owns `frontend/`, `contracts/`, deployment, and all merges. Read `AGENTS.md`, `contracts/api.md`, and `DEV_LOG.md`, then take the portable-preprocessing and backend deployment-readiness tasks above as focused PRs. Report branch, commit SHA, PR URL, exact tests and blockers in each PR; never push directly to `main`.

**GitHub handoff:** [Issue #9 — portable preprocessing and stable backend](https://github.com/Sanjith-Jam/warehouse-intelligence-twin/issues/9).
