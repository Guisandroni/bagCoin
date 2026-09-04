"""Tests for CreditCard REST endpoints."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

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


class MockCreditCard:
    """Mock credit card for testing."""

    def __init__(self, **kwargs):
        self.id = kwargs.get("id", 1)
        self.user_id = kwargs.get("user_id", 1)
        self.name = kwargs.get("name", "Nubank")
        self.issuer = kwargs.get("issuer", "visa")
        self.limit = kwargs.get("limit", 5000.0)
        self.closing_day = kwargs.get("closing_day", 10)
        self.due_day = kwargs.get("due_day", 20)
        self.color = kwargs.get("color", "#820AD1")
        self.active = kwargs.get("active", True)
        self.created_at = kwargs.get("created_at", datetime.now(UTC))
        self.updated_at = kwargs.get("updated_at", datetime.now(UTC))


@pytest.fixture
def mock_user():
    return MockUser()


@pytest.fixture
def mock_card():
    return MockCreditCard()


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
# Auth-guard tests – unauthenticated requests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_list_credit_cards_requires_auth(client):
    """Test that unauthenticated requests are rejected."""
    response = await client.get(f"{settings.API_V1_STR}/bagcoin/credit-cards")
    assert response.status_code == 401


@pytest.mark.anyio
async def test_create_credit_card_requires_auth(client):
    """Test that creating a credit card requires auth."""
    response = await client.post(
        f"{settings.API_V1_STR}/bagcoin/credit-cards",
        json={
            "name": "Nubank",
            "issuer": "visa",
            "limit": 5000.0,
            "closing_day": 10,
            "due_day": 20,
        },
    )
    assert response.status_code == 401


@pytest.mark.anyio
async def test_get_credit_card_requires_auth(client):
    """Test that getting a credit card requires auth."""
    response = await client.get(f"{settings.API_V1_STR}/bagcoin/credit-cards/{1}")
    assert response.status_code == 401


@pytest.mark.anyio
async def test_update_credit_card_requires_auth(client):
    """Test that updating a credit card requires auth."""
    response = await client.patch(
        f"{settings.API_V1_STR}/bagcoin/credit-cards/{1}",
        json={"name": "Updated"},
    )
    assert response.status_code == 401


@pytest.mark.anyio
async def test_delete_credit_card_requires_auth(client):
    """Test that deleting a credit card requires auth."""
    response = await client.delete(
        f"{settings.API_V1_STR}/bagcoin/credit-cards/{1}"
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# CRUD tests – authenticated
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_list_credit_cards_empty(client_with_auth):
    """Test listing credit cards when empty."""
    with patch(
        "app.api.routes.v1.credit_cards.cc_service.list_credit_cards",
        new_callable=AsyncMock,
    ) as mock_list:
        mock_list.return_value = []

        response = await client_with_auth.get(
            f"{settings.API_V1_STR}/bagcoin/credit-cards"
        )

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.anyio
async def test_list_credit_cards_with_data(client_with_auth, mock_user):
    """Test listing credit cards with data."""
    fake_id = 1
    now = datetime.now(UTC)
    cards_data = [
        {
            "id": str(fake_id),
            "user_id": str(mock_user.id),
            "name": "Nubank",
            "issuer": "visa",
            "limit": 5000.0,
            "closing_day": 10,
            "due_day": 20,
            "color": "#820AD1",
            "active": True,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
    ]

    with patch(
        "app.api.routes.v1.credit_cards.cc_service.list_credit_cards",
        new_callable=AsyncMock,
    ) as mock_list:
        mock_list.return_value = cards_data

        response = await client_with_auth.get(
            f"{settings.API_V1_STR}/bagcoin/credit-cards"
        )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Nubank"
    assert data[0]["issuer"] == "visa"
    assert data[0]["limit"] == 5000.0
    assert data[0]["closing_day"] == 10
    assert data[0]["due_day"] == 20
    assert data[0]["active"] is True


@pytest.mark.anyio
async def test_create_credit_card_201(client_with_auth, mock_user):
    """Test creating a credit card returns 201."""
    fake_id = 1
    now = datetime.now(UTC)

    with patch(
        "app.api.routes.v1.credit_cards.cc_service.create_credit_card",
        new_callable=AsyncMock,
    ) as mock_create:
        mock_create.return_value = {
            "id": str(fake_id),
            "user_id": str(mock_user.id),
            "name": "Inter Black",
            "issuer": "mastercard",
            "limit": 8000.0,
            "closing_day": 15,
            "due_day": 25,
            "color": "#000000",
            "active": True,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

        response = await client_with_auth.post(
            f"{settings.API_V1_STR}/bagcoin/credit-cards",
            json={
                "name": "Inter Black",
                "issuer": "mastercard",
                "limit": 8000.0,
                "closing_day": 15,
                "due_day": 25,
                "color": "#000000",
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Inter Black"
    assert data["limit"] == 8000.0
    assert data["closing_day"] == 15
    assert data["due_day"] == 25


@pytest.mark.anyio
async def test_create_credit_card_invalid_data(client_with_auth):
    """Test creating a credit card with invalid data returns 422."""
    response = await client_with_auth.post(
        f"{settings.API_V1_STR}/bagcoin/credit-cards",
        json={
            "name": "",
            "issuer": "",
            "limit": -1,
            "closing_day": 0,
            "due_day": 32,
        },
    )
    assert response.status_code == 422


@pytest.mark.anyio
async def test_get_credit_card(client_with_auth, mock_user):
    """Test getting a specific credit card."""
    card_id = 1
    now = datetime.now(UTC)

    with patch(
        "app.api.routes.v1.credit_cards.cc_service.get_credit_card",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = {
            "id": str(card_id),
            "user_id": str(mock_user.id),
            "name": "Nubank",
            "issuer": "visa",
            "limit": 5000.0,
            "closing_day": 10,
            "due_day": 20,
            "color": "#820AD1",
            "active": True,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

        response = await client_with_auth.get(
            f"{settings.API_V1_STR}/bagcoin/credit-cards/{card_id}"
        )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(card_id)
    assert data["name"] == "Nubank"


@pytest.mark.anyio
async def test_get_credit_card_not_found(client_with_auth):
    """Test getting a non-existent credit card returns 404."""
    from app.core.exceptions import NotFoundError

    with patch(
        "app.api.routes.v1.credit_cards.cc_service.get_credit_card",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.side_effect = NotFoundError(
            message="Credit card not found", details={"id": str(1)}
        )

        response = await client_with_auth.get(
            f"{settings.API_V1_STR}/bagcoin/credit-cards/{1}"
        )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.anyio
async def test_update_credit_card(client_with_auth, mock_user):
    """Test updating a credit card."""
    card_id = 1
    now = datetime.now(UTC)

    with patch(
        "app.api.routes.v1.credit_cards.cc_service.update_credit_card",
        new_callable=AsyncMock,
    ) as mock_update:
        mock_update.return_value = {
            "id": str(card_id),
            "user_id": str(mock_user.id),
            "name": "Updated Card",
            "issuer": "amex",
            "limit": 10000.0,
            "closing_day": 5,
            "due_day": 15,
            "color": "#FFFFFF",
            "active": False,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

        response = await client_with_auth.patch(
            f"{settings.API_V1_STR}/bagcoin/credit-cards/{card_id}",
            json={
                "name": "Updated Card",
                "issuer": "amex",
                "limit": 10000.0,
                "active": False,
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Card"
    assert data["issuer"] == "amex"
    assert data["limit"] == 10000.0
    assert data["active"] is False


@pytest.mark.anyio
async def test_update_credit_card_not_found(client_with_auth):
    """Test updating a non-existent credit card returns 404."""
    from app.core.exceptions import NotFoundError

    with patch(
        "app.api.routes.v1.credit_cards.cc_service.update_credit_card",
        new_callable=AsyncMock,
    ) as mock_update:
        mock_update.side_effect = NotFoundError(
            message="Credit card not found", details={"id": str(1)}
        )

        response = await client_with_auth.patch(
            f"{settings.API_V1_STR}/bagcoin/credit-cards/{1}",
            json={"name": "Ghost"},
        )

    assert response.status_code == 404


@pytest.mark.anyio
async def test_delete_credit_card(client_with_auth):
    """Test deleting a credit card returns 204."""
    with patch(
        "app.api.routes.v1.credit_cards.cc_service.delete_credit_card",
        new_callable=AsyncMock,
    ) as mock_delete:
        mock_delete.return_value = None

        response = await client_with_auth.delete(
            f"{settings.API_V1_STR}/bagcoin/credit-cards/{1}"
        )

    assert response.status_code == 204


@pytest.mark.anyio
async def test_delete_credit_card_not_found(client_with_auth):
    """Test deleting a non-existent credit card returns 404."""
    from app.core.exceptions import NotFoundError

    with patch(
        "app.api.routes.v1.credit_cards.cc_service.delete_credit_card",
        new_callable=AsyncMock,
    ) as mock_delete:
        mock_delete.side_effect = NotFoundError(
            message="Credit card not found", details={"id": str(1)}
        )

        response = await client_with_auth.delete(
            f"{settings.API_V1_STR}/bagcoin/credit-cards/{1}"
        )

    assert response.status_code == 404
