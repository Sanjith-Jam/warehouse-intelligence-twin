"""Data loader providing access to active warehouse dataset and orders."""
import json
from pathlib import Path
from typing import Optional
from backend.app.models.schemas import (
    DatasetMeta,
    WarehouseLayout,
    Product,
    Order,
    DemoResponse,
    WarehouseResponse,
    OrdersResponse,
)
from backend.app.data.fixtures import (
    SAMPLE_META,
    SAMPLE_LAYOUT,
    SAMPLE_PRODUCTS,
    SAMPLE_ORDERS,
)

DEFAULT_DATA_PATH = Path(__file__).resolve().parent / "demo.json"


class DataLoader:
    """Manages loaded dataset, layout, products, and orders."""

    def __init__(self, data_path: Optional[Path] = DEFAULT_DATA_PATH) -> None:
        self.load(data_path)

    def load(self, data_path: Optional[Path]) -> None:
        """Load dataset from path or fall back to sample fixture."""
        if data_path and data_path.exists():
            with open(data_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._meta = DatasetMeta.model_validate(data["meta"])
            self._layout = WarehouseLayout.model_validate(data["layout"])
            self._products = [Product.model_validate(p) for p in data["products"]]
            self._orders = [Order.model_validate(o) for o in data["orders"]]
        else:
            self._meta = SAMPLE_META
            self._layout = SAMPLE_LAYOUT
            self._products = SAMPLE_PRODUCTS
            self._orders = SAMPLE_ORDERS

        self._order_map = {o.order_id: o for o in self._orders}

    @property
    def meta(self) -> DatasetMeta:
        return self._meta

    @property
    def layout(self) -> WarehouseLayout:
        return self._layout

    @property
    def products(self) -> list[Product]:
        return self._products

    @property
    def orders(self) -> list[Order]:
        return self._orders

    def get_order(self, order_id: str) -> Optional[Order]:
        return self._order_map.get(order_id)

    def get_demo_response(self) -> DemoResponse:
        return DemoResponse(
            meta=self._meta,
            layout=self._layout,
            products=self._products,
            orders=self._orders,
        )

    def get_warehouse_response(self) -> WarehouseResponse:
        return WarehouseResponse(
            meta=self._meta,
            layout=self._layout,
            products=self._products,
        )

    def get_orders_response(self) -> OrdersResponse:
        return OrdersResponse(
            dataset_id=self._meta.dataset_id,
            orders=self._orders,
        )


data_loader = DataLoader()
