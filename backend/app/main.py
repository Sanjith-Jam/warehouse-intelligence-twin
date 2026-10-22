"""FastAPI main application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.config import settings
from backend.app.api import (
    health_router,
    demo_router,
    warehouse_router,
    orders_router,
    simulate_router,
    datasets_router,
    layouts_router,
)

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Deterministic warehouse simulation and picking intelligence API.",
)

# CORS configuration allowing frontend origins (localhost and Cloudflare Pages)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"https://.*\.warehouse-intelligence-twin\.pages\.dev",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register endpoint routers
app.include_router(health_router)
app.include_router(demo_router)
app.include_router(warehouse_router)
app.include_router(orders_router)
app.include_router(simulate_router)
app.include_router(datasets_router)
app.include_router(layouts_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=settings.host, port=settings.port, reload=True)
