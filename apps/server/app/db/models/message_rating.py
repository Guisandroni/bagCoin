"""Message rating model for user feedback on AI responses."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.conversation import Message
    from app.db.models.user import User


class MessageRating(Base, TimestampMixin):
    """User rating for AI assistant messages."""

    __tablename__ = "message_ratings"
    __table_args__ = (
        UniqueConstraint("message_id", "user_id", name="uq_message_user_rating"),
        CheckConstraint("rating IN (1, -1)", name="ck_rating_value"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    message: Mapped["Message"] = relationship("Message", foreign_keys="MessageRating.message_id")
    user: Mapped["User"] = relationship("User", foreign_keys="MessageRating.user_id")

    def __repr__(self) -> str:
        return f"<MessageRating(id={self.id}, rating={self.rating})>"
