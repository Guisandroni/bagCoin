"""SQLAdmin setup for BagCoin operational administration."""

from __future__ import annotations

from fastapi import FastAPI
from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from sqlalchemy import select
from starlette.requests import Request

from app.core.config import settings
from app.core.security import verify_password
from app.db import session as db_session
from app.db.models.user import User, UserRole


class BagCoinAdminAuth(AuthenticationBackend):
    """Authenticate SQLAdmin with existing BagCoin admin users."""

    async def login(self, request: Request) -> bool:
        form = await request.form()
        email = str(form.get("username") or form.get("email") or "").strip().lower()
        password = str(form.get("password") or "")

        if not email or not password:
            return False

        with db_session.sync_session_maker() as session:
            user = session.execute(select(User).where(User.email == email)).scalar_one_or_none()
            if (
                user is None
                or not user.is_active
                or user.role != UserRole.ADMIN.value
                or not user.hashed_password
                or not verify_password(password, user.hashed_password)
            ):
                return False

            request.session.update({"admin_user_id": user.id})
            return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        user_id = request.session.get("admin_user_id")
        if not user_id:
            return False

        with db_session.sync_session_maker() as session:
            user = session.get(User, user_id)
            return bool(user and user.is_active and user.role == UserRole.ADMIN.value)


class UserAdmin(ModelView, model=User):
    """Initial admin view scoped to users only."""

    name = "Usuário"
    name_plural = "Usuários"
    icon = "fa-solid fa-users"

    column_list = [
        User.id,
        User.email,
        User.full_name,
        User.phone_number,
        User.role,
        User.is_active,
        User.email_verified_at,
        User.created_at,
    ]
    column_searchable_list = [User.email, User.full_name, User.phone_number]
    column_sortable_list = [User.id, User.email, User.role, User.is_active, User.created_at]
    form_columns = [
        User.email,
        User.full_name,
        User.phone_number,
        User.role,
        User.is_active,
        User.status,
    ]


def setup_admin(app: FastAPI) -> Admin:
    """Register SQLAdmin on the FastAPI app."""

    authentication_backend = BagCoinAdminAuth(secret_key=settings.SECRET_KEY)
    admin = Admin(
        app,
        db_session.sync_engine,
        title="BagCoin Admin",
        base_url="/admin",
        authentication_backend=authentication_backend,
    )
    admin.add_view(UserAdmin)
    return admin


__all__: list[str] = ["BagCoinAdminAuth", "UserAdmin", "setup_admin"]
