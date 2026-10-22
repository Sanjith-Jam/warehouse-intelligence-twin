"""Data loader providing access to active warehouse dataset and orders."""
import json
from pathlib import Path
from typing import Optional
from fastapi import HTTPException, status
from backend.app.config import settings
from backend.app.models.schemas import (
    DatasetMeta,
    WarehouseLayout,
    Product,
    Order,
    DemoResponse,
    WarehouseResponse,
    OrdersResponse,
    ErrorCode,
    make_error_detail,
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


def load_demo_data(data_path: Optional[Path] = DEFAULT_DATA_PATH) -> DemoResponse:
    """Load demo dataset cached via global data_loader instance."""
    if data_path and data_path != DEFAULT_DATA_PATH:
        loader = DataLoader(data_path)
        return loader.get_demo_response()
    return data_loader.get_demo_response()


def get_dataset(dataset_id: str) -> DemoResponse:
    """Retrieve preprocessed dataset snapshot by ID or demo dataset.

    If dataset_id in ("demo", "uci-online-retail-ii-june-2011") or active demo ID:
        Loads demo dataset from demo.json.
    If dataset_id is an uploaded/preprocessed dataset:
        Checks uploads/{dataset_id}/processed.json (or snapshot.json).
    If not found:
        Raises HTTPException(404) with structured error code DATASET_NOT_FOUND.
    """
    normalized_id = dataset_id.strip()

    # Demo dataset aliases and active dataset ID
    if normalized_id in ("demo", "uci-online-retail-ii-june-2011", data_loader.meta.dataset_id):
        return load_demo_data()

    # Search staged / uploaded datasets in configured upload directory and fallbacks
    possible_roots = [
        Path(settings.upload_storage_dir),
        Path(__file__).resolve().parent / "uploads",
        Path(__file__).resolve().parent.parent / "data" / "uploads",
    ]

    for root in possible_roots:
        dataset_dir = root / normalized_id
        for filename in ("processed.json", "snapshot.json"):
            file_path = dataset_dir / filename
            if file_path.exists() and file_path.is_file():
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    return DemoResponse(
                        meta=DatasetMeta.model_validate(data["meta"]),
                        layout=WarehouseLayout.model_validate(data["layout"]),
                        products=[Product.model_validate(p) for p in data["products"]],
                        orders=[Order.model_validate(o) for o in data["orders"]],
                    )
                except Exception as err:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=make_error_detail(
                            ErrorCode.DATASET_NOT_FOUND,
                            f"Corrupted or invalid dataset file at {file_path}: {err}",
                        ).model_dump(),
                    ) from err

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=make_error_detail(
            ErrorCode.DATASET_NOT_FOUND,
            f"Dataset '{dataset_id}' not found",
        ).model_dump(),
    )
