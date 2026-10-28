"""Report and research node handlers."""

import logging

from app.agents.deep_research import deep_research
from app.agents.recommendations import generate_recommendations
from app.agents.reports import generate_report
from app.agents.state import AgentState

logger = logging.getLogger(__name__)


def generate_report_node(state: AgentState) -> AgentState:
    """Nó de geração de relatório."""
    logger.info("Gerando relatório")
    result = generate_report(dict(state))
    return AgentState(**result)


def generate_recommendations_node(state: AgentState) -> AgentState:
    """Nó de recomendações financeiras."""
    logger.info("Gerando recomendações")
    result = generate_recommendations(dict(state))
    return AgentState(**result)


def deep_research_node(state: AgentState) -> AgentState:
    """Nó de pesquisa aprofundada."""
    logger.info("Realizando pesquisa")
    result = deep_research(dict(state))
    return AgentState(**result)
