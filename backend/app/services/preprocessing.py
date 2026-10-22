"""Reusable retail dataset preprocessing service.

Processes uploaded CSV/Excel workbooks or local files with arbitrary column mappings,
target month filtering, SKU frequency ranking, and synthetic warehouse layout generation.
Produces canonical DemoResponse and CleaningReport schemas.
"""
import hashlib
from pathlib import Path
import random
import sys
from typing import Any, Optional

import pandas as pd

from backend.app.models.schemas import (
    REQUIRED_CANONICAL_COLUMNS,
    CleaningReport,
    ColumnMapping,
    DatasetMeta,
    DemoResponse,
    ErrorCode,
    Order,
    OrderLine,
    PreprocessRequest,
    Product,
    WarehouseLayout,
    detect_canonical_columns,
)
from backend.app.services.parsing import (
    ParsingError,
    read_sheet_dataframe,
    validate_file_content,
)

EXPECTED_SHA256 = "bcbe73b35f5b7babf197fb0cb983a11f5d9ff929078d4aa53d171b1f2df2e980"
UCI_PAGE_URL = "https://archive.ics.uci.edu/dataset/502/online+retail+ii"
UCI_DOWNLOAD_URL = "https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip"

EXCLUDED_NONPRODUCT_CODES = [
    "POST",
    "DOT",
    "M",
    "D",
    "BANK CHARGES",
    "AMAZONFEE",
    "C2",
    "CRUK",
    "S",
    "PADS",
    "B",
    "ADJUST",
    "ADJUST2",
    "TEST001",
    "TEST002",
    "SAMPLES",
]


class PreprocessingError(ParsingError):
    """Exception raised during dataset preprocessing."""


def compute_sha256(filepath: str | Path) -> str:
    """Compute sha256 checksum of file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def validate_workbook_checksum(filepath: str | Path, allow_mismatch: bool = False) -> str:
    """Verify workbook SHA-256 against expected official hash."""
    sha256 = compute_sha256(str(filepath))
    if sha256 != EXPECTED_SHA256:
        msg = (
            f"Error: Source workbook SHA-256 checksum mismatch!\n"
            f"  File:     {filepath}\n"
            f"  Expected: {EXPECTED_SHA256}\n"
            f"  Actual:   {sha256}\n\n"
            f"Official source: {UCI_PAGE_URL}\n"
            "If using an intentional variation or test fixture, pass --allow-hash-mismatch."
        )
        if not allow_mismatch:
            print(msg, file=sys.stderr)
            sys.exit(1)
        else:
            print(f"Warning: SHA-256 mismatch ignored due to --allow-hash-mismatch:\n  {sha256}", file=sys.stderr)
    return sha256


def generate_synthetic_21x21_layout(top_skus: list[str]) -> dict[str, Any]:
    """
    Generate synthetic 21x21 warehouse floor with 100 shelf slots,
    dock at [0, 0], and walkable aisles matching the authoritative frontend scene.
    """
    width = 21
    height = 21
    dock = [0, 0]

    # Walkable aisles: outer perimeter and cross-aisles
    # Walkable cells: x in [0..20] where x is even OR z is even
    walkable_cells: list[list[int]] = []
    for z in range(height):
        for x in range(width):
            if x % 2 == 0 or z % 2 == 0:
                walkable_cells.append([x, z])

    # 100 rack slots on impassable cells (odd x, odd z)
    # Rack cells at x in [1, 3, 5, 7, 9, 11, 13, 15, 17, 19] (10 columns)
    # and z in [1, 3, 5, 7, 9, 11, 13, 15, 17, 19] (10 rows) -> 10 x 10 = 100 slots
    # Access cell is immediately South: [x, z - 1], which has even z and is walkable!
    # Initial SKU placement uses seeded shuffle Random(42)
    shuffled_skus = list(top_skus)
    rng = random.Random(42)
    rng.shuffle(shuffled_skus)

    slots: list[dict[str, Any]] = []
    slot_index = 1
    for z in [1, 3, 5, 7, 9, 11, 13, 15, 17, 19]:
        for x in [1, 3, 5, 7, 9, 11, 13, 15, 17, 19]:
            slot_id = f"S{slot_index:03d}"
            sku = shuffled_skus[slot_index - 1] if slot_index - 1 < len(shuffled_skus) else f"EMPTY_{slot_index:03d}"
            slots.append({
                "slot_id": slot_id,
                "rack_cell": [x, z],
                "access_cell": [x, z - 1],
                "sku": sku,
            })
            slot_index += 1

    return {
        "layout_id": "original",
        "width": width,
        "height": height,
        "walkable_cells": walkable_cells,
        "dock": dock,
        "slots": slots,
    }


def _process_dataset_core(
    file_path: Path,
    target_month: str,
    top_skus: int = 100,
    max_orders: int = 20,
    sheet_name: Optional[str] = None,
    column_mapping: Optional[dict[str, str] | ColumnMapping] = None,
    cell_size_m: float = 1.5,
    dataset_id: Optional[str] = None,
    source_name: Optional[str] = None,
    sha256: Optional[str] = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Internal core extraction pipeline returning raw JSON-serializable payloads."""
    file_path = Path(file_path)
    ext = file_path.suffix.lower()

    # 1. Validate file content and structure
    validate_file_content(file_path, ext)

    # 2. Read sheet dataframe
    target_sheet = None if ext == ".csv" else sheet_name
    df, available_sheets = read_sheet_dataframe(file_path, ext, target_sheet=target_sheet)
    actual_sheet = target_sheet if target_sheet else (available_sheets[0] if available_sheets else None)

    # 3. Detect canonical columns and apply custom mapping overrides
    detected, _ = detect_canonical_columns(df.columns.tolist())
    col_map = dict(detected)

    if column_mapping:
        if isinstance(column_mapping, ColumnMapping):
            overrides = column_mapping.model_dump(exclude_none=True)
        elif isinstance(column_mapping, dict):
            overrides = {k: v for k, v in column_mapping.items() if v}
        else:
            overrides = {}
        col_map.update(overrides)

    missing_required = [
        req for req in REQUIRED_CANONICAL_COLUMNS
        if req not in col_map or col_map[req] not in df.columns
    ]
    if missing_required:
        raise PreprocessingError(
            ErrorCode.MISSING_REQUIRED_COLUMNS,
            f"Missing required canonical columns: {missing_required}. Available columns: {list(df.columns)}",
            {"missing_columns": missing_required, "available_columns": list(df.columns)},
        )

    col_invoice = col_map["invoice"]
    col_sku = col_map["sku"]
    col_qty = col_map["quantity"]
    col_date = col_map["date"]
    col_desc = col_map.get("description")
    if col_desc and col_desc not in df.columns:
        col_desc = None

    # 4. Filter target calendar month
    parsed_dates = pd.to_datetime(df[col_date], errors="coerce")
    year_months = parsed_dates.dt.strftime("%Y-%m")
    month_mask = year_months == target_month
    month_df = df[month_mask].copy()
    month_df["_parsed_date"] = parsed_dates[month_mask]
    month_rows = len(month_df)

    if month_rows == 0:
        raise PreprocessingError(
            ErrorCode.NO_DATA_IN_MONTH,
            f"No records found for target month '{target_month}'",
            {"target_month": target_month},
        )

    # 5. Track filter statistics and exclude invalid rows
    is_cancelled = month_df[col_invoice].astype(str).str.upper().str.startswith("C")
    cancelled_count = int(is_cancelled.sum())

    qty_numeric = pd.to_numeric(month_df[col_qty], errors="coerce")
    is_nonpos_qty = (qty_numeric.isna()) | (qty_numeric <= 0)
    nonpos_qty_count = int(is_nonpos_qty.sum())

    month_df["StockCodeClean"] = month_df[col_sku].astype(str).str.strip().str.upper()
    excluded_set = set(EXCLUDED_NONPRODUCT_CODES)
    is_blank_or_nonproduct = (
        month_df[col_sku].isna()
        | (month_df["StockCodeClean"] == "")
        | (month_df["StockCodeClean"].isin(excluded_set | {"NAN", "NULL", "NONE"}))
    )
    nonproduct_count = int(is_blank_or_nonproduct.sum())

    valid_mask = (~is_cancelled) & (~is_nonpos_qty) & (~is_blank_or_nonproduct)
    valid_df = month_df[valid_mask].copy()
    valid_df["QuantityClean"] = qty_numeric[valid_mask].astype(int)
    valid_lines = len(valid_df)

    if valid_lines == 0:
        raise PreprocessingError(
            ErrorCode.NO_DATA_IN_MONTH,
            f"No valid positive product lines found for target month '{target_month}' after exclusions",
            {"target_month": target_month},
        )

    # 6. Compute pick frequency: count of picking lines per SKU (NOT sum of units)
    sku_freq = valid_df.groupby("StockCodeClean").size()

    if col_desc and col_desc in valid_df.columns:
        sku_desc = (
            valid_df.dropna(subset=[col_desc])
            .groupby("StockCodeClean", sort=False)[col_desc]
            .first()
            .to_dict()
        )
    else:
        sku_desc = {}

    # Sort descending by pick frequency, tie-break SKU ascending
    sorted_skus = sorted(
        sku_freq.index.tolist(),
        key=lambda s: (-sku_freq[s], s),
    )
    selected_skus = sorted_skus[:top_skus]
    selected_sku_set = set(selected_skus)

    products: list[dict[str, Any]] = []
    for s in selected_skus:
        name = str(sku_desc.get(s, "Product")).strip()
        products.append({
            "sku": s,
            "name": name,
            "pick_frequency": int(sku_freq[s]),
        })

    # 7. Filter valid lines to selected top SKUs
    top_df = valid_df[valid_df["StockCodeClean"].isin(selected_sku_set)].copy()
    top_sku_lines = len(top_df)
    top_sku_invoices = top_df[col_invoice].nunique()

    # Extract first N orders in stable order of appearance (first line timestamp, tie-broken by source row order)
    order_first_ts = top_df.groupby(col_invoice, sort=False)["_parsed_date"].min().sort_values(kind="stable")
    selected_invoice_ids = [str(inv) for inv in order_first_ts.index.tolist()[:max_orders]]

    orders: list[dict[str, Any]] = []
    for inv in selected_invoice_ids:
        inv_lines = top_df[top_df[col_invoice].astype(str) == str(inv)]
        line_items = [
            {"sku": str(row.StockCodeClean), "quantity": int(row.QuantityClean)}
            for row in inv_lines.itertuples()
        ]
        if line_items:
            orders.append({
                "order_id": str(inv),
                "lines": line_items,
            })

    # 8. Warehouse layout
    layout = generate_synthetic_21x21_layout(selected_skus)

    # 9. Compute metadata and provenance
    if sha256 is None:
        sha256 = compute_sha256(file_path)

    if dataset_id is None:
        dataset_id = f"uci-{target_month}-preview-{sha256[:12]}"

    source = source_name or "UCI Online Retail II"

    meta = {
        "dataset_id": dataset_id,
        "source": source,
        "month": target_month,
        "real_order_data": True,
        "synthetic_warehouse": True,
        "cell_size_m": cell_size_m,
    }

    demo_payload = {
        "meta": meta,
        "layout": layout,
        "products": products,
        "orders": orders,
    }

    selection_desc = (
        f"First {len(orders)} invoices by first retained line timestamp, "
        f"stable source row order; each order restricted to top {len(selected_skus)} SKUs."
    )

    provenance = {
        "purpose": "Authoritative shared June 2011 UCI order snapshot used by the frontend and backend simulation.",
        "source_url": UCI_PAGE_URL,
        "download_url": UCI_DOWNLOAD_URL,
        "citation": "Chen, D. (2012), Online Retail II, DOI 10.24432/C5CG6D",
        "license": "CC BY 4.0",
        "workbook_sha256": sha256,
        "sheet": actual_sheet or (sheet_name or "Year 2010-2011"),
        "month": target_month,
        "time_assumption": "Source naive invoice dates; calendar month without timezone conversion.",
        "month_rows": month_rows,
        "cancelled_month_rows": cancelled_count,
        "nonpositive_or_missing_quantity_rows": nonpos_qty_count,
        "nonproduct_or_blank_sku_rows": nonproduct_count,
        "filter_counts_overlap": True,
        "excluded_nonproduct_codes": list(EXCLUDED_NONPRODUCT_CODES),
        "valid_positive_product_lines": valid_lines,
        "top_sku_count": len(selected_skus),
        "pick_frequency_definition": "Number of retained positive picking lines per SKU in the complete month; not units.",
        "top_sku_month_lines": top_sku_lines,
        "top_sku_month_order_count": top_sku_invoices,
        "selected_order_count": len(orders),
        "selected_order_ids": [o["order_id"] for o in orders],
        "selection": selection_desc,
        "missing_customers": "Retained for picking; customer identifiers are not included in the public snapshot.",
        "warehouse": "Synthetic 21x21 grid, 1.5m cells, 100 fixed racks, 341 walkable cells, dock[0,0]; slot assignments seeded with Python Random(42).",
        "metrics": "This data export contains no route metrics; distance and time are returned by the backend simulation.",
    }

    return demo_payload, provenance


def preprocess_dataset(
    file_path: Path,
    request: PreprocessRequest,
    *,
    dataset_id: Optional[str] = None,
    source_name: Optional[str] = None,
) -> tuple[DemoResponse, CleaningReport]:
    """
    Modular preprocessing service processing any uploaded dataset or workbook.

    Validates file content, maps canonical columns, filters by target calendar month,
    applies business exclusions, ranks SKUs by pick frequency, extracts demo orders,
    and returns canonical (DemoResponse, CleaningReport) Pydantic models.
    """
    file_path = Path(file_path)
    demo_dict, prov_dict = _process_dataset_core(
        file_path=file_path,
        target_month=request.target_month,
        top_skus=request.top_skus,
        max_orders=request.max_orders,
        sheet_name=request.sheet_name,
        column_mapping=request.column_mapping,
        cell_size_m=request.cell_size_m,
        dataset_id=dataset_id,
        source_name=source_name,
    )

    demo_response = DemoResponse.model_validate(demo_dict)
    cleaning_report = CleaningReport.model_validate(prov_dict)
    return demo_response, cleaning_report


def preprocess_retail_month(
    filepath: str | Path,
    sheet_name: str = "Year 2010-2011",
    target_month: str = "2011-06",
    num_top_skus: int = 100,
    num_demo_orders: int = 20,
    allow_hash_mismatch: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Load workbook, verify checksum, filter month, compute pick frequencies, select top SKUs,
    extract demo orders, and construct demo payload & provenance dictionaries.
    Maintains backward compatibility with CLI and official UCI snapshot fixtures.
    """
    filepath = Path(filepath)
    sha256 = validate_workbook_checksum(filepath, allow_mismatch=allow_hash_mismatch)
    print(f"Loaded file {filepath} (SHA256: {sha256})")

    demo_dict, prov_dict = _process_dataset_core(
        file_path=filepath,
        target_month=target_month,
        top_skus=num_top_skus,
        max_orders=num_demo_orders,
        sheet_name=sheet_name,
        cell_size_m=1.5,
        sha256=sha256,
    )

    print(f"Rows in month {target_month}: {prov_dict['month_rows']}")
    print(f"Valid positive product lines: {prov_dict['valid_positive_product_lines']}")

    return demo_dict, prov_dict
