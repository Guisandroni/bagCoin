"""Budget and Goal Service for BagCoin agents.

Provides sync (non-async) operations for budget/goal CRUD and alerts.
These are used by agents that run in sync context via sync_session_maker.
"""

import logging
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import func

from app.core.financial_categories import default_category_names, resolve_default_category_name
from app.db.models.budget import Budget
from app.db.models.category import Category
from app.db.models.enums import GoalStatus
from app.db.models.goal import Goal
from app.db.models.transaction import Transaction
from app.db.session import sync_session_maker
from app.services.agent_memory_service import add_memory_event

logger = logging.getLogger(__name__)


# =====================================================================
# HELPERS
# =====================================================================


def _period_start(period: str) -> datetime | None:
    """Return the start of the current period as a tz-aware UTC datetime.

    Always tz-aware to match Transaction.transaction_date (TIMESTAMPTZ).
    Avoids naive vs aware comparison bugs under non-UTC session timezones.
    """
    now = datetime.now(UTC)
    if period == "daily":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "weekly":
        monday = now - timedelta(days=now.weekday())
        return monday.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "monthly":
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if period == "yearly":
        return now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    return None


def _get_or_create_user(phone_number: str, db=None):
    """Get or create a phone user (sync)."""
    from app.agents.persistence import get_or_create_user, get_or_create_user_sync

    if db is not None:
        return get_or_create_user(phone_number, db)
    return get_or_create_user_sync(phone_number)


# =====================================================================
# BUDGET
# =====================================================================


def create_budget(
    phone_number: str,
    name: str,
    total_limit: float,
    period: str = "monthly",
    budget_type: str = "category",
) -> dict[str, Any]:
    """Create a new budget for the user.

    Args:
        phone_number: User's phone identifier.
        name: Budget name.
        total_limit: Spending limit or account balance.
        period: Budget period (monthly, weekly, yearly).
        budget_type: "general" (conta/saldo) or "category" (limite por categoria).
    """
    db = sync_session_maker()
    try:
        user = _get_or_create_user(phone_number, db)

        # For "general" type, category is optional
        category = None
        category_id = None
        if budget_type == "category":
            name = resolve_default_category_name(name)
            category = (
                db.query(Category)
                .filter(
                    Category.user_id == user.id,
                    Category.name.ilike(name),
                )
                .first()
            )
            if not category:
                category = Category(
                    user_id=user.id,
                    name=name,
                    is_default=name in default_category_names(),
                )
                db.add(category)
                db.commit()
                db.refresh(category)
            category_id = category.id

        budget = Budget(
            user_id=user.id,
            category_id=category_id,
            name=name,
            period=period,
            total_limit=total_limit,
            budget_date=date.today(),
            budget_type=budget_type,
        )
        db.add(budget)
        db.flush()
        add_memory_event(
            db,
            user_id=user.id,
            event_type="budget_created",
            entity_type="budget",
            entity_id=budget.id,
            source="agent",
            summary=f"Orçamento criado: {budget.name} limite R$ {float(budget.total_limit):.2f}",
            payload={"budget_id": budget.id, "name": budget.name, "total_limit": float(budget.total_limit)},
        )
        db.commit()
        db.refresh(budget)

        return {
            "id": budget.id,
            "name": budget.name,
            "category_id": budget.category_id,
            "category_name": category.name if category else None,
            "total_limit": budget.total_limit,
            "period": budget.period,
            "budget_type": budget.budget_type,
            "budget_date": budget.budget_date.isoformat() if budget.budget_date else None,
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating budget: {e}")
        raise
    finally:
        db.close()


def get_budgets(phone_number: str) -> list[dict[str, Any]]:
    """Return active budgets with progress calculations."""
    db = sync_session_maker()
    try:
        user = _get_or_create_user(phone_number, db)
        budgets = db.query(Budget).filter(Budget.user_id == user.id).all()

        result = []
        for budget in budgets:
            spent = get_budget_spent(db, budget.id, user.id, budget.period)
            cat_name = budget.category.name if budget.category else budget.name
            result.append(
                {
                    "id": budget.id,
                    "name": budget.name,
                    "category_id": budget.category_id,
                    "category_name": cat_name,
                    "total_limit": budget.total_limit,
                    "total_spent": spent,
                    "total_remaining": budget.total_limit - spent,
                    "percentage": round((spent / budget.total_limit) * 100, 1)
                    if budget.total_limit > 0
                    else 0,
                    "period": budget.period,
                    "budget_date": budget.budget_date.isoformat() if budget.budget_date else None,
                }
            )
        return result
    finally:
        db.close()


def get_budget_spent(db, budget_id: int, user_id: int, period: str) -> float:
    """Calculate how much has been spent in the budget period."""
    date_from = _period_start(period)
    if not date_from:
        logger.warning(f"[budget_spent] unknown period={period!r} — returning 0")
        return 0.0

    budget = (
        db.query(Budget)
        .filter(
            Budget.id == budget_id,
            Budget.user_id == user_id,
        )
        .first()
    )
    if not budget:
        return 0.0

    if budget.category_id is None and getattr(budget, "budget_type", "category") == "category":
        logger.warning(
            f"[budget_spent] budget_id={budget_id} has budget_type=category but category_id is NULL"
        )

    result = (
        db.query(func.coalesce(func.sum(func.abs(Transaction.amount)), 0))
        .filter(
            Transaction.type == "EXPENSE",
            Transaction.user_id == user_id,
            Transaction.category_id == budget.category_id,
            Transaction.transaction_date >= date_from,
        )
        .scalar()
    )
    spent = float(result or 0)
    logger.info(
        f"[budget_spent] budget_id={budget_id} category_id={budget.category_id} "
        f"period={period} from={date_from.isoformat()} spent={spent}"
    )
    return spent


def delete_budget_by_name(phone_number: str, name: str) -> int:
    """Delete budget by name/category. Returns count deleted."""
    db = sync_session_maker()
    try:
        user = _get_or_create_user(phone_number, db)
        budgets = (
            db.query(Budget)
            .filter(
                Budget.user_id == user.id,
                Budget.name.ilike(f"%{name}%"),
            )
            .all()
        )
        if not budgets:
            budgets = (
                db.query(Budget)
                .filter(
                    Budget.user_id == user.id,
                )
                .join(Category, Budget.category_id == Category.id)
                .filter(
                    Category.name.ilike(f"%{name}%"),
                )
                .all()
            )
        count = 0
        for budget in budgets:
            add_memory_event(
                db,
                user_id=user.id,
                event_type="budget_deleted",
                entity_type="budget",
                entity_id=budget.id,
                source="agent",
                summary=f"Orçamento removido: {budget.name}",
                payload={"budget_id": budget.id, "name": budget.name},
            )
            db.delete(budget)
            count += 1
        db.commit()
        return count
    finally:
        db.close()


def delete_all_budgets(phone_number: str) -> int:
    """Delete all budgets for a user."""
    db = sync_session_maker()
    try:
        user = _get_or_create_user(phone_number, db)
        count = db.query(Budget).filter(Budget.user_id == user.id).delete()
        db.commit()
        return count
    finally:
        db.close()


def update_budget_limit(phone_number: str, name: str, new_limit: float) -> dict[str, Any] | None:
    """Update the limit of a budget by name/category."""
    db = sync_session_maker()
    try:
        user = _get_or_create_user(phone_number, db)
        budget = (
            db.query(Budget)
            .filter(
                Budget.user_id == user.id,
                Budget.name.ilike(f"%{name}%"),
            )
            .first()
        )
        if not budget:
            budget = (
                db.query(Budget)
                .filter(
                    Budget.user_id == user.id,
                )
                .join(Category, Budget.category_id == Category.id)
                .filter(
                    Category.name.ilike(f"%{name}%"),
                )
                .first()
            )
        if not budget:
            return None
        budget.total_limit = new_limit
        for item in budget.items:
            item.limit_amount = new_limit
        add_memory_event(
            db,
            user_id=user.id,
            event_type="budget_updated",
            entity_type="budget",
            entity_id=budget.id,
            source="agent",
            summary=f"Orçamento atualizado: {budget.name} limite R$ {float(new_limit):.2f}",
            payload={"budget_id": budget.id, "new_limit": float(new_limit)},
        )
        db.commit()
        db.refresh(budget)
        cat_name = budget.category.name if budget.category else budget.name
        return {
            "id": budget.id,
            "name": budget.name,
            "category_name": cat_name,
            "total_limit": budget.total_limit,
            "period": budget.period,
            "budget_date": budget.budget_date.isoformat() if budget.budget_date else None,
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating budget: {e}")
        raise
    finally:
        db.close()


# =====================================================================
# GOAL
# =====================================================================


def create_goal(
    phone_number: str,
    title: str,
    target_amount: float,
    deadline: date | None = None,
) -> dict[str, Any]:
    """Create a new financial goal."""
    db = sync_session_maker()
    try:
        user = _get_or_create_user(phone_number, db)

        goal = Goal(
            user_id=user.id,
            title=title,
            target_amount=target_amount,
            current_amount=0.0,
            deadline=deadline,
            status=GoalStatus.ACTIVE.value,
        )
        db.add(goal)
        db.flush()
        add_memory_event(
            db,
            user_id=user.id,
            event_type="goal_created",
            entity_type="goal",
            entity_id=goal.id,
            source="agent",
            summary=f"Meta criada: {goal.title} R$ {float(goal.target_amount):.2f}",
            payload={"goal_id": goal.id, "title": goal.title, "target_amount": float(goal.target_amount)},
        )
        db.commit()
        db.refresh(goal)

        return {
            "id": goal.id,
            "title": goal.title,
            "target_amount": goal.target_amount,
            "current_amount": goal.current_amount,
            "deadline": goal.deadline.isoformat() if goal.deadline else None,
            "percentage": 0.0,
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating goal: {e}")
        raise
    finally:
        db.close()


def update_goal_progress(phone_number: str, goal_id: int, amount: float) -> dict[str, Any]:
    """Update the progress of a goal."""
    db = sync_session_maker()
    try:
        user = _get_or_create_user(phone_number, db)
        goal = (
            db.query(Goal)
            .filter(
                Goal.id == goal_id,
                Goal.user_id == user.id,
            )
            .first()
        )

        if not goal:
            raise ValueError("Goal not found")

        goal.current_amount = min(goal.current_amount + amount, goal.target_amount)
        if goal.current_amount >= goal.target_amount:
            goal.status = GoalStatus.COMPLETED.value
        add_memory_event(
            db,
            user_id=user.id,
            event_type="goal_contributed",
            entity_type="goal",
            entity_id=goal.id,
            source="agent",
            summary=f"Contribuição em meta: {goal.title} +R$ {float(amount):.2f}",
            payload={"goal_id": goal.id, "amount": float(amount), "current_amount": float(goal.current_amount)},
        )

        db.commit()
        db.refresh(goal)

        return {
            "id": goal.id,
            "title": goal.title,
            "current_amount": goal.current_amount,
            "target_amount": goal.target_amount,
            "percentage": round((goal.current_amount / goal.target_amount) * 100, 1)
            if goal.target_amount > 0
            else 0,
            "status": goal.status.value if hasattr(goal.status, "value") else str(goal.status),
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating goal: {e}")
        raise
    finally:
        db.close()


def get_goals(phone_number: str) -> list[dict[str, Any]]:
    """Return active goals for the user."""
    db = sync_session_maker()
    try:
        user = _get_or_create_user(phone_number, db)
        goals = (
            db.query(Goal)
            .filter(
                Goal.user_id == user.id,
                Goal.status == GoalStatus.ACTIVE.value,
            )
            .all()
        )

        return [
            {
                "id": g.id,
                "title": g.title,
                "target_amount": g.target_amount,
                "current_amount": g.current_amount,
                "deadline": g.deadline.isoformat() if g.deadline else None,
                "percentage": round((g.current_amount / g.target_amount) * 100, 1)
                if g.target_amount > 0
                else 0,
                "status": g.status.value if hasattr(g.status, "value") else str(g.status),
            }
            for g in goals
        ]
    finally:
        db.close()


def delete_goal(phone_number: str, goal_identifier: str) -> bool:
    """Delete a goal by title or index. Returns True if deleted."""
    db = sync_session_maker()
    try:
        user = _get_or_create_user(phone_number, db)
        goals = (
            db.query(Goal)
            .filter(
                Goal.user_id == user.id,
                Goal.status == GoalStatus.ACTIVE.value,
            )
            .all()
        )
        target = None
        for g in goals:
            if goal_identifier.lower() in g.title.lower():
                target = g
                break
        if not target:
            try:
                idx = int(goal_identifier) - 1
                if 0 <= idx < len(goals):
                    target = goals[idx]
            except ValueError:
                pass
        if not target:
            return False
        add_memory_event(
            db,
            user_id=user.id,
            event_type="goal_deleted",
            entity_type="goal",
            entity_id=target.id,
            source="agent",
            summary=f"Meta removida: {target.title}",
            payload={"goal_id": target.id, "title": target.title},
        )
        db.delete(target)
        db.commit()
        return True
    finally:
        db.close()


def update_goal(
    phone_number: str,
    goal_identifier: str,
    new_target: float | None = None,
    new_title: str | None = None,
    new_deadline: date | None = None,
) -> dict[str, Any] | None:
    """Update title, target, or deadline of a goal."""
    db = sync_session_maker()
    try:
        user = _get_or_create_user(phone_number, db)
        goals = (
            db.query(Goal)
            .filter(
                Goal.user_id == user.id,
                Goal.status == GoalStatus.ACTIVE.value,
            )
            .all()
        )
        target = None
        for g in goals:
            if goal_identifier.lower() in g.title.lower():
                target = g
                break
        if not target:
            try:
                idx = int(goal_identifier) - 1
                if 0 <= idx < len(goals):
                    target = goals[idx]
            except ValueError:
                pass
        if not target:
            return None
        if new_target is not None:
            target.target_amount = new_target
        if new_title:
            target.title = new_title
        if new_deadline:
            target.deadline = new_deadline
        add_memory_event(
            db,
            user_id=user.id,
            event_type="goal_updated",
            entity_type="goal",
            entity_id=target.id,
            source="agent",
            summary=f"Meta atualizada: {target.title}",
            payload={
                "goal_id": target.id,
                "new_target": new_target,
                "new_title": new_title,
                "new_deadline": new_deadline.isoformat() if new_deadline else None,
            },
        )
        db.commit()
        db.refresh(target)
        return {
            "id": target.id,
            "title": target.title,
            "target_amount": target.target_amount,
            "current_amount": target.current_amount,
            "deadline": target.deadline.isoformat() if target.deadline else None,
            "percentage": round((target.current_amount / target.target_amount) * 100, 1)
            if target.target_amount > 0
            else 0,
            "status": target.status.value
            if hasattr(target.status, "value")
            else str(target.status),
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating goal: {e}")
        raise
    finally:
        db.close()


# =====================================================================
# ALERTS
# =====================================================================


def get_financial_alerts_enabled(phone_number: str) -> bool:
    """Check if financial alerts are enabled for the user. Default: True."""
    db = sync_session_maker()
    try:
        user = _get_or_create_user(phone_number, db)
        prefs = user.preferences or {}
        return bool(prefs.get("financial_alerts_enabled", True))
    finally:
        db.close()


def set_financial_alerts_enabled(phone_number: str, enabled: bool) -> None:
    """Persist alert preference in user's preferences JSON."""
    db = sync_session_maker()
    try:
        user = _get_or_create_user(phone_number, db)
        prefs = dict(user.preferences or {})
        prefs["financial_alerts_enabled"] = bool(enabled)
        user.preferences = prefs
        from sqlalchemy.orm.attributes import flag_modified

        flag_modified(user, "preferences")
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def check_budget_alerts(phone_number: str) -> list[dict[str, Any]]:
    """Check budgets that are near or over limit."""
    if not get_financial_alerts_enabled(phone_number):
        return []
    alerts = []
    budgets = get_budgets(phone_number)

    for budget in budgets:
        pct = budget["percentage"]
        if pct >= 100:
            alerts.append(
                {
                    "type": "budget_exceeded",
                    "severity": "high",
                    "budget_name": budget["name"],
                    "message": (
                        f"📊 Orçamento de **{budget['name']}** estourado! "
                        f"R$ {budget['total_spent']:,.2f} usado de R$ {budget['total_limit']:,.2f} ({pct}%)"
                    ),
                }
            )
        elif pct >= 80:
            alerts.append(
                {
                    "type": "budget_warning",
                    "severity": "medium",
                    "budget_name": budget["name"],
                    "message": (
                        f"📊 Atenção: orçamento de **{budget['name']}** está em {pct}% "
                        f"(R$ {budget['total_spent']:,.2f} de R$ {budget['total_limit']:,.2f})"
                    ),
                }
            )

    return alerts


def check_goal_alerts(phone_number: str) -> list[dict[str, Any]]:
    """Check goals that are completed or close to deadline."""
    if not get_financial_alerts_enabled(phone_number):
        return []
    alerts = []
    goals = get_goals(phone_number)
    today = date.today()

    for goal in goals:
        if goal["percentage"] >= 100:
            alerts.append(
                {
                    "type": "goal_completed",
                    "severity": "info",
                    "goal_title": goal["title"],
                    "message": (
                        f"Parabéns! Meta '{goal['title']}' atingida! "
                        f"R$ {goal['current_amount']:,.2f} de R$ {goal['target_amount']:,.2f}"
                    ),
                }
            )
        elif goal.get("deadline"):
            deadline = date.fromisoformat(goal["deadline"])
            days_left = (deadline - today).days
            if days_left <= 7 and days_left > 0 and goal["percentage"] < 100:
                alerts.append(
                    {
                        "type": "goal_deadline",
                        "severity": "medium",
                        "goal_title": goal["title"],
                        "message": (
                            f"Meta '{goal['title']}' vence em {days_left} dias. "
                            f"Progresso: {goal['percentage']}% "
                            f"(R$ {goal['current_amount']:,.2f} de R$ {goal['target_amount']:,.2f})"
                        ),
                    }
                )

    return alerts
