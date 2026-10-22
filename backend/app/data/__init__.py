"""Data access and fixtures."""
from backend.app.data.fixtures import (
    SAMPLE_META,
    SAMPLE_LAYOUT,
    SAMPLE_PRODUCTS,
    SAMPLE_ORDERS,
    get_sample_demo_response,
)
from backend.app.data.loader import DataLoader, data_loader

__all__ = [
    "SAMPLE_META",
    "SAMPLE_LAYOUT",
    "SAMPLE_PRODUCTS",
    "SAMPLE_ORDERS",
    "get_sample_demo_response",
    "DataLoader",
    "data_loader",
]
