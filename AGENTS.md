# Repository Agent Instructions

Read `PROJECT_CONTEXT.md`, `RESEARCH_REPOS_AND_IDEAS.md`, `WORK_PLAN_3H.md`, `contracts/api.md`, `IMPLEMENTATION_PLAN.md`, `README.md`, and `DEV_LOG.md` before changing code. The integration and ownership rules in this file and README resolve conflicting assignments in the original sprint plan.

## Ownership

- **Codex:** sole owner of `main` merges; owns `frontend/`, root configuration/documentation, shared `contracts/`, integration, and deployment.
- **Antigravity (AGY):** owns `backend/`, `tests/`, and backend preprocessing scripts. Start from the latest `main`, implement small independent milestones on `agy/*` branches, push, and open PRs. Never push directly to or merge into `main`.
- Do not modify another owner's paths or change the API contract silently. Raise a PR comment or request agreement before changing `contracts/api.md`.

## Current priority

The mandatory PS 4.2 implementation is integrated: the API serves real June 2011 data and the Pages frontend is connected through a currently running Quick Tunnel. The tunnel is ephemeral. Prioritize portable preprocessing and a durable API origin before analytics or stretch goals. See `IMPLEMENTATION_PLAN.md` for exact handoff gates.

## PR and verification rules

- AGY opens a focused PR for each independently testable milestone and reports branch, commit SHA, PR URL, exact checks/results, contract dependencies, and blockers.
- AGY updates `STATUS.md` in its PR or supplies exact text in its PR description. Do not fabricate progress, results, metrics, or timestamps.
- Codex reviews every PR diff for API compatibility and overlap, runs relevant integration checks, and squash-merges safe changes. Failed changes remain with AGY to fix on its branch; never force-push or rewrite another agent's branch.
- Keep `DEV_LOG.md` for technical stack, decisions, AI assistance, and rejected approaches. Keep current completion evidence in `STATUS.md` and remaining tasks in `IMPLEMENTATION_PLAN.md`.

## Data, safety, and metric integrity

- Use UCI Online Retail II with attribution and CC BY 4.0. Filter cancellations, non-positive/missing quantities, and non-product codes before ranking picks. Retain missing customer IDs for picking, but do not expose customer identifiers.
- Use the same immutable order selection, layout graph, route algorithm, speed, and handling assumptions for original, baseline, and player scoring. Report only backend-computed metrics.
- Treat warehouse positions, aisle layout, cell size, walking speed, and handling time as synthetic assumptions.
- Keep credentials out of Git and browser bundles. Do not expose a temporary tunnel as a production API.
- Review source and license before reusing external code or assets; record reused material and notices in `THIRD_PARTY_NOTICES.md`.
