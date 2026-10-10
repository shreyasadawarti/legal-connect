from typing import Any

import pytest

from app.config import settings
from app.services.email_service import EmailDeliveryError, email_service


@pytest.mark.asyncio
async def test_password_reset_template(monkeypatch: pytest.MonkeyPatch):
    captured: dict[str, str] = {}

    async def fake_send(to: str, subject: str, text: str, html_body: str) -> None:
        captured.update(to=to, subject=subject, text=text, html=html_body)

    monkeypatch.setattr(email_service, "_send", fake_send)
    await email_service.send_password_reset("user@example.com", "abc-token-123")

    assert captured["to"] == "user@example.com"
    assert captured["subject"] == "Reset Your Legal Connect Password"
    assert "Reset My Password" in captured["html"]
    assert "/reset-password?token=abc-token-123" in captured["html"]
    assert "/reset-password?token=abc-token-123" in captured["text"]
    assert "legal connect" in captured["text"].lower()


@pytest.mark.asyncio
async def test_verification_template(monkeypatch: pytest.MonkeyPatch):
    captured: dict[str, str] = {}

    async def fake_send(to: str, subject: str, text: str, html_body: str) -> None:
        captured.update(to=to, subject=subject, text=text, html=html_body)

    monkeypatch.setattr(email_service, "_send", fake_send)
    await email_service.send_verification("user@example.com", "verify-token-456")

    assert captured["subject"] == "Verify Your Legal Connect Email"
    assert "Verify My Email" in captured["html"]
    assert "/verify-email?token=verify-token-456" in captured["html"]


@pytest.mark.asyncio
async def test_unconfigured_never_logs_token(caplog: pytest.LogCaptureFixture):
    assert not email_service.is_configured
    await email_service.send_verification("user@example.com", "super-secret-token")
    sent = [r.getMessage() for r in caplog.records]
    assert any("Email not configured" in m for m in sent)
    assert not any("super-secret-token" in m for m in sent)


@pytest.mark.asyncio
async def test_delivery_failure_raises(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "smtp_host", "smtp.invalid.local")
    monkeypatch.setattr(settings, "smtp_from_email", "Legal Connect <no-reply@example.com>")
    monkeypatch.setattr(settings, "resend_api_key", "")

    def boom(to: str, subject: str, text: str, html_body: str) -> None:
        raise RuntimeError("connection refused")

    monkeypatch.setattr(email_service, "_send_smtp", boom)
    with pytest.raises(EmailDeliveryError):
        await email_service.send_password_reset("user@example.com", "token")


@pytest.mark.asyncio
async def test_send_success_when_configured(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "smtp_host", "smtp.invalid.local")
    monkeypatch.setattr(settings, "smtp_from_email", "Legal Connect <no-reply@example.com>")
    monkeypatch.setattr(settings, "resend_api_key", "")

    sent: list[Any] = []

    def ok(to: str, subject: str, text: str, html_body: str) -> None:
        sent.append(to)

    monkeypatch.setattr(email_service, "_send_smtp", ok)
    await email_service.send_verification("user@example.com", "token")
    assert sent == ["user@example.com"]