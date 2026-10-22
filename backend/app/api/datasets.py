"""Dataset upload, inspection, preprocessing, and export API endpoints."""
from typing import Optional
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import FileResponse

from backend.app.config import settings
from backend.app.models.schemas import (
    DatasetDetailResponse,
    DatasetExportResponse,
    DatasetInspectionResponse,
    ErrorCode,
    ErrorResponse,
    PreprocessRequest,
    make_error_detail,
)
from backend.app.services.dataset_store import (
    DatasetNotFoundError,
    DatasetNotPreprocessedError,
    DatasetStoreError,
    ImmutableDatasetError,
    export_dataset,
    get_dataset_detail,
    preprocess_and_store_dataset,
)
from backend.app.services.parsing import (
    ParsingError,
    inspect_uploaded_file,
    save_uploaded_dataset,
)
from backend.app.services.preprocessing import PreprocessingError

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


@router.post(
    "/upload",
    response_model=DatasetInspectionResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponse,
            "description": "Unsupported file type, corrupted archive, or empty file",
        },
        status.HTTP_413_CONTENT_TOO_LARGE: {
            "model": ErrorResponse,
            "description": "File exceeds maximum upload size limit",
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ErrorResponse,
            "description": "Unprocessable workbook parameters or schema mismatch",
        },
    },
)
async def upload_dataset(
    request: Request,
    file: UploadFile = File(..., description="Multipart workbook file (.csv, .xlsx, or .xls)"),
    target_sheet: Optional[str] = Query(
        default=None,
        description="Target sheet name for multi-sheet Excel workbooks",
    ),
) -> DatasetInspectionResponse:
    """Upload a raw workbook (.csv, .xlsx, .xls) for safe inspection and session staging.

    Validates file extension, magic bytes, and size limit.
    Inspects columns, detects canonical aliases, parses available months, and returns preview rows.
    Raw uploads are staged in session-isolated storage and never modify demo.json.
    """
    resolved_sheet = target_sheet
    if not resolved_sheet:
        try:
            form = await request.form()
            form_sheet = form.get("target_sheet")
            if form_sheet and isinstance(form_sheet, str):
                resolved_sheet = form_sheet.strip()
        except Exception:
            pass

    dataset_id = f"ds_{uuid.uuid4().hex[:12]}"

    try:
        raw_path, clean_filename, file_size, _ = save_uploaded_dataset(
            stream=file.file,
            original_filename=file.filename,
            dataset_id=dataset_id,
            max_size_bytes=settings.max_upload_size_bytes,
            base_dir=settings.upload_storage_dir,
        )

        inspection = inspect_uploaded_file(
            file_path=raw_path,
            filename=clean_filename,
            dataset_id=dataset_id,
            file_size_bytes=file_size,
            target_sheet=resolved_sheet,
        )

        return inspection

    except ParsingError as err:
        if err.code == ErrorCode.FILE_TOO_LARGE:
            http_status = status.HTTP_413_CONTENT_TOO_LARGE
        elif err.code in (ErrorCode.UNSUPPORTED_FILE_TYPE, ErrorCode.EMPTY_FILE):
            http_status = status.HTTP_400_BAD_REQUEST
        elif err.code == ErrorCode.MISSING_REQUIRED_COLUMNS:
            http_status = status.HTTP_422_UNPROCESSABLE_CONTENT
        else:
            http_status = status.HTTP_400_BAD_REQUEST

        raise HTTPException(
            status_code=http_status,
            detail=make_error_detail(err.code, err.message, err.details).model_dump(),
        ) from err
    except HTTPException:
        raise
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=make_error_detail(
                ErrorCode.UNSUPPORTED_FILE_TYPE,
                f"Failed to process uploaded dataset: {err}",
            ).model_dump(),
        ) from err


@router.post(
    "/{dataset_id}/preprocess",
    response_model=DatasetDetailResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "Dataset staging directory or raw file not found",
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ErrorResponse,
            "description": "No data in selected month, missing columns, or immutable demo dataset",
        },
    },
)
async def preprocess_dataset_endpoint(
    dataset_id: str,
    payload: PreprocessRequest,
) -> DatasetDetailResponse:
    """Preprocess an uploaded workbook into a clean, reproducible warehouse simulation snapshot."""
    try:
        detail = preprocess_and_store_dataset(
            dataset_id=dataset_id,
            request=payload,
            base_dir=settings.upload_storage_dir,
        )
        return detail
    except DatasetNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=make_error_detail(ErrorCode.DATASET_NOT_FOUND, err.message, err.details).model_dump(),
        ) from err
    except ImmutableDatasetError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=make_error_detail(ErrorCode.IMMUTABLE_DATASET, err.message, err.details).model_dump(),
        ) from err
    except PreprocessingError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=make_error_detail(err.code, err.message, err.details).model_dump(),
        ) from err
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=make_error_detail(
                ErrorCode.DATASET_NOT_FOUND,
                f"Failed to preprocess dataset '{dataset_id}': {err}",
            ).model_dump(),
        ) from err


@router.get(
    "/{dataset_id}",
    response_model=DatasetDetailResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "Dataset not found or has not been preprocessed yet",
        },
    },
)
async def get_dataset_endpoint(dataset_id: str) -> DatasetDetailResponse:
    """Retrieve full preprocessed dataset details including metadata, cleaning report, layout, products, and orders."""
    try:
        return get_dataset_detail(dataset_id=dataset_id, base_dir=settings.upload_storage_dir)
    except DatasetNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=make_error_detail(ErrorCode.DATASET_NOT_FOUND, err.message, err.details).model_dump(),
        ) from err
    except DatasetNotPreprocessedError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=make_error_detail(ErrorCode.DATASET_NOT_FOUND, err.message, err.details).model_dump(),
        ) from err
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=make_error_detail(
                ErrorCode.DATASET_NOT_FOUND,
                f"Error retrieving dataset '{dataset_id}': {err}",
            ).model_dump(),
        ) from err


@router.get(
    "/{dataset_id}/export",
    response_model=DatasetExportResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "Dataset not found or not preprocessed",
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponse,
            "description": "Unsupported export format",
        },
    },
)
async def export_dataset_endpoint(
    dataset_id: str,
    format: str = Query(default="json", description="Export format ('json' or 'csv')"),
) -> DatasetExportResponse:
    """Export metadata and download descriptor for a preprocessed dataset."""
    try:
        export_resp, _ = export_dataset(
            dataset_id=dataset_id,
            export_format=format,
            base_dir=settings.upload_storage_dir,
        )
        return export_resp
    except (DatasetNotFoundError, DatasetNotPreprocessedError) as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=make_error_detail(ErrorCode.DATASET_NOT_FOUND, err.message, err.details).model_dump(),
        ) from err
    except DatasetStoreError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=make_error_detail(ErrorCode.UNSUPPORTED_FILE_TYPE, err.message, err.details).model_dump(),
        ) from err


@router.get(
    "/{dataset_id}/download",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "Dataset not found or not preprocessed",
        },
    },
)
async def download_dataset_endpoint(
    dataset_id: str,
    format: str = Query(default="json", description="File format to download ('json' or 'csv')"),
) -> FileResponse:
    """Download preprocessed dataset artifacts as a JSON or CSV file attachment."""
    try:
        export_resp, file_path = export_dataset(
            dataset_id=dataset_id,
            export_format=format,
            base_dir=settings.upload_storage_dir,
        )
        media_type = "application/json" if export_resp.format == "json" else "text/csv"
        ext = "json" if export_resp.format == "json" else "csv"
        filename = f"{dataset_id}_export.{ext}"
        return FileResponse(
            path=file_path,
            media_type=media_type,
            filename=filename,
        )
    except (DatasetNotFoundError, DatasetNotPreprocessedError) as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=make_error_detail(ErrorCode.DATASET_NOT_FOUND, err.message, err.details).model_dump(),
        ) from err
    except DatasetStoreError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=make_error_detail(ErrorCode.UNSUPPORTED_FILE_TYPE, err.message, err.details).model_dump(),
        ) from err
