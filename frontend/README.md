# Frontend

React, Vite, TypeScript, React Three Fiber, and Drei power the warehouse floor. The interface reads `GET /api/demo` and sends the same ordered demo IDs, speed, and copied slot mapping to three `POST /api/simulate` requests. Routes, assignments, distance, and pick times come from the API; the browser only animates returned waypoints. If the API is unavailable, the app shows the matching real-data static snapshot when available, then falls back to a clearly labeled synthetic fixture. Offline modes never display simulation scores.

```sh
cd frontend
npm ci
npm run dev
```

Run the backend at `http://localhost:8000`; Vite proxies `/api` in development. For a deployed frontend, set `VITE_API_BASE_URL` to the public backend origin (no trailing slash). Never put API secrets in this variable. `npm test` checks assignment and playback/response rules; `npm run build` checks types and bundles.

`frontend/public/demo.json` and `backend/app/data/demo.json` are the same verified UCI snapshot. `demo-provenance.json` records its source and preprocessing details. The static snapshot permits floor inspection and slot changes, but comparison remains disabled until the API responds with matching simulation results.

Use Node.js 22.12 or newer (the model tests use native TypeScript stripping).

## Optional browser contract check

With the dev server running, from `frontend/`:

```sh
npx --yes @playwright/cli -s=wit open http://localhost:5173
npx --yes @playwright/cli -s=wit run-code --filename checks/browser-contract-check.js
npx --yes @playwright/cli -s=wit close
```

This injects a tiny, explicitly synthetic API fixture into that isolated browser session. It checks equal replay inputs, layout switching, swaps clearing stale results, play/pause/reset/seek, camera controls, orders, and mobile overflow. It does **not** prove real-data/backend correctness or measured warehouse savings. Close the session afterward to remove its request mocks. Playwright CLI is an optional verification tool, not an app dependency.
