"""
Admin Schemas
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class UserListItem(BaseModel):
    """User list item schema"""
    id: int
    username: str
    email: str
    user_level: str
    status: str
    created_at: datetime
    last_login_at: Optional[datetime] = None


class UserListResponse(BaseModel):
    """User list response schema"""
    total: int
    page: int
    page_size: int
    items: List[UserListItem]


class ThresholdConfig(BaseModel):
    """Threshold configuration schema"""
    low_threshold: int = 30
    medium_threshold: int = 60
    high_threshold: int = 80


class ModelVersion(BaseModel):
    """Model version schema"""
    version_id: str
    version: str
    trained_at: datetime
    accuracy: float
    recall: float
    f1_score: float
    status: str  # pending, deployed, deprecated


class ModelListResponse(BaseModel):
    """Model list response schema"""
    total: int
    items: List[ModelVersion]


class SystemMetrics(BaseModel):
    """System metrics schema"""
    qps: float
    avg_latency_ms: float
    p99_latency_ms: float
    error_rate: float
    model_inference_ms: float


class SystemMetricsResponse(BaseModel):
    """System metrics response schema"""
    realtime: SystemMetrics
    historical: dict
