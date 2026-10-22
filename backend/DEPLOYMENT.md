# Warehouse Intelligence Twin — Stable Backend Deployment Guide

This guide documents the simplest Python-capable stable-host options, free-plan/runtime limitations, and the exact steps to connect a permanent backend origin to the Cloudflare Pages frontend.

---

## Current Architecture & State

- **Frontend:** Cloudflare Pages ([https://warehouse-intelligence-twin.pages.dev](https://warehouse-intelligence-twin.pages.dev))
- **Backend API:** FastAPI running deterministic BFS routing and 3-way layout simulation
- **Current Demo Bridge:** Ephemeral Cloudflare Quick Tunnel (`trycloudflare.com`), which requires local daemon processes (`uvicorn` and `cloudflared`).

---

## Stable Hosting Options (Free Tier Comparison)

| Option | Stability / Uptime | Cold Starts | Free Plan Quota | Setup Complexity | Best For |
|---|---|---|---|---|---|
| **1. Cloudflare Named Tunnel** *(Recommended)* | 100% persistent stable hostname | **0s (Instant)** | Unlimited (Free) | Low (CLI command) | Projects already using Cloudflare |
| **2. Render.com Web Service** | Persistent URL (`*.onrender.com`) | ~50s after 15m idle | 750 hrs/month | Low (GitHub App click) | Zero-maintenance cloud hosting |
| **3. Railway / Fly.io (Docker)** | Persistent URL | Minimal | Trial / Hobby credits | Medium | Container deployments |

---

## Option 1: Cloudflare Named Tunnel (Recommended)

Since the project already uses Cloudflare Pages under the operator's account, a **Named Cloudflare Tunnel** gives a permanent, zero-cost public HTTPS URL with zero cold starts.

### Prerequisites
- A domain managed in your Cloudflare dashboard (e.g. `example.com`), OR access to a subdomain.
- The `cloudflared` CLI.

### Steps
1. **Authenticate cloudflared with your Cloudflare account:**
   ```bash
   cloudflared tunnel login
   ```
2. **Create a permanent named tunnel:**
   ```bash
   cloudflared tunnel create warehouse-api
   ```
   *Note: This creates a credentials JSON file in `~/.cloudflared/<tunnel-uuid>.json`. Keep this file private; never commit it to Git.*

3. **Configure the tunnel (`~/.cloudflared/config.yml`):**
   ```yaml
   tunnel: <tunnel-uuid>
   credentials-file: /path/to/.cloudflared/<tunnel-uuid>.json

   ingress:
     - hostname: api.example.com
       service: http://localhost:8000
     - service: http_status:404
   ```

4. **Route DNS to your tunnel:**
   ```bash
   cloudflared tunnel route dns warehouse-api api.example.com
   ```

5. **Run the tunnel (or configure as a system service):**
   ```bash
   # Foreground:
   cloudflared tunnel run warehouse-api

   # Or persistent background system service:
   sudo cloudflared service install
   sudo systemctl start cloudflared
   ```

---

## Option 2: Render.com (Cloud PaaS)

If you prefer cloud hosting independent of local processes:

### Steps
1. Create a free account at [render.com](https://render.com).
2. Click **New +** → **Web Service** → Connect repository `Sanjith-Jam/warehouse-intelligence-twin`.
3. Configure the service settings:
   - **Environment:** `Python 3`
   - **Region:** Closest to users (e.g. Frankfurt or Singapore)
   - **Branch:** `main`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
4. Set Environment Variables:
   - `CORS_ORIGINS`: `https://warehouse-intelligence-twin.pages.dev,http://localhost:5173`
5. Click **Create Web Service**. Your permanent public URL will be `https://<service-name>.onrender.com`.

### Free-Tier Limitations
- **Cold start:** Free instances spin down after 15 minutes of inactivity. The first request after idle takes ~50 seconds to respond.
- **Instance hours:** 750 free hours per month (sufficient for one full-time service).

---

## Option 3: Container Deployment (Railway / Fly.io / Self-Hosted)

A production-ready [Dockerfile](file:///home/bread/warehouse-intelligence-twin/Dockerfile) is provided in the repository root:

```bash
docker build -t warehouse-twin-backend .
docker run -d -p 8000:8000 \
  -e CORS_ORIGINS="https://warehouse-intelligence-twin.pages.dev" \
  warehouse-twin-backend
```

---

## Connecting the Permanent Backend to Cloudflare Pages

Once your permanent backend is live (e.g. `https://api.example.com` or `https://warehouse-intelligence-twin.onrender.com`), update the Cloudflare Pages production deployment:

```bash
cd frontend
VITE_API_BASE_URL="https://<your-stable-backend-url>" npm run build
npx -y wrangler@4.151.3 pages deploy dist --project-name warehouse-intelligence-twin --branch main
```

### Verification Checklist:
- [ ] `curl https://<your-stable-backend-url>/health` returns `{"status":"ok"}`
- [ ] `curl https://<your-stable-backend-url>/api/demo` returns `real_order_data: true`
- [ ] CORS preflight from `https://warehouse-intelligence-twin.pages.dev` returns HTTP 200
- [ ] Loading `https://warehouse-intelligence-twin.pages.dev` in a browser shows **"Simulation connected"** (no offline warning)
- [ ] Clicking **"Replay & compare"** scores all 3 layouts live
