"""
Risk Assessment Schemas

Pydantic models for risk detection API request/response validation.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Event type enumeration."""

    LOGIN = "login"
    POST = "post"
    COMMENT = "comment"
    DM = "dm"


class LocationInfo(BaseModel):
    """Location information schema."""

    latitude: Optional[float] = Field(None, description="Latitude coordinate")
    longitude: Optional[float] = Field(None, description="Longitude coordinate")


class RiskAnalyzeRequest(BaseModel):
    """Risk analysis request schema.

    POST /api/v1/risk/analyze
    """

    user_id: str = Field(..., description="User ID")
    login_time: datetime = Field(..., description="Login timestamp")
    ip_address: str = Field(..., description="Client IP address")
    user_agent: str = Field(..., description="Browser user agent")
    screen_resolution: str = Field(..., description="Screen resolution (e.g., 1920x1080)")
    timezone: str = Field(..., description="Client timezone (e.g., UTC+8)")
    location: Optional[LocationInfo] = Field(None, description="Geographic location")
    event_type: EventType = Field(EventType.LOGIN, description="Event type")
    event_data: Optional[dict[str, Any]] = Field(None, description="Additional event data")


class RiskComponent(BaseModel):
    """Risk component schema."""

    name: str = Field(..., description="Component name (lstm, location, device, time)")
    score: float = Field(..., description="Score contribution")
    weight: float = Field(..., description="Weight in final calculation")


class RiskAnalyzeResponse(BaseModel):
    """Risk analysis response schema."""

    user_id: str = Field(..., description="User ID")
    risk_score: float = Field(..., description="Final risk score (0-100)")
    risk_level: str = Field(..., description="Risk level: low, medium, high, critical")
    risk_level_display: str = Field(..., description="Risk level display name")
    color: str = Field(..., description="Color code: green, yellow, orange, red")
    reasons: list[str] = Field(default_factory=list, description="Risk reasons")
    components: list[RiskComponent] = Field(..., description="Risk components breakdown")
    alert_triggered: bool = Field(..., description="Whether alert was triggered")
    alert_id: Optional[str] = Field(None, description="Alert ID if triggered")
    analyzed_at: datetime = Field(..., description="Analysis timestamp")


class RiskRecord(BaseModel):
    """Risk record schema."""

    id: str = Field(..., description="Record ID")
    user_id: str = Field(..., description="User ID")
    risk_score: float = Field(..., description="Risk score")
    risk_level: str = Field(..., description="Risk level")
    event_type: str = Field(..., description="Event type")
    ip_address: Optional[str] = Field(None, description="IP address")
    reasons: list[str] = Field(default_factory=list, description="Risk reasons")
    created_at: datetime = Field(..., description="Created timestamp")

    class Config:
        from_attributes = True


class RiskHistoryResponse(BaseModel):
    """Risk history response schema.

    GET /api/v1/risk/history/{user_id}
    """

    user_id: str = Field(..., description="User ID")
    total: int = Field(..., description="Total records")
    page: int = Field(..., description="Current page")
    page_size: int = Field(..., description="Page size")
    items: list[RiskRecord] = Field(default_factory=list, description="Risk records")


class RiskThresholdConfig(BaseModel):
    """Risk threshold configuration schema."""

    low_threshold: int = Field(30, description="Low risk threshold (default 30)")
    medium_threshold: int = Field(60, description="Medium risk threshold (default 60)")
    high_threshold: int = Field(80, description="High risk threshold (default 80)")
    alert_enabled: bool = Field(True, description="Enable automatic alerts")
    alert_threshold: int = Field(60, description="Alert trigger threshold")


class RiskThresholdUpdateRequest(BaseModel):
    """Risk threshold update request schema.

    POST /api/v1/risk/threshold
    """

    config: RiskThresholdConfig = Field(..., description="Threshold configuration")


class RiskThresholdUpdateResponse(BaseModel):
    """Risk threshold update response schema."""

    success: bool = Field(..., description="Update success status")
    message: str = Field(..., description="Response message")
    updated_config: Optional[RiskThresholdConfig] = Field(None, description="Updated configuration")
    updated_at: datetime = Field(..., description="Update timestamp")


class RiskTrendData(BaseModel):
    """Risk trend data schema."""

    date: str = Field(..., description="Date")
    high_risk_count: int = Field(..., description="High risk events count")
    avg_risk_score: float = Field(..., description="Average risk score")


class RiskTrendResponse(BaseModel):
    """Risk trend response schema."""

    user_id: str = Field(..., description="User ID")
    days: int = Field(..., description="Days analyzed")
    trend: list[RiskTrendData] = Field(default_factory=list, description="Trend data")
    peak_times: dict[str, int] = Field(default_factory=dict, description="Peak time distribution")


# Legacy schemas (for backward compatibility)
class RiskEvaluationRequest(BaseModel):
    """Legacy risk evaluation request schema."""

    login_time: datetime
    ip_address: str
    user_agent: str
    device_fingerprint: str
    location: Optional[LocationInfo] = None
    event_type: str = "login"
    event_data: Optional[dict] = None


class RiskFactor(BaseModel):
    """Legacy risk factor schema."""

    type: str
    description: str
    weight: float


class RiskEvaluationResponse(BaseModel):
    """Legacy risk evaluation response schema."""

    risk_score: int
    risk_level: str
    anomaly_probability: float
    factors: list[RiskFactor]
    recommended_action: str
    alert_id: Optional[str] = None


class RiskHistoryResponseLegacy(BaseModel):
    """Legacy risk history response schema."""

    total: int
    page: int
    page_size: int
    items: list[RiskRecord]