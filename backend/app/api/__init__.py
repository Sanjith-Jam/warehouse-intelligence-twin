"""API route handlers."""
from backend.app.api.health import router as health_router
from backend.app.api.demo import router as demo_router
from backend.app.api.warehouse import router as warehouse_router
from backend.app.api.orders import router as orders_router
from backend.app.api.simulate import router as simulate_router
from backend.app.api.datasets import router as datasets_router

__all__ = [
    "health_router",
    "demo_router",
    "warehouse_router",
    "orders_router",
    "simulate_router",
    "datasets_router",
]
