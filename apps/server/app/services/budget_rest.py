"""REST service for Budget operations (web frontend, async)."""

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models.budget import Budget
from app.db.models.category import Category
from app.db.models.transaction import Transaction
from app.repositories import budget as budget_repo
from app.schemas.budget import BudgetCreate, BudgetUpdate
from app.services.agent_memory_service import add_memory_event_async
from app.services.category_rest import get_or_create_category_for_user


def _budget_cycle_start(budget: Budget) -> datetime:
    """Return the start of the current budget period (calendar-based)."""
    now = datetime.now(UTC)
    period = budget.period or "monthly"
    if period == "daily":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "weekly":
        monday = now - timedelta(days=now.weekday())
        return monday.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "monthly":
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if period == "yearly":
        return now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


async def _calculate_spent(db: AsyncSession, budget: Budget) -> float:
    date_from = _budget_cycle_start(budget)
    if not date_from or not budget.category_id:
        return 0.0
    result = await db.execute(
        select(func.coalesce(func.sum(func.abs(Transaction.amount)), 0)).where(
            Transaction.type == "EXPENSE",
            Transaction.user_id == budget.user_id,
            Transaction.category_id == budget.category_id,
            Transaction.transaction_date >= date_from,
        )
    )
    return float(result.scalar() or 0)


def _budget_progress_payload(budget: Budget, spent: float) -> dict[str, float]:
    total_limit = abs(float(budget.total_limit or 0))
    total_spent = abs(float(spent or 0))
    total_remaining = total_limit - total_spent
    percentage = round((total_spent / total_limit) * 100, 1) if total_limit > 0 else 0
    return {
        "total_limit": total_limit,
        "total_spent": total_spent,
        "total_remaining": total_remaining,
        "percentage": percentage,
    }


async def list_budgets(db: AsyncSession, user_id: int) -> list[dict[str, Any]]:
    budgets = await budget_repo.get_budgets_by_user(db, user_id=user_id)
    result = []
    for budget in budgets:
        spent = await _calculate_spent(db, budget)
        progress = _budget_progress_payload(budget, spent)
        cat_name = budget.category.name if budget.category else budget.name
        result.append(
            {
                "id": budget.id,
                "name": budget.name,
                "category_id": budget.category_id,
                "category_name": cat_name,
                **progress,
                "period": budget.period,
                "budget_type": budget.budget_type,
                "budget_date": budget.budget_date,
                "created_at": budget.created_at,
                "updated_at": budget.updated_at,
            }
        )
    return result


async def create_budget(db: AsyncSession, user_id: int, data: BudgetCreate) -> dict[str, Any]:
    category = await _resolve_budget_category(db, user_id, data)
    budget_type = data.budget_type or ("category" if category else "general")
    name = category.name if category else data.name
    budget = await budget_repo.create_budget(
        db,
        user_id=user_id,
        name=name,
        period=data.period,
        total_limit=data.total_limit,
        budget_date=data.budget_date,
        category_id=category.id if category else None,
        budget_type=budget_type,
    )
    await add_memory_event_async(
        db,
        user_id=user_id,
        event_type="budget_created",
        entity_type="budget",
        entity_id=budget.id,
        source="web",
        summary=f"Orçamento criado: {budget.name} limite R$ {float(budget.total_limit):.2f}",
        payload={"budget_id": budget.id, "name": budget.name, "total_limit": float(budget.total_limit)},
    )
    return await get_budget(db, budget.id, user_id)


async def _resolve_budget_category(
    db: AsyncSession, user_id: int, data: BudgetCreate
) -> Category | None:
    if data.category_id:
        result = await db.execute(
            select(Category).where(Category.id == data.category_id, Category.user_id == user_id)
        )
        category = result.scalar_one_or_none()
        if not category:
            raise NotFoundError(message="Category not found", details={"id": data.category_id})
        return category
    if data.category_name or data.name:
        return await get_or_create_category_for_user(db, user_id, data.category_name or data.name)
    return None


async def get_budget(db: AsyncSession, budget_id: int, user_id: int) -> dict[str, Any]:
    budget = await budget_repo.get_budget_by_id(db, budget_id)
    if not budget or budget.user_id != user_id:
        raise NotFoundError(message="Budget not found", details={"id": budget_id})
    spent = await _calculate_spent(db, budget)
    progress = _budget_progress_payload(budget, spent)
    cat_name = budget.category.name if budget.category else budget.name
    return {
        "id": budget.id,
        "name": budget.name,
        "category_id": budget.category_id,
        "category_name": cat_name,
        **progress,
        "period": budget.period,
        "budget_type": budget.budget_type,
        "budget_date": budget.budget_date,
        "created_at": budget.created_at,
        "updated_at": budget.updated_at,
    }


async def update_budget(
    db: AsyncSession, budget_id: int, user_id: int, data: BudgetUpdate
) -> dict[str, Any]:
    budget = await budget_repo.get_budget_by_id(db, budget_id)
    if not budget or budget.user_id != user_id:
        raise NotFoundError(message="Budget not found", details={"id": budget_id})
    update_data = data.model_dump(exclude_unset=True)
    category_id = update_data.pop("category_id", None)
    category_name = update_data.pop("category_name", None)
    if category_id:
        result = await db.execute(
            select(Category).where(Category.id == category_id, Category.user_id == user_id)
        )
        category = result.scalar_one_or_none()
        if not category:
            raise NotFoundError(message="Category not found", details={"id": category_id})
        update_data["category_id"] = category.id
        update_data["name"] = category.name
        update_data.setdefault("budget_type", "category")
    elif category_name:
        category = await get_or_create_category_for_user(db, user_id, category_name)
        if category:
            update_data["category_id"] = category.id
            update_data["name"] = category.name
            update_data.setdefault("budget_type", "category")
    await budget_repo.update_budget(db, db_budget=budget, update_data=update_data)
    await add_memory_event_async(
        db,
        user_id=user_id,
        event_type="budget_updated",
        entity_type="budget",
        entity_id=budget.id,
        source="web",
        summary=f"Orçamento atualizado: {budget.name}",
        payload={"budget_id": budget.id, "changes": update_data},
    )
    return await get_budget(db, budget_id, user_id)


async def delete_budget(db: AsyncSession, budget_id: int, user_id: int) -> None:
    budget = await budget_repo.get_budget_by_id(db, budget_id)
    if not budget or budget.user_id != user_id:
        raise NotFoundError(message="Budget not found", details={"id": budget_id})
    await add_memory_event_async(
        db,
        user_id=user_id,
        event_type="budget_deleted",
        entity_type="budget",
        entity_id=budget.id,
        source="web",
        summary=f"Orçamento removido: {budget.name}",
        payload={"budget_id": budget.id, "name": budget.name},
    )
    await budget_repo.delete_budget(db, budget_id)


async def get_budget_alerts(db: AsyncSession, user_id: int) -> list[dict[str, Any]]:
    alerts = []
    budgets = await list_budgets(db, user_id)
    for budget in budgets:
        pct = budget["percentage"]
        if pct >= 100:
            alerts.append({
                "type": "budget_exceeded",
                "severity": "high",
                "budget_name": budget["name"],
                "message": f"Orçamento de {budget['name']} estourado! R$ {budget['total_spent']:,.2f} usado de R$ {budget['total_limit']:,.2f} ({pct}%)",
            })
        elif pct >= 80:
            alerts.append({
                "type": "budget_warning",
                "severity": "medium",
                "budget_name": budget["name"],
                "message": f"Atenção: orçamento de {budget['name']} está em {pct}% (R$ {budget['total_spent']:,.2f} de R$ {budget['total_limit']:,.2f})",
            })
    return alerts
