"""Conversation sharing schemas."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema


class ConversationShareCreate(BaseSchema):
    """Schema for creating a conversation share."""

    shared_with: int | None = Field(
        default=None, description="User ID to share with (omit for link sharing)"
    )
    permission: Literal["view", "edit"] = Field(default="view", description="Access level")
    generate_link: bool = Field(default=False, description="Generate a public share link")


class ConversationShareRead(BaseSchema):
    """Schema for reading a conversation share."""

    id: UUID
    conversation_id: UUID
    shared_by: int
    shared_with: int | None = None
    share_token: str | None = None
    permission: Literal["view", "edit"] = "view"
    shared_with_email: str | None = Field(default=None, description="Email of the user shared with")
    shared_by_email: str | None = Field(default=None, description="Email of the user who shared")
    created_at: datetime


class ConversationShareList(BaseSchema):
    """Paginated list of conversation shares."""

    items: list[ConversationShareRead]
    total: int


# Admin schemas


class AdminConversationRead(BaseSchema):
    """Admin view of a conversation — includes owner email."""

    id: UUID
    user_id: int | None = None
    title: str | None = None
    is_archived: bool = False
    message_count: int = 0
    user_email: str | None = None
    created_at: datetime
    updated_at: datetime | None = None


class AdminConversationList(BaseSchema):
    """Paginated list of conversations for admin."""

    items: list[AdminConversationRead]
    total: int


class AdminUserRead(BaseSchema):
    """Minimal user info for admin endpoints."""

    id: int
    email: str | None = None
    full_name: str | None = None
    is_active: bool = True
    conversation_count: int = 0
    created_at: datetime


class AdminUserList(BaseSchema):
    """Paginated list of users for admin."""

    items: list[AdminUserRead]
    total: int
