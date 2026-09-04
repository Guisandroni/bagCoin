"""Account Pydantic schemas."""

from datetime import datetime
from typing import Literal
from pydantic import Field

from app.schemas.base import BaseSchema, TimestampSchema


class AccountBase(BaseSchema):
    """Base account schema."""

    name: str = Field(max_length=100)
    bank: str = Field(max_length=100)
    type: Literal["CHECKING", "SAVINGS"] = "CHECKING"
    balance: float = 0.0
    color: str | None = Field(default=None, max_length=7)
    active: bool = True


class AccountCreate(AccountBase):
    """Schema for creating a new account."""

    pass


class AccountUpdate(BaseSchema):
    """Schema for updating an existing account."""

    name: str | None = Field(default=None, max_length=100)
    bank: str | None = Field(default=None, max_length=100)
    type: Literal["CHECKING", "SAVINGS"] | None = None
    balance: float | None = None
    color: str | None = Field(default=None, max_length=7)
    active: bool | None = None


class AccountResponse(AccountBase, TimestampSchema):
    """Schema for reading an account."""

    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime | None = None
