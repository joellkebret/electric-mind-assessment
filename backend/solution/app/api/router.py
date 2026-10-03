"""Route modules mounted by the application."""

from fastapi import APIRouter

from app.api.health import router as health_router
from app.api.portfolios import router as portfolios_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(portfolios_router)
