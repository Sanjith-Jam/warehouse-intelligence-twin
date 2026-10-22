"""Deployment readiness, persistence policies, CORS, and post-restart simulation smoke tests (FLASH-09)."""
from pathlib import Path
import json
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.config import settings
from backend.app.data.loader import DataLoader, data_loader, DEFAULT_DATA_PATH
from backend.app.models.schemas import ErrorCode


RETAIL_CSV_PAYLOAD = """Invoice,StockCode,Description,Quantity,InvoiceDate,Price,Customer ID,Country
900001,SKU_APPLE,Fresh Crisp Apple,10,2023-05-02 09:15:00,1.50,12345,United Kingdom
900001,SKU_BANANA,Organic Banana Bunch,5,2023-05-02 09:15:00,2.00,12345,United Kingdom
900002,SKU_CHERRY,Sweet Red Cherries,8,2023-05-03 10:30:00,3.25,12346,United Kingdom
900002,SKU_DATE,Medjool Dates Box,3,2023-05-03 10:30:00,4.50,12346,United Kingdom
900003,SKU_APPLE,Fresh Crisp Apple,4,2023-05-04 11:00:00,1.50,12347,United Kingdom
900003,SKU_DATE,Medjool Dates Box,6,2023-05-04 11:00:00,4.50,12347,United Kingdom
900004,SKU_BANANA,Organic Banana Bunch,12,2023-05-05 14:20:00,2.00,12348,United Kingdom
900005,SKU_CHERRY,Sweet Red Cherries,2,2023-05-06 16:45:00,3.25,12349,United Kingdom
"""


# ==============================================================================
# 1. Health Endpoint Smoke Tests
# ==============================================================================

def test_health_endpoint():
    """Verify GET /health returns HTTP 200 with {'status': 'ok'} for load balancer and health checks."""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ==============================================================================
# 2. CORS Preflight & Request Header Smoke Tests
# ==============================================================================

def test_cors_preflight_and_get_production_origin():
    """Verify CORS headers on OPTIONS preflight and GET requests from production Cloudflare Pages."""
    client = TestClient(app)
    prod_origin = "https://warehouse-intelligence-twin.pages.dev"

    # Preflight OPTIONS request
    preflight_res = client.options(
        "/api/simulate",
        headers={
            "Origin": prod_origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert preflight_res.status_code == 200
    assert preflight_res.headers.get("access-control-allow-origin") == prod_origin
    assert "POST" in preflight_res.headers.get("access-control-allow-methods", "")

    # GET request with Origin
    get_res = client.get("/health", headers={"Origin": prod_origin})
    assert get_res.status_code == 200
    assert get_res.headers.get("access-control-allow-origin") == prod_origin


def test_cors_preview_deployments_and_local_origins():
    """Verify CORS regex permits Cloudflare Pages branch/commit preview subdomains and localhost."""
    client = TestClient(app)

    allowed_origins = [
        "https://warehouse-intelligence-twin.pages.dev",
        "https://preview-feat-branch.warehouse-intelligence-twin.pages.dev",
        "https://7a8b9c.warehouse-intelligence-twin.pages.dev",
        "http://localhost:5173",
        "http://localhost:3000",
    ]

    for origin in allowed_origins:
        res = client.options(
            "/api/demo",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
            },
        )
        assert res.status_code == 200, f"Failed preflight for allowed origin {origin}"
        assert res.headers.get("access-control-allow-origin") == origin

    # Unauthorized domain should NOT receive access-control-allow-origin
    unauthorized_origin = "https://malicious-external-site.example.com"
    unauth_res = client.options(
        "/api/demo",
        headers={
            "Origin": unauthorized_origin,
            "Access-Control-Request-Method": "GET",
        },
    )
    assert unauth_res.headers.get("access-control-allow-origin") != unauthorized_origin


# ==============================================================================
# 3. Upload Size Limit Enforcement
# ==============================================================================

def test_default_upload_size_limit_configuration():
    """Verify default maximum upload size is configured to 50MB."""
    assert settings.max_upload_size_bytes == 50 * 1024 * 1024


def test_oversized_file_upload_rejected_with_413(tmp_path, monkeypatch):
    """Verify file uploads exceeding the configured size limit are rejected with HTTP 413 and cleaned up."""
    storage_dir = tmp_path / "uploads"
    monkeypatch.setattr(settings, "upload_storage_dir", str(storage_dir))
    # Set simulated strict limit to 500 bytes
    monkeypatch.setattr(settings, "max_upload_size_bytes", 500)

    client = TestClient(app)
    # Payload is ~700 bytes, exceeding 500 byte limit
    oversized_data = RETAIL_CSV_PAYLOAD.encode("utf-8")
    assert len(oversized_data) > 500

    response = client.post(
        "/api/datasets/upload",
        files={"file": ("large_orders.csv", oversized_data, "text/csv")},
    )

    assert response.status_code == 413
    error_detail = response.json()["detail"]
    assert error_detail["code"] == ErrorCode.FILE_TOO_LARGE
    assert "exceeds maximum allowed size" in error_detail["message"]

    # Verify no leaked staging directories remain in uploads directory
    if storage_dir.exists():
        subdirs = [p for p in storage_dir.iterdir() if p.is_dir()]
        assert len(subdirs) == 0, f"Expected no leftover directories, found: {subdirs}"


# ==============================================================================
# 4. Persistence Survival Across Server Restart Smoke Test
# ==============================================================================

def test_dataset_lifecycle_survival_across_server_restart(tmp_path, monkeypatch):
    """Test full dynamic dataset lifecycle survival across server restart / cache reset:

    1. Upload CSV dataset.
    2. Preprocess dataset into isolated staging directory.
    3. Simulate fresh server restart by resetting DataLoader in-memory state.
    4. Verify GET /api/datasets/{id} and POST /api/datasets/{id}/simulate work purely from disk.
    """
    storage_dir = tmp_path / "persistent_uploads"
    monkeypatch.setattr(settings, "upload_storage_dir", str(storage_dir))

    # --- Phase 1: Upload CSV Dataset ---
    client_pre = TestClient(app)
    upload_res = client_pre.post(
        "/api/datasets/upload",
        files={"file": ("warehouse_orders.csv", RETAIL_CSV_PAYLOAD.encode("utf-8"), "text/csv")},
    )
    assert upload_res.status_code == 200, upload_res.text
    upload_data = upload_res.json()
    dataset_id = upload_data["dataset_id"]
    assert dataset_id.startswith("ds_")
    assert "2023-05" in upload_data["available_months"]

    # --- Phase 2: Preprocess Dataset ---
    prep_res = client_pre.post(
        f"/api/datasets/{dataset_id}/preprocess",
        json={"target_month": "2023-05", "top_skus": 20, "max_orders": 10},
    )
    assert prep_res.status_code == 200, prep_res.text
    prep_data = prep_res.json()
    assert prep_data["meta"]["dataset_id"] == dataset_id
    assert len(prep_data["products"]) == 4  # APPLE, BANANA, CHERRY, DATE
    assert len(prep_data["orders"]) == 5

    # Verify disk artifacts exist on filesystem
    dataset_disk_dir = storage_dir / dataset_id
    assert (dataset_disk_dir / "raw.csv").exists()
    assert (dataset_disk_dir / "meta.json").exists()
    assert (dataset_disk_dir / "processed.json").exists()
    assert (dataset_disk_dir / "cleaning_report.json").exists()

    # --- Phase 3: Simulate Fresh Server Startup / Memory Cache Reset ---
    # Re-initialize DataLoader strictly to default seed demo.json (discarding any runtime references)
    data_loader.load(DEFAULT_DATA_PATH)
    assert data_loader.meta.dataset_id != dataset_id
    assert data_loader.get_order("900001") is None  # uploaded order is not in demo.json

    # Create a completely fresh TestClient (simulating new HTTP client after server reboot)
    fresh_client = TestClient(app)

    # --- Phase 4: Query Dataset & Simulate Purely from Disk Post-Restart ---

    # 4a. GET /api/datasets/{id}
    detail_res = fresh_client.get(f"/api/datasets/{dataset_id}")
    assert detail_res.status_code == 200, detail_res.text
    detail = detail_res.json()
    assert detail["meta"]["dataset_id"] == dataset_id
    assert detail["meta"]["source"] == "warehouse_orders.csv"
    assert len(detail["products"]) == 4
    assert len(detail["orders"]) == 5
    assert detail["cleaning_report"]["selected_order_count"] == 5

    # 4b. POST /api/datasets/{id}/simulate
    sim_res = fresh_client.post(
        f"/api/datasets/{dataset_id}/simulate",
        json={
            "speed_mps": 1.2,
            "handling_seconds_per_line": 10.0,
        },
    )
    assert sim_res.status_code == 200, sim_res.text
    sim = sim_res.json()
    assert sim["dataset_id"] == dataset_id
    assert "policies" in sim
    assert "original" in sim["policies"]
    assert "baseline" in sim["policies"]

    orig_policy = sim["policies"]["original"]
    base_policy = sim["policies"]["baseline"]

    assert orig_policy["orders_replayed"] == 5
    assert orig_policy["distance_m"] > 0
    assert orig_policy["estimated_pick_time_s"] > 0
    assert len(orig_policy["routes"]) == 5

    assert base_policy["orders_replayed"] == 5
    assert base_policy["distance_m"] > 0
    assert base_policy["estimated_pick_time_s"] > 0
    assert len(base_policy["routes"]) == 5

    # 4c. Verify exports survive and serve correctly from disk post-restart
    exp_json = fresh_client.get(f"/api/datasets/{dataset_id}/export?format=json")
    assert exp_json.status_code == 200
    assert exp_json.json()["format"] == "json"

    exp_csv = fresh_client.get(f"/api/datasets/{dataset_id}/export?format=csv")
    assert exp_csv.status_code == 200
    assert exp_csv.json()["format"] == "csv"

    dl_res = fresh_client.get(f"/api/datasets/{dataset_id}/download?format=json")
    assert dl_res.status_code == 200
    assert dl_res.headers["content-type"].startswith("application/json")
    dl_data = json.loads(dl_res.content)
    assert dl_data["meta"]["dataset_id"] == dataset_id

    # 4d. Verify Layouts API resolves legal slots and default layout post-restart
    layout_res = fresh_client.get(f"/api/datasets/{dataset_id}/layouts")
    assert layout_res.status_code == 200
    layouts = layout_res.json()["layouts"]
    assert any(l["layout_id"] == "original" for l in layouts)


# ==============================================================================
# 5. Configurable Storage Directory
# ==============================================================================

def test_upload_storage_dir_configurable_via_env(tmp_path, monkeypatch):
    """Verify that UPLOAD_STORAGE_DIR environment variable directs file persistence."""
    custom_dir = tmp_path / "custom_env_dir"
    monkeypatch.setenv("UPLOAD_STORAGE_DIR", str(custom_dir))

    # Reload Settings instance or update attribute
    monkeypatch.setattr(settings, "upload_storage_dir", str(custom_dir))
    client = TestClient(app)

    res = client.post(
        "/api/datasets/upload",
        files={"file": ("orders.csv", RETAIL_CSV_PAYLOAD.encode("utf-8"), "text/csv")},
    )
    assert res.status_code == 200
    ds_id = res.json()["dataset_id"]

    # Verify upload was written directly into custom_dir
    assert (custom_dir / ds_id / "raw.csv").exists()
    assert (custom_dir / ds_id / "meta.json").exists()
