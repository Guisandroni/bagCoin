"""Reports agent — generates financial PDF reports for BagCoin.

Uses sync_session_maker for database access.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from app.agents.persistence import get_or_create_user
from app.agents.text_to_sql import fetch_financial_transactions_for_query, resolve_financial_query_period
from app.db.models.budget import Budget
from app.db.models.enums import GoalStatus
from app.db.models.goal import Goal
from app.db.session import sync_session_maker
from app.services.pdf_generator import generate_financial_report
from app.services.report_time import report_now

logger = logging.getLogger(__name__)


def _get_period_from_message(message: str) -> tuple:
    """Extrai período de início e fim baseado na mensagem do usuário."""
    period = resolve_financial_query_period(message, today=report_now().date())
    start = period.start or report_now().date()
    end = period.end or report_now().date()
    period_start = datetime.combine(start, datetime.min.time(), tzinfo=report_now().tzinfo)
    period_end = datetime.combine(end, datetime.max.time(), tzinfo=report_now().tzinfo)
    if period.end == report_now().date():
        period_end = report_now()
    return period_start, period_end, period.label


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=report_now().tzinfo)
    return value.astimezone(UTC)


def _format_report_date(value: datetime) -> str:
    return value.strftime("%d/%m/%Y")


def _fmt_money(value: float) -> str:
    formatted = f"{float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatted}"


def _format_report_summary(
    period_start: datetime,
    period_end: datetime,
    period_label: str,
    total_income: float,
    total_expense: float,
) -> str:
    balance = total_income - total_expense
    return (
        "📄 Relatório financeiro gerado com sucesso!\n\n"
        f"Período: {period_start.strftime('%d/%m/%Y')} a {period_end.strftime('%d/%m/%Y')} ({period_label})\n\n"
        f"Receitas: {_fmt_money(total_income)}\n"
        f"Despesas: {_fmt_money(total_expense)}\n"
        f"Saldo: {_fmt_money(balance)}\n\n"
        "PDF gerado com sucesso!"
    )


def _row_type(row: dict[str, Any]) -> str:
    value = row.get("type")
    return str(getattr(value, "value", value))


def _row_date(row: dict[str, Any]) -> datetime:
    value = row.get("transaction_date")
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return report_now()


def _period_datetimes_from_rows(
    period_start: datetime,
    period_end: datetime,
    period_label: str,
    rows: list[dict[str, Any]],
) -> tuple[datetime, datetime]:
    if period_label != "todo histórico" or not rows:
        return period_start, period_end
    dates = [_row_date(row) for row in rows if row.get("transaction_date")]
    if not dates:
        return period_start, period_end
    start = min(dates).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )
    end = max(dates).replace(
        hour=23,
        minute=59,
        second=59,
        microsecond=999999,
    )
    return start, end


def generate_report(state: dict[str, Any]) -> dict[str, Any]:
    """Gera relatório financeiro em PDF."""
    db = sync_session_maker()
    try:
        phone_number = state.get("phone_number")
        user = get_or_create_user(phone_number, db)
        message = state.get("message", "")

        query_result = fetch_financial_transactions_for_query(message, phone_number)
        transactions = query_result["rows"]
        period_start, period_end, period_label = _get_period_from_message(message)
        period_start, period_end = _period_datetimes_from_rows(
            period_start,
            period_end,
            period_label,
            transactions,
        )

        period_start_query = _to_utc(period_start)
        period_end_query = _to_utc(period_end)

        # Calcula totais
        total_income = sum(float(t.get("amount") or 0) for t in transactions if _row_type(t) == "INCOME")
        total_expense = sum(float(t.get("amount") or 0) for t in transactions if _row_type(t) == "EXPENSE")

        # Agrupa por categoria
        category_totals = {}
        for t in transactions:
            if _row_type(t) == "EXPENSE":
                cat_name = str(t.get("category") or "Outros")
                category_totals[cat_name] = category_totals.get(cat_name, 0) + float(t.get("amount") or 0)

        categories_summary = [
            {"name": name, "total": total}
            for name, total in sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
        ]

        # Formata transações para o PDF
        tx_formatted = [
            {
                "date": _format_report_date(_row_date(t)),
                "type": _row_type(t),
                "category": str(t.get("category") or "Outros"),
                "description": str(t.get("description") or "-"),
                "amount": float(t.get("amount") or 0),
            }
            for t in transactions
        ]

        # Busca orçamentos
        budgets = (
            db.query(Budget)
            .filter(Budget.user_id == user.id)
            .order_by(Budget.created_at.desc())
            .all()
        )

        budgets_info = []
        for budget in budgets:
            if budget.category_id:
                spent = sum(
                    abs(float(t.get("amount") or 0))
                    for t in transactions
                    if _row_type(t) == "EXPENSE" and t.get("category_id") == budget.category_id
                )
            else:
                spent = sum(abs(float(t.get("amount") or 0)) for t in transactions if _row_type(t) == "EXPENSE")
            limit = abs(float(budget.total_limit or 0))
            remaining = limit - spent
            percentage = round((spent / limit) * 100, 1) if limit > 0 else 0
            budgets_info.append(
                {
                    "name": budget.category.name if budget.category else budget.name,
                    "limit": limit,
                    "spent": spent,
                    "remaining": remaining,
                    "percentage": percentage,
                }
            )

        # Busca metas
        goals = (
            db.query(Goal)
            .filter(Goal.user_id == user.id, Goal.status == GoalStatus.ACTIVE.value)
            .all()
        )

        goals_info = [
            {
                "title": g.title,
                "target": g.target_amount,
                "current": g.current_amount,
                "deadline": g.deadline,
            }
            for g in goals
        ]

        # Gera PDF
        report_path = generate_financial_report(
            user_name=user.full_name or user.phone_number or str(user.id),
            period_start=period_start.strftime("%d/%m/%Y"),
            period_end=period_end.strftime("%d/%m/%Y"),
            transactions=tx_formatted,
            categories_summary=categories_summary,
            total_income=total_income,
            total_expense=total_expense,
            budgets_info=budgets_info,
            goals_info=goals_info,
            generated_at=report_now(),
        )

        # Gera CSV também
        csv_path = report_path.replace(".pdf", ".csv")
        try:
            import csv as csv_module

            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv_module.writer(f)
                writer.writerow(["Data", "Tipo", "Categoria", "Descrição", "Valor"])
                for tx in tx_formatted:
                    writer.writerow(
                        [
                            tx["date"],
                            "Receita" if tx["type"] == "INCOME" else "Despesa",
                            tx["category"],
                            tx["description"],
                            f"R$ {tx['amount']:,.2f}",
                        ]
                    )
                writer.writerow([])
                writer.writerow(["Resumo", "", "", "", ""])
                writer.writerow(["Receitas", "", "", "", f"R$ {total_income:,.2f}"])
                writer.writerow(["Despesas", "", "", "", f"R$ {total_expense:,.2f}"])
                writer.writerow(["Saldo", "", "", "", f"R$ {(total_income - total_expense):,.2f}"])
            logger.info(f"CSV gerado: {csv_path}")
        except Exception as csv_err:
            logger.warning(f"Erro ao gerar CSV: {csv_err}")

        state["report_path"] = report_path
        state["report_summary"] = _format_report_summary(
            period_start,
            period_end,
            period_label,
            total_income,
            total_expense,
        )

        # Persist Report row so bridges can download via HTTP (Fase 7)
        try:
            from app.services.report_sync import create_report_sync

            report_row = create_report_sync(
                db,
                user_id=user.id,
                period_start=period_start_query,
                period_end=period_end_query,
                file_url=report_path,
            )
            db.commit()
            state["report_id"] = report_row.id
            logger.info(f"Report row {report_row.id} created for file {report_path}")
        except Exception as exc:
            db.rollback()
            logger.warning(f"Could not persist Report row (non-blocking): {exc}")

        logger.info(f"Relatório gerado: {report_path}")

    except Exception as e:
        logger.error(f"Erro ao gerar relatório: {e}")
        state["error"] = f"Erro ao gerar relatório: {e!s}"
    finally:
        db.close()

    return state
