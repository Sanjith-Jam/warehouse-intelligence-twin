"""Dataset upload, inspection, and lifecycle API endpoints."""
from typing import Optional
import uuid

from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile, status

from backend.app.config import settings
from backend.app.models.schemas import (
    DatasetInspectionResponse,
    ErrorCode,
    ErrorResponse,
    make_error_detail,
)
from backend.app.services.parsing import (
    ParsingError,
    inspect_uploaded_file,
    save_uploaded_dataset,
)

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
    # Allow target_sheet from query parameter or multipart form field
    resolved_sheet = target_sheet
    if not resolved_sheet:
        try:
            form = await request.form()
            form_sheet = form.get("target_sheet")
            if form_sheet and isinstance(form_sheet, str):
                resolved_sheet = form_sheet.strip()
        except Exception:
            pass

    # Generate a cryptographically secure random dataset ID
    dataset_id = f"ds_{uuid.uuid4().hex[:12]}"

    try:
        # Save uploaded stream into isolated staging directory
        raw_path, clean_filename, file_size, _ = save_uploaded_dataset(
            stream=file.file,
            original_filename=file.filename,
            dataset_id=dataset_id,
            max_size_bytes=settings.max_upload_size_bytes,
            base_dir=settings.upload_storage_dir,
        )

        # Inspect workbook: detect sheets, canonical columns, available months, preview rows
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
