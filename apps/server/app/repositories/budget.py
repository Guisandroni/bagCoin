"""Budget repository (PostgreSQL async)."""

from datetime import date

from sqlalchemy import delete as sa_delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.budget import Budget, BudgetItem


async def get_budget_by_id(
    db: AsyncSession,
    budget_id: int,
    *,
    include_items: bool = False,
) -> Budget | None:
    if include_items:
        query = select(Budget).options(selectinload(Budget.items)).where(Budget.id == budget_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    return await db.get(Budget, budget_id)


async def get_budgets_by_user(
    db: AsyncSession,
    user_id: int,
    *,
    skip: int = 0,
    limit: int = 50,
) -> list[Budget]:
    query = (
        select(Budget)
        .options(selectinload(Budget.items), selectinload(Budget.category))
        .where(Budget.user_id == user_id)
        .order_by(Budget.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def count_budgets(db: AsyncSession, user_id: int) -> int:
    query = select(func.count(Budget.id)).where(Budget.user_id == user_id)
    result = await db.execute(query)
    return result.scalar() or 0


async def create_budget(
    db: AsyncSession,
    *,
    user_id: int,
    category_id: int | None = None,
    name: str,
    period: str,
    total_limit: float,
    budget_date: date,
    budget_type: str = "general",
    items: list[dict] | None = None,
) -> Budget:
    budget = Budget(
        user_id=user_id,
        category_id=category_id,
        name=name,
        period=period,
        total_limit=total_limit,
        budget_date=budget_date,
        budget_type=budget_type,
    )
    db.add(budget)
    await db.flush()
    await db.refresh(budget)

    if items:
        for item_data in items:
            item = BudgetItem(
                budget_id=budget.id,
                category_id=item_data.get("category_id"),
                limit_amount=item_data["limit_amount"],
            )
            db.add(item)
        await db.flush()

    await db.refresh(budget)
    return budget


async def update_budget(
    db: AsyncSession,
    *,
    db_budget: Budget,
    update_data: dict,
) -> Budget:
    for field, value in update_data.items():
        if field == "items":
            continue
        setattr(db_budget, field, value)

    if "items" in update_data and update_data["items"] is not None:
        await db.execute(sa_delete(BudgetItem).where(BudgetItem.budget_id == db_budget.id))
        for item_data in update_data["items"]:
            item = BudgetItem(
                budget_id=db_budget.id,
                category_id=item_data.get("category_id"),
                limit_amount=item_data["limit_amount"],
            )
            db.add(item)

    db.add(db_budget)
    await db.flush()
    await db.refresh(db_budget)
    return db_budget


async def delete_budget(db: AsyncSession, budget_id: int) -> bool:
    budget = await get_budget_by_id(db, budget_id)
    if budget:
        await db.delete(budget)
        await db.flush()
        return True
    return False
