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
   cloudflared tunnel run --token eyJhIjoiNTlkYzUwZWMxYzhkNWM2NGU4MjY5MTA1OTUzYzdlYmYiLCJ0IjoiYTVmZjJjMGItM2FlZi00ZWIwLThjMjAtNGQ4MzVlM2FhOTc4IiwicyI6IllXRmhZV0ZoWVdGaFlXRmhZV0ZoWVdGaFlXRmhZV0ZoWVdGaFlXRmhZV0U9In0=
   ```

3. **Deploy / Update the Workers VPC Gateway (if modified):**
   ```bash
   cd deploy/cloudflare-worker
   npx wrangler deploy
   ```

### Option B: Docker Container Deployment

A production-ready [`Dockerfile`](../Dockerfile) is provided in the repository root.

1. **Build the Docker Image:**
   ```bash
   docker build -t warehouse-intelligence-twin-backend .
   ```

2. **Run the Container:**
   ```bash
   docker run -d -p 8000:8000 --name wit-backend warehouse-intelligence-twin-backend
   ```

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

---

## 4. Service Limits & Availability

- **Cloudflare Workers Free Tier:**
  - 100,000 requests/day.
  - 10 ms CPU execution time per request (Worker only proxies; compute happens in FastAPI).
  - High availability globally with automatic SSL certificate rotation.
- **Cloudflare Tunnels:**
  - Zero bandwidth egress costs on free tier.
  - Multi-datacenter connection routing with automatic failover (bom, del, maa edge locations).
- **Restart Resilience:**
  - If the FastAPI process restarts cleanly, the Tunnel and Worker maintain their connection bindings. Once Uvicorn is back up, incoming requests immediately succeed without DNS propagation delays or frontend bundle updates.

---

## 5. Verification Commands

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
