"""
Alert Schemas
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class AlertResponse(BaseModel):
    """Alert response schema"""
    alert_id: str
    user_id: str
    alert_type: str
    risk_score: int
    triggered_at: datetime
    status: str
    handled_at: Optional[datetime] = None
    factors: List[dict]
    notification_status: dict

    class Config:
        from_attributes = True


class AlertListResponse(BaseModel):
    """Alert list response schema"""
    total: int
    page: int
    page_size: int
    items: List[AlertResponse]


class AlertHandleRequest(BaseModel):
    """Alert handle request schema"""
    action: str  # required or ignore
    comment: Optional[str] = None
    notify_user: bool = True
