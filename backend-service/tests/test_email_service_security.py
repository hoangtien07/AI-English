import logging
import smtplib
from email.message import EmailMessage
from unittest.mock import MagicMock, Mock, patch

import pytest

from app.core.config import settings
from app.services import email_service as email_service_module
from app.services.email_service import EmailService


def test_gmail_starttls_uses_bounded_timeout_and_tls_context(monkeypatch):
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setattr(settings, "SMTP_PORT", 587)
    monkeypatch.setattr(settings, "SMTP_USERNAME", "sender@example.com")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "not-a-real-password")
    monkeypatch.setattr(settings, "SMTP_USE_TLS", True)
    monkeypatch.setattr(settings, "SMTP_USE_SSL", False)
    monkeypatch.setattr(settings, "SMTP_TIMEOUT", 10)

    smtp_server = MagicMock()
    smtp_server.has_extn.return_value = True
    smtp_factory = MagicMock()
    smtp_factory.return_value.__enter__.return_value = smtp_server
    message = EmailMessage()
    message["To"] = "learner@example.com"

    with patch("app.services.email_service.smtplib.SMTP", smtp_factory):
        EmailService._send_message_blocking(message)

    smtp_factory.assert_called_once_with("smtp.gmail.com", 587, timeout=10)
    smtp_server.ehlo.assert_called()
    smtp_server.has_extn.assert_called_once_with("starttls")
    smtp_server.starttls.assert_called_once()
    smtp_server.login.assert_called_once_with("sender@example.com", "not-a-real-password")
    smtp_server.send_message.assert_called_once_with(message)


def test_starttls_is_required_before_authentication(monkeypatch):
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setattr(settings, "SMTP_PORT", 587)
    monkeypatch.setattr(settings, "SMTP_USERNAME", "sender@example.com")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "not-a-real-password")
    monkeypatch.setattr(settings, "SMTP_USE_TLS", True)
    monkeypatch.setattr(settings, "SMTP_USE_SSL", False)

    smtp_server = MagicMock()
    smtp_server.has_extn.return_value = False
    smtp_factory = MagicMock()
    smtp_factory.return_value.__enter__.return_value = smtp_server

    with patch("app.services.email_service.smtplib.SMTP", smtp_factory), pytest.raises(
        smtplib.SMTPNotSupportedError, match="STARTTLS"
    ):
        EmailService._send_message_blocking(EmailMessage())

    smtp_server.login.assert_not_called()


@pytest.mark.asyncio
async def test_unsent_password_reset_logs_full_local_url_in_development(
    monkeypatch,
):
    monkeypatch.setattr(settings, "APP_ENV", "development")
    monkeypatch.setattr(settings, "SMTP_HOST", None)
    monkeypatch.setattr(
        settings,
        "PASSWORD_RESET_URL_BASE",
        "http://localhost:8080/reset-password",
    )
    token = "local-reset-token"
    warning = Mock()
    monkeypatch.setattr(email_service_module.logger, "warning", warning)

    sent = await EmailService.send_password_reset_email(
        to_email="learner@example.com",
        reset_token=token,
        display_name="Learner",
    )

    assert sent is False
    warning.assert_called_once_with(
        "SMTP_HOST not configured. %s email was not sent. "
        "Generated local URL for %s: %s",
        "Password reset",
        "learner@example.com",
        f"http://localhost:8080/reset-password?token={token}",
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("app_env", ["testing", "production"])
async def test_unsent_verification_suppresses_tokenized_url_outside_development(
    app_env,
    monkeypatch,
    caplog,
):
    monkeypatch.setattr(settings, "APP_ENV", app_env)
    monkeypatch.setattr(settings, "SMTP_HOST", None)
    monkeypatch.setattr(
        settings,
        "EMAIL_VERIFICATION_URL_BASE",
        "http://localhost:8080/verify-email",
    )
    token = "must-not-appear-in-logs"

    with caplog.at_level(logging.ERROR, logger="app.services.email_service"):
        sent = await EmailService.send_verification_email(
            to_email="learner@example.com",
            token=token,
            display_name="Learner",
        )

    assert sent is False
    assert "tokenized URL suppressed outside development" in caplog.text
    assert token not in caplog.text
    assert "?token=" not in caplog.text
