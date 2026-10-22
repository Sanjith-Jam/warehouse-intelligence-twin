# Remaining Work and AGY Handoff

The mandatory PS 4.2 implementation is now on `main`: real UCI preprocessing, a 100-SKU/20-order snapshot, aisle routing, and original/baseline/player scoring. The frontend and API are connected on the live Pages deployment. Follow-up work is about reliable availability, reproducibility from a clean checkout, and submission packaging.

## Current verified state

- **Frontend:** https://warehouse-intelligence-twin.pages.dev
- **Latest release:** https://b4229a4a.warehouse-intelligence-twin.pages.dev
- **Current API origin:** https://interventions-stopping-fell-quiz.trycloudflare.com
- The API currently responds from the running FastAPI and `cloudflared` processes. The Quick Tunnel URL is ephemeral and tied to those processes; the app returns to its unscored real-data preview if the backend becomes unavailable.
- Verified live simulation on 20 June 2011 invoices, 1.2 m/s, 10 seconds per retained order line, and the synthetic 21×21 layout:
  - Original: 2,844.0 m and 3,470.0 s.
  - Fast-mover baseline: 2,820.0 m and 3,450.0 s.
  - Player with original assignment: 2,844.0 m and 3,470.0 s.
- CORS preflight from the Pages origin returned 200. Live API responses carried the same dataset ID and 20 order routes for all three policies.
- PRs #6 and #8 are merged. No open PR was present when the current documentation work began.

## P0 — Stabilize and make the backend reproducible

### AGY: portable preprocessing invocation

**Owner:** AGY. **Branch:** start from current `main`; use a small `agy/*` PR.

- Remove the machine-specific default path from `scripts/preprocess_retail.py`, or make the input path required with a clear error. Document the official UCI download and expected SHA-256.
- Keep the generated backend JSON and frontend JSON/provenance aligned; add a byte/data identity assertion so a future export cannot silently diverge.
- **Acceptance:** the documented invocation works from a clean checkout when given the workbook path, produces stable output and the same dataset ID, and reports accurate counts. Add or update a focused test for the path/error and determinism.

### AGY + Codex: durable public API

- **AGY:** document the service runtime requirements and any backend changes needed for a stable deployment; keep API secrets out of Git and keep frontend ownership with Codex.
- **Codex:** select a durable Python-capable host (or a named Cloudflare Tunnel with a stable hostname), verify its current free-plan/runtime limits, provision with the operator's account, configure CORS, and rebuild/redeploy Pages with that stable public origin.
- Do not treat a Cloudflare Quick Tunnel as a permanent endpoint. Keep it only as a demo bridge while the local processes are running.
- **Acceptance:** after a clean restart, public `/health`, `/api/demo`, `/api/orders`, and all three simulation policies remain reachable; dataset IDs/order IDs match; browser CORS works; Pages scene playback and score are verified. Document uptime/cold-start limitations if the chosen free host has them.

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
