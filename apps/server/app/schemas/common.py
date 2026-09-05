"""Common BagCoin schemas — webhooks, agent state, etc."""


from pydantic import Field

from app.schemas.base import BaseSchema
from app.schemas.enums import IntentType, SourceFormat


class WebhookPayload(BaseSchema):
    """Incoming webhook payload from WhatsApp bridge."""

    phone_number: str
    message: str = ""
    type: str = "chat"
    timestamp: int = 0
    hasMedia: bool = False
    media: dict | None = None
    raw_data: dict | None = None


class WhatsAppResponse(BaseSchema):
    """Outgoing response to the WhatsApp bridge."""

    reply: str
    document: dict | None = None
    media: dict | None = None
    actions: list[dict] | None = None


class TelegramWebhookPayload(BaseSchema):
    """Incoming webhook payload from Telegram bridge."""

    chat_id: str
    message: str = ""
    username: str | None = None
    source_format: str = "text"
    media: dict | None = None


class TelegramResponse(BaseSchema):
    """Outgoing response to the Telegram caller."""

    reply: str
    media: dict | None = None
    actions: list


class ExtractedTransaction(BaseSchema):
    """Transaction data extracted by the AI agent from natural language."""

    type: str
    amount: float | None = None
    currency: str = "BRL"
    category: str | None = None
    description: str | None = None
    date: str | None = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)
    raw_text: str | None = None


class QueryResult(BaseSchema):
    """Result of a natural-language database query."""

    sql: str | None = None
    results: list[dict] | None = None
    summary: str | None = None
    error: str | None = None


class ReportRequest(BaseSchema):
    """Request to generate a financial report."""

    period_start: str | None = None
    period_end: str | None = None
    category_id: int | None = None


class AgentState(BaseSchema):
    """State that flows through the LangGraph agent graph."""

    phone_number: str
    user_id: int | None = None
    message: str
    intent: IntentType | None = None
    extracted_data: dict | None = None
    query_result: QueryResult | None = None
    report_id: int | None = None
    report_path: str | None = None
    report_summary: str | None = None
    import_summary: str | None = None
    imported_count: int | None = None
    skipped_count: int | None = None
    import_errors: list[str] | None = None
    budget_data: dict | None = None
    goal_data: dict | None = None
    alerts: list[dict] | None = None
    wizard: dict | None = None
    response: str | None = None
    context: dict = Field(default_factory=dict)
    error: str | None = None
    source_format: SourceFormat = SourceFormat.TEXT
