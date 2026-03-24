"""
API v1 Router - Combines all endpoints
"""
from fastapi import APIRouter

from app.api.v1.endpoints import auth, risk, alerts, admin, health

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router)
api_router.include_router(risk.router)
api_router.include_router(alerts.router)
api_router.include_router(admin.router)
api_router.include_router(health.router)
