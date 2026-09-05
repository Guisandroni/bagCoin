"""Shared conversation context for tool-agent node handlers."""


def tool_history(phone_number: str, limit: int = 6) -> str:
    """Format recent conversation history for tool-agent context."""
    from app.services.agent_memory_service import build_agent_context_text

    return build_agent_context_text(phone_number, message_limit=limit) or ""
