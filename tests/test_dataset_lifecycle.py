"""Integration tests for dataset lifecycle: upload -> preprocess -> detail -> export -> download (FLASH-05)."""
from pathlib import Path
import json
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.config import settings
from backend.app.models.schemas import ErrorCode

client = TestClient(app)

SAMPLE_CSV_CONTENT = """Invoice,StockCode,Description,Quantity,InvoiceDate,Price,Customer ID,Country
536365,85123A,WHITE HANGING HEART T-LIGHT HOLDER,6,2011-06-01 08:26:00,2.55,17850,United Kingdom
536365,71053,WHITE METAL LANTERN,6,2011-06-01 08:26:00,3.39,17850,United Kingdom
536366,84029G,KNITTED UNION FLAG HOT WATER BOTTLE,6,2011-06-02 08:28:00,3.39,17850,United Kingdom
C536367,84029G,CANCELLED ITEM,6,2011-06-02 08:30:00,3.39,17850,United Kingdom
536368,POST,POSTAGE,1,2011-06-03 09:00:00,18.00,17850,United Kingdom
536369,85123A,WHITE HANGING HEART T-LIGHT HOLDER,-2,2011-06-04 10:00:00,2.55,17850,United Kingdom
536370,85123A,WHITE HANGING HEART T-LIGHT HOLDER,12,2011-06-05 11:00:00,2.55,17850,United Kingdom
"""

SAMPLE_CSV_2_CONTENT = """OrderNumber,ItemSKU,ItemName,ItemQty,OrderTimestamp
INV-100,SKU-ALPHA,Alpha Widget,5,2022-03-01 10:00:00
INV-100,SKU-BETA,Beta Gadget,10,2022-03-01 10:05:00
INV-200,SKU-ALPHA,Alpha Widget,2,2022-03-05 12:00:00
"""


def test_demo_dataset_detail_and_export():
    """Verify built-in demo dataset can be retrieved and exported."""
    # GET /api/datasets/demo
    resp = client.get("/api/datasets/demo")
    assert resp.status_code == 200
    data = resp.json()
    assert "meta" in data
    assert "cleaning_report" in data
    assert "layout" in data
    assert "products" in data
    assert "orders" in data
    assert len(data["products"]) == 100
    assert len(data["orders"]) == 20

    # GET /api/datasets/demo/export (json)
    exp_resp = client.get("/api/datasets/demo/export?format=json")
    assert exp_resp.status_code == 200
    exp_data = exp_resp.json()
    assert exp_data["format"] == "json"
    assert exp_data["record_count"] == 100
    assert "download_url" in exp_data

    # GET /api/datasets/demo/export (csv)
    exp_csv_resp = client.get("/api/datasets/demo/export?format=csv")
    assert exp_csv_resp.status_code == 200
    exp_csv_data = exp_csv_resp.json()
    assert exp_csv_data["format"] == "csv"
    assert exp_csv_data["record_count"] == 100

    # GET /api/datasets/demo/download
    dl_resp = client.get("/api/datasets/demo/download?format=json")
    assert dl_resp.status_code == 200
    assert dl_resp.headers["content-type"].startswith("application/json")


def test_demo_dataset_preprocess_rejected():
    """Attempting to re-preprocess the built-in demo dataset must be rejected."""
    payload = {"target_month": "2011-06", "top_skus": 100}
    resp = client.post("/api/datasets/demo/preprocess", json=payload)
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == ErrorCode.IMMUTABLE_DATASET


def test_upload_preprocess_inspect_export_workflow(tmp_path):
    """End-to-end test of uploading a custom CSV, preprocessing, inspecting, and exporting."""
    # 1. Upload CSV
    upload_resp = client.post(
        "/api/datasets/upload",
        files={"file": ("orders.csv", SAMPLE_CSV_CONTENT.encode("utf-8"), "text/csv")},
    )
    assert upload_resp.status_code == 200
    upload_data = upload_resp.json()
    dataset_id = upload_data["dataset_id"]
    assert dataset_id.startswith("ds_")
    assert "2011-06" in upload_data["available_months"]

    # 2. Before preprocessing: GET /api/datasets/{id} returns 404 (not preprocessed)
    detail_pre = client.get(f"/api/datasets/{dataset_id}")
    assert detail_pre.status_code == 404
    assert detail_pre.json()["detail"]["code"] == ErrorCode.DATASET_NOT_FOUND

    # 3. Preprocess dataset
    preprocess_payload = {
        "target_month": "2011-06",
        "top_skus": 50,
        "max_orders": 10,
    }
    prep_resp = client.post(f"/api/datasets/{dataset_id}/preprocess", json=preprocess_payload)
    assert prep_resp.status_code == 200
    prep_data = prep_resp.json()

    assert prep_data["meta"]["dataset_id"] == dataset_id
    assert prep_data["meta"]["month"] == "2011-06"
    assert prep_data["cleaning_report"]["cancelled_month_rows"] == 1
    assert prep_data["cleaning_report"]["nonpositive_or_missing_quantity_rows"] == 1
    assert prep_data["cleaning_report"]["nonproduct_or_blank_sku_rows"] == 1
    # Retained valid products: 85123A (2 orders), 71053 (1 order), 84029G (1 order) = 3 products
    assert len(prep_data["products"]) == 3
    # Check pick frequency ordering: 85123A has frequency 2, others have 1
    skus = [p["sku"] for p in prep_data["products"]]
    assert skus[0] == "85123A"

    # 4. GET /api/datasets/{id}
    detail_resp = client.get(f"/api/datasets/{dataset_id}")
    assert detail_resp.status_code == 200
    detail_data = detail_resp.json()
    assert detail_data["meta"]["dataset_id"] == dataset_id
    assert len(detail_data["products"]) == 3
    assert len(detail_data["orders"]) == 3

    # 5. Export JSON
    exp_json = client.get(f"/api/datasets/{dataset_id}/export?format=json")
    assert exp_json.status_code == 200
    assert exp_json.json()["format"] == "json"
    assert exp_json.json()["record_count"] == 3

    # 6. Export CSV
    exp_csv = client.get(f"/api/datasets/{dataset_id}/export?format=csv")
    assert exp_csv.status_code == 200
    assert exp_csv.json()["format"] == "csv"
    assert exp_csv.json()["record_count"] == 3

    # 7. Download JSON
    dl_json = client.get(f"/api/datasets/{dataset_id}/download?format=json")
    assert dl_json.status_code == 200
    assert dl_json.headers["content-type"].startswith("application/json")
    dl_json_data = dl_json.json()
    assert dl_json_data["meta"]["dataset_id"] == dataset_id

    # 8. Download CSV
    dl_csv = client.get(f"/api/datasets/{dataset_id}/download?format=csv")
    assert dl_csv.status_code == 200
    assert dl_csv.headers["content-type"].startswith("text/csv")
    csv_text = dl_csv.text
    assert "sku,name,pick_frequency" in csv_text
    assert "85123A" in csv_text


def test_two_datasets_isolation_no_cross_contamination():
    """Verify uploading two datasets produces isolated data with no cross-talk."""
    # Upload dataset 1
    up1 = client.post(
        "/api/datasets/upload",
        files={"file": ("dataset1.csv", SAMPLE_CSV_CONTENT.encode("utf-8"), "text/csv")},
    )
    ds1_id = up1.json()["dataset_id"]

    # Upload dataset 2
    up2 = client.post(
        "/api/datasets/upload",
        files={"file": ("dataset2.csv", SAMPLE_CSV_2_CONTENT.encode("utf-8"), "text/csv")},
    )
    ds2_id = up2.json()["dataset_id"]
    assert ds1_id != ds2_id

    # Preprocess dataset 1 (2011-06)
    prep1 = client.post(f"/api/datasets/{ds1_id}/preprocess", json={"target_month": "2011-06"})
    assert prep1.status_code == 200

    # Preprocess dataset 2 (2022-03) with column mapping
    prep2 = client.post(
        f"/api/datasets/{ds2_id}/preprocess",
        json={
            "target_month": "2022-03",
            "column_mapping": {
                "invoice": "OrderNumber",
                "sku": "ItemSKU",
                "description": "ItemName",
                "quantity": "ItemQty",
                "date": "OrderTimestamp",
            },
        },
    )
    assert prep2.status_code == 200

    # Inspect dataset 1: contains 85123A, does NOT contain SKU-ALPHA
    d1 = client.get(f"/api/datasets/{ds1_id}").json()
    d1_skus = {p["sku"] for p in d1["products"]}
    assert "85123A" in d1_skus
    assert "SKU-ALPHA" not in d1_skus

    # Inspect dataset 2: contains SKU-ALPHA, does NOT contain 85123A
    d2 = client.get(f"/api/datasets/{ds2_id}").json()
    d2_skus = {p["sku"] for p in d2["products"]}
    assert "SKU-ALPHA" in d2_skus
    assert "85123A" not in d2_skus

    # Verify official demo.json remains unchanged
    demo_resp = client.get("/api/demo").json()
    assert demo_resp["meta"]["dataset_id"].startswith("uci-2011-06")
    assert len(demo_resp["products"]) == 100


def test_preprocess_nonexistent_dataset():
    """Preprocessing a nonexistent dataset ID returns 404."""
    resp = client.post("/api/datasets/ds_nonexistent/preprocess", json={"target_month": "2011-06"})
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == ErrorCode.DATASET_NOT_FOUND


def test_preprocess_no_data_in_month():
    """Preprocessing for a month that doesn't exist returns 422 NO_DATA_IN_MONTH."""
    up = client.post(
        "/api/datasets/upload",
        files={"file": ("orders.csv", SAMPLE_CSV_CONTENT.encode("utf-8"), "text/csv")},
    )
    ds_id = up.json()["dataset_id"]

    resp = client.post(f"/api/datasets/{ds_id}/preprocess", json={"target_month": "2025-01"})
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == ErrorCode.NO_DATA_IN_MONTH
