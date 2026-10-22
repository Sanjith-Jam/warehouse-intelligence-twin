"""Unit tests for canonical schemas, column detection, dataset models, and structured errors."""
import json
from pathlib import Path
import pytest
from pydantic import ValidationError

from backend.app.models.schemas import (
    # Error schemas & codes
    ErrorCode,
    ErrorDetail,
    ErrorResponse,
    make_error_detail,
    # Column mapping & aliases
    CANONICAL_COLUMN_ALIASES,
    REQUIRED_CANONICAL_COLUMNS,
    normalize_column_name,
    detect_canonical_columns,
    ColumnMapping,
    # Health check
    HealthResponse,
    # Warehouse & geometry
    Slot,
    WarehouseLayout,
    Product,
    OrderLine,
    Order,
    # Dataset, snapshot & provenance
    DatasetMeta,
    CleaningReport,
    Provenance,
    PreprocessRequest,
    DatasetInspectionResponse,
    DatasetDetailResponse,
    DatasetExportResponse,
    # Layout management
    SaveLayoutRequest,
    LayoutSaveRequest,
    SavedLayout,
    LayoutDetail,
    LayoutsListResponse,
    LayoutListResponse,
    # Legacy / bootstrap responses
    DemoResponse,
    WarehouseResponse,
    OrdersResponse,
    # Simulation schemas
    SimulateRequest,
    RouteVisit,
    OrderRoute,
    SimulationAssumptions,
    SimulateResponse,
)


REPO_ROOT = Path(__file__).resolve().parent.parent
DEMO_PROV_PATH = REPO_ROOT / "backend" / "app" / "data" / "demo-provenance.json"


# ==============================================================================
# 1. Structured Error Schemas & Codes
# ==============================================================================

def test_error_codes_enum_values():
    """Verify all 7 canonical error codes required by FLASH-02 are defined."""
    required_codes = {
        "UNSUPPORTED_FILE_TYPE",
        "FILE_TOO_LARGE",
        "MISSING_REQUIRED_COLUMNS",
        "NO_DATA_IN_MONTH",
        "DATASET_NOT_FOUND",
        "MALFORMED_ORDER",
        "INVALID_SLOT_ASSIGNMENT",
    }
    actual_codes = {code.value for code in ErrorCode}
    assert required_codes.issubset(actual_codes)
    assert ErrorCode.UNSUPPORTED_FILE_TYPE == "UNSUPPORTED_FILE_TYPE"
    assert ErrorCode.FILE_TOO_LARGE == "FILE_TOO_LARGE"
    assert ErrorCode.MISSING_REQUIRED_COLUMNS == "MISSING_REQUIRED_COLUMNS"
    assert ErrorCode.NO_DATA_IN_MONTH == "NO_DATA_IN_MONTH"
    assert ErrorCode.DATASET_NOT_FOUND == "DATASET_NOT_FOUND"
    assert ErrorCode.MALFORMED_ORDER == "MALFORMED_ORDER"
    assert ErrorCode.INVALID_SLOT_ASSIGNMENT == "INVALID_SLOT_ASSIGNMENT"


def test_error_detail_model_and_factories():
    """Test ErrorDetail serialization, string code vs enum code, and details dict."""
    err1 = ErrorDetail(
        code="UNSUPPORTED_FILE_TYPE",
        message="Only .csv, .xlsx, .xls files are supported",
        details={"extension": ".pdf"},
    )
    assert err1.code == "UNSUPPORTED_FILE_TYPE"
    assert err1.message == "Only .csv, .xlsx, .xls files are supported"
    assert err1.details == {"extension": ".pdf"}
    dumped = err1.model_dump()
    assert dumped["code"] == "UNSUPPORTED_FILE_TYPE"
    assert dumped["details"]["extension"] == ".pdf"

    # Test from_code with enum
    err2 = ErrorDetail.from_code(
        ErrorCode.DATASET_NOT_FOUND,
        "Dataset not found",
        {"dataset_id": "ds_123"},
    )
    assert err2.code == "DATASET_NOT_FOUND"

    # Test make_error_detail helper
    err3 = make_error_detail(ErrorCode.FILE_TOO_LARGE, "File exceeds 50MB", {"size": 60000000})
    assert err3.code == "FILE_TOO_LARGE"
    assert err3.details["size"] == 60000000

    # Test without details
    err4 = ErrorDetail(code="MALFORMED_ORDER", message="Order line has invalid SKU")
    assert err4.details is None


def test_error_response_wrapping():
    """Test ErrorResponse wrapper with ErrorDetail and string detail."""
    detail = make_error_detail(ErrorCode.INVALID_SLOT_ASSIGNMENT, "Slot S001 is duplicate")
    resp = ErrorResponse(detail=detail)
    assert isinstance(resp.detail, ErrorDetail)
    assert resp.detail.code == "INVALID_SLOT_ASSIGNMENT"

    # Also supports string detail for backwards compatibility with FastAPI default
    resp_str = ErrorResponse(detail="Internal Server Error")
    assert resp_str.detail == "Internal Server Error"


# ==============================================================================
# 2. Canonical Column Aliases & Detection
# ==============================================================================

def test_canonical_aliases_definitions():
    """Verify alias dictionary contains all 5 required canonical entities."""
    for col in ("invoice", "sku", "description", "quantity", "date"):
        assert col in CANONICAL_COLUMN_ALIASES
        assert len(CANONICAL_COLUMN_ALIASES[col]) > 0


def test_column_name_normalization():
    """Verify normalization strips special characters, spaces, and case."""
    assert normalize_column_name("InvoiceNo") == "invoiceno"
    assert normalize_column_name("Stock Code") == "stockcode"
    assert normalize_column_name("order_id") == "orderid"
    assert normalize_column_name("  Customer ID #  ") == "customerid"


def test_detect_canonical_columns_uci():
    """Verify canonical column detection on UCI Online Retail II headers."""
    uci_headers = ["Invoice", "StockCode", "Description", "Quantity", "InvoiceDate", "Price", "Customer ID", "Country"]
    detected, missing = detect_canonical_columns(uci_headers)

    assert detected["invoice"] == "Invoice"
    assert detected["sku"] == "StockCode"
    assert detected["description"] == "Description"
    assert detected["quantity"] == "Quantity"
    assert detected["date"] == "InvoiceDate"
    assert missing == []


def test_detect_canonical_columns_aliases_and_missing():
    """Verify detection on alternative aliases and reporting missing required columns."""
    custom_headers = ["Order ID", "Product Code", "Qty", "Timestamp"]
    detected, missing = detect_canonical_columns(custom_headers)

    assert detected["invoice"] == "Order ID"
    assert detected["sku"] == "Product Code"
    assert detected["quantity"] == "Qty"
    assert detected["date"] == "Timestamp"
    assert "description" not in detected  # description is optional
    assert missing == []  # All 4 required columns are present

    # Test missing required column
    incomplete_headers = ["Order ID", "Qty"]
    detected, missing = detect_canonical_columns(incomplete_headers)
    assert "sku" in missing
    assert "date" in missing


def test_column_mapping_model():
    """Verify ColumnMapping Pydantic model serialization and defaults."""
    cm = ColumnMapping(invoice="InvoiceNum", sku="ItemID", quantity="Units", date="OrderDate")
    assert cm.invoice == "InvoiceNum"
    assert cm.sku == "ItemID"
    assert cm.description is None
    dumped = cm.model_dump()
    assert dumped["quantity"] == "Units"


# ==============================================================================
# 3. DatasetMeta & Backwards Compatibility
# ==============================================================================

def test_dataset_meta_backwards_compatibility():
    """Verify DatasetMeta handles legacy fixture fields and synchronizes source/source_filename."""
    # Legacy style instantiation (as in fixtures.py and demo.json)
    legacy = DatasetMeta(
        dataset_id="sample-v1",
        source="synthetic fixture",
        month=None,
        real_order_data=False,
        synthetic_warehouse=True,
        cell_size_m=1.5,
    )
    assert legacy.dataset_id == "sample-v1"
    assert legacy.source == "synthetic fixture"
    assert legacy.source_filename == "synthetic fixture"
    assert legacy.snapshot_id == "sample-v1"
    assert legacy.cell_size_m == 1.5

    # New style instantiation (with source_filename and snapshot_id)
    new_meta = DatasetMeta(
        dataset_id="ds_abc123",
        snapshot_id="snap_789",
        source_filename="custom_orders.xlsx",
        month="2011-06",
        created_at="2026-10-22T10:00:00Z",
        top_sku_count=100,
        order_count=20,
        real_order_data=True,
        synthetic_warehouse=True,
        cell_size_m=1.5,
    )
    assert new_meta.source == "custom_orders.xlsx"
    assert new_meta.source_filename == "custom_orders.xlsx"
    assert new_meta.snapshot_id == "snap_789"
    assert new_meta.top_sku_count == 100
    assert new_meta.order_count == 20

    # Serialization round-trip
    serialized = new_meta.model_dump_json()
    deserialized = DatasetMeta.model_validate_json(serialized)
    assert deserialized.dataset_id == new_meta.dataset_id
    assert deserialized.source_filename == new_meta.source_filename


# ==============================================================================
# 4. PreprocessRequest Validation
# ==============================================================================

def test_preprocess_request_defaults_and_validation():
    """Verify PreprocessRequest default values and field validations."""
    req = PreprocessRequest(target_month="2011-06")
    assert req.target_month == "2011-06"
    assert req.sheet_name is None
    assert req.top_skus == 100
    assert req.max_orders == 20
    assert req.cell_size_m == 1.5

    # Target month validation (YYYY-MM)
    with pytest.raises(ValidationError, match="target_month"):
        PreprocessRequest(target_month="2011-13")

    with pytest.raises(ValidationError, match="target_month"):
        PreprocessRequest(target_month="invalid")

    with pytest.raises(ValidationError, match="target_month"):
        PreprocessRequest(target_month="2011/06")

    with pytest.raises(ValidationError, match="target_month"):
        PreprocessRequest(target_month="2011-6")

    # top_skus bounds (ge=1, le=1000)
    with pytest.raises(ValidationError):
        PreprocessRequest(target_month="2011-06", top_skus=0)

    with pytest.raises(ValidationError):
        PreprocessRequest(target_month="2011-06", top_skus=1001)

    # max_orders bounds (ge=1, le=100)
    with pytest.raises(ValidationError):
        PreprocessRequest(target_month="2011-06", max_orders=0)

    with pytest.raises(ValidationError):
        PreprocessRequest(target_month="2011-06", max_orders=101)

    # cell_size_m bounds (gt=0, le=10.0)
    with pytest.raises(ValidationError):
        PreprocessRequest(target_month="2011-06", cell_size_m=0.0)


# ==============================================================================
# 5. DatasetInspectionResponse
# ==============================================================================

def test_dataset_inspection_response():
    """Verify DatasetInspectionResponse model creation, defaults, and serialization."""
    inspection = DatasetInspectionResponse(
        dataset_id="ds_test_123",
        filename="online_retail.xlsx",
        file_size_bytes=1048576,
        sheets=["Year 2009-2010", "Year 2010-2011"],
        detected_columns={"invoice": "Invoice", "sku": "StockCode"},
        missing_required_columns=["date"],
        available_months=["2010-12", "2011-01", "2011-02"],
        total_rows=525461,
        preview_rows=[{"Invoice": "489434", "StockCode": "85048"}],
    )
    assert inspection.dataset_id == "ds_test_123"
    assert inspection.file_size_bytes == 1048576
    assert len(inspection.sheets) == 2
    assert inspection.missing_required_columns == ["date"]
    assert len(inspection.preview_rows) == 1

    # Check serialization
    dumped = inspection.model_dump()
    assert dumped["total_rows"] == 525461

    # Negative sizes rejected
    with pytest.raises(ValidationError):
        DatasetInspectionResponse(
            dataset_id="ds_1",
            filename="test.csv",
            file_size_bytes=-1,
        )


# ==============================================================================
# 6. CleaningReport / Provenance
# ==============================================================================

def test_cleaning_report_provenance_validation():
    """Verify CleaningReport matches actual demo-provenance.json and enforces counts."""
    assert DEMO_PROV_PATH.exists(), f"Missing {DEMO_PROV_PATH}"
    with open(DEMO_PROV_PATH) as f:
        data = json.load(f)

    report = CleaningReport.model_validate(data)
    assert report.month == "2011-06"
    assert report.month_rows == 36874
    assert report.cancelled_month_rows == 711
    assert report.nonpositive_or_missing_quantity_rows == 818
    assert report.nonproduct_or_blank_sku_rows == 241
    assert report.valid_positive_product_lines == 35857
    assert report.top_sku_count == 100
    assert report.top_sku_month_lines == 8927
    assert report.top_sku_month_order_count == 1284
    assert report.selected_order_count == 20
    assert "POST" in report.excluded_nonproduct_codes

    # Verify Provenance alias
    assert Provenance is CleaningReport

    # Verify round-trip serialization
    json_str = report.model_dump_json()
    deserialized = CleaningReport.model_validate_json(json_str)
    assert deserialized.valid_positive_product_lines == 35857


# ==============================================================================
# 7. DatasetDetailResponse
# ==============================================================================

def test_dataset_detail_response():
    """Verify DatasetDetailResponse holds metadata, cleaning report, layout, products, and orders."""
    meta = DatasetMeta(
        dataset_id="ds_test",
        source_filename="test.csv",
        month="2011-06",
        real_order_data=True,
    )
    report = CleaningReport(
        month_rows=1000,
        cancelled_month_rows=50,
        valid_positive_product_lines=900,
    )
    layout = WarehouseLayout(
        layout_id="original",
        width=4,
        height=3,
        walkable_cells=[[0, 0], [1, 0]],
        dock=[0, 0],
        slots=[Slot(slot_id="S001", rack_cell=[1, 1], access_cell=[1, 0], sku="SKU1")],
    )
    products = [Product(sku="SKU1", name="Test Product", pick_frequency=10)]
    orders = [Order(order_id="ORD1", lines=[OrderLine(sku="SKU1", quantity=2)])]

    detail = DatasetDetailResponse(
        meta=meta,
        cleaning_report=report,
        layout=layout,
        products=products,
        orders=orders,
    )
    assert detail.meta.dataset_id == "ds_test"
    assert detail.cleaning_report.valid_positive_product_lines == 900
    assert detail.provenance.valid_positive_product_lines == 900
    assert len(detail.products) == 1
    assert len(detail.orders) == 1

    # Verify provenance alias in constructor
    detail_prov = DatasetDetailResponse(
        meta=meta,
        provenance=report,
        layout=layout,
        products=products,
        orders=orders,
    )
    assert detail_prov.cleaning_report.valid_positive_product_lines == 900


# ==============================================================================
# 8. Layout Saving and Retrieval Schemas
# ==============================================================================

def test_layout_save_and_retrieval_schemas():
    """Verify SaveLayoutRequest, SavedLayout, and LayoutsListResponse."""
    req = SaveLayoutRequest(
        layout_id="player-v1",
        name="Optimized Layout 1",
        description="Layout grouped by pick frequency",
        slot_assignments={"S001": "SKU-TOP-1", "S002": "SKU-TOP-2"},
    )
    assert req.layout_id == "player-v1"
    assert req.slot_assignments["S001"] == "SKU-TOP-1"
    assert LayoutSaveRequest is SaveLayoutRequest

    # Missing slot_assignments or empty layout_id rejected
    with pytest.raises(ValidationError):
        SaveLayoutRequest(layout_id="", slot_assignments={})

    # SavedLayout model
    saved = SavedLayout(
        dataset_id="ds_123",
        layout_id="player-v1",
        name="Optimized Layout 1",
        slot_assignments={"S001": "SKU-TOP-1"},
        created_at="2026-10-22T10:00:00Z",
    )
    assert saved.dataset_id == "ds_123"
    assert LayoutDetail is SavedLayout

    # LayoutsListResponse
    list_resp = LayoutsListResponse(
        dataset_id="ds_123",
        layouts=[saved],
    )
    assert len(list_resp.layouts) == 1
    assert LayoutListResponse is LayoutsListResponse


# ==============================================================================
# 9. DatasetExportResponse
# ==============================================================================

def test_dataset_export_response():
    """Verify DatasetExportResponse serialization and validation."""
    export = DatasetExportResponse(
        dataset_id="ds_123",
        format="json",
        download_url="/api/datasets/ds_123/download",
        record_count=100,
        file_size_bytes=54321,
    )
    assert export.format == "json"
    assert export.record_count == 100
    dumped = export.model_dump()
    assert dumped["download_url"] == "/api/datasets/ds_123/download"


# ==============================================================================
# 10. Existing Invariants & Validations Remain Strict
# ==============================================================================

def test_existing_schema_invariants():
    """Confirm existing coordinate, dock, and simulation validators remain intact."""
    # Slot coordinate length validation
    with pytest.raises(ValidationError, match="2-element"):
        Slot(slot_id="S1", rack_cell=[1, 2, 3], access_cell=[1, 2], sku="A")

    # WarehouseLayout dock coordinate validation
    with pytest.raises(ValidationError, match="2-element"):
        WarehouseLayout(
            layout_id="test",
            width=5,
            height=5,
            walkable_cells=[[0, 0]],
            dock=[0, 0, 0],
            slots=[],
        )

    # SimulateRequest order_ids non-empty and unique
    with pytest.raises(ValidationError, match="not be empty"):
        SimulateRequest(order_ids=[])

    with pytest.raises(ValidationError, match="unique"):
        SimulateRequest(order_ids=["O1", "O1"])

    # SimulateRequest speed_mps finite, positive, <= 10.0
    with pytest.raises(ValidationError, match="positive"):
        SimulateRequest(order_ids=["O1"], speed_mps=0.0)

    with pytest.raises(ValidationError, match="<= 10.0"):
        SimulateRequest(order_ids=["O1"], speed_mps=15.0)
