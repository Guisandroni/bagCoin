"""Account REST endpoints for web frontend."""

from typing import Any
from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DBSession
from app.schemas.account import AccountCreate, AccountResponse, AccountUpdate
from app.services import account_service

router = APIRouter(prefix="/bagcoin/accounts", tags=["bagcoin"])


@router.get("", response_model=list[AccountResponse])
async def list_accounts(
    current_user: CurrentUser,
    db: DBSession,
) -> Any:
    """List accounts for the authenticated user."""
    return await account_service.list_accounts(db, current_user.id)


@router.post("", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    current_user: CurrentUser,
    db: DBSession,
    body: AccountCreate,
) -> Any:
    """Create a new account."""
    return await account_service.create_account(db, current_user.id, body)


@router.get("/{account_id}", response_model=AccountResponse)
async def get_account(
    account_id: int,
    current_user: CurrentUser,
    db: DBSession,
) -> Any:
    """Get a specific account."""
    return await account_service.get_account(db, account_id, current_user.id)


@router.patch("/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: int,
    current_user: CurrentUser,
    db: DBSession,
    body: AccountUpdate,
) -> Any:
    """Update an account."""
    return await account_service.update_account(db, account_id, current_user.id, body)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: int,
    current_user: CurrentUser,
    db: DBSession,
) -> None:
    """Delete an account."""
    await account_service.delete_account(db, account_id, current_user.id)
