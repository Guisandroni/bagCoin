"""Tests for /bagcoin/accounts/ REST endpoints."""

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


def _mock_account_dict(**kwargs) -> dict:
    """Return a mock account response dict."""
    now = kwargs.get("created_at", datetime.now(UTC))
    account_id = kwargs.get("id", 1)
    user_id = kwargs.get("user_id", 1)
    return {
        "id": str(account_id) if False else account_id,
        "user_id": str(user_id) if False else user_id,
        "name": kwargs.get("name", "Nubank"),
        "bank": kwargs.get("bank", "Nubank"),
        "type": kwargs.get("type", "CHECKING"),
        "balance": kwargs.get("balance", 1000.0),
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
async def test_list_accounts_requires_auth(client):
    """Test that listing accounts requires auth."""
    response = await client.get(f"{settings.API_V1_STR}/bagcoin/accounts")
    assert response.status_code == 401


@pytest.mark.anyio
async def test_create_account_requires_auth(client):
    """Test that creating an account requires auth."""
    response = await client.post(
        f"{settings.API_V1_STR}/bagcoin/accounts",
        json={"name": "Nubank", "bank": "Nubank", "type": "CHECKING"},
    )
    assert response.status_code == 401


@pytest.mark.anyio
async def test_get_account_requires_auth(client):
    """Test that getting an account requires auth."""
    response = await client.get(f"{settings.API_V1_STR}/bagcoin/accounts/{1}")
    assert response.status_code == 401


@pytest.mark.anyio
async def test_update_account_requires_auth(client):
    """Test that updating an account requires auth."""
    response = await client.patch(
        f"{settings.API_V1_STR}/bagcoin/accounts/{1}",
        json={"name": "Updated"},
    )
    assert response.status_code == 401


@pytest.mark.anyio
async def test_delete_account_requires_auth(client):
    """Test that deleting an account requires auth."""
    response = await client.delete(f"{settings.API_V1_STR}/bagcoin/accounts/{1}")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# List accounts
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_list_accounts_empty(client_with_auth):
    """Test listing accounts when empty."""
    with patch(
        "app.api.routes.v1.accounts.account_service.list_accounts",
        new_callable=AsyncMock,
    ) as mock_list:
        mock_list.return_value = []

        response = await client_with_auth.get(f"{settings.API_V1_STR}/bagcoin/accounts")

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.anyio
async def test_list_accounts_with_data(client_with_auth, mock_user):
    """Test listing accounts with data."""
    accounts_data = [
        _mock_account_dict(id=1, name="Nubank", bank="Nubank", balance=1500.0, user_id=mock_user.id),
        _mock_account_dict(id=1, name="Itaú", bank="Itaú", balance=5000.0, user_id=mock_user.id, color="#003399"),
    ]

    with patch(
        "app.api.routes.v1.accounts.account_service.list_accounts",
        new_callable=AsyncMock,
    ) as mock_list:
        mock_list.return_value = accounts_data

        response = await client_with_auth.get(f"{settings.API_V1_STR}/bagcoin/accounts")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["name"] == "Nubank"
    assert data[0]["bank"] == "Nubank"
    assert data[1]["name"] == "Itaú"


# ---------------------------------------------------------------------------
# Create account
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_create_account(client_with_auth, mock_user):
    """Test creating an account returns 201."""
    fake_id = 1
    now = datetime.now(UTC)

    with patch(
        "app.api.routes.v1.accounts.account_service.create_account",
        new_callable=AsyncMock,
    ) as mock_create:
        mock_create.return_value = _mock_account_dict(
            id=fake_id,
            name="Nu Conta",
            bank="Nubank",
            balance=500.0,
            user_id=mock_user.id,
            created_at=now,
        )

        response = await client_with_auth.post(
            f"{settings.API_V1_STR}/bagcoin/accounts",
            json={
                "name": "Nu Conta",
                "bank": "Nubank",
                "type": "CHECKING",
                "balance": 500.0,
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Nu Conta"
    assert data["balance"] == 500.0


@pytest.mark.anyio
async def test_create_account_invalid_data(client_with_auth):
    """Test creating an account with invalid data returns 422."""
    response = await client_with_auth.post(
        f"{settings.API_V1_STR}/bagcoin/accounts",
        json={"name": "", "bank": "", "type": "INVALID"},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Get account
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_get_account(client_with_auth, mock_user):
    """Test getting a specific account."""
    account_id = 1
    account_data = _mock_account_dict(
        id=account_id,
        name="Nubank",
        bank="Nubank",
        balance=2000.0,
        user_id=mock_user.id,
    )

    with patch(
        "app.api.routes.v1.accounts.account_service.get_account",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = account_data

        response = await client_with_auth.get(
            f"{settings.API_V1_STR}/bagcoin/accounts/{account_id}"
        )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(account_id)
    assert data["name"] == "Nubank"


@pytest.mark.anyio
async def test_get_account_not_found(client_with_auth):
    """Test getting a non-existent account returns 404."""
    from app.core.exceptions import NotFoundError

    with patch(
        "app.api.routes.v1.accounts.account_service.get_account",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.side_effect = NotFoundError(
            message="Account not found", details={"id": str(1)}
        )

        response = await client_with_auth.get(
            f"{settings.API_V1_STR}/bagcoin/accounts/{1}"
        )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


# ---------------------------------------------------------------------------
# Update account
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_update_account(client_with_auth, mock_user):
    """Test updating an account."""
    account_id = 1
    updated_data = _mock_account_dict(
        id=account_id,
        name="Updated Account",
        bank="Nubank",
        type="SAVINGS",
        balance=3000.0,
        color="#000000",
        user_id=mock_user.id,
    )

    with patch(
        "app.api.routes.v1.accounts.account_service.update_account",
        new_callable=AsyncMock,
    ) as mock_update:
        mock_update.return_value = updated_data

        response = await client_with_auth.patch(
            f"{settings.API_V1_STR}/bagcoin/accounts/{account_id}",
            json={
                "name": "Updated Account",
                "balance": 3000.0,
                "type": "SAVINGS",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Account"
    assert data["balance"] == 3000.0
    assert data["type"] == "SAVINGS"


# ---------------------------------------------------------------------------
# Delete account
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_delete_account(client_with_auth):
    """Test deleting an account returns 204."""
    with patch(
        "app.api.routes.v1.accounts.account_service.delete_account",
        new_callable=AsyncMock,
    ) as mock_delete:
        mock_delete.return_value = None

        response = await client_with_auth.delete(
            f"{settings.API_V1_STR}/bagcoin/accounts/{1}"
        )

    assert response.status_code == 204


@pytest.mark.anyio
async def test_delete_account_not_found(client_with_auth):
    """Test deleting a non-existent account returns 404."""
    from app.core.exceptions import NotFoundError

    with patch(
        "app.api.routes.v1.accounts.account_service.delete_account",
        new_callable=AsyncMock,
    ) as mock_delete:
        mock_delete.side_effect = NotFoundError(
            message="Account not found", details={"id": str(1)}
        )

        response = await client_with_auth.delete(
            f"{settings.API_V1_STR}/bagcoin/accounts/{1}"
        )

    assert response.status_code == 404
