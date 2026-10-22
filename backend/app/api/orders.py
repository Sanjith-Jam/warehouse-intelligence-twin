"""Order set endpoint."""
from fastapi import APIRouter
from backend.app.models.schemas import OrdersResponse
from backend.app.data.loader import data_loader

router = APIRouter(prefix="/api", tags=["orders"])


@router.get("/orders", response_model=OrdersResponse)
def get_orders() -> OrdersResponse:
    """Return immutable demo order set."""
    return data_loader.get_orders_response()
