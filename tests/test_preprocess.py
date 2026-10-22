"""Tests for data preprocessing CLI, input validation, checksum verification, and fixture identity."""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from scripts.preprocess_retail import (
    EXPECTED_SHA256,
    generate_synthetic_21x21_layout,
    preprocess_retail_month,
    resolve_input_path,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
PREPROCESS_SCRIPT = REPO_ROOT / "scripts" / "preprocess_retail.py"
BACKEND_DEMO = REPO_ROOT / "backend" / "app" / "data" / "demo.json"
FRONTEND_DEMO = REPO_ROOT / "frontend" / "public" / "demo.json"
BACKEND_PROV = REPO_ROOT / "backend" / "app" / "data" / "demo-provenance.json"
FRONTEND_PROV = REPO_ROOT / "frontend" / "public" / "demo-provenance.json"

EXPECTED_WORKBOOK_SHA256 = "bcbe73b35f5b7babf197fb0cb983a11f5d9ff929078d4aa53d171b1f2df2e980"


def test_preprocess_cli_help():
    """Verify scripts/preprocess_retail.py --help succeeds and documents usage."""
    res = subprocess.run(
        [sys.executable, str(PREPROCESS_SCRIPT), "--help"],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0
    assert "Preprocess UCI Online Retail II dataset" in res.stdout
    assert "--input" in res.stdout
    assert "--sheet" in res.stdout
    assert "--month" in res.stdout
    assert "--allow-hash-mismatch" in res.stdout
    assert "--sync-frontend" in res.stdout


def test_preprocess_missing_input_explicit():
    """Verify that specifying a nonexistent input file fails with clear instructions and expected SHA256."""
    res = subprocess.run(
        [sys.executable, str(PREPROCESS_SCRIPT), "--input", "nonexistent_online_retail.xlsx"],
        capture_output=True,
        text=True,
    )
    assert res.returncode != 0
    err = res.stderr
    assert "not found" in err.lower() or "error" in err.lower()
    assert EXPECTED_WORKBOOK_SHA256 in err
    assert "archive.ics.uci.edu" in err or "uci" in err.lower()


def test_preprocess_missing_input_default_portable(monkeypatch, tmp_path):
    """Verify default invocation without machine-specific paths provides clear error when no file is present."""
    res = subprocess.run(
        [sys.executable, str(PREPROCESS_SCRIPT)],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin", "UCI_DATASET_PATH": ""},
    )
    assert res.returncode != 0
    err = res.stderr
    assert EXPECTED_WORKBOOK_SHA256 in err
    assert "online_retail_II.xlsx" in err
    # Confirm NO machine-specific paths are mentioned
    assert "/home/bread/Documents" not in err


def test_preprocess_checksum_validation_failure(tmp_path):
    """Verify that a corrupted or mismatched source workbook is rejected by default."""
    corrupted_file = tmp_path / "corrupted_retail.xlsx"
    corrupted_file.write_text("not a real excel workbook")

    res = subprocess.run(
        [sys.executable, str(PREPROCESS_SCRIPT), "--input", str(corrupted_file)],
        capture_output=True,
        text=True,
    )
    assert res.returncode != 0
    err = res.stderr
    assert "checksum mismatch" in err.lower()
    assert EXPECTED_WORKBOOK_SHA256 in err
    assert "--allow-hash-mismatch" in err


def test_backend_frontend_fixture_byte_identity():
    """Verify backend and frontend demo.json snapshots are strictly byte-for-byte identical."""
    assert BACKEND_DEMO.exists(), f"Backend fixture missing: {BACKEND_DEMO}"
    assert FRONTEND_DEMO.exists(), f"Frontend fixture missing: {FRONTEND_DEMO}"

    backend_bytes = BACKEND_DEMO.read_bytes()
    frontend_bytes = FRONTEND_DEMO.read_bytes()

    backend_hash = hashlib.sha256(backend_bytes).hexdigest()
    frontend_hash = hashlib.sha256(frontend_bytes).hexdigest()

    assert backend_hash == frontend_hash, (
        f"Backend demo.json (sha256={backend_hash}) and Frontend demo.json (sha256={frontend_hash}) have diverged! "
        f"They must remain byte-identical."
    )

    data = json.loads(backend_bytes.decode("utf-8"))
    assert data["meta"]["real_order_data"] is True
    assert data["meta"]["dataset_id"].startswith("uci-2011-06-preview-")
    assert len(data["products"]) == 100
    assert len(data["orders"]) == 20
    assert len(data["layout"]["slots"]) == 100


def test_backend_frontend_provenance_identity():
    """Verify backend and frontend demo-provenance.json record identical counts, hashes, and byte content."""
    assert BACKEND_PROV.exists(), f"Backend provenance missing: {BACKEND_PROV}"
    assert FRONTEND_PROV.exists(), f"Frontend provenance missing: {FRONTEND_PROV}"

    backend_bytes = BACKEND_PROV.read_bytes()
    frontend_bytes = FRONTEND_PROV.read_bytes()
    assert backend_bytes == frontend_bytes, "demo-provenance.json must be byte-identical in backend and frontend!"

    prov = json.loads(backend_bytes.decode("utf-8"))
    assert prov["workbook_sha256"] == EXPECTED_WORKBOOK_SHA256
    assert prov["month"] == "2011-06"
    assert prov["month_rows"] == 36874
    assert prov["cancelled_month_rows"] == 711
    assert prov["nonpositive_or_missing_quantity_rows"] == 818
    assert prov["nonproduct_or_blank_sku_rows"] == 241
    assert prov["valid_positive_product_lines"] == 35857
    assert prov["top_sku_count"] == 100
    assert prov["selected_order_count"] == 20
    assert len(prov["selected_order_ids"]) == 20
    assert prov["selected_order_ids"][0] == "555157"
    assert prov["selected_order_ids"][10] == "555200"
    assert prov["selected_order_ids"][11] == "555199"


def test_synthetic_workbook_repeat_generation_deterministic(tmp_path):
    """Verify that preprocess_retail_month generates identical outputs across repeat runs on a test workbook."""
    rows = []
    # 5 SKUs with different frequencies and distinct descriptions
    skus = [("SKU_A", "Widget Alpha"), ("SKU_B", "Widget Beta"), ("SKU_C", "Widget Gamma")]
    for i in range(10):
        rows.append({
            "Invoice": f"INV{100 + i}",
            "StockCode": "SKU_A",
            "Description": "Widget Alpha",
            "Quantity": 5,
            "InvoiceDate": f"2011-06-01 10:{i:02d}:00",
            "Price": 1.5,
            "Customer ID": 12345,
            "Country": "United Kingdom",
        })
    for i in range(5):
        rows.append({
            "Invoice": f"INV{100 + i}",
            "StockCode": "SKU_B",
            "Description": "Widget Beta",
            "Quantity": 3,
            "InvoiceDate": f"2011-06-01 10:{i:02d}:00",
            "Price": 2.0,
            "Customer ID": 12345,
            "Country": "United Kingdom",
        })
    # Cancelled invoice
    rows.append({
        "Invoice": "C10099",
        "StockCode": "SKU_A",
        "Description": "Widget Alpha",
        "Quantity": 5,
        "InvoiceDate": "2011-06-01 09:00:00",
        "Price": 1.5,
        "Customer ID": 12345,
        "Country": "United Kingdom",
    })
    # Non-positive quantity
    rows.append({
        "Invoice": "INV199",
        "StockCode": "SKU_A",
        "Description": "Widget Alpha",
        "Quantity": 0,
        "InvoiceDate": "2011-06-01 09:00:00",
        "Price": 1.5,
        "Customer ID": 12345,
        "Country": "United Kingdom",
    })

    test_excel = tmp_path / "test_retail.xlsx"
    df = pd.DataFrame(rows)
    with pd.ExcelWriter(test_excel, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Year 2010-2011", index=False)

    demo1, prov1 = preprocess_retail_month(
        filepath=str(test_excel),
        num_top_skus=2,
        num_demo_orders=2,
        allow_hash_mismatch=True,
    )
    demo2, prov2 = preprocess_retail_month(
        filepath=str(test_excel),
        num_top_skus=2,
        num_demo_orders=2,
        allow_hash_mismatch=True,
    )

    assert demo1 == demo2, "Repeat preprocessing runs must produce identical demo payloads!"
    assert prov1 == prov2, "Repeat preprocessing runs must produce identical provenance metadata!"
    assert len(demo1["products"]) == 2
    assert demo1["products"][0]["sku"] == "SKU_A"
    assert demo1["products"][0]["pick_frequency"] == 10
    assert demo1["products"][1]["sku"] == "SKU_B"
    assert demo1["products"][1]["pick_frequency"] == 5
    assert prov1["cancelled_month_rows"] == 1
    assert prov1["nonpositive_or_missing_quantity_rows"] == 1
    assert prov1["valid_positive_product_lines"] == 15


def test_real_workbook_regeneration_matches_committed_if_present(tmp_path):
    """If real workbook is located on the system, verify regeneration matches committed fixtures exactly."""
    workbook_path, _ = resolve_input_path(None)
    if not workbook_path:
        # Also check local environment or standard development path
        dev_path = Path("/home/bread/Documents/Codex/2026-10-22/you-are-the-technical-lead-github/work/datasets/online-retail-ii/online_retail_II.xlsx")
        if dev_path.is_file():
            workbook_path = dev_path

    if not workbook_path:
        pytest.skip("Full UCI workbook online_retail_II.xlsx not present in standard location; skipping full regeneration test.")

    gen_json = tmp_path / "demo.json"
    gen_prov = tmp_path / "demo-provenance.json"

    res = subprocess.run(
        [
            sys.executable,
            str(PREPROCESS_SCRIPT),
            "--input",
            str(workbook_path),
            "--output-json",
            str(gen_json),
            "--output-provenance",
            str(gen_prov),
            "--no-sync-frontend",
        ],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"Preprocessing failed: {res.stderr}"

    assert gen_json.read_bytes() == BACKEND_DEMO.read_bytes(), (
        "Regenerated demo.json does not match committed backend/app/data/demo.json byte-for-byte!"
    )
    assert gen_prov.read_bytes() == BACKEND_PROV.read_bytes(), (
        "Regenerated demo-provenance.json does not match committed backend/app/data/demo-provenance.json byte-for-byte!"
    )
