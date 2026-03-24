"""
Alert Service

Multi-channel alert service with email, SMS, and in-app push support.
Includes deduplication logic and database recording for high-risk alerts.
"""
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

from app.database.redis import get_redis
from app.notifications.channels.email import (
    EmailSender,
    SMTPEmailSender,
    render_alert_email,
)
from app.notifications.channels.sms import SMSSender, AliyunSMSSender, get_alert_template, format_alert_sms_params


class AlertChannel(str, Enum):
    """Alert channel enumeration."""

    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"


class AlertStatus(str, Enum):
    """Alert status enumeration."""

    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    READ = "read"


@dataclass
class AlertRecord:
    """Alert record for database storage."""

    id: str
    user_id: str
    risk_score: float
    risk_level: str
    channels: list[str]
    status: str
    reasons: list[str] = field(default_factory=list)
    ip_address: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    sent_at: Optional[datetime] = None


@dataclass
class AlertResult:
    """Alert sending result."""

    success: bool
    alert_id: Optional[str] = None
    channels_sent: list[str] = field(default_factory=list)
    channels_failed: list[str] = field(default_factory=list)
    message: str = ""
    is_duplicate: bool = False


class InAppPushChannel:
    """In-app push notification via Redis queue."""

    QUEUE_NAME = "alerts:push:notifications"

    def __init__(self) -> None:
        """Initialize in-app push channel."""
        self._redis = None

    async def _get_redis(self):
        """Get Redis client."""
        if self._redis is None:
            self._redis = get_redis()
        return self._redis

    async def send(self, user_id: str, title: str, message: str, data: dict[str, Any]) -> bool:
        """Send in-app push notification via Redis queue.

        Args:
            user_id: Target user ID
            title: Notification title
            message: Notification message
            data: Additional data

        Returns:
            True if queued successfully
        """
        try:
            redis_client = await self._get_redis()
            if redis_client is None:
                print("[In-App Push] Redis not available, skipping")
                return False

            # Create notification payload
            notification = {
                "user_id": user_id,
                "title": title,
                "message": message,
                "data": data,
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Push to Redis queue
            await redis_client.rpush(self.QUEUE_NAME, json.dumps(notification))
            print(f"[In-App Push] Queued notification for user {user_id}")
            return True
        except Exception as e:
            print(f"[In-App Push] Failed to queue notification: {e}")
            return False


class AlertService:
    """Multi-channel alert service.

    Features:
    - Support email, SMS, and in-app push channels
    - Deduplication: no duplicate alerts for same user within 5 minutes for same level
    - Automatic database recording for high-risk alerts (score > 70)
    """

    # Deduplication key pattern
    DEDUP_KEY_PATTERN = "alert:dedup:{user_id}:{level}"

    # Deduplication TTL (5 minutes)
    DEDUP_TTL_SECONDS = 300

    # Risk threshold for database recording
    RECORD_THRESHOLD = 70

    def __init__(
        self,
        email_sender: Optional[EmailSender] = None,
        sms_sender: Optional[SMSSender] = None,
    ) -> None:
        """Initialize alert service.

        Args:
            email_sender: Email sender instance
            sms_sender: SMS sender instance
        """
        self.email_sender = email_sender or SMTPEmailSender()
        self.sms_sender = sms_sender or AliyunSMSSender()
        self.push_channel = InAppPushChannel()

    async def send_alert(
        self,
        user_id: str,
        username: str,
        email: str,
        phone: Optional[str],
        risk_score: float,
        risk_level: str,
        reasons: list[str],
        ip_address: Optional[str] = None,
        login_time: Optional[datetime] = None,
        channels: list[str] = None,
    ) -> AlertResult:
        """Send alert to user via specified channels.

        Args:
            user_id: User ID
            username: User's username
            email: User's email address
            phone: User's phone number
            risk_score: Risk score (0-100)
            risk_level: Risk level (low, medium, high, critical)
            reasons: List of risk reasons
            ip_address: Login IP address
            login_time: Login timestamp
            channels: List of channels to send (default: ['email', 'push'])

        Returns:
            AlertResult with sending status
        """
        if channels is None:
            channels = [AlertChannel.EMAIL.value, AlertChannel.PUSH.value]

        # Check deduplication
        is_duplicate = await self._check_dedup(user_id, risk_level)
        if is_duplicate:
            return AlertResult(
                success=True,
                message=f"Duplicate alert skipped for user {user_id} (level: {risk_level})",
                is_duplicate=True,
            )

        # Generate alert ID
        alert_id = f"alert_{uuid.uuid4().hex[:12]}"

        # Track results
        channels_sent: list[str] = []
        channels_failed: list[str] = []
        all_success = True

        # Send via each channel
        for channel in channels:
            try:
                if channel == AlertChannel.EMAIL.value:
                    success = await self._send_email(
                        email=email,
                        username=username,
                        risk_score=risk_score,
                        risk_level=risk_level,
                        reasons=reasons,
                        ip_address=ip_address or "unknown",
                        login_time=login_time or datetime.utcnow(),
                    )
                    if success:
                        channels_sent.append(AlertChannel.EMAIL.value)
                    else:
                        channels_failed.append(AlertChannel.EMAIL.value)
                        all_success = False

                elif channel == AlertChannel.SMS.value and phone:
                    success = await self._send_sms(
                        phone=phone,
                        username=username,
                        risk_score=risk_score,
                        risk_level=risk_level,
                        ip_address=ip_address or "unknown",
                    )
                    if success:
                        channels_sent.append(AlertChannel.SMS.value)
                    else:
                        channels_failed.append(AlertChannel.SMS.value)
                        all_success = False

                elif channel == AlertChannel.PUSH.value:
                    success = await self._send_push(
                        user_id=user_id,
                        risk_score=risk_score,
                        risk_level=risk_level,
                        reasons=reasons,
                        ip_address=ip_address,
                    )
                    if success:
                        channels_sent.append(AlertChannel.PUSH.value)
                    else:
                        channels_failed.append(AlertChannel.PUSH.value)
                        all_success = False

            except Exception as e:
                print(f"[AlertService] Failed to send via {channel}: {e}")
                channels_failed.append(channel)
                all_success = False

        # Record to database if risk > threshold
        if risk_score > self.RECORD_THRESHOLD:
            await self._record_alert(
                alert_id=alert_id,
                user_id=user_id,
                risk_score=risk_score,
                risk_level=risk_level,
                channels=channels_sent,
                reasons=reasons,
                ip_address=ip_address,
            )

        # Set deduplication key
        await self._set_dedup(user_id, risk_level)

        return AlertResult(
            success=all_success,
            alert_id=alert_id if channels_sent else None,
            channels_sent=channels_sent,
            channels_failed=channels_failed,
            message=f"Alert sent via {', '.join(channels_sent)}" if channels_sent else "No alerts sent",
        )

    async def _send_email(
        self,
        email: str,
        username: str,
        risk_score: float,
        risk_level: str,
        reasons: list[str],
        ip_address: str,
        login_time: datetime,
    ) -> bool:
        """Send email alert."""
        subject, html_body = render_alert_email(
            username=username,
            risk_score=risk_score,
            risk_level=risk_level,
            reasons=reasons,
            login_time=login_time.strftime("%Y-%m-%d %H:%M:%S"),
            ip_address=ip_address,
        )
        return await self.email_sender.send(email, subject, html_body)

    async def _send_sms(
        self,
        phone: str,
        username: str,
        risk_score: float,
        risk_level: str,
        ip_address: str,
    ) -> bool:
        """Send SMS alert."""
        template_id = get_alert_template(risk_level)
        params = format_alert_sms_params(username, risk_score, risk_level, ip_address)
        return await self.sms_sender.send(phone, template_id, params)

    async def _send_push(
        self,
        user_id: str,
        risk_score: float,
        risk_level: str,
        reasons: list[str],
        ip_address: Optional[str],
    ) -> bool:
        """Send in-app push notification."""
        title = "账户安全预警"
        message = f"检测到异常登录风险 (分数: {int(risk_score)}, 级别: {risk_level})"

        data = {
            "alert_id": "",
            "risk_score": risk_score,
            "risk_level": risk_level,
            "reasons": reasons,
            "ip_address": ip_address,
        }

        return await self.push_channel.send(user_id, title, message, data)

    async def _check_dedup(self, user_id: str, risk_level: str) -> bool:
        """Check if alert should be deduplicated.

        Args:
            user_id: User ID
            risk_level: Risk level

        Returns:
            True if duplicate (should skip)
        """
        try:
            redis_client = get_redis()
            if redis_client is None:
                return False

            key = self.DEDUP_KEY_PATTERN.format(user_id=user_id, level=risk_level)
            exists = await redis_client.exists(key)
            return exists > 0
        except Exception:
            return False

    async def _set_dedup(self, user_id: str, risk_level: str) -> None:
        """Set deduplication key.

        Args:
            user_id: User ID
            risk_level: Risk level
        """
        try:
            redis_client = get_redis()
            if redis_client is None:
                return

            key = self.DEDUP_KEY_PATTERN.format(user_id=user_id, level=risk_level)
            await redis_client.setex(key, self.DEDUP_TTL_SECONDS, "1")
        except Exception as e:
            print(f"[AlertService] Failed to set dedup key: {e}")

    async def _record_alert(
        self,
        alert_id: str,
        user_id: str,
        risk_score: float,
        risk_level: str,
        channels: list[str],
        reasons: list[str],
        ip_address: Optional[str],
    ) -> None:
        """Record alert to database.

        Args:
            alert_id: Alert ID
            user_id: User ID
            risk_score: Risk score
            risk_level: Risk level
            channels: List of channels sent
            reasons: List of risk reasons
            ip_address: Login IP
        """
        # Placeholder - would insert into PostgreSQL in production
        print(f"[AlertService] Recording alert {alert_id}: user={user_id}, score={risk_score}, level={risk_level}")

    async def get_alerts(
        self,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Get alerts with filters.

        Args:
            user_id: Filter by user ID
            status: Filter by status
            start_time: Filter by start time
            end_time: Filter by end time
            page: Page number
            page_size: Page size

        Returns:
            Dictionary with alerts and pagination info
        """
        # Placeholder - would query from database in production
        return {
            "total": 0,
            "page": page,
            "page_size": page_size,
            "items": [],
        }

    async def get_alert_detail(self, alert_id: str) -> dict[str, Any]:
        """Get alert detail.

        Args:
            alert_id: Alert ID

        Returns:
            Alert detail dictionary
        """
        # Placeholder - would query from database in production
        return {}

    async def handle_alert(
        self,
        alert_id: str,
        action: str,
        comment: Optional[str] = None,
        notify_user: bool = True,
    ) -> dict[str, Any]:
        """Handle alert (require verification or ignore).

        Args:
            alert_id: Alert ID
            action: Action (verify, ignore, block)
            comment: Optional comment
            notify_user: Whether to notify user

        Returns:
            Result dictionary
        """
        # Placeholder - would update database in production
        return {
            "success": True,
            "alert_id": alert_id,
            "action": action,
        }


def create_alert_service() -> AlertService:
    """Create alert service instance.

    Returns:
        AlertService instance
    """
    return AlertService()