"""Orchestrator — LangGraph state graph for BagCoin agent orchestration.

Connects all agent node handlers (organized by domain in app.agents.nodes)
via LangGraph's StateGraph with conditional routing.
"""

import logging

from langgraph.graph import END, StateGraph

from app.agents.nodes.chat import (
    build_response_node,
    chat_node,
    finalize_response_node,
    wizard_handler_node,
)
from app.agents.nodes.finance import (
    alerts_node,
    classify_intent_node,
    extract_data_node,
    pending_confirmation_node,
    save_transaction_node,
)
from app.agents.nodes.imports import import_statement_node
from app.agents.nodes.multimodal import (
    document_agent_node,
    process_multimodal_node,
    receipt_confirm_node,
)
from app.agents.nodes.register import register_agent_node
from app.agents.nodes.reports import (
    deep_research_node,
    generate_recommendations_node,
    generate_report_node,
)
from app.agents.nodes.smart import (
    smart_manage_node,
    smart_manage_tool_node,
    smart_query_node,
    smart_query_tool_node,
)
from app.agents.routing import route_after_multimodal, route_by_intent
from app.agents.state import AgentState

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)


def create_orchestrator():
    """Cria e retorna o grafo de orquestração LangGraph."""
    workflow = StateGraph(AgentState)

    # Adiciona nós
    workflow.add_node("process_multimodal", process_multimodal_node)
    workflow.add_node("pending_confirmation", pending_confirmation_node)
    workflow.add_node("classify_intent", classify_intent_node)
    workflow.add_node("register_agent", register_agent_node)
    workflow.add_node("document_agent", document_agent_node)
    workflow.add_node("receipt_confirm", receipt_confirm_node)
    workflow.add_node("extract_data", extract_data_node)
    workflow.add_node("save_transaction", save_transaction_node)
    workflow.add_node("check_alerts", alerts_node)
    workflow.add_node("generate_report", generate_report_node)
    workflow.add_node("generate_recommendations", generate_recommendations_node)
    workflow.add_node("deep_research", deep_research_node)
    workflow.add_node("import_statement", import_statement_node)
    workflow.add_node("wizard", wizard_handler_node)
    workflow.add_node("smart_query", smart_query_node)
    workflow.add_node("smart_manage", smart_manage_node)
    workflow.add_node("chat", chat_node)
    workflow.add_node("build_response", build_response_node)
    workflow.add_node("finalize_response", finalize_response_node)

    # Define fluxo
    # 1. Sempre processa multimodal primeiro (se for texto, passa direto)
    workflow.set_entry_point("process_multimodal")

    workflow.add_conditional_edges(
        "process_multimodal",
        route_after_multimodal,
        {
            "classify_intent": "classify_intent",
            "pending_confirmation": "pending_confirmation",
            "receipt_confirm": "receipt_confirm",
            "document_agent": "document_agent",
            "import_statement": "import_statement",
            "build_response": "build_response",
        },
    )

    # 2. Classifica intenção do texto (original ou extraído da mídia)
    workflow.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {
            "extract_data": "extract_data",
            "register_agent": "register_agent",
            "smart_query": "smart_query",
            "smart_manage": "smart_manage",
            "generate_report": "generate_report",
            "generate_recommendations": "generate_recommendations",
            "deep_research": "deep_research",
            "wizard": "wizard",
            "chat": "chat",
            "build_response": "build_response",
        },
    )

    workflow.add_edge("pending_confirmation", "build_response")
    workflow.add_edge("register_agent", "build_response")
    workflow.add_edge("receipt_confirm", "build_response")
    workflow.add_edge("document_agent", "build_response")
    workflow.add_edge("extract_data", "save_transaction")
    workflow.add_edge("save_transaction", "check_alerts")
    workflow.add_edge("check_alerts", "build_response")
    workflow.add_edge("generate_report", "build_response")
    workflow.add_edge("generate_recommendations", "build_response")
    workflow.add_edge("deep_research", "build_response")
    workflow.add_edge("import_statement", "build_response")
    workflow.add_edge("wizard", "build_response")
    workflow.add_edge("chat", "build_response")
    workflow.add_edge("smart_query", "build_response")
    workflow.add_edge("smart_manage", "build_response")
    workflow.add_edge("build_response", "finalize_response")
    workflow.add_edge("finalize_response", END)

    return workflow.compile()


# Instância global do orquestrador
orchestrator = create_orchestrator()
