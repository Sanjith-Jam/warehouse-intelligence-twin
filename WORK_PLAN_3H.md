# 3-Hour Parallel Sprint — Warehouse Intelligence Twin

**Duration:** 180 minutes from actual start. **Primary submission:** PS 4.2; PS 1.2-inspired analytics secondary. **No hardware.** All agents use one canonical Git remote with separate worktrees/branches. See `AGENTS.md` for model assignments, safety and quota management.

| Elapsed | Sol Medium — 3D frontend | Luna — data/simulation | Antigravity Claude — API/SQL | Antigravity Flash — QA/ops | Codex repo owner / PR integrator |
|---|---|---|---|---|---|
| 00–15 min | Clone/inspect WareTwin and 3D Express Warehouse in research directory; check licenses | Validate available Retail II source/CSV and choose a reproducible month | Agree API schemas and read-only analytics boundary | Scaffold smoke-test and demo checklist | Initialize canonical repo, branches/worktrees, `contracts/api.md`, fixtures |
| 15–45 min | Rack/aisle/dock scene, camera, shelf selection | Filter cancellations/returns; top ~100 SKUs; immutable order fixture; graph pathfinder | FastAPI health, warehouse/orders endpoints and simulation adapter | Test dataset counts, deterministic fixtures and endpoint shapes | Merge initial contracts, inspect UI/backend integration |
| 45–90 min | Animate picker on path points; distance/time overlay; SKU swap UI | Baseline placement, player-layout replay, distance/time scoring with same orders | `POST /api/simulate`, DuckDB loading, safe analytics query path | Route validity, collision/blocked-cell tests, SQL safety tests | Midpoint integration; resolve shape mismatches |
| 90–120 min | Baseline/player comparison UI, highlight moved slots, polish | Reproducible metrics, optimize correctness/performance | Expose SQL/result/provenance; basic NL questions only if reliable | End-to-end happy-path tests; inspect deployment | Ensure all 3 mandatory PS 4.2 requirements work |
| 120–150 min | Fix scene bugs; no new features | Fix data/route bugs; no new algorithms | Fix integration, graceful analytics fallback | Regression tests, README, attribution/license review | **Feature freeze at 120**; integrate and run full demo |
| 150–180 min | Demo visual fixes only | Metric verification only | API/deployment blocker fixes only | Build, deploy smoke test, capture checklist | **Code freeze at 150** except blockers; demo recording/submission artifacts |

## Acceptance gates

- **T+45:** Real-data parser or transparent sample fixture; warehouse scene renders; API contract is stable.
- **T+90:** At least one picker moves on walkable aisles; order and layout IDs are consistent; backend computes routes.
- **T+120:** Same orders replay across original, auto fast-mover baseline and player layouts; comparable distance/time metrics; 3D swaps function.
- **T+150:** Integrated frontend/backend builds; all P0 workflows pass; analytics panel must not block the demo.
- **T+180:** Deployable demo, repository README, short recorded walkthrough, slides and submission checklist where feasible. If official deadline arrives earlier, stop and submit the best stable build.

## Non-negotiable metric integrity

All three layout comparisons must share the same order snapshot, aisle geometry, picker speed, route policy and distance units. Retail transactions do not contain physical slot coordinates: explicitly label warehouse geometry and travel times as simulation assumptions. Cancellations and negative quantities must not inflate picking demand.

## Scope cuts in order

1. Remove voice, multiplayer, advanced visual effects and hardware (already excluded).
2. Simplify NL-to-SQL to a few validated read-only templates and always show SQL; never fabricate a successful query.
3. Keep a single animated picker; no multi-robot scheduling.
4. Keep a small fixed warehouse with 100 mapped SKUs and simple slot swaps.
5. Never cut real-order processing, aisle-respecting paths, or same-orders three-way comparison.

## Cross-agent handoffs

Sol consumes `GET /api/warehouse`, `GET /api/orders`, `POST /api/simulate`; Luna supplies deterministic simulation objects; Antigravity Claude exposes those through FastAPI; Flash tests against the contract. Codex owns repository creation, integration, shared contracts, all PR reviews and merges. AGY pushes milestone branches and opens PRs continuously. Communicate branch/commit/tests/blockers in `STATUS.md` every ~30 minutes.

## AGY pull request milestones

- ~T+15: AGY PR 1 — backend scaffold, health endpoint, API contract compliance.
- ~T+45: AGY PR 2 — dataset preprocessing, reproducible order fixtures, warehouse/orders endpoints.
- ~T+90: AGY PR 3 — aisle-respecting routes, simulation, slotting comparison.
- ~T+120: AGY PR 4 — safe read-only SQL if reliable, test coverage.
- T+120 onward: Codex merges only verified blocker fixes; no new features. AGY may push incremental fixes on an open PR.

PR times are checkpoints, not excuses to delay ready code. Codex is the **sole merge authority** and must not merge untested changes.
