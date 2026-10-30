"""PhoneUser model - BagCoin user identified by phone number."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.db.models.enums import UserStatus

if TYPE_CHECKING:
    from app.db.models.user import User


class PhoneUser(Base, TimestampMixin):
    """BagCoin user identified by phone number.

    This is separate from the auth User model — it represents a
    financial profile user reachable via WhatsApp.

    Attributes:
        id: Auto-increment primary key (SERIAL).
        phone_number: Unique phone number identifier.
        name: Optional display name.
        status: Account status (active/inactive/blocked).
        preferences: JSON blob for user preferences.
        financial_profile: JSON blob for financial profile data.
        platform: Communication platform (whatsapp).
    """

    __tablename__ = "phone_users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    phone_number: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[UserStatus] = mapped_column(
        String(20), default=UserStatus.ACTIVE.value, nullable=False
    )
    preferences: Mapped[dict | None] = mapped_column(JSON, default=dict, nullable=True)
    financial_profile: Mapped[dict | None] = mapped_column(JSON, default=dict, nullable=True)
    platform: Mapped[str] = mapped_column(String(20), default="whatsapp", nullable=False)
    merged_into_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Relationships
    merged_into_user: Mapped["User | None"] = relationship("User", foreign_keys=[merged_into_user_id])

    # Relationships (phone profile)
    categories: Mapped[list["Category"]] = relationship(
        "Category",
        back_populates="phone_user",
        cascade="all, delete-orphan",
    )
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction",
        back_populates="phone_user",
        cascade="all, delete-orphan",
    )
    budgets: Mapped[list["Budget"]] = relationship(
        "Budget",
        back_populates="phone_user",
        cascade="all, delete-orphan",
    )
    goals: Mapped[list["Goal"]] = relationship(
        "Goal",
        back_populates="phone_user",
        cascade="all, delete-orphan",
    )
    reports: Mapped[list["Report"]] = relationship(
        "Report",
        back_populates="phone_user",
        cascade="all, delete-orphan",
    )
    conversations: Mapped[list["PhoneConversation"]] = relationship(
        "PhoneConversation",
        back_populates="phone_user",
        cascade="all, delete-orphan",
    )
    agent_logs: Mapped[list["AgentLog"]] = relationship(
        "AgentLog",
        back_populates="phone_user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<PhoneUser(id={self.id}, phone={self.phone_number}, status={self.status})>"
