"""PhoneConversation model — WhatsApp/Telegram conversation context tracking."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.agent_memory_event import AgentMemoryEvent
    from app.db.models.conversation_message import ConversationMessage
    from app.db.models.user import User


class PhoneConversation(Base, TimestampMixin):
    """Tracks WhatsApp/Telegram conversation context for BagCoin agents."""

    __tablename__ = "phone_conversations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel: Mapped[str] = mapped_column(String(20), default="whatsapp", nullable=False)
    last_intent: Mapped[str | None] = mapped_column(String(50), nullable=True)
    context_json: Mapped[dict | None] = mapped_column(JSON, default=dict, nullable=True)
    message_history: Mapped[list | None] = mapped_column(JSON, default=list, nullable=True)

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="conversations")
    messages: Mapped[list[ConversationMessage]] = relationship(
        "ConversationMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )
    memory_events: Mapped[list[AgentMemoryEvent]] = relationship(
        "AgentMemoryEvent",
        back_populates="conversation",
    )

    def __repr__(self) -> str:
        return f"<PhoneConversation(id={self.id}, user_id={self.user_id}, channel={self.channel})>"
