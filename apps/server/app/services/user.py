"""User service (PostgreSQL async).

Contains business logic for user operations.
"""

from typing import TYPE_CHECKING, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    AlreadyExistsError,
    AuthenticationError,
    BadRequestError,
    NotFoundError,
)
from app.core.security import get_password_hash, verify_google_access_token, verify_google_token, verify_password
from app.db.models.user import User
from app.repositories import user_repo
from app.schemas.user import GoogleLoginRequest, UserCreate, UserUpdate

if TYPE_CHECKING:
    from app.schemas.conversation_share import AdminUserList


class UserService:
    """Service for user-related business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: int) -> User:
        """Get user by ID."""
        user = await user_repo.get_by_id(self.db, user_id)
        if not user:
            raise NotFoundError(
                message="Usuário não encontrado",
                details={"user_id": user_id},
            )
        return user

    async def get_by_email(self, email: str) -> User | None:
        return await user_repo.get_by_email(self.db, email)

    async def get_by_phone_number(self, phone_number: str) -> User | None:
        return await user_repo.get_by_phone_number(self.db, phone_number)

    async def get_or_create_by_phone(
        self, phone_number: str, name: str | None = None, platform: str = "whatsapp"
    ) -> User:
        return await user_repo.get_or_create_by_phone(
            self.db, phone_number=phone_number, name=name, platform=platform
        )

    async def get_multi(self, *, skip: int = 0, limit: int = 100) -> list[User]:
        return await user_repo.get_multi(self.db, skip=skip, limit=limit)

    async def list_paginated(self) -> Any:
        from fastapi_pagination.ext.sqlalchemy import paginate
        return await paginate(self.db, user_repo.list_query())

    async def delete_non_admins(self) -> int:
        return await user_repo.delete_non_admins(self.db)

    async def has_any(self) -> bool:
        return await user_repo.has_any(self.db)

    async def admin_list_with_counts(
        self, *, skip: int = 0, limit: int = 50, search: str | None = None
    ) -> "AdminUserList":
        from app.schemas.conversation_share import AdminUserList, AdminUserRead

        rows, total = await user_repo.admin_list_with_counts(
            self.db, skip=skip, limit=limit, search=search
        )
        items = [
            AdminUserRead(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                is_active=user.is_active,
                conversation_count=conv_count,
                created_at=user.created_at,
            )
            for user, conv_count in rows
        ]
        return AdminUserList(items=items, total=total)

    async def register(self, user_in: UserCreate) -> User:
        existing = await user_repo.get_by_email(self.db, user_in.email)
        if existing:
            raise AlreadyExistsError(
                message="Email já cadastrado",
                details={"email": user_in.email},
            )
        hashed_password = get_password_hash(user_in.password)
        return await user_repo.create(
            self.db,
            email=user_in.email,
            hashed_password=hashed_password,
            full_name=user_in.full_name,
            phone_number=user_in.phone_number,
            auth_provider="email",
            role=user_in.role.value,
        )

    async def google_auth(self, request: GoogleLoginRequest) -> User:
        google_payload = verify_google_token(request.id_token) if request.id_token else None
        if not google_payload and request.access_token:
            google_payload = await verify_google_access_token(request.access_token)
        if not google_payload:
            raise AuthenticationError(message="Token do Google inválido")

        google_id = google_payload.get("sub")
        email = google_payload.get("email", "").lower()
        name = google_payload.get("name")

        if not email:
            raise BadRequestError(message="A conta do Google não possui um email válido")

        existing = await user_repo.get_by_google_id(self.db, google_id)
        if existing:
            return existing

        existing_email = await user_repo.get_by_email(self.db, email)
        if existing_email:
            if not existing_email.google_id:
                await user_repo.update(
                    self.db,
                    db_user=existing_email,
                    update_data={"google_id": google_id, "auth_provider": "google"},
                )
            return existing_email

        return await user_repo.create(
            self.db,
            email=email,
            hashed_password=None,
            full_name=name,
            google_id=google_id,
            auth_provider="google",
        )

    async def authenticate(self, email: str, password: str) -> User:
        user = await user_repo.get_by_email(self.db, email)
        if (
            not user
            or not user.hashed_password
            or not verify_password(password, user.hashed_password)
        ):
            raise AuthenticationError(message="Email ou senha incorretos")
        if not user.is_active:
            raise AuthenticationError(message="Sua conta está desativada")
        if not user.email_verified:
            raise AuthenticationError(
                message="Seu email ainda não foi verificado",
                code="EMAIL_NOT_VERIFIED",
                details={"email": user.email},
            )
        return user

    async def update(self, user_id: int, user_in: UserUpdate) -> User:
        user = await self.get_by_id(user_id)
        update_data = user_in.model_dump(exclude_unset=True)
        if "password" in update_data:
            update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
        return await user_repo.update(self.db, db_user=user, update_data=update_data)

    async def update_avatar(
        self, user_id: int, file_data: bytes, filename: str, content_type: str
    ) -> User:
        import contextlib
        from app.services.file_storage import get_file_storage

        ALLOWED_AVATAR_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
        if content_type not in ALLOWED_AVATAR_TYPES:
            raise ValueError("Only JPEG, PNG, WebP, and GIF images are allowed")
        if len(file_data) > 2 * 1024 * 1024:
            raise ValueError("Avatar image too large. Maximum 2MB.")

        storage = get_file_storage()
        user = await self.get_by_id(user_id)
        if user.avatar_url:
            with contextlib.suppress(Exception):
                await storage.delete(user.avatar_url)

        storage_path = await storage.save(f"avatars/{user_id}", filename, file_data)
        return await user_repo.update_avatar(self.db, user_id, storage_path)

    async def delete(self, user_id: int) -> User:
        user = await user_repo.delete(self.db, user_id)
        if not user:
            raise NotFoundError(
                message="Usuário não encontrado",
                details={"user_id": str(user_id)},
            )
        return user
