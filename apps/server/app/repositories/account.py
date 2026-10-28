"""Account repository (PostgreSQL async)."""

from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.account import Account


async def get_by_id(db: AsyncSession, account_id: int) -> Account | None:
    """Get account by ID."""
    return await db.get(Account, account_id)


async def get_multi_by_user(
    db: AsyncSession,
    user_id: int,
    *,
    skip: int = 0,
    limit: int = 50,
    active_only: bool = True,
) -> list[Account]:
    """Get accounts for a user."""
    query = select(Account).where(Account.user_id == user_id)
    if active_only:
        query = query.where(Account.active.is_(True))
    query = query.order_by(Account.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def create(
    db: AsyncSession,
    *,
    user_id: int,
    name: str,
    bank: str,
    type: str = "CHECKING",
    balance: float = 0.0,
    color: str | None = None,
    active: bool = True,
) -> Account:
    """Create a new account."""
    account = Account(
        user_id=user_id,
        name=name,
        bank=bank,
        type=type,
        balance=balance,
        color=color,
        active=active,
    )
    db.add(account)
    await db.flush()
    await db.refresh(account)
    return account


async def update(
    db: AsyncSession,
    *,
    db_account: Account,
    update_data: dict[str, Any],
) -> Account:
    """Update an account."""
    for field, value in update_data.items():
        setattr(db_account, field, value)
    db.add(db_account)
    await db.flush()
    await db.refresh(db_account)
    return db_account


async def delete(db: AsyncSession, account_id: int) -> Account | None:
    """Delete an account by ID."""
    account = await get_by_id(db, account_id)
    if account:
        await db.delete(account)
        await db.flush()
    return account
