"""Budget Pydantic schemas."""

from datetime import date, datetime

from pydantic import Field, field_validator

from app.schemas.base import BaseSchema, TimestampSchema


class BudgetItemSchema(BaseSchema):
    """Schema for a budget item (per-category limit)."""

    category_id: int | None = None
    limit_amount: float = Field(gt=0)


class BudgetCreate(BaseSchema):
    """Schema for creating a new budget."""

    name: str = Field(max_length=100)
    period: str = Field(max_length=20)  # monthly, weekly, yearly
    total_limit: float = Field(gt=0)
    budget_type: str | None = Field(default=None, max_length=50)
    budget_date: date = Field(default_factory=date.today)
    category_id: int | None = None
    category_name: str | None = Field(default=None, max_length=100)
    items: list[BudgetItemSchema] = Field(default_factory=list)

    @field_validator("period")
    @classmethod
    def validate_monthly_period(cls, value: str) -> str:
        if value != "monthly":
            raise ValueError("Orçamentos devem ser mensais")
        return value


class BudgetUpdate(BaseSchema):
    """Schema for updating an existing budget."""

    name: str | None = Field(default=None, max_length=100)
    period: str | None = Field(default=None, max_length=20)
    total_limit: float | None = Field(default=None, gt=0)
    budget_type: str | None = Field(default=None, max_length=50)
    budget_date: date | None = None
    category_id: int | None = None
    category_name: str | None = Field(default=None, max_length=100)
    items: list[BudgetItemSchema] | None = None

    @field_validator("period")
    @classmethod
    def validate_monthly_period(cls, value: str | None) -> str | None:
        if value is not None and value != "monthly":
            raise ValueError("Orçamentos devem ser mensais")
        return value


class BudgetResponse(BudgetCreate, TimestampSchema):
    """Schema for reading a budget."""

    id: int
    budget_date: date
    created_at: datetime
    updated_at: datetime | None = None
