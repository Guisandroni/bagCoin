"""Sync flow integration tests: webhook -> confirmation -> dashboard.

Tests the full lifecycle of a transaction:
1. Webhook receives a message -> orchestrator creates a pending transaction
2. Pending message appears in the pending list
3. User confirms the transaction
4. Confirmed transaction appears in the dashboard summary

All tests use mocked dependencies — no real DB required.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_user, get_db_session, get_redis
from app.core.config import settings
from app.main import app

WHATSAPP_URL = f"{settings.API_V1_STR}/webhook/whatsapp"
WHATSAPP_HEADERS = {"X-API-Key": settings.WHATSAPP_API_KEY}

BASE_CONVERSATIONS = f"{settings.API_V1_STR}/bagcoin/conversations"
TRANSACTIONS_URL = f"{settings.API_V1_STR}/bagcoin/transactions"


# =============================================================================
# Fixtures
# =============================================================================


class MockUser:
    """Mock authenticated user matching the User ORM model."""

    def __init__(self):
        self.id = 1
        self.email = "test@example.com"
        self.full_name = "Test User"
        self.is_active = True
        self.role = "user"
        self.phone_number = "+551****9999"
        self.google_id = None
        self.auth_provider = "email"
        self.avatar_url = None
        self.created_at = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)


@pytest.fixture
def mock_user():
    return MockUser()


@pytest.fixture
async def client_with_auth(mock_user, mock_redis, mock_db_session):
    """Client with authenticated user override."""

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_redis] = lambda: mock_redis
    app.dependency_overrides[get_db_session] = lambda: mock_db_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# =============================================================================
# Helpers: mock ORM objects
# =============================================================================


def _mock_transaction(**kwargs) -> MagicMock:
    """Return a mock Transaction ORM object."""
    tx = MagicMock()
    tx.id = kwargs.get("id", 1)
    tx.type = kwargs.get("type", "EXPENSE")
    tx.amount = kwargs.get("amount", 99.90)
    tx.currency = kwargs.get("currency", "BRL")
    tx.description = kwargs.get("description", "Supermarket purchase")
    tx.source_format = kwargs.get("source_format", "text")
    tx.transaction_date = kwargs.get("transaction_date", datetime.now(UTC))
    tx.raw_input = kwargs.get("raw_input", "gastou 99,90 no mercado")
    tx.confidence_score = kwargs.get("confidence_score", 0.5)
    tx.user_id = kwargs.get("user_id", 1)
    tx.created_at = kwargs.get("created_at", datetime.now(UTC))
    tx.updated_at = kwargs.get("updated_at", datetime.now(UTC))
    return tx


# =============================================================================
# Test: Webhook creates a pending transaction
# =============================================================================


@pytest.mark.anyio
async def test_sync_webhook_creates_pending_transaction(client: AsyncClient):
    """POST /webhook/whatsapp com mensagem financeira -> pending transaction criada.

    Mocks the orchestrator to simulate extracting a transaction
    with low confidence (pending).
    """
    with (
        patch("app.api.routes.v1.webhook.is_duplicate_message", return_value=False),
        patch("app.api.routes.v1.webhook.orchestrator.invoke") as mock_orch,
    ):
        # Orchestrator returns state indicating a transaction was recorded
        mock_orch.return_value = {
            "response": "Registrei uma despesa de R$ 99,90 no mercado, mas não tenho certeza. Confirma?",
            "extracted_data": {
                "type": "EXPENSE",
                "amount": 99.90,
                "description": "Mercado",
                "confidence": 0.45,
            },
        }

        payload = {
            "phone_number": "5511999999999",
            "message": "gastou 99,90 no mercado",
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
        assert "Confirma" in data["reply"]
        assert data["document"] is None

        # Verify the orchestrator was called with the expected state
        mock_orch.assert_called_once()
        call_state = mock_orch.call_args[0][0]
        assert call_state["phone_number"] == "5511999999999"
        assert call_state["message"] == "gastou 99,90 no mercado"
        assert call_state["source_format"] == "text"


# =============================================================================
# Test: Pending transaction appears in pending list
# =============================================================================


@pytest.mark.anyio
async def test_sync_pending_appears_in_pending_list(
    client_with_auth: AsyncClient, mock_db_session: AsyncMock, mock_user: MockUser
):
    """GET /bagcoin/conversations/pending mostra transacao com confidence < 0.7."""
    now = datetime.now(UTC)
    tx = _mock_transaction(
        id=1,
        type="EXPENSE",
        amount=99.90,
        description="Mercado",
        confidence_score=0.45,
        source_format="text",
        raw_input="gastou 99,90 no mercado",
        transaction_date=now,
        created_at=now,
        user_id=mock_user.id,
    )

    pending_result = MagicMock()
    pending_result.scalars.return_value.all.return_value = [tx]

    mock_db_session.execute = AsyncMock(return_value=pending_result)

    response = await client_with_auth.get(f"{BASE_CONVERSATIONS}/pending")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == 1
    assert data[0]["type"] == "EXPENSE"
    assert data[0]["amount"] == 99.90
    assert data[0]["description"] == "Mercado"
    assert data[0]["source_format"] == "text"
    assert data[0]["raw_input"] == "gastou 99,90 no mercado"


# =============================================================================
# Test: Confirm a pending transaction
# =============================================================================


@pytest.mark.anyio
async def test_sync_confirm_pending_transaction(
    client_with_auth: AsyncClient, mock_db_session: AsyncMock, mock_user: MockUser
):
    """PATCH /bagcoin/conversations/{conv_id}/messages/{tx_id}/confirm -> confidence=1.0."""
    tx = _mock_transaction(
        id=1,
        confidence_score=0.45,
        user_id=mock_user.id,
    )

    tx_result = MagicMock()
    tx_result.scalar_one_or_none.return_value = tx

    mock_db_session.execute = AsyncMock(return_value=tx_result)

    response = await client_with_auth.patch(
        f"{BASE_CONVERSATIONS}/1/messages/1/confirm"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["status"] == "confirmed"
    assert data["message"] == "Transaction confirmed successfully"

    # Verify the transaction was updated
    assert tx.confidence_score == 1.0
    mock_db_session.add.assert_called_once_with(tx)
    mock_db_session.flush.assert_awaited_once()
    mock_db_session.refresh.assert_awaited_once_with(tx)


# =============================================================================
# Test: Confirmed transaction appears in summary
# =============================================================================


@pytest.mark.anyio
async def test_sync_confirmed_appears_in_summary(
    client_with_auth: AsyncClient, mock_db_session: AsyncMock, mock_user: MockUser
):
    """GET /bagcoin/transactions/summary inclui transacao confirmada."""
    now = datetime.now(UTC)
    tx = _mock_transaction(
        id=1,
        type="EXPENSE",
        amount=99.90,
        description="Mercado",
        confidence_score=1.0,  # confirmed
        source_format="text",
        transaction_date=now,
        created_at=now,
        user_id=mock_user.id,
    )

    # get_summary() executes a simple select(Transaction).where(...)
    result = MagicMock()
    result.scalars.return_value.all.return_value = [tx]

    mock_db_session.execute = AsyncMock(return_value=result)

    response = await client_with_auth.get(f"{TRANSACTIONS_URL}/summary")

    assert response.status_code == 200
    data = response.json()
    assert data["transaction_count"] == 1
    assert data["total_expenses"] == 99.90
    assert data["total_income"] == 0.0
    assert data["balance"] == -99.90
    assert len(data["recent_transactions"]) == 1
    assert data["recent_transactions"][0]["status"] == "confirmed"
    assert data["recent_transactions"][0]["name"] == "Mercado"


# =============================================================================
# Test: Confirm wrong user returns 404
# =============================================================================


@pytest.mark.anyio
async def test_sync_confirm_wrong_user_returns_404(
    client_with_auth: AsyncClient, mock_db_session: AsyncMock
):
    """PATCH confirm de transacao de outro usuario -> 404."""
    # Transaction belongs to a different user -> query returns None
    tx_result = MagicMock()
    tx_result.scalar_one_or_none.return_value = None

    mock_db_session.execute = AsyncMock(return_value=tx_result)

    response = await client_with_auth.patch(
        f"{BASE_CONVERSATIONS}/1/messages/999/confirm"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Transaction not found"


# =============================================================================
# Test: Full flow webhook -> pending -> confirm -> summary
# =============================================================================


@pytest.mark.anyio
async def test_sync_full_flow_webhook_to_summary(
    client: AsyncClient,
    client_with_auth: AsyncClient,
    mock_db_session: AsyncMock,
    mock_user: MockUser,
):
    """Fluxo completo: webhook cria transacao -> aparece pending ->
    usuario confirma -> aparece no summary."""
    now = datetime.now(UTC)

    # ---- Step 1: Webhook recebe mensagem ----
    with (
        patch("app.api.routes.v1.webhook.is_duplicate_message", return_value=False),
        patch("app.api.routes.v1.webhook.orchestrator.invoke") as mock_orch,
    ):
        mock_orch.return_value = {
            "response": "Registrei R$ 199,90 no supermercado, mas não tenho certeza. Confirma?",
            "extracted_data": {
                "type": "EXPENSE",
                "amount": 199.90,
                "description": "Supermercado",
                "confidence": 0.35,
            },
        }

        wh_response = await client.post(
            WHATSAPP_URL,
            json={
                "phone_number": "5511999999999",
                "message": "gastou 199,90 no supermercado",
                "type": "chat",
                "timestamp": 1234567890,
            },
            headers=WHATSAPP_HEADERS,
        )

        assert wh_response.status_code == 200
        assert "Confirma" in wh_response.json()["reply"]

    # ---- Step 2: Pending aparece na lista ----
    tx = _mock_transaction(
        id=1,
        type="EXPENSE",
        amount=199.90,
        description="Supermercado",
        confidence_score=0.35,
        source_format="text",
        raw_input="gastou 199,90 no supermercado",
        transaction_date=now,
        created_at=now,
        user_id=mock_user.id,
    )

    pending_result = MagicMock()
    pending_result.scalars.return_value.all.return_value = [tx]
    mock_db_session.execute = AsyncMock(return_value=pending_result)

    pending_response = await client_with_auth.get(
        f"{BASE_CONVERSATIONS}/pending"
    )

    assert pending_response.status_code == 200
    pending_data = pending_response.json()
    assert len(pending_data) == 1
    assert pending_data[0]["id"] == 1
    assert pending_data[0]["amount"] == 199.90

    # ---- Step 3: Usuario confirma ----
    tx_result = MagicMock()
    tx_result.scalar_one_or_none.return_value = tx
    mock_db_session.execute = AsyncMock(return_value=tx_result)

    confirm_response = await client_with_auth.patch(
        f"{BASE_CONVERSATIONS}/1/messages/1/confirm"
    )

    assert confirm_response.status_code == 200
    assert confirm_response.json()["status"] == "confirmed"
    assert tx.confidence_score == 1.0  # foi atualizado

    # ---- Step 4: Summary mostra a transacao confirmada ----
    # Agora a transacao tem confidence=1.0
    tx.confidence_score = 1.0
    summary_result = MagicMock()
    summary_result.scalars.return_value.all.return_value = [tx]
    mock_db_session.execute = AsyncMock(return_value=summary_result)

    summary_response = await client_with_auth.get(
        f"{TRANSACTIONS_URL}/summary"
    )

    assert summary_response.status_code == 200
    summary_data = summary_response.json()
    assert summary_data["transaction_count"] == 1
    assert summary_data["total_expenses"] == 199.90
    assert len(summary_data["recent_transactions"]) == 1
    rt = summary_data["recent_transactions"][0]
    assert rt["name"] == "Supermercado"
    assert rt["status"] == "confirmed"
    assert rt["amount"] == 199.90
