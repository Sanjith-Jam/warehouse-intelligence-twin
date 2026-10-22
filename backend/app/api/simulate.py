"""Simulation and routing execution endpoint."""
from typing import Optional
from fastapi import APIRouter, Body, HTTPException, status
from backend.app.models.schemas import (
    SimulateRequest,
    SimulateResponse,
    SimulationRequest,
    SimulationResponse,
    ErrorResponse,
    ErrorCode,
    make_error_detail,
)
from backend.app.data.loader import data_loader, get_dataset
from backend.app.simulation.router import simulate_orders, simulate_dataset_policies
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


@router.post(
    "/datasets/{dataset_id}/simulate",
    response_model=SimulationResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "Dataset not found",
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ErrorResponse,
            "description": "Validation error or invalid player permutation",
        },
    },
)
def post_dataset_simulate(
    dataset_id: str,
    request: Optional[SimulationRequest] = Body(default=None),
) -> SimulationResponse:
    """Execute order picking simulation for a specific dataset snapshot.

    Replays frozen orders across original, baseline, and player policies deterministically.
    Supports dynamic datasets with any number of SKUs (<100 SKUs).
    """
    req = request or SimulationRequest()

    # Load dataset or raise 404
    dataset = get_dataset(dataset_id)

    # Resolve speed (default 1.2 m/s) and handling time (default 15.0 s per pick)
    speed = req.speed_m_s or req.speed_mps or 1.2
    handling_time = req.handling_time_s or req.handling_seconds_per_line or 15.0

    # Resolve player permutation if passed
    permutation = req.layout_permutation or req.slot_assignments

    try:
        response = simulate_dataset_policies(
            dataset=dataset,
            order_ids=req.order_ids,
            layout_permutation=permutation,
            speed_mps=speed,
            handling_seconds_per_line=handling_time,
            cell_size_m=dataset.meta.cell_size_m,
        )
        return response
    except ValueError as err:
        err_msg = str(err)
        code = ErrorCode.MALFORMED_ORDER if "order ID" in err_msg else ErrorCode.INVALID_SLOT_ASSIGNMENT
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=make_error_detail(code, err_msg).model_dump(),
        ) from err
