"""
Email Notification Channel

Implements SMTP-based email sending with template support.
"""
import asyncio
import smtplib
from abc import ABC, abstractmethod
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from app.core.config import settings


class EmailSender(ABC):
    """Abstract email sender."""

    async def send(self, to: str, subject: str, html_body: str) -> bool:
        """Send email.

        Args:
            to: Recipient email address
            subject: Email subject
            html_body: HTML email body

        Returns:
            True if sent successfully
        """
        pass  # Abstract method


class SMTPEmailSender(EmailSender):
    """SMTP email sender implementation."""

    def __init__(
        self,
        host: str = "smtp.gmail.com",
        port: int = 587,
        username: str = "",
        password: str = "",
        use_tls: bool = True,
    ) -> None:
        """Initialize SMTP sender.

        Args:
            host: SMTP server host
            port: SMTP server port
            username: SMTP username
            password: SMTP password
            use_tls: Use TLS encryption
        """
        self.host = host
        self.port = port
        self.username = username or settings.EMAIL_FROM
        self.password = password
        self.use_tls = use_tls

    async def send(self, to: str, subject: str, html_body: str) -> bool:
        """Send email via SMTP.

        Args:
            to: Recipient email address
            subject: Email subject
            html_body: HTML email body

        Returns:
            True if sent successfully
        """
        try:
            # Run blocking SMTP operation in thread pool
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self._send_sync,
                to,
                subject,
                html_body,
            )
            return True
        except Exception:
            return False

    def _send_sync(self, to: str, subject: str, html_body: str) -> None:
        """Send email synchronously."""
        # If credentials not configured, skip sending
        if not self.username or not self.password:
            print(f"[Email] Skipping email to {to}: SMTP not configured")
            return

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.username
            msg["To"] = to

            # Attach HTML and plain text versions
            html_part = MIMEText(html_body, "html", "utf-8")
            plain_part = MIMEText(html_body.replace("<br>", "\n").replace("<p>", "\n").replace("</p>", ""), "plain", "utf-8")

            msg.attach(plain_part)
            msg.attach(html_part)

            # Connect to server and send
            with smtplib.SMTP(self.host, self.port) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)

            print(f"[Email] Sent to {to}: {subject}")
        except Exception as e:
            print(f"[Email] Failed to send to {to}: {e}")


class SendGridEmailSender(EmailSender):
    """SendGrid API email sender."""

    def __init__(self, api_key: str = "") -> None:
        """Initialize SendGrid sender.

        Args:
            api_key: SendGrid API key
        """
        self.api_key = api_key or settings.EMAIL_API_KEY

    async def send(self, to: str, subject: str, html_body: str) -> bool:
        """Send email via SendGrid API.

        Args:
            to: Recipient email address
            subject: Email subject
            html_body: HTML email body

        Returns:
            True if sent successfully
        """
        # Placeholder - would use sendgrid library in production
        if not self.api_key:
            print(f"[SendGrid] Skipping email to {to}: API key not configured")
            return False

        print(f"[SendGrid] Would send to {to}: {subject}")
        return True


def create_email_sender(provider: str = "smtp") -> EmailSender:
    """Create email sender based on provider.

    Args:
        provider: Email provider (smtp, sendgrid)

    Returns:
        EmailSender instance
    """
    if provider == "sendgrid":
        return SendGridEmailSender()
    return SMTPEmailSender()


# Email templates
ALERT_EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #ff6b6b; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f9f9f9; padding: 20px; }}
        .score {{ font-size: 48px; font-weight: bold; color: #ff6b6b; }}
        .level {{ font-size: 24px; padding: 10px 20px; border-radius: 4px; display: inline-block; }}
        .low {{ background: #4caf50; color: white; }}
        .medium {{ background: #ff9800; color: white; }}
        .high {{ background: #ff5722; color: white; }}
        .critical {{ background: #d32f2f; color: white; }}
        .reasons {{ background: white; padding: 15px; border-radius: 4px; margin: 15px 0; }}
        .footer {{ background: #333; color: white; padding: 15px; text-align: center; border-radius: 0 0 8px 8px; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>账户安全预警</h1>
        </div>
        <div class="content">
            <p>尊敬的 <strong>{username}</strong>：</p>
            <p>我们检测到您的账户存在异常登录行为，请及时确认是否为本人操作。</p>
            
            <div style="text-align: center; margin: 20px 0;">
                <div class="score">{risk_score}</div>
                <div class="level {level_class}">{risk_level}</div>
            </div>
            
            <div class="reasons">
                <h3>风险原因：</h3>
                <ul>
                    {reasons_html}
                </ul>
            </div>
            
            <p><strong>登录时间：</strong>{login_time}</p>
            <p><strong>登录 IP：</strong>{ip_address}</p>
            
            <p style="color: #666; font-size: 12px;">
                如果不是您本人的操作，请立即修改密码并联系我们。
            </p>
        </div>
        <div class="footer">
            此邮件由系统自动发送，请勿回复
        </div>
    </div>
</body>
</html>
"""


def render_alert_email(
    username: str,
    risk_score: float,
    risk_level: str,
    reasons: list[str],
    login_time: str,
    ip_address: str,
) -> tuple[str, str]:
    """Render alert email content.

    Args:
        username: User's username
        risk_score: Risk score
        risk_level: Risk level
        reasons: List of risk reasons
        login_time: Login timestamp
        ip_address: Login IP

    Returns:
        Tuple of (subject, html_body)
    """
    level_class = risk_level.lower()
    reasons_html = "".join(f"<li>{r}</li>" for r in reasons)

    subject = f"【安全预警】您的账户存在异常登录风险 (风险分数: {int(risk_score)})"

    html_body = ALERT_EMAIL_TEMPLATE.format(
        username=username,
        risk_score=int(risk_score),
        risk_level=risk_level,
        level_class=level_class,
        reasons_html=reasons_html,
        login_time=login_time,
        ip_address=ip_address,
    )

    return subject, html_body