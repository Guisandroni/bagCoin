"""Routing functions for the BagCoin LangGraph orchestrator.

route_after_multimodal and route_by_intent decide which node
the graph invokes next.
"""

import logging
import unicodedata

from app.agents.pending_actions import has_pending_confirmation_message
from app.agents.state import AgentState
from app.agents.statement_parser import detect_statement
from app.schemas.enums import IntentType

logger = logging.getLogger(__name__)


def _msg_norm(message: str) -> str:
    return unicodedata.normalize("NFKD", message.lower()).encode("ASCII", "ignore").decode("ASCII")


def _is_account_or_card_request(msg_norm: str) -> bool:
    create_terms = ("criar", "crie", "adicionar", "cadastrar", "abrir", "nova", "novo")
    account_terms = ("conta", "saldo", "banco", "nubank", "itau", "inter", "bradesco", "santander")
    card_terms = ("cartao", "credito", "limite do cartao", "fatura")
    if not any(term in msg_norm for term in create_terms):
        return False
    return any(term in msg_norm for term in account_terms) or any(
        term in msg_norm for term in card_terms
    )


def _is_budget_create_request(msg_norm: str) -> bool:
    budget_terms = ("orcamento", "orcamentos", "limite mensal", "limite por categoria")
    create_terms = ("criar", "crie", "novo", "nova", "definir", "defina", "adicionar")
    delete_terms = ("excluir", "deletar", "apagar", "remover")
    update_terms = ("editar", "alterar", "atualizar", "mudar", "trocar", "aumentar", "diminuir")
    if any(term in msg_norm for term in delete_terms + update_terms):
        return False
    if any(term in msg_norm for term in budget_terms):
        return True
    return any(term in msg_norm for term in create_terms) and "limite" in msg_norm


def route_after_multimodal(state: AgentState) -> str:
    """Roteia após processamento multimodal:
    - Se detectar extrato bancário, vai para import_statement
    - Senão, vai para classify_intent (ponto de entrada unificado)
    """
    error = state.get("error")
    if error:
        return "build_response"
    if state.get("response"):
        return "build_response"
    if has_pending_confirmation_message(
        state.get("phone_number", ""),
        state.get("message", ""),
    ):
        return "pending_confirmation"
    original_format = (state.get("context") or {}).get("original_format")
    # Imagem de recibo com extração estruturada → registrar como transação única
    image_structured = (state.get("context") or {}).get("image_structured")
    if isinstance(image_structured, dict):
        from app.agents.document_understanding import _normalize_receipt_payload

        image_structured = _normalize_receipt_payload(image_structured)
    if (
        original_format == "image"
        and image_structured
        and image_structured.get("is_receipt")
        and (image_structured.get("total_amount") or image_structured.get("items"))
    ):
        logger.info("Recibo identificado na imagem. Criando confirmação de registro.")
        return "receipt_confirm"
    if original_format in {"document", "image"}:
        logger.info("Mídia financeira será analisada pela tool de documentos.")
        return "document_agent"
    if state.get("source_format") == "document" and detect_statement(dict(state)):
        logger.info("Extrato bancário detectado. Roteando para importação.")
        return "import_statement"
    return "classify_intent"


def route_by_intent(state: AgentState) -> str:
    """Roteia para o proximo no baseado na macro-intencao + contexto.

    Usa 8 macro-intencoes em vez de 37 intencoes individuais.
    O desempate (ex: criar vs editar orcamento) e feito pelo handler downstream.
    """
    intent = state.get("intent")
    error = state.get("error")
    macro = state.get("macro_intent", "")

    if error:
        return "build_response"

    # Fast-path: response already set by classify_intent
    if state.get("response"):
        return "build_response"

    if _is_account_or_card_request(_msg_norm(state.get("message", ""))):
        return "smart_manage"

    # === Macro-intent routing ===
    if macro == "register":
        return "register_agent"

    if macro == "query":
        return "smart_query"

    if macro == "manage":
        return "smart_manage"

    if macro == "report":
        return "generate_report"

    if macro == "import_stmt":
        return "import_statement"

    if macro == "recommend":
        return "generate_recommendations"

    if macro == "research":
        return "deep_research"

    # Fallback routing for states that still carry only the detailed intent.
    routing_map = {
        IntentType.REGISTER_EXPENSE.value: "register_agent",
        IntentType.REGISTER_INCOME.value: "register_agent",
        IntentType.QUERY_DATA.value: "smart_query",
        IntentType.GENERATE_REPORT.value: "generate_report",
        IntentType.RECOMMENDATION.value: "generate_recommendations",
        IntentType.DEEP_RESEARCH.value: "deep_research",
        IntentType.IMPORT_STATEMENT.value: "import_statement",
        IntentType.GREETING.value: "chat",
        IntentType.INTRODUCE.value: "chat",
        IntentType.HELP.value: "chat",
        IntentType.CHAT.value: "chat",
        IntentType.CREATE_BUDGET.value: "smart_manage",
        IntentType.CREATE_GOAL.value: "smart_manage",
        IntentType.CONTRIBUTE_GOAL.value: "smart_manage",
        IntentType.DELETE_BUDGET.value: "smart_manage",
        IntentType.UPDATE_BUDGET.value: "smart_manage",
        IntentType.DELETE_GOAL.value: "smart_manage",
        IntentType.UPDATE_GOAL.value: "smart_manage",
        IntentType.DELETE_TRANSACTION.value: "smart_manage",
        IntentType.UPDATE_TRANSACTION.value: "smart_manage",
        IntentType.CORRECTION.value: "smart_manage",
        IntentType.TOGGLE_ALERTS.value: "smart_manage",
        IntentType.CREATE_CATEGORY.value: "smart_manage",
        IntentType.DELETE_CATEGORY.value: "smart_manage",
        IntentType.LIST_CATEGORIES.value: "smart_manage",
        IntentType.UPDATE_CATEGORY.value: "smart_manage",
        IntentType.UNKNOWN.value: "chat",
    }
    return routing_map.get(intent or "", "chat")
