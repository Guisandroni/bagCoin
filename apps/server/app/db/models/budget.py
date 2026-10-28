"""Budget and BudgetItem models for spending limits."""

from __future__ import annotations

from typing import TYPE_CHECKING

from datetime import date

from sqlalchemy import Date, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.category import Category
    from app.db.models.user import User


class Budget(Base, TimestampMixin):
    """Budget model — defines a spending plan for a period."""

    __tablename__ = "budgets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    period: Mapped[str] = mapped_column(String(20), nullable=False)
    total_limit: Mapped[float] = mapped_column(Float, nullable=False)
    budget_type: Mapped[str] = mapped_column(String(20), nullable=False, default="category")
    budget_date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="budgets")
    category: Mapped[Category | None] = relationship("Category", back_populates="budgets")
    items: Mapped[list["BudgetItem"]] = relationship(
        "BudgetItem", back_populates="budget", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Budget(id={self.id}, name={self.name}, period={self.period}, limit={self.total_limit})>"


class BudgetItem(Base):
    """BudgetItem model — per-category limit within a budget."""

    __tablename__ = "budget_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    budget_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("budgets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    limit_amount: Mapped[float] = mapped_column(Float, nullable=False)

    # Relationships
    budget: Mapped[Budget] = relationship("Budget", back_populates="items")
    category: Mapped[Category | None] = relationship("Category", back_populates="budget_items")

    def __repr__(self) -> str:
        return f"<BudgetItem(id={self.id}, budget_id={self.budget_id}, limit={self.limit_amount})>"
