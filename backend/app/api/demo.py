"""Frontend demo bootstrap endpoint."""
from fastapi import APIRouter
from backend.app.models.schemas import DemoResponse
from backend.app.data.loader import data_loader

router = APIRouter(prefix="/api", tags=["demo"])


@router.get("/demo", response_model=DemoResponse)
def get_demo() -> DemoResponse:
    """Return bootstrap metadata, warehouse layout, product catalog, and demo orders."""
    return data_loader.get_demo_response()
