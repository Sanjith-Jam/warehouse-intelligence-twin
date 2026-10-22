# Current Status

**Target:** NEXAI PS 4.2 — Warehouse Digital Twin. **Repository:** https://github.com/Sanjith-Jam/warehouse-intelligence-twin. **Pages:** https://warehouse-intelligence-twin.pages.dev. **Latest verified Pages release:** https://4dd24bfe.warehouse-intelligence-twin.pages.dev.

## Delivered

- The frontend uses the actual UCI Online Retail II June 2011 snapshot: 100 products and 20 deterministic orders with public provenance.
- The backend loads the matching real-data snapshot and returns deterministic aisle-respecting simulation routes for original, fast-mover baseline, and player layouts. The selected orders are the same across policies.
- AGY's real-data milestone PR #6 and end-to-end Pages integration PR #8 are merged. Integration commit is `a3f7d0a`; Codex's documentation/handoff commits are `293e565` and `3020327`.
- Codex redeployed the current frontend build after updating shared data provenance. Production and deployment URLs return HTTP 200; the production bundle includes the active API origin and the current provenance text.
- Current verification of the live service: `/health` HTTP 200; `/api/demo` returns `real_order_data=true`, 100 products, 100 slots and 20 orders; original/baseline/player simulations all returned matching dataset/order counts; browser-style CORS preflight from Pages returned 200. Results were original 2,844.0 m / 3,470.0 s, baseline 2,820.0 m / 3,450.0 s, and player-original assignment 2,844.0 m / 3,470.0 s. Layout, speed, and handling remain assumptions.
- Current local checks: frontend unit tests 3/3 pass; Vite/TypeScript build succeeds (595 modules, 1,176 kB minified JS with the existing chunk-size warning); backend pytest 14/14 passes (one Starlette/httpx deprecation warning).

## Availability and remaining work

- The Pages frontend is public. Its backend URL is a Cloudflare Quick Tunnel that relies on running local `uvicorn` and `cloudflared` processes. Those processes were alive at the latest check, but their hostname and uptime are not durable.
- `scripts/preprocess_retail.py` currently has a machine-specific default workbook path; use `--input` explicitly or fix portability before treating the default command as reproducible on another checkout.
- Final human team roster, demo recording, pitch deck, and LinkedIn/X post links are not in the repository.
- Optional text-to-SQL and stretch goals are deferred.

Follow [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md). Codex retains frontend and Git merge authority; AGY remains the backend/data owner and should use small PRs for remaining backend work.
