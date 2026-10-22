"""Warehouse layout and product catalog endpoint."""
from fastapi import APIRouter
from backend.app.models.schemas import WarehouseResponse
from backend.app.data.loader import data_loader

router = APIRouter(prefix="/api", tags=["warehouse"])


@router.get("/warehouse", response_model=WarehouseResponse)
def get_warehouse() -> WarehouseResponse:
    """Return warehouse grid layout, slots, dock, and product catalog."""
    return data_loader.get_warehouse_response()
