#!/usr/bin/env python3
"""
Preprocess one complete month of UCI Online Retail II into ~100 top SKUs,
deterministic pick frequencies, actual order lines, and synthetic warehouse layout.

Citation: Chen, D. (2012), Online Retail II, DOI 10.24432/C5CG6D (CC BY 4.0)
Official workbook SHA256: bcbe73b35f5b7babf197fb0cb983a11f5d9ff929078d4aa53d171b1f2df2e980
"""
import argparse
import hashlib
import json
import os
import random
import sys
from pathlib import Path
from typing import Any

EXPECTED_SHA256 = "bcbe73b35f5b7babf197fb0cb983a11f5d9ff929078d4aa53d171b1f2df2e980"

EXCLUDED_NONPRODUCT_CODES = {
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
}


def compute_sha256(filepath: str) -> str:
    """Compute sha256 checksum of file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


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
            sku = shuffled_skus[slot_index - 1]
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


def preprocess_retail_month(
    filepath: str,
    sheet_name: str = "Year 2010-2011",
    target_month: str = "2011-06",
    num_top_skus: int = 100,
    num_demo_orders: int = 20,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Load workbook, filter month, compute pick frequencies, select top SKUs,
    extract demo orders, and construct demo payload & provenance.
    """
    import pandas as pd

    sha256 = compute_sha256(filepath)
    print(f"Loaded file {filepath} (SHA256: {sha256})")

    df = pd.read_excel(filepath, sheet_name=sheet_name)
    print(f"Total sheet rows: {len(df)}")

    # Normalize column names
    col_map = {}
    for c in df.columns:
        norm = c.strip().lower().replace(" ", "")
        if norm in ("invoice", "invoiceno"):
            col_map[c] = "Invoice"
        elif norm in ("stockcode", "code"):
            col_map[c] = "StockCode"
        elif norm in ("description", "desc"):
            col_map[c] = "Description"
        elif norm in ("quantity", "qty"):
            col_map[c] = "Quantity"
        elif norm in ("invoicedate", "date"):
            col_map[c] = "InvoiceDate"
        elif norm in ("price", "unitprice"):
            col_map[c] = "Price"
        elif norm in ("customerid", "customer"):
            col_map[c] = "CustomerID"
        elif norm in ("country",):
            col_map[c] = "Country"

    df = df.rename(columns=col_map)
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])

    # Filter target calendar month
    df["YearMonth"] = df["InvoiceDate"].dt.strftime("%Y-%m")
    month_df = df[df["YearMonth"] == target_month].copy()
    month_rows = len(month_df)
    print(f"Rows in month {target_month}: {month_rows}")

    # Track filter statistics
    is_cancelled = month_df["Invoice"].astype(str).str.upper().str.startswith("C")
    cancelled_count = int(is_cancelled.sum())

    is_nonpos_qty = (month_df["Quantity"].isna()) | (month_df["Quantity"] <= 0)
    nonpos_qty_count = int(is_nonpos_qty.sum())

    month_df["StockCodeClean"] = month_df["StockCode"].astype(str).str.strip().str.upper()
    is_blank_or_nonproduct = (
        month_df["StockCode"].isna()
        | (month_df["StockCodeClean"] == "")
        | (month_df["StockCodeClean"].isin(EXCLUDED_NONPRODUCT_CODES))
    )
    nonproduct_count = int(is_blank_or_nonproduct.sum())

    # Valid positive product lines
    valid_df = month_df[
        (~is_cancelled) & (~is_nonpos_qty) & (~is_blank_or_nonproduct)
    ].copy()
    valid_lines = len(valid_df)
    print(f"Valid positive product lines: {valid_lines}")

    # Compute pick frequency: count of picking lines per SKU (NOT sum of units)
    sku_freq = valid_df.groupby("StockCodeClean").size()
    # Most common description for each SKU
    sku_desc = (
        valid_df.groupby("StockCodeClean")["Description"]
        .agg(lambda s: s.mode().iloc[0] if not s.empty and not pd.isna(s.mode().iloc[0]) else "Product")
        .to_dict()
    )

    # Sort descending by pick frequency, tie-break SKU ascending
    sorted_skus = sorted(
        sku_freq.index.tolist(),
        key=lambda s: (-sku_freq[s], s),
    )
    top_100_skus = sorted_skus[:num_top_skus]
    top_100_set = set(top_100_skus)

    products: list[dict[str, Any]] = []
    for s in top_100_skus:
        name = str(sku_desc.get(s, "Product")).strip()
        products.append({
            "sku": s,
            "name": name,
            "pick_frequency": int(sku_freq[s]),
        })

    # Filter valid lines to top 100 SKUs
    top_df = valid_df[valid_df["StockCodeClean"].isin(top_100_set)].copy()
    top_sku_lines = len(top_df)
    top_sku_invoices = top_df["Invoice"].nunique()

    # Extract first N orders in stable order of appearance (first line timestamp)
    order_first_ts = top_df.groupby("Invoice")["InvoiceDate"].min().sort_values()
    selected_invoice_ids = order_first_ts.index.tolist()[:num_demo_orders]

    orders: list[dict[str, Any]] = []
    for inv in selected_invoice_ids:
        inv_lines = top_df[top_df["Invoice"] == inv]
        # Aggregate quantity per SKU within the order if repeated
        line_items: list[dict[str, Any]] = []
        for sku, group in inv_lines.groupby("StockCodeClean", sort=False):
            line_items.append({
                "sku": sku,
                "quantity": int(group["Quantity"].sum()),
            })
        if line_items:
            orders.append({
                "order_id": str(inv),
                "lines": line_items,
            })

    # Warehouse layout
    layout = generate_synthetic_21x21_layout(top_100_skus)

    dataset_id = f"uci-{target_month}-preview-{sha256[:12]}"
    meta = {
        "dataset_id": dataset_id,
        "source": "UCI Online Retail II",
        "month": target_month,
        "real_order_data": True,
        "synthetic_warehouse": True,
        "cell_size_m": 1.5,
    }

    demo_payload = {
        "meta": meta,
        "layout": layout,
        "products": products,
        "orders": orders,
    }

    provenance = {
        "purpose": "Authoritative real-data export for Warehouse Intelligence Twin simulation.",
        "source_url": "https://archive.ics.uci.edu/dataset/502/online+retail+ii",
        "citation": "Chen, D. (2012), Online Retail II, DOI 10.24432/C5CG6D",
        "license": "CC BY 4.0",
        "workbook_sha256": sha256,
        "sheet": sheet_name,
        "month": target_month,
        "time_assumption": "Source naive invoice dates; calendar month without timezone conversion.",
        "month_rows": month_rows,
        "cancelled_month_rows": cancelled_count,
        "nonpositive_or_missing_quantity_rows": nonpos_qty_count,
        "nonproduct_or_blank_sku_rows": nonproduct_count,
        "filter_counts_overlap": True,
        "excluded_nonproduct_codes": sorted(list(EXCLUDED_NONPRODUCT_CODES)),
        "valid_positive_product_lines": valid_lines,
        "top_sku_count": len(top_100_skus),
        "pick_frequency_definition": "Number of retained positive picking lines per SKU in the complete month; not units.",
        "top_sku_month_lines": top_sku_lines,
        "top_sku_month_order_count": top_sku_invoices,
        "selected_order_count": len(orders),
        "selected_order_ids": [o["order_id"] for o in orders],
        "selection": f"First {len(orders)} invoices by first retained line timestamp, stable source row order; each order restricted to top 100 SKUs.",
        "warehouse": "Synthetic 21x21 grid, 1.5m cells, 100 fixed racks, 341 walkable cells, dock[0,0]; slot assignments seeded with Python Random(42).",
    }

    return demo_payload, provenance


def main():
    parser = argparse.ArgumentParser(description="Preprocess UCI Online Retail II dataset")
    parser.add_argument(
        "--input",
        type=str,
        default="/home/bread/Documents/Codex/2026-10-22/you-are-the-technical-lead-github/work/datasets/online-retail-ii/online_retail_II.xlsx",
        help="Path to online_retail_II.xlsx",
    )
    parser.add_argument("--sheet", type=str, default="Year 2010-2011")
    parser.add_argument("--month", type=str, default="2011-06")
    parser.add_argument("--top-skus", type=int, default=100)
    parser.add_argument("--orders", type=int, default=20)
    parser.add_argument(
        "--output-json",
        type=str,
        default="backend/app/data/demo.json",
        help="Output path for preprocessed demo JSON",
    )
    parser.add_argument(
        "--output-provenance",
        type=str,
        default="backend/app/data/demo-provenance.json",
        help="Output path for provenance JSON",
    )
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: Dataset not found at {args.input}", file=sys.stderr)
        sys.exit(1)

    demo, prov = preprocess_retail_month(
        filepath=args.input,
        sheet_name=args.sheet,
        target_month=args.month,
        num_top_skus=args.top_skus,
        num_demo_orders=args.orders,
    )

    out_json = Path(args.output_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(demo, f, indent=2)
    print(f"Wrote preprocessed snapshot to {out_json}")

    out_prov = Path(args.output_provenance)
    out_prov.parent.mkdir(parents=True, exist_ok=True)
    with open(out_prov, "w", encoding="utf-8") as f:
        json.dump(prov, f, indent=2)
    print(f"Wrote provenance metadata to {out_prov}")


if __name__ == "__main__":
    main()
