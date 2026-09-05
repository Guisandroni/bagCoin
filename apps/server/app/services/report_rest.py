"""REST service for Report operations (web frontend, async)."""

import logging
import os
from datetime import datetime, timedelta

from fastapi.responses import FileResponse
from sqlalchemy import select as sa_select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.db.models.budget import Budget as BudgetModel
from app.db.models.enums import GoalStatus
from app.db.models.goal import Goal as GoalModel
from app.db.models.transaction import Transaction
from app.db.models.user import User as UserModel
from app.repositories import report as report_repo
from app.services.pdf_generator import generate_financial_report
from app.services.report_time import report_now

logger = logging.getLogger(__name__)


async def list_reports(db: AsyncSession, user_id: int, *, skip: int = 0, limit: int = 20) -> list[dict]:
    reports = await report_repo.get_reports_by_user(db, user_id=user_id, skip=skip, limit=limit)
    return [
        {
            "id": r.id,
            "period_start": r.period_start.isoformat() if r.period_start else None,
            "period_end": r.period_end.isoformat() if r.period_end else None,
            "file_url": r.file_url,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in reports
    ]


async def get_report_download(db: AsyncSession, report_id: int, user_id: int) -> FileResponse:
    report = await report_repo.get_report_by_id(db, report_id)
    if not report or report.user_id != user_id:
        raise NotFoundError(message="Report not found", details={"id": report_id})
    if not report.file_url or not os.path.exists(report.file_url):
        raise NotFoundError(message="Report file not found")
    return FileResponse(
        path=report.file_url,
        media_type="application/pdf",
        filename=os.path.basename(report.file_url),
    )


async def delete_report(db: AsyncSession, report_id: int, user_id: int) -> None:
    report = await report_repo.get_report_by_id(db, report_id)
    if not report or report.user_id != user_id:
        raise NotFoundError(message="Report not found", details={"id": report_id})
    await report_repo.delete_report(db, report_id)


async def generate_report_for_web_user(
    db: AsyncSession, user_id: int, *, month: int, year: int, report_type: str = "monthly"
) -> dict:
    period_start = datetime(year, month, 1)
    if month == 12:
        period_end = datetime(year, 12, 31, 23, 59, 59)
    else:
        period_end = datetime(year, month + 1, 1) - timedelta(seconds=1)

    user_result = await db.execute(sa_select(UserModel).where(UserModel.id == user_id))
    web_user = user_result.scalar_one_or_none()
    user_name = web_user.full_name or web_user.email or str(user_id) if web_user else str(user_id)

    tx_result = await db.execute(
        sa_select(Transaction)
        .options(selectinload(Transaction.category))
        .where(
            Transaction.user_id == user_id,
            Transaction.transaction_date >= period_start,
            Transaction.transaction_date <= period_end,
        )
        .order_by(Transaction.transaction_date.desc())
    )
    transactions = list(tx_result.scalars().all())

    total_income = sum(t.amount for t in transactions if str(t.type) == "INCOME")
    total_expense = sum(t.amount for t in transactions if str(t.type) == "EXPENSE")

    category_totals: dict[str, float] = {}
    for t in transactions:
        if str(t.type) == "EXPENSE":
            cat_name = t.category.name if t.category else "Outros"
            category_totals[cat_name] = category_totals.get(cat_name, 0) + t.amount

    categories_summary = [
        {"name": name, "total": total}
        for name, total in sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
    ]

    tx_formatted = [
        {
            "date": t.transaction_date.strftime("%d/%m/%Y"),
            "type": str(t.type),
            "category": t.category.name if t.category else "Outros",
            "description": t.description or "-",
            "amount": t.amount,
        }
        for t in transactions
    ]

    budget_result = await db.execute(
        sa_select(BudgetModel)
        .options(selectinload(BudgetModel.category))
        .where(BudgetModel.user_id == user_id)
        .order_by(BudgetModel.created_at.desc())
    )
    budgets = list(budget_result.scalars().all())
    budgets_info = []
    for budget in budgets:
        if budget.category_id:
            spent = sum(
                abs(float(t.amount or 0))
                for t in transactions
                if str(t.type) == "EXPENSE" and t.category_id == budget.category_id
            )
        else:
            spent = sum(abs(float(t.amount or 0)) for t in transactions if str(t.type) == "EXPENSE")
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

    goals_result = await db.execute(
        sa_select(GoalModel).where(GoalModel.user_id == user_id, GoalModel.status == GoalStatus.ACTIVE.value)
    )
    goals_info = [
        {
            "title": g.title,
            "target": g.target_amount,
            "current": g.current_amount,
            "deadline": g.deadline,
        }
        for g in goals_result.scalars().all()
    ]

    report_path = generate_financial_report(
        user_name=user_name,
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

    report = await report_repo.create_report(
        db, user_id=user_id, period_start=period_start, period_end=period_end, file_url=report_path
    )

    return {
        "id": report.id,
        "period_start": report.period_start.isoformat() if report.period_start else None,
        "period_end": report.period_end.isoformat() if report.period_end else None,
        "file_url": report.file_url,
        "created_at": report.created_at.isoformat() if report.created_at else None,
        "summary": {
            "total_income": total_income,
            "total_expense": total_expense,
            "balance": total_income - total_expense,
            "transaction_count": len(transactions),
        },
    }
