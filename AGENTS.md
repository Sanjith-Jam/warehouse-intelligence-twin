# AGENTS.md — Multi-agent coordination (3-hour sprint)

Read `PROJECT_CONTEXT.md`, `WORK_PLAN_3H.md`, and `RESEARCH_REPOS_AND_IDEAS.md` first. Primary deliverable is NEXAI PS 4.2, with PS 1.2-inspired read-only analytics. **No hardware.** All agents work on the **same Git repository**, not independent products. Do not assume an agent is running until its operator launches it.

## Ownership and model allocation

| Agent | Environment / model preference | Exclusive ownership | Deliverable |
|---|---|---|---|
| Sol | Main coding runner, **Sol Medium** | `frontend/src/scene/**`, 3D meshes, camera, aisle/picker animation, visual polish | Usable 3D picking game; inspect and clone licensed reference repos into temporary research directories |
| Luna | Main coding runner, **Luna** | `backend/app/data/**`, `backend/app/simulation/**` | Retail II preprocessing, reproducible order sets, deterministic aisle pathfinding, slotting baseline, metrics |
| Antigravity-A | **Claude model** if available in Antigravity Pro model picker | `backend/app/api/**`, `backend/app/analytics/**` | FastAPI contracts, DuckDB read-only analytics, SQLGlot safety; integration tests |
| Antigravity-B | **Gemini Flash** or lowest-cost suitable model | `tests/**`, `scripts/**`, docs, sample data | Smoke tests, dataset validation, API fixtures, demo checklist, deploy/build validation |
| Codex lead | Codex / Sol Medium + low-cost integration assistant | GitHub repo creation, root config, shared types/contracts, PR review and merges, deployment, deadlines | Resolve conflicts, maintain status and keep agents within budget |

If Antigravity cannot provide Claude or the desired model, **check its available model selector and use the closest available Claude model**, or explicitly report unavailability; never assume a model or plan entitlement. Gemini Flash for mechanical work; upgrade to a stronger model only for a specific blocker. Sol/Luna names refer to user-selected subagents and must be mapped to actual available model identifiers.

## Shared repository and concurrency protocol

1. **One canonical Git remote and one integration branch (`main`)**. Each agent creates a separate worktree/branch: `agent/sol-3d`, `agent/luna-sim`, `agent/agy-claude-api`, `agent/agy-flash-qa`. They may share the same repo, **not the same working directory/index**. Use `git worktree add ../wit-sol -b agent/sol-3d`, etc., from the canonical clone. Do not force-push or reset another agent's work.
2. Codex creates the public GitHub repository `warehouse-intelligence-twin`, commits the initial skeleton and **API contract** to `main` before parallel work: `GET /health`, `GET /api/warehouse`, `GET /api/orders`, `POST /api/simulate`, `POST /api/analytics/query`; response fields for geometry, products, slots, ordered path points, distance, time, comparison and SQL provenance. Agree coordinate units, order IDs, slot IDs and JSON shape in `contracts/api.md`.
3. **No simultaneous edits to the same files.** Sol owns 3D UI, Luna owns simulation/data, Antigravity Claude owns API/analytics, Antigravity Flash owns tests/docs. Shared contracts and root dependencies are Codex-only; AGY requests changes through a PR comment or status update. Agents must request contract changes in a short message, not silently change schemas.
4. Commit small, coherent changes every 20–30 minutes. Antigravity pushes small independently testable feature branches and opens PRs for every milestone; Codex reviews diffs, validates contracts and tests, then squash-merges safe PRs to `main`. Only Codex merges. Conflicts are resolved by the originating file owner. Each agent posts: branch, commit SHA, changed files, tests, blockers, next dependency.
5. Use fixture data until real data loads; no hardcoded fake KPIs presented as real. Backend and UI must agree on immutable order snapshot, layout versions and identical route scoring.
6. Never execute untrusted repository scripts, install hooks, or copy code without reviewing source and license. For references, clone into `../reference-repos/` (outside product tree), inspect `LICENSE`, `README`, file tree, and actual source. **Borrow code only where license permits**, preserve notices/attribution and record file origins in `THIRD_PARTY_NOTICES.md`. If uncertain, borrow ideas, not code. SI Storage Devpost can be visual inspiration; its previously linked GitHub repo may be unavailable, so don't block on it.

## Hard priorities and stop conditions

P0: Real one-month order preprocessing (~100 SKUs); walkable aisle-path 3D picker replay; original vs fast-mover baseline vs user slot swaps with identical orders and distance/time metrics. P1: visible read-only text-to-SQL with provenance. P2: aesthetic extras and complex agents. At 120 minutes, **freeze new features** and integrate; at 150 minutes, freeze code except blocker fixes and package/deploy. Never trade P0 for an LLM demo.

## Usage-limit discipline

- Check each provider's **actual** remaining credits, requests, tokens and context limits in its UI before dispatch. Pro plan does not imply unlimited Claude or Antigravity usage. Do not invent quota figures.
- Sol Medium is reserved for 3D architecture/complex scene bugs; Luna for simulation/data logic; Antigravity Claude for backend API/SQL safety; Gemini Flash for routine tests/docs. Avoid running multiple high-cost models on the same task.
- Before a long call: specify file scope, precise acceptance criteria, relevant contract, and max intended work. No repeated full-repo scans; use targeted searches and summarize findings in a shared `STATUS.md`.
- Cap parallel workers to the four roles above; cancel redundant/looping tasks. Stop after two failed attempts on a blocker, report the exact error, and ask coordinator to triage.
- Avoid huge context dumps: point agents to the Markdown docs, and provide concise diffs/commit summaries. Prefer deterministic tests to repeated model critique.
- Do not claim automatic coordination or autonomous agent launch. The operator must explicitly start agents and give them access to the repo/worktrees.

## Communication template

`[agent] branch=<branch> commit=<sha> status=<done|blocked> files=<paths> tests=<results> needs=<contract/dependency> next=<one action>`

## GitHub PR cadence and single merge authority (mandatory)

- **Codex alone creates the repository and owns `main`**; initial setup includes all four Markdown docs, scaffold, branch protections where permitted, and `contracts/api.md`. Codex is also frontend lead; do not wait for backend implementation after publishing contract.
- **AGY independently clones the public remote**, uses its own directory/worktree, and never works on the same checked-out branch or filesystem index as Codex. Antigravity Claude owns backend API/analytics; Flash workers own tests, fixtures, and documentation. Backend simulation/data responsibilities may be delegated to a suitable Luna agent on Codex side only if AGY does not own those same paths; **default: AGY owns all `backend/**`** to avoid conflicts.
- **AGY commits and pushes each small stable milestone and immediately opens a focused PR** (`agy/01-api-scaffold`, `agy/02-orders-data`, `agy/03-path-and-slotting`, `agy/04-analytics-sql`, `agy/05-tests`) against `main`. Prefer 15–25 minute milestones; do not open duplicate PRs or split one dependent change across conflicting PRs. Use actual time to decide; do not delay a ready PR.
- Each PR description includes **what changed, API/schema changes, tests run, known caveats, and exact review needs**. AGY must send PR URL and SHA to Codex through the available shared channel or `STATUS.md`; agents cannot automatically read each other's chats.
- **Codex polls GitHub at each handoff and milestone**, runs smoke/integration tests, requests precise corrections for failed PRs, and squash-merges acceptable PRs promptly. **AGY never merges its own PR or pushes to main.** Neither agent force-pushes nor silently edits the other's directory.
- To avoid competing branch dependencies, AGY branches from the latest `main` for each milestone; when a previous PR has not merged and the next change depends on it, continue on the same PR branch and update it rather than stack unrelated PRs unless Codex explicitly coordinates stacked PRs.
- Codex syncs frontend worktree with `main` after merges and manages deployment/submission. Minimize busy polling and costly agent turns; request a review only after actual code/test changes.
