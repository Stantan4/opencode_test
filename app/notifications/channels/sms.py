"""
SMS Notification Channel

Implements SMS sending with support for multiple providers (Aliyun, Tencent).
Placeholder implementation for demonstration.
"""
from abc import ABC, abstractmethod
from typing import Any

from app.core.config import settings


class SMSSender(ABC):
    """Abstract SMS sender."""

    @abstractmethod
    async def send(self, phone: str, template_id: str, params: dict[str, Any]) -> bool:
        """Send SMS.

        Args:
            phone: Recipient phone number
            template_id: SMS template ID
            params: Template parameters

        Returns:
            True if sent successfully
        """
        pass  # Abstract method


class AliyunSMSSender(SMSSender):
    """Aliyun SMS sender."""

    def __init__(
        self,
        access_key: str = "",
        secret_key: str = "",
        sign_name: str = "",
    ) -> None:
        """Initialize Aliyun SMS sender.

        Args:
            access_key: Aliyun access key
            secret_key: Aliyun secret key
            sign_name: SMS sign name
        """
        self.access_key = access_key or settings.SMS_ACCESS_KEY
        self.secret_key = secret_key or settings.SMS_SECRET_KEY
        self.sign_name = sign_name or settings.SMS_SIGN_NAME

    async def send(self, phone: str, template_id: str, params: dict[str, Any]) -> bool:
        """Send SMS via Aliyun.

        Args:
            phone: Recipient phone number
            template_id: SMS template ID
            params: Template parameters

        Returns:
            True if sent successfully
        """
        # Placeholder - would use aliyun-sdk-core library in production
        if not self.access_key or not self.secret_key:
            print(f"[Aliyun SMS] Skipping SMS to {phone}: Credentials not configured")
            return False

        print(f"[Aliyun SMS] Would send to {phone}: template={template_id}, params={params}")
        return True


class TencentSMSSender(SMSSender):
    """Tencent SMS sender."""

    def __init__(
        self,
        app_id: str = "",
        app_key: str = "",
        sign_name: str = "",
    ) -> None:
        """Initialize Tencent SMS sender.

        Args:
            app_id: Tencent SMS app ID
            app_key: Tencent SMS app key
            sign_name: SMS sign name
        """
        self.app_id = app_id
        self.app_key = app_key
        self.sign_name = sign_name

    async def send(self, phone: str, template_id: str, params: dict[str, Any]) -> bool:
        """Send SMS via Tencent.

        Args:
            phone: Recipient phone number
            template_id: SMS template ID
            params: Template parameters

        Returns:
            True if sent successfully
        """
        # Placeholder - would use tencentcloud-sdk library in production
        if not self.app_id or not self.app_key:
            print(f"[Tencent SMS] Skipping SMS to {phone}: Credentials not configured")
            return False

        print(f"[Tencent SMS] Would send to {phone}: template={template_id}, params={params}")
        return True


def create_sms_sender(provider: str = "aliyun") -> SMSSender:
    """Create SMS sender based on provider.

    Args:
        provider: SMS provider (aliyun, tencent)

    Returns:
        SMSSender instance
    """
    if provider == "tencent":
        return TencentSMSSender()
    return AliyunSMSSender()


# SMS templates
ALERT_SMS_TEMPLATES = {
    "high_risk": "SMS_ALERT_HIGH_RISK",
    "medium_risk": "SMS_ALERT_MEDIUM_RISK",
    "low_risk": "SMS_ALERT_LOW_RISK",
}


def get_alert_template(risk_level: str) -> str:
    """Get SMS template ID for risk level.

    Args:
        risk_level: Risk level (low, medium, high, critical)

    Returns:
        SMS template ID
    """
    return ALERT_SMS_TEMPLATES.get(risk_level, ALERT_SMS_TEMPLATES["low_risk"])


def format_alert_sms_params(
    username: str,
    risk_score: float,
    risk_level: str,
    ip_address: str,
) -> dict[str, str]:
    """Format SMS template parameters.

    Args:
        username: User's username
        risk_score: Risk score
        risk_level: Risk level
        ip_address: Login IP

    Returns:
        Template parameters dictionary
    """
    return {
        "username": username,
        "score": str(int(risk_score)),
        "level": risk_level,
        "ip": ip_address,
    }