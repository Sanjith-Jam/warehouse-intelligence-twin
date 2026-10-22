# Backend Deployment & Production Integration Guide

This guide details the durable hosting architecture, stable HTTPS API origin, configuration options, and verification procedures for the **Warehouse Intelligence Twin** FastAPI backend.

---

## 1. Production Architecture Overview

The production deployment consists of three decoupled layers:

```
[ Browser / User ]
       │
       ▼
[ Cloudflare Pages Frontend ] (https://warehouse-intelligence-twin.pages.dev)
       │  VITE_API_BASE_URL: https://warehouse-intelligence-twin-api.warehouse-intelligence-twin-frontend.workers.dev
       ▼
[ Cloudflare Workers VPC Gateway ] (Edge reverse proxy on *.workers.dev)
       │  Cloudflare VPC Service Binding (wit-api-service, 01a16279-2416-7f52-b54d-5b89e44ad6bb)
       ▼
[ Cloudflare Named Tunnel ] (wit-backend, a5ff2c0b-3aef-4eb0-8c20-4d835e3aa978)
       │  Encrypted QUIC/HTTP2 edge connector
       ▼
[ FastAPI Backend ] (Uvicorn ASGI server on Python 3.12)
       ├── GET  /health
       ├── GET  /api/demo
       ├── GET  /api/warehouse
       ├── GET  /api/orders
       └── POST /api/simulate
```

### Key Differences from Ephemeral Quick Tunnel

| Property | Old Quick Tunnel (`trycloudflare.com`) | New Production Architecture |
| :--- | :--- | :--- |
| **Hostname Stability** | Ephemeral random subdomain (changes on restart) | **Permanent stable URL** (`*.workers.dev`) |
| **Authentication** | None (anonymous tunnel) | **Operator Cloudflare Account Credentials** |
| **Process Coupling** | Breaking the process breaks the frontend URL | **Durable Gateway** survives backend restarts |
| **TLS / SSL** | Dynamic Cloudflare cert per random subdomain | **Edge-managed Cloudflare SSL** |
| **Pages Integration** | Required rebuilding frontend every restart | **Built once with permanent API origin** |

---

## 2. Live Endpoints

- **Frontend Production:** [`https://warehouse-intelligence-twin.pages.dev`](https://warehouse-intelligence-twin.pages.dev)
- **Stable API Origin:** [`https://warehouse-intelligence-twin-api.warehouse-intelligence-twin-frontend.workers.dev`](https://warehouse-intelligence-twin-api.warehouse-intelligence-twin-frontend.workers.dev)
- **API Health Check:** [`https://warehouse-intelligence-twin-api.warehouse-intelligence-twin-frontend.workers.dev/health`](https://warehouse-intelligence-twin-api.warehouse-intelligence-twin-frontend.workers.dev/health)
- **API Demo Dataset:** [`https://warehouse-intelligence-twin-api.warehouse-intelligence-twin-frontend.workers.dev/api/demo`](https://warehouse-intelligence-twin-api.warehouse-intelligence-twin-frontend.workers.dev/api/demo)

---

## 3. Hosting Options & Configuration

### Option A: Cloudflare Named Tunnel + Workers VPC (Active Durable Production)

This architecture exposes the local or VM-hosted FastAPI backend through the operator's authorized Cloudflare account.

1. **Start the FastAPI Backend:**
   ```bash
   uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
   ```

2. **Connect the Cloudflare Named Tunnel:**
   ```bash
   cloudflared tunnel run --token "$CLOUDFLARE_TUNNEL_TOKEN"
   ```
   > [!IMPORTANT]
   > Export `CLOUDFLARE_TUNNEL_TOKEN` in your environment or inject via a secret manager. Never commit raw token literals or secret credentials to Git.

3. **Deploy / Update the Workers VPC Gateway (if modified):**
   ```bash
   cd deploy/cloudflare-worker
   npx wrangler deploy
   ```

### Option B: Docker Container Deployment

A production-ready [`Dockerfile`](../Dockerfile) is provided in the repository root with support for configurable upload storage and volume mounting.

1. **Build the Docker Image:**
   ```bash
   docker build -t warehouse-intelligence-twin-backend .
   ```

2. **Run the Container with Persistent Storage Volume:**
   ```bash
   docker run -d \
     -p 8000:8000 \
     -v wit_uploads:/app/backend/app/data/uploads \
     -e UPLOAD_STORAGE_DIR="/app/backend/app/data/uploads" \
     -e MAX_UPLOAD_SIZE_BYTES="52428800" \
     -e CORS_ORIGINS="http://localhost:5173,http://localhost:3000,https://warehouse-intelligence-twin.pages.dev" \
     --name wit-backend warehouse-intelligence-twin-backend
   ```
   > [!TIP]
   > Mounting the named volume `wit_uploads` guarantees that dynamic customer uploads, preprocessed snapshots (`processed.json`), provenance reports, and custom layout variants persist across container restarts and updates.

3. **Verify Container Health:**
   ```bash
   curl http://localhost:8000/health
   # Returns: {"status":"ok"}
   ```

### Option C: Platform-as-a-Service (Render.com / Railway / Fly.io)

Configuration files [`Procfile`](../Procfile) and [`render.yaml`](../render.yaml) are included for automated deployments on cloud platforms.

- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
- **Health Check Path:** `/health`
- **Required Environment Variables:**
  - `PYTHON_VERSION`: `3.12.15`
  - `CORS_ORIGINS`: `http://localhost:5173,http://localhost:3000,https://warehouse-intelligence-twin.pages.dev`
  - `UPLOAD_STORAGE_DIR`: `/tmp/wit_uploads` (or persistent disk mount path such as `/var/data/uploads`)
  - `MAX_UPLOAD_SIZE_BYTES`: `52428800`

---

## 4. Storage & Persistence Policy for Dynamic Datasets

Warehouse Intelligence Twin supports both immutable built-in demo data and dynamic user-uploaded workbooks (.csv, .xlsx, .xls) for multi-dataset picking simulations.

### 4.1 Storage Architecture & Durability

| Storage Mode | Target Environment | Durability & Lifecycle | Recommended Configuration |
| :--- | :--- | :--- | :--- |
| **Persistent Volume (Durability)** | Production Docker, Kubernetes, Bare Metal / VM | **Full Durability**: Uploaded files, preprocessed dataset snapshots (`processed.json`), cleaning reports, and custom layouts survive process and container restarts indefinitely. | Mount a host directory or persistent volume to `UPLOAD_STORAGE_DIR` (e.g. `/app/backend/app/data/uploads` or `/var/data/uploads`). |
| **Ephemeral Session Storage** | Serverless containers, PaaS without attached disks | **Session-Scoped Lifecycle**: Dynamic datasets remain fully available and simulateable for the active lifetime of the container instance. Storage resets on cold container redeployment. | Point `UPLOAD_STORAGE_DIR` to `/tmp/wit_uploads` or default local path. |
| **Immutable Seed Data** | All environments | **Unconditional Durability**: The canonical June 2011 UCI demo dataset (`demo.json`) is packaged directly within the application image and is read-only. It cannot be overwritten or deleted by user uploads. | Hardcoded safety invariant in `parsing.py` and `dataset_store.py`. |

### 4.2 File Size Limits & Processing Rules

- **Maximum Upload Size:** Bounded strictly to **50MB** (`52,428,800` bytes). Configurable via `MAX_UPLOAD_SIZE_BYTES`.
- **Early Stream Rejection:** Multipart uploads are streamed in 1MB chunks with continuous byte-counting. If an upload exceeds the limit, the connection is aborted immediately and responds with **HTTP 413 (Content Too Large)**. Any partially written files are pruned immediately to prevent disk exhaustion.
- **Processing Timeouts & Optimization:**
  - Workbook parsing uses streaming iterators (`openpyxl` read-only mode, `csv.reader`) to minimize memory footprint.
  - Preprocessing selects the top SKUs (up to 100) and orders (up to 20) for the target month in under 1 second.
  - Order picking simulation executes deterministically in memory (<50ms per policy), well within standard HTTP gateway timeouts (Cloudflare 100s limit).

---

## 5. Environment Variables Reference

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `CLOUDFLARE_TUNNEL_TOKEN` | *(None)* | Authentication credential token for connecting Cloudflare Named Tunnel (`wit-backend`). Required for Option A production tunnel. |
| `UPLOAD_STORAGE_DIR` | `backend/app/data/uploads` | Local filesystem path where uploaded workbooks, parsed sheets, preprocessed snapshots (`processed.json`), provenance reports, and layout variants are stored. Mount to persistent volume for durability across restarts. |
| `MAX_UPLOAD_SIZE_BYTES` | `52428800` (50MB) | Maximum allowable payload size in bytes for uploaded multipart datasets. Files exceeding this size are rejected with HTTP 413. |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000,https://warehouse-intelligence-twin.pages.dev` | Comma-separated list of allowed HTTP/HTTPS origins. Preview deployments matching `https://*.warehouse-intelligence-twin.pages.dev` are dynamically allowed via CORS origin regex. |
| `HOST` | `0.0.0.0` | Host interface IP address for Uvicorn ASGI server binding. |
| `PORT` | `8000` | TCP port on which Uvicorn listens. |

---

## 6. Service Limits & Availability

- **Cloudflare Workers Free Tier:**
  - 100,000 requests/day.
  - 10 ms CPU execution time per request (Worker only proxies; compute happens in FastAPI).
  - High availability globally with automatic SSL certificate rotation.
- **Cloudflare Tunnels:**
  - Zero bandwidth egress costs on free tier.
  - Multi-datacenter connection routing with automatic failover (bom, del, maa edge locations).
- **Restart Resilience:**
  - If the FastAPI process restarts cleanly, the Tunnel and Worker maintain their connection bindings. Once Uvicorn is back up, incoming requests immediately succeed without DNS propagation delays or frontend bundle updates.
  - Preprocessed datasets stored in `UPLOAD_STORAGE_DIR` reload instantly on demand without requiring re-upload or re-preprocessing.

---

## 7. Verification Commands

Run these commands from any terminal to verify the live deployment:

### 1. Health Endpoint
```bash
curl -i https://warehouse-intelligence-twin-api.warehouse-intelligence-twin-frontend.workers.dev/health
# Expected: HTTP/2 200, {"status":"ok"}
```

### 2. Demo Dataset Check
```bash
curl -s https://warehouse-intelligence-twin-api.warehouse-intelligence-twin-frontend.workers.dev/api/demo | jq '.meta'
# Expected:
# {
#   "dataset_id": "uci-2011-06-preview-bcbe73b35f5b",
#   "source": "UCI Online Retail II",
#   "month": "2011-06",
#   "real_order_data": true,
#   "synthetic_warehouse": true,
#   "cell_size_m": 1.5
# }
```

### 3. Orders Endpoint
```bash
curl -s https://warehouse-intelligence-twin-api.warehouse-intelligence-twin-frontend.workers.dev/api/orders | jq '{count: (.orders | length), first_order: .orders[0].order_id}'
# Expected: { "count": 20, "first_order": "555157" }
```

### 4. CORS Preflight from Pages Origin
```bash
curl -i -X OPTIONS "https://warehouse-intelligence-twin-api.warehouse-intelligence-twin-frontend.workers.dev/api/simulate" \
  -H "Origin: https://warehouse-intelligence-twin.pages.dev" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type"
# Expected: HTTP/2 200, access-control-allow-origin: https://warehouse-intelligence-twin.pages.dev
```

### 5. Simulation Scoring Across Policies
```bash
# Original Policy:
curl -s -X POST "https://warehouse-intelligence-twin-api.warehouse-intelligence-twin-frontend.workers.dev/api/simulate" \
  -H "Content-Type: application/json" \
  -d '{"order_ids":["555157","555158","555159","555160","555161","555162","555164","555194","555195","555198","555200","555199","555201","555202","555203","555207","555213","555233","555234","555240"],"policy":"original","speed_mps":1.2}' \
  | jq '{policy, distance_m, estimated_pick_time_s}'
# Expected: { "policy": "original", "distance_m": 2844.0, "estimated_pick_time_s": 3470.0 }

# Baseline Policy:
curl -s -X POST "https://warehouse-intelligence-twin-api.warehouse-intelligence-twin-frontend.workers.dev/api/simulate" \
  -H "Content-Type: application/json" \
  -d '{"order_ids":["555157","555158","555159","555160","555161","555162","555164","555194","555195","555198","555200","555199","555201","555202","555203","555207","555213","555233","555234","555240"],"policy":"baseline","speed_mps":1.2}' \
  | jq '{policy, distance_m, estimated_pick_time_s}'
# Expected: { "policy": "baseline", "distance_m": 2820.0, "estimated_pick_time_s": 3450.0 }
```

### 6. Deployment Readiness & Restart Smoke Tests
```bash
pytest tests/test_deployment_readiness.py -v
# Validates health endpoint, CORS policies, upload limits, and post-restart persistence survival.
```
