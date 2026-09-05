"""REST service for Goal operations (web frontend, async)."""

from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.repositories import goal as goal_repo
from app.schemas.goal import GoalCreate, GoalUpdate
from app.services.agent_memory_service import add_memory_event_async


def _status_value(status: Any) -> str:
    return status.value if hasattr(status, "value") else str(status)


def _goal_response(g) -> dict[str, Any]:
    return {
        "id": g.id,
        "title": g.title,
        "target_amount": g.target_amount,
        "current_amount": g.current_amount,
        "deadline": g.deadline.isoformat() if g.deadline else None,
        "percentage": round((g.current_amount / g.target_amount) * 100, 1) if g.target_amount > 0 else 0,
        "status": _status_value(g.status),
        "created_at": g.created_at,
        "updated_at": g.updated_at,
    }


async def list_goals(db: AsyncSession, user_id: int, status: str | None = None) -> list[dict[str, Any]]:
    goals = await goal_repo.get_goals_by_user(db, user_id=user_id, status=status)
    return [_goal_response(g) for g in goals]


async def create_goal(db: AsyncSession, user_id: int, data: GoalCreate) -> dict[str, Any]:
    goal = await goal_repo.create_goal(
        db,
        user_id=user_id,
        title=data.title,
        target_amount=data.target_amount,
        current_amount=data.current_amount,
        deadline=data.deadline,
        status=data.status.value if hasattr(data.status, "value") else str(data.status),
    )
    await add_memory_event_async(
        db,
        user_id=user_id,
        event_type="goal_created",
        entity_type="goal",
        entity_id=goal.id,
        source="web",
        summary=f"Meta criada: {goal.title} R$ {float(goal.target_amount):.2f}",
        payload={"goal_id": goal.id, "title": goal.title, "target_amount": float(goal.target_amount)},
    )
    return _goal_response(goal)


async def get_goal(db: AsyncSession, goal_id: int, user_id: int) -> dict[str, Any]:
    goal = await goal_repo.get_goal_by_id(db, goal_id)
    if not goal or goal.user_id != user_id:
        raise NotFoundError(message="Goal not found", details={"id": goal_id})
    return _goal_response(goal)


async def update_goal(db: AsyncSession, goal_id: int, user_id: int, data: GoalUpdate) -> dict[str, Any]:
    goal = await goal_repo.get_goal_by_id(db, goal_id)
    if not goal or goal.user_id != user_id:
        raise NotFoundError(message="Goal not found", details={"id": goal_id})
    update_data = data.serializable_dict(exclude_unset=True)
    await goal_repo.update_goal(db, db_goal=goal, update_data=update_data)
    await add_memory_event_async(
        db,
        user_id=user_id,
        event_type="goal_updated",
        entity_type="goal",
        entity_id=goal.id,
        source="web",
        summary=f"Meta atualizada: {goal.title}",
        payload={"goal_id": goal.id, "changes": update_data},
    )
    return await get_goal(db, goal_id, user_id)


async def delete_goal(db: AsyncSession, goal_id: int, user_id: int) -> None:
    goal = await goal_repo.get_goal_by_id(db, goal_id)
    if not goal or goal.user_id != user_id:
        raise NotFoundError(message="Goal not found", details={"id": goal_id})
    await add_memory_event_async(
        db,
        user_id=user_id,
        event_type="goal_deleted",
        entity_type="goal",
        entity_id=goal.id,
        source="web",
        summary=f"Meta removida: {goal.title}",
        payload={"goal_id": goal.id, "title": goal.title},
    )
    await goal_repo.delete_goal(db, goal_id)


async def get_goal_alerts(db: AsyncSession, user_id: int) -> list[dict[str, Any]]:
    alerts = []
    goals = await list_goals(db, user_id)
    today = date.today()
    for goal in goals:
        if goal["percentage"] >= 100:
            alerts.append({
                "type": "goal_completed",
                "severity": "info",
                "goal_title": goal["title"],
                "message": f"Parabéns! Meta '{goal['title']}' atingida! R$ {goal['current_amount']:,.2f} de R$ {goal['target_amount']:,.2f}",
            })
        elif goal.get("deadline"):
            deadline = date.fromisoformat(goal["deadline"][:10])
            days_left = (deadline - today).days
            if 0 < days_left <= 7 and goal["percentage"] < 100:
                alerts.append({
                    "type": "goal_deadline",
                    "severity": "medium",
                    "goal_title": goal["title"],
                    "message": f"Meta '{goal['title']}' vence em {days_left} dias. Progresso: {goal['percentage']}% (R$ {goal['current_amount']:,.2f} de R$ {goal['target_amount']:,.2f})",
                })
    return alerts
