"""Financial transaction tools for BagCoin chat agents."""

from __future__ import annotations

from datetime import UTC, datetime

from langchain_core.tools import BaseTool, tool

from app.agents import responses as resp
from app.agents.pending_actions import save_pending_action
from app.agents.persistence import get_user_transactions


def _money(value: float) -> str:
    return f"R$ {float(value):,.2f}"


def _channel_from_context(context: dict | None) -> str:
    channel = (context or {}).get("channel") or "whatsapp"
    return str(channel) if channel in {"whatsapp", "telegram"} else "whatsapp"


def _date_from_recurring_day(day: int | None) -> str | None:
    if day is None:
        return None
    try:
        safe_day = max(1, min(int(day), 28))
    except (TypeError, ValueError):
        return None
    now = datetime.now(UTC)
    return now.replace(day=safe_day).date().isoformat()


def _today_iso_date() -> str:
    return datetime.now(UTC).date().isoformat()


def create_financial_tools(phone_number: str, context: dict | None = None) -> list[BaseTool]:
    """Create transaction tools with tenant context captured in closures."""
    channel = _channel_from_context(context)

    @tool
    def prepare_register_transaction(
        amount: float,
        description: str,
        transaction_type: str = "EXPENSE",
        category: str = "Outros",
        date: str | None = None,
        is_recurring: bool = False,
        recurrence_frequency: str | None = None,
        recurrence_day: int | None = None,
    ) -> str:
        """Prepare a transaction for user confirmation before saving it.

        Args:
            amount: Positive BRL amount.
            description: Short transaction description.
            transaction_type: EXPENSE for spending or INCOME for income.
            category: Financial category name.
            date: Optional date in YYYY-MM-DD format.
            is_recurring: True when this is a repeated income or expense.
            recurrence_frequency: weekly, monthly or yearly when recurring.
            recurrence_day: Day of month for monthly recurring transactions.
        """
        if amount <= 0:
            return "Qual foi o valor da transacao?"
        tx_type = "INCOME" if str(transaction_type).upper() == "INCOME" else "EXPENSE"
        clean_description = (description or "").strip() or "Sem descricao"
        clean_category = (category or "Outros").strip() or "Outros"
        clean_frequency = str(recurrence_frequency or "monthly").lower()
        if clean_frequency not in {"weekly", "monthly", "yearly"}:
            clean_frequency = "monthly"
        transaction_date = date or (_date_from_recurring_day(recurrence_day) if is_recurring else _today_iso_date())
        params = {
            "amount": float(amount),
            "description": clean_description,
            "type": tx_type,
            "category": clean_category,
            "date": transaction_date,
            "currency": "BRL",
            "confidence": 0.9,
            "raw_text": clean_description,
            "source_format": "text",
            "is_recurring": bool(is_recurring),
            "recurrence_frequency": clean_frequency if is_recurring else None,
            "recurrence_day": recurrence_day if is_recurring else None,
        }
        summary = resp.transaction_confirmation(
            tx_type,
            float(amount),
            clean_category,
            clean_description,
            transaction_date,
        )
        return save_pending_action(
            phone_number,
            action="register_transaction",
            params=params,
            summary=summary,
            channel=channel,
        )

    @tool
    def get_recent_transactions(limit: int = 5, transaction_type: str | None = None) -> str:
        """List recent user transactions.

        Args:
            limit: Maximum number of transactions to show.
            transaction_type: Optional EXPENSE or INCOME filter.
        """
        txs = get_user_transactions(phone_number, limit=max(1, min(int(limit or 5), 10)))
        if transaction_type:
            txs = [
                tx
                for tx in txs
                if str(getattr(getattr(tx, "type", ""), "value", getattr(tx, "type", ""))).upper()
                == transaction_type.upper()
            ]
        if not txs:
            return "Nenhuma transacao recente encontrada."
        lines = ["Transacoes recentes:"]
        for tx in txs:
            tx_type = str(getattr(getattr(tx, "type", ""), "value", getattr(tx, "type", ""))).upper()
            sign = "+" if tx_type == "INCOME" else "-"
            when = getattr(tx, "transaction_date", None) or datetime.now(UTC)
            lines.append(
                f"- id={tx.id}: {sign}{_money(float(tx.amount))} - {tx.description or 'Sem descricao'} ({when:%d/%m})"
            )
        return "\n".join(lines)

    @tool
    def prepare_update_transaction(
        description: str | None = None,
        amount: float | None = None,
        category: str | None = None,
        new_description: str | None = None,
        transaction_id: int | None = None,
    ) -> str:
        """Prepare a transaction update for confirmation before applying it."""
        if amount is None and not category and not new_description:
            return "O que voce quer corrigir nessa transacao: valor, categoria ou descricao?"
        parts = []
        if amount is not None:
            parts.append(f"valor para {_money(float(amount))}")
        if category:
            parts.append(f"categoria para {category}")
        if new_description:
            parts.append(f"descricao para {new_description}")
        target = f"id={transaction_id}" if transaction_id else (description or "transacao recente")
        summary = f"Vou atualizar {target}: {', '.join(parts)}."
        return save_pending_action(
            phone_number,
            action="update_transaction",
            params={
                "transaction_id": transaction_id,
                "description": description,
                "amount": amount,
                "category": category,
                "new_description": new_description,
            },
            summary=summary,
            channel=channel,
        )

    @tool
    def prepare_delete_transaction(description: str | None = None, transaction_id: int | None = None) -> str:
        """Prepare deletion of a recent transaction for confirmation."""
        target = f"id={transaction_id}" if transaction_id else (description or "transacao recente")
        return save_pending_action(
            phone_number,
            action="delete_transaction",
            params={"transaction_id": transaction_id, "description": description},
            summary=f"Vou remover {target}.",
            channel=channel,
        )

    return [
        prepare_register_transaction,
        get_recent_transactions,
        prepare_update_transaction,
        prepare_delete_transaction,
    ]
