from fastapi import APIRouter

from src.modules.identity.router import router as identity_router
from src.modules.billing.router import router as billing_router
from src.modules.exchange.router import router as exchange_router
from src.modules.menu.router import router as menu_router
from src.modules.menu_scan.router import router as menu_scan_router
from src.modules.dining.router import router as dining_router


api_router = APIRouter()
api_router.include_router(identity_router)
api_router.include_router(menu_scan_router)
api_router.include_router(menu_router)
api_router.include_router(billing_router)
api_router.include_router(exchange_router)
api_router.include_router(dining_router)
