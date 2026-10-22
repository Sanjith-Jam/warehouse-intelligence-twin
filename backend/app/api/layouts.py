"""Layouts API router for dataset-scoped warehouse layout scenarios."""
from typing import Any
from fastapi import APIRouter, HTTPException, status

from backend.app.models.schemas import (
    CreateLayoutRequest,
    ErrorCode,
    ErrorResponse,
    LayoutPermutation,
    LayoutRecord,
    LayoutValidationResult,
    LayoutsListResponse,
    UpdateLayoutRequest,
    make_error_detail,
)
from backend.app.services.layout_service import (
    DatasetNotFoundError,
    ImmutableLayoutError,
    InvalidLayoutPermutationError,
    LayoutAlreadyExistsError,
    LayoutNotFoundError,
    LayoutServiceError,
    layout_service,
)

router = APIRouter(prefix="/api/datasets", tags=["layouts"])


@router.post(
    "/{dataset_id}/layouts",
    response_model=LayoutRecord,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponse,
            "description": "Immutable reference name or layout ID violation",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "Dataset not found",
        },
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponse,
            "description": "Layout already exists",
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ErrorResponse,
            "description": "Invalid layout permutation",
        },
    },
)
def create_layout_endpoint(
    dataset_id: str,
    payload: CreateLayoutRequest,
) -> LayoutRecord:
    """Create a new named layout scenario for dataset_id."""
    try:
        return layout_service.create_layout(dataset_id, payload)
    except DatasetNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=make_error_detail(err.code, err.message, err.details).model_dump(),
        ) from err
    except ImmutableLayoutError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=make_error_detail(ErrorCode.INVALID_LAYOUT_PERMUTATION, err.message, err.details).model_dump(),
        ) from err
    except LayoutAlreadyExistsError as err:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=make_error_detail("LAYOUT_ALREADY_EXISTS", err.message, err.details).model_dump(),
        ) from err
    except InvalidLayoutPermutationError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=make_error_detail(err.code, err.message, err.details).model_dump(),
        ) from err
    except LayoutServiceError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=make_error_detail(err.code, err.message, err.details).model_dump(),
        ) from err


@router.get(
    "/{dataset_id}/layouts",
    response_model=LayoutsListResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "Dataset not found",
        },
    },
)
def list_layouts_endpoint(dataset_id: str) -> LayoutsListResponse:
    """List all saved layouts and built-in reference layouts for dataset_id."""
    try:
        layouts = layout_service.list_layouts(dataset_id)
        return LayoutsListResponse(dataset_id=dataset_id, layouts=layouts)
    except DatasetNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=make_error_detail(err.code, err.message, err.details).model_dump(),
        ) from err


@router.post(
    "/{dataset_id}/layouts/validate",
    response_model=LayoutValidationResult,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "Dataset not found",
        },
    },
)
def validate_layout_endpoint(
    dataset_id: str,
    payload: LayoutPermutation,
) -> LayoutValidationResult:
    """Validate a layout permutation without saving."""
    try:
        return layout_service.validate_layout_permutation(dataset_id, payload)
    except DatasetNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=make_error_detail(err.code, err.message, err.details).model_dump(),
        ) from err


@router.get(
    "/{dataset_id}/layouts/{layout_id}",
    response_model=LayoutRecord,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "Dataset or layout not found",
        },
    },
)
def get_layout_endpoint(dataset_id: str, layout_id: str) -> LayoutRecord:
    """Get a specific layout by ID for dataset_id."""
    try:
        return layout_service.get_layout(dataset_id, layout_id)
    except DatasetNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=make_error_detail(err.code, err.message, err.details).model_dump(),
        ) from err
    except LayoutNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=make_error_detail(err.code, err.message, err.details).model_dump(),
        ) from err


@router.put(
    "/{dataset_id}/layouts/{layout_id}",
    response_model=LayoutRecord,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponse,
            "description": "Immutable reference modification violation",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "Dataset or layout not found",
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ErrorResponse,
            "description": "Invalid layout permutation",
        },
    },
)
def update_layout_endpoint(
    dataset_id: str,
    layout_id: str,
    payload: UpdateLayoutRequest,
) -> LayoutRecord:
    """Update layout permutation, name, or description."""
    try:
        return layout_service.update_layout(dataset_id, layout_id, payload)
    except DatasetNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=make_error_detail(err.code, err.message, err.details).model_dump(),
        ) from err
    except LayoutNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=make_error_detail(err.code, err.message, err.details).model_dump(),
        ) from err
    except ImmutableLayoutError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=make_error_detail(ErrorCode.INVALID_LAYOUT_PERMUTATION, err.message, err.details).model_dump(),
        ) from err
    except InvalidLayoutPermutationError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=make_error_detail(err.code, err.message, err.details).model_dump(),
        ) from err
    except LayoutServiceError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=make_error_detail(err.code, err.message, err.details).model_dump(),
        ) from err


@router.delete(
    "/{dataset_id}/layouts/{layout_id}",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponse,
            "description": "Immutable reference deletion violation",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "Dataset or layout not found",
        },
    },
)
def delete_layout_endpoint(dataset_id: str, layout_id: str) -> dict[str, Any]:
    """Delete a layout scenario under dataset_id."""
    try:
        deleted = layout_service.delete_layout(dataset_id, layout_id)
        return {"status": "deleted", "layout_id": layout_id, "success": deleted}
    except DatasetNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=make_error_detail(err.code, err.message, err.details).model_dump(),
        ) from err
    except LayoutNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=make_error_detail(err.code, err.message, err.details).model_dump(),
        ) from err
    except ImmutableLayoutError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=make_error_detail(ErrorCode.INVALID_LAYOUT_PERMUTATION, err.message, err.details).model_dump(),
        ) from err
