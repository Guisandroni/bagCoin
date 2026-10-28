"""Transaction REST service for web frontend."""

import contextlib
import csv
import io
from datetime import UTC, date, datetime, time
from typing import Literal

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.core.financial_categories import category_color
from app.db.models.category import Category
from app.db.models.transaction import Transaction
from app.schemas.transaction import (
    TransactionListResponse,
    TransactionRestCreate,
    TransactionRestResponse,
    TransactionRestUpdate,
    TransactionSummaryResponse,
)
from app.services.agent_memory_service import add_memory_event_async
from app.services.category_rest import get_or_create_category_for_user
from app.services.recurring_transactions import create_recurring_transaction, next_run_from


def _transaction_type(tx: Transaction) -> Literal["EXPENSE", "INCOME"]:
    value = str(getattr(tx.type, "value", tx.type))
    return "INCOME" if value == "INCOME" else "EXPENSE"


def _transaction_amount(tx: Transaction) -> float:
    return abs(float(tx.amount or 0))


def _transaction_category_name(tx: Transaction) -> str:
    category = getattr(tx, "category", None)
    name = getattr(category, "name", None)
    return name if isinstance(name, str) and name else "Outros"


def _transaction_category_id(tx: Transaction) -> int | None:
    category_id = getattr(tx, "category_id", None)
    return category_id if isinstance(category_id, int) else None


def _transaction_recurrence_frequency(tx: Transaction) -> Literal["weekly", "monthly", "yearly"] | None:
    recurring_id = getattr(tx, "recurring_transaction_id", None)
    if not isinstance(recurring_id, int):
        return None
    recurring = getattr(tx, "recurring_transaction", None)
    frequency = getattr(recurring, "frequency", None)
    return frequency if frequency in ("weekly", "monthly", "yearly") else None


def _format_transaction_date_pt_br(tx: Transaction) -> str:
    if not tx.transaction_date:
        return ""
    months = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
    return f"{tx.transaction_date.day:02d} {months[tx.transaction_date.month - 1]}"


def _to_frontend_response(tx: Transaction) -> TransactionRestResponse:
    category_name = _transaction_category_name(tx)
    recurrence_frequency = _transaction_recurrence_frequency(tx)
    recurring_id = getattr(tx, "recurring_transaction_id", None)
    return TransactionRestResponse(
        id=str(tx.id),
        type=_transaction_type(tx),
        name=tx.description or "Sem descrição",
        category=category_name,
        category_id=_transaction_category_id(tx),
        category_name=category_name,
        amount=_transaction_amount(tx),
        date=_format_transaction_date_pt_br(tx),
        transaction_date=tx.transaction_date.date().isoformat() if tx.transaction_date else None,
        source=tx.source_format if tx.source_format != "text" else "manual",
        status="confirmed" if tx.confidence_score >= 0.7 else "pending",
        is_recurring=isinstance(recurring_id, int),
        recurrence_frequency=recurrence_frequency,
        created_at=tx.created_at,
        updated_at=tx.updated_at,
    )


class TransactionRestService:
    """Service for transaction REST API (web frontend)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_for_user(
        self,
        user_id: int,
        *,
        skip: int = 0,
        limit: int = 50,
        type_filter: str | None = None,
        search: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> TransactionListResponse:
        query = (
            select(Transaction)
            .options(selectinload(Transaction.category), selectinload(Transaction.recurring_transaction))
            .where(Transaction.user_id == user_id)
        )
        if type_filter and type_filter in ("EXPENSE", "INCOME"):
            query = query.where(Transaction.type == type_filter)
        if search:
            query = query.where(Transaction.description.ilike(f"%{search}%"))
        query = self._apply_date_filters(query, date_from=date_from, date_to=date_to)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        query = query.order_by(Transaction.transaction_date.desc().nulls_last()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        items = [_to_frontend_response(tx) for tx in result.scalars().all()]
        return TransactionListResponse(items=items, total=total)

    async def get_for_user(self, transaction_id: int, user_id: int) -> Transaction:
        result = await self.db.execute(
            select(Transaction)
            .options(selectinload(Transaction.category), selectinload(Transaction.recurring_transaction))
            .where(and_(Transaction.id == transaction_id, Transaction.user_id == user_id))
        )
        tx = result.scalar_one_or_none()
        if not tx:
            raise NotFoundError(message="Transaction not found", details={"id": transaction_id})
        return tx

    async def create_for_user(self, user_id: int, data: TransactionRestCreate) -> TransactionRestResponse:
        tx_date = None
        if data.transaction_date:
            try:
                tx_date = datetime.strptime(data.transaction_date, "%Y-%m-%d")
            except ValueError:
                tx_date = datetime.now(UTC)

        category_id = None
        if data.category_id:
            category_id = (await self._get_user_category(user_id, data.category_id)).id
        elif data.category_name:
            category = await get_or_create_category_for_user(self.db, user_id, data.category_name)
            category_id = category.id if category else None

        transaction = Transaction(
            user_id=user_id,
            type=data.type,
            amount=abs(data.amount),
            description=data.description,
            category_id=category_id,
            source_format=data.source,
            confidence_score=1.0 if data.status == "confirmed" else 0.5,
            transaction_date=tx_date or datetime.now(UTC),
        )
        self.db.add(transaction)
        await self.db.flush()
        await self.db.refresh(transaction)
        await add_memory_event_async(
            self.db,
            user_id=user_id,
            event_type="transaction_created",
            entity_type="transaction",
            entity_id=transaction.id,
            source="web",
            summary=(
                f"{transaction.type} R$ {float(transaction.amount):.2f}: "
                f"{transaction.description or 'Sem descricao'}"
            ),
            payload={
                "transaction_id": transaction.id,
                "type": transaction.type,
                "amount": float(transaction.amount),
                "description": transaction.description,
                "source_format": transaction.source_format,
                "transaction_date": transaction.transaction_date.isoformat()
                if transaction.transaction_date
                else None,
            },
        )

        if data.is_recurring:
            recurring = await create_recurring_transaction(
                self.db,
                user_id=user_id,
                type=data.type,
                amount=data.amount,
                category_id=category_id,
                description=data.description,
                frequency=data.recurrence_frequency or "monthly",
                start_date=transaction.transaction_date or datetime.now(UTC),
            )
            transaction.recurring_transaction_id = recurring.id
            await self.db.flush()

        loaded_transaction = await self.get_for_user(transaction.id, user_id)
        return _to_frontend_response(loaded_transaction)

    async def _get_user_category(self, user_id: int, category_id: int) -> Category:
        result = await self.db.execute(
            select(Category).where(Category.id == category_id, Category.user_id == user_id)
        )
        category = result.scalar_one_or_none()
        if not category:
            raise NotFoundError(message="Category not found", details={"id": category_id})
        return category

    async def update_for_user(
        self, transaction_id: int, user_id: int, data: TransactionRestUpdate
    ) -> TransactionRestResponse:
        transaction = await self.get_for_user(transaction_id, user_id)
        update_data = data.model_dump(exclude_unset=True)

        if update_data.get("type"):
            transaction.type = update_data["type"]
        if update_data.get("amount"):
            transaction.amount = abs(update_data["amount"])
        if update_data.get("description"):
            transaction.description = update_data["description"]
        if update_data.get("category_id"):
            category = await self._get_user_category(user_id, update_data["category_id"])
            transaction.category_id = category.id
        elif "category_name" in update_data:
            category = await get_or_create_category_for_user(self.db, user_id, update_data.get("category_name"))
            transaction.category_id = category.id if category else None
        if "status" in update_data:
            transaction.confidence_score = 1.0 if update_data["status"] == "confirmed" else 0.5
        if update_data.get("transaction_date"):
            with contextlib.suppress(ValueError):
                transaction.transaction_date = datetime.strptime(update_data["transaction_date"], "%Y-%m-%d")
        if "is_recurring" in update_data:
            if update_data["is_recurring"]:
                frequency = update_data.get("recurrence_frequency") or "monthly"
                if transaction.recurring_transaction:
                    transaction.recurring_transaction.type = transaction.type
                    transaction.recurring_transaction.amount = abs(transaction.amount)
                    transaction.recurring_transaction.category_id = transaction.category_id
                    transaction.recurring_transaction.description = transaction.description or "Sem descrição"
                    transaction.recurring_transaction.frequency = frequency
                    transaction.recurring_transaction.next_run_at = next_run_from(
                        transaction.transaction_date or datetime.now(UTC), frequency
                    )
                    transaction.recurring_transaction.active = True
                    self.db.add(transaction.recurring_transaction)
                else:
                    recurring = await create_recurring_transaction(
                        self.db,
                        user_id=user_id,
                        type=transaction.type,
                        amount=abs(transaction.amount),
                        category_id=transaction.category_id,
                        description=transaction.description or "Sem descrição",
                        frequency=frequency,
                        start_date=transaction.transaction_date or datetime.now(UTC),
                    )
                    transaction.recurring_transaction_id = recurring.id
            else:
                if transaction.recurring_transaction:
                    transaction.recurring_transaction.active = False
                    self.db.add(transaction.recurring_transaction)
                transaction.recurring_transaction_id = None

        self.db.add(transaction)
        await self.db.flush()
        await self.db.refresh(transaction)
        await add_memory_event_async(
            self.db,
            user_id=user_id,
            event_type="transaction_updated",
            entity_type="transaction",
            entity_id=transaction.id,
            source="web",
            summary=(
                f"Transação atualizada: R$ {float(transaction.amount):.2f} - "
                f"{transaction.description or 'Sem descricao'}"
            ),
            payload={"transaction_id": transaction.id, "changes": update_data},
        )
        loaded_transaction = await self.get_for_user(transaction.id, user_id)
        return _to_frontend_response(loaded_transaction)

    async def delete_for_user(self, transaction_id: int, user_id: int) -> None:
        transaction = await self.get_for_user(transaction_id, user_id)
        await add_memory_event_async(
            self.db,
            user_id=user_id,
            event_type="transaction_deleted",
            entity_type="transaction",
            entity_id=transaction.id,
            source="web",
            summary=(
                f"Transação removida: R$ {float(transaction.amount):.2f} - "
                f"{transaction.description or 'Sem descricao'}"
            ),
            payload={"transaction_id": transaction.id},
        )
        await self.db.delete(transaction)
        await self.db.flush()

    def _apply_date_filters(self, query, *, date_from: date | None, date_to: date | None):
        if date_from:
            query = query.where(Transaction.transaction_date >= datetime.combine(date_from, time.min))
        if date_to:
            query = query.where(Transaction.transaction_date <= datetime.combine(date_to, time.max))
        return query

    async def get_summary(
        self, user_id: int, *, date_from: date | None = None, date_to: date | None = None
    ) -> TransactionSummaryResponse:
        query = (
            select(Transaction)
            .options(selectinload(Transaction.category), selectinload(Transaction.recurring_transaction))
            .where(Transaction.user_id == user_id)
        )
        query = self._apply_date_filters(query, date_from=date_from, date_to=date_to)
        result = await self.db.execute(query)
        transactions = result.scalars().all()

        total_income = sum(_transaction_amount(tx) for tx in transactions if _transaction_type(tx) == "INCOME")
        total_expenses = sum(_transaction_amount(tx) for tx in transactions if _transaction_type(tx) == "EXPENSE")
        balance = total_income - total_expenses

        cat_map: dict[str, float] = {}
        for tx in transactions:
            if _transaction_type(tx) == "EXPENSE":
                cat = _transaction_category_name(tx)
                cat_map[cat] = cat_map.get(cat, 0) + _transaction_amount(tx)

        categories = [
            {"name": name, "amount": amt, "color": category_color(name)}
            for name, amt in sorted(cat_map.items(), key=lambda x: -x[1])
        ]

        recent = sorted(transactions, key=lambda t: t.transaction_date or datetime.min, reverse=True)[:10]
        recent_responses = [_to_frontend_response(tx) for tx in recent]

        return TransactionSummaryResponse(
            balance=balance,
            total_income=total_income,
            total_expenses=total_expenses,
            transaction_count=len(transactions),
            categories=categories,
            recent_transactions=recent_responses,
        )

    async def export_csv_for_user(self, user_id: int) -> str:
        result = await self.db.execute(
            select(Transaction)
            .options(selectinload(Transaction.category), selectinload(Transaction.recurring_transaction))
            .where(Transaction.user_id == user_id)
            .order_by(Transaction.transaction_date.desc().nulls_last())
        )
        transactions = result.scalars().all()

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["id", "tipo", "descricao", "categoria", "valor", "data", "origem", "status", "recorrente", "frequencia_recorrencia"])
        for tx in transactions:
            writer.writerow([
                tx.id,
                _transaction_type(tx),
                tx.description or "",
                _transaction_category_name(tx),
                f"{_transaction_amount(tx):.2f}",
                tx.transaction_date.date().isoformat() if tx.transaction_date else "",
                tx.source_format,
                "confirmed" if tx.confidence_score >= 0.7 else "pending",
                "true" if isinstance(getattr(tx, "recurring_transaction_id", None), int) else "false",
                _transaction_recurrence_frequency(tx) or "",
            ])
        return buffer.getvalue()
