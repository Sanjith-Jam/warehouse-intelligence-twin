"""Layout scenario service for managing dataset-scoped warehouse layouts."""
from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any, Optional
import uuid

from backend.app.config import settings
from backend.app.data.loader import data_loader
from backend.app.models.schemas import (
    CreateLayoutRequest,
    ErrorCode,
    LayoutPermutation,
    LayoutRecord,
    LayoutValidationResult,
    UpdateLayoutRequest,
    WarehouseLayout,
)
from backend.app.simulation.router import compute_baseline_assignments

RESERVED_LAYOUT_IDS: set[str] = {"original", "baseline"}
RESERVED_NAMES: set[str] = {"original", "baseline"}


class LayoutServiceError(Exception):
    """Base exception for layout service errors."""

    def __init__(self, code: ErrorCode | str, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(message)
        self.code = code.value if isinstance(code, ErrorCode) else str(code)
        self.message = message
        self.details = details or {}


class DatasetNotFoundError(LayoutServiceError):
    """Raised when a requested dataset identifier does not exist."""

    def __init__(self, dataset_id: str):
        super().__init__(
            code=ErrorCode.DATASET_NOT_FOUND,
            message=f"Dataset '{dataset_id}' not found",
            details={"dataset_id": dataset_id},
        )
        self.dataset_id = dataset_id


class LayoutNotFoundError(LayoutServiceError):
    """Raised when a layout scenario does not exist under a dataset."""

    def __init__(self, dataset_id: str, layout_id: str):
        super().__init__(
            code=ErrorCode.LAYOUT_NOT_FOUND,
            message=f"Layout '{layout_id}' not found for dataset '{dataset_id}'",
            details={"dataset_id": dataset_id, "layout_id": layout_id},
        )
        self.dataset_id = dataset_id
        self.layout_id = layout_id


class InvalidLayoutPermutationError(LayoutServiceError):
    """Raised when a layout permutation fails validation rules."""

    def __init__(self, errors: list[str]):
        super().__init__(
            code=ErrorCode.INVALID_LAYOUT_PERMUTATION,
            message="Invalid layout permutation: " + "; ".join(errors),
            details={"errors": errors},
        )
        self.errors = errors


class ImmutableLayoutError(LayoutServiceError):
    """Raised when attempting to overwrite, modify, or delete a reserved reference layout."""

    def __init__(self, layout_id_or_name: str, message: Optional[str] = None):
        super().__init__(
            code=ErrorCode.INVALID_LAYOUT_PERMUTATION,
            message=message or f"Cannot modify immutable reference layout '{layout_id_or_name}'",
            details={"identifier": layout_id_or_name},
        )
        self.layout_id_or_name = layout_id_or_name


class LayoutAlreadyExistsError(LayoutServiceError):
    """Raised when creating a layout with an ID that already exists."""

    def __init__(self, dataset_id: str, layout_id: str):
        super().__init__(
            code=ErrorCode.LAYOUT_ALREADY_EXISTS,
            message=f"Layout '{layout_id}' already exists for dataset '{dataset_id}'",
            details={"dataset_id": dataset_id, "layout_id": layout_id},
        )
        self.dataset_id = dataset_id
        self.layout_id = layout_id


class LayoutService:
    """Manages player warehouse layout scenarios scoped to datasets."""

    def __init__(self, base_dir: Optional[Path | str] = None) -> None:
        self._base_dir = base_dir

    @property
    def base_dir(self) -> Path:
        """Return configured root storage directory."""
        return Path(self._base_dir or settings.upload_storage_dir)

    def dataset_exists(self, dataset_id: str) -> bool:
        """Check if a dataset_id exists (demo or uploaded dataset)."""
        if not dataset_id or not isinstance(dataset_id, str):
            return False
        # Prevent directory traversal in dataset_id
        if ".." in dataset_id or "/" in dataset_id or "\\" in dataset_id:
            return False

        if dataset_id in ("demo", "sample-v1"):
            return True
        if hasattr(data_loader, "meta") and dataset_id == data_loader.meta.dataset_id:
            return True

        upload_dir = self.base_dir / dataset_id
        return upload_dir.is_dir()

    def get_layouts_dir(self, dataset_id: str) -> Path:
        """Return the directory path where layouts for dataset_id are stored."""
        # For demo dataset, store under demo/layouts
        folder_name = "demo" if dataset_id in ("demo", "sample-v1") else dataset_id
        return self.base_dir / folder_name / "layouts"

    def get_layout_file_path(self, dataset_id: str, layout_id: str) -> Path:
        """Return file path for a layout scenario."""
        clean_id = Path(layout_id).name
        return self.get_layouts_dir(dataset_id) / f"{clean_id}.json"

    def get_dataset_legal_slots(self, dataset_id: str) -> set[str]:
        """Return legal warehouse slots (S001..S100) for dataset."""
        if dataset_id in ("demo", "sample-v1") or dataset_id == getattr(data_loader.meta, "dataset_id", None):
            return {s.slot_id for s in data_loader.layout.slots}

        upload_dir = self.base_dir / dataset_id
        if upload_dir.is_dir():
            for json_name in ("dataset.json", "preprocessed.json", "data.json"):
                json_file = upload_dir / json_name
                if json_file.is_file():
                    try:
                        with open(json_file, "r", encoding="utf-8") as f:
                            content = json.load(f)
                        if "layout" in content and "slots" in content["layout"]:
                            return {s["slot_id"] for s in content["layout"]["slots"]}
                    except Exception:
                        pass

        # Standard legal slots S001..S100
        return {f"S{i:03d}" for i in range(1, 101)}

    def get_dataset_legal_skus(self, dataset_id: str) -> set[str]:
        """Return valid product SKUs belonging to the dataset."""
        if dataset_id in ("demo", "sample-v1") or dataset_id == getattr(data_loader.meta, "dataset_id", None):
            return {p.sku for p in data_loader.products}

        upload_dir = self.base_dir / dataset_id
        if not upload_dir.is_dir():
            return set()

        # 1. Check preprocessed snapshot JSON files
        for json_name in ("dataset.json", "preprocessed.json", "data.json"):
            json_file = upload_dir / json_name
            if json_file.is_file():
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        content = json.load(f)
                    if "products" in content and isinstance(content["products"], list):
                        skus = {p["sku"] for p in content["products"] if isinstance(p, dict) and "sku" in p}
                        if skus:
                            return skus
                except Exception:
                    pass

        # 2. Check standalone products.json
        products_file = upload_dir / "products.json"
        if products_file.is_file():
            try:
                with open(products_file, "r", encoding="utf-8") as f:
                    content = json.load(f)
                if isinstance(content, list):
                    skus = {p["sku"] if isinstance(p, dict) else str(p) for p in content}
                    if skus:
                        return skus
            except Exception:
                pass

        # 3. Check meta.json
        meta_file = upload_dir / "meta.json"
        if meta_file.is_file():
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    meta_data = json.load(f)
                if "products" in meta_data and isinstance(meta_data["products"], list):
                    return {p["sku"] if isinstance(p, dict) else str(p) for p in meta_data["products"]}
                if "skus" in meta_data and isinstance(meta_data["skus"], list):
                    return {str(s) for s in meta_data["skus"]}
            except Exception:
                pass

        # 4. Check raw tabular workbook files
        for raw_name in ("raw.csv", "raw.xlsx", "raw.xls"):
            raw_file = upload_dir / raw_name
            if raw_file.is_file():
                try:
                    from backend.app.services.parsing import detect_canonical_columns, read_sheet_dataframe
                    df, _ = read_sheet_dataframe(raw_file, raw_file.suffix)
                    cols = [str(c).strip() for c in df.columns]
                    det, _ = detect_canonical_columns(cols)
                    sku_col = det.get("sku")
                    if sku_col and sku_col in df.columns:
                        valid_skus = df[sku_col].dropna().astype(str).str.strip()
                        skus = {s for s in valid_skus if s and s.lower() != "nan"}
                        if skus:
                            return skus
                except Exception:
                    pass

        return set()

    def _get_original_reference_layout(self, dataset_id: str) -> LayoutRecord:
        """Construct the immutable 'original' reference layout record."""
        if dataset_id in ("demo", "sample-v1") or dataset_id == getattr(data_loader.meta, "dataset_id", None):
            assignments = {s.slot_id: s.sku for s in data_loader.layout.slots}
            return LayoutRecord(
                dataset_id=dataset_id,
                layout_id="original",
                name="Original Default",
                description="Initial reference layout",
                slot_assignments=assignments,
                revision=1,
                created_at="2026-10-22T00:00:00Z",
                updated_at=None,
            )

        upload_dir = self.base_dir / dataset_id
        if upload_dir.is_dir():
            for json_name in ("dataset.json", "preprocessed.json", "data.json"):
                json_file = upload_dir / json_name
                if json_file.is_file():
                    try:
                        with open(json_file, "r", encoding="utf-8") as f:
                            content = json.load(f)
                        if "layout" in content and "slots" in content["layout"]:
                            assignments = {s["slot_id"]: s["sku"] for s in content["layout"]["slots"]}
                            return LayoutRecord(
                                dataset_id=dataset_id,
                                layout_id="original",
                                name="Original Default",
                                description="Initial reference layout",
                                slot_assignments=assignments,
                                revision=1,
                                created_at="2026-10-22T00:00:00Z",
                                updated_at=None,
                            )
                    except Exception:
                        pass

        legal_skus = sorted(list(self.get_dataset_legal_skus(dataset_id)))
        assignments = {f"S{i+1:03d}": sku for i, sku in enumerate(legal_skus[:100])}
        return LayoutRecord(
            dataset_id=dataset_id,
            layout_id="original",
            name="Original Default",
            description="Initial reference layout",
            slot_assignments=assignments,
            revision=1,
            created_at="2026-10-22T00:00:00Z",
            updated_at=None,
        )

    def _get_baseline_reference_layout(self, dataset_id: str) -> LayoutRecord:
        """Construct the immutable 'baseline' reference layout record."""
        if dataset_id in ("demo", "sample-v1") or dataset_id == getattr(data_loader.meta, "dataset_id", None):
            walkable_set = {(c[0], c[1]) for c in data_loader.layout.walkable_cells}
            assignments = compute_baseline_assignments(data_loader.layout, data_loader.products, walkable_set)
            return LayoutRecord(
                dataset_id=dataset_id,
                layout_id="baseline",
                name="Fast-Mover Baseline",
                description="Fastest-moving items slotted closest to dock",
                slot_assignments=assignments,
                revision=1,
                created_at="2026-10-22T00:00:00Z",
                updated_at=None,
            )

        legal_skus = sorted(list(self.get_dataset_legal_skus(dataset_id)))
        assignments = {f"S{i+1:03d}": sku for i, sku in enumerate(legal_skus[:100])}
        return LayoutRecord(
            dataset_id=dataset_id,
            layout_id="baseline",
            name="Fast-Mover Baseline",
            description="Fastest-moving items slotted closest to dock",
            slot_assignments=assignments,
            revision=1,
            created_at="2026-10-22T00:00:00Z",
            updated_at=None,
        )

    def validate_layout_permutation(
        self,
        dataset_id: str,
        permutation: LayoutPermutation | dict[str, str],
    ) -> LayoutValidationResult:
        """Validate layout slot-to-SKU permutation against dataset constraints."""
        if not self.dataset_exists(dataset_id):
            raise DatasetNotFoundError(dataset_id)

        # Extract mapping
        if isinstance(permutation, LayoutPermutation):
            slot_assignments = permutation.slot_assignments
        elif isinstance(permutation, dict):
            if "slot_assignments" in permutation and isinstance(permutation["slot_assignments"], dict):
                slot_assignments = permutation["slot_assignments"]
            elif "permutation" in permutation and isinstance(permutation["permutation"], dict):
                slot_assignments = permutation["permutation"]
            else:
                slot_assignments = permutation
        else:
            return LayoutValidationResult(
                is_valid=False,
                errors=["Permutation must be a dictionary or LayoutPermutation instance"],
            )

        errors: list[str] = []

        if not slot_assignments:
            errors.append("Permutation cannot be empty")
            return LayoutValidationResult(is_valid=False, errors=errors)

        legal_slots = self.get_dataset_legal_slots(dataset_id)
        legal_skus = self.get_dataset_legal_skus(dataset_id)

        sku_to_slots: dict[str, list[str]] = defaultdict(list)

        for slot_id, sku in slot_assignments.items():
            slot_str = str(slot_id).strip()
            sku_str = str(sku).strip()

            if not slot_str:
                errors.append(f"Invalid empty slot identifier: '{slot_id}'")
            elif slot_str not in legal_slots:
                errors.append(f"Slot '{slot_str}' is not a legal warehouse slot")

            if not sku_str:
                errors.append(f"Invalid empty SKU assigned to slot '{slot_str}'")
            elif sku_str not in legal_skus:
                errors.append(f"SKU '{sku_str}' does not exist in dataset products")

            sku_to_slots[sku_str].append(slot_str)

        # Check for duplicate SKU assignments across multiple slots
        for sku, slots in sku_to_slots.items():
            if len(slots) > 1 and sku:
                errors.append(f"Duplicate SKU '{sku}' assigned to multiple slots: {', '.join(sorted(slots))}")

        is_valid = len(errors) == 0
        return LayoutValidationResult(is_valid=is_valid, errors=errors)

    def create_layout(self, dataset_id: str, payload: CreateLayoutRequest) -> LayoutRecord:
        """Create a new named layout scenario under dataset_id."""
        if not self.dataset_exists(dataset_id):
            raise DatasetNotFoundError(dataset_id)

        name = (payload.name or "").strip()
        if not name:
            name = (payload.layout_id or "Custom Layout").strip()

        if name.lower() in RESERVED_NAMES:
            raise ImmutableLayoutError(name, "Layout name cannot be 'original' or 'baseline'; these are reserved reference layouts")

        if payload.layout_id:
            layout_id = payload.layout_id.strip()
            if ".." in layout_id or "/" in layout_id or "\\" in layout_id:
                raise LayoutServiceError(
                    ErrorCode.INVALID_LAYOUT_PERMUTATION,
                    f"Layout ID contains illegal characters: '{layout_id}'",
                )
            if layout_id.lower() in RESERVED_LAYOUT_IDS:
                raise ImmutableLayoutError(layout_id, f"Cannot overwrite built-in reference layout '{layout_id}'")
        else:
            slug = re.sub(r"[^a-zA-Z0-9_-]", "_", name.lower())[:24].strip("_")
            layout_id = f"{slug}_{uuid.uuid4().hex[:6]}" if slug else f"layout_{uuid.uuid4().hex[:8]}"

        file_path = self.get_layout_file_path(dataset_id, layout_id)
        if file_path.exists():
            raise LayoutAlreadyExistsError(dataset_id, layout_id)

        # Validate permutation
        val = self.validate_layout_permutation(dataset_id, payload.slot_assignments)
        if not val.is_valid:
            raise InvalidLayoutPermutationError(val.errors)

        now_iso = datetime.now(timezone.utc).isoformat()
        record = LayoutRecord(
            dataset_id=dataset_id,
            layout_id=layout_id,
            name=name,
            description=payload.description,
            slot_assignments=payload.slot_assignments,
            revision=1,
            created_at=now_iso,
            updated_at=None,
            layout=payload.layout,
        )

        layouts_dir = self.get_layouts_dir(dataset_id)
        layouts_dir.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(record.model_dump(mode="json"), f, indent=2)

        return record

    def list_layouts(self, dataset_id: str) -> list[LayoutRecord]:
        """List all layouts for dataset_id, including immutable reference layouts."""
        if not self.dataset_exists(dataset_id):
            raise DatasetNotFoundError(dataset_id)

        layouts: list[LayoutRecord] = [
            self._get_original_reference_layout(dataset_id),
            self._get_baseline_reference_layout(dataset_id),
        ]

        layouts_dir = self.get_layouts_dir(dataset_id)
        if layouts_dir.exists():
            for file in sorted(layouts_dir.glob("*.json")):
                try:
                    with open(file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    layouts.append(LayoutRecord.model_validate(data))
                except Exception:
                    continue

        return layouts

    def get_layout(self, dataset_id: str, layout_id: str) -> LayoutRecord:
        """Get a specific layout by ID under dataset_id."""
        if not self.dataset_exists(dataset_id):
            raise DatasetNotFoundError(dataset_id)

        if ".." in layout_id or "/" in layout_id or "\\" in layout_id:
            raise LayoutNotFoundError(dataset_id, layout_id)

        norm_id = layout_id.strip().lower()
        if norm_id == "original":
            return self._get_original_reference_layout(dataset_id)
        if norm_id == "baseline":
            return self._get_baseline_reference_layout(dataset_id)

        file_path = self.get_layout_file_path(dataset_id, layout_id)
        if not file_path.exists():
            raise LayoutNotFoundError(dataset_id, layout_id)

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return LayoutRecord.model_validate(data)

    def update_layout(self, dataset_id: str, layout_id: str, payload: UpdateLayoutRequest) -> LayoutRecord:
        """Update an existing layout's name, description, or permutation."""
        if not self.dataset_exists(dataset_id):
            raise DatasetNotFoundError(dataset_id)

        if ".." in layout_id or "/" in layout_id or "\\" in layout_id:
            raise LayoutNotFoundError(dataset_id, layout_id)

        if layout_id.strip().lower() in RESERVED_LAYOUT_IDS:
            raise ImmutableLayoutError(layout_id, f"Cannot modify immutable reference layout '{layout_id}'")

        file_path = self.get_layout_file_path(dataset_id, layout_id)
        if not file_path.exists():
            raise LayoutNotFoundError(dataset_id, layout_id)

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        record = LayoutRecord.model_validate(data)

        if payload.name is not None:
            new_name = payload.name.strip()
            if new_name.lower() in RESERVED_NAMES:
                raise ImmutableLayoutError(new_name, "Layout name cannot be updated to reserved name 'original' or 'baseline'")
            record.name = new_name

        if payload.description is not None:
            record.description = payload.description

        if payload.slot_assignments is not None:
            val = self.validate_layout_permutation(dataset_id, payload.slot_assignments)
            if not val.is_valid:
                raise InvalidLayoutPermutationError(val.errors)
            record.slot_assignments = payload.slot_assignments

        # Increment revision and record update timestamp
        record.revision = (record.revision or 1) + 1
        record.updated_at = datetime.now(timezone.utc).isoformat()

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(record.model_dump(mode="json"), f, indent=2)

        return record

    def delete_layout(self, dataset_id: str, layout_id: str) -> bool:
        """Delete a layout scenario under dataset_id."""
        if not self.dataset_exists(dataset_id):
            raise DatasetNotFoundError(dataset_id)

        if ".." in layout_id or "/" in layout_id or "\\" in layout_id:
            raise LayoutNotFoundError(dataset_id, layout_id)

        if layout_id.strip().lower() in RESERVED_LAYOUT_IDS:
            raise ImmutableLayoutError(layout_id, f"Cannot delete immutable reference layout '{layout_id}'")

        file_path = self.get_layout_file_path(dataset_id, layout_id)
        if not file_path.exists():
            raise LayoutNotFoundError(dataset_id, layout_id)

        file_path.unlink()
        return True


# Default service instance
layout_service = LayoutService()


# Convenience functional wrappers
def create_layout(dataset_id: str, payload: CreateLayoutRequest) -> LayoutRecord:
    return layout_service.create_layout(dataset_id, payload)


def list_layouts(dataset_id: str) -> list[LayoutRecord]:
    return layout_service.list_layouts(dataset_id)


def get_layout(dataset_id: str, layout_id: str) -> LayoutRecord:
    return layout_service.get_layout(dataset_id, layout_id)


def update_layout(dataset_id: str, layout_id: str, payload: UpdateLayoutRequest) -> LayoutRecord:
    return layout_service.update_layout(dataset_id, layout_id, payload)


def delete_layout(dataset_id: str, layout_id: str) -> bool:
    return layout_service.delete_layout(dataset_id, layout_id)


def validate_layout_permutation(
    dataset_id: str,
    permutation: LayoutPermutation | dict[str, str],
) -> LayoutValidationResult:
    return layout_service.validate_layout_permutation(dataset_id, permutation)
