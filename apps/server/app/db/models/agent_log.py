"""AgentLog model — audit trail for BagCoin agent invocations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.user import User


class AgentLog(Base, TimestampMixin):
    """Audit log for BagCoin agent invocations."""

    __tablename__ = "agent_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_name: Mapped[str] = mapped_column(String(50), nullable=False)
    request_payload: Mapped[dict | None] = mapped_column(JSON, default=dict, nullable=True)
    response_payload: Mapped[dict | None] = mapped_column(JSON, default=dict, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="success", nullable=False)

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="agent_logs")

    def __repr__(self) -> str:
        return f"<AgentLog(id={self.id}, agent={self.agent_name}, status={self.status}, user_id={self.user_id})>"
