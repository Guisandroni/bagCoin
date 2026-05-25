"""Credit Card REST endpoints for web frontend."""

from typing import Any
from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DBSession
from app.schemas.credit_card import CreditCardCreate, CreditCardResponse, CreditCardUpdate
from app.services import credit_card_service as cc_service

router = APIRouter(prefix="/bagcoin/credit-cards", tags=["bagcoin"])


@router.get("", response_model=list[CreditCardResponse])
async def list_credit_cards(
    current_user: CurrentUser,
    db: DBSession,
) -> Any:
    """List credit cards for the authenticated user."""
    return await cc_service.list_credit_cards(db, current_user.id)


@router.post("", response_model=CreditCardResponse, status_code=status.HTTP_201_CREATED)
async def create_credit_card(
    current_user: CurrentUser,
    db: DBSession,
    body: CreditCardCreate,
) -> Any:
    """Create a new credit card."""
    return await cc_service.create_credit_card(db, current_user.id, body)


@router.get("/{card_id}", response_model=CreditCardResponse)
async def get_credit_card(
    card_id: int,
    current_user: CurrentUser,
    db: DBSession,
) -> Any:
    """Get a specific credit card."""
    return await cc_service.get_credit_card(db, card_id, current_user.id)


@router.patch("/{card_id}", response_model=CreditCardResponse)
async def update_credit_card(
    card_id: int,
    current_user: CurrentUser,
    db: DBSession,
    body: CreditCardUpdate,
) -> Any:
    """Update a credit card."""
    return await cc_service.update_credit_card(db, card_id, current_user.id, body)


@router.delete("/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_credit_card(
    card_id: int,
    current_user: CurrentUser,
    db: DBSession,
) -> None:
    """Delete a credit card."""
    await cc_service.delete_credit_card(db, card_id, current_user.id)
