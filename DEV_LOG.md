# Development Log: Technical Decisions and AI Assistance

This file records the project's technical stack, durable decisions, AI assistance, and approaches considered and rejected. It is not a completion ledger; current state and remaining work are in [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md). Do not add unverified test results, data metrics, or timestamps here.

## Technology stack

- **Frontend:** React 19, TypeScript, Vite 7, Three.js, React Three Fiber, and Drei. CSS supplies the dashboard layout and styling. Warehouse racks, cartons, picker, and floor are built from original simple meshes.
- **Backend:** Python, FastAPI, Pydantic, pandas; DuckDB/SQLGlot are reserved for optional analytics and are not part of the current PS 4.2 completion path.
- **Data:** UCI Online Retail II, June 2011 preview. Full workbook downloaded and inspected; source workbook hashes and preprocessing counts for the preview are in `frontend/public/demo-provenance.json`.
- **Hosting:** Cloudflare Pages Direct Upload for the static frontend. No public API service is currently configured.
- **Shared interface:** `contracts/api.md` is the schema authority for `/health`, `/api/demo`, `/api/warehouse`, `/api/orders`, and `/api/simulate`.

## Decisions

- PS 4.2 is the submission target. PS 1.2-style text-to-SQL, multiple pickers, congestion, batching, and leaderboards are deferred until every PS 4.2 requirement works.
- Use one complete calendar month from the 2010–2011 UCI workbook. Remove cancelled invoices, non-positive quantities, blank stock codes, and known service/non-product codes before measuring picking-line frequency. Missing customer IDs remain valid picking records; customer IDs are excluded from the public preview.
- UCI supplies transactions, not warehouse topology. Rack and aisle placement, grid cell size, walking speed, and handling time are documented simulation assumptions.
- Keep slot IDs tied to fixed geometry and change only SKU assignments. A player assignment must be a complete SKU permutation.
- Compare original, fast-mover baseline, and player layouts against the same ordered invoice IDs, warehouse graph, route algorithm, picker speed, and handling-time rule. A static JSON preview cannot claim route metrics or savings.
- Use deterministic cardinal-cell BFS; each order route starts at and returns to the packing dock. The frontend animates returned route waypoints rather than inventing a straight-line path.
- Codex owns frontend, shared contract, root documentation, deployment, PR review, and merge authority. AGY owns backend, tests, and preprocessing scripts. AGY submits milestone branches by PR; it does not merge to `main`.
- Keep Cloudflare Pages as a static deployment. The API needs a separate Python-capable host; the Pages frontend may only enable scoring once its public API origin and CORS are verified.

## AI assistance

- **Codex:** repository setup, API contract, integration/review, original frontend implementation, UCI preview export and provenance, Cloudflare Pages setup/deployment, and this documentation. Exact model identity for all Codex turns is not asserted.
- **Sol Medium (gpt-6-sol):** frontend scene architecture and operations-interface implementation in the explicitly scoped frontend work. Codex reviewed and integrated its changes.
- **Antigravity (AGY):** FastAPI contract scaffold, deterministic routing/simulation scaffold, and backend tests were delivered in PR #3 and merged by Codex. The actual model used during AGY execution was not independently verified.
- **Reference inspection:** WareTwin and 3D Express Warehouse source and MIT licenses were reviewed in temporary research clones. The SI Storage showcase and other cited visual references were inspected as described in `THIRD_PARTY_NOTICES.md`. No reference code or assets were copied into the application.
- AI-generated changes were reviewed and integrated by the repository owner. Team members remain responsible for understanding the final implementation.

## Rejected and deferred approaches

- **Claiming performance from the static preview:** rejected because order data alone does not provide route simulation results. No savings are displayed without valid backend responses.
- **Presenting generated fixture metrics as real UCI results:** rejected. The current backend fixture is synthetic and must stay labeled as such.
- **Straight-line picker interpolation:** rejected because it can cut through rack cells. The picker follows backend-provided cardinal aisle waypoints.
- **Adding SQL/chat analytics before the core game works:** deferred to protect time for the three mandatory PS 4.2 requirements.
- **Copying code or assets from reference projects:** rejected for this implementation; original primitives keep licensing and asset integration simple.
- **Deploying the Python API as a static Pages asset:** rejected because static Pages does not execute this FastAPI service. Choose and verify a Python-capable host for the API before connecting the public frontend.
- **Treating Cloudflare Direct Upload Pages as Git-backed deployment:** rejected because this project was created for Direct Upload. A future Git-integrated Pages project would need a separate project configuration.

## Technical caveats

- The checked-in real-data preview and the current one-product synthetic backend fixture have different dataset identities; the frontend correctly leaves comparison unscored until they are replaced by a matching real-data API response.
- No public backend, real-data simulation metrics, recording, pitch deck, or social-post links are verified yet. See [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md).
