"""Shared plain-text email delivery helpers."""

from __future__ import annotations

import logging
from email.message import EmailMessage

import httpx

from app.core.config import settings
from app.core.exceptions import ExternalServiceError

logger = logging.getLogger(__name__)


async def send_plain_email(*, to_email: str, subject: str, body: str, reply_to: str | None = None) -> None:
    """Send a plain-text email using the configured provider."""
    provider = (settings.EMAIL_PROVIDER or "smtp").strip().lower()
    if provider == "smtp":
        await _send_smtp(to_email=to_email, subject=subject, body=body, reply_to=reply_to)
        return
    if provider == "resend_api":
        await _send_resend(to_email=to_email, subject=subject, body=body, reply_to=reply_to)
        return
    raise ExternalServiceError(
        message="Provedor de email inválido",
        code="EMAIL_DELIVERY_NOT_CONFIGURED",
        details={"provider": provider},
    )


async def _send_smtp(*, to_email: str, subject: str, body: str, reply_to: str | None = None) -> None:
    if not settings.SMTP_HOST or not settings.SMTP_FROM_EMAIL:
        raise ExternalServiceError(
            message="SMTP não está configurado",
            code="EMAIL_DELIVERY_NOT_CONFIGURED",
        )
    try:
        import aiosmtplib
    except ImportError as exc:
        raise ExternalServiceError(
            message="A dependência de SMTP não está instalada",
            code="EMAIL_DELIVERY_NOT_CONFIGURED",
        ) from exc

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.SMTP_FROM_EMAIL
    message["To"] = to_email
    if reply_to:
        message["Reply-To"] = reply_to
    message.set_content(body)

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER or None,
            password=settings.SMTP_PASSWORD or None,
            start_tls=settings.SMTP_USE_TLS,
        )
    except Exception as exc:
        logger.exception("[email_delivery] smtp send failed", extra={"email": to_email})
        raise ExternalServiceError(
            message="Não foi possível enviar o email",
            code="EMAIL_DELIVERY_FAILED",
        ) from exc


async def _send_resend(*, to_email: str, subject: str, body: str, reply_to: str | None = None) -> None:
    if not settings.RESEND_API_KEY or not settings.RESEND_FROM_EMAIL:
        raise ExternalServiceError(
            message="Resend não está configurado",
            code="EMAIL_DELIVERY_NOT_CONFIGURED",
        )

    payload = {
        "from": settings.RESEND_FROM_EMAIL,
        "to": [to_email],
        "subject": subject,
        "text": body,
    }
    if reply_to:
        payload["reply_to"] = reply_to
    headers = {
        "Authorization": f"Bearer {settings.RESEND_API_KEY}",
        "Content-Type": "application/json",
    }
    url = f"{settings.RESEND_API_BASE_URL.rstrip('/')}/emails"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.exception("[email_delivery] resend send failed", extra={"email": to_email})
        raise ExternalServiceError(
            message="Não foi possível enviar o email",
            code="EMAIL_DELIVERY_FAILED",
        ) from exc
