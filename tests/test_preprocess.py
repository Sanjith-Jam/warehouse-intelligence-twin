"""Tests for data preprocessing CLI, input validation, and fixture identity."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path


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


def test_preprocess_missing_input_default_portable(monkeypatch):
    """Verify default invocation without machine-specific paths provides clear error when no file is present."""
    # Run with empty environment and working directory without local workbook
    res = subprocess.run(
        [sys.executable, str(PREPROCESS_SCRIPT)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin", "UCI_DATASET_PATH": ""},
    )
    # The default machine-specific path must not be silently used; if not found, it must report clear error
    if res.returncode != 0:
        err = res.stderr
        assert EXPECTED_WORKBOOK_SHA256 in err
        assert "online_retail_II.xlsx" in err


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
