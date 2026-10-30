"""Contratos provisórios de webhook Evolution 2.3.7, sem contato com WhatsApp."""

import asyncio
from unittest.mock import MagicMock

import httpx
import pytest
from fastapi import FastAPI

from app.api.routes.v1 import webhook


@pytest.fixture
def client(monkeypatch):
    config = MagicMock(wraps=webhook.settings)
    config.EVOLUTION_WEBHOOK_SECRET = "test-webhook-secret"
    config.EVOLUTION_INSTANCE_NAME = "bagcoin-test"
    monkeypatch.setattr(webhook, "settings", config)
    monkeypatch.setattr(webhook, "orchestrator", MagicMock())
    application = FastAPI()
    application.include_router(webhook.router, prefix="/api/v1")
    return application


def event(*, sender="5511999999999@s.whatsapp.net", from_me=False, instance="bagcoin-test"):
    return {
        "event": "messages.upsert",
        "instance": instance,
        "data": {
            "key": {"id": "TEST-MESSAGE-1", "remoteJid": sender, "fromMe": from_me},
            "message": {"conversation": "Olá"},
        },
    }


def post(client, body, secret="test-webhook-secret"):
    async def request():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=client), base_url="http://test"
        ) as session:
            return await session.post(
                "/api/v1/webhook/evolution",
                json=body,
                headers={"X-Evolution-Webhook-Secret": secret},
            )

    return asyncio.run(request())


def test_webhook_rejects_wrong_secret_without_invoking_agent(client):
    response = post(client, event(), secret="incorrect")
    assert response.status_code in (401, 403)
    webhook.orchestrator.invoke.assert_not_called()


@pytest.mark.parametrize(
    "body",
    [
        event(from_me=True),
        event(sender="123456789@g.us"),
        event(sender="123456789@lid"),
        event(instance="unexpected-instance"),
    ],
    ids=["own-message", "group", "unresolved-lid", "other-instance"],
)
def test_ignored_or_ambiguous_events_do_not_invoke_agent(client, body):
    response = post(client, body)
    assert response.status_code != 404
    webhook.orchestrator.invoke.assert_not_called()
