"""Transaction REST endpoints for web frontend."""

from typing import Annotated, Any
from datetime import date

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import Response

from app.api.deps import CurrentUser, DBSession
from app.schemas.transaction import (
    TransactionListResponse,
    TransactionRestCreate,
    TransactionRestResponse,
    TransactionRestUpdate,
    TransactionSummaryResponse,
)
from app.services.transaction_rest import TransactionRestService, _to_frontend_response

router = APIRouter()


def get_transaction_rest_service(db: DBSession) -> TransactionRestService:
    """Create TransactionRestService instance."""
    return TransactionRestService(db)


TransactionRestSvc = Annotated[TransactionRestService, Depends(get_transaction_rest_service)]


@router.get("/summary", response_model=TransactionSummaryResponse)
async def get_summary(
    current_user: CurrentUser,
    service: TransactionRestSvc,
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
) -> Any:
    """Get dashboard summary for the authenticated user."""
    return await service.get_summary(current_user.id, date_from=date_from, date_to=date_to)


@router.get("", response_model=TransactionListResponse)
async def list_transactions(
    current_user: CurrentUser,
    service: TransactionRestSvc,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    type: str | None = Query(None, pattern="^(EXPENSE|INCOME)$"),
    search: str | None = Query(None, min_length=1),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
) -> Any:
    """List transactions for the authenticated user."""
    return await service.list_for_user(
        current_user.id,
        skip=skip,
        limit=limit,
        type_filter=type,
        search=search,
        date_from=date_from,
        date_to=date_to,
    )


@router.post("", response_model=TransactionRestResponse, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    current_user: CurrentUser,
    service: TransactionRestSvc,
    body: TransactionRestCreate,
) -> Any:
    """Create a new transaction."""
    return await service.create_for_user(current_user.id, body)


@router.get("/export.csv")
async def export_transactions_csv(
    current_user: CurrentUser,
    service: TransactionRestSvc,
) -> Any:
    """Export authenticated user's transactions as CSV."""
    csv_content = await service.export_csv_for_user(current_user.id)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="bagcoin-transacoes.csv"'},
    )


@router.get("/{transaction_id}", response_model=TransactionRestResponse)
async def get_transaction(
    transaction_id: int,
    current_user: CurrentUser,
    service: TransactionRestSvc,
) -> Any:
    """Get a specific transaction."""
    tx = await service.get_for_user(transaction_id, current_user.id)
    return _to_frontend_response(tx)


@router.patch("/{transaction_id}", response_model=TransactionRestResponse)
async def update_transaction(
    transaction_id: int,
    current_user: CurrentUser,
    service: TransactionRestSvc,
    body: TransactionRestUpdate,
) -> Any:
    """Update a transaction."""
    return await service.update_for_user(transaction_id, current_user.id, body)


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: int,
    current_user: CurrentUser,
    service: TransactionRestSvc,
) -> None:
    """Delete a transaction."""
    await service.delete_for_user(transaction_id, current_user.id)
