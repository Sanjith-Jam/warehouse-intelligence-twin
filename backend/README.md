# Warehouse Intelligence Twin — Backend

FastAPI backend scaffold for deterministic warehouse simulation, aisle-respecting path routing, and slotting endpoints. **Current data is a one-product synthetic fixture**; the public real-data preview is not yet connected to this API, so do not report its simulation results as UCI metrics. Follow the current data-loader and simulation milestones in [`../IMPLEMENTATION_PLAN.md`](../IMPLEMENTATION_PLAN.md).

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

## Current scope

The API routes and simulator implement the shared contract against a synthetic fixture. Real June 2011 preprocessing, the 100-SKU service response, and public API deployment are pending. Optional analytics are out of scope until PS 4.2 is complete.

## Architecture & Module Layout

- `backend/app/main.py`: FastAPI entry point and CORS configuration
- `backend/app/config.py`: Environment and runtime settings
- `backend/app/models/schemas.py`: Authoritative Pydantic models matching `contracts/api.md`
- `backend/app/api/`: Endpoint routers (`health`, `demo`, `warehouse`, `orders`, `simulate`)
- `backend/app/data/`: Fixtures, datasets, and active data loader
- `backend/app/simulation/`: Deterministic BFS aisle routing and fast-mover baseline slotting logic
