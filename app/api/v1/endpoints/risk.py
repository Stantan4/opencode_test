"""
Risk Assessment Endpoints

API endpoints for risk analysis, history, and threshold configuration.
All endpoints require JWT authentication.
"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.schemas.risk import (
    RiskAnalyzeRequest,
    RiskAnalyzeResponse,
    RiskComponent,
    RiskHistoryResponse,
    RiskRecord,
    RiskThresholdConfig,
    RiskThresholdUpdateRequest,
    RiskThresholdUpdateResponse,
    RiskTrendResponse,
    RiskTrendData,
)
from app.schemas.user import User
from app.services.risk_service import RiskScoringEngine, create_scoring_engine
from app.ml.feature_extractor import (
    BehaviorFeatureExtractor,
    LoginEvent,
    DeviceFingerprintGenerator,
    create_feature_extractor,
)
from app.ml.models.lstm_model import LSTMAnomalyDetector
from app.core.security.jwt import decode_token

# Router configuration
router = APIRouter(prefix="/risk", tags=["Risk Assessment"])

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# Global instances (would be managed by dependency injection in production)
_scoring_engine: Optional[RiskScoringEngine] = None
_feature_extractor: Optional[BehaviorFeatureExtractor] = None
_lstm_model: Optional[LSTMAnomalyDetector] = None
_threshold_config: RiskThresholdConfig = RiskThresholdConfig(
    low_threshold=30,
    medium_threshold=60,
    high_threshold=80,
    alert_enabled=True,
    alert_threshold=60,
)


def get_scoring_engine() -> RiskScoringEngine:
    """Get or create risk scoring engine instance."""
    global _scoring_engine
    if _scoring_engine is None:
        _scoring_engine = create_scoring_engine()
    return _scoring_engine


def get_feature_extractor() -> BehaviorFeatureExtractor:
    """Get or create feature extractor instance."""
    global _feature_extractor
    if _feature_extractor is None:
        _feature_extractor = create_feature_extractor()
    return _feature_extractor


def get_lstm_model() -> LSTMAnomalyDetector:
    """Get or create LSTM model instance."""
    global _lstm_model
    if _lstm_model is None:
        # Create model with default input dimension (109)
        _lstm_model = LSTMAnomalyDetector(input_dim=109)
    return _lstm_model


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Validate JWT token and get current user.

    Args:
        token: JWT access token

    Returns:
        User object

    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_token(token)
    if payload is None:
        raise credentials_exception

    user_id: str = str(payload.get("sub", ""))
    if not user_id:
        raise credentials_exception

    # In production, fetch user from database
    # For now, create a minimal User object
    return User(
        id=1,
        username=user_id,
        email=f"{user_id}@example.com",
        user_level="normal",
        status="active",
        created_at=datetime.utcnow(),
    )


@router.post(
    "/analyze",
    response_model=RiskAnalyzeResponse,
    summary="Analyze Risk",
    description="Analyze user behavior and calculate risk score",
)
async def analyze_risk(
    request: RiskAnalyzeRequest,
    current_user: User = Depends(get_current_user),
) -> RiskAnalyzeResponse:
    """Analyze user behavior and calculate risk score.

    This endpoint:
    1. Extracts features from user behavior log
    2. Runs LSTM model inference
    3. Calculates risk score using scoring engine
    4. Triggers alert if threshold exceeded

    Args:
        request: Risk analysis request with user behavior data
        current_user: Authenticated user (from JWT)

    Returns:
        RiskAnalyzeResponse with score, level, and reasons

    Raises:
        HTTPException: If analysis fails
    """
    try:
        # Initialize components
        scoring_engine = get_scoring_engine()
        feature_extractor = get_feature_extractor()
        lstm_model = get_lstm_model()

        # Generate device fingerprint
        device_fingerprint = DeviceFingerprintGenerator.generate(
            user_agent=request.user_agent,
            screen_resolution=request.screen_resolution,
            timezone=request.timezone,
        )

        # Create login event
        login_event = LoginEvent(
            user_id=request.user_id,
            timestamp=request.login_time,
            ip_address=request.ip_address,
            latitude=request.location.latitude if request.location else None,
            longitude=request.location.longitude if request.location else None,
            user_agent=request.user_agent,
            screen_resolution=request.screen_resolution,
            timezone=request.timezone,
            operation_type=request.event_type.value,
        )

        # Extract features (requires baseline - use dummy for now)
        # In production, would load baseline from database
        features = feature_extractor.transform(login_event)

        # Reshape for LSTM: (1, seq_len, features) -> use last 30 events as sequence
        # For single event, pad to sequence length
        import numpy as np

        seq_len = 30
        if features.shape[0] < 109:
            # Single event - pad sequence
            padded_features = np.zeros((seq_len, 109), dtype=np.float32)
            padded_features[-1] = features
        else:
            # Already a sequence
            padded_features = features

        # Convert to tensor and add batch dimension
        import torch

        input_tensor = torch.from_numpy(padded_features).unsqueeze(0)

        # Run LSTM inference
        lstm_model.eval()
        with torch.no_grad():
            lstm_probability = lstm_model.predict(input_tensor).item()

        # Calculate location anomaly (simplified - would use baseline in production)
        location_anomaly = 0.0
        if request.location and request.location.latitude and request.location.longitude:
            # Assume normal if within reasonable distance
            location_anomaly = 0.1  # Default low anomaly

        # Check device change (would compare with baseline in production)
        is_new_device = False  # Would check against historical devices

        # Calculate time anomaly (simplified)
        hour = request.login_time.hour + request.login_time.minute / 60.0
        # Assume normal working hours
        time_anomaly = 0.2 if 9 <= hour <= 18 else 0.4

        # Build features dict for scoring engine
        scoring_features = {
            "lstm_probability": lstm_probability,
            "location_anomaly": location_anomaly,
            "is_new_device": is_new_device,
            "time_anomaly": time_anomaly,
        }

        # Calculate risk score
        risk_result = scoring_engine.calculate_score(scoring_features)

        # Determine if alert should be triggered
        alert_triggered = risk_result.score >= _threshold_config.alert_threshold
        alert_id = f"alert_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}" if alert_triggered else None

        # Build response components
        components = [
            RiskComponent(
                name="lstm",
                score=risk_result.details["components"]["lstm_score"],
                weight=risk_result.details["weights"]["lstm"],
            ),
            RiskComponent(
                name="location",
                score=risk_result.details["components"]["location_score"],
                weight=risk_result.details["weights"]["location"],
            ),
            RiskComponent(
                name="device",
                score=risk_result.details["components"]["device_score"],
                weight=risk_result.details["weights"]["device"],
            ),
            RiskComponent(
                name="time",
                score=risk_result.details["components"]["time_score"],
                weight=risk_result.details["weights"]["time"],
            ),
        ]

        return RiskAnalyzeResponse(
            user_id=request.user_id,
            risk_score=risk_result.score,
            risk_level=risk_result.level.value,
            risk_level_display=risk_result.level.display_name,
            color=risk_result.level.color,
            reasons=risk_result.reasons,
            components=components,
            alert_triggered=alert_triggered,
            alert_id=alert_id,
            analyzed_at=datetime.utcnow(),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Risk analysis failed: {str(e)}",
        )


@router.get(
    "/history/{user_id}",
    response_model=RiskHistoryResponse,
    summary="Get Risk History",
    description="Query historical risk records with pagination",
)
async def get_risk_history(
    user_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
) -> RiskHistoryResponse:
    """Query historical risk records for a user.

    Args:
        user_id: User ID to query
        start_date: Start date filter (ISO format)
        end_date: End date filter (ISO format)
        page: Page number (1-indexed)
        page_size: Items per page
        current_user: Authenticated user (from JWT)

    Returns:
        RiskHistoryResponse with paginated risk records

    Raises:
        HTTPException: If query fails
    """
    # Validate pagination
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 20
    if page_size > 100:
        page_size = 100

    # In production, query from database
    # For now, return empty response
    return RiskHistoryResponse(
        user_id=user_id,
        total=0,
        page=page,
        page_size=page_size,
        items=[],
    )


@router.post(
    "/threshold",
    response_model=RiskThresholdUpdateResponse,
    summary="Update Risk Threshold",
    description="Update risk alert threshold configuration",
)
async def update_threshold(
    request: RiskThresholdUpdateRequest,
    current_user: User = Depends(get_current_user),
) -> RiskThresholdUpdateResponse:
    """Update risk threshold configuration.

    Only admin users should be able to update thresholds.

    Args:
        request: New threshold configuration
        current_user: Authenticated user (from JWT)

    Returns:
        RiskThresholdUpdateResponse with updated config

    Raises:
        HTTPException: If update fails
    """
    global _threshold_config

    try:
        # Validate thresholds
        config = request.config
        if config.low_threshold >= config.medium_threshold:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Low threshold must be less than medium threshold",
            )
        if config.medium_threshold >= config.high_threshold:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Medium threshold must be less than high threshold",
            )

        # Update global config
        _threshold_config = config

        return RiskThresholdUpdateResponse(
            success=True,
            message="Threshold configuration updated successfully",
            updated_config=_threshold_config,
            updated_at=datetime.utcnow(),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Threshold update failed: {str(e)}",
        )


@router.get(
    "/trend/{user_id}",
    response_model=RiskTrendResponse,
    summary="Get Risk Trend",
    description="Analyze risk score trends over time",
)
async def get_risk_trend(
    user_id: str,
    days: int = 30,
    current_user: User = Depends(get_current_user),
) -> RiskTrendResponse:
    """Analyze risk score trends for a user.

    Args:
        user_id: User ID to analyze
        days: Number of days to analyze (default 30)
        current_user: Authenticated user (from JWT)

    Returns:
        RiskTrendResponse with trend data

    Raises:
        HTTPException: If analysis fails
    """
    # Validate days
    if days < 1:
        days = 1
    if days > 365:
        days = 365

    # In production, query from database and calculate trends
    # For now, return empty response
    return RiskTrendResponse(
        user_id=user_id,
        days=days,
        trend=[],
        peak_times={},
    )


# Legacy endpoints (for backward compatibility)
@router.post("/evaluate")
async def evaluate_risk_legacy(
    request: dict,
    token: str = Depends(oauth2_scheme),
) -> dict:
    """Legacy risk evaluation endpoint."""
    # Redirect to new endpoint
    raise HTTPException(
        status_code=status.HTTP_MOVED_PERMANENTLY,
        detail="Use POST /api/v1/risk/analyze instead",
    )


@router.get("/history")
async def get_risk_history_legacy(
    user_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    token: str = Depends(oauth2_scheme),
) -> dict:
    """Legacy risk history endpoint."""
    # Redirect to new endpoint with user_id in path
    raise HTTPException(
        status_code=status.HTTP_MOVED_PERMANENTLY,
        detail="Use GET /api/v1/risk/history/{user_id} instead",
    )