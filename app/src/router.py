from fastapi import APIRouter

from src.modules.identity.router import router as identity_router


api_router = APIRouter()
api_router.include_router(identity_router)
