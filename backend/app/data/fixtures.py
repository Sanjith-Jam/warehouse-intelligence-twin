"""Deterministic demo fixture conforming to contracts/api.md."""
from backend.app.models.schemas import (
    DatasetMeta,
    WarehouseLayout,
    Slot,
    Product,
    Order,
    OrderLine,
    DemoResponse,
)

SAMPLE_META = DatasetMeta(
    dataset_id="sample-v1",
    source="synthetic fixture",
    month=None,
    real_order_data=False,
    synthetic_warehouse=True,
    cell_size_m=1.5,
)

SAMPLE_LAYOUT = WarehouseLayout(
    layout_id="original",
    width=4,
    height=3,
    walkable_cells=[[0, 0], [1, 0], [2, 0], [3, 0]],
    dock=[0, 0],
    slots=[
        Slot(
            slot_id="S001",
            rack_cell=[1, 1],
            access_cell=[1, 0],
            sku="DEMO-001",
        )
    ],
)

SAMPLE_PRODUCTS = [
    Product(
        sku="DEMO-001",
        name="Sample product",
        pick_frequency=1,
    )
]

SAMPLE_ORDERS = [
    Order(
        order_id="DEMO-ORDER-1",
        lines=[
            OrderLine(
                sku="DEMO-001",
                quantity=2,
            )
        ],
    )
]


def get_sample_demo_response() -> DemoResponse:
    """Return the canonical demo fixture response."""
    return DemoResponse(
        meta=SAMPLE_META,
        layout=SAMPLE_LAYOUT,
        products=SAMPLE_PRODUCTS,
        orders=SAMPLE_ORDERS,
    )
