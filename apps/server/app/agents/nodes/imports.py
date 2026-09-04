"""Import statement node handler."""

import logging

from app.agents.import_statement import import_transactions
from app.agents.state import AgentState

logger = logging.getLogger(__name__)


def import_statement_node(state: AgentState) -> AgentState:
    """Nó de importação de extrato bancário."""
    logger.info("Importando extrato bancário")
    result = import_transactions(dict(state))
    return AgentState(**result)
