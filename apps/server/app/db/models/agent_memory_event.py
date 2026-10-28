"""Structured memory events for BagCoin agents."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.phone_conversation import PhoneConversation
    from app.db.models.user import User


class AgentMemoryEvent(Base, TimestampMixin):
    """Auditable structured event used to build agent context."""

    __tablename__ = "agent_memory_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    conversation_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("phone_conversations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    entity_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(30), default="agent", nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSON, default=dict, nullable=True)

    user: Mapped[User] = relationship("User", back_populates="agent_memory_events")
    conversation: Mapped[PhoneConversation | None] = relationship(
        "PhoneConversation",
        back_populates="memory_events",
    )

    def __repr__(self) -> str:
        return f"<AgentMemoryEvent(id={self.id}, event={self.event_type}, user_id={self.user_id})>"
