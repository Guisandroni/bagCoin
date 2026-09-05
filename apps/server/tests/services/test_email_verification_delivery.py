from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.core.config import settings
from app.core.exceptions import ExternalServiceError
from app.services.email_verification import EmailVerificationService


@pytest.mark.anyio
async def test_send_email_routes_to_smtp():
    service = EmailVerificationService(db=None, redis=None)  # type: ignore[arg-type]

    with (
        patch.object(settings, "EMAIL_PROVIDER", "smtp"),
        patch.object(service, "_send_email_smtp", new=AsyncMock()) as smtp_mock,
        patch.object(service, "_send_email_resend_api", new=AsyncMock()) as resend_mock,
    ):
        await service._send_email("user@example.com", "123456")

    smtp_mock.assert_awaited_once_with("user@example.com", "123456")
    resend_mock.assert_not_called()


@pytest.mark.anyio
async def test_send_email_routes_to_resend():
    service = EmailVerificationService(db=None, redis=None)  # type: ignore[arg-type]

    with (
        patch.object(settings, "EMAIL_PROVIDER", "resend_api"),
        patch.object(service, "_send_email_smtp", new=AsyncMock()) as smtp_mock,
        patch.object(service, "_send_email_resend_api", new=AsyncMock()) as resend_mock,
    ):
        await service._send_email("user@example.com", "123456")

    resend_mock.assert_awaited_once_with("user@example.com", "123456")
    smtp_mock.assert_not_called()


@pytest.mark.anyio
async def test_send_email_resend_requires_config():
    service = EmailVerificationService(db=None, redis=None)  # type: ignore[arg-type]

    with (
        patch.object(settings, "RESEND_API_KEY", ""),
        patch.object(settings, "RESEND_FROM_EMAIL", ""),
    ):
        with pytest.raises(ExternalServiceError) as exc_info:
            await service._send_email_resend_api("user@example.com", "123456")

    assert exc_info.value.code == "EMAIL_DELIVERY_NOT_CONFIGURED"


class _FakeResendClientError:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, *args, **kwargs):
        response = httpx.Response(401, request=httpx.Request("POST", "https://api.resend.com/emails"))
        raise httpx.HTTPStatusError("unauthorized", request=response.request, response=response)


@pytest.mark.anyio
async def test_send_email_resend_http_error_returns_delivery_failed():
    service = EmailVerificationService(db=None, redis=None)  # type: ignore[arg-type]

    with (
        patch.object(settings, "RESEND_API_KEY", "re_test"),
        patch.object(settings, "RESEND_FROM_EMAIL", "noreply@bagcoin.test"),
        patch("app.services.email_verification.httpx.AsyncClient", return_value=_FakeResendClientError()),
    ):
        with pytest.raises(ExternalServiceError) as exc_info:
            await service._send_email_resend_api("user@example.com", "123456")

    assert exc_info.value.code == "EMAIL_DELIVERY_FAILED"
