"""Pydantic schemas strictly matching contracts/api.md."""
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "ok"


class DatasetMeta(BaseModel):
    """Dataset metadata."""
    dataset_id: str
    source: str
    month: Optional[str] = None
    real_order_data: bool
    synthetic_warehouse: bool
    cell_size_m: float


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
