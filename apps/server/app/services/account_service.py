"""REST service for Account operations."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.repositories import account as account_repo
from app.schemas.account import AccountCreate, AccountResponse, AccountUpdate


async def list_accounts(
    db: AsyncSession,
    user_id: int,
    *,
    skip: int = 0,
    limit: int = 50,
) -> list[AccountResponse]:
    """List accounts for a user."""
    accounts = await account_repo.get_multi_by_user(db, user_id, skip=skip, limit=limit)
    return [AccountResponse.model_validate(a) for a in accounts]


async def create_account(
    db: AsyncSession,
    user_id: int,
    data: AccountCreate,
) -> AccountResponse:
    """Create a new account."""
    account = await account_repo.create(
        db,
        user_id=user_id,
        name=data.name,
        bank=data.bank,
        type=data.type,
        balance=data.balance,
        color=data.color,
        active=data.active,
    )
    return AccountResponse.model_validate(account)


async def get_account(db: AsyncSession, account_id: int, user_id: int) -> AccountResponse:
    """Get an account by ID."""
    account = await account_repo.get_by_id(db, account_id)
    if not account or account.user_id != user_id:
        raise NotFoundError(message="Account not found", details={"id": str(account_id)})
    return AccountResponse.model_validate(account)


async def update_account(
    db: AsyncSession,
    account_id: int,
    user_id: int,
    data: AccountUpdate,
) -> AccountResponse:
    """Update an account."""
    account = await account_repo.get_by_id(db, account_id)
    if not account or account.user_id != user_id:
        raise NotFoundError(message="Account not found", details={"id": str(account_id)})
    update_data = data.model_dump(exclude_unset=True)
    account = await account_repo.update(db, db_account=account, update_data=update_data)
    return AccountResponse.model_validate(account)


async def delete_account(db: AsyncSession, account_id: int, user_id: int) -> None:
    """Delete an account."""
    account = await account_repo.get_by_id(db, account_id)
    if not account or account.user_id != user_id:
        raise NotFoundError(message="Account not found", details={"id": str(account_id)})
    await account_repo.delete(db, account_id)
