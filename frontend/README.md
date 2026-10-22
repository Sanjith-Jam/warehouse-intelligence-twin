# Frontend

React, Vite, TypeScript, React Three Fiber, and Drei power the warehouse floor. The interface reads `GET /api/demo` and sends the same ordered demo IDs, speed, and copied slot mapping to three `POST /api/simulate` requests. Routes, assignments, distance, and pick times come from the API; the browser only animates returned waypoints. A local synthetic fixture displays the floor while the API is unavailable, with scoring disabled and a visible preview label.

```sh
cd frontend
npm install
npm run dev
```

Run the backend at `http://localhost:8000`; Vite proxies `/api` in development. For a deployed frontend, set `VITE_API_BASE_URL` to the public backend origin (no trailing slash). Never put API secrets in this variable. `npm test` checks assignment and playback/response rules; `npm run build` checks types and bundles.

If the simulation API is unavailable, the UI remains an unscored floor preview. A verified backend demo export may be placed at `frontend/public/demo.json` to show its real order snapshot in that preview; it must match the `/api/demo` contract and set `meta.real_order_data` to `true`. Comparison remains disabled until the API responds.

Use Node.js 22.12 or newer (the model tests use native TypeScript stripping).

## Optional browser contract check

With the dev server running, from `frontend/`:

```sh
npx --yes @playwright/cli -s=wit open http://localhost:5173
npx --yes @playwright/cli -s=wit run-code --filename checks/browser-contract-check.js
npx --yes @playwright/cli -s=wit close
```

This injects a tiny, explicitly synthetic API fixture into that isolated browser session. It checks equal replay inputs, layout switching, swaps clearing stale results, play/pause/reset/seek, camera controls, orders, and mobile overflow. It does **not** prove real-data/backend correctness or measured warehouse savings. Close the session afterward to remove its request mocks. Playwright CLI is an optional verification tool, not an app dependency.
