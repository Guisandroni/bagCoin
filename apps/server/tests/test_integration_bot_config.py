"""Integration pairing requires BOT_* env vars for the requested channel."""

from unittest.mock import AsyncMock
from urllib.parse import parse_qs, unquote, urlparse
from uuid import uuid4

import pytest

from app.core.exceptions import ValidationError
from app.services import integration_service as mod
from app.services.integration_service import IntegrationService


@pytest.mark.anyio
async def test_create_link_token_whatsapp_raises_when_bot_number_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mod, "_whatsapp_bot_digits", lambda: "")
    svc = IntegrationService(AsyncMock())
    with pytest.raises(ValidationError) as excinfo:
        await svc.create_link_token(uuid4(), "whatsapp")
    assert excinfo.value.code == "INTEGRATION_BOT_NOT_CONFIGURED"
    assert excinfo.value.details.get("channel") == "whatsapp"


@pytest.mark.anyio
async def test_create_link_token_telegram_raises_when_username_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mod, "_telegram_bot_username", lambda: "")
    svc = IntegrationService(AsyncMock())
    with pytest.raises(ValidationError) as excinfo:
        await svc.create_link_token(uuid4(), "telegram")
    assert excinfo.value.code == "INTEGRATION_BOT_NOT_CONFIGURED"
    assert excinfo.value.details.get("channel") == "telegram"


def test_whatsapp_deeplink_includes_authentication_text(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mod, "_whatsapp_bot_digits", lambda: "5511999999999")
    monkeypatch.setattr(mod, "_telegram_bot_username", lambda: "bagcoin_bot")
    svc = IntegrationService(AsyncMock())

    deeplink_whatsapp, _, manual_whatsapp, _ = svc._build_deeplinks("abcdefghijklmnop")

    assert manual_whatsapp == "Enviando token para autenticacao. #bagcoin link abcdefghijklmnop"
    assert deeplink_whatsapp is not None
    text = parse_qs(urlparse(deeplink_whatsapp).query)["text"][0]
    assert unquote(text) == manual_whatsapp
