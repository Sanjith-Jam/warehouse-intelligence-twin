# Warehouse Intelligence Twin — Backend

FastAPI service for deterministic warehouse simulation, aisle-respecting routing, and slotting. It loads the committed June 2011 UCI Online Retail II snapshot by default. The current public API is exposed through an ephemeral Cloudflare Quick Tunnel; see the root [`IMPLEMENTATION_PLAN.md`](../IMPLEMENTATION_PLAN.md) for deployment limitations and next steps.

## Prerequisites

- Python 3.11+ (Python 3.12 recommended)
- `uv` (recommended) or `pip`

## Quick Start

### 1. Create and Activate Virtual Environment

Using `uv`:
```bash
uv venv --python 3.12
source .venv/bin/activate
```

Using standard `venv`:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install Dependencies

Using `uv`:
```bash
uv pip install -r backend/requirements.txt
```

Using standard `pip`:
```bash
pip install -r backend/requirements.txt
```

### 3. Configure Environment

Copy `.env.example` to `.env` if custom configuration is needed:
```bash
cp backend/.env.example backend/.env
```

Default settings:
- `HOST`: `0.0.0.0`
- `PORT`: `8000`
- `CORS_ORIGINS`: `http://localhost:5173,http://localhost:3000`

### 4. Run Development Server

```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
The server will be available at `http://localhost:8000`. Interactive OpenAPI documentation is accessible at `http://localhost:8000/docs`.

### 5. Run Test Suite

```bash
pytest tests/ -v
```

## API Endpoints

All endpoints strictly adhere to `contracts/api.md`:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check (`{"status":"ok"}`) |
| `GET` | `/api/demo` | Frontend bootstrap: metadata, layout, products, demo orders |
| `GET` | `/api/warehouse` | Warehouse grid layout, slot geometry, and product catalog |
| `GET` | `/api/orders` | Immutable order snapshot |
| `POST` | `/api/simulate` | Deterministic order picking simulation across `original`, `baseline`, or `player` layouts |

## Dataset Preprocessing & Provenance

The backend serves the preprocessed June 2011 UCI Online Retail II dataset (`backend/app/data/demo.json`). To re-run or verify the preprocessing pipeline:

1. **Download the official workbook:**
   - Source: UCI Machine Learning Repository — [Online Retail II](https://archive.ics.uci.edu/dataset/502/online+retail+ii)
   - Direct zip: `https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip`
   - File: `online_retail_II.xlsx` (45,622,278 bytes)
   - Expected SHA-256: `bcbe73b35f5b7babf197fb0cb983a11f5d9ff929078d4aa53d171b1f2df2e980`

2. **Run portable preprocessing:**
   ```bash
   # Explicit path:
   python scripts/preprocess_retail.py --input /path/to/online_retail_II.xlsx

   # Or via environment variable:
   export UCI_DATASET_PATH=/path/to/online_retail_II.xlsx
   python scripts/preprocess_retail.py

   # Standard search locations checked automatically:
   # datasets/online-retail-ii/online_retail_II.xlsx
   # datasets/online_retail_II.xlsx
   # data/online_retail_II.xlsx
   # ./online_retail_II.xlsx
   ```

The script automatically synchronizes `backend/app/data/demo.json` with `frontend/public/demo.json` to guarantee byte-for-byte consistency.

## Deployment & Production Hosting

See [`backend/DEPLOYMENT.md`](DEPLOYMENT.md) for detailed deployment guides:
- **Cloudflare Named Tunnel** (recommended for zero-cost, persistent custom domain on Cloudflare)
- **Render.com / Railway / Fly.io** (cloud container or native Python deployment with Dockerfile / Procfile)
- Steps for reconnecting Cloudflare Pages to the permanent backend origin.

## Current scope

The API routes and simulator implement the shared contract against 100 real products and 20 deterministic selected orders. The warehouse geometry and travel assumptions remain synthetic. Optional analytics are deferred.

## Architecture & Module Layout

- `backend/app/main.py`: FastAPI entry point and CORS configuration
- `backend/app/config.py`: Environment and runtime settings
- `backend/app/models/schemas.py`: Authoritative Pydantic models matching `contracts/api.md`
- `backend/app/api/`: Endpoint routers (`health`, `demo`, `warehouse`, `orders`, `simulate`)
- `backend/app/data/`: Fixtures, datasets, and active data loader
- `backend/app/simulation/`: Deterministic BFS aisle routing and fast-mover baseline slotting logic
