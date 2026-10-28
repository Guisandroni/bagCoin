"""Goal service (PostgreSQL async).

Contains business logic for goal operations.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models.goal import Goal
from app.repositories import goal as goal_repo
from app.schemas.goal import GoalCreate, GoalUpdate


class GoalService:
    """Service for goal-related business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_goal(self, goal_id: int, user_id: int | None = None) -> Goal:
        """Get goal by ID.

        Raises:
            NotFoundError: If goal does not exist or user has no access.
        """
        goal = await goal_repo.get_goal_by_id(self.db, goal_id)
        if not goal:
            raise NotFoundError(
                message="Goal not found",
                details={"goal_id": goal_id},
            )
        if user_id is not None and goal.user_id != user_id:
            raise NotFoundError(
                message="Goal not found",
                details={"goal_id": goal_id},
            )
        return goal

    async def list_goals(
        self,
        user_id: int | None = None,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Goal], int]:
        """List goals with pagination.

        Returns:
            Tuple of (goals, total_count).
        """
        items = await goal_repo.get_goals_by_user(
            self.db,
            user_id=user_id,
            skip=skip,
            limit=limit,
        )
        total = await goal_repo.count_goals(
            self.db,
            user_id=user_id,
        )
        return items, total

    async def create_goal(
        self,
        data: GoalCreate,
        user_id: int | None = None,
    ) -> Goal:
        """Create a new goal."""
        return await goal_repo.create_goal(
            self.db,
            user_id=user_id,
            title=data.title,
            target_amount=data.target_amount,
            current_amount=data.current_amount,
            deadline=data.deadline,
            status=data.status,
        )

    async def update_goal(
        self,
        goal_id: int,
        data: GoalUpdate,
        user_id: int | None = None,
    ) -> Goal:
        """Update a goal.

        Raises:
            NotFoundError: If goal does not exist.
        """
        goal = await self.get_goal(goal_id, user_id=user_id)
        update_data = data.model_dump(exclude_unset=True)
        return await goal_repo.update_goal(
            self.db, db_goal=goal, update_data=update_data
        )

    async def delete_goal(
        self,
        goal_id: int,
        user_id: int | None = None,
    ) -> bool:
        """Delete a goal.

        Raises:
            NotFoundError: If goal does not exist or user has no access.
        """
        await self.get_goal(goal_id, user_id=user_id)
        deleted = await goal_repo.delete_goal(self.db, goal_id)
        if not deleted:
            raise NotFoundError(
                message="Goal not found",
                details={"goal_id": goal_id},
            )
        return True
