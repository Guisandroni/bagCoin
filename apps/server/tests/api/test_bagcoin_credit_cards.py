"""Tests for /bagcoin/credit-cards/ REST endpoints."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

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


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


def _mock_credit_card_dict(**kwargs) -> dict:
    """Return a mock credit card response dict."""
    now = kwargs.get("created_at", datetime.now(UTC))
    card_id = kwargs.get("id", 1)
    user_id = kwargs.get("user_id", 1)
    return {
        "id": str(card_id) if False else card_id,
        "user_id": str(user_id) if False else user_id,
        "name": kwargs.get("name", "Nubank"),
        "issuer": kwargs.get("issuer", "visa"),
        "limit": kwargs.get("limit", 5000.0),
        "closing_day": kwargs.get("closing_day", 10),
        "due_day": kwargs.get("due_day", 20),
        "color": kwargs.get("color", "#820AD1"),
        "active": kwargs.get("active", True),
        "created_at": now.isoformat() if hasattr(now, "isoformat") else now,
        "updated_at": kwargs.get("updated_at", now).isoformat()
        if hasattr(kwargs.get("updated_at", now), "isoformat")
        else kwargs.get("updated_at", now),
    }


# ---------------------------------------------------------------------------
# Auth-guard tests – unauthenticated requests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_list_credit_cards_requires_auth(client):
    """Test that listing credit cards requires auth."""
    response = await client.get(f"{settings.API_V1_STR}/bagcoin/credit-cards")
    assert response.status_code == 401


@pytest.mark.anyio
async def test_create_credit_card_requires_auth(client):
    """Test that creating a credit card requires auth."""
    response = await client.post(
        f"{settings.API_V1_STR}/bagcoin/credit-cards",
        json={"name": "Nubank", "issuer": "visa", "limit": 5000.0, "closing_day": 10, "due_day": 20},
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
    response = await client.delete(f"{settings.API_V1_STR}/bagcoin/credit-cards/{1}")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# List credit cards
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
    cards_data = [
        _mock_credit_card_dict(
            id=1, name="Nubank", issuer="visa", limit=5000.0, user_id=mock_user.id
        ),
        _mock_credit_card_dict(
            id=1, name="Inter", issuer="mastercard", limit=3000.0, user_id=mock_user.id, color="#FF6600"
        ),
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
    assert len(data) == 2
    assert data[0]["name"] == "Nubank"
    assert data[0]["issuer"] == "visa"
    assert data[1]["name"] == "Inter"
    assert data[1]["issuer"] == "mastercard"


# ---------------------------------------------------------------------------
# Create credit card
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_create_credit_card(client_with_auth, mock_user):
    """Test creating a credit card returns 201."""
    fake_id = 1
    now = datetime.now(UTC)

    with patch(
        "app.api.routes.v1.credit_cards.cc_service.create_credit_card",
        new_callable=AsyncMock,
    ) as mock_create:
        mock_create.return_value = _mock_credit_card_dict(
            id=fake_id,
            name="Nubank",
            issuer="visa",
            limit=5000.0,
            closing_day=10,
            due_day=20,
            user_id=mock_user.id,
            created_at=now,
        )

        response = await client_with_auth.post(
            f"{settings.API_V1_STR}/bagcoin/credit-cards",
            json={
                "name": "Nubank",
                "issuer": "visa",
                "limit": 5000.0,
                "closing_day": 10,
                "due_day": 20,
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Nubank"
    assert data["issuer"] == "visa"
    assert data["limit"] == 5000.0
    assert data["closing_day"] == 10
    assert data["due_day"] == 20


@pytest.mark.anyio
async def test_create_credit_card_invalid_data(client_with_auth):
    """Test creating a credit card with invalid data returns 422."""
    response = await client_with_auth.post(
        f"{settings.API_V1_STR}/bagcoin/credit-cards",
        json={"name": "", "issuer": "", "limit": -100, "closing_day": 32, "due_day": 0},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Get credit card
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_get_credit_card(client_with_auth, mock_user):
    """Test getting a specific credit card."""
    card_id = 1
    card_data = _mock_credit_card_dict(
        id=card_id,
        name="Nubank",
        issuer="visa",
        limit=5000.0,
        closing_day=10,
        due_day=20,
        user_id=mock_user.id,
    )

    with patch(
        "app.api.routes.v1.credit_cards.cc_service.get_credit_card",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = card_data

        response = await client_with_auth.get(
            f"{settings.API_V1_STR}/bagcoin/credit-cards/{card_id}"
        )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(card_id)
    assert data["name"] == "Nubank"
    assert data["issuer"] == "visa"
    assert data["limit"] == 5000.0


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


# ---------------------------------------------------------------------------
# Update credit card
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_update_credit_card(client_with_auth, mock_user):
    """Test updating a credit card."""
    card_id = 1
    updated_data = _mock_credit_card_dict(
        id=card_id,
        name="Updated Card",
        issuer="mastercard",
        limit=8000.0,
        closing_day=15,
        due_day=25,
        color="#000000",
        user_id=mock_user.id,
    )

    with patch(
        "app.api.routes.v1.credit_cards.cc_service.update_credit_card",
        new_callable=AsyncMock,
    ) as mock_update:
        mock_update.return_value = updated_data

        response = await client_with_auth.patch(
            f"{settings.API_V1_STR}/bagcoin/credit-cards/{card_id}",
            json={
                "name": "Updated Card",
                "issuer": "mastercard",
                "limit": 8000.0,
                "closing_day": 15,
                "due_day": 25,
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Card"
    assert data["issuer"] == "mastercard"
    assert data["limit"] == 8000.0


# ---------------------------------------------------------------------------
# Delete credit card
# ---------------------------------------------------------------------------


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
