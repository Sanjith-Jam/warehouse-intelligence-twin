"""Data loader providing access to active warehouse dataset and orders."""
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


class DataLoader:
    """Manages loaded dataset, layout, products, and orders."""

    def __init__(self) -> None:
        self._meta: DatasetMeta = SAMPLE_META
        self._layout: WarehouseLayout = SAMPLE_LAYOUT
        self._products: list[Product] = SAMPLE_PRODUCTS
        self._orders: list[Order] = SAMPLE_ORDERS
        self._order_map: dict[str, Order] = {o.order_id: o for o in self._orders}

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
