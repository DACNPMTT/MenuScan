from fastapi import APIRouter

from src.modules.identity.router import router as identity_router
from src.modules.menu_scan.router import router as menu_scan_router
from src.modules.billing.router import router as billing_router



api_router = APIRouter()
api_router.include_router(identity_router)
api_router.include_router(menu_scan_router)
api_router.include_router(billing_router)
