"""Dataset storage and lifecycle service for managing uploaded and preprocessed snapshots."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Optional
import uuid

from backend.app.config import settings
from backend.app.data.loader import DEFAULT_DATA_PATH, data_loader, load_demo_data
from backend.app.models.schemas import (
    CleaningReport,
    DatasetDetailResponse,
    DatasetExportResponse,
    DatasetMeta,
    Order,
    PreprocessRequest,
    Product,
    WarehouseLayout,
)
from backend.app.services.parsing import get_dataset_dir, get_dataset_meta
from backend.app.services.preprocessing import PreprocessingError, preprocess_dataset


class DatasetStoreError(Exception):
    """Base exception for dataset store errors."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class DatasetNotFoundError(DatasetStoreError):
    """Raised when the requested dataset does not exist."""


class DatasetNotPreprocessedError(DatasetStoreError):
    """Raised when a dataset was uploaded but has not yet been preprocessed."""


class ImmutableDatasetError(DatasetStoreError):
    """Raised when an operation attempts to modify the immutable demo dataset."""


def _get_demo_provenance_path() -> Path:
    return Path(__file__).resolve().parent.parent / "data" / "demo-provenance.json"


def get_dataset_detail(dataset_id: str, base_dir: Optional[Path | str] = None) -> DatasetDetailResponse:
    """Retrieve complete preprocessed dataset details including metadata, cleaning report, layout, products, and orders."""
    normalized_id = dataset_id.strip()

    # Built-in demo dataset
    if normalized_id in ("demo", "uci-online-retail-ii-june-2011", data_loader.meta.dataset_id):
        demo_resp = load_demo_data()
        prov_path = _get_demo_provenance_path()
        if prov_path.exists():
            with open(prov_path, "r", encoding="utf-8") as f:
                prov_dict = json.load(f)
            cleaning_report = CleaningReport.model_validate(prov_dict)
        else:
            cleaning_report = CleaningReport(
                purpose="Authoritative shared June 2011 UCI order snapshot",
                month=demo_resp.meta.month or "2011-06",
                valid_positive_product_lines=len(demo_resp.products),
                top_sku_count=len(demo_resp.products),
                selected_order_count=len(demo_resp.orders),
            )

        return DatasetDetailResponse(
            meta=demo_resp.meta,
            cleaning_report=cleaning_report,
            layout=demo_resp.layout,
            products=demo_resp.products,
            orders=demo_resp.orders,
        )

    # Search uploaded dataset directory
    ds_dir = get_dataset_dir(normalized_id, base_dir)
    if not ds_dir.exists() or not ds_dir.is_dir():
        raise DatasetNotFoundError(f"Dataset '{dataset_id}' not found.")

    meta = get_dataset_meta(normalized_id, base_dir)
    if not meta:
        raise DatasetNotFoundError(f"Dataset '{dataset_id}' metadata is missing.")

    # Check for processed snapshot
    processed_path = ds_dir / "processed.json"
    if not processed_path.exists():
        snapshot_path = ds_dir / "snapshot.json"
        if snapshot_path.exists():
            processed_path = snapshot_path
        else:
            raise DatasetNotPreprocessedError(
                f"Dataset '{dataset_id}' has not been preprocessed yet. Run POST /api/datasets/{dataset_id}/preprocess first."
            )

    with open(processed_path, "r", encoding="utf-8") as f:
        processed_data = json.load(f)

    # Load cleaning report / provenance
    cleaning_report_path = ds_dir / "cleaning_report.json"
    if cleaning_report_path.exists():
        with open(cleaning_report_path, "r", encoding="utf-8") as f:
            cleaning_dict = json.load(f)
        cleaning_report = CleaningReport.model_validate(cleaning_dict)
    elif "provenance" in processed_data or "cleaning_report" in processed_data:
        report_data = processed_data.get("cleaning_report") or processed_data.get("provenance")
        cleaning_report = CleaningReport.model_validate(report_data)
    else:
        cleaning_report = CleaningReport(
            purpose=f"Preprocessed snapshot for {dataset_id}",
            month=processed_data.get("meta", {}).get("month") or "unknown",
            valid_positive_product_lines=len(processed_data.get("products", [])),
            top_sku_count=len(processed_data.get("products", [])),
            selected_order_count=len(processed_data.get("orders", [])),
        )

    return DatasetDetailResponse(
        meta=DatasetMeta.model_validate(processed_data["meta"]),
        cleaning_report=cleaning_report,
        layout=WarehouseLayout.model_validate(processed_data["layout"]),
        products=[Product.model_validate(p) for p in processed_data["products"]],
        orders=[Order.model_validate(o) for o in processed_data["orders"]],
    )


def preprocess_and_store_dataset(
    dataset_id: str,
    request: PreprocessRequest,
    base_dir: Optional[Path | str] = None,
) -> DatasetDetailResponse:
    """Preprocess an uploaded raw workbook and store the generated snapshot safely."""
    normalized_id = dataset_id.strip()

    if normalized_id in ("demo", "uci-online-retail-ii-june-2011", data_loader.meta.dataset_id):
        raise ImmutableDatasetError("The built-in demo dataset is immutable and cannot be re-preprocessed.")

    ds_dir = get_dataset_dir(normalized_id, base_dir)
    if not ds_dir.exists() or not ds_dir.is_dir():
        raise DatasetNotFoundError(f"Dataset '{dataset_id}' not found.")

    meta = get_dataset_meta(normalized_id, base_dir)
    if not meta:
        raise DatasetNotFoundError(f"Dataset '{dataset_id}' metadata is missing.")

    # Locate raw file
    raw_files = list(ds_dir.glob("raw.*"))
    if not raw_files:
        raise DatasetNotFoundError(f"No raw upload file found for dataset '{dataset_id}'.")
    raw_path = raw_files[0]

    # Preprocess dataset
    source_filename = meta.get("filename") or raw_path.name
    demo_response, cleaning_report = preprocess_dataset(
        file_path=raw_path,
        request=request,
        dataset_id=normalized_id,
        source_name=source_filename,
    )

    # Save artifacts into isolated directory
    processed_path = ds_dir / "processed.json"
    with open(processed_path, "w", encoding="utf-8") as f:
        json.dump(demo_response.model_dump(mode="json"), f, indent=2)

    cleaning_report_path = ds_dir / "cleaning_report.json"
    with open(cleaning_report_path, "w", encoding="utf-8") as f:
        json.dump(cleaning_report.model_dump(mode="json"), f, indent=2)

    # Update metadata
    meta["status"] = "preprocessed"
    meta["target_month"] = request.target_month
    meta["top_skus"] = len(demo_response.products)
    meta["order_count"] = len(demo_response.orders)
    meta["snapshot_id"] = demo_response.meta.snapshot_id or f"snap_{uuid.uuid4().hex[:8]}"

    meta_path = ds_dir / "meta.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    return DatasetDetailResponse(
        meta=demo_response.meta,
        cleaning_report=cleaning_report,
        layout=demo_response.layout,
        products=demo_response.products,
        orders=demo_response.orders,
    )


def export_dataset(
    dataset_id: str,
    export_format: str = "json",
    base_dir: Optional[Path | str] = None,
) -> tuple[DatasetExportResponse, Path]:
    """Prepare a downloadable export file (JSON or CSV) for a dataset."""
    normalized_id = dataset_id.strip()
    fmt = export_format.lower().strip()
    if fmt not in ("json", "csv"):
        raise DatasetStoreError(f"Unsupported export format '{export_format}'. Must be 'json' or 'csv'.")

    # Fetch dataset details (validates existence and preprocessed state)
    detail = get_dataset_detail(normalized_id, base_dir)

    ds_dir = get_dataset_dir(normalized_id, base_dir) if normalized_id not in ("demo", "uci-online-retail-ii-june-2011") else Path(__file__).resolve().parent.parent / "data"

    if fmt == "json":
        export_file = ds_dir / "processed.json" if ds_dir.exists() and (ds_dir / "processed.json").exists() else DEFAULT_DATA_PATH
        file_size = export_file.stat().st_size
        return (
            DatasetExportResponse(
                dataset_id=normalized_id,
                format="json",
                download_url=f"/api/datasets/{normalized_id}/download?format=json",
                record_count=len(detail.products),
                file_size_bytes=file_size,
            ),
            export_file,
        )

    # CSV format: export products catalog
    csv_file = ds_dir / "products_export.csv"
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["sku", "name", "pick_frequency"])
        for p in detail.products:
            writer.writerow([p.sku, p.name, p.pick_frequency])

    file_size = csv_file.stat().st_size
    return (
        DatasetExportResponse(
            dataset_id=normalized_id,
            format="csv",
            download_url=f"/api/datasets/{normalized_id}/download?format=csv",
            record_count=len(detail.products),
            file_size_bytes=file_size,
        ),
        csv_file,
    )
