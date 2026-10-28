"""Sync version of recurring transaction helpers for use inside agent nodes."""

from datetime import UTC, datetime

from dateutil.relativedelta import relativedelta

from app.db.models.recurring_transaction import RecurringTransaction


def _next_run(start: datetime, frequency: str) -> datetime:
    if start.tzinfo is None:
        start = start.replace(tzinfo=UTC)
    if frequency == "weekly":
        return start + relativedelta(weeks=1)
    if frequency == "yearly":
        return start + relativedelta(years=1)
    return start + relativedelta(months=1)


def create_recurring_transaction_sync(
    db,
    *,
    user_id: int,
    type: str,
    amount: float,
    category_id: int | None,
    description: str,
    frequency: str,
    start_date: datetime,
) -> RecurringTransaction:
    """Create a RecurringTransaction rule (sync, for agent nodes)."""
    if start_date.tzinfo is None:
        start_date = start_date.replace(tzinfo=UTC)

    recurring = RecurringTransaction(
        user_id=user_id,
        type=type,
        amount=abs(amount),
        category_id=category_id,
        description=description,
        frequency=frequency,
        next_run_at=_next_run(start_date, frequency),
        active=True,
    )
    db.add(recurring)
    db.flush()
    db.refresh(recurring)
    return recurring
