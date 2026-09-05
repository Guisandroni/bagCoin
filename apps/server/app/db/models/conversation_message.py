"""Persistent agent conversation messages."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.phone_conversation import PhoneConversation
    from app.db.models.user import User


class ConversationMessage(Base, TimestampMixin):
    """Full persisted message history for chat-based BagCoin agents."""

    __tablename__ = "conversation_messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    conversation_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("phone_conversations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel: Mapped[str] = mapped_column(String(20), default="whatsapp", nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_metadata: Mapped[dict | None] = mapped_column("metadata", JSON, default=dict, nullable=True)

    user: Mapped[User] = relationship("User", back_populates="conversation_messages")
    conversation: Mapped[PhoneConversation | None] = relationship(
        "PhoneConversation",
        back_populates="messages",
    )

    def __repr__(self) -> str:
        return f"<ConversationMessage(id={self.id}, role={self.role}, user_id={self.user_id})>"
