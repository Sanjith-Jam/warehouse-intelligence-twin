"""Comprehensive tests for dataset-scoped player layout scenario management and validation."""
import pytest
from fastapi.testclient import TestClient

from backend.app.config import settings
from backend.app.main import app
from backend.app.models.schemas import (
    CreateLayoutRequest,
    ErrorCode,
    LayoutPermutation,
    LayoutRecord,
    LayoutValidationResult,
    UpdateLayoutRequest,
)
from backend.app.services.layout_service import (
    DatasetNotFoundError,
    ImmutableLayoutError,
    InvalidLayoutPermutationError,
    LayoutAlreadyExistsError,
    LayoutNotFoundError,
    layout_service,
)


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Provide a TestClient with upload storage isolated in temporary directory."""
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "upload_storage_dir", str(upload_dir))
    return TestClient(app)


def create_sample_csv(rows: int = 5) -> bytes:
    """Generate minimal valid CSV bytes for dataset upload."""
    lines = ["Invoice,StockCode,Description,Quantity,InvoiceDate"]
    for i in range(1, rows + 1):
        lines.append(f"INV00{i},SKU00{i},Test Product {i},{i * 2},2023-01-15 10:30:00")
    return "\n".join(lines).encode("utf-8")


# ==============================================================================
# 1. CRUD Operations on "demo" Dataset
# ==============================================================================

def test_demo_layouts_crud_lifecycle(client):
    """Verify complete CRUD lifecycle of player layout scenarios on demo dataset."""
    # 1. List initial layouts (should contain built-in original and baseline)
    res_list = client.get("/api/datasets/demo/layouts")
    assert res_list.status_code == 200, res_list.text
    data = res_list.json()
    assert data["dataset_id"] == "demo"
    layout_ids = [l["layout_id"] for l in data["layouts"]]
    assert "original" in layout_ids
    assert "baseline" in layout_ids

    # 2. Create a new layout scenario
    create_payload = {
        "layout_id": "fast-movers-v1",
        "name": "Fast Movers Front",
        "description": "High frequency SKUs placed close to dock",
        "slot_assignments": {
            "S001": "20724",
            "S002": "23200",
        },
    }
    res_create = client.post("/api/datasets/demo/layouts", json=create_payload)
    assert res_create.status_code == 201, res_create.text
    created = res_create.json()
    assert created["dataset_id"] == "demo"
    assert created["layout_id"] == "fast-movers-v1"
    assert created["name"] == "Fast Movers Front"
    assert created["description"] == "High frequency SKUs placed close to dock"
    assert created["slot_assignments"]["S001"] == "20724"
    assert created["slot_assignments"]["S002"] == "23200"
    assert created["revision"] == 1
    assert created["created_at"] is not None
    assert created["updated_at"] is None

    # 3. Retrieve the created layout by ID
    res_get = client.get("/api/datasets/demo/layouts/fast-movers-v1")
    assert res_get.status_code == 200, res_get.text
    got = res_get.json()
    assert got["layout_id"] == "fast-movers-v1"
    assert got["name"] == "Fast Movers Front"

    # 4. Verify listed layouts now includes the created layout
    res_list_after = client.get("/api/datasets/demo/layouts")
    assert res_list_after.status_code == 200
    listed_ids = [l["layout_id"] for l in res_list_after.json()["layouts"]]
    assert "fast-movers-v1" in listed_ids
    assert len(listed_ids) == 3

    # 5. Update layout name and slot assignments (swapping slots)
    update_payload = {
        "name": "Fast Movers Front Re-optimized",
        "slot_assignments": {
            "S001": "23200",
            "S002": "20724",
        },
    }
    res_update = client.put("/api/datasets/demo/layouts/fast-movers-v1", json=update_payload)
    assert res_update.status_code == 200, res_update.text
    updated = res_update.json()
    assert updated["layout_id"] == "fast-movers-v1"
    assert updated["name"] == "Fast Movers Front Re-optimized"
    assert updated["slot_assignments"]["S001"] == "23200"
    assert updated["slot_assignments"]["S002"] == "20724"
    assert updated["revision"] == 2
    assert updated["updated_at"] is not None

    # 6. Delete layout
    res_delete = client.delete("/api/datasets/demo/layouts/fast-movers-v1")
    assert res_delete.status_code == 200, res_delete.text
    assert res_delete.json()["status"] == "deleted"

    # 7. Confirm deletion returns 404
    res_get_deleted = client.get("/api/datasets/demo/layouts/fast-movers-v1")
    assert res_get_deleted.status_code == 404
    detail = res_get_deleted.json()["detail"]
    assert detail["code"] == ErrorCode.LAYOUT_NOT_FOUND.value


# ==============================================================================
# 2. CRUD Operations on Uploaded Datasets
# ==============================================================================

def test_uploaded_dataset_layouts_crud(client):
    """Verify layout scenario CRUD scoped to a dynamic uploaded dataset."""
    # 1. Upload sample CSV workbook
    csv_bytes = create_sample_csv(rows=4)
    upload_res = client.post(
        "/api/datasets/upload",
        files={"file": ("warehouse_orders.csv", csv_bytes, "text/csv")},
    )
    assert upload_res.status_code == 200, upload_res.text
    dataset_id = upload_res.json()["dataset_id"]

    # 2. Initial layouts list for uploaded dataset
    res_list = client.get(f"/api/datasets/{dataset_id}/layouts")
    assert res_list.status_code == 200
    assert len(res_list.json()["layouts"]) >= 2  # original and baseline

    # 3. Create layout using SKUs from the uploaded CSV (SKU001, SKU002)
    payload = {
        "layout_id": "uploaded-scenario-1",
        "name": "Optimized Upload Layout",
        "slot_assignments": {
            "S001": "SKU001",
            "S002": "SKU002",
        },
    }
    res_create = client.post(f"/api/datasets/{dataset_id}/layouts", json=payload)
    assert res_create.status_code == 201, res_create.text
    created = res_create.json()
    assert created["dataset_id"] == dataset_id
    assert created["layout_id"] == "uploaded-scenario-1"
    assert created["revision"] == 1

    # 4. Get specific layout
    res_get = client.get(f"/api/datasets/{dataset_id}/layouts/uploaded-scenario-1")
    assert res_get.status_code == 200
    assert res_get.json()["layout_id"] == "uploaded-scenario-1"

    # 5. Update layout
    res_update = client.put(
        f"/api/datasets/{dataset_id}/layouts/uploaded-scenario-1",
        json={"name": "Renamed Scenario"},
    )
    assert res_update.status_code == 200
    assert res_update.json()["name"] == "Renamed Scenario"
    assert res_update.json()["revision"] == 2

    # 6. Delete layout
    res_del = client.delete(f"/api/datasets/{dataset_id}/layouts/uploaded-scenario-1")
    assert res_del.status_code == 200
    assert res_del.json()["status"] == "deleted"

    # 7. Verify 404
    res_del_get = client.get(f"/api/datasets/{dataset_id}/layouts/uploaded-scenario-1")
    assert res_del_get.status_code == 404
    assert res_del_get.json()["detail"]["code"] == ErrorCode.LAYOUT_NOT_FOUND.value


# ==============================================================================
# 3. Permutation Validation Rules
# ==============================================================================

def test_permutation_validation_valid(client):
    """Verify validation endpoint reports valid for correct legal permutations."""
    valid_payload = {
        "slot_assignments": {
            "S001": "20724",
            "S002": "23200",
            "S003": "22427",
        }
    }
    res = client.post("/api/datasets/demo/layouts/validate", json=valid_payload)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["is_valid"] is True
    assert data["errors"] == []


def test_permutation_validation_duplicate_sku(client):
    """Verify validation detects duplicate SKU assigned to multiple slots."""
    dup_payload = {
        "slot_assignments": {
            "S001": "20724",
            "S002": "20724",  # Duplicate SKU
        }
    }
    # Validate endpoint returns is_valid=False without error
    res_val = client.post("/api/datasets/demo/layouts/validate", json=dup_payload)
    assert res_val.status_code == 200
    val_data = res_val.json()
    assert val_data["is_valid"] is False
    assert any("Duplicate SKU '20724'" in err for err in val_data["errors"])

    # Attempting to create layout with duplicate SKU raises HTTP 422
    create_payload = {
        "name": "Invalid Duplicate SKU",
        "slot_assignments": dup_payload["slot_assignments"],
    }
    res_create = client.post("/api/datasets/demo/layouts", json=create_payload)
    assert res_create.status_code == 422
    detail = res_create.json()["detail"]
    assert detail["code"] == ErrorCode.INVALID_LAYOUT_PERMUTATION.value
    assert "Duplicate SKU" in detail["message"]


def test_permutation_validation_nonexistent_sku(client):
    """Verify validation rejects SKUs that do not exist in dataset products."""
    bad_sku_payload = {
        "slot_assignments": {
            "S001": "NONEXISTENT_SKU_XYZ_9999",
        }
    }
    res_val = client.post("/api/datasets/demo/layouts/validate", json=bad_sku_payload)
    assert res_val.status_code == 200
    val_data = res_val.json()
    assert val_data["is_valid"] is False
    assert any("does not exist in dataset products" in err for err in val_data["errors"])

    # Creation rejected with 422
    res_create = client.post(
        "/api/datasets/demo/layouts",
        json={"name": "Bad SKU", "slot_assignments": bad_sku_payload["slot_assignments"]},
    )
    assert res_create.status_code == 422
    assert res_create.json()["detail"]["code"] == ErrorCode.INVALID_LAYOUT_PERMUTATION.value


def test_permutation_validation_invalid_slot(client):
    """Verify validation rejects slot identifiers not in legal warehouse slots (S001..S100)."""
    bad_slot_payload = {
        "slot_assignments": {
            "INVALID_SLOT_001": "20724",
            "S999": "23200",
        }
    }
    res_val = client.post("/api/datasets/demo/layouts/validate", json=bad_slot_payload)
    assert res_val.status_code == 200
    val_data = res_val.json()
    assert val_data["is_valid"] is False
    assert any("INVALID_SLOT_001" in err and "legal warehouse slot" in err for err in val_data["errors"])
    assert any("S999" in err and "legal warehouse slot" in err for err in val_data["errors"])

    # Creation rejected with 422
    res_create = client.post(
        "/api/datasets/demo/layouts",
        json={"name": "Bad Slot", "slot_assignments": bad_slot_payload["slot_assignments"]},
    )
    assert res_create.status_code == 422
    assert res_create.json()["detail"]["code"] == ErrorCode.INVALID_LAYOUT_PERMUTATION.value


def test_permutation_validation_empty(client):
    """Verify validation rejects empty permutation."""
    res_val = client.post("/api/datasets/demo/layouts/validate", json={"slot_assignments": {}})
    assert res_val.status_code == 200
    assert res_val.json()["is_valid"] is False
    assert any("cannot be empty" in err.lower() for err in res_val.json()["errors"])


# ==============================================================================
# 4. Dataset Isolation Tests
# ==============================================================================

def test_dataset_isolation(client):
    """Verify layouts created under dataset A are NOT visible or accessible under dataset B."""
    # 1. Upload dataset A
    csv_a = create_sample_csv(rows=3)
    res_a = client.post("/api/datasets/upload", files={"file": ("dataset_a.csv", csv_a, "text/csv")})
    ds_a = res_a.json()["dataset_id"]

    # 2. Upload dataset B
    csv_b = create_sample_csv(rows=4)
    res_b = client.post("/api/datasets/upload", files={"file": ("dataset_b.csv", csv_b, "text/csv")})
    ds_b = res_b.json()["dataset_id"]

    # 3. Create layout in dataset A
    payload_a = {
        "layout_id": "layout-ds-a-only",
        "name": "Scenario A",
        "slot_assignments": {"S001": "SKU001"},
    }
    create_a = client.post(f"/api/datasets/{ds_a}/layouts", json=payload_a)
    assert create_a.status_code == 201

    # 4. Create layout in dataset B
    payload_b = {
        "layout_id": "layout-ds-b-only",
        "name": "Scenario B",
        "slot_assignments": {"S001": "SKU001"},
    }
    create_b = client.post(f"/api/datasets/{ds_b}/layouts", json=payload_b)
    assert create_b.status_code == 201

    # 5. Verify dataset A listing does NOT contain layout-ds-b-only
    list_a = client.get(f"/api/datasets/{ds_a}/layouts").json()["layouts"]
    ids_in_a = [l["layout_id"] for l in list_a]
    assert "layout-ds-a-only" in ids_in_a
    assert "layout-ds-b-only" not in ids_in_a

    # 6. Verify dataset B listing does NOT contain layout-ds-a-only
    list_b = client.get(f"/api/datasets/{ds_b}/layouts").json()["layouts"]
    ids_in_b = [l["layout_id"] for l in list_b]
    assert "layout-ds-b-only" in ids_in_b
    assert "layout-ds-a-only" not in ids_in_b

    # 7. Cross-access returns 404
    cross_get_a = client.get(f"/api/datasets/{ds_a}/layouts/layout-ds-b-only")
    assert cross_get_a.status_code == 404
    assert cross_get_a.json()["detail"]["code"] == ErrorCode.LAYOUT_NOT_FOUND.value

    cross_get_b = client.get(f"/api/datasets/{ds_b}/layouts/layout-ds-a-only")
    assert cross_get_b.status_code == 404
    assert cross_get_b.json()["detail"]["code"] == ErrorCode.LAYOUT_NOT_FOUND.value

    # 8. Cross-delete returns 404
    cross_del = client.delete(f"/api/datasets/{ds_a}/layouts/layout-ds-b-only")
    assert cross_del.status_code == 404
    assert cross_del.json()["detail"]["code"] == ErrorCode.LAYOUT_NOT_FOUND.value


# ==============================================================================
# 5. Immutable Reference Layout Protection
# ==============================================================================

def test_immutable_reference_layout_protection(client):
    """Verify built-in 'original' and 'baseline' reference layouts cannot be deleted or overwritten."""
    # 1. Fetching original and baseline returns 200
    res_orig = client.get("/api/datasets/demo/layouts/original")
    assert res_orig.status_code == 200
    assert res_orig.json()["layout_id"] == "original"
    assert len(res_orig.json()["slot_assignments"]) > 0

    res_base = client.get("/api/datasets/demo/layouts/baseline")
    assert res_base.status_code == 200
    assert res_base.json()["layout_id"] == "baseline"
    assert len(res_base.json()["slot_assignments"]) > 0

    # 2. Cannot create layout with reserved ID 'original'
    res_create_orig = client.post(
        "/api/datasets/demo/layouts",
        json={"layout_id": "original", "name": "Fake Original", "slot_assignments": {"S001": "20724"}},
    )
    assert res_create_orig.status_code == 400
    assert "built-in reference layout" in res_create_orig.json()["detail"]["message"].lower()

    # 3. Cannot create layout with reserved ID 'baseline'
    res_create_base = client.post(
        "/api/datasets/demo/layouts",
        json={"layout_id": "baseline", "name": "Fake Baseline", "slot_assignments": {"S001": "20724"}},
    )
    assert res_create_base.status_code == 400
    assert "built-in reference layout" in res_create_base.json()["detail"]["message"].lower()

    # 4. Cannot create layout with reserved name 'Original' or 'Baseline'
    res_name_orig = client.post(
        "/api/datasets/demo/layouts",
        json={"name": "original", "slot_assignments": {"S001": "20724"}},
    )
    assert res_name_orig.status_code == 400
    assert "reserved reference" in res_name_orig.json()["detail"]["message"].lower()

    res_name_base = client.post(
        "/api/datasets/demo/layouts",
        json={"name": "baseline", "slot_assignments": {"S001": "20724"}},
    )
    assert res_name_base.status_code == 400
    assert "reserved reference" in res_name_base.json()["detail"]["message"].lower()

    # 5. Cannot update immutable reference layouts
    res_put_orig = client.put(
        "/api/datasets/demo/layouts/original",
        json={"name": "Hacked Original"},
    )
    assert res_put_orig.status_code == 400
    assert "immutable reference layout" in res_put_orig.json()["detail"]["message"].lower()

    res_put_base = client.put(
        "/api/datasets/demo/layouts/baseline",
        json={"name": "Hacked Baseline"},
    )
    assert res_put_base.status_code == 400
    assert "immutable reference layout" in res_put_base.json()["detail"]["message"].lower()

    # 6. Cannot delete immutable reference layouts
    res_del_orig = client.delete("/api/datasets/demo/layouts/original")
    assert res_del_orig.status_code == 400
    assert "immutable reference layout" in res_del_orig.json()["detail"]["message"].lower()

    res_del_base = client.delete("/api/datasets/demo/layouts/baseline")
    assert res_del_base.status_code == 400
    assert "immutable reference layout" in res_del_base.json()["detail"]["message"].lower()


# ==============================================================================
# 6. Nonexistent Dataset Rejection
# ==============================================================================

def test_nonexistent_dataset_handling(client):
    """Verify all operations on unknown dataset_id return 404 DATASET_NOT_FOUND."""
    bad_ds = "ds_nonexistent_12345"

    assert client.get(f"/api/datasets/{bad_ds}/layouts").status_code == 404
    assert client.post(f"/api/datasets/{bad_ds}/layouts", json={"slot_assignments": {"S001": "20724"}}).status_code == 404
    assert client.get(f"/api/datasets/{bad_ds}/layouts/some-layout").status_code == 404
    assert client.put(f"/api/datasets/{bad_ds}/layouts/some-layout", json={"name": "Test"}).status_code == 404
    assert client.delete(f"/api/datasets/{bad_ds}/layouts/some-layout").status_code == 404
    assert client.post(f"/api/datasets/{bad_ds}/layouts/validate", json={"slot_assignments": {"S001": "20724"}}).status_code == 404

    # Verify structured ErrorDetail format
    err = client.get(f"/api/datasets/{bad_ds}/layouts").json()["detail"]
    assert err["code"] == ErrorCode.DATASET_NOT_FOUND.value
    assert f"Dataset '{bad_ds}' not found" in err["message"]


# ==============================================================================
# 7. Service Unit Tests
# ==============================================================================

def test_layout_service_python_api(tmp_path, monkeypatch):
    """Verify LayoutService direct Python interface and method signatures."""
    monkeypatch.setattr(settings, "upload_storage_dir", str(tmp_path / "uploads"))

    # Test create_layout with auto-generated ID
    req = CreateLayoutRequest(
        name="Auto ID Scenario",
        slot_assignments={"S001": "20724"},
    )
    rec = layout_service.create_layout("demo", req)
    assert isinstance(rec, LayoutRecord)
    assert rec.layout_id.startswith("auto_id_scenario_")
    assert rec.revision == 1

    # Duplicate creation raises LayoutAlreadyExistsError
    req_dup = CreateLayoutRequest(
        layout_id=rec.layout_id,
        name="Duplicate Scenario",
        slot_assignments={"S001": "20724"},
    )
    with pytest.raises(LayoutAlreadyExistsError):
        layout_service.create_layout("demo", req_dup)

    # Update layout incrementing revision
    up_req = UpdateLayoutRequest(name="Updated Auto ID Scenario")
    up_rec = layout_service.update_layout("demo", rec.layout_id, up_req)
    assert up_rec.name == "Updated Auto ID Scenario"
    assert up_rec.revision == 2
    assert up_rec.updated_at is not None

    # Get layout
    got = layout_service.get_layout("demo", rec.layout_id)
    assert got.name == "Updated Auto ID Scenario"

    # Delete layout
    deleted = layout_service.delete_layout("demo", rec.layout_id)
    assert deleted is True

    with pytest.raises(LayoutNotFoundError):
        layout_service.get_layout("demo", rec.layout_id)
