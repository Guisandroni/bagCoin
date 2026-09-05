"""Report Pydantic schemas."""

from datetime import datetime

from pydantic import Field

from app.schemas.base import BaseSchema, TimestampSchema


class ReportBase(BaseSchema):
    """Base report schema."""

    period_start: datetime
    period_end: datetime
    file_url: str | None = None


class ReportCreate(ReportBase):
    """Schema for creating a new report."""

    pass


class ReportUpdate(BaseSchema):
    """Schema for updating a report."""

    period_start: datetime | None = None
    period_end: datetime | None = None
    file_url: str | None = None


class ReportResponse(ReportBase, TimestampSchema):
    """Schema for reading a report."""

    id: int
    user_id: int | None = None


class ReportGenerateRequest(BaseSchema):
    """Schema for requesting report generation from the web frontend."""

    report_type: str = Field(default="monthly", description="Tipo de relatório: monthly, category, budget")
    month: int = Field(ge=1, le=12, description="Mês (1-12)")
    year: int = Field(ge=2020, le=2100, description="Ano")
