"""Webhook endpoint tests for WhatsApp, Telegram, and health.

Covers:
- Auth (missing/invalid API Key)
- WhatsApp valid, invalid phone, duplicate, media, PDF, orchestrator error
- Telegram valid, username, orchestrator error
- Health: ok, redis_ok, redis_unavailable
"""

from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient

from app.core.config import settings

WHATSAPP_URL = f"{settings.API_V1_STR}/webhook/whatsapp"
TELEGRAM_URL = f"{settings.API_V1_STR}/webhook/telegram"
HEALTH_URL = f"{settings.API_V1_STR}/webhook/health"

WHATSAPP_HEADERS = {"X-API-Key": settings.WHATSAPP_API_KEY}
TELEGRAM_HEADERS = {"X-API-Key": settings.API_KEY}


# =============================================================================
# WhatsApp — Authentication
# =============================================================================


@pytest.mark.anyio
async def test_whatsapp_requires_api_key(client: AsyncClient):
    """POST /webhook/whatsapp sem header X-API-Key → 422 (Header(...) required)."""
    response = await client.post(WHATSAPP_URL, json={})
    # FastAPI retorna 422 quando um parâmetro Header(...) obrigatório está ausente,
    # antes mesmo de chamar verify_api_key que retornaria 401.
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data


@pytest.mark.anyio
async def test_whatsapp_invalid_api_key(client: AsyncClient):
    """POST /webhook/whatsapp com X-API-Key inválida → 401."""
    response = await client.post(
        WHATSAPP_URL,
        json={},
        headers={"X-API-Key": "invalid-key-xyz"},
    )
    assert response.status_code == 401
    data = response.json()
    assert "inválida" in data["detail"].lower() or "API Key" in data["detail"]


# =============================================================================
# WhatsApp — Processamento
# =============================================================================


@pytest.mark.anyio
async def test_whatsapp_valid_message(client: AsyncClient):
    """POST /webhook/whatsapp com mensagem válida → 200 + reply do orquestrador."""
    with (
        patch("app.api.routes.v1.webhook.is_duplicate_message", return_value=False),
        patch("app.api.routes.v1.webhook.orchestrator.invoke") as mock_orch,
    ):
        mock_orch.return_value = {"response": "Olá! Como posso ajudar?"}

        payload = {
            "phone_number": "5511999999999",
            "message": "Olá",
            "type": "chat",
            "timestamp": 1234567890,
        }

        response = await client.post(
            WHATSAPP_URL,
            json=payload,
            headers=WHATSAPP_HEADERS,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["reply"] == "Olá! Como posso ajudar?"
        assert data["document"] is None
        mock_orch.assert_called_once()


@pytest.mark.anyio
async def test_whatsapp_invalid_phone(client: AsyncClient):
    """POST /webhook/whatsapp com telefone inválido (sem dígitos) → 200 + erro amigável."""
    with patch("app.api.routes.v1.webhook.is_duplicate_message", return_value=False):
        payload = {
            "phone_number": "@invalid",  # após normalize vira "" → < 5 dígitos
            "message": "Olá",
            "type": "chat",
            "timestamp": 1234567890,
        }

        response = await client.post(
            WHATSAPP_URL,
            json=payload,
            headers=WHATSAPP_HEADERS,
        )

        assert response.status_code == 200
        data = response.json()
        assert "inválido" in data["reply"].lower() or "incompleto" in data["reply"].lower()


@pytest.mark.anyio
async def test_whatsapp_duplicate_message(client: AsyncClient):
    """POST /webhook/whatsapp com mensagem duplicada → 200 + reply vazio."""
    with (
        patch("app.api.routes.v1.webhook.is_duplicate_message", return_value=True),
        patch("app.api.routes.v1.webhook.orchestrator.invoke") as mock_orch,
    ):
        payload = {
            "phone_number": "5511999999999",
            "message": "Saldo",
            "type": "chat",
            "timestamp": 1234567890,
        }

        response = await client.post(
            WHATSAPP_URL,
            json=payload,
            headers=WHATSAPP_HEADERS,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["reply"] == ""
        mock_orch.assert_not_called()


@pytest.mark.anyio
async def test_whatsapp_with_media(client: AsyncClient):
    """POST /webhook/whatsapp com mídia (imagem) → 200 + context.media no state."""
    with (
        patch("app.api.routes.v1.webhook.is_duplicate_message", return_value=False),
        patch("app.api.routes.v1.webhook.orchestrator.invoke") as mock_orch,
    ):
        mock_orch.return_value = {"response": "Imagem recebida e processada."}

        payload = {
            "phone_number": "5511999999999",
            "message": "O que tem nesta imagem?",
            "type": "image",
            "timestamp": 1234567890,
            "hasMedia": True,
            "media": {"mimetype": "image/jpeg", "url": "https://example.com/img.jpg"},
        }

        response = await client.post(
            WHATSAPP_URL,
            json=payload,
            headers=WHATSAPP_HEADERS,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["reply"] == "Imagem recebida e processada."

        # Verifica que media foi passada no estado inicial
        call_args = mock_orch.call_args[0][0]
        assert call_args["source_format"] == "image"
        assert "media" in call_args["context"]


@pytest.mark.anyio
async def test_whatsapp_with_pdf(client: AsyncClient, tmp_path):
    """POST /webhook/whatsapp com relatório PDF → 200 + document com base64."""
    with (
        patch("app.api.routes.v1.webhook.is_duplicate_message", return_value=False),
        patch("app.api.routes.v1.webhook.orchestrator.invoke") as mock_orch,
    ):
        # Cria um PDF fake no caminho que o orquestrador retornará
        fake_pdf = tmp_path / "relatorio.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 fake pdf content for testing")

        mock_orch.return_value = {
            "response": "Relatório gerado com sucesso.",
            "report_path": str(fake_pdf),
        }

        payload = {
            "phone_number": "5511999999999",
            "message": "Gere um relatório",
            "type": "chat",
            "timestamp": 1234567890,
        }

        response = await client.post(
            WHATSAPP_URL,
            json=payload,
            headers=WHATSAPP_HEADERS,
        )

        assert response.status_code == 200
        data = response.json()
        assert "Relatório" in data["reply"]
        assert data["document"] is not None
        assert data["document"]["mimetype"] == "application/pdf"
        assert data["document"]["filename"] == "relatorio.pdf"
        assert isinstance(data["document"]["data"], str)
        assert len(data["document"]["data"]) > 0


@pytest.mark.anyio
async def test_whatsapp_orchestrator_error(client: AsyncClient):
    """POST /webhook/whatsapp com erro no orquestrador → 200 + fallback amigável."""
    with (
        patch("app.api.routes.v1.webhook.is_duplicate_message", return_value=False),
        patch("app.api.routes.v1.webhook.orchestrator.invoke") as mock_orch,
    ):
        mock_orch.side_effect = RuntimeError("Falha interna no grafo")

        payload = {
            "phone_number": "5511999999999",
            "message": "Saldo",
            "type": "chat",
            "timestamp": 1234567890,
        }

        response = await client.post(
            WHATSAPP_URL,
            json=payload,
            headers=WHATSAPP_HEADERS,
        )

        assert response.status_code == 200
        data = response.json()
        assert "erro" in data["reply"].lower()
        assert "tente novamente" in data["reply"].lower()


# =============================================================================
# Telegram — Authentication
# =============================================================================


@pytest.mark.anyio
async def test_telegram_requires_api_key(client: AsyncClient):
    """POST /webhook/telegram sem X-API-Key → 401."""
    response = await client.post(TELEGRAM_URL, json={})
    assert response.status_code == 401
    data = response.json()
    # verify_api_key de deps.py usa auto_error=False e levanta AuthenticationError,
    # que o exception handler formata como {"error": {"code": "AUTHENTICATION_ERROR", ...}}
    assert "error" in data
    assert data["error"]["code"] == "AUTHENTICATION_ERROR"
    assert "API Key" in data["error"]["message"]


# =============================================================================
# Telegram — Processamento
# =============================================================================


@pytest.mark.anyio
async def test_telegram_valid_message(client: AsyncClient):
    """POST /webhook/telegram com mensagem válida → 200 + reply."""
    with (
        patch("app.api.routes.v1.webhook.is_duplicate_message", return_value=False),
        patch("app.api.routes.v1.webhook.get_or_create_user_sync") as mock_get_user,
        patch("app.api.routes.v1.webhook.orchestrator.invoke") as mock_orch,
    ):
        mock_get_user.return_value = None
        mock_orch.return_value = {"response": "Olá do Telegram!"}

        payload = {
            "chat_id": "123456789",
            "message": "Oi",
            "username": None,
        }

        response = await client.post(
            TELEGRAM_URL,
            json=payload,
            headers=TELEGRAM_HEADERS,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["reply"] == "Olá do Telegram!"
        mock_orch.assert_called_once()

        # Verifica phone_number sintético
        call_state = mock_orch.call_args[0][0]
        assert "telegram:123456789" in call_state["phone_number"]
        assert call_state["report_id"] is None


@pytest.mark.anyio
async def test_telegram_report_response_includes_media_url(client: AsyncClient):
    """POST /webhook/telegram com relatório gerado → retorna media.url."""
    with (
        patch("app.api.routes.v1.webhook.is_duplicate_message", return_value=False),
        patch("app.api.routes.v1.webhook.get_or_create_user_sync") as mock_get_user,
        patch("app.api.routes.v1.webhook.orchestrator.invoke") as mock_orch,
    ):
        mock_get_user.return_value = None
        mock_orch.return_value = {
            "response": "Relatório gerado.",
            "report_id": 42,
            "report_path": "/app/reports/report_telegram_42.pdf",
        }

        payload = {
            "chat_id": "123456789",
            "message": "gere um relatório em pdf",
            "username": None,
        }

        response = await client.post(
            TELEGRAM_URL,
            json=payload,
            headers=TELEGRAM_HEADERS,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["reply"] == "Relatório gerado."
        assert data["media"] == {
            "type": "document",
            "url": "http://app:8000/api/v1/webhook/reports/42/download",
            "filename": "report_telegram_42.pdf",
            "mimetype": "application/pdf",
        }


@pytest.mark.anyio
async def test_telegram_with_username(client: AsyncClient):
    """POST /webhook/telegram com username opcional → 200."""
    with (
        patch("app.api.routes.v1.webhook.is_duplicate_message", return_value=False),
        patch("app.api.routes.v1.webhook.get_or_create_user_sync") as mock_get_user,
        patch("app.api.routes.v1.webhook.orchestrator.invoke") as mock_orch,
    ):
        mock_get_user.return_value = None
        mock_orch.return_value = {"response": "Resposta com username."}

        payload = {
            "chat_id": "987654321",
            "message": "Meu saldo",
            "username": "joaosilva",
        }

        response = await client.post(
            TELEGRAM_URL,
            json=payload,
            headers=TELEGRAM_HEADERS,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["reply"] == "Resposta com username."


@pytest.mark.anyio
async def test_telegram_orchestrator_error(client: AsyncClient):
    """POST /webhook/telegram com erro no orquestrador → 200 + fallback."""
    with (
        patch("app.api.routes.v1.webhook.is_duplicate_message", return_value=False),
        patch("app.api.routes.v1.webhook.get_or_create_user_sync") as mock_get_user,
        patch("app.api.routes.v1.webhook.orchestrator.invoke") as mock_orch,
    ):
        mock_get_user.return_value = None
        mock_orch.side_effect = ValueError("Falha no Telegram")

        payload = {
            "chat_id": "555555555",
            "message": "Histórico",
        }

        response = await client.post(
            TELEGRAM_URL,
            json=payload,
            headers=TELEGRAM_HEADERS,
        )

        assert response.status_code == 200
        data = response.json()
        assert "erro" in data["reply"].lower()
        assert "tente novamente" in data["reply"].lower()


# =============================================================================
# Telegram — Agent actions (create expense, check balance, create goal, invalid)
# =============================================================================


@pytest.mark.anyio
async def test_telegram_agent_create_expense(client: AsyncClient):
    """POST /webhook/telegram com 'gastei 50 no mercado' → criacao de despesa."""
    with (
        patch("app.api.routes.v1.webhook.is_duplicate_message", return_value=False),
        patch("app.api.routes.v1.webhook.get_or_create_user_sync") as mock_get_user,
        patch("app.api.routes.v1.webhook.orchestrator.invoke") as mock_orch,
    ):
        mock_get_user.return_value = None
        mock_orch.return_value = {
            "response": "Despesa de R$ 50,00 no mercado registrada com sucesso! ✅",
        }

        payload = {
            "chat_id": "111222333",
            "message": "gastei 50 no mercado",
            "username": None,
        }

        response = await client.post(
            TELEGRAM_URL,
            json=payload,
            headers=TELEGRAM_HEADERS,
        )

        assert response.status_code == 200
        data = response.json()
        assert "Despesa" in data["reply"]
        assert "50" in data["reply"]
        assert "mercado" in data["reply"]

        # Verifica que o orchestrator foi chamado com a mensagem correta
        call_state = mock_orch.call_args[0][0]
        assert call_state["message"] == "gastei 50 no mercado"
        assert call_state["source_format"] == "text"
        mock_orch.assert_called_once()


@pytest.mark.anyio
async def test_telegram_agent_check_balance(client: AsyncClient):
    """POST /webhook/telegram com 'quanto tenho' → retorno de saldo."""
    with (
        patch("app.api.routes.v1.webhook.is_duplicate_message", return_value=False),
        patch("app.api.routes.v1.webhook.get_or_create_user_sync") as mock_get_user,
        patch("app.api.routes.v1.webhook.orchestrator.invoke") as mock_orch,
    ):
        mock_get_user.return_value = None
        mock_orch.return_value = {
            "response": "Seu saldo atual é de R$ 1.250,00 💰",
        }

        payload = {
            "chat_id": "444555666",
            "message": "quanto tenho",
            "username": "testuser",
        }

        response = await client.post(
            TELEGRAM_URL,
            json=payload,
            headers=TELEGRAM_HEADERS,
        )

        assert response.status_code == 200
        data = response.json()
        assert "saldo" in data["reply"].lower()
        assert "1.250" in data["reply"]

        call_state = mock_orch.call_args[0][0]
        assert call_state["message"] == "quanto tenho"
        assert "telegram:444555666" in call_state["phone_number"]
        mock_orch.assert_called_once()


@pytest.mark.anyio
async def test_telegram_agent_create_goal(client: AsyncClient):
    """POST /webhook/telegram com 'quero guardar 5000' → criacao de meta."""
    with (
        patch("app.api.routes.v1.webhook.is_duplicate_message", return_value=False),
        patch("app.api.routes.v1.webhook.get_or_create_user_sync") as mock_get_user,
        patch("app.api.routes.v1.webhook.orchestrator.invoke") as mock_orch,
    ):
        mock_get_user.return_value = None
        mock_orch.return_value = {
            "response": "Meta de R$ 5.000,00 criada com sucesso! 🎯",
        }

        payload = {
            "chat_id": "777888999",
            "message": "quero guardar 5000",
        }

        response = await client.post(
            TELEGRAM_URL,
            json=payload,
            headers=TELEGRAM_HEADERS,
        )

        assert response.status_code == 200
        data = response.json()
        assert "Meta" in data["reply"]
        assert "5.000" in data["reply"]

        call_state = mock_orch.call_args[0][0]
        assert call_state["message"] == "quero guardar 5000"
        mock_orch.assert_called_once()


@pytest.mark.anyio
async def test_telegram_agent_invalid_message(client: AsyncClient):
    """POST /webhook/telegram com mensagem vazia → fallback."""
    with (
        patch("app.api.routes.v1.webhook.is_duplicate_message", return_value=False),
        patch("app.api.routes.v1.webhook.get_or_create_user_sync") as mock_get_user,
        patch("app.api.routes.v1.webhook.orchestrator.invoke") as mock_orch,
    ):
        mock_get_user.return_value = None
        mock_orch.return_value = {
            "response": "Não entendi sua mensagem. Por favor, digite uma mensagem válida.",
        }

        payload = {
            "chat_id": "000000001",
            "message": "",
        }

        response = await client.post(
            TELEGRAM_URL,
            json=payload,
            headers=TELEGRAM_HEADERS,
        )

        assert response.status_code == 200
        data = response.json()
        # Deve retornar fallback — mensagem vazia não é uma instrução válida
        assert "não entendi" in data["reply"].lower() or "válida" in data["reply"].lower()

        call_state = mock_orch.call_args[0][0]
        assert call_state["message"] == ""  # mensagem vazia foi passada adiante
        mock_orch.assert_called_once()


# =============================================================================
# WhatsApp — Agent actions (create expense, statement upload)
# =============================================================================


@pytest.mark.anyio
async def test_whatsapp_agent_create_expense(client: AsyncClient):
    """POST /webhook/whatsapp com 'gastei 30 no ifood' → criacao de despesa."""
    with (
        patch("app.api.routes.v1.webhook.is_duplicate_message", return_value=False),
        patch("app.api.routes.v1.webhook.orchestrator.invoke") as mock_orch,
    ):
        mock_orch.return_value = {
            "response": "Despesa de R$ 30,00 no ifood registrada com sucesso! ✅",
        }

        payload = {
            "phone_number": "5511888888888",
            "message": "gastei 30 no ifood",
            "type": "chat",
            "timestamp": 1234567890,
        }

        response = await client.post(
            WHATSAPP_URL,
            json=payload,
            headers=WHATSAPP_HEADERS,
        )

        assert response.status_code == 200
        data = response.json()
        assert "Despesa" in data["reply"]
        assert "30" in data["reply"]
        assert "ifood" in data["reply"]
        assert data["document"] is None

        call_state = mock_orch.call_args[0][0]
        assert call_state["message"] == "gastei 30 no ifood"
        assert call_state["phone_number"] == "5511888888888"
        mock_orch.assert_called_once()


@pytest.mark.anyio
async def test_whatsapp_agent_statement_upload(client: AsyncClient):
    """POST /webhook/whatsapp com 'extrato' → processamento de extrato."""
    with (
        patch("app.api.routes.v1.webhook.is_duplicate_message", return_value=False),
        patch("app.api.routes.v1.webhook.orchestrator.invoke") as mock_orch,
    ):
        mock_orch.return_value = {
            "response": "Extrato processado! 15 transacoes importadas com sucesso. 📄",
        }

        payload = {
            "phone_number": "5511999990000",
            "message": "Quero enviar meu extrato bancario",
            "type": "chat",
            "timestamp": 1234567890,
        }

        response = await client.post(
            WHATSAPP_URL,
            json=payload,
            headers=WHATSAPP_HEADERS,
        )

        assert response.status_code == 200
        data = response.json()
        assert "Extrato" in data["reply"] or "extrato" in data["reply"]
        assert "transacoes" in data["reply"].lower() or "importadas" in data["reply"].lower()
        assert data["document"] is None

        call_state = mock_orch.call_args[0][0]
        assert call_state["message"] == "Quero enviar meu extrato bancario"
        assert call_state["phone_number"] == "5511999990000"
        mock_orch.assert_called_once()


# =============================================================================
# Health Check
# =============================================================================


@pytest.mark.anyio
async def test_webhook_health(client: AsyncClient):
    """GET /webhook/health → 200 com status básico."""
    response = await client.get(HEALTH_URL)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "webhook"
    assert "redis" in data


@pytest.mark.anyio
async def test_webhook_health_redis_ok(client: AsyncClient):
    """GET /webhook/health com Redis saudável → redis: ok."""
    mock_redis = MagicMock()
    mock_redis.ping.return_value = True

    with patch("app.api.routes.v1.webhook._get_redis", return_value=mock_redis):
        response = await client.get(HEALTH_URL)

        assert response.status_code == 200
        data = response.json()
        assert data["redis"] == "ok"


@pytest.mark.anyio
async def test_webhook_health_redis_unavailable(client: AsyncClient):
    """GET /webhook/health com Redis indisponível → redis: unavailable."""
    with patch("app.api.routes.v1.webhook._get_redis", return_value=None):
        response = await client.get(HEALTH_URL)

        assert response.status_code == 200
        data = response.json()
        assert data["redis"] == "unavailable"
