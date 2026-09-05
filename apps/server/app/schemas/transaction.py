"""Transaction Pydantic schemas."""

from datetime import datetime
from typing import Literal

from pydantic import Field

from app.schemas.base import BaseSchema, TimestampSchema
from app.schemas.enums import SourceFormat, TransactionType

# === Internal schemas (WhatsApp/Telegram) ===


class TransactionCreate(BaseSchema):
    """Schema for creating a new transaction (internal/WhatsApp)."""

    user_id: int
    type: TransactionType
    amount: float = Field(gt=0)
    currency: str = Field(default="BRL", max_length=3)
    category_id: int | None = None
    description: str | None = Field(default=None, max_length=500)
    source_format: SourceFormat = SourceFormat.TEXT
    transaction_date: datetime | None = None
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)
    raw_input: str | None = None


class TransactionUpdate(BaseSchema):
    """Schema for updating an existing transaction."""

    type: TransactionType | None = None
    amount: float | None = Field(default=None, gt=0)
    currency: str | None = Field(default=None, max_length=3)
    category_id: int | None = None
    description: str | None = Field(default=None, max_length=500)
    source_format: SourceFormat | None = None
    transaction_date: datetime | None = None
    confidence_score: float | None = Field(default=None, ge=0.0, le=1.0)
    raw_input: str | None = None


class TransactionResponse(TransactionCreate, TimestampSchema):
    """Schema for reading a transaction."""

    id: int
    created_at: datetime
    updated_at: datetime | None = None


# === REST API schemas (web frontend) ===


class TransactionRestCreate(BaseSchema):
    """Schema for creating a transaction via the web frontend."""

    type: Literal["EXPENSE", "INCOME"] = "EXPENSE"
    amount: float = Field(gt=0, description="Transaction amount (positive)")
    description: str = Field(min_length=1, max_length=500)
    category_name: str | None = Field(default=None, max_length=100)
    category_id: int | None = None
    transaction_date: str | None = Field(
        default=None,
        description="ISO date string (e.g. '2026-04-30')",
    )
    source: Literal["manual", "auto"] = "manual"
    status: Literal["confirmed", "pending"] = "confirmed"
    is_recurring: bool = False
    recurrence_frequency: Literal["weekly", "monthly", "yearly"] | None = None


class TransactionRestUpdate(BaseSchema):
    """Schema for updating a transaction via the web frontend."""

    type: Literal["EXPENSE", "INCOME"] | None = None
    amount: float | None = Field(default=None, gt=0)
    description: str | None = Field(default=None, min_length=1, max_length=500)
    category_id: int | None = None
    category_name: str | None = Field(default=None, max_length=100)
    transaction_date: str | None = None
    status: Literal["confirmed", "pending"] | None = None
    is_recurring: bool | None = None
    recurrence_frequency: Literal["weekly", "monthly", "yearly"] | None = None


class TransactionRestResponse(BaseSchema, TimestampSchema):
    """Transaction response schema matching frontend types."""

    id: str  # stringified ID for frontend compatibility
    type: Literal["EXPENSE", "INCOME"]
    name: str
    category: str
    category_id: int | None = None
    category_name: str | None = None
    amount: float
    date: str
    transaction_date: str | None = None
    source: str
    status: str
    is_recurring: bool = False
    recurrence_frequency: Literal["weekly", "monthly", "yearly"] | None = None


class TransactionListResponse(BaseSchema):
    """Paginated list of transactions."""

    items: list[TransactionRestResponse]
    total: int


class TransactionSummaryResponse(BaseSchema):
    """Dashboard summary for frontend."""

    balance: float
    total_income: float
    total_expenses: float
    transaction_count: int
    categories: list[dict]
    recent_transactions: list[TransactionRestResponse]
