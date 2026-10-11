import asyncio
import html
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings

logger = logging.getLogger("legalconnect.email")


class EmailDeliveryError(RuntimeError):
    """Raised when the email backend is configured but delivery fails."""


def _button(link: str, label: str) -> str:
    return (
        f'<a href="{html.escape(link, quote=True)}" '
        f'style="display:inline-block;padding:12px 24px;background-color:#1d4ed8;'
        f'color:#ffffff;text-decoration:none;border-radius:6px;font-weight:600;">'
        f"{html.escape(label)}</a>"
    )


def _envelope(title: str, body_html: str) -> str:
    return (
        "<div style=\"font-family:Arial,Helvetica,sans-serif;max-width:560px;margin:0 auto;\">"
        f"<div style=\"background-color:#1d4ed8;padding:16px 24px;color:#ffffff;"
        f"font-size:18px;font-weight:700;\">Legal Connect</div>"
        f'<div style="padding:24px;background-color:#ffffff;">{body_html}</div>'
        f'<div style="padding:16px 24px;color:#6b7280;font-size:12px;">'
        f"Legal Connect Support Team &middot; You are receiving this email because you have "
        f"an account on Legal Connect.</div></div>"
    )


class EmailService:
    """Sends transactional emails via SMTP or Resend.

    When email is unconfigured the send is a no-op so development flows keep
    working (graceful degradation). When configured, a delivery failure raises
    `EmailDeliveryError` so callers never claim an email was sent when it was
    not.
    """

    @property
    def is_configured(self) -> bool:
        return bool(
            (settings.smtp_host and settings.smtp_from_email) or settings.resend_api_key
        )

    async def send_password_reset(self, to: str, token: str) -> None:
        reset_url = f"{settings.frontend_url}/reset-password?token={token}"
        subject = "Reset Your Legal Connect Password"
        text = (
            "Hello,\n\n"
            "We received a request to reset the password for your Legal Connect account.\n\n"
            f"To create a new password, please open the secure link below:\n{reset_url}\n\n"
            "This link is valid for a limited time and can be used only once. If you did "
            "not request a password reset, you can safely ignore this email. Your password "
            "will remain unchanged.\n\n"
            "Regards,\nLegal Connect Support Team"
        )
        body_html = (
            "<p>Hello,</p>"
            "<p>We received a request to reset the password for your Legal Connect account.</p>"
            f'<p>To create a new password, please click the secure button below:</p><p>{_button(reset_url, "Reset My Password")}</p>'
            "<p style=\"font-size:13px;color:#6b7280;\">This link is valid for a limited time and "
            "can be used only once. If you did not request a password reset, you can safely "
            "ignore this email. Your password will remain unchanged.</p>"
            "<p>Regards,<br/>Legal Connect Support Team</p>"
        )
        await self._send(to, subject, text, _envelope(subject, body_html))

    async def send_verification(self, to: str, token: str) -> None:
        verify_url = f"{settings.frontend_url}/verify-email?token={token}"
        subject = "Verify Your Legal Connect Email"
        text = (
            "Hello,\n\n"
            "Welcome to Legal Connect! Please verify your email address by opening the "
            f"secure link below (valid for 24 hours):\n{verify_url}\n\n"
            "Regards,\nLegal Connect Support Team"
        )
        body_html = (
            "<p>Hello,</p>"
            "<p>Welcome to Legal Connect! Please verify your email address by clicking "
            f"the secure button below (valid for 24 hours):</p><p>{_button(verify_url, 'Verify My Email')}</p>"
            "<p>Regards,<br/>Legal Connect Support Team</p>"
        )
        await self._send(to, subject, text, _envelope(subject, body_html))

    async def _send(self, to: str, subject: str, text: str, html_body: str) -> None:
        if not self.is_configured:
            logger.info("Email not configured; skipping send to %s (subject '%s').", to, subject)
            return
        try:
            if settings.resend_api_key:
                await asyncio.to_thread(self._send_resend, to, subject, text, html_body)
            else:
                await asyncio.to_thread(self._send_smtp, to, subject, text, html_body)
        except Exception as exc:  # noqa: BLE001
            logger.error("Email delivery failed for %s (subject '%s'): %s", to, subject, exc)
            raise EmailDeliveryError("Failed to send email") from exc

    def _send_smtp(self, to: str, subject: str, text: str, html_body: str) -> None:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        from_email = settings.smtp_from_email or "Legal Connect <noreply@legalconnect.local>"
        msg["From"] = from_email
        msg["To"] = to
        msg.attach(MIMEText(text, "plain"))
        msg.attach(MIMEText(html_body, "html"))
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            if settings.smtp_use_tls:
                server.starttls()
            if settings.smtp_username:
                server.login(settings.smtp_username, settings.smtp_password)
            server.sendmail(from_email, [to], msg.as_string())

    def _send_resend(self, to: str, subject: str, text: str, html_body: str) -> None:
        import resend

        resend.api_key = settings.resend_api_key
        from_email = settings.smtp_from_email or "Legal Connect <onboarding@resend.dev>"
        params = {
            "from": from_email,
            "to": [to],
            "subject": subject,
            "text": text,
            "html": html_body,
        }
        resend.Emails.send(params)


email_service = EmailService()