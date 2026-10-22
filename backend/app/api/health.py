"""Health check endpoint."""
from fastapi import APIRouter
from backend.app.models.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """Service health check."""
    return HealthResponse(status="ok")
