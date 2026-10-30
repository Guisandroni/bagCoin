"""Contrato provisório sendText Evolution 2.3.7; somente tráfego simulado."""

import asyncio
from types import SimpleNamespace

import httpx

from app.services import whatsapp_service


def test_send_text_uses_instance_endpoint_and_api_key(monkeypatch):
    requests = []

    def handle(request):
        requests.append(request)
        return httpx.Response(201, json={"key": {"id": "test"}})

    monkeypatch.setattr(
        whatsapp_service,
        "settings",
        SimpleNamespace(
            EVOLUTION_API_URL="http://evolution.local:8080",
            EVOLUTION_API_KEY="test-api-key",
            EVOLUTION_INSTANCE_NAME="bagcoin-test",
        ),
    )
    original_client = httpx.AsyncClient
    monkeypatch.setattr(
        whatsapp_service.httpx,
        "AsyncClient",
        lambda **kwargs: original_client(transport=httpx.MockTransport(handle), **kwargs),
    )

    assert asyncio.run(whatsapp_service.send_whatsapp_message("5511999999999", "Olá")) is True
    assert len(requests) == 1
    request = requests[0]
    assert request.url.path == "/message/sendText/bagcoin-test"
    assert request.headers["apikey"] == "test-api-key"
    import json

    assert json.loads(request.content) == {"number": "5511999999999", "text": "Olá"}


def test_send_text_stops_after_http_failure_without_retry(monkeypatch):
    requests = []

    def handle(request):
        requests.append(request)
        return httpx.Response(503)

    monkeypatch.setattr(whatsapp_service, "settings", SimpleNamespace(
        EVOLUTION_API_URL="http://evolution.local:8080",
        EVOLUTION_API_KEY="test-api-key",
        EVOLUTION_INSTANCE_NAME="bagcoin-test",
    ))
    original_client = httpx.AsyncClient
    monkeypatch.setattr(
        whatsapp_service.httpx,
        "AsyncClient",
        lambda **kwargs: original_client(transport=httpx.MockTransport(handle), **kwargs),
    )
    assert asyncio.run(whatsapp_service.send_whatsapp_message("5511999999999", "x" * 5000)) is False
    assert len(requests) == 1
