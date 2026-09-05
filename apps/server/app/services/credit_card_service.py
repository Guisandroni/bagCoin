"""REST service for CreditCard operations."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.repositories import credit_card as credit_card_repo
from app.schemas.credit_card import CreditCardCreate, CreditCardResponse, CreditCardUpdate


async def list_credit_cards(
    db: AsyncSession,
    user_id: int,
    *,
    skip: int = 0,
    limit: int = 50,
) -> list[CreditCardResponse]:
    """List credit cards for a user."""
    cards = await credit_card_repo.get_multi_by_user(db, user_id, skip=skip, limit=limit)
    return [CreditCardResponse.model_validate(c) for c in cards]


async def create_credit_card(
    db: AsyncSession,
    user_id: int,
    data: CreditCardCreate,
) -> CreditCardResponse:
    """Create a new credit card."""
    card = await credit_card_repo.create(
        db,
        user_id=user_id,
        name=data.name,
        issuer=data.issuer,
        limit=data.limit,
        closing_day=data.closing_day,
        due_day=data.due_day,
        color=data.color,
        active=data.active,
    )
    return CreditCardResponse.model_validate(card)


async def get_credit_card(db: AsyncSession, card_id: int, user_id: int) -> CreditCardResponse:
    """Get a credit card by ID."""
    card = await credit_card_repo.get_by_id(db, card_id)
    if not card or card.user_id != user_id:
        raise NotFoundError(message="Credit card not found", details={"id": str(card_id)})
    return CreditCardResponse.model_validate(card)


async def update_credit_card(
    db: AsyncSession,
    card_id: int,
    user_id: int,
    data: CreditCardUpdate,
) -> CreditCardResponse:
    """Update a credit card."""
    card = await credit_card_repo.get_by_id(db, card_id)
    if not card or card.user_id != user_id:
        raise NotFoundError(message="Credit card not found", details={"id": str(card_id)})
    update_data = data.model_dump(exclude_unset=True)
    card = await credit_card_repo.update(db, db_card=card, update_data=update_data)
    return CreditCardResponse.model_validate(card)


async def delete_credit_card(db: AsyncSession, card_id: int, user_id: int) -> None:
    """Delete a credit card."""
    card = await credit_card_repo.get_by_id(db, card_id)
    if not card or card.user_id != user_id:
        raise NotFoundError(message="Credit card not found", details={"id": str(card_id)})
    await credit_card_repo.delete(db, card_id)
