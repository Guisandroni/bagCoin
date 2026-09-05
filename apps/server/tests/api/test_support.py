from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from app.api.routes.v1 import support
from app.core.exceptions import BadRequestError
from app.schemas.support import SupportContactRequest


@pytest.mark.anyio
async def test_contact_support_sends_to_configured_support_email_with_reply_to(monkeypatch):
    send_email = AsyncMock()
    monkeypatch.setattr(support.settings, "SUPPORT_EMAIL", "responsavel@bagcoin.app")
    monkeypatch.setattr(support, "send_plain_email", send_email)
    current_user = SimpleNamespace(
        id=123,
        full_name="Guilherme",
        email="guilherme@example.com",
    )

    response = await support.contact_support(
        SupportContactRequest(subject="Ajuda", message="Preciso de suporte no aplicativo."),
        current_user,
    )

    assert response.sent is True
    send_email.assert_awaited_once()
    kwargs = send_email.await_args.kwargs
    assert kwargs["to_email"] == "responsavel@bagcoin.app"
    assert kwargs["reply_to"] == "guilherme@example.com"
    assert "Usuário: Guilherme" in kwargs["body"]
    assert "Email: guilherme@example.com" in kwargs["body"]
    assert "ID:" not in kwargs["body"]


@pytest.mark.anyio
async def test_contact_support_requires_support_email(monkeypatch):
    monkeypatch.setattr(support.settings, "SUPPORT_EMAIL", "")

    with pytest.raises(BadRequestError) as exc_info:
        await support.contact_support(
            SupportContactRequest(subject="Ajuda", message="Preciso de suporte no aplicativo."),
            SimpleNamespace(full_name="Guilherme", email="guilherme@example.com"),
        )

    assert exc_info.value.code == "SUPPORT_EMAIL_NOT_CONFIGURED"


def test_support_contact_request_strips_fields():
    request = SupportContactRequest(
        subject="  Ajuda  ",
        message="  Preciso de suporte no aplicativo.  ",
    )

    assert request.subject == "Ajuda"
    assert request.message == "Preciso de suporte no aplicativo."


def test_support_contact_request_rejects_short_fields_after_strip():
    with pytest.raises(ValidationError):
        SupportContactRequest(subject="  oi  ", message="Preciso de suporte no aplicativo.")

    with pytest.raises(ValidationError):
        SupportContactRequest(subject="Ajuda", message="  curta  ")
