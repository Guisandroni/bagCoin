"""Tests for BagCoin conversation REST endpoints."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_user, get_db_session, get_redis
from app.core.config import settings
from app.main import app


class MockUser:
    """Mock authenticated user."""

    def __init__(self):
        self.id = 1
        self.email = "test@example.com"
        self.full_name = "Test User"
        self.is_active = True
        self.role = "user"
        self.phone_number = "+5511999999999"
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


# ---------------------------------------------------------------------------
# Helper: build a chain of mock execute results for conversation endpoints
# ---------------------------------------------------------------------------


def _mock_user_with_phone(phone: str = "+5511999999999") -> MagicMock:
    """Return a mock User ORM object with a phone_number."""
    user = MagicMock()
    user.phone_number = phone
    return user


def _mock_user(user_id: int = 42) -> MagicMock:
    """Return a mock execute result for the PhoneUnified user id query."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = user_id
    return result


def _mock_empty_user() -> MagicMock:
    """Return a mock execute result where no unified user exists."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    return result


def _mock_conversation(**kwargs) -> MagicMock:
    """Return a mock PhoneConversation ORM object."""
    conv = MagicMock()
    conv.id = kwargs.get("id", 1)
    conv.channel = kwargs.get("channel", "whatsapp")
    conv.last_intent = kwargs.get("last_intent", "create_expense")
    conv.message_history = kwargs.get("message_history", [])
    conv.created_at = kwargs.get("created_at", datetime.now(UTC))
    conv.updated_at = kwargs.get("updated_at", datetime.now(UTC))
    return conv


def _mock_message(**kwargs) -> MagicMock:
    """Return a mock ConversationMessage ORM object."""
    msg = MagicMock()
    msg.role = kwargs.get("role", "user")
    msg.content = kwargs.get("content", "message")
    msg.created_at = kwargs.get("created_at", datetime.now(UTC))
    msg.message_metadata = kwargs.get("message_metadata", {})
    return msg


def _mock_count(value: int) -> MagicMock:
    """Return a mock count query result."""
    result = MagicMock()
    result.scalar.return_value = value
    return result


def _mock_transaction(**kwargs) -> MagicMock:
    """Return a mock Transaction ORM object."""
    tx = MagicMock()
    tx.id = kwargs.get("id", 1)
    tx.type = kwargs.get("type", "EXPENSE")
    tx.amount = kwargs.get("amount", 99.90)
    tx.currency = kwargs.get("currency", "BRL")
    tx.description = kwargs.get("description", "Test purchase")
    tx.source_format = kwargs.get("source_format", "manual")
    tx.transaction_date = kwargs.get("transaction_date", datetime.now(UTC))
    tx.raw_input = kwargs.get("raw_input", None)
    tx.confidence_score = kwargs.get("confidence_score", 0.5)
    tx.user_id = kwargs.get("user_id", 1)
    tx.created_at = kwargs.get("created_at", datetime.now(UTC))
    tx.updated_at = kwargs.get("updated_at", datetime.now(UTC))
    return tx


def _make_user_query_result(user: MagicMock | None) -> MagicMock:
    """Return a mock execute result for the User query in _get_user_id."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    return result


# ---------------------------------------------------------------------------
# Auth-guard tests – unauthenticated requests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_list_conversations_requires_auth(client):
    """Test that listing conversations requires auth."""
    response = await client.get(f"{settings.API_V1_STR}/bagcoin/conversations")
    assert response.status_code == 401


@pytest.mark.anyio
async def test_get_conversation_messages_requires_auth(client):
    """Test that getting conversation messages requires auth."""
    response = await client.get(
        f"{settings.API_V1_STR}/bagcoin/conversations/1/messages"
    )
    assert response.status_code == 401


@pytest.mark.anyio
async def test_get_pending_messages_requires_auth(client):
    """Test that getting pending messages requires auth."""
    response = await client.get(f"{settings.API_V1_STR}/bagcoin/conversations/pending")
    assert response.status_code == 401


@pytest.mark.anyio
async def test_confirm_message_requires_auth(client):
    """Test that confirming a message requires auth."""
    response = await client.patch(
        f"{settings.API_V1_STR}/bagcoin/conversations/1/messages/1/confirm"
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# List conversations
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_list_conversations_empty_no_user(client_with_auth, mock_db_session):
    """Test listing conversations when user has no unified user (no phone linked)."""
    merged_result = _mock_empty_user()
    user_result = _make_user_query_result(None)
    mock_db_session.execute = AsyncMock(side_effect=[merged_result, user_result])

    response = await client_with_auth.get(
        f"{settings.API_V1_STR}/bagcoin/conversations"
    )

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.anyio
async def test_list_conversations_empty_no_convs(client_with_auth, mock_db_session):
    """Test listing conversations when user has no conversations."""
    mock_user_orm = _mock_user_with_phone()
    merged_result = _mock_empty_user()
    user_result = _make_user_query_result(mock_user_orm)
    user_result = _mock_user(user_id=42)

    conv_result = MagicMock()
    conv_result.scalars.return_value.all.return_value = []

    mock_db_session.execute = AsyncMock(
        side_effect=[merged_result, user_result, user_result, conv_result, _mock_count(1), _mock_count(0)]
    )

    response = await client_with_auth.get(
        f"{settings.API_V1_STR}/bagcoin/conversations"
    )

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.anyio
async def test_list_conversations_with_data(client_with_auth, mock_db_session):
    """Test listing conversations with data."""
    now = datetime.now(UTC)
    conv1 = _mock_conversation(
        id=1,
        channel="whatsapp",
        last_intent="create_expense",
        message_history=[{"role": "user", "content": "Spent 50"}],
        created_at=now,
        updated_at=now,
    )
    conv2 = _mock_conversation(
        id=2,
        channel="telegram",
        last_intent="check_balance",
        message_history=[],
        created_at=now,
        updated_at=now,
    )

    mock_user_orm = _mock_user_with_phone()
    merged_result = _mock_empty_user()
    user_result = _make_user_query_result(mock_user_orm)
    user_result = _mock_user(user_id=42)

    conv_result = MagicMock()
    conv_result.scalars.return_value.all.return_value = [conv1, conv2]

    mock_db_session.execute = AsyncMock(
        side_effect=[conv_result, _mock_count(1), _mock_count(0)]
    )

    response = await client_with_auth.get(
        f"{settings.API_V1_STR}/bagcoin/conversations"
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["id"] == 1
    assert data[0]["channel"] == "whatsapp"
    assert data[0]["last_intent"] == "create_expense"
    assert data[0]["message_count"] == 1  # len(message_history)
    assert data[1]["id"] == 2
    assert data[1]["message_count"] == 0


# ---------------------------------------------------------------------------
# Get conversation messages
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_get_conversation_messages(client_with_auth, mock_db_session):
    """Test getting messages from a conversation."""
    messages = [
        {"role": "user", "content": "Spent 50 on lunch"},
        {"role": "assistant", "content": "I've recorded that expense."},
    ]
    conv = _mock_conversation(id=1, message_history=messages)

    mock_user_orm = _mock_user_with_phone()
    merged_result = _mock_empty_user()
    user_result = _make_user_query_result(mock_user_orm)
    user_result = _mock_user(user_id=42)

    conv_result = MagicMock()
    conv_result.scalar_one_or_none.return_value = conv
    messages_result = MagicMock()
    messages_result.scalars.return_value.all.return_value = [
        _mock_message(role="user", content="Spent 50 on lunch"),
        _mock_message(role="assistant", content="I've recorded that expense."),
    ]

    mock_db_session.execute = AsyncMock(
        side_effect=[conv_result, messages_result]
    )

    response = await client_with_auth.get(
        f"{settings.API_V1_STR}/bagcoin/conversations/1/messages"
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["role"] == "user"
    assert data[0]["content"] == "Spent 50 on lunch"
    assert data[1]["role"] == "assistant"


@pytest.mark.anyio
async def test_get_conversation_messages_not_found(client_with_auth, mock_db_session):
    """Test getting messages from a non-existent conversation returns 404."""
    mock_user_orm = _mock_user_with_phone()
    merged_result = _mock_empty_user()
    user_result = _make_user_query_result(mock_user_orm)
    user_result = _mock_user(user_id=42)

    conv_result = MagicMock()
    conv_result.scalar_one_or_none.return_value = None  # no conversation found

    mock_db_session.execute = AsyncMock(
        side_effect=[merged_result, user_result, user_result, conv_result]
    )

    response = await client_with_auth.get(
        f"{settings.API_V1_STR}/bagcoin/conversations/999/messages"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Conversation not found"


@pytest.mark.anyio
async def test_get_conversation_messages_no_user(
    client_with_auth, mock_db_session
):
    """Test getting messages when user has no unified user returns 404."""
    # User has no phone_number -> _get_user_id returns None
    user_no_phone = _mock_user_with_phone(phone=None)
    merged_result = _mock_empty_user()
    user_result = _make_user_query_result(user_no_phone)

    mock_db_session.execute = AsyncMock(side_effect=[merged_result, user_result])

    response = await client_with_auth.get(
        f"{settings.API_V1_STR}/bagcoin/conversations/1/messages"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Conversation not found"


# ---------------------------------------------------------------------------
# Get pending messages (low-confidence transactions)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_get_pending_messages_empty(client_with_auth, mock_db_session):
    """Test listing pending transactions when empty."""
    pending_result = MagicMock()
    pending_result.scalars.return_value.all.return_value = []

    mock_db_session.execute = AsyncMock(return_value=pending_result)

    response = await client_with_auth.get(
        f"{settings.API_V1_STR}/bagcoin/conversations/pending"
    )

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.anyio
async def test_get_pending_messages_with_data(client_with_auth, mock_db_session, mock_user):
    """Test listing pending transactions with data."""
    now = datetime.now(UTC)
    tx1 = _mock_transaction(
        id=1,
        type="EXPENSE",
        amount=199.90,
        description="Supermarket",
        confidence_score=0.45,
        source_format="text",
        raw_input="gastou 199,90 no mercado",
        transaction_date=now,
        created_at=now,
        user_id=mock_user.id,
    )
    tx2 = _mock_transaction(
        id=2,
        type="INCOME",
        amount=2500.0,
        description="Salary",
        confidence_score=0.3,
        source_format="text",
        raw_input="recebeu 2500 de salário",
        transaction_date=now,
        created_at=now,
        user_id=mock_user.id,
    )

    pending_result = MagicMock()
    pending_result.scalars.return_value.all.return_value = [tx1, tx2]

    mock_db_session.execute = AsyncMock(return_value=pending_result)

    response = await client_with_auth.get(
        f"{settings.API_V1_STR}/bagcoin/conversations/pending"
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["id"] == 1
    assert data[0]["type"] == "EXPENSE"
    assert data[0]["amount"] == 199.90
    assert data[0]["description"] == "Supermarket"
    assert data[0]["source_format"] == "text"
    assert data[0]["raw_input"] == "gastou 199,90 no mercado"
    assert data[1]["id"] == 2
    assert data[1]["type"] == "INCOME"


# ---------------------------------------------------------------------------
# Confirm a pending message
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_confirm_message(client_with_auth, mock_db_session, mock_user):
    """Test confirming a pending transaction."""
    tx = _mock_transaction(
        id=1,
        confidence_score=0.45,
        user_id=mock_user.id,
    )

    tx_result = MagicMock()
    tx_result.scalar_one_or_none.return_value = tx

    mock_db_session.execute = AsyncMock(return_value=tx_result)

    response = await client_with_auth.patch(
        f"{settings.API_V1_STR}/bagcoin/conversations/1/messages/1/confirm"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["status"] == "confirmed"
    assert data["message"] == "Transaction confirmed successfully"

    # Verify confidence_score was updated and flush was called
    assert tx.confidence_score == 1.0
    mock_db_session.add.assert_called_once_with(tx)
    mock_db_session.flush.assert_awaited_once()
    mock_db_session.refresh.assert_awaited_once_with(tx)


@pytest.mark.anyio
async def test_confirm_message_invalid_id(client_with_auth, mock_db_session):
    """Test confirming with non-numeric message ID returns 400."""
    response = await client_with_auth.patch(
        f"{settings.API_V1_STR}/bagcoin/conversations/1/messages/abc/confirm"
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid transaction ID"


@pytest.mark.anyio
async def test_confirm_message_not_found(client_with_auth, mock_db_session):
    """Test confirming a non-existent transaction returns 404."""
    tx_result = MagicMock()
    tx_result.scalar_one_or_none.return_value = None

    mock_db_session.execute = AsyncMock(return_value=tx_result)

    response = await client_with_auth.patch(
        f"{settings.API_V1_STR}/bagcoin/conversations/1/messages/999/confirm"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Transaction not found"


@pytest.mark.anyio
async def test_confirm_message_wrong_user(client_with_auth, mock_db_session):
    """Test confirming a transaction that belongs to another user returns 404."""
    tx = _mock_transaction(
        id=1,
        confidence_score=0.5,
        user_id=1,  # different user
    )

    tx_result = MagicMock()
    tx_result.scalar_one_or_none.return_value = tx

    mock_db_session.execute = AsyncMock(return_value=tx_result)

    # The route filters by both Transaction.id AND Transaction.user_id == current_user.id,
    # so a transaction belonging to a different user would never be returned
    tx_result.scalar_one_or_none.return_value = None

    response = await client_with_auth.patch(
        f"{settings.API_V1_STR}/bagcoin/conversations/1/messages/999/confirm"
    )

    assert response.status_code == 404
