"""Multimodal node handlers: media processing, document analysis, receipt confirmation."""

import logging
from typing import cast

from app.agents.multimodal import process_multimodal
from app.agents.state import AgentState
from app.agents.tenant_context import tenant_phone_error
from app.agents.tools.documents import create_document_tools
from app.schemas.enums import IntentType

logger = logging.getLogger(__name__)


def process_multimodal_node(state: AgentState) -> AgentState:
    """Nó de processamento de mídia (áudio, imagem, documento)."""
    terr = tenant_phone_error(state.get("phone_number"))
    if terr:
        s = dict(state)
        s["error"] = terr
        return cast(AgentState, s)

    # Web ↔ bot pairing (same entry as multimodal; text-only)
    from app.services.integration_service import try_consume_link_pairing_sync

    ctx = state.get("context") or {}
    integration_channel: str = ctx.get("channel") or (
        "telegram"
        if str(state.get("phone_number", "")).startswith("telegram:")
        else "whatsapp"
    )
    if integration_channel not in ("whatsapp", "telegram"):
        integration_channel = "whatsapp"
    if state.get("source_format") == "text":
        reply = try_consume_link_pairing_sync(
            phone_number=state["phone_number"],
            message=state.get("message") or "",
            channel=integration_channel,  # type: ignore[arg-type]
            source_format=state.get("source_format", "text"),
        )
        if reply is not None:
            s = dict(state)
            s["response"] = reply
            return cast(AgentState, s)

    logger.info(f"Processando mídia: {state.get('source_format', 'text')}")
    result = process_multimodal(dict(state))
    return cast(AgentState, result)


def document_agent_node(state: AgentState) -> AgentState:
    """Analyze uploaded document/image with the document tool."""
    result = dict(state)
    try:
        tool = create_document_tools(
            state.get("phone_number", ""),
            state.get("context") or {},
        )[0]
        result["response"] = str(tool.invoke({}))
        result["intent"] = IntentType.IMPORT_STATEMENT.value
    except Exception as exc:
        logger.exception("[document_agent] failed")
        result["error"] = f"Erro ao analisar documento: {exc}"
    return cast(AgentState, result)


def receipt_confirm_node(state: AgentState) -> AgentState:
    """Cria confirmação para recibo/nota fiscal extraído de imagem."""
    from app.agents.pending_actions import save_pending_action
    from app.agents.tools.documents import (
        _build_receipt_transaction_confirmation,
        _handle_receipt_structured,
        _receipt_transaction_type,
    )

    result = dict(state)
    ctx = state.get("context") or {}
    channel = str(ctx.get("channel") or "whatsapp")
    if channel not in ("whatsapp", "telegram"):
        channel = "whatsapp"
    structured = ctx.get("image_structured") or {}

    if structured.get("needs_type_confirmation"):
        result["response"] = _handle_receipt_structured(
            structured,
            state["phone_number"],
            channel,
        )
        return cast(AgentState, result)

    tx_type = _receipt_transaction_type(structured) or "EXPENSE"
    tx_params, summary = _build_receipt_transaction_confirmation(structured, tx_type)
    tx_params = {**tx_params, "source_format": "image"}

    result["response"] = save_pending_action(
        state["phone_number"],
        action="register_transaction",
        params=tx_params,
        summary=summary,
        channel=channel,
    )
    return cast(AgentState, result)
