"""
Admin Management Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

from app.schemas.admin import (
    UserListResponse,
    ThresholdConfig,
    ModelListResponse,
    SystemMetricsResponse
)

router = APIRouter(prefix="/admin", tags=["Admin"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


@router.get("/users", response_model=UserListResponse)
async def get_users(
    page: int = 1,
    page_size: int = 20,
    keyword: str = None,
    status: str = None,
    token: str = Depends(oauth2_scheme)
):
    """Query user list"""
    # Implementation to be added
    pass


@router.get("/config/thresholds", response_model=ThresholdConfig)
async def get_threshold_config(token: str = Depends(oauth2_scheme)):
    """Get risk threshold configuration"""
    # Implementation to be added
    pass


@router.put("/config/thresholds")
async def update_threshold_config(
    config: ThresholdConfig,
    token: str = Depends(oauth2_scheme)
):
    """Update risk threshold configuration"""
    # Implementation to be added
    pass


@router.get("/models", response_model=ModelListResponse)
async def get_models(token: str = Depends(oauth2_scheme)):
    """Get model version list"""
    # Implementation to be added
    pass


@router.post("/models/{version_id}/deploy")
async def deploy_model(
    version_id: str,
    token: str = Depends(oauth2_scheme)
):
    """Deploy specified model version"""
    # Implementation to be added
    pass


@router.post("/models/{version_id}/rollback")
async def rollback_model(
    version_id: str,
    token: str = Depends(oauth2_scheme)
):
    """Rollback to specified model version"""
    # Implementation to be added
    pass


@router.get("/metrics", response_model=SystemMetricsResponse)
async def get_system_metrics(token: str = Depends(oauth2_scheme)):
    """Get system running metrics"""
    # Implementation to be added
    pass
