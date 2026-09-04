"""Unified User repository (PostgreSQL async).

Handles both web (email/Google) and agent (phone/telegram) users.
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User


async def get_by_id(db: AsyncSession, user_id: int) -> User | None:
    """Get user by ID."""
    return await db.get(User, user_id)


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    """Get user by email."""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_by_google_id(db: AsyncSession, google_id: str) -> User | None:
    """Get user by Google ID."""
    result = await db.execute(select(User).where(User.google_id == google_id))
    return result.scalar_one_or_none()


async def get_by_phone_number(db: AsyncSession, phone_number: str) -> User | None:
    """Get user by phone number."""
    result = await db.execute(select(User).where(User.phone_number == phone_number))
    return result.scalar_one_or_none()


async def get_by_telegram_chat_id(db: AsyncSession, telegram_chat_id: str) -> User | None:
    """Get user by Telegram chat ID."""
    result = await db.execute(select(User).where(User.telegram_chat_id == telegram_chat_id))
    return result.scalar_one_or_none()


async def get_or_create_by_phone(
    db: AsyncSession,
    *,
    phone_number: str,
    name: str | None = None,
    platform: str = "whatsapp",
) -> User:
    """Get existing user by phone number or create a new one."""
    existing = await get_by_phone_number(db, phone_number)
    if existing:
        return existing

    user = User(
        phone_number=phone_number,
        full_name=name,
        platform=platform,
        preferences={"language": "pt-BR", "currency": "BRL"},
        financial_profile={},
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def get_multi(
    db: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 100,
) -> list[User]:
    """Get multiple users with pagination."""
    result = await db.execute(select(User).offset(skip).limit(limit))
    return list(result.scalars().all())


def list_query() -> Any:
    """Return the SQL Select for listing users (used by paginate)."""
    return select(User)


async def create(
    db: AsyncSession,
    *,
    email: str | None = None,
    hashed_password: str | None = None,
    full_name: str | None = None,
    phone_number: str | None = None,
    google_id: str | None = None,
    auth_provider: str | None = None,
    is_active: bool = True,
    email_verified_at: Any | None = None,
    email_verification_code_hash: str | None = None,
    email_verification_expires_at: Any | None = None,
    email_verification_sent_at: Any | None = None,
    email_verification_attempts: int = 0,
    role: str = "user",
    platform: str | None = None,
    telegram_chat_id: str | None = None,
    preferences: dict | None = None,
    financial_profile: dict | None = None,
) -> User:
    """Create a new user."""
    user = User(
        email=email,
        hashed_password=hashed_password,
        full_name=full_name,
        phone_number=phone_number,
        google_id=google_id,
        auth_provider=auth_provider,
        is_active=is_active,
        email_verified_at=email_verified_at,
        email_verification_code_hash=email_verification_code_hash,
        email_verification_expires_at=email_verification_expires_at,
        email_verification_sent_at=email_verification_sent_at,
        email_verification_attempts=email_verification_attempts,
        role=role,
        platform=platform,
        telegram_chat_id=telegram_chat_id,
        preferences=preferences or {},
        financial_profile=financial_profile or {},
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def update(
    db: AsyncSession,
    *,
    db_user: User,
    update_data: dict[str, Any],
) -> User:
    """Update a user."""
    for field, value in update_data.items():
        setattr(db_user, field, value)
    db.add(db_user)
    await db.flush()
    await db.refresh(db_user)
    return db_user


async def update_avatar(db: AsyncSession, user_id: int, avatar_url: str) -> User:
    """Update a user's avatar URL."""
    user = await db.get(User, user_id)
    if user is None:
        raise ValueError(f"User {user_id} not found")
    user.avatar_url = avatar_url
    await db.flush()
    await db.refresh(user)
    return user


async def update_preferences(
    db: AsyncSession,
    user_id: int,
    preferences: dict[str, Any],
) -> User:
    """Update user preferences (partial merge)."""
    user = await get_by_id(db, user_id)
    if user is None:
        from app.core.exceptions import NotFoundError
        raise NotFoundError(message="User not found", details={"user_id": user_id})
    current = dict(user.preferences or {})
    current.update(preferences)
    user.preferences = current
    await db.flush()
    await db.refresh(user)
    return user


async def update_financial_profile(
    db: AsyncSession,
    user_id: int,
    profile: dict[str, Any],
) -> User:
    """Update user financial profile."""
    user = await get_by_id(db, user_id)
    if user is None:
        from app.core.exceptions import NotFoundError
        raise NotFoundError(message="User not found", details={"user_id": user_id})
    user.financial_profile = profile
    await db.flush()
    await db.refresh(user)
    return user


async def delete(db: AsyncSession, user_id: int) -> User | None:
    """Delete a user."""
    user = await get_by_id(db, user_id)
    if user:
        await db.delete(user)
        await db.flush()
    return user


async def delete_non_admins(db: AsyncSession) -> int:
    """Bulk-delete users without the admin role."""
    from sqlalchemy import delete as sql_delete
    result = await db.execute(sql_delete(User).where(User.role != "admin"))
    await db.flush()
    return result.rowcount  # type: ignore[no-any-return, attr-defined]


async def has_any(db: AsyncSession) -> bool:
    """Return True if at least one user exists."""
    result = await db.execute(select(User).limit(1))
    return result.scalars().first() is not None


async def admin_list_with_counts(
    db: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 50,
    search: str | None = None,
) -> tuple[list[tuple[User, int]], int]:
    """Admin: list users with their conversation counts."""
    from sqlalchemy import func
    from app.db.models.conversation import Conversation

    query = (
        select(User, func.count(Conversation.id).label("conversation_count"))
        .outerjoin(Conversation, Conversation.user_id == User.id)
        .group_by(User.id)
    )
    count_query = select(func.count()).select_from(User)

    if search:
        condition = User.email.ilike(f"%{search}%") | User.full_name.ilike(f"%{search}%")
        query = query.where(condition)
        count_query = count_query.where(condition)

    query = query.order_by(User.created_at.desc()).offset(skip).limit(limit)
    total = await db.scalar(count_query) or 0
    rows = (await db.execute(query)).all()
    return [(user, count) for user, count in rows], total
