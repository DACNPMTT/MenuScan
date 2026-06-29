from fastapi import APIRouter, Depends

from src.modules.identity.dependencies import require_valid_access_token
from src.modules.identity.router import private_router as identity_private_router
from src.modules.identity.router import public_router as identity_public_router
from src.modules.menu_scan.router import private_router as menu_scan_private_router
from src.modules.menu_scan.router import public_router as menu_scan_public_router


api_router = APIRouter()

public_api_router = APIRouter()
private_api_router = APIRouter(dependencies=[Depends(require_valid_access_token)])

public_api_router.include_router(identity_public_router)
public_api_router.include_router(menu_scan_public_router)

private_api_router.include_router(identity_private_router)
private_api_router.include_router(menu_scan_private_router)

api_router.include_router(public_api_router)
api_router.include_router(private_api_router)
