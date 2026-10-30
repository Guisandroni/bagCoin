"""Durable inbound events and ordered outbound replies for Evolution."""

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class EvolutionEvent(Base, TimestampMixin):
    __tablename__ = "evolution_events"
    __table_args__ = (
        UniqueConstraint("instance", "message_id", name="uq_evolution_event_instance_message"),
        CheckConstraint(
            "status IN ('processing', 'completed', 'uncertain')",
            name="evolution_event_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    instance: Mapped[str] = mapped_column(String(100), nullable=False)
    message_id: Mapped[str] = mapped_column(String(255), nullable=False)
    owner: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)


class EvolutionReply(Base, TimestampMixin):
    __tablename__ = "evolution_replies"
    __table_args__ = (
        UniqueConstraint("event_id", "position", name="uq_evolution_reply_event_position"),
        CheckConstraint(
            "status IN ('pending', 'sending', 'sent', 'uncertain')",
            name="evolution_reply_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("evolution_events.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
