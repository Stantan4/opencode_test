"""
Health Check Endpoint
"""
from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@router.get("/health/ready")
async def readiness_check():
    """Readiness check endpoint"""
    return {"status": "ready"}
