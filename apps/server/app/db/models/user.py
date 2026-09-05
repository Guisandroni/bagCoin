"""Unified User database model (web + agent)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.account import Account
    from app.db.models.agent_log import AgentLog
    from app.db.models.agent_memory_event import AgentMemoryEvent
    from app.db.models.budget import Budget
    from app.db.models.category import Category
    from app.db.models.conversation_message import ConversationMessage
    from app.db.models.credit_card import CreditCard
    from app.db.models.goal import Goal
    from app.db.models.integration_link_token import IntegrationLinkToken
    from app.db.models.phone_conversation import PhoneConversation
    from app.db.models.report import Report
    from app.db.models.transaction import Transaction


class UserRole(StrEnum):
    ADMIN = "admin"
    USER = "user"


class User(Base, TimestampMixin):
    """Unified user model for web and agent (WhatsApp/Telegram) channels."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Web auth fields
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    google_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    auth_provider: Mapped[str | None] = mapped_column(String(20), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    email_verification_code_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email_verification_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    email_verification_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    email_verification_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    password_reset_token_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_reset_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    password_reset_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Agent fields (WhatsApp/Telegram)
    phone_number: Mapped[str | None] = mapped_column(String(80), unique=True, index=True, nullable=True)
    telegram_chat_id: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True, index=True)
    platform: Mapped[str | None] = mapped_column(String(20), nullable=True)
    preferences: Mapped[dict | None] = mapped_column(JSON, default=dict, nullable=True)
    financial_profile: Mapped[dict | None] = mapped_column(JSON, default=dict, nullable=True)

    # Common fields
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    role: Mapped[str] = mapped_column(String(50), default=UserRole.USER.value, nullable=False)

    # Relationships
    transactions: Mapped[list[Transaction]] = relationship(
        "Transaction", back_populates="user", cascade="all, delete-orphan"
    )
    budgets: Mapped[list[Budget]] = relationship(
        "Budget", back_populates="user", cascade="all, delete-orphan"
    )
    goals: Mapped[list[Goal]] = relationship(
        "Goal", back_populates="user", cascade="all, delete-orphan"
    )
    reports: Mapped[list[Report]] = relationship(
        "Report", back_populates="user", cascade="all, delete-orphan"
    )
    credit_cards: Mapped[list[CreditCard]] = relationship(
        "CreditCard", back_populates="user", cascade="all, delete-orphan"
    )
    accounts: Mapped[list[Account]] = relationship(
        "Account", back_populates="user", cascade="all, delete-orphan"
    )
    integration_link_tokens: Mapped[list[IntegrationLinkToken]] = relationship(
        "IntegrationLinkToken", back_populates="user", cascade="all, delete-orphan"
    )
    categories: Mapped[list[Category]] = relationship(
        "Category", back_populates="user", cascade="all, delete-orphan"
    )
    conversations: Mapped[list[PhoneConversation]] = relationship(
        "PhoneConversation", back_populates="user", cascade="all, delete-orphan"
    )
    agent_logs: Mapped[list[AgentLog]] = relationship(
        "AgentLog", back_populates="user", cascade="all, delete-orphan"
    )
    conversation_messages: Mapped[list[ConversationMessage]] = relationship(
        "ConversationMessage", back_populates="user", cascade="all, delete-orphan"
    )
    agent_memory_events: Mapped[list[AgentMemoryEvent]] = relationship(
        "AgentMemoryEvent", back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def user_role(self) -> UserRole:
        return UserRole(self.role)

    @property
    def email_verified(self) -> bool:
        return self.email_verified_at is not None

    def has_role(self, required_role: UserRole) -> bool:
        if self.role == UserRole.ADMIN.value:
            return True
        return self.role == required_role.value

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, phone={self.phone_number})>"
