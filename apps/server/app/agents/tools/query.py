"""Query tools for BagCoin chat agents."""

from __future__ import annotations

import csv
import io
from datetime import UTC, datetime

from langchain_core.tools import BaseTool, tool
from sqlalchemy import func

from app.agents import responses as resp
from app.agents.persistence import (
    get_or_create_user,
    get_user_transactions,
)
from app.db.models.category import Category
from app.db.models.transaction import Transaction
from app.db.session import sync_session_maker
from app.services.budget_service import get_budgets, get_goals


def _money(value: float) -> str:
    return f"R$ {float(value):,.2f}"


def create_query_tools(phone_number: str) -> list[BaseTool]:
    @tool
    def get_financial_snapshot() -> str:
        """Return a compact snapshot with recent transactions, budgets and goals."""
        txs = get_user_transactions(phone_number, limit=5)
        budgets = get_budgets(phone_number)
        goals = get_goals(phone_number)
        parts = []
        if txs:
            tx_lines = ["Transacoes recentes:"]
            for tx in txs:
                tx_lines.append(f"- {_money(float(tx.amount))}: {tx.description or 'Sem descricao'}")
            parts.append("\n".join(tx_lines))
        parts.append(resp.budget_list(budgets))
        parts.append(resp.goal_list(goals))
        return "\n\n".join(parts)

    @tool
    def get_balance_summary() -> str:
        """Return income, expenses and balance for the current month."""
        db = sync_session_maker()
        try:
            user = get_or_create_user(phone_number, db)
            start = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            income = (
                db.query(func.coalesce(func.sum(Transaction.amount), 0))
                .filter(Transaction.user_id == user.id, Transaction.type == "INCOME", Transaction.transaction_date >= start)
                .scalar()
            )
            expense = (
                db.query(func.coalesce(func.sum(Transaction.amount), 0))
                .filter(Transaction.user_id == user.id, Transaction.type == "EXPENSE", Transaction.transaction_date >= start)
                .scalar()
            )
            income_f = float(income or 0)
            expense_f = float(expense or 0)
            return (
                "Resumo do mes:\n"
                f"Receitas: {_money(income_f)}\n"
                f"Gastos: {_money(expense_f)}\n"
                f"Saldo: {_money(income_f - expense_f)}"
            )
        finally:
            db.close()

    @tool
    def get_spending_by_category() -> str:
        """Return current-month expense totals grouped by category."""
        db = sync_session_maker()
        try:
            user = get_or_create_user(phone_number, db)
            start = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            rows = (
                db.query(Category.name, func.coalesce(func.sum(Transaction.amount), 0).label("total"))
                .join(Category, Transaction.category_id == Category.id)
                .filter(Transaction.user_id == user.id, Transaction.type == "EXPENSE", Transaction.transaction_date >= start)
                .group_by(Category.name)
                .order_by(func.sum(Transaction.amount).desc())
                .all()
            )
            if not rows:
                return "Nenhum gasto encontrado no mes atual."
            return "\n".join(["Gastos por categoria:"] + [f"- {name}: {_money(float(total or 0))}" for name, total in rows])
        finally:
            db.close()

    @tool
    def export_transactions_csv(limit: int = 200) -> str:
        """Export user transactions to CSV text that can be copied/imported."""
        db = sync_session_maker()
        try:
            user = get_or_create_user(phone_number, db)
            safe_limit = max(1, min(int(limit or 200), 2000))
            txs = (
                db.query(Transaction)
                .filter(Transaction.user_id == user.id)
                .order_by(Transaction.transaction_date.desc())
                .limit(safe_limit)
                .all()
            )
            if not txs:
                return "Nao encontrei transacoes para exportar."
            buffer = io.StringIO()
            writer = csv.writer(buffer)
            writer.writerow(["id", "tipo", "valor", "descricao", "categoria", "data"])
            for tx in txs:
                tx_type = str(getattr(getattr(tx, "type", ""), "value", getattr(tx, "type", ""))).upper()
                cat = getattr(getattr(tx, "category", None), "name", None) or "Outros"
                dt = getattr(tx, "transaction_date", None)
                writer.writerow(
                    [
                        tx.id,
                        tx_type,
                        f"{float(tx.amount or 0):.2f}",
                        tx.description or "",
                        cat,
                        dt.date().isoformat() if dt else "",
                    ]
                )
            return (
                "CSV gerado abaixo:\n\n"
                f"```csv\n{buffer.getvalue().strip()}\n```\n\n"
                "Se preferir, também posso orientar a exportação direta pela web no Dashboard."
            )
        finally:
            db.close()

    return [get_financial_snapshot, get_balance_summary, get_spending_by_category, export_transactions_csv]
