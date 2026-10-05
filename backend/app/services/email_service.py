import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings

logger = logging.getLogger("legalconnect.email")


class EmailService:
    """Sends transactional emails via SMTP or Resend. Falls back gracefully when unconfigured."""

    async def send_password_reset(self, to: str, token: str) -> None:
        reset_url = f"{settings.frontend_url}/reset-password?token={token}"
        subject = "Reset your Legal Connect password"
        body = (
            f"Hello,\n\nWe received a request to reset your Legal Connect password.\n\n"
            f"Click the link below to set a new password (valid for 30 minutes):\n{reset_url}\n\n"
            f"If you did not request this, you can safely ignore this email.\n\n"
            f"Regards,\nLegal Connect Team"
        )
        await self._send(to, subject, body)

    async def send_verification(self, to: str, token: str) -> None:
        verify_url = f"{settings.frontend_url}/verify-email?token={token}"
        subject = "Verify your Legal Connect email"
        body = (
            f"Hello,\n\nWelcome to Legal Connect! Please verify your email address "
            f"by clicking the link below (valid for 24 hours):\n{verify_url}\n\n"
            f"Regards,\nLegal Connect Team"
        )
        await self._send(to, subject, body)

    async def _send(self, to: str, subject: str, body: str) -> None:
        if (settings.smtp_host and settings.smtp_from_email) or settings.resend_api_key:
            try:
                if settings.resend_api_key:
                    self._send_resend(to, subject, body)
                else:
                    self._send_smtp(to, subject, body)
                return
            except Exception as exc:  # noqa: BLE001
                logger.warning("Email sending failed: %s", exc)
                return
        logger.warning(
            "Email not configured for %s. Subject='%s' Body: %s", to, subject, body
        )

    def _send_smtp(self, to: str, subject: str, body: str) -> None:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.smtp_from_email
        msg["To"] = to
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            if settings.smtp_use_tls:
                server.starttls()
            if settings.smtp_username:
                server.login(settings.smtp_username, settings.smtp_password)
            server.sendmail(settings.smtp_from_email, [to], msg.as_string())

    def _send_resend(self, to: str, subject: str, body: str) -> None:
        import resend

        resend.api_key = settings.resend_api_key
        params = {
            "from": settings.smtp_from_email or "Legal Connect <onboarding@resend.dev>",
            "to": [to],
            "subject": subject,
            "text": body,
        }
        resend.Emails.send(params)


email_service = EmailService()
