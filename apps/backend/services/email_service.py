from __future__ import annotations

from email.message import EmailMessage
import logging
import smtplib

import requests

from core.config import settings

logger = logging.getLogger("email_service")


class EmailService:
    @staticmethod
    def _smtp_configured() -> bool:
        return bool(settings.SMTP_HOST and settings.SMTP_FROM_EMAIL)

    @staticmethod
    def _send_via_smtp(user_email: str, subject: str, body: str) -> dict:
        message = EmailMessage()
        message["From"] = settings.SMTP_FROM_EMAIL
        message["To"] = user_email
        message["Subject"] = subject
        message.set_content(body)

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
            if settings.SMTP_USE_TLS:
                server.starttls()
            if settings.SMTP_USERNAME:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(message)

        return {"provider": "smtp", "status": "sent"}

    @staticmethod
    def _send_via_sendgrid(user_email: str, subject: str, body: str) -> dict:
        if not settings.SENDGRID_API_KEY:
            raise RuntimeError("SendGrid is not configured.")

        response = requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={
                "Authorization": f"Bearer {settings.SENDGRID_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "personalizations": [{"to": [{"email": user_email}]}],
                "from": {"email": settings.SMTP_FROM_EMAIL or settings.SMTP_USERNAME or "notifications@arogyaai.local"},
                "subject": subject,
                "content": [{"type": "text/plain", "value": body}],
            },
            timeout=15,
        )
        response.raise_for_status()
        return {"provider": "sendgrid", "status": "sent"}

    @staticmethod
    def send_email(user_email: str, subject: str, body: str) -> dict:
        last_error: Exception | None = None

        if EmailService._smtp_configured():
            try:
                return EmailService._send_via_smtp(user_email, subject, body)
            except Exception as exc:
                last_error = exc
                logger.warning("[Notifications] SMTP delivery failed for %s: %s", user_email, exc)

        if settings.SENDGRID_API_KEY:
            try:
                return EmailService._send_via_sendgrid(user_email, subject, body)
            except Exception as exc:
                last_error = exc
                logger.warning("[Notifications] SendGrid delivery failed for %s: %s", user_email, exc)

        if last_error is not None:
            raise last_error

        raise RuntimeError("No email provider is configured. Set SMTP or SendGrid credentials.")
