"""Tests for Account REST endpoints."""

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


class MockAccount:
    """Mock account for testing."""

    def __init__(self, **kwargs):
        self.id = kwargs.get("id", 1)
        self.user_id = kwargs.get("user_id", 1)
        self.name = kwargs.get("name", "Nubank")
        self.bank = kwargs.get("bank", "Nubank")
        self.type = kwargs.get("type", "CHECKING")
        self.balance = kwargs.get("balance", 1000.0)
        self.color = kwargs.get("color", "#820AD1")
        self.active = kwargs.get("active", True)
        self.created_at = kwargs.get("created_at", datetime.now(UTC))
        self.updated_at = kwargs.get("updated_at", datetime.now(UTC))


@pytest.fixture
def mock_user():
    return MockUser()


@pytest.fixture
def mock_account():
    return MockAccount()


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
async def test_list_accounts_requires_auth(client):
    """Test that unauthenticated requests are rejected."""
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
# CRUD tests – authenticated
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
    fake_id = 1
    now = datetime.now(UTC)
    accounts_data = [
        {
            "id": str(fake_id),
            "user_id": str(mock_user.id),
            "name": "Nubank",
            "bank": "Nubank",
            "type": "CHECKING",
            "balance": 1500.0,
            "color": "#820AD1",
            "active": True,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
    ]

    with patch(
        "app.api.routes.v1.accounts.account_service.list_accounts",
        new_callable=AsyncMock,
    ) as mock_list:
        mock_list.return_value = accounts_data

        response = await client_with_auth.get(f"{settings.API_V1_STR}/bagcoin/accounts")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Nubank"
    assert data[0]["bank"] == "Nubank"
    assert data[0]["type"] == "CHECKING"
    assert data[0]["balance"] == 1500.0
    assert data[0]["active"] is True


@pytest.mark.anyio
async def test_create_account_201(client_with_auth, mock_user):
    """Test creating an account returns 201."""
    fake_id = 1
    now = datetime.now(UTC)

    with patch(
        "app.api.routes.v1.accounts.account_service.create_account",
        new_callable=AsyncMock,
    ) as mock_create:
        mock_create.return_value = {
            "id": str(fake_id),
            "user_id": str(mock_user.id),
            "name": "Nu Conta",
            "bank": "Nubank",
            "type": "CHECKING",
            "balance": 500.0,
            "color": "#820AD1",
            "active": True,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

        response = await client_with_auth.post(
            f"{settings.API_V1_STR}/bagcoin/accounts",
            json={
                "name": "Nu Conta",
                "bank": "Nubank",
                "type": "CHECKING",
                "balance": 500.0,
                "color": "#820AD1",
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


@pytest.mark.anyio
async def test_get_account(client_with_auth, mock_user):
    """Test getting a specific account."""
    account_id = 1
    now = datetime.now(UTC)

    with patch(
        "app.api.routes.v1.accounts.account_service.get_account",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = {
            "id": str(account_id),
            "user_id": str(mock_user.id),
            "name": "Nubank",
            "bank": "Nubank",
            "type": "CHECKING",
            "balance": 2000.0,
            "color": "#820AD1",
            "active": True,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

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


@pytest.mark.anyio
async def test_update_account(client_with_auth, mock_user):
    """Test updating an account."""
    account_id = 1
    now = datetime.now(UTC)

    with patch(
        "app.api.routes.v1.accounts.account_service.update_account",
        new_callable=AsyncMock,
    ) as mock_update:
        mock_update.return_value = {
            "id": str(account_id),
            "user_id": str(mock_user.id),
            "name": "Updated Account",
            "bank": "Nubank",
            "type": "SAVINGS",
            "balance": 3000.0,
            "color": "#000000",
            "active": True,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

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


@pytest.mark.anyio
async def test_update_account_not_found(client_with_auth):
    """Test updating a non-existent account returns 404."""
    from app.core.exceptions import NotFoundError

    with patch(
        "app.api.routes.v1.accounts.account_service.update_account",
        new_callable=AsyncMock,
    ) as mock_update:
        mock_update.side_effect = NotFoundError(
            message="Account not found", details={"id": str(1)}
        )

        response = await client_with_auth.patch(
            f"{settings.API_V1_STR}/bagcoin/accounts/{1}",
            json={"name": "Ghost"},
        )

    assert response.status_code == 404


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
