"""Finance node handlers: intent classification, transaction extraction/persistence, alerts."""

import logging

from app.agents.ingestion import classify_intent
from app.agents.pending_actions import handle_pending_confirmation
from app.agents.state import AgentState

logger = logging.getLogger(__name__)


def classify_intent_node(state: AgentState) -> AgentState:
    """Nó de classificação de intenção."""
    logger.info(
        "Classificando intenção para: %s — msg: %s",
        state["phone_number"],
        state.get("message", "")[:60],
    )
    result = classify_intent(dict(state))
    return AgentState(**result)


def pending_confirmation_node(state: AgentState) -> AgentState:
    """Executa ou cancela uma acao financeira pendente."""
    response = handle_pending_confirmation(
        state.get("phone_number", ""),
        state.get("message", ""),
    )
    if response:
        state["response"] = response
    else:
        state["response"] = "Nao encontrei uma acao pendente para confirmar."
    return state
