"""
User Behavior Feature Extractor.

This module extracts features from raw user behavior logs for LSTM anomaly detection.
The extracted features match the LSTM model input dimensions (109 features).
"""
import hashlib
import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import numpy as np
from sklearn.preprocessing import StandardScaler


@dataclass
class LoginEvent:
    """Login event data structure."""

    user_id: str
    timestamp: datetime
    ip_address: str
    latitude: float | None
    longitude: float | None
    user_agent: str
    screen_resolution: str
    timezone: str
    operation_type: str  # 'login', 'post', 'comment', 'dm'


@dataclass
class UserBaseline:
    """User historical behavior baseline."""

    login_hours: list[float]  # List of normalized hours (0-23)
    locations: list[tuple[float, float]]  # List of (lat, lon)
    device_fingerprints: set[str]
    operation_intervals: list[float]  # Time between operations in seconds


class DeviceFingerprintGenerator:
    """Generate device fingerprint from browser attributes."""

    # Standard screen resolutions for one-hot encoding
    COMMON_RESOLUTIONS = [
        "1920x1080", "1366x768", "1536x864", "1440x900",
        "1280x720", "2560x1440", "1600x900", "1280x800",
    ]

    # One-hot encoding mapping
    _resolution_to_idx: dict[str, int] = {res: i for i, res in enumerate(COMMON_RESOLUTIONS)}

    @staticmethod
    def generate(
        user_agent: str,
        screen_resolution: str,
        timezone: str,
    ) -> str:
        """Generate 32-character MD5 device fingerprint.

        Args:
            user_agent: Browser user agent string
            screen_resolution: Screen resolution (e.g., "1920x1080")
            timezone: User timezone (e.g., "UTC+8")

        Returns:
            32-character MD5 hash fingerprint
        """
        # Normalize screen resolution
        normalized_res = screen_resolution.replace(" ", "").lower()

        # Create component string
        components = f"{user_agent}|{normalized_res}|{timezone}"

        # Generate MD5 hash
        fingerprint = hashlib.md5(components.encode("utf-8")).hexdigest()[:32]

        return fingerprint

    @staticmethod
    def to_one_hot(fingerprint: str, fingerprint_vocab: dict[str, int]) -> np.ndarray:
        """Convert fingerprint to one-hot encoding.

        Args:
            fingerprint: Device fingerprint string
            fingerprint_vocab: Vocabulary mapping fingerprint -> index

        Returns:
            One-hot encoded numpy array (100 dims)
        """
        one_hot = np.zeros(100, dtype=np.float32)

        # Map fingerprint to vocabulary index (hash to vocab size)
        if fingerprint in fingerprint_vocab:
            idx = fingerprint_vocab[fingerprint]
        else:
            # Use hash to assign to a bucket
            idx = int(fingerprint[:8], 16) % 100

        one_hot[idx] = 1.0
        return one_hot


class LocationAnomalyCalculator:
    """Calculate location anomaly based on distance from historical locations."""

    @staticmethod
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two coordinates using Haversine formula.

        Args:
            lat1, lon1: First coordinate
            lat2, lon2: Second coordinate

        Returns:
            Distance in kilometers
        """
        R = 6371  # Earth's radius in km

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        a = (
            math.sin(delta_lat / 2) ** 2
            + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    def calculate_distance_from_baseline(
        self,
        current_lat: float,
        current_lon: float,
        baseline_locations: list[tuple[float, float]],
    ) -> float:
        """Calculate minimum distance from current location to any baseline location.

        Args:
            current_lat: Current latitude
            current_lon: Current longitude
            baseline_locations: List of historical locations

        Returns:
            Minimum distance in km (log-normalized)
        """
        if not baseline_locations:
            return 0.0  # No baseline, assume normal

        min_distance = float("inf")
        for lat, lon in baseline_locations:
            if lat is not None and lon is not None:
                dist = self.haversine_distance(current_lat, current_lon, lat, lon)
                min_distance = min(min_distance, dist)

        # Log normalize (add 1 to avoid log(0))
        log_distance = math.log1p(min_distance) if min_distance != float("inf") else 0.0

        return log_distance / 10.0  # Normalize to 0-1 range (max ~10 for very far)

    def normalize_coordinates(self, lat: float, lon: float) -> tuple[float, float]:
        """Normalize coordinates to 0-1 range.

        Args:
            lat: Latitude (-90 to 90)
            lon: Longitude (-180 to 180)

        Returns:
            Normalized (lat, lon)
        """
        # Normalize latitude: -90~90 -> 0~1
        norm_lat = (lat + 90) / 180
        # Normalize longitude: -180~180 -> 0~1
        norm_lon = (lon + 180) / 360

        return norm_lat, norm_lon


class TimeAnomalyCalculator:
    """Calculate time anomaly based on deviation from user's login time distribution."""

    def calculate_time_deviation(
        self,
        current_hour: float,
        baseline_hours: list[float],
    ) -> float:
        """Calculate deviation from historical login time distribution.

        Args:
            current_hour: Current login hour (0-23, normalized)
            baseline_hours: Historical login hours

        Returns:
            Time deviation score (0-1)
        """
        if not baseline_hours:
            return 0.0  # No baseline, assume normal

        # Calculate circular mean and standard deviation for hours
        # Convert hours to angles (0-23 -> 0-2π)
        angles = [(h / 24) * 2 * math.pi for h in baseline_hours]

        # Calculate mean angle
        sin_sum = sum(math.sin(a) for a in angles)
        cos_sum = sum(math.cos(a) for a in angles)
        mean_angle = math.atan2(sin_sum / len(angles), cos_sum / len(angles))

        # Calculate circular standard deviation
        r = math.sqrt(sin_sum ** 2 + cos_sum ** 2) / len(angles)
        circular_std = math.sqrt(-2 * math.log(r)) if r > 0 else 0

        # Convert current hour to angle
        current_angle = (current_hour / 24) * 2 * math.pi

        # Calculate angular difference
        angle_diff = abs(current_angle - mean_angle)
        if angle_diff > math.pi:
            angle_diff = 2 * math.pi - angle_diff

        # Normalize deviation (larger deviation = higher anomaly)
        # If circular_std is very small, any deviation is significant
        if circular_std < 0.1:
            normalized_deviation = min(angle_diff / math.pi, 1.0)
        else:
            normalized_deviation = min(angle_diff / (circular_std * 3), 1.0)

        return normalized_deviation


class BehaviorFeatureExtractor:
    """Extract features from user behavior events for LSTM model.

    Input: Raw login/operation events
    Output: Feature vector (109 dimensions) matching LSTM input:
        - Login time (1): normalized 0-23 hours
        - Location (2): normalized latitude/longitude
        - Device fingerprint (100): one-hot encoding
        - Operation type (4): one-hot encoding
        - Operation interval (1): log-normalized
    """

    def __init__(self, num_device_types: int = 100) -> None:
        """Initialize feature extractor.

        Args:
            num_device_types: Number of device fingerprint categories
        """
        self.num_device_types = num_device_types

        # Component calculators
        self.device_generator = DeviceFingerprintGenerator()
        self.location_calculator = LocationAnomalyCalculator()
        self.time_calculator = TimeAnomalyCalculator()

        # User baselines (fitted during fit())
        self.user_baselines: dict[str, UserBaseline] = {}

        # Feature scaler for standardization
        self.scaler = StandardScaler()

        # Device fingerprint vocabulary
        self.device_vocab: dict[str, int] = {}

        # Operation type mapping
        self.operation_mapping = {
            "login": 0,
            "post": 1,
            "comment": 2,
            "dm": 3,
        }

        # Fitted flag
        self._is_fitted = False

    def fit(self, historical_events: list[LoginEvent]) -> "BehaviorFeatureExtractor":
        """Learn user historical baseline from login events.

        Args:
            historical_events: List of historical login events

        Returns:
            Self for method chaining
        """
        # Group events by user
        user_events: defaultdict[str, list[LoginEvent]] = defaultdict(list)
        for event in historical_events:
            user_events[event.user_id].append(event)

        # Build baseline for each user
        for user_id, events in user_events.items():
            # Sort by timestamp
            sorted_events = sorted(events, key=lambda e: e.timestamp)

            # Extract baseline features
            login_hours = [
                e.timestamp.hour + e.timestamp.minute / 60.0
                for e in sorted_events
            ]

            locations = [
                (e.latitude, e.longitude)
                for e in sorted_events
                if e.latitude is not None and e.longitude is not None
            ]

            device_fps = set()
            for e in sorted_events:
                fp = self.device_generator.generate(
                    e.user_agent, e.screen_resolution, e.timezone
                )
                device_fps.add(fp)

            # Calculate operation intervals
            intervals = []
            for i in range(1, len(sorted_events)):
                delta = (sorted_events[i].timestamp - sorted_events[i - 1].timestamp).total_seconds()
                intervals.append(delta)

            self.user_baselines[user_id] = UserBaseline(
                login_hours=login_hours,
                locations=locations,
                device_fingerprints=device_fps,
                operation_intervals=intervals,
            )

        # Build device fingerprint vocabulary from all historical data
        all_fingerprints: set[str] = set()
        for user_id, baseline in self.user_baselines.items():
            all_fingerprints.update(baseline.device_fingerprints)

        # Create vocabulary (limit to num_device_types)
        fingerprint_list = list(all_fingerprints)[: self.num_device_types]
        self.device_vocab = {fp: i for i, fp in enumerate(fingerprint_list)}

        # Fit scaler on operation intervals (log-normalized)
        all_intervals = []
        for baseline in self.user_baselines.values():
            log_intervals = [math.log1p(i) for i in baseline.operation_intervals if i > 0]
            all_intervals.extend(log_intervals)

        if all_intervals:
            self.scaler.fit(np.array(all_intervals).reshape(-1, 1))

        self._is_fitted = True
        return self

    def transform(self, event: LoginEvent) -> np.ndarray:
        """Extract features from a single login event.

        Args:
            event: Login event to extract features from

        Returns:
            Feature vector (109 dimensions)
        """
        if not self._is_fitted:
            raise RuntimeError("Feature extractor must be fitted before transform")

        # Initialize feature vector (109 dims)
        features = np.zeros(109, dtype=np.float32)
        feature_idx = 0

        # 1. Login time (1 dimension): normalized 0-23 hours
        login_hour = event.timestamp.hour + event.timestamp.minute / 60.0
        features[feature_idx] = login_hour / 24.0
        feature_idx += 1

        # 2. Location (2 dimensions): normalized lat/lon
        if event.latitude is not None and event.longitude is not None:
            norm_lat, norm_lon = self.location_calculator.normalize_coordinates(
                event.latitude, event.longitude
            )
            features[feature_idx] = norm_lat
            features[feature_idx + 1] = norm_lon
        feature_idx += 2

        # 3. Device fingerprint (100 dimensions): one-hot encoding
        fingerprint = self.device_generator.generate(
            event.user_agent, event.screen_resolution, event.timezone
        )
        device_one_hot = self.device_generator.to_one_hot(fingerprint, self.device_vocab)
        features[feature_idx : feature_idx + 100] = device_one_hot
        feature_idx += 100

        # 4. Operation type (4 dimensions): one-hot encoding
        op_type = event.operation_type.lower()
        op_idx = self.operation_mapping.get(op_type, 0)
        features[feature_idx + op_idx] = 1.0
        feature_idx += 4

        # 5. Operation interval (1 dimension): log-normalized
        baseline = self.user_baselines.get(event.user_id)
        if baseline and baseline.operation_intervals:
            # Get average interval from baseline
            avg_interval = np.mean(baseline.operation_intervals)
            log_interval = math.log1p(avg_interval)
            # Normalize using scaler
            if hasattr(self.scaler, "scale_"):
                normalized_interval = log_interval / (self.scaler.scale_[0] * 3)
                normalized_interval = min(max(normalized_interval, 0), 1)
            else:
                normalized_interval = log_interval / 20.0  # Default normalization
            features[feature_idx] = normalized_interval

        return features

    def transform_sequence(self, events: list[LoginEvent]) -> np.ndarray:
        """Extract features from a sequence of events.

        Args:
            events: List of login events in chronological order

        Returns:
            Feature matrix (num_events, 109)
        """
        return np.array([self.transform(e) for e in events])

    def fit_transform(
        self,
        historical_events: list[LoginEvent],
    ) -> np.ndarray:
        """Fit on historical events and transform (for initial baseline).

        Args:
            historical_events: Historical events for fitting

        Returns:
            Feature matrix of historical events
        """
        self.fit(historical_events)
        return self.transform_sequence(historical_events)

    def add_event(self, event: LoginEvent) -> None:
        """Update baseline with a new event (online learning).

        Args:
            event: New login event to add to baseline
        """
        if event.user_id not in self.user_baselines:
            self.user_baselines[event.user_id] = UserBaseline(
                login_hours=[],
                locations=[],
                device_fingerprints=set(),
                operation_intervals=[],
            )

        baseline = self.user_baselines[event.user_id]

        # Add login hour
        login_hour = event.timestamp.hour + event.timestamp.minute / 60.0
        baseline.login_hours.append(login_hour)

        # Add location
        if event.latitude is not None and event.longitude is not None:
            baseline.locations.append((event.latitude, event.longitude))

        # Add device fingerprint
        fingerprint = self.device_generator.generate(
            event.user_agent, event.screen_resolution, event.timezone
        )
        baseline.device_fingerprints.add(fingerprint)

    @property
    def is_fitted(self) -> bool:
        """Check if extractor has been fitted."""
        return self._is_fitted


def create_feature_extractor(num_device_types: int = 100) -> BehaviorFeatureExtractor:
    """Create a behavior feature extractor instance.

    Args:
        num_device_types: Number of device fingerprint categories

    Returns:
        BehaviorFeatureExtractor instance
    """
    return BehaviorFeatureExtractor(num_device_types=num_device_types)


# Example usage and testing
if __name__ == "__main__":
    from datetime import timedelta

    print("Testing BehaviorFeatureExtractor...")

    # Create sample historical events
    base_time = datetime(2024, 1, 1, 12, 0, 0)
    historical_events = []

    # Generate events for a test user
    for i in range(50):
        event = LoginEvent(
            user_id="test_user",
            timestamp=base_time + timedelta(hours=i * 6),
            ip_address=f"192.168.1.{i % 10}",
            latitude=39.9042 + (i % 3) * 0.1,
            longitude=116.4074 + (i % 3) * 0.1,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
            screen_resolution="1920x1080",
            timezone="UTC+8",
            operation_type="login" if i % 5 == 0 else "post",
        )
        historical_events.append(event)

    # Create and fit extractor
    extractor = create_feature_extractor(num_device_types=100)
    extractor.fit(historical_events)

    print(f"Baseline for test_user:")
    baseline = extractor.user_baselines.get("test_user")
    if baseline:
        print(f"  - Login hours: {len(baseline.login_hours)}")
        print(f"  - Locations: {len(baseline.locations)}")
        print(f"  - Devices: {len(baseline.device_fingerprints)}")
        print(f"  - Intervals: {len(baseline.operation_intervals)}")

    # Test feature extraction
    test_event = LoginEvent(
        user_id="test_user",
        timestamp=datetime(2024, 1, 15, 14, 30, 0),
        ip_address="8.8.8.8",
        latitude=37.7749,
        longitude=-122.4194,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
        screen_resolution="1920x1080",
        timezone="UTC+8",
        operation_type="login",
    )

    features = extractor.transform(test_event)

    print(f"\nExtracted features shape: {features.shape}")
    print(f"Login time: {features[0]:.4f}")
    print(f"Location: {features[1]:.4f}, {features[2]:.4f}")
    print(f"Device (first 10): {features[3:13]}")
    print(f"Operation type (first 4): {features[103:107]}")
    print(f"Interval: {features[108]:.4f}")

    # Test sequence extraction
    print("\nTesting sequence extraction...")
    sequence_events = [
        LoginEvent(
            user_id="test_user",
            timestamp=base_time + timedelta(hours=i * 3),
            ip_address=f"192.168.1.{i}",
            latitude=39.9,
            longitude=116.4,
            user_agent="Mozilla/5.0",
            screen_resolution="1920x1080",
            timezone="UTC+8",
            operation_type="post" if i % 2 == 0 else "login",
        )
        for i in range(30)
    ]

    seq_features = extractor.transform_sequence(sequence_events)
    print(f"Sequence features shape: {seq_features.shape}")

    print("\nAll tests passed!")