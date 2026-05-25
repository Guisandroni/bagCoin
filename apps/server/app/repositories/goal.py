"""Goal repository (PostgreSQL async)."""

from datetime import date, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.enums import GoalStatus
from app.db.models.goal import Goal


async def get_by_id(db: AsyncSession, goal_id: int) -> Goal | None:
    return await db.get(Goal, goal_id)


async def get_multi_by_user(
    db: AsyncSession,
    user_id: int,
    status: str | None = None,
) -> list[Goal]:
    query = select(Goal).where(Goal.user_id == user_id)
    if status:
        query = query.where(Goal.status == status)
    query = query.order_by(Goal.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def create(
    db: AsyncSession,
    *,
    user_id: int,
    title: str,
    target_amount: float,
    current_amount: float = 0.0,
    deadline: date | None = None,
    status: str | None = None,
) -> Goal:
    goal = Goal(
        user_id=user_id,
        title=title,
        target_amount=target_amount,
        current_amount=current_amount,
        deadline=deadline,
        status=status or GoalStatus.ACTIVE.value,
    )
    db.add(goal)
    await db.flush()
    await db.refresh(goal)
    return goal


async def update(
    db: AsyncSession,
    *,
    db_goal: Goal,
    update_data: dict[str, Any],
) -> Goal:
    for field, value in update_data.items():
        setattr(db_goal, field, value)
    db.add(db_goal)
    await db.flush()
    await db.refresh(db_goal)
    return db_goal


async def update_progress(
    db: AsyncSession,
    goal_id: int,
    user_id: int,
    amount: float,
) -> Goal | None:
    goal = await db.get(Goal, goal_id)
    if not goal or goal.user_id != user_id:
        return None
    goal.current_amount = min(goal.current_amount + amount, goal.target_amount)
    if goal.current_amount >= goal.target_amount:
        goal.status = GoalStatus.COMPLETED.value
    await db.flush()
    await db.refresh(goal)
    return goal


async def delete(db: AsyncSession, goal_id: int) -> Goal | None:
    goal = await get_by_id(db, goal_id)
    if goal:
        await db.delete(goal)
        await db.flush()
    return goal


# Aliases for REST service compatibility
get_goal_by_id = get_by_id


async def get_goals_by_user(
    db: AsyncSession,
    user_id: int,
    *,
    skip: int = 0,
    limit: int = 50,
    status: str | None = None,
) -> list[Goal]:
    query = select(Goal).where(Goal.user_id == user_id)
    if status:
        query = query.where(Goal.status == status)
    query = query.order_by(Goal.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def count_goals(db: AsyncSession, user_id: int) -> int:
    query = select(func.count(Goal.id)).where(Goal.user_id == user_id)
    result = await db.execute(query)
    return result.scalar() or 0


async def create_goal(
    db: AsyncSession,
    *,
    user_id: int,
    title: str,
    target_amount: float,
    current_amount: float = 0.0,
    deadline: datetime | None = None,
    status: str | None = None,
) -> Goal:
    return await create(
        db,
        user_id=user_id,
        title=title,
        target_amount=target_amount,
        current_amount=current_amount,
        deadline=deadline,
        status=status,
    )


async def update_goal(
    db: AsyncSession,
    *,
    db_goal: Goal,
    update_data: dict[str, Any],
) -> Goal:
    return await update(db, db_goal=db_goal, update_data=update_data)


async def delete_goal(db: AsyncSession, goal_id: int) -> Goal | None:
    return await delete(db, goal_id)
