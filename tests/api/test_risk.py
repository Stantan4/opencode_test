"""
Integration Tests for Risk API Endpoints

Tests cover:
1. Normal request - successful risk analysis
2. Missing authentication - 401 response
3. Parameter validation failure - 422 response

Uses mocked LSTM model to avoid dependency on model files.
"""
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
import numpy as np

from app.main import app


@pytest.fixture
def mock_lstm_model():
    """Mock LSTM model to avoid dependency on model files."""
    mock_model = MagicMock()
    mock_model.predict.return_value = MagicMock(item=lambda: 0.3)
    mock_model.eval.return_value = None
    return mock_model


@pytest.fixture
def mock_feature_extractor():
    """Mock feature extractor to avoid needing fitted baseline."""
    mock_extractor = MagicMock()
    mock_extractor.transform.return_value = np.zeros(109, dtype=np.float32)
    mock_extractor.is_fitted = True
    return mock_extractor


@pytest.fixture
def client(mock_lstm_model, mock_feature_extractor):
    """Create test client with mocked components."""
    with patch("app.ml.models.lstm_model.LSTMAnomalyDetector", return_value=mock_lstm_model):
        with patch("app.api.v1.endpoints.risk.get_lstm_model", return_value=mock_lstm_model):
            with patch("app.api.v1.endpoints.risk.get_feature_extractor", return_value=mock_feature_extractor):
                yield TestClient(app)


@pytest.fixture
def auth_headers(client):
    """Get authentication headers for protected endpoints."""
    # Login to get token
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "testuser", "password": "testpass"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestRiskAnalyzeEndpoint:
    """Test POST /api/v1/risk/analyze endpoint."""

    def test_normal_request_success(self, client, auth_headers):
        """Test successful risk analysis request."""
        response = client.post(
            "/api/v1/risk/analyze",
            json={
                "user_id": "test_user_123",
                "login_time": "2024-01-15T10:30:00",
                "ip_address": "192.168.1.100",
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
                "screen_resolution": "1920x1080",
                "timezone": "UTC+8",
                "location": {
                    "latitude": 39.9042,
                    "longitude": 116.4074,
                },
                "event_type": "login",
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "risk_score" in data
        assert "risk_level" in data
        assert "reasons" in data
        assert data["user_id"] == "test_user_123"

    def test_missing_authentication(self, client):
        """Test request without authentication token."""
        response = client.post(
            "/api/v1/risk/analyze",
            json={
                "user_id": "test_user_123",
                "login_time": "2024-01-15T10:30:00",
                "ip_address": "192.168.1.100",
                "user_agent": "Mozilla/5.0",
                "screen_resolution": "1920x1080",
                "timezone": "UTC+8",
                "event_type": "login",
            },
        )

        assert response.status_code == 401

    def test_invalid_token(self, client):
        """Test request with invalid authentication token."""
        response = client.post(
            "/api/v1/risk/analyze",
            json={
                "user_id": "test_user_123",
                "login_time": "2024-01-15T10:30:00",
                "ip_address": "192.168.1.100",
                "user_agent": "Mozilla/5.0",
                "screen_resolution": "1920x1080",
                "timezone": "UTC+8",
                "event_type": "login",
            },
            headers={"Authorization": "Bearer invalid_token_here"},
        )

        assert response.status_code == 401

    def test_missing_required_fields(self, client, auth_headers):
        """Test request with missing required fields."""
        response = client.post(
            "/api/v1/risk/analyze",
            json={
                "user_id": "test_user_123",
                # Missing login_time, ip_address, user_agent
            },
            headers=auth_headers,
        )

        assert response.status_code == 422

    def test_invalid_event_type(self, client, auth_headers):
        """Test request with invalid event type."""
        response = client.post(
            "/api/v1/risk/analyze",
            json={
                "user_id": "test_user_123",
                "login_time": "2024-01-15T10:30:00",
                "ip_address": "192.168.1.100",
                "user_agent": "Mozilla/5.0",
                "screen_resolution": "1920x1080",
                "timezone": "UTC+8",
                "event_type": "invalid_type",
            },
            headers=auth_headers,
        )

        assert response.status_code == 422

    def test_invalid_login_time_format(self, client, auth_headers):
        """Test request with invalid login time format."""
        response = client.post(
            "/api/v1/risk/analyze",
            json={
                "user_id": "test_user_123",
                "login_time": "not-a-valid-date",
                "ip_address": "192.168.1.100",
                "user_agent": "Mozilla/5.0",
                "screen_resolution": "1920x1080",
                "timezone": "UTC+8",
                "event_type": "login",
            },
            headers=auth_headers,
        )

        assert response.status_code == 422


class TestRiskHistoryEndpoint:
    """Test GET /api/v1/risk/history/{user_id} endpoint."""

    def test_get_history_success(self, client, auth_headers):
        """Test successful history retrieval."""
        response = client.get(
            "/api/v1/risk/history/test_user_123",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "items" in data
        assert data["user_id"] == "test_user_123"

    def test_get_history_pagination(self, client, auth_headers):
        """Test history pagination parameters."""
        response = client.get(
            "/api/v1/risk/history/test_user_123?page=2&page_size=10",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["page_size"] == 10

    def test_get_history_without_auth(self, client):
        """Test history endpoint without authentication."""
        response = client.get("/api/v1/risk/history/test_user_123")

        assert response.status_code == 401


class TestRiskThresholdEndpoint:
    """Test POST /api/v1/risk/threshold endpoint."""

    def test_update_threshold_success(self, client, auth_headers):
        """Test successful threshold update."""
        response = client.post(
            "/api/v1/risk/threshold",
            json={
                "config": {
                    "low_threshold": 25,
                    "medium_threshold": 55,
                    "high_threshold": 75,
                    "alert_enabled": True,
                    "alert_threshold": 55,
                }
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_invalid_threshold_order(self, client, auth_headers):
        """Test threshold update with invalid order."""
        response = client.post(
            "/api/v1/risk/threshold",
            json={
                "config": {
                    "low_threshold": 60,
                    "medium_threshold": 30,  # Invalid: should be > low
                    "high_threshold": 80,
                    "alert_enabled": True,
                    "alert_threshold": 50,
                }
            },
            headers=auth_headers,
        )

        assert response.status_code == 400

    def test_threshold_update_without_auth(self, client):
        """Test threshold update without authentication."""
        response = client.post(
            "/api/v1/risk/threshold",
            json={
                "config": {
                    "low_threshold": 30,
                    "medium_threshold": 60,
                    "high_threshold": 80,
                    "alert_enabled": True,
                    "alert_threshold": 60,
                }
            },
        )

        assert response.status_code == 401


class TestRiskTrendEndpoint:
    """Test GET /api/v1/risk/trend/{user_id} endpoint."""

    def test_get_trend_success(self, client, auth_headers):
        """Test successful trend retrieval."""
        response = client.get(
            "/api/v1/risk/trend/test_user_123?days=7",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "trend" in data
        assert "peak_times" in data
        assert data["user_id"] == "test_user_123"
        assert data["days"] == 7

    def test_get_trend_without_auth(self, client):
        """Test trend endpoint without authentication."""
        response = client.get("/api/v1/risk/trend/test_user_123")

        assert response.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v"])