"""AgentState type for the BagCoin LangGraph orchestrator."""

from typing import Any, TypedDict


class AgentState(TypedDict):
    """Estado que trafega pelo grafo LangGraph do BagCoin."""

    phone_number: str
    user_id: int | None
    message: str
    intent: str | None
    macro_intent: str | None
    extracted_data: dict[str, Any] | None
    query_result: dict[str, Any] | None
    report_id: int | None
    report_path: str | None
    report_summary: str | None
    import_summary: str | None
    imported_count: int | None
    skipped_count: int | None
    import_errors: list | None
    budget_data: dict[str, Any] | None
    goal_data: dict[str, Any] | None
    alerts: list | None
    wizard: dict[str, Any] | None
    response: str | None
    context: dict[str, Any]
    error: str | None
    source_format: str
