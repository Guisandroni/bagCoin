"""Transaction model for financial records."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.db.models.enums import TransactionType

if TYPE_CHECKING:
    from app.db.models.category import Category
    from app.db.models.recurring_transaction import RecurringTransaction
    from app.db.models.user import User


class Transaction(Base, TimestampMixin):
    """Financial transaction record."""

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[TransactionType] = mapped_column(String(20), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="BRL", nullable=False)
    category_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    recurring_transaction_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("recurring_transactions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_format: Mapped[str] = mapped_column(String(20), default="text", nullable=False)
    transaction_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    confidence_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    raw_input: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="transactions")
    category: Mapped[Category | None] = relationship("Category", back_populates="transactions")
    recurring_transaction: Mapped[RecurringTransaction | None] = relationship("RecurringTransaction")

    def __repr__(self) -> str:
        return f"<Transaction(id={self.id}, type={self.type}, amount={self.amount}, user_id={self.user_id})>"
