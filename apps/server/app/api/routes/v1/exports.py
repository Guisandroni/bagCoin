"""BagCoin consolidated export endpoints."""

from typing import Any

from fastapi import APIRouter
from fastapi.responses import Response

from app.api.deps import CurrentUser, DBSession
from app.services.export_rest import export_financial_csv_for_user

router = APIRouter(prefix="/bagcoin", tags=["bagcoin"])


@router.get("/export.csv")
async def export_financial_csv(
    current_user: CurrentUser,
    db: DBSession,
) -> Any:
    """Export authenticated user's transactions, goals and budgets as CSV."""
    csv_content = await export_financial_csv_for_user(db, current_user.id)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="bagcoin-financeiro.csv"'},
    )
