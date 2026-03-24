"""
Risk Scoring Engine.

This module implements the risk scoring algorithm for account theft detection.
It combines LSTM model predictions with rule-based features to generate a unified risk score.
"""
import enum
from dataclasses import dataclass, field
from typing import Any

import numpy as np


class RiskLevel(enum.Enum):
    """Risk level enumeration."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @property
    def color(self) -> str:
        """Get color code for the risk level."""
        colors = {
            "low": "green",
            "medium": "yellow",
            "high": "orange",
            "critical": "red",
        }
        return colors[self.value]

    @property
    def display_name(self) -> str:
        """Get display name for the risk level."""
        names = {
            "low": "低风险",
            "medium": "中风险",
            "high": "高风险",
            "critical": "极高风险",
        }
        return names[self.value]


@dataclass
class RiskResult:
    """Risk assessment result."""

    score: float
    level: RiskLevel
    reasons: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "score": round(self.score, 2),
            "level": self.level.value,
            "level_display": self.level.display_name,
            "color": self.level.color,
            "reasons": self.reasons,
            "details": self.details,
        }


class RiskScoringEngine:
    """Risk scoring engine for account theft detection.

    Scoring rules:
        - LSTM anomaly probability × 60% (max 60 points)
        - Location anomaly × 20% (max 20 points)
        - Device change + 10 points
        - Time anomaly + 10 points

    Risk levels:
        - 0-30: LOW (green)
        - 31-60: MEDIUM (yellow)
        - 61-80: HIGH (orange)
        - 81-100: CRITICAL (red)
    """

    def __init__(
        self,
        lstm_weight: float = 0.6,
        location_weight: float = 0.2,
        device_weight: float = 10.0,
        time_weight: float = 10.0,
    ) -> None:
        """Initialize risk scoring engine.

        Args:
            lstm_weight: Weight for LSTM model probability (default 0.6)
            location_weight: Weight for location anomaly (default 0.2)
            device_weight: Points added for new device (default 10)
            time_weight: Points added for time anomaly (default 10)
        """
        self.lstm_weight = lstm_weight
        self.location_weight = location_weight
        self.device_weight = device_weight
        self.time_weight = time_weight

    def _calculate_level(self, score: float) -> RiskLevel:
        """Determine risk level from score.

        Args:
            score: Risk score (0-100)

        Returns:
            RiskLevel enum
        """
        if score <= 30:
            return RiskLevel.LOW
        elif score <= 60:
            return RiskLevel.MEDIUM
        elif score <= 80:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL

    def calculate_score(self, features: dict[str, Any]) -> RiskResult:
        """Calculate risk score from extracted features.

        Args:
            features: Dictionary containing:
                - lstm_probability: LSTM model anomaly probability (0-1)
                - location_anomaly: Location anomaly score (0-1)
                - is_new_device: Whether this is a new device (bool)
                - time_anomaly: Time anomaly score (0-1)
                - device_fingerprint: Device fingerprint string
                - baseline_devices: List of historical device fingerprints
                - baseline_locations: List of historical locations
                - baseline_hours: List of historical login hours

        Returns:
            RiskResult with score, level, and reasons
        """
        # Extract features with defaults
        lstm_prob = float(features.get("lstm_probability", 0.0))
        lstm_prob = max(0.0, min(1.0, lstm_prob))  # Clamp to 0-1

        location_anomaly = float(features.get("location_anomaly", 0.0))
        location_anomaly = max(0.0, min(1.0, location_anomaly))

        is_new_device = bool(features.get("is_new_device", False))

        time_anomaly = float(features.get("time_anomaly", 0.0))
        time_anomaly = max(0.0, min(1.0, time_anomaly))

        # Calculate component scores
        lstm_score = lstm_prob * 100 * self.lstm_weight  # Max 60 points
        location_score = location_anomaly * 100 * self.location_weight  # Max 20 points
        device_score = self.device_weight if is_new_device else 0.0
        time_score = self.time_weight if time_anomaly > 0.5 else 0.0

        # Calculate total score
        total_score = lstm_score + location_score + device_score + time_score

        # Clamp to 0-100
        total_score = max(0.0, min(100.0, total_score))

        # Determine risk level
        level = self._calculate_level(total_score)

        # Build reasons list
        reasons: list[str] = []

        # LSTM analysis
        if lstm_prob > 0.7:
            reasons.append(f"LSTM模型检测到高度异常行为 (概率: {lstm_prob:.2f})")
        elif lstm_prob > 0.4:
            reasons.append(f"LSTM模型检测到中度异常 (概率: {lstm_prob:.2f})")

        # Location analysis
        if location_anomaly > 0.7:
            reasons.append(f"地理位置异常: 与常用登录地距离过远")
        elif location_anomaly > 0.4:
            reasons.append(f"地理位置偏离历史记录")

        # Device analysis
        if is_new_device:
            reasons.append("检测到新设备登录")

        # Time analysis
        if time_anomaly > 0.7:
            reasons.append("登录时间异常: 非常用时段")
        elif time_anomaly > 0.4:
            reasons.append("登录时间偏离日常习惯")

        # Build details
        details = {
            "components": {
                "lstm_score": round(lstm_score, 2),
                "location_score": round(location_score, 2),
                "device_score": round(device_score, 2),
                "time_score": round(time_score, 2),
            },
            "weights": {
                "lstm": self.lstm_weight,
                "location": self.location_weight,
                "device": self.device_weight,
                "time": self.time_weight,
            },
            "raw_features": {
                "lstm_probability": round(lstm_prob, 4),
                "location_anomaly": round(location_anomaly, 4),
                "is_new_device": is_new_device,
                "time_anomaly": round(time_anomaly, 4),
            },
        }

        return RiskResult(
            score=total_score,
            level=level,
            reasons=reasons,
            details=details,
        )

    def calculate_from_user_baseline(
        self,
        event_features: np.ndarray,
        lstm_model_output: float,
        current_device: str,
        historical_devices: list[str],
        current_location: tuple[float, float] | None,
        historical_locations: list[tuple[float, float]],
        current_hour: float,
        historical_hours: list[float],
    ) -> RiskResult:
        """Calculate risk score from user baseline data.

        This method takes raw user baseline information and computes all features internally.

        Args:
            event_features: Raw event features (109-dim)
            lstm_model_output: LSTM model probability output (0-1)
            current_device: Current device fingerprint
            historical_devices: Historical device fingerprints
            historical_locations: Historical login locations [(lat, lon), ...]
            current_hour: Current login hour (0-23)
            historical_hours: Historical login hours

        Returns:
            RiskResult with calculated score
        """
        import math

        # Calculate location anomaly
        location_anomaly = 0.0
        if current_location and historical_locations:
            from app.ml.feature_extractor import LocationAnomalyCalculator

            calc = LocationAnomalyCalculator()
            distances = [
                calc.haversine_distance(
                    current_location[0], current_location[1], lat, lon
                )
                for lat, lon in historical_locations
            ]
            min_dist = min(distances) if distances else 0
            # Normalize: >1000km = 1.0, <10km = 0.0
            location_anomaly = min(min(1000, min_dist) / 1000, 1.0)

        # Check device change
        is_new_device = current_device not in historical_devices

        # Calculate time anomaly
        time_anomaly = 0.0
        if historical_hours:
            from app.ml.feature_extractor import TimeAnomalyCalculator

            calc = TimeAnomalyCalculator()
            time_anomaly = calc.calculate_time_deviation(current_hour, historical_hours)

        # Build features dict
        features = {
            "lstm_probability": lstm_model_output,
            "location_anomaly": location_anomaly,
            "is_new_device": is_new_device,
            "time_anomaly": time_anomaly,
        }

        return self.calculate_score(features)

    def get_threshold_config(self) -> dict[str, Any]:
        """Get the threshold configuration for risk levels.

        Returns:
            Dictionary with threshold configuration
        """
        return {
            "levels": {
                "low": {"min": 0, "max": 30, "color": "green"},
                "medium": {"min": 31, "max": 60, "color": "yellow"},
                "high": {"min": 61, "max": 80, "color": "orange"},
                "critical": {"min": 81, "max": 100, "color": "red"},
            },
            "weights": {
                "lstm": self.lstm_weight,
                "location": self.location_weight,
                "device": self.device_weight,
                "time": self.time_weight,
            },
        }


def create_scoring_engine(
    lstm_weight: float = 0.6,
    location_weight: float = 0.2,
    device_weight: float = 10.0,
    time_weight: float = 10.0,
) -> RiskScoringEngine:
    """Create a risk scoring engine instance.

    Args:
        lstm_weight: Weight for LSTM model (default 0.6)
        location_weight: Weight for location anomaly (default 0.2)
        device_weight: Points for new device (default 10)
        time_weight: Points for time anomaly (default 10)

    Returns:
        RiskScoringEngine instance
    """
    return RiskScoringEngine(
        lstm_weight=lstm_weight,
        location_weight=location_weight,
        device_weight=device_weight,
        time_weight=time_weight,
    )


# Example usage and testing
if __name__ == "__main__":
    print("Testing RiskScoringEngine...")

    # Create scoring engine
    engine = create_scoring_engine()

    # Test case 1: Low risk - normal login
    print("\n--- Test 1: Normal Login (Expected: Low Risk) ---")
    features1 = {
        "lstm_probability": 0.1,
        "location_anomaly": 0.1,
        "is_new_device": False,
        "time_anomaly": 0.2,
    }
    result1 = engine.calculate_score(features1)
    print(f"Score: {result1.score:.2f}")
    print(f"Level: {result1.level.display_name} ({result1.level.color})")
    print(f"Reasons: {result1.reasons}")

    # Test case 2: Medium risk - suspicious login
    print("\n--- Test 2: Suspicious Login (Expected: Medium Risk) ---")
    features2 = {
        "lstm_probability": 0.5,
        "location_anomaly": 0.4,
        "is_new_device": True,
        "time_anomaly": 0.3,
    }
    result2 = engine.calculate_score(features2)
    print(f"Score: {result2.score:.2f}")
    print(f"Level: {result2.level.display_name} ({result2.level.color})")
    print(f"Reasons: {result2.reasons}")
    print(f"Details: {result2.details['components']}")

    # Test case 3: High risk - account theft attempt
    print("\n--- Test 3: Account Theft Attempt (Expected: Critical Risk) ---")
    features3 = {
        "lstm_probability": 0.95,
        "location_anomaly": 0.9,
        "is_new_device": True,
        "time_anomaly": 0.8,
    }
    result3 = engine.calculate_score(features3)
    print(f"Score: {result3.score:.2f}")
    print(f"Level: {result3.level.display_name} ({result3.level.color})")
    print(f"Reasons: {result3.reasons}")
    print(f"Details: {result3.details['components']}")

    # Test case 4: Test from user baseline
    print("\n--- Test 4: From User Baseline ---")
    result4 = engine.calculate_from_user_baseline(
        event_features=np.zeros(109),
        lstm_model_output=0.3,
        current_device="device_001",
        historical_devices=["device_001", "device_002"],
        current_location=(39.9, 116.4),
        historical_locations=[(39.9, 116.4), (40.0, 116.5)],
        current_hour=14.0,
        historical_hours=[9.0, 10.0, 18.0, 19.0],
    )
    print(f"Score: {result4.score:.2f}")
    print(f"Level: {result4.level.display_name}")

    # Print threshold config
    print("\n--- Threshold Configuration ---")
    config = engine.get_threshold_config()
    print(config)

    print("\nAll tests passed!")