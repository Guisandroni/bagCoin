"""Consolidated CSV export for BagCoin web data."""

from __future__ import annotations

import csv
import io
from datetime import date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.budget import Budget
from app.db.models.goal import Goal
from app.db.models.transaction import Transaction
from app.services.budget_rest import _calculate_spent
from app.services.transaction_rest import (
    _transaction_amount,
    _transaction_category_name,
    _transaction_recurrence_frequency,
    _transaction_type,
)


CSV_INJECTION_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _csv_cell(value: Any) -> str:
    text = "" if value is None else str(value)
    return f"'{text}" if text.startswith(CSV_INJECTION_PREFIXES) else text


def _money(value: float | int | None) -> str:
    return f"{float(value or 0):.2f}".replace(".", ",")


def _date_ptbr(value: date | datetime | None) -> str:
    if not value:
        return ""
    if isinstance(value, datetime):
        value = value.date()
    return value.strftime("%d/%m/%Y")


def _status_ptbr(value: Any) -> str:
    normalized = str(getattr(value, "value", value) or "").lower()
    return {
        "active": "ativa",
        "completed": "concluída",
        "cancelled": "cancelada",
        "confirmed": "confirmada",
        "pending": "pendente",
    }.get(normalized, normalized)


def _type_ptbr(value: Any) -> str:
    normalized = str(getattr(value, "value", value) or "").upper()
    return {
        "EXPENSE": "despesa",
        "INCOME": "receita",
    }.get(normalized, str(value or "").lower())


def _source_ptbr(value: Any) -> str:
    normalized = str(getattr(value, "value", value) or "").lower()
    return {
        "manual": "manual",
        "text": "texto",
        "image": "imagem",
        "document": "documento",
        "audio": "áudio",
        "auto": "automático",
        "whatsapp": "whatsapp",
    }.get(normalized, normalized)


def _period_ptbr(value: Any) -> str:
    normalized = str(value or "").lower()
    return {
        "daily": "diário",
        "weekly": "semanal",
        "monthly": "mensal",
        "yearly": "anual",
    }.get(normalized, normalized)


def _recurrence_ptbr(value: Any) -> str:
    normalized = str(value or "").lower()
    return _period_ptbr(normalized)


async def export_financial_csv_for_user(db: AsyncSession, user_id: int) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "seção", "data", "nome", "descrição", "categoria", "tipo", "valor",
        "status", "origem", "recorrente", "frequência",
        "valor atual", "valor alvo",
        "limite", "gasto", "restante", "período",
        "quantidade de transações", "valor total de despesas", "valor total de receitas", "saldo da categoria",
    ])

    category_totals: dict[str, dict[str, float | int]] = {}

    tx_result = await db.execute(
        select(Transaction)
        .options(selectinload(Transaction.category), selectinload(Transaction.recurring_transaction))
        .where(Transaction.user_id == user_id)
        .order_by(Transaction.transaction_date.desc().nulls_last())
    )
    for tx in tx_result.scalars().all():
        recurring_id = getattr(tx, "recurring_transaction_id", None)
        tx_type = _transaction_type(tx)
        amount = _transaction_amount(tx)
        category_name = _transaction_category_name(tx)
        category_bucket = category_totals.setdefault(
            category_name,
            {"count": 0, "expenses": 0.0, "income": 0.0},
        )
        category_bucket["count"] = int(category_bucket["count"]) + 1
        if tx_type == "INCOME":
            category_bucket["income"] = float(category_bucket["income"]) + amount
        else:
            category_bucket["expenses"] = float(category_bucket["expenses"]) + amount
        writer.writerow([
            "Transações",
            _date_ptbr(tx.transaction_date),
            _csv_cell(tx.description or ""), _csv_cell(tx.description or ""),
            _csv_cell(category_name), _type_ptbr(tx_type),
            _money(amount),
            "confirmada" if tx.confidence_score >= 0.7 else "pendente",
            _source_ptbr(tx.source_format),
            "sim" if isinstance(recurring_id, int) else "não",
            _recurrence_ptbr(_transaction_recurrence_frequency(tx)),
            "", "", "", "", "", "", "", "", "", "",
        ])

    goal_result = await db.execute(
        select(Goal).where(Goal.user_id == user_id).order_by(Goal.created_at.desc())
    )
    for goal in goal_result.scalars().all():
        writer.writerow([
            "Metas",
            _date_ptbr(goal.deadline),
            _csv_cell(goal.title), "", "", "",
            "",
            _status_ptbr(goal.status),
            "", "", "",
            _money(goal.current_amount), _money(goal.target_amount),
            "", "", "", "", "", "", "", "",
        ])

    budget_result = await db.execute(
        select(Budget)
        .options(selectinload(Budget.category))
        .where(Budget.user_id == user_id)
        .order_by(Budget.created_at.desc())
    )
    for budget in budget_result.scalars().all():
        spent = await _calculate_spent(db, budget)
        limit = abs(float(budget.total_limit or 0))
        spent_abs = abs(float(spent or 0))
        writer.writerow([
            "Orçamentos",
            _date_ptbr(getattr(budget, "budget_date", None) or getattr(budget, "created_at", None)),
            _csv_cell(budget.name), "",
            _csv_cell(budget.category.name if budget.category else budget.name),
            "orçamento", "", "", "", "", "", "", "",
            _money(limit), _money(spent_abs),
            _money(limit - spent_abs), _period_ptbr(budget.period or "monthly"),
            "", "", "", "",
        ])

    for category_name, totals in sorted(
        category_totals.items(),
        key=lambda item: (
            -int(item[1]["count"]),
            -(float(item[1]["expenses"]) + float(item[1]["income"])),
            item[0].lower(),
        ),
    ):
        expenses = float(totals["expenses"])
        income = float(totals["income"])
        writer.writerow([
            "Categorias mais utilizadas", "", _csv_cell(category_name), "",
            _csv_cell(category_name), "", "", "", "", "", "", "", "", "", "", "", "",
            int(totals["count"]), _money(expenses), _money(income), _money(income - expenses),
        ])

    return buffer.getvalue()
