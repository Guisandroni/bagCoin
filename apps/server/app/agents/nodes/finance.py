"""Finance node handlers: intent classification, transaction extraction/persistence, alerts."""

import logging

from app.agents.budget_goal import check_alerts_node
from app.agents.ingestion import classify_intent
from app.agents.normalization import extract_transaction
from app.agents.pending_actions import handle_pending_confirmation
from app.agents.persistence import save_transaction
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


def extract_data_node(state: AgentState) -> AgentState:
    """Nó de extração de dados financeiros."""
    logger.info("Extraindo dados da mensagem")
    result = extract_transaction(dict(state))
    return AgentState(**result)


def save_transaction_node(state: AgentState) -> AgentState:
    """Nó de persistência de transação."""
    logger.info("Salvando transação no banco")
    result = save_transaction(dict(state))
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


def alerts_node(state: AgentState) -> AgentState:
    """Nó de verificação de alertas após transação."""
    logger.info("Verificando alertas")
    result = check_alerts_node(dict(state))
    return AgentState(**result)
