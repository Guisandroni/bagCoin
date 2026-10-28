"""Goal model for financial savings goals."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.db.models.enums import GoalStatus

if TYPE_CHECKING:
    from app.db.models.user import User


class Goal(Base, TimestampMixin):
    """Financial savings goal."""

    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    target_amount: Mapped[float] = mapped_column(Float, nullable=False)
    current_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[GoalStatus] = mapped_column(
        String(20), default=GoalStatus.ACTIVE.value, nullable=False
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="goals")

    def __repr__(self) -> str:
        return f"<Goal(id={self.id}, title={self.title}, target={self.target_amount}, status={self.status})>"
