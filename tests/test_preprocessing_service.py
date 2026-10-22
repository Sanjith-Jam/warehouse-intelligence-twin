"""Tests for backend preprocessing service (FLASH-04).

Verifies arbitrary dataset preprocessing with custom column mappings,
business exclusion rules, pick frequency calculation, small dataset handling
without fake EMPTY_* products, deterministic repeat runs, and error handling.
"""
import hashlib
from pathlib import Path
import pytest
import pandas as pd
import openpyxl

from backend.app.models.schemas import (
    CleaningReport,
    ColumnMapping,
    DemoResponse,
    ErrorCode,
    PreprocessRequest,
)
from backend.app.services.preprocessing import (
    PreprocessingError,
    generate_synthetic_21x21_layout,
    preprocess_dataset,
)


def create_csv_file(path: Path, rows: list[dict[str, str | int | float | None]]) -> Path:
    """Helper to write rows into a CSV file."""
    df = pd.DataFrame(rows)
    df.to_csv(path, index=False)
    return path


def create_xlsx_file(path: Path, sheet_name: str, rows: list[dict[str, str | int | float | None]]) -> Path:
    """Helper to write rows into an XLSX workbook."""
    df = pd.DataFrame(rows)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
    return path


# ==============================================================================
# 1. Custom Column Mapping & Exclusion Business Rules
# ==============================================================================

def test_preprocessing_synthetic_csv_custom_columns(tmp_path):
    """Verify custom column mappings, exclusions, frequency count, and deterministic orders."""
    csv_path = tmp_path / "custom_orders.csv"
    rows = [
        # Target month: 2023-05
        # Order 1 (Time 10:00:00): contains SKU_ALPHA and SKU_BETA
        {
            "OrderRef": "ORD100",
            "PartNum": "SKU_ALPHA",
            "ItemName": "Alpha Widget",
            "ItemCount": 10,
            "OrderTime": "2023-05-01 10:00:00",
        },
        {
            "OrderRef": "ORD100",
            "PartNum": "SKU_BETA",
            "ItemName": "Beta Widget",
            "ItemCount": 5,
            "OrderTime": "2023-05-01 10:00:00",
        },
        # Order 2 (Time 11:00:00): contains SKU_ALPHA
        {
            "OrderRef": "ORD101",
            "PartNum": "SKU_ALPHA",
            "ItemName": "Alpha Widget",
            "ItemCount": 2,
            "OrderTime": "2023-05-01 11:00:00",
        },
        # Order 3 (Time 12:00:00): contains SKU_GAMMA with huge unit count (500 units)
        # Should have pick_frequency = 1 (lines count), NOT 500!
        {
            "OrderRef": "ORD102",
            "PartNum": "SKU_GAMMA",
            "ItemName": "Gamma Widget",
            "ItemCount": 500,
            "OrderTime": "2023-05-01 12:00:00",
        },
        # Order 4 (Time 13:00:00): contains SKU_ALPHA
        {
            "OrderRef": "ORD103",
            "PartNum": "SKU_ALPHA",
            "ItemName": "Alpha Widget",
            "ItemCount": 1,
            "OrderTime": "2023-05-01 13:00:00",
        },
        # Excluded 1: Cancelled order (startswith C)
        {
            "OrderRef": "C_ORD999",
            "PartNum": "SKU_ALPHA",
            "ItemName": "Alpha Widget",
            "ItemCount": 10,
            "OrderTime": "2023-05-01 14:00:00",
        },
        # Excluded 2: Nonpositive quantity (<= 0)
        {
            "OrderRef": "ORD104",
            "PartNum": "SKU_ALPHA",
            "ItemName": "Alpha Widget",
            "ItemCount": 0,
            "OrderTime": "2023-05-01 14:30:00",
        },
        # Excluded 3: Non-product code (POST)
        {
            "OrderRef": "ORD105",
            "PartNum": "POST",
            "ItemName": "Postage",
            "ItemCount": 1,
            "OrderTime": "2023-05-01 15:00:00",
        },
        # Excluded 4: Blank SKU
        {
            "OrderRef": "ORD106",
            "PartNum": "",
            "ItemName": "Empty Item",
            "ItemCount": 1,
            "OrderTime": "2023-05-01 15:30:00",
        },
        # Out-of-month row: 2023-04
        {
            "OrderRef": "ORD050",
            "PartNum": "SKU_ALPHA",
            "ItemName": "Alpha Widget",
            "ItemCount": 5,
            "OrderTime": "2023-04-30 23:59:00",
        },
    ]
    create_csv_file(csv_path, rows)

    req = PreprocessRequest(
        target_month="2023-05",
        top_skus=10,
        max_orders=2,
        column_mapping={
            "invoice": "OrderRef",
            "sku": "PartNum",
            "description": "ItemName",
            "quantity": "ItemCount",
            "date": "OrderTime",
        },
    )

    demo, report = preprocess_dataset(csv_path, req)

    assert isinstance(demo, DemoResponse)
    assert isinstance(report, CleaningReport)

    # Verify cleaning report counts for month 2023-05 (9 month rows total)
    assert report.month_rows == 9
    assert report.cancelled_month_rows == 1
    assert report.nonpositive_or_missing_quantity_rows == 1
    assert report.nonproduct_or_blank_sku_rows == 2  # "POST" and ""
    assert report.valid_positive_product_lines == 5  # 3 SKU_ALPHA, 1 SKU_BETA, 1 SKU_GAMMA
    assert report.top_sku_count == 3

    # Verify pick frequency ranking (count of lines, NOT unit quantity):
    # SKU_ALPHA: 3 lines
    # SKU_BETA: 1 line (tie-broken by SKU ascending vs SKU_GAMMA)
    # SKU_GAMMA: 1 line
    assert len(demo.products) == 3
    assert demo.products[0].sku == "SKU_ALPHA"
    assert demo.products[0].pick_frequency == 3
    assert demo.products[1].sku == "SKU_BETA"
    assert demo.products[1].pick_frequency == 1
    assert demo.products[2].sku == "SKU_GAMMA"
    assert demo.products[2].pick_frequency == 1

    # Verify max_orders=2 selects first 2 orders deterministically: ORD100 and ORD101
    assert len(demo.orders) == 2
    assert demo.orders[0].order_id == "ORD100"
    assert len(demo.orders[0].lines) == 2
    assert demo.orders[0].lines[0].sku == "SKU_ALPHA"
    assert demo.orders[0].lines[0].quantity == 10
    assert demo.orders[0].lines[1].sku == "SKU_BETA"
    assert demo.orders[0].lines[1].quantity == 5

    assert demo.orders[1].order_id == "ORD101"
    assert demo.orders[1].lines[0].sku == "SKU_ALPHA"
    assert demo.orders[1].lines[0].quantity == 2


# ==============================================================================
# 2. Small Dataset Handling (< 100 SKUs) & No Fake EMPTY_* Products
# ==============================================================================

def test_preprocessing_small_dataset_no_empty_products(tmp_path):
    """Verify small datasets (< 100 SKUs) retain only real products and never inject EMPTY_* items."""
    csv_path = tmp_path / "small_dataset.csv"
    skus = ["WIDGET_A", "WIDGET_B", "WIDGET_C", "WIDGET_D", "WIDGET_E"]
    rows = []
    for i, sku in enumerate(skus):
        rows.append({
            "Invoice": f"INV{100 + i}",
            "StockCode": sku,
            "Description": f"Description for {sku}",
            "Quantity": (i + 1) * 2,
            "InvoiceDate": f"2023-06-01 10:{i:02d}:00",
        })

    create_csv_file(csv_path, rows)

    req = PreprocessRequest(
        target_month="2023-06",
        top_skus=100,  # Request 100, but dataset only has 5
        max_orders=10,
    )

    demo, report = preprocess_dataset(csv_path, req)

    # Exact product count must be 5, matching available valid SKUs
    assert len(demo.products) == 5
    assert report.top_sku_count == 5

    # NEVER inject fake EMPTY_* items into products catalog!
    for p in demo.products:
        assert not p.sku.startswith("EMPTY_"), f"Fake product SKU detected: {p.sku}"
        assert not p.name.startswith("EMPTY_"), f"Fake product name detected: {p.name}"

    # Warehouse layout retains 100 physical slots in 21x21 scene
    assert len(demo.layout.slots) == 100
    occupied_slots = [s for s in demo.layout.slots if not s.sku.startswith("EMPTY_")]
    empty_slots = [s for s in demo.layout.slots if s.sku.startswith("EMPTY_")]

    assert len(occupied_slots) == 5
    assert len(empty_slots) == 95
    assert set(s.sku for s in occupied_slots) == set(skus)
    assert empty_slots[0].sku == "EMPTY_006"
    assert empty_slots[-1].sku == "EMPTY_100"


# ==============================================================================
# 3. Deterministic Repeat Runs
# ==============================================================================

def test_preprocessing_deterministic_repeat_runs(tmp_path):
    """Verify repeat runs produce identical JSON outputs and hash."""
    csv_path = tmp_path / "repeat_test.csv"
    rows = []
    for i in range(15):
        sku = f"SKU_{i % 5:02d}"
        rows.append({
            "invoiceno": f"INV{i}",
            "stockcode": sku,
            "description": f"Item {sku}",
            "quantity": (i % 3) + 1,
            "invoicedate": f"2023-07-0{1 + (i % 5)} 10:00:00",
        })
    create_csv_file(csv_path, rows)

    req = PreprocessRequest(target_month="2023-07", top_skus=5, max_orders=5)

    demo1, report1 = preprocess_dataset(csv_path, req)
    demo2, report2 = preprocess_dataset(csv_path, req)

    hash1 = hashlib.sha256(demo1.model_dump_json().encode("utf-8")).hexdigest()
    hash2 = hashlib.sha256(demo2.model_dump_json().encode("utf-8")).hexdigest()
    assert hash1 == hash2, "Repeat runs must produce identical serialized demo responses!"

    rep_hash1 = hashlib.sha256(report1.model_dump_json().encode("utf-8")).hexdigest()
    rep_hash2 = hashlib.sha256(report2.model_dump_json().encode("utf-8")).hexdigest()
    assert rep_hash1 == rep_hash2, "Repeat runs must produce identical cleaning reports!"


# ==============================================================================
# 4. Canonical Column Auto-Detection
# ==============================================================================

def test_preprocessing_auto_detected_columns(tmp_path):
    """Verify automatic detection of common column aliases without explicit overrides."""
    csv_path = tmp_path / "autodetect.csv"
    rows = [
        {
            "BillNo": "INV001",
            "ItemCode": "ITEM1",
            "Name": "Widget 1",
            "Units": 10,
            "Datetime": "2023-08-10 12:00:00",
        },
    ]
    create_csv_file(csv_path, rows)

    req = PreprocessRequest(target_month="2023-08", top_skus=10)
    demo, report = preprocess_dataset(csv_path, req)

    assert len(demo.products) == 1
    assert demo.products[0].sku == "ITEM1"
    assert demo.products[0].name == "Widget 1"
    assert len(demo.orders) == 1
    assert demo.orders[0].lines[0].quantity == 10


# ==============================================================================
# 5. Error Handling: Missing Columns & No Data in Month
# ==============================================================================

def test_preprocessing_missing_required_columns(tmp_path):
    """Verify PreprocessingError with MISSING_REQUIRED_COLUMNS when required field absent."""
    csv_path = tmp_path / "missing_cols.csv"
    rows = [{"Invoice": "100", "Description": "Test"}]  # Missing SKU, Quantity, Date
    create_csv_file(csv_path, rows)

    req = PreprocessRequest(target_month="2023-08")
    with pytest.raises(PreprocessingError) as exc_info:
        preprocess_dataset(csv_path, req)

    assert exc_info.value.code == ErrorCode.MISSING_REQUIRED_COLUMNS
    assert "sku" in exc_info.value.details["missing_columns"]


def test_preprocessing_no_data_in_month(tmp_path):
    """Verify PreprocessingError with NO_DATA_IN_MONTH when target month has no records."""
    csv_path = tmp_path / "different_month.csv"
    rows = [
        {
            "Invoice": "INV001",
            "StockCode": "SKU1",
            "Quantity": 1,
            "InvoiceDate": "2023-01-15 10:00:00",
        }
    ]
    create_csv_file(csv_path, rows)

    req = PreprocessRequest(target_month="2023-09")
    with pytest.raises(PreprocessingError) as exc_info:
        preprocess_dataset(csv_path, req)

    assert exc_info.value.code == ErrorCode.NO_DATA_IN_MONTH


def test_preprocessing_all_rows_filtered_out(tmp_path):
    """Verify PreprocessingError with NO_DATA_IN_MONTH when all lines in month are cancelled/nonpositive."""
    csv_path = tmp_path / "all_cancelled.csv"
    rows = [
        # All cancelled
        {
            "Invoice": "C1001",
            "StockCode": "SKU1",
            "Quantity": 10,
            "InvoiceDate": "2023-05-15 10:00:00",
        },
        # Or non-positive quantity
        {
            "Invoice": "INV1002",
            "StockCode": "SKU2",
            "Quantity": 0,
            "InvoiceDate": "2023-05-15 10:00:00",
        },
    ]
    create_csv_file(csv_path, rows)

    req = PreprocessRequest(target_month="2023-05")
    with pytest.raises(PreprocessingError) as exc_info:
        preprocess_dataset(csv_path, req)

    assert exc_info.value.code == ErrorCode.NO_DATA_IN_MONTH


# ==============================================================================
# 6. Excel Workbook (.xlsx) Processing
# ==============================================================================

def test_preprocessing_excel_workbook(tmp_path):
    """Verify preprocess_dataset works seamlessly with multi-sheet XLSX workbooks."""
    xlsx_path = tmp_path / "sample_retail.xlsx"
    rows = [
        {
            "Invoice": "55001",
            "StockCode": "EXCEL_SKU",
            "Description": "Excel Item",
            "Quantity": 7,
            "InvoiceDate": "2023-10-15 09:30:00",
        }
    ]
    create_xlsx_file(xlsx_path, "CustomSheet", rows)

    req = PreprocessRequest(
        target_month="2023-10",
        sheet_name="CustomSheet",
        top_skus=10,
    )
    demo, report = preprocess_dataset(xlsx_path, req)

    assert report.sheet == "CustomSheet"
    assert report.valid_positive_product_lines == 1
    assert len(demo.products) == 1
    assert demo.products[0].sku == "EXCEL_SKU"
    assert demo.products[0].pick_frequency == 1
