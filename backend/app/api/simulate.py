"""Simulation and routing execution endpoint."""
from fastapi import APIRouter, HTTPException, status
from backend.app.models.schemas import SimulateRequest, SimulateResponse
from backend.app.data.loader import data_loader
from backend.app.simulation.router import simulate_orders
from backend.app.config import settings

router = APIRouter(prefix="/api", tags=["simulate"])


@router.post(
    "/simulate",
    response_model=SimulateResponse,
    responses={
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "Validation error or unprocessable simulation parameters"
        }
    },
)
def post_simulate(request: SimulateRequest) -> SimulateResponse:
    """Execute order picking simulation for original, baseline, or player layouts."""
    # Validate order_ids exist in current dataset
    orders_to_replay = []
    for order_id in request.order_ids:
        order = data_loader.get_order(order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Unknown order ID '{order_id}'",
            )
        orders_to_replay.append(order)

    try:
        response = simulate_orders(
            dataset_id=data_loader.meta.dataset_id,
            orders=orders_to_replay,
            layout=data_loader.layout,
            products=data_loader.products,
            policy=request.policy,
            slot_assignments=request.slot_assignments,
            speed_mps=request.speed_mps,
            cell_size_m=data_loader.meta.cell_size_m,
            handling_seconds_per_line=settings.handling_seconds_per_line,
        )
        return response
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(err),
        ) from err
