"""Data models and schemas."""
from backend.app.models.schemas import (
    # Error schemas & codes
    ErrorCode,
    ErrorDetail,
    ErrorResponse,
    make_error_detail,
    # Column mapping & aliases
    CANONICAL_COLUMN_ALIASES,
    REQUIRED_CANONICAL_COLUMNS,
    normalize_column_name,
    detect_canonical_columns,
    ColumnMapping,
    # Health check
    HealthResponse,
    # Warehouse & geometry
    Slot,
    WarehouseLayout,
    Product,
    OrderLine,
    Order,
    # Dataset, snapshot & provenance
    DatasetMeta,
    CleaningReport,
    Provenance,
    PreprocessRequest,
    DatasetInspectionResponse,
    DatasetDetailResponse,
    DatasetExportResponse,
    # Layout management
    SaveLayoutRequest,
    LayoutSaveRequest,
    CreateLayoutRequest,
    UpdateLayoutRequest,
    SavedLayout,
    LayoutRecord,
    LayoutDetail,
    LayoutPermutation,
    LayoutValidationResult,
    LayoutsListResponse,
    LayoutListResponse,
    # Legacy / bootstrap responses
    DemoResponse,
    WarehouseResponse,
    OrdersResponse,
    # Simulation schemas
    SimulateRequest,
    RouteVisit,
    OrderRoute,
    SimulationAssumptions,
    SimulateResponse,
    PolicyResult,
    SimulatedOrder,
    SimulationRequest,
    SimulationResponse,
)

__all__ = [
    # Error schemas & codes
    "ErrorCode",
    "ErrorDetail",
    "ErrorResponse",
    "make_error_detail",
    # Column mapping & aliases
    "CANONICAL_COLUMN_ALIASES",
    "REQUIRED_CANONICAL_COLUMNS",
    "normalize_column_name",
    "detect_canonical_columns",
    "ColumnMapping",
    # Health check
    "HealthResponse",
    # Warehouse & geometry
    "Slot",
    "WarehouseLayout",
    "Product",
    "OrderLine",
    "Order",
    # Dataset, snapshot & provenance
    "DatasetMeta",
    "CleaningReport",
    "Provenance",
    "PreprocessRequest",
    "DatasetInspectionResponse",
    "DatasetDetailResponse",
    "DatasetExportResponse",
    # Layout management
    "SaveLayoutRequest",
    "LayoutSaveRequest",
    "CreateLayoutRequest",
    "UpdateLayoutRequest",
    "SavedLayout",
    "LayoutRecord",
    "LayoutDetail",
    "LayoutPermutation",
    "LayoutValidationResult",
    "LayoutsListResponse",
    "LayoutListResponse",
    # Legacy / bootstrap responses
    "DemoResponse",
    "WarehouseResponse",
    "OrdersResponse",
    # Simulation schemas
    "SimulateRequest",
    "RouteVisit",
    "OrderRoute",
    "SimulationAssumptions",
    "SimulateResponse",
    "PolicyResult",
    "SimulatedOrder",
    "SimulationRequest",
    "SimulationResponse",
]
