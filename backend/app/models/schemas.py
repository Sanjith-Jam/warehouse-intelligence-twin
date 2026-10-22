"""Pydantic schemas strictly matching contracts/api.md."""
from enum import Enum
import math
import re
from typing import Any, Optional, Literal
from pydantic import BaseModel, Field, field_validator, model_validator


# ==============================================================================
# Stable Error Codes & Structured Error Schemas
# ==============================================================================

class ErrorCode(str, Enum):
    """Stable machine-readable error codes for API error responses."""
    UNSUPPORTED_FILE_TYPE = "UNSUPPORTED_FILE_TYPE"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    MISSING_REQUIRED_COLUMNS = "MISSING_REQUIRED_COLUMNS"
    NO_DATA_IN_MONTH = "NO_DATA_IN_MONTH"
    DATASET_NOT_FOUND = "DATASET_NOT_FOUND"
    MALFORMED_ORDER = "MALFORMED_ORDER"
    INVALID_SLOT_ASSIGNMENT = "INVALID_SLOT_ASSIGNMENT"
    EMPTY_FILE = "EMPTY_FILE"


class ErrorDetail(BaseModel):
    """Standardized structured error detail payload."""
    code: str = Field(..., description="Stable machine-readable error code")
    message: str = Field(..., description="Human-readable explanation of the error")
    details: Optional[dict[str, Any]] = Field(default=None, description="Optional structured context or parameters")

    @classmethod
    def from_code(
        cls,
        code: ErrorCode | str,
        message: str,
        details: Optional[dict[str, Any]] = None,
    ) -> "ErrorDetail":
        code_str = code.value if isinstance(code, ErrorCode) else str(code)
        return cls(code=code_str, message=message, details=details)


class ErrorResponse(BaseModel):
    """Standardized API error response payload wrapping detail."""
    detail: ErrorDetail | str


def make_error_detail(
    code: ErrorCode | str,
    message: str,
    details: Optional[dict[str, Any]] = None,
) -> ErrorDetail:
    """Convenience factory function for ErrorDetail instances."""
    return ErrorDetail.from_code(code, message, details)


# ==============================================================================
# Canonical Column Aliases & Detection
# ==============================================================================

CANONICAL_COLUMN_ALIASES: dict[str, list[str]] = {
    "invoice": ["invoiceno", "invoice", "order_id", "order id", "invoicenum", "billno"],
    "sku": ["stockcode", "sku", "productcode", "itemcode", "product id"],
    "description": ["description", "productname", "item_description", "name", "title"],
    "quantity": ["quantity", "qty", "units"],
    "date": ["invoicedate", "date", "timestamp", "order_date", "datetime"],
}

REQUIRED_CANONICAL_COLUMNS: list[str] = [
    "invoice",
    "sku",
    "quantity",
    "date",
]


def normalize_column_name(col: str) -> str:
    """Normalize column header for alias matching (lowercase, stripped, alphanumeric only)."""
    return re.sub(r"[^a-z0-9]", "", col.strip().lower())


def detect_canonical_columns(columns: list[str]) -> tuple[dict[str, str], list[str]]:
    """Detect canonical columns from a list of dataset column headers.

    Returns:
        tuple[dict[str, str], list[str]]: (detected_columns, missing_required_columns)
        where detected_columns maps canonical field name -> actual column name in input.
    """
    normalized_to_raw = {normalize_column_name(col): col for col in columns}
    detected: dict[str, str] = {}

    for canonical, aliases in CANONICAL_COLUMN_ALIASES.items():
        norm_canonical = normalize_column_name(canonical)
        if norm_canonical in normalized_to_raw:
            detected[canonical] = normalized_to_raw[norm_canonical]
            continue
        for alias in aliases:
            norm_alias = normalize_column_name(alias)
            if norm_alias in normalized_to_raw:
                detected[canonical] = normalized_to_raw[norm_alias]
                break

    missing = [req for req in REQUIRED_CANONICAL_COLUMNS if req not in detected]
    return detected, missing


class ColumnMapping(BaseModel):
    """Explicit mapping of canonical field names to dataset column names."""
    invoice: Optional[str] = Field(default=None, description="Source column for invoice identifier")
    sku: Optional[str] = Field(default=None, description="Source column for stock-keeping unit")
    description: Optional[str] = Field(default=None, description="Source column for item description")
    quantity: Optional[str] = Field(default=None, description="Source column for quantity")
    date: Optional[str] = Field(default=None, description="Source column for invoice date/timestamp")


# ==============================================================================
# Health Check
# ==============================================================================

class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "ok"


# ==============================================================================
# Warehouse & Geometry
# ==============================================================================

class Slot(BaseModel):
    """Warehouse storage slot geometry and initial product assignment."""
    slot_id: str
    rack_cell: list[int] = Field(..., description="[x, z] coordinate of impassable rack")
    access_cell: list[int] = Field(..., description="[x, z] coordinate of walkable access cell")
    sku: str

    @field_validator("rack_cell", "access_cell")
    @classmethod
    def validate_coord(cls, v: list[int]) -> list[int]:
        if len(v) != 2:
            raise ValueError("Coordinate must be a 2-element [x, z] list")
        return v


class WarehouseLayout(BaseModel):
    """Warehouse grid layout specification."""
    layout_id: str
    width: int
    height: int
    walkable_cells: list[list[int]]
    dock: list[int]
    slots: list[Slot]

    @field_validator("dock")
    @classmethod
    def validate_dock(cls, v: list[int]) -> list[int]:
        if len(v) != 2:
            raise ValueError("Dock coordinate must be a 2-element [x, z] list")
        return v


class Product(BaseModel):
    """Product catalog item."""
    sku: str
    name: str
    pick_frequency: int


class OrderLine(BaseModel):
    """Individual line item in an order."""
    sku: str
    quantity: int


class Order(BaseModel):
    """Customer order containing lines to pick."""
    order_id: str
    lines: list[OrderLine]


# ==============================================================================
# Dataset, Snapshot & Provenance
# ==============================================================================

class DatasetMeta(BaseModel):
    """Dataset metadata."""
    dataset_id: str
    source: Optional[str] = None
    snapshot_id: Optional[str] = None
    source_filename: Optional[str] = None
    month: Optional[str] = None
    created_at: Optional[str] = None
    top_sku_count: Optional[int] = None
    order_count: Optional[int] = None
    real_order_data: bool = False
    synthetic_warehouse: bool = True
    cell_size_m: float = 1.5

    @model_validator(mode="before")
    @classmethod
    def populate_source_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            src = data.get("source")
            src_file = data.get("source_filename")
            if src and not src_file:
                data["source_filename"] = src
            elif src_file and not src:
                data["source"] = src_file

            if "snapshot_id" not in data and "dataset_id" in data:
                data["snapshot_id"] = data["dataset_id"]
        return data


class CleaningReport(BaseModel):
    """Cleaning report and data provenance."""
    purpose: Optional[str] = None
    source_filename: Optional[str] = None
    month: Optional[str] = None
    sheet: Optional[str] = None
    time_assumption: Optional[str] = None
    month_rows: int = Field(default=0, ge=0)
    cancelled_month_rows: int = Field(default=0, ge=0)
    nonpositive_or_missing_quantity_rows: int = Field(default=0, ge=0)
    nonproduct_or_blank_sku_rows: int = Field(default=0, ge=0)
    filter_counts_overlap: bool = True
    excluded_nonproduct_codes: list[str] = Field(default_factory=list)
    valid_positive_product_lines: int = Field(default=0, ge=0)
    top_sku_count: int = Field(default=100, ge=0)
    pick_frequency_definition: Optional[str] = (
        "Number of retained positive picking lines per SKU in the complete month; not units."
    )
    top_sku_month_lines: int = Field(default=0, ge=0)
    top_sku_month_order_count: int = Field(default=0, ge=0)
    selected_order_count: int = Field(default=0, ge=0)
    selected_order_ids: list[str] = Field(default_factory=list)
    selection_criteria: Optional[str] = "Deterministic selection of multi-line orders filtered to retained SKUs"

    model_config = {"extra": "allow"}


Provenance = CleaningReport


class PreprocessRequest(BaseModel):
    """Options for dataset preprocessing."""
    sheet_name: Optional[str] = Field(default=None, description="Target sheet name for multi-sheet workbooks")
    target_month: str = Field(..., description="Target month in YYYY-MM format (e.g., '2011-06')")
    top_skus: int = Field(default=100, ge=1, le=1000, description="Number of top SKUs to retain")
    max_orders: int = Field(default=20, ge=1, le=100, description="Maximum number of orders to retain for replay")
    column_mapping: Optional[dict[str, str]] = Field(default=None, description="Optional custom column mapping overrides")
    cell_size_m: float = Field(default=1.5, gt=0, le=10.0, description="Grid cell size in meters")

    @field_validator("target_month")
    @classmethod
    def validate_target_month(cls, v: str) -> str:
        if not re.match(r"^\d{4}-(?:0[1-9]|1[0-2])$", v):
            raise ValueError("target_month must be in YYYY-MM format (e.g. '2011-06')")
        return v


class DatasetInspectionResponse(BaseModel):
    """Inspection summary for an uploaded dataset."""
    dataset_id: str
    filename: str
    file_size_bytes: int = Field(..., ge=0)
    sheets: list[str] = Field(default_factory=list)
    detected_columns: dict[str, str] = Field(default_factory=dict)
    missing_required_columns: list[str] = Field(default_factory=list)
    available_months: list[str] = Field(default_factory=list)
    total_rows: int = Field(default=0, ge=0)
    preview_rows: list[dict[str, Any]] = Field(default_factory=list)


class DatasetDetailResponse(BaseModel):
    """Detailed dataset response including metadata, cleaning report, layout, products, and orders."""
    meta: DatasetMeta
    cleaning_report: CleaningReport
    layout: WarehouseLayout
    products: list[Product]
    orders: list[Order]

    @model_validator(mode="before")
    @classmethod
    def map_provenance_alias(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "provenance" in data and "cleaning_report" not in data:
                data["cleaning_report"] = data["provenance"]
        return data

    @property
    def provenance(self) -> CleaningReport:
        return self.cleaning_report


class DatasetExportResponse(BaseModel):
    """Dataset export payload metadata."""
    dataset_id: str
    format: str = Field(..., description="Export format, e.g. json, csv, zip")
    download_url: Optional[str] = None
    record_count: Optional[int] = None
    file_size_bytes: Optional[int] = None


# ==============================================================================
# Layout Management Schemas
# ==============================================================================

class SaveLayoutRequest(BaseModel):
    """Payload to save a customized layout / slot assignment."""
    layout_id: str = Field(..., min_length=1, description="Unique identifier for the layout")
    name: Optional[str] = Field(default=None, description="Human-readable name")
    description: Optional[str] = None
    slot_assignments: dict[str, str] = Field(..., description="Mapping of slot_id -> sku")
    layout: Optional[WarehouseLayout] = None


LayoutSaveRequest = SaveLayoutRequest


class SavedLayout(BaseModel):
    """Saved warehouse layout record."""
    dataset_id: str
    layout_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    slot_assignments: dict[str, str] = Field(default_factory=dict)
    layout: Optional[WarehouseLayout] = None
    created_at: Optional[str] = None


LayoutDetail = SavedLayout


class LayoutsListResponse(BaseModel):
    """Response containing list of layouts for a dataset."""
    dataset_id: str
    layouts: list[SavedLayout]


LayoutListResponse = LayoutsListResponse


# ==============================================================================
# Legacy / Bootstrap Responses (Backwards-Compatible)
# ==============================================================================

class DemoResponse(BaseModel):
    """Full demo bootstrap payload."""
    meta: DatasetMeta
    layout: WarehouseLayout
    products: list[Product]
    orders: list[Order]


class WarehouseResponse(BaseModel):
    """Warehouse layout and product catalog payload."""
    meta: DatasetMeta
    layout: WarehouseLayout
    products: list[Product]


class OrdersResponse(BaseModel):
    """Order set payload."""
    dataset_id: str
    orders: list[Order]


# ==============================================================================
# Simulation Schemas
# ==============================================================================

class SimulateRequest(BaseModel):
    """Simulation replay request payload."""
    order_ids: list[str]
    slot_assignments: Optional[dict[str, str]] = None
    policy: Literal["original", "baseline", "player"] = "player"
    speed_mps: float = 1.2

    @field_validator("order_ids")
    @classmethod
    def validate_order_ids(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("order_ids must not be empty")
        if len(v) != len(set(v)):
            raise ValueError("order_ids must be unique")
        return v

    @field_validator("speed_mps")
    @classmethod
    def validate_speed(cls, v: float) -> float:
        if not math.isfinite(v):
            raise ValueError("speed_mps must be a finite number")
        if v <= 0:
            raise ValueError("speed_mps must be positive")
        if v > 10.0:
            raise ValueError("speed_mps must be <= 10.0")
        return v


class RouteVisit(BaseModel):
    """Record of a SKU pick visit during route execution."""
    sku: str
    slot_id: str
    waypoint_index: int


class OrderRoute(BaseModel):
    """Picker tour for a single order starting and ending at the dock."""
    order_id: str
    waypoints: list[list[int]]
    visits: list[RouteVisit]


class SimulationAssumptions(BaseModel):
    """Constants and assumptions used during simulation scoring."""
    speed_mps: float = 1.2
    handling_seconds_per_line: float = 10.0


class SimulateResponse(BaseModel):
    """Complete simulation results matching contracts/api.md."""
    dataset_id: str
    policy: str
    slot_assignments: dict[str, str]
    orders_replayed: int
    distance_m: float
    estimated_pick_time_s: float
    average_pick_time_s: float
    routes: list[OrderRoute]
    warnings: list[str] = Field(default_factory=list)
    assumptions: SimulationAssumptions
