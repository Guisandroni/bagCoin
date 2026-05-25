"""Admin dashboard configuration tests."""

from types import SimpleNamespace

import pytest

from app.admin import BagCoinAdminAuth
from app.core.security import get_password_hash
from app.db.models.user import UserRole


class FakeRequest:
    def __init__(self, form_data: dict[str, str] | None = None) -> None:
        self._form_data = form_data or {}
        self.session: dict[str, int] = {}

    async def form(self) -> dict[str, str]:
        return self._form_data


class FakeScalarResult:
    def __init__(self, user: object | None) -> None:
        self.user = user

    def scalar_one_or_none(self) -> object | None:
        return self.user


class FakeSession:
    def __init__(self, user: object | None) -> None:
        self.user = user

    def __enter__(self) -> "FakeSession":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def execute(self, statement: object) -> FakeScalarResult:
        return FakeScalarResult(self.user)

    def get(self, model: object, user_id: int) -> object | None:
        return self.user if getattr(self.user, "id", None) == user_id else None


def fake_session_maker(user: object | None):
    def factory() -> FakeSession:
        return FakeSession(user)

    return factory


@pytest.mark.anyio
async def test_admin_auth_allows_active_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    user = SimpleNamespace(
        id=1,
        email="admin@bagcoin.com",
        hashed_password=get_password_hash("Senha123"),
        is_active=True,
        role=UserRole.ADMIN.value,
    )
    monkeypatch.setattr("app.admin.db_session.sync_session_maker", fake_session_maker(user))
    auth = BagCoinAdminAuth(secret_key="x" * 32)
    request = FakeRequest({"username": "admin@bagcoin.com", "password": "Senha123"})

    assert await auth.login(request) is True
    assert request.session["admin_user_id"] == 1
    assert await auth.authenticate(request) is True


@pytest.mark.anyio
async def test_admin_auth_rejects_regular_user(monkeypatch: pytest.MonkeyPatch) -> None:
    user = SimpleNamespace(
        id=2,
        email="user@bagcoin.com",
        hashed_password=get_password_hash("Senha123"),
        is_active=True,
        role=UserRole.USER.value,
    )
    monkeypatch.setattr("app.admin.db_session.sync_session_maker", fake_session_maker(user))
    auth = BagCoinAdminAuth(secret_key="x" * 32)
    request = FakeRequest({"username": "user@bagcoin.com", "password": "Senha123"})

    assert await auth.login(request) is False
    assert "admin_user_id" not in request.session
