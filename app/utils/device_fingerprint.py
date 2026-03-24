"""
Device Fingerprint Utility
"""
import hashlib
from typing import Optional


class DeviceFingerprint:
    """Device fingerprint generator"""

    @staticmethod
    def generate(
        user_agent: str,
        screen_resolution: str,
        timezone: str,
        language: str,
        canvas_hash: Optional[str] = None,
        webgl_hash: Optional[str] = None
    ) -> str:
        """Generate device fingerprint"""
        # Implementation to be added
        pass

    @staticmethod
    def hash_components(components: dict) -> str:
        """Hash device components"""
        component_str = "|".join(f"{k}:{v}" for k, v in sorted(components.items()))
        return hashlib.sha256(component_str.encode()).hexdigest()
