# ruff: noqa: I001 - Imports structured for Jinja2 template conditionals
"""Tests for authentication routes."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

ServiceMock = AsyncMock
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.api.deps import get_user_service
from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token
from app.main import app
from app.services.email_verification import VerificationDispatchResult


class MockUser:
    """Mock user for testing."""

    def __init__(
        self,
        id=None,
        email="test@example.com",
        full_name="Test User",
        is_active=True,
        email_verified=True,
        role="user",
    ):
        self.id = id or uuid4()
        self.email = email
        self.full_name = full_name
        self.is_active = is_active
        self.email_verified = email_verified
        self.email_verified_at = datetime.now(UTC) if email_verified else None
        self.email_verification_code_hash = "hashed-code" if not email_verified else None
        self.email_verification_expires_at = (
            datetime.now(UTC) + timedelta(minutes=10) if not email_verified else None
        )
        self.email_verification_sent_at = datetime.now(UTC) if not email_verified else None
        self.email_verification_attempts = 0
        self.role = role
        self.hashed_password = "hashed"
        self.phone_number = None
        self.google_id = None
        self.auth_provider = "email"
        self.avatar_url = None
        self.created_at = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)


@pytest.fixture
def mock_user() -> MockUser:
    """Create a mock user."""
    return MockUser()


@pytest.fixture
def mock_user_service(mock_user: MockUser) -> MagicMock:
    """Create a mock user service."""
    service = MagicMock()
    service.authenticate = ServiceMock(return_value=mock_user)
    service.register = ServiceMock(return_value=mock_user)
    service.get_by_id = ServiceMock(return_value=mock_user)
    service.get_by_email = ServiceMock(return_value=mock_user)
    service.google_auth = ServiceMock(return_value=mock_user)
    return service


@pytest.fixture
async def client_with_mock_service(
    mock_user_service: MagicMock,
    mock_redis: MagicMock,
    mock_db_session,
) -> AsyncClient:
    """Client with mocked user service."""
    from app.api.deps import get_redis
    from app.api.deps import get_db_session
    from httpx import ASGITransport

    app.dependency_overrides[get_user_service] = lambda: mock_user_service
    app.dependency_overrides[get_redis] = lambda: mock_redis
    app.dependency_overrides[get_db_session] = lambda: mock_db_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_login_success(client_with_mock_service: AsyncClient):
    """Test successful login."""
    response = await client_with_mock_service.post(
        f"{settings.API_V1_STR}/auth/login",
        data={"username": "test@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.anyio
async def test_login_invalid_credentials(
    client_with_mock_service: AsyncClient,
    mock_user_service: MagicMock,
):
    """Test login with invalid credentials."""
    from app.core.exceptions import AuthenticationError

    mock_user_service.authenticate = ServiceMock(
        side_effect=AuthenticationError(message="Invalid credentials")
    )

    response = await client_with_mock_service.post(
        f"{settings.API_V1_STR}/auth/login",
        data={"username": "test@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401


@pytest.mark.anyio
async def test_register_success(client_with_mock_service: AsyncClient):
    """Test successful registration."""
    with patch(
        "app.api.routes.v1.auth.EmailVerificationService.issue_code_for_user",
        new=AsyncMock(return_value=VerificationDispatchResult(600, 60)),
    ):
        response = await client_with_mock_service.post(
            f"{settings.API_V1_STR}/auth/register",
            json={
                "email": "new@example.com",
                "password": "Password1",
                "full_name": "New User",
            },
        )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["requires_email_verification"] is True
    assert data["auth_provider"] == "email"


@pytest.mark.anyio
async def test_register_duplicate_email(
    client_with_mock_service: AsyncClient,
    mock_user_service: MagicMock,
):
    """Test registration with duplicate email."""
    from app.core.exceptions import AlreadyExistsError

    mock_user_service.register = ServiceMock(
        side_effect=AlreadyExistsError(message="Email already registered")
    )

    response = await client_with_mock_service.post(
        f"{settings.API_V1_STR}/auth/register",
        json={
            "email": "existing@example.com",
            "password": "Password1",
            "full_name": "Test User",
        },
    )
    assert response.status_code == 409


@pytest.mark.anyio
async def test_register_weak_password_returns_422(client_with_mock_service: AsyncClient):
    """Test registration rejects weak passwords before service execution."""
    response = await client_with_mock_service.post(
        f"{settings.API_V1_STR}/auth/register",
        json={
            "email": "new@example.com",
            "password": "abcdef",
            "full_name": "New User",
        },
    )
    assert response.status_code == 422
    details = response.json()["detail"]
    assert any("letra maiúscula" in item["msg"] for item in details)


@pytest.mark.anyio
async def test_refresh_token_success(
    client_with_mock_service: AsyncClient,
    mock_user: MockUser,
):
    """Test successful token refresh."""
    refresh_token = create_refresh_token(subject=str(mock_user.id))

    response = await client_with_mock_service.post(
        f"{settings.API_V1_STR}/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.anyio
async def test_refresh_token_invalid(client_with_mock_service: AsyncClient):
    """Test refresh with invalid token."""
    response = await client_with_mock_service.post(
        f"{settings.API_V1_STR}/auth/refresh",
        json={"refresh_token": "invalid.token.here"},
    )
    assert response.status_code == 401


@pytest.mark.anyio
async def test_refresh_token_wrong_type(
    client_with_mock_service: AsyncClient,
    mock_user: MockUser,
):
    """Test refresh with access token instead of refresh token."""
    access_token = create_access_token(subject=str(mock_user.id))

    response = await client_with_mock_service.post(
        f"{settings.API_V1_STR}/auth/refresh",
        json={"refresh_token": access_token},
    )
    assert response.status_code == 401


@pytest.mark.anyio
async def test_refresh_token_inactive_user(
    client_with_mock_service: AsyncClient,
    mock_user_service: MagicMock,
):
    """Test refresh token for inactive user."""
    inactive_user = MockUser(is_active=False)
    mock_user_service.get_by_id = ServiceMock(return_value=inactive_user)
    refresh_token = create_refresh_token(subject=str(inactive_user.id))

    response = await client_with_mock_service.post(
        f"{settings.API_V1_STR}/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 401


@pytest.mark.anyio
async def test_get_current_user(
    client_with_mock_service: AsyncClient,
    mock_user: MockUser,
    mock_user_service: MagicMock,
):
    """Test getting current user info."""
    from app.api.deps import get_current_user

    # Override get_current_user to return mock user
    app.dependency_overrides[get_current_user] = lambda: mock_user

    response = await client_with_mock_service.get(
        f"{settings.API_V1_STR}/auth/me",
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == mock_user.email


@pytest.mark.anyio
async def test_google_login_success(
    client_with_mock_service: AsyncClient,
    mock_user: MockUser,
    mock_user_service: MagicMock,
):
    """Test successful Google login."""
    mock_user.email_verified = True
    mock_user.email_verified_at = datetime.now(UTC)
    mock_user_service.google_auth = ServiceMock(return_value=mock_user)

    response = await client_with_mock_service.post(
        f"{settings.API_V1_STR}/auth/google",
        json={"id_token": "valid-google-id-token"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.anyio
async def test_google_login_invalid_token(
    client_with_mock_service: AsyncClient,
    mock_user_service: MagicMock,
):
    """Test Google login with invalid token."""
    from app.core.exceptions import AuthenticationError

    mock_user_service.google_auth = ServiceMock(
        side_effect=AuthenticationError(message="Invalid Google token")
    )

    response = await client_with_mock_service.post(
        f"{settings.API_V1_STR}/auth/google",
        json={"id_token": "invalid-token"},
    )
    assert response.status_code == 401


@pytest.mark.anyio
async def test_google_login_pending_verification(
    client_with_mock_service: AsyncClient,
    mock_user_service: MagicMock,
):
    """Test Google login returns pending verification when user is unverified."""
    pending_user = MockUser(email_verified=False)
    pending_user.google_id = "google-id"
    pending_user.auth_provider = "google"
    mock_user_service.google_auth = ServiceMock(return_value=pending_user)

    with patch(
        "app.api.routes.v1.auth.EmailVerificationService.issue_code_for_user",
        new=AsyncMock(return_value=VerificationDispatchResult(600, 60)),
    ):
        response = await client_with_mock_service.post(
            f"{settings.API_V1_STR}/auth/google",
            json={"id_token": "valid-google-id-token"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["requires_email_verification"] is True
    assert data["auth_provider"] == "google"


@pytest.mark.anyio
async def test_verify_email_success(client_with_mock_service: AsyncClient):
    """Test email verification success."""
    with patch(
        "app.api.routes.v1.auth.EmailVerificationService.verify_code",
        new=AsyncMock(return_value=MockUser()),
    ):
        response = await client_with_mock_service.post(
            f"{settings.API_V1_STR}/auth/verify-email",
            json={"email": "test@example.com", "code": "123456"},
        )

    assert response.status_code == 200
    assert response.json()["verified"] is True


@pytest.mark.anyio
async def test_verify_email_invalid_code_returns_attempt_details(client_with_mock_service: AsyncClient):
    """Test invalid verification code returns remaining attempts."""
    from app.core.exceptions import AuthenticationError

    with patch(
        "app.api.routes.v1.auth.EmailVerificationService.verify_code",
        new=AsyncMock(
            side_effect=AuthenticationError(
                message="Invalid verification code",
                code="EMAIL_VERIFICATION_INVALID",
                details={
                    "attempts_used": 1,
                    "attempts_remaining": 4,
                    "max_attempts": 5,
                },
            )
        ),
    ):
        response = await client_with_mock_service.post(
            f"{settings.API_V1_STR}/auth/verify-email",
            json={"email": "test@example.com", "code": "000000"},
        )

    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "EMAIL_VERIFICATION_INVALID"
    assert data["error"]["details"]["attempts_remaining"] == 4


@pytest.mark.anyio
async def test_resend_verification_success(client_with_mock_service: AsyncClient):
    """Test resending a verification code."""
    with patch(
        "app.api.routes.v1.auth.EmailVerificationService.resend_code",
        new=AsyncMock(
            return_value={
                "sent": True,
                "resend_available_in_seconds": 60,
                "expires_in_seconds": 600,
            }
        ),
    ):
        response = await client_with_mock_service.post(
            f"{settings.API_V1_STR}/auth/resend-verification",
            json={"email": "test@example.com"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["sent"] is True
    assert data["resend_available_in_seconds"] == 60


@pytest.mark.anyio
async def test_register_with_phone(
    client_with_mock_service: AsyncClient,
    mock_user_service: MagicMock,
):
    """Test registration with phone number."""
    mock_user_service.register = ServiceMock(return_value=mock_user_service.authenticate.return_value)

    with patch(
        "app.api.routes.v1.auth.EmailVerificationService.issue_code_for_user",
        new=AsyncMock(return_value=VerificationDispatchResult(600, 60)),
    ):
        response = await client_with_mock_service.post(
            f"{settings.API_V1_STR}/auth/register",
            json={
                "email": "new@example.com",
                "password": "Password1",
                "full_name": "New User",
                "phone_number": "+5511999999999",
            },
        )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"


@pytest.mark.anyio
async def test_register_inactive_user_google(
    client_with_mock_service: AsyncClient,
    mock_user_service: MagicMock,
):
    """Test Google login for inactive user."""

    inactive_user = MockUser(is_active=False)
    mock_user_service.google_auth = ServiceMock(return_value=inactive_user)

    response = await client_with_mock_service.post(
        f"{settings.API_V1_STR}/auth/google",
        json={"id_token": "valid-token"},
    )
    assert response.status_code == 401
