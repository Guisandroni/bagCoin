"""Budget service (PostgreSQL async).

Contains business logic for budget operations including spent calculation.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models.budget import Budget
from app.repositories import budget as budget_repo
from app.schemas.budget import BudgetCreate, BudgetUpdate


class BudgetService:
    """Service for budget-related business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_budget(self, budget_id: int, user_id: int | None = None) -> Budget:
        """Get budget by ID.

        Raises:
            NotFoundError: If budget does not exist or user has no access.
        """
        budget = await budget_repo.get_budget_by_id(self.db, budget_id, include_items=True)
        if not budget:
            raise NotFoundError(
                message="Budget not found",
                details={"budget_id": budget_id},
            )
        if user_id is not None and budget.user_id != user_id:
            raise NotFoundError(
                message="Budget not found",
                details={"budget_id": budget_id},
            )
        return budget

    async def list_budgets(
        self,
        user_id: int | None = None,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Budget], int]:
        """List budgets with pagination.

        Returns:
            Tuple of (budgets, total_count).
        """
        items = await budget_repo.get_budgets_by_user(
            self.db,
            user_id=user_id,
            skip=skip,
            limit=limit,
        )
        total = await budget_repo.count_budgets(
            self.db,
            user_id=user_id,
        )
        return items, total

    async def create_budget(
        self,
        data: BudgetCreate,
        user_id: int | None = None,
    ) -> Budget:
        """Create a new budget."""
        items_data = [item.model_dump() for item in data.items] if data.items else None
        return await budget_repo.create_budget(
            self.db,
            user_id=user_id,
            category_id=data.category_id,
            name=data.name,
            period=data.period,
            total_limit=data.total_limit,
            budget_date=data.budget_date,
            budget_type=data.budget_type,
            items=items_data,
        )

    async def update_budget(
        self,
        budget_id: int,
        data: BudgetUpdate,
        user_id: int | None = None,
    ) -> Budget:
        """Update a budget.

        Raises:
            NotFoundError: If budget does not exist.
        """
        budget = await self.get_budget(budget_id, user_id=user_id)
        update_data = data.model_dump(exclude_unset=True)
        return await budget_repo.update_budget(
            self.db, db_budget=budget, update_data=update_data
        )

    async def delete_budget(
        self,
        budget_id: int,
        user_id: int | None = None,
    ) -> bool:
        """Delete a budget.

        Raises:
            NotFoundError: If budget does not exist or user has no access.
        """
        # Verify ownership first
        await self.get_budget(budget_id, user_id=user_id)
        deleted = await budget_repo.delete_budget(self.db, budget_id)
        if not deleted:
            raise NotFoundError(
                message="Budget not found",
                details={"budget_id": budget_id},
            )
        return True

    async def get_spent_for_budget(self, budget_id: int, user_id: int | None = None) -> float:
        """Calculate total spent for a budget in its period.

        This queries transactions that match the budget's period and categories.
        """
        budget = await self.get_budget(budget_id, user_id=user_id)
        # For now return 0 - actual spent calculation depends on transaction model
        # which may not exist yet. This is a placeholder.
        return 0.0
