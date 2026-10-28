"""CreditCard repository (PostgreSQL async)."""

from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.credit_card import CreditCard


async def get_by_id(db: AsyncSession, card_id: int) -> CreditCard | None:
    """Get credit card by ID."""
    return await db.get(CreditCard, card_id)


async def get_multi_by_user(
    db: AsyncSession,
    user_id: int,
    *,
    skip: int = 0,
    limit: int = 50,
    active_only: bool = True,
) -> list[CreditCard]:
    """Get credit cards for a user."""
    query = select(CreditCard).where(CreditCard.user_id == user_id)
    if active_only:
        query = query.where(CreditCard.active.is_(True))
    query = query.order_by(CreditCard.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def create(
    db: AsyncSession,
    *,
    user_id: int,
    name: str,
    issuer: str,
    limit: float,
    closing_day: int,
    due_day: int,
    color: str | None = None,
    active: bool = True,
) -> CreditCard:
    """Create a new credit card."""
    card = CreditCard(
        user_id=user_id,
        name=name,
        issuer=issuer,
        limit=limit,
        closing_day=closing_day,
        due_day=due_day,
        color=color,
        active=active,
    )
    db.add(card)
    await db.flush()
    await db.refresh(card)
    return card


async def update(
    db: AsyncSession,
    *,
    db_card: CreditCard,
    update_data: dict[str, Any],
) -> CreditCard:
    """Update a credit card."""
    for field, value in update_data.items():
        setattr(db_card, field, value)
    db.add(db_card)
    await db.flush()
    await db.refresh(db_card)
    return db_card


async def delete(db: AsyncSession, card_id: int) -> CreditCard | None:
    """Delete a credit card by ID."""
    card = await get_by_id(db, card_id)
    if card:
        await db.delete(card)
        await db.flush()
    return card
