from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.responses import RedirectResponse, Response

from src.core.responses import success_response
from src.modules.identity.dependencies import get_authenticated_user
from src.modules.menu_scan.dependencies import get_ocr_service, get_scan_service
from src.modules.menu_scan.ocr.service import OcrService, OcrSource
from src.modules.menu_scan.service import ScanService

public_router = APIRouter(prefix="/scans", tags=["scans"])
private_router = APIRouter(prefix="/scans", tags=["scans"])


@private_router.post("", status_code=status.HTTP_202_ACCEPTED)
async def create_scan(
    file: UploadFile = File(...),
    target_language: str | None = Form(default=None),
    current_user=Depends(get_authenticated_user),
    service: ScanService = Depends(get_scan_service),
) -> dict[str, object]:
    data = service.create_scan(
        user=current_user,
        file_name=file.filename,
        content=await file.read(),
        target_language=target_language,
    )
    return success_response(data=data.model_dump(mode="json"))


@public_router.post("/ocr-test", status_code=status.HTTP_200_OK)
async def test_ocr_document(
    file: UploadFile = File(...),
    service: OcrService = Depends(get_ocr_service),
) -> dict[str, object]:
    """Run OCR immediately for a source document without persisting results.

    This endpoint exists for provider/preprocessing verification. It does not
    create scan state, write OCR results, parse menu items, or mutate source
    storage.
    """
    content = await file.read()
    document = service.process(
        OcrSource(
            object_key=f"ocr-test/public/{file.filename or 'source'}",
            data=content,
            mime_type=file.content_type or "application/octet-stream",
        )
    )
    return success_response(data=document.model_dump(mode="json"))


@private_router.get("/{scan_id}", status_code=status.HTTP_200_OK)
def get_scan(
    scan_id: uuid.UUID,
    current_user=Depends(get_authenticated_user),
    service: ScanService = Depends(get_scan_service),
) -> dict[str, object]:
    data = service.get_scan(user=current_user, scan_id=scan_id)
    return success_response(data=data.model_dump(mode="json"))


@private_router.get("/{scan_id}/source", status_code=status.HTTP_200_OK)
def get_scan_source(
    scan_id: uuid.UUID,
    current_user=Depends(get_authenticated_user),
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


router = APIRouter()
router.include_router(public_router)
router.include_router(private_router)
