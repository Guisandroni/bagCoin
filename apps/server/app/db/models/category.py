"""Category model for transaction categorization."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.budget import Budget, BudgetItem
    from app.db.models.transaction import Transaction
    from app.db.models.user import User


class Category(Base, TimestampMixin):
    """Transaction category with optional hierarchy."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    parent_category_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="categories")
    parent: Mapped[Category | None] = relationship(
        "Category", remote_side="Category.id", backref="children"
    )
    transactions: Mapped[list[Transaction]] = relationship("Transaction", back_populates="category")
    budgets: Mapped[list[Budget]] = relationship("Budget", back_populates="category")
    budget_items: Mapped[list[BudgetItem]] = relationship("BudgetItem", back_populates="category")

    def __repr__(self) -> str:
        return f"<Category(id={self.id}, name={self.name}, user_id={self.user_id})>"
