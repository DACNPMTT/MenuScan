from __future__ import annotations

import logging
import uuid

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import RedirectResponse, Response

from src.core.rate_limit import enforce_scan_throttle
from src.core.responses import success_response
from src.modules.identity.dependencies import get_current_user, get_optional_current_user
from src.modules.identity.models import User
from src.modules.menu_scan.dependencies import get_scan_pipeline, get_scan_service
from src.modules.menu_scan.pipeline import ScanPipeline
from src.modules.menu_scan.service import ScanService, UploadCandidate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scans", tags=["scans"])


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def create_scan(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(default=[]),
    file: UploadFile | None = File(default=None),
    target_language: str | None = Form(default=None),
    current_user: User | None = Depends(get_optional_current_user),
    service: ScanService = Depends(get_scan_service),
    pipeline: ScanPipeline = Depends(get_scan_pipeline),
    _throttle: None = Depends(enforce_scan_throttle),
) -> dict[str, object]:
    # Accept the multi-file field ``files`` (up to 8 pages) and the legacy
    # single-file field ``file`` for backward compatibility.
    uploads = list(files)
    if file is not None:
        uploads.append(file)
    candidates = [
        UploadCandidate(file_name=upload.filename, content=await upload.read())
        for upload in uploads
    ]

    data = service.create_scan(
        user=current_user,
        files=candidates,
        target_language=target_language,
    )
    background_tasks.add_task(_run_pipeline, pipeline, data.id)
    return success_response(data=data.model_dump(mode="json"))


@router.get("", status_code=status.HTTP_200_OK)
def list_scans(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    service: ScanService = Depends(get_scan_service),
) -> dict[str, object]:
    items, total = service.list_scans(
        user=current_user,
        page=page,
        page_size=page_size,
    )
    total_pages = (total + page_size - 1) // page_size
    return success_response(
        data=[item.model_dump(mode="json") for item in items],
        meta={
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
        },
    )


@router.get("/{scan_id}", status_code=status.HTTP_200_OK)
def get_scan(
    scan_id: uuid.UUID,
    current_user: User | None = Depends(get_optional_current_user),
    service: ScanService = Depends(get_scan_service),
) -> dict[str, object]:
    data = service.get_scan(user=current_user, scan_id=scan_id)
    return success_response(data=data.model_dump(mode="json"))


@router.get("/{scan_id}/source", status_code=status.HTTP_200_OK)
def get_scan_source(
    scan_id: uuid.UUID,
    current_user: User | None = Depends(get_optional_current_user),
    service: ScanService = Depends(get_scan_service),
) -> Response:
    access = service.get_source_access(user=current_user, scan_id=scan_id)
    if access.redirect_url is not None:
        return RedirectResponse(access.redirect_url, status_code=status.HTTP_302_FOUND)

    assert access.data is not None  # noqa: S101
    return Response(
        content=access.data,
        media_type=access.mime_type,
        headers={"Content-Disposition": f'inline; filename="{access.file_name}"'},
    )


@router.get("/{scan_id}/result", status_code=status.HTTP_200_OK)
def get_scan_result(
    scan_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=6, ge=1, le=50),
    current_user: User | None = Depends(get_optional_current_user),
    service: ScanService = Depends(get_scan_service),
) -> dict[str, object]:
    data, total = service.get_result(
        user=current_user,
        scan_id=scan_id,
        page=page,
        page_size=page_size,
    )
    total_pages = (total + page_size - 1) // page_size
    return success_response(
        data=data.model_dump(mode="json"),
        meta={
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
        },
    )


def _run_pipeline(pipeline: ScanPipeline, scan_id: uuid.UUID) -> None:
    """Background task wrapper — catches exceptions to prevent unhandled crashes."""
    try:
        pipeline.process(scan_id)
    except Exception:
        logger.exception("pipeline_background_error scan_id=%s", scan_id)
