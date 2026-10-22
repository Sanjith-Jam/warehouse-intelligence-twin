# Current Status

**Target:** NEXAI PS 4.2 — Warehouse Digital Twin. **Repository:** https://github.com/Sanjith-Jam/warehouse-intelligence-twin. **Pages:** https://warehouse-intelligence-twin.pages.dev. **Latest verified Pages release:** https://2b7a47d7.warehouse-intelligence-twin.pages.dev.

## Delivered

- The frontend uses the actual UCI Online Retail II June 2011 snapshot: 100 products and 20 deterministic orders with public provenance.
- The backend loads the matching real-data snapshot and returns deterministic aisle-respecting simulation routes for original, fast-mover baseline, and player layouts. The selected orders are the same across policies.
- Durable public backend origin is live at `https://warehouse-intelligence-twin-api.warehouse-intelligence-twin-frontend.workers.dev` backed by Cloudflare Named Tunnel (`wit-backend`) and Cloudflare Workers VPC Gateway (`wit-api-service`).
- Production Pages deployment (`index-Cu3St36S.js`) is connected to the durable backend origin; browser CORS verified.
- Results verified: original 2,844.0 m / 3,470.0 s, baseline 2,820.0 m / 3,450.0 s, and player-original assignment 2,844.0 m / 3,470.0 s.
- `scripts/preprocess_retail.py` is portable: searches `--input`, `UCI_DATASET_PATH`, or standard candidate paths, reporting actionable download instructions and expected SHA-256 (`bcbe73b35f5b7babf197fb0cb983a11f5d9ff929078d4aa53d171b1f2df2e980`) if missing.
- Backend and frontend fixtures (`demo.json` and `demo-provenance.json`) are verified byte-identical by automated regression tests in `tests/test_preprocess.py`.

## Availability and remaining work

- The durable public backend is live and connected to production Pages. Survives controlled process restarts without changing URLs.
- Alternative deployment configurations provided: `Dockerfile` (Python 3.12-slim), `Procfile`, `render.yaml` for Render.com/Railway/Fly.io.
- Final human team roster, demo recording, pitch deck, and LinkedIn/X post links are not in the repository.
- Optional text-to-SQL and stretch goals are deferred.

Follow [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md). Codex retains frontend and Git merge authority; AGY remains the backend/data owner and uses small PRs for remaining backend work.

[AGY] branch=agy/durable-backend status=done files=Dockerfile,Procfile,render.yaml,backend/DEPLOYMENT.md,deploy/** tests=19 passed (pytest), 3 passed (frontend) needs=merge PR #11 next=merge PR #12
