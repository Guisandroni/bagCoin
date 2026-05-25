"""Orchestrator — LangGraph state graph for BagCoin agent orchestration.

Defines the AgentState TypedDict and connects all agent nodes
via LangGraph's StateGraph with conditional routing.
"""

import logging
import re
import unicodedata
from datetime import UTC, datetime
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from app.agents import responses as resp
from app.agents.budget_goal import (
    check_alerts_node,
    contribute_goal_node,
    create_budget_node,
    create_goal_node,
    delete_budget_node,
    delete_goal_node,
    delete_transaction_node,
    query_budgets_node,
    toggle_alerts_node,
    update_budget_node,
    update_goal_node,
    update_transaction_node,
)
from app.agents.deep_research import deep_research
from app.agents.import_statement import import_transactions
from app.agents.ingestion import classify_intent
from app.agents.humanize import humanize_safely, should_humanize
from app.agents.multimodal import process_multimodal
from app.agents.normalization import extract_transaction
from app.agents.persistence import save_message_to_history, save_transaction
from app.agents.pending_actions import (
    handle_pending_confirmation,
    has_pending_confirmation_message,
    save_pending_action,
)
from app.agents.recommendations import generate_recommendations
from app.agents.reports import generate_report
from app.agents.statement_parser import detect_statement
from app.agents.tenant_context import tenant_phone_error
from app.agents.text_to_sql import process_query
from app.agents.tools.documents import create_document_tools
from app.agents.wizard import wizard_node
from app.core.config import settings
from app.db.session import sync_session_maker
from app.schemas.enums import IntentType
from app.services.integration_service import redact_message_for_log
from app.services.llm_service import get_llm, timed_invoke

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """Estado que trafega pelo grafo LangGraph do BagCoin."""

    phone_number: str
    user_id: int | None
    message: str
    intent: str | None
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


def process_multimodal_node(state: AgentState) -> AgentState:
    """Nó de processamento de mídia (áudio, imagem, documento)."""
    terr = tenant_phone_error(state.get("phone_number"))
    if terr:
        s = dict(state)
        s["error"] = terr
        return AgentState(**s)

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
            return AgentState(**s)

    logger.info(f"Processando mídia: {state.get('source_format', 'text')}")
    result = process_multimodal(dict(state))
    if result.get("error"):
        return AgentState(**result)
    return AgentState(**result)


def import_statement_node(state: AgentState) -> AgentState:
    """Nó de importação de extrato bancário."""
    logger.info("Importando extrato bancário")
    result = import_transactions(dict(state))
    return AgentState(**result)


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
    return AgentState(**result)


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
        return AgentState(**result)

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
    return AgentState(**result)


def classify_intent_node(state: AgentState) -> AgentState:
    """Nó de classificação de intenção."""
    logger.info(
        "Classificando intenção para: %s — msg: %s",
        state["phone_number"],
        redact_message_for_log(state.get("message", ""), 60),
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


def process_query_node(state: AgentState) -> AgentState:
    """Nó de consulta text-to-SQL."""
    logger.info("Processando consulta")
    result = process_query(dict(state))
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


def budget_node(state: AgentState) -> AgentState:
    """Nó de criação de orçamento."""
    logger.info("Criando orçamento")
    result = create_budget_node(dict(state))
    return AgentState(**result)


def goal_node(state: AgentState) -> AgentState:
    """Nó de criação de meta."""
    logger.info("Criando meta")
    result = create_goal_node(dict(state))
    return AgentState(**result)


def alerts_node(state: AgentState) -> AgentState:
    """Nó de verificação de alertas após transação."""
    logger.info("Verificando alertas")
    result = check_alerts_node(dict(state))
    return AgentState(**result)


def budgets_query_node(state: AgentState) -> AgentState:
    """Nó de consulta de orçamentos/metas."""
    logger.info("Consultando budgets/goals")
    result = query_budgets_node(dict(state))
    return AgentState(**result)


def update_budget_handler_node(state: AgentState) -> AgentState:
    """Nó de atualização de orçamento."""
    logger.info("Atualizando budget")
    result = update_budget_node(dict(state))
    return AgentState(**result)


def contribute_goal_handler_node(state: AgentState) -> AgentState:
    """Nó de contribuição para meta."""
    logger.info("Contribuindo para meta")
    result = contribute_goal_node(dict(state))
    return AgentState(**result)


def delete_goal_handler_node(state: AgentState) -> AgentState:
    """Nó de exclusão de meta."""
    logger.info("Excluindo meta")
    result = delete_goal_node(dict(state))
    return AgentState(**result)


def update_goal_handler_node(state: AgentState) -> AgentState:
    """Nó de atualização de meta."""
    logger.info("Atualizando meta")
    result = update_goal_node(dict(state))
    return AgentState(**result)


def delete_transaction_handler_node(state: AgentState) -> AgentState:
    """Nó de exclusão de transação."""
    logger.info("Excluindo transação")
    result = delete_transaction_node(dict(state))
    return AgentState(**result)


def update_transaction_handler_node(state: AgentState) -> AgentState:
    """Nó de atualização de transação."""
    logger.info("Atualizando transação")
    result = update_transaction_node(dict(state))
    return AgentState(**result)


def update_category_handler_node(state: AgentState) -> AgentState:
    """Nó de renomear categoria."""
    from app.agents.persistence import list_categories, rename_category

    phone_number = state.get("phone_number", "")
    message = state.get("message", "")
    msg_norm = (
        unicodedata.normalize("NFKD", message.lower()).encode("ASCII", "ignore").decode("ASCII")
    )
    match = re.search(
        r'(?:renomear|mudar nome da|alterar)\s+categoria\s+["\']?(.+?)["\']?\s+(?:para|->)\s+["\']?(.+?)["\']?$',
        msg_norm,
    )
    if match:
        old_name = match.group(1).strip().capitalize()
        new_name = match.group(2).strip().capitalize()
        if rename_category(phone_number, old_name, new_name):
            state["response"] = f"Categoria '{old_name}' renomeada para '{new_name}'."
        else:
            state["response"] = f"Não encontrei a categoria '{old_name}'."
    else:
        cats = list_categories(phone_number)
        user_cats = [c["name"] for c in cats if not c["is_default"]]
        if user_cats:
            state["response"] = (
                "Para renomear, use: 'renomear categoria NOME_ANTIGO para NOVO_NOME'. Categorias: "
                + ", ".join(user_cats)
            )
        else:
            state["response"] = "Você não tem categorias personalizadas para renomear."
    return state


def _msg_norm(message: str) -> str:
    import unicodedata

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
    if any(term in msg_norm for term in budget_terms):
        return True
    return any(term in msg_norm for term in create_terms) and "limite" in msg_norm


def _extract_budget_request(message: str) -> dict[str, Any] | None:
    amount_match = re.search(
        r"(?:r\$?\s*)?(\d{1,3}(?:[.,]\d{3})*[.,]\d{1,2}|\d+(?:[.,]\d{1,2})?)",
        message,
        flags=re.IGNORECASE,
    )
    if not amount_match:
        return None
    raw_amount = amount_match.group(1)
    normalized_amount = raw_amount.replace(".", "").replace(",", ".")
    try:
        total_limit = float(normalized_amount)
    except ValueError:
        return None

    category_text = message[: amount_match.start()] + " " + message[amount_match.end() :]
    category_text = _msg_norm(category_text)
    category_text = re.sub(
        r"\b(criar|crie|quero|novo|nova|definir|defina|adicionar|um|uma|de|do|da|para|pra|em|na|no|categoria|orcamento|orcamentos|limite|mensal|mes|por|r)\b",
        " ",
        category_text,
    )
    category_text = re.sub(r"\s+", " ", category_text).strip(" .,!?\n\t")
    if not category_text:
        return None

    from app.core.financial_categories import resolve_default_category_name

    return {
        "name": resolve_default_category_name(category_text),
        "total_limit": total_limit,
        "period": "monthly",
        "budget_type": "category",
    }


def _format_recent_transaction_for_prompt(tx: Any) -> str:
    if isinstance(tx, dict):
        tx_id = tx.get("id", "?")
        name = tx.get("name") or tx.get("description") or ""
        amount = tx.get("amount") or 0
        date = tx.get("date") or tx.get("transaction_date") or "?"
    else:
        tx_id = getattr(tx, "id", "?")
        name = getattr(tx, "description", "") or ""
        amount = getattr(tx, "amount", 0) or 0
        date = getattr(tx, "transaction_date", "?")
    try:
        amount_value = float(amount)
    except (TypeError, ValueError):
        amount_value = 0.0
    return f"- id={tx_id}: {name} R${amount_value:.2f} ({date})"


def _transaction_type_label(tx: Any) -> str:
    tx_type = tx.get("type") if isinstance(tx, dict) else getattr(tx, "type", "")
    tx_type_value = getattr(tx_type, "value", tx_type)
    return "Receita" if str(tx_type_value).upper() == "INCOME" else "Gasto"


def _money(value: Any) -> str:
    try:
        amount = float(value or 0)
    except (TypeError, ValueError):
        amount = 0.0
    return f"R$ {amount:,.2f}"


def _smart_query_needs_budget_goal_context(msg_norm: str) -> bool:
    terms = (
        "orcamento",
        "orcamentos",
        "budget",
        "budgets",
        "meta",
        "metas",
        "objetivo",
        "objetivos",
        "goal",
        "goals",
    )
    return any(term in msg_norm for term in terms)


def _build_financial_snapshot_response(
    message: str,
    transactions: list[Any],
    budgets: list[dict[str, Any]],
    goals: list[dict[str, Any]],
) -> str:
    msg_norm = _msg_norm(message)
    wants_spending = any(
        term in msg_norm
        for term in ("gasto", "gastos", "despesa", "despesas", "transacao", "transacoes")
    )
    wants_budgets = any(term in msg_norm for term in ("orcamento", "orcamentos", "budget", "budgets"))
    wants_goals = any(
        term in msg_norm for term in ("meta", "metas", "objetivo", "objetivos", "goal", "goals")
    )

    if not any((wants_spending, wants_budgets, wants_goals)):
        wants_spending = wants_budgets = wants_goals = True

    parts: list[str] = []
    if wants_spending:
        expenses = [
            tx
            for tx in transactions
            if str(getattr(getattr(tx, "type", ""), "value", getattr(tx, "type", ""))).upper()
            == "EXPENSE"
        ]
        total = sum(abs(float(getattr(tx, "amount", 0) or 0)) for tx in expenses)
        lines = [f"Gastos recentes: {_money(total)} em {len(expenses)} lançamento(s)."]
        for tx in expenses[:5]:
            description = getattr(tx, "description", None) or "Sem descrição"
            lines.append(f"- {_money(getattr(tx, 'amount', 0))}: {description}")
        parts.append("\n".join(lines))

    if wants_budgets:
        parts.append(resp.budget_list(budgets))

    if wants_goals:
        parts.append(resp.goal_list(goals))

    return "\n\n".join(part for part in parts if part.strip())


def create_category_handler_node(state: AgentState) -> AgentState:
    """Nó de criação de categoria."""
    from app.agents.persistence import create_category

    phone_number = state.get("phone_number", "")
    message = state.get("message", "")
    msg_norm = _msg_norm(message)
    name = None
    for prefix in [
        "criar categoria ",
        "nova categoria ",
        "adicionar categoria ",
        "crie uma categoria ",
    ]:
        if prefix in msg_norm:
            idx = msg_norm.find(prefix) + len(prefix)
            name = message[idx:].strip().capitalize()
            break
    if not name or len(name) < 2:
        state["response"] = "Qual o nome da nova categoria? Ex: 'Criar categoria Academia'"
        return state
    result = create_category(phone_number, name)
    if result is None:
        state["response"] = f"A categoria '{name}' já existe."
    else:
        state["response"] = f"Categoria '{name}' criada com sucesso!"
    return state


def delete_category_handler_node(state: AgentState) -> AgentState:
    """Nó de exclusão de categoria."""
    from app.agents.persistence import delete_category, list_categories

    phone_number = state.get("phone_number", "")
    message = state.get("message", "")
    msg_norm = _msg_norm(message)
    name = None
    for prefix in ["excluir categoria ", "apagar categoria ", "remover categoria "]:
        if prefix in msg_norm:
            idx = msg_norm.find(prefix) + len(prefix)
            name = message[idx:].strip().capitalize()
            break
    if not name or len(name) < 2:
        cats = list_categories(phone_number)
        user_cats = [c["name"] for c in cats if not c["is_default"]]
        if user_cats:
            state["response"] = "Qual categoria deseja excluir? " + ", ".join(user_cats)
        else:
            state["response"] = "Você não tem categorias personalizadas para excluir."
        return state
    if delete_category(phone_number, name):
        state["response"] = f"Categoria '{name}' removida."
    else:
        state["response"] = (
            f"Não encontrei a categoria '{name}' ou ela é padrão e não pode ser removida."
        )
    return state


def list_categories_handler_node(state: AgentState) -> AgentState:
    """Nó de listagem de categorias."""
    from app.agents.persistence import list_categories

    phone_number = state.get("phone_number", "")
    cats = list_categories(phone_number)
    if not cats:
        state["response"] = "Você não tem categorias ainda."
        return state
    default_cats = [c["name"] for c in cats if c["is_default"]]
    user_cats = [c["name"] for c in cats if not c["is_default"]]
    lines = ["Suas categorias:"]
    if default_cats:
        lines.append("\nPadrão: " + ", ".join(default_cats))
    if user_cats:
        lines.append("\nPersonalizadas: " + ", ".join(user_cats))
    state["response"] = "".join(lines)
    return state


def intro_handler_node(state: AgentState) -> AgentState:
    """Nó de introdução do usuário (nome)."""
    import re as regex

    from app.agents.persistence import save_user_name

    message = state.get("message", "")
    phone_number = state.get("phone_number", "")

    patterns = [
        r"(?:meu nome [eé]|me chamo|pode me chamar de|eu sou o|eu sou a)\s+([a-zA-ZÀ-ÿ]+)",
    ]
    name = None
    for p in patterns:
        m = regex.search(p, message, regex.IGNORECASE)
        if m:
            name = m.group(1).strip().capitalize()
            break
    if name:
        save_user_name(phone_number, name)
        state["response"] = f"Prazer em conhecer você, {name}! Como posso ajudar?"
    else:
        state["response"] = "Prazer em conhecer você! Como posso ajudar?"
    return state


def correction_handler_node(state: AgentState) -> AgentState:
    """Nó de correção de transação — suporta valor, categoria, descrição."""
    import re as regex

    phone_number = state.get("phone_number", "")
    message = state.get("message", "")

    # 1. Correção de valor: "R$ 50" ou "na verdade foi R$ 60"
    amount_match = regex.search(
        r"R?\$\s*(\d{1,3}(?:[.,]\d{3})*[.,]\d{1,2}|\d+(?:[.,]\d{1,2})?)", message
    )
    if amount_match:
        return update_transaction_handler_node(state)

    # 2. Correção de categoria: "era Alimentação" / "categoria certa é Transporte"
    msg_lower = message.lower()
    cat_match = regex.search(
        r"(?:era|categoria\s+(?:certa|correta)\s+[ée])\s+([a-zA-ZÀ-ÿ\s]+)", msg_lower
    )
    if not cat_match:
        cat_match = regex.search(
            r"(?:corrige|muda)\s+(?:a\s+)?categoria\s+(?:para|como)\s+([a-zA-ZÀ-ÿ\s]+)", msg_lower
        )
    if cat_match:
        state["extracted_data"] = {
            "category_name": cat_match.group(1).strip().capitalize()
        }
        return update_transaction_handler_node(state)

    # 3. Correção de descrição: "o nome é Mercado" / "descrição certa é Padaria"
    desc_match = regex.search(r"(?:o\s+)?nome\s+(?:[ée]|certo\s+[ée])\s+(.+)", msg_lower)
    if not desc_match:
        desc_match = regex.search(r"descrição\s+(?:certa\s+)?[ée]\s+(.+)", msg_lower)
    if desc_match:
        state["extracted_data"] = {
            "description": desc_match.group(1).strip().capitalize()
        }
        return update_transaction_handler_node(state)

    # Fallback: pergunta o que corrigir
    state["response"] = (
        "O que você quer corrigir?\n"
        "• Valor: 'era R$ 60'\n"
        "• Categoria: 'era Alimentação'\n"
        "• Descrição: 'o nome é Mercado'"
    )
    return state


def delete_budget_handler_node(state: AgentState) -> AgentState:
    """Nó de exclusão de orçamentos."""
    logger.info("Excluindo budgets")
    result = delete_budget_node(dict(state))
    return AgentState(**result)


def toggle_alerts_handler_node(state: AgentState) -> AgentState:
    """Nó de ativar/desativar alertas."""
    logger.info("Toggling alerts")
    result = toggle_alerts_node(dict(state))
    return AgentState(**result)


def wizard_handler_node(state: AgentState) -> AgentState:
    """Nó de wizard multi-turno para orçamentos, metas, etc."""
    logger.info("Executando wizard")
    result = wizard_node(dict(state))
    return AgentState(**result)


def chat_node(state: AgentState) -> AgentState:
    """Nó conversacional — responde com LLM usando histórico da conversa.

    Usado para:
    - Agradecimentos e conversa casual
    - Follow-ups sem contexto explícito ("E no mês passado?")
    - Correções contextuais ("Na verdade foi R$ 60")
    - Quando a intenção é CHAT, HELP ou UNKNOWN
    - Saudações com contexto
    """
    from datetime import datetime, UTC

    from langchain_core.messages import HumanMessage, SystemMessage

    from app.agents.persistence import get_conversation_history
    from app.services.llm_service import get_llm, timed_invoke

    phone_number = state.get("phone_number", "")
    message = state.get("message", "")
    intent = state.get("intent")

    # Se for HELP, tenta responder especificamente com LLM
    if intent == IntentType.HELP.value:
        from langchain_core.messages import HumanMessage, SystemMessage

        from app.agents.prompts.chat import HELP_SPECIFIC_PROMPT
        from app.services.llm_service import get_llm, timed_invoke

        llm = get_llm(temperature=0.3)
        if llm:
            prompt = HELP_SPECIFIC_PROMPT
            try:
                msgs = [SystemMessage(content=prompt), HumanMessage(content=message)]
                r, _ = timed_invoke(llm, msgs, operation="help_response")
                state["response"] = r.content[:1000]
                logger.info(
                    "[chat_node] HELP específico gerado em resposta a: %s",
                    redact_message_for_log(message, 50),
                )
                return state
            except Exception as e:
                logger.warning(f"[chat_node] HELP via LLM falhou: {e}")
        # Fallback: menu completo
        from app.agents import responses as resp

        state["response"] = resp.help_menu()
        return state

    if intent == IntentType.INTRODUCE.value:
        state["response"] = "Prazer em conhecer você! Como posso ajudar hoje?"
        return state

    # Tenta usar LLM com histórico
    llm = get_llm(temperature=0.7)
    history = get_conversation_history(phone_number, limit=6)

    if not llm:
        # Fallback sem LLM — respostas simples
        msg_lower = message.lower()

        # Saudação sem contexto
        greeting_words = [
            "oi",
            "ola",
            "hello",
            "hey",
            "eai",
            "salve",
            "bom dia",
            "boa tarde",
            "boa noite",
            "eae",
            "iai",
        ]
        if any(w in msg_lower for w in greeting_words):
            hour = datetime.now(UTC).hour
            if hour < 12:
                gt = "Bom dia"
            elif hour < 18:
                gt = "Boa tarde"
            else:
                gt = "Boa noite"
            state["response"] = (
                f"{gt}! Sou o BagCoin, seu assistente financeiro. Como posso ajudar?"
            )
            return state

        thanks_words = [
            "obrigado",
            "obrigada",
            "valeu",
            "brigado",
            "thanks",
            "show",
            "beleza",
            "top",
        ]
        if any(w in msg_lower for w in thanks_words):
            state["response"] = "Por nada! Se precisar de algo, é só chamar."
            return state

        if any(
            w in msg_lower for w in ["ok", "certo", "entendi", "tendi", "blz", "perfeito", "legal"]
        ):
            state["response"] = "Show! O que mais posso ajudar?"
            return state

        # Follow-up detection
        if msg_lower.startswith("e ") or msg_lower.startswith("e,"):
            state["response"] = (
                "Pode repetir a pergunta completa? Assim fica mais fácil de entender "
                "o que você quer consultar. Ex: 'Quanto gastei no mês passado?'"
            )
            return state

        # Correção contextual
        import re as regex

        if any(
            w in msg_lower for w in ["na verdade", "era na verdade", "corrigindo", "foi na verdade"]
        ):
            amount_match = regex.search(r"R?\$?\s*(\d+(?:[.,]\d{1,2})?)", message)
            if amount_match:
                state["response"] = (
                    "Entendi, vou ajustar! Qual transação quer corrigir? "
                    "Pode me dar mais detalhes (descrição, data)?"
                )
                return state

        # Para UNKNOWN e HELP, tenta responder algo útil
        if any(
            w in msg_lower
            for w in [
                "quem",
                "o que",
                "como voce",
                "que é",
                "que e",
                "sabe fazer",
                "pode fazer",
                "capacidade",
                "funcionalidade",
            ]
        ):
            from app.agents import responses as resp

            state["response"] = (
                "Sou o **BagCoin**, seu assistente financeiro! 💰\n\n"
                "Posso ajudar com:\n"
                "• **Registrar** gastos e receitas\n"
                "• **Consultar** seus dados financeiros\n"
                "• **Orçamentos** por categoria\n"
                "• **Metas** financeiras\n"
                "• **Exportação CSV** pelo Dashboard\n"
                "• **Importar** extratos bancários\n"
                "• **Dicas** de economia\n\n"
                "Manda **'ajuda'** pra ver exemplos de como usar cada função!"
            )
            return state

        state["response"] = (
            "Não entendi muito bem. Posso ajudar com:\n"
            "- Registrar gastos e receitas\n"
            "- Consultar seus dados\n"
            "- Exportar CSV pelo Dashboard\n"
            "- Criar orçamentos e metas\n\n"
            "Manda 'ajuda' para ver exemplos ou me faça uma pergunta!"
        )
        return state

    # Usa LLM — mesmo sem histórico ele consegue responder bem
    history = get_conversation_history(phone_number, limit=6)

    # Tem LLM — resposta inteligente
    from app.agents.prompts.chat import build_chat_prompt

    hour = datetime.now(UTC).hour
    if hour < 12:
        greeting = "Bom dia"
    elif hour < 18:
        greeting = "Boa tarde"
    else:
        greeting = "Boa noite"

    system_prompt = build_chat_prompt(greeting=greeting, history=history)

    try:
        messages = [SystemMessage(content=system_prompt), HumanMessage(content=message)]

        response, latency_ms = timed_invoke(llm, messages, operation="chat_node")
        state["response"] = response.content

        logger.info(f"[chat_node] Resposta gerada em {latency_ms:.0f}ms")

    except Exception as e:
        logger.error(f"[chat_node] Erro: {e}")
        state["response"] = (
            "Entendi! Se precisar registrar algo ou consultar dados, pode me falar que eu ajudo."
        )

    return state


def legacy_smart_query_node(state: AgentState) -> AgentState:
    """Consulta inteligente — text-to-SQL ou LLM com dados do usuario.

    Combina process_query (text-to-SQL) com consulta LLM contextual.
    Se o text-to-SQL falhar, o LLM responde com o historico da conversa.
    """
    from app.agents.persistence import (
        get_conversation_history,
        get_or_create_user,
        get_user_transactions,
    )
    from app.db.session import sync_session_maker
    from app.services.budget_service import get_budgets, get_goals

    phone_number = state.get("phone_number", "")
    message = state.get("message", "")
    msg_norm = _msg_norm(message)

    # 1. Tenta text-to-SQL primeiro (precisao)
    if not _smart_query_needs_budget_goal_context(msg_norm):
        result = process_query(dict(state))
        if result.get("query_result") and result["query_result"].get("summary"):
            result["query_result"]["type"] = "sql"
            return AgentState(**result)

    # 2. Fallback: dados reais do usuario, com resposta deterministica quando inclui metas/orcamentos.
    db = sync_session_maker()
    try:
        get_or_create_user(phone_number, db)
        recent = get_user_transactions(phone_number, limit=10) or []
        budgets = get_budgets(phone_number) or []
        goals = get_goals(phone_number) or []
        history = get_conversation_history(phone_number, limit=4) or ""
    finally:
        db.close()

    if _smart_query_needs_budget_goal_context(msg_norm):
        state["response"] = _build_financial_snapshot_response(message, recent, budgets, goals)
        return state

    llm = get_llm(temperature=0.3)
    if not llm:
        state["response"] = "Não consegui consultar seus dados agora. Tente novamente!"
        return state

    # Formata dados para o prompt
    tx_lines = []
    for tx in recent[:10]:
        tx_type = _transaction_type_label(tx)
        tx_lines.append(f"- {tx_type}: {_format_recent_transaction_for_prompt(tx)}")
    tx_context = "\n".join(tx_lines) if tx_lines else "(sem transacoes)"

    system_prompt = f"""Voce e o BagCoin, assistente financeiro. Responda consultas com base nos DADOS REAIS do usuario.

DADOS DO USUARIO:
Ultimas transacoes:
{tx_context}

Historico da conversa:
{history if history else '(primeira mensagem)'}

REGRAS:
- Responda APENAS com base nos dados acima. Nao invente numeros.
- Se perguntarem algo que nao esta nos dados, diga que nao tem essa informacao.
- Seja breve e direto (maximo 3 paragrafos para WhatsApp).
- Formate valores como R$ X.XXX,XX.
- Se for pergunta sobre orcamentos/metas e nao tem dados, oriente como criar."""

    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        msgs = [SystemMessage(content=system_prompt), HumanMessage(content=message)]
        r, latency = timed_invoke(llm, msgs, operation="smart_query")
        state["response"] = r.content[:800]
        logger.info(f"[smart_query] LLM query em {latency:.0f}ms")
    except Exception as e:
        logger.error(f"[smart_query] Erro: {e}")
        state["response"] = "Ops, não consegui consultar. Tente de novo!"

    return state


def legacy_smart_manage_node(state: AgentState) -> AgentState:
    """Gerencia unificada — LLM decide qual acao tomar (criar/editar/excluir).

    Substitui o roteamento manual para budget, goal, transaction, category.
    O LLM analisa a mensagem, decide a acao e extrai os parametros.
    """
    phone_number = state.get("phone_number", "")
    message = state.get("message", "")
    msg_norm = _msg_norm(message)

    if _is_account_or_card_request(msg_norm):
        state["response"] = (
            "Por enquanto eu não crio contas, saldos ou cartões pelo chat. "
            "Posso criar um orçamento por categoria, por exemplo: "
            "'criar orçamento de R$ 500 para Supermercado'."
        )
        return state

    # 1. Fast-path: comandos explicitos com keywords claras
    # Categoria — mantido deterministico pois e simples
    if any(w in msg_norm for w in ["criar categoria", "nova categoria", "adicionar categoria"]):
        return create_category_handler_node(state)
    if any(w in msg_norm for w in ["excluir categoria", "apagar categoria", "remover categoria"]):
        return delete_category_handler_node(state)
    if any(w in msg_norm for w in ["minhas categorias", "quais categorias", "listar categorias"]):
        return list_categories_handler_node(state)
    if any(w in msg_norm for w in ["renomear categoria", "mudar nome da categoria"]):
        return update_category_handler_node(state)

    # 2. Wizard — se tem estado ativo, continua
    from app.agents.wizard import _load_wizard_state

    wizard = _load_wizard_state(phone_number)
    if wizard and wizard.get("status") in ["collecting", "confirming"]:
        return wizard_handler_node(state)

    # 3. LLM decide a acao e extrai parametros
    llm = get_llm(temperature=0.1)
    if not llm:
        state["response"] = (
            "O que voce quer gerenciar? 🤔\n"
            "• Orcamento: 'criar orcamento de R$ 500 para lazer'\n"
            "• Meta: 'quero guardar R$ 2000 para viagem'\n"
            "• Transacao: 'excluir gasto de ontem' ou 'mudar valor do mercado'\n"
            "• Categoria: 'criar categoria academia'"
        )
        return state

    from app.agents.persistence import (
        get_or_create_user,
        get_user_transactions,
    )

    db = sync_session_maker()
    try:
        user = get_or_create_user(phone_number, db)
        recent_tx = get_user_transactions(phone_number, limit=5) or []
    finally:
        db.close()

    tx_context = ""
    if recent_tx:
        tx_context = "Transacoes recentes:\n" + "\n".join(
            _format_recent_transaction_for_prompt(tx)
            for tx in recent_tx
        )

    system_prompt = f"""Voce e o gerenciador financeiro do BagCoin. Analise a mensagem e decida a acao.

Acoes possiveis:
- create_budget: criar novo orcamento por categoria. Extraia: name, amount_limit, period (monthly/weekly/yearly)
- create_goal: criar nova meta. Extraia: name, target_amount, deadline (opcional)
- contribute_goal: adicionar valor a meta existente. Extraia: goal_name, amount
- delete_budget: excluir orcamento. Extraia: budget_name
- delete_goal: excluir meta. Extraia: goal_name
- update_budget: atualizar orcamento. Extraia: budget_name, new_limit
- update_goal: atualizar meta. Extraia: goal_name, new_target
- delete_transaction: excluir transacao. Extraia: description (nome/descricao da transacao)
- update_transaction: corrigir transacao. Extraia: description, new_amount, new_category
- toggle_alerts: ativar/desativar alertas
- help: usuario nao especificou o que quer gerenciar

Regras:
- Nao crie contas, saldos, bancos ou cartoes de credito pelo chat.
- Se o usuario pedir conta/saldo/cartao, use action=help e explique que so pode criar orcamento por categoria.
- Orcamentos devem ser sempre por categoria.

{tx_context}

Responda APENAS JSON:
{{"action": "create_budget", "params": {{"name": "Lazer", "amount_limit": 500, "period": "monthly"}}, "message": "Vou criar o orcamento!"}}"""

    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from langchain_core.output_parsers import JsonOutputParser

        msgs = [SystemMessage(content=system_prompt), HumanMessage(content=message)]
        r, latency = timed_invoke(llm, msgs, operation="smart_manage")
        result = JsonOutputParser().parse(r.content)

        action = result.get("action", "help")
        params = result.get("params", {})
        user_msg = result.get("message", "")

        logger.info(f"[smart_manage] LLM action={action} em {latency:.0f}ms")

        # Roteia para o handler especifico
        if action == "create_budget":
            state["extracted_data"] = params
            return budget_node(state)
        elif action == "create_goal":
            state["extracted_data"] = params
            return goal_node(state)
        elif action == "delete_budget":
            state["extracted_data"] = {"name": params.get("budget_name", "")}
            return delete_budget_handler_node(state)
        elif action == "delete_goal":
            state["extracted_data"] = {"title": params.get("goal_name", "")}
            return delete_goal_handler_node(state)
        elif action == "update_budget":
            state["extracted_data"] = {"name": params.get("budget_name", ""), "total_limit": params.get("new_limit", 0)}
            return update_budget_handler_node(state)
        elif action == "contribute_goal":
            state["extracted_data"] = {"title": params.get("goal_name", ""), "amount": params.get("amount", 0)}
            return contribute_goal_handler_node(state)
        elif action == "delete_transaction":
            state["extracted_data"] = {"description": params.get("description", "")}
            return delete_transaction_handler_node(state)
        elif action == "update_transaction":
            state["extracted_data"] = {
                "description": params.get("description", ""),
                "amount": params.get("new_amount"),
                "category_name": params.get("new_category"),
            }
            return update_transaction_handler_node(state)
        elif action == "toggle_alerts":
            return toggle_alerts_handler_node(state)
        else:
            # help — usuario nao especificou
            state["response"] = (
                "O que voce quer gerenciar? 🤔\n\n"
                "📊 Orcamentos:\n"
                "• 'criar orcamento de R$ 500 para lazer'\n"
                "• 'mudar limite do orcamento alimentacao para 800'\n"
                "• 'excluir orcamento transporte'\n\n"
                "🎯 Metas:\n"
                "• 'quero guardar R$ 2000 para viagem'\n"
                "• 'guardei R$ 300 na meta viagem'\n\n"
                "💳 Transacoes:\n"
                "• 'excluir gasto do mercado de ontem'\n"
                "• 'corrigir valor do uber para 15'\n\n"
                "🏷 Categorias:\n"
                "• 'criar categoria academia'\n"
                "• 'renomear categoria mercado para supermercado'"
            )
    except Exception as e:
        logger.error(f"[smart_manage] LLM error: {e}")
        state["response"] = (
            "Me explica melhor o que voce quer fazer? 😊\n"
            "Quer criar, editar ou excluir algo?"
        )

    return state


def _tool_history(phone_number: str, limit: int = 6) -> str:
    from app.services.agent_memory_service import build_agent_context_text

    return build_agent_context_text(phone_number, message_limit=limit) or ""


def register_agent_node(state: AgentState) -> AgentState:
    """Tool-based transaction registration agent with confirmation-first behavior."""
    if not settings.USE_TOOL_AGENTS:
        return extract_data_node(state)

    from app.agents.tool_agent import run_tool_agent
    from app.agents.tools import create_financial_tools

    phone_number = state.get("phone_number", "")
    message = state.get("message", "")
    llm = get_llm(temperature=0.1)
    if not llm:
        state["response"] = (
            "Nao consegui interpretar isso agora. Pode me dizer valor, tipo e descricao? "
            "Ex: 'gastei R$ 80 no mercado'."
        )
        return state

    system_prompt = """Voce e o registrador financeiro do BagCoin.

Objetivo: entender mensagens naturais do usuario e preparar uma transacao para confirmacao.

Regras:
- Use prepare_register_transaction quando entender valor, tipo e descricao.
- NUNCA salve direto; a tool prepara a confirmacao.
- Se faltar valor, tipo (gasto/receita) ou descricao, pergunte apenas o campo faltante.
- Categoria pode ser inferida de forma razoavel; se estiver inseguro, use Outros.
- Use transaction_type=EXPENSE para gastos e INCOME para receitas.
- Se o usuario disser que e recorrente, mensal, semanal, anual, assinatura, salario fixo ou "todo dia X", chame a tool com is_recurring=true.
- Para recorrencia mensal em "todo dia X", preencha recurrence_day=X e recurrence_frequency=monthly.
- Depois que a tool retornar a confirmacao, responda preservando os dados preparados e peca confirmacao; nao diga que salvou.
- Responda em portugues, breve e adequado para WhatsApp."""

    try:
        state["response"] = run_tool_agent(
            llm=llm,
            tools=create_financial_tools(phone_number, state.get("context") or {}),
            system_prompt=system_prompt,
            user_message=message,
            history=_tool_history(phone_number, limit=4),
            max_iterations=3,
        )
    except Exception as exc:
        logger.warning("[register_agent] tool flow failed: %s", exc)
        state["response"] = (
            "Nao consegui preparar esse registro com seguranca agora. "
            "Pode tentar de novo com valor, descricao e se foi gasto ou receita?"
        )
    return state


def smart_query_tool_node(state: AgentState) -> AgentState:
    """Tool-based query agent for financial questions."""
    from app.agents.tool_agent import run_tool_agent
    from app.agents.tools import create_query_tools

    phone_number = state.get("phone_number", "")
    message = state.get("message", "")
    llm = get_llm(temperature=0.2)
    if not llm:
        return legacy_smart_query_node(state)

    system_prompt = """Voce e o consultor financeiro do BagCoin.

Use as tools para consultar dados reais do usuario antes de responder.
Nao invente valores. Se a tool nao trouxer a informacao, diga isso.
Responda em portugues, curto e claro para WhatsApp."""

    try:
        state["response"] = run_tool_agent(
            llm=llm,
            tools=create_query_tools(phone_number),
            system_prompt=system_prompt,
            user_message=message,
            history=_tool_history(phone_number, limit=4),
            max_iterations=3,
        )
    except Exception as exc:
        logger.warning("[smart_query_tool] falling back to legacy query: %s", exc)
        return legacy_smart_query_node(state)
    return state


def smart_manage_tool_node(state: AgentState) -> AgentState:
    """Tool-based management agent for budgets, goals, categories and edits."""
    from app.agents.tool_agent import run_tool_agent
    from app.agents.tools import (
        create_budget_tools,
        create_category_tools,
        create_financial_tools,
        create_goal_tools,
    )

    phone_number = state.get("phone_number", "")
    message = state.get("message", "")
    msg_norm = _msg_norm(message)

    if _is_account_or_card_request(msg_norm):
        state["response"] = (
            "Por enquanto eu não crio contas, saldos ou cartões pelo chat. "
            "Posso criar um orçamento por categoria, por exemplo: "
            "'criar orçamento de R$ 500 para Supermercado'."
        )
        return state

    from app.agents.wizard import _load_wizard_state

    wizard = _load_wizard_state(phone_number)
    if wizard and wizard.get("status") in ["collecting", "confirming"]:
        return wizard_handler_node(state)

    if _is_budget_create_request(msg_norm):
        budget_params = _extract_budget_request(message)
        if budget_params:
            state["response"] = save_pending_action(
                phone_number,
                action="create_budget",
                params=budget_params,
                summary=resp.budget_confirmation(
                    budget_params["name"],
                    float(budget_params["total_limit"]),
                    "monthly",
                ),
                channel=str((state.get("context") or {}).get("channel") or "whatsapp"),
            )
            return state
        wizard_state = dict(state)
        wizard_state["intent"] = IntentType.CREATE_BUDGET.value
        return wizard_handler_node(AgentState(**wizard_state))

    llm = get_llm(temperature=0.1)
    if not llm:
        state["response"] = (
            "Nao consegui gerenciar isso com seguranca agora. "
            "Pode tentar novamente em instantes?"
        )
        return state

    context = state.get("context") or {}
    tools = [
        *create_budget_tools(phone_number, context),
        *create_goal_tools(phone_number, context),
        *create_financial_tools(phone_number, context),
        *create_category_tools(phone_number, context),
    ]
    system_prompt = """Voce e o gerenciador financeiro do BagCoin.

Objetivo: interpretar o que o usuario quer gerenciar e chamar a tool correta.

Regras:
- Use tools para orcamentos, metas, categorias, correcoes e exclusoes.
- Toda criacao, edicao ou exclusao deve ser preparada para confirmacao pela tool.
- Metas tambem devem ser sempre preparadas pela tool; nunca responda como se a meta ja tivesse sido salva antes da confirmacao.
- Orcamento precisa apenas de categoria e valor. Nunca peca descricao para orcamento.
- Se o usuario disser so "criar orcamento", peca categoria e valor em uma frase.
- Nao crie contas bancarias, saldos ou cartoes de credito.
- Orcamentos sao sempre por categoria, mensais, a cada 30 dias.
- Para consultas simples de categorias/metas/orcamentos, pode listar direto.
- Quando uma tool retornar dados reais, nao invente estado diferente do resultado da tool.
- Responda em portugues, breve e natural para WhatsApp."""

    try:
        state["response"] = run_tool_agent(
            llm=llm,
            tools=tools,
            system_prompt=system_prompt,
            user_message=message,
            history=_tool_history(phone_number, limit=6),
            max_iterations=4,
        )
    except Exception as exc:
        logger.warning("[smart_manage_tool] tool flow failed: %s", exc)
        state["response"] = (
            "Nao consegui preparar essa acao com seguranca agora. "
            "Pode tentar novamente com mais detalhes?"
        )
    return state


def smart_query_node(state: AgentState) -> AgentState:
    if settings.USE_TOOL_AGENTS:
        return smart_query_tool_node(state)
    return legacy_smart_query_node(state)


def smart_manage_node(state: AgentState) -> AgentState:
    if settings.USE_TOOL_AGENTS:
        return smart_manage_tool_node(state)
    return legacy_smart_manage_node(state)


def build_response_node(state: AgentState) -> AgentState:
    """Nó de construção da resposta final."""
    from app.agents.persistence import get_or_create_user
    from app.db.session import sync_session_maker

    intent = state.get("intent")
    error = state.get("error")
    message = state.get("message", "")
    phone_number = state.get("phone_number", "")

    if message.startswith("[") and message.endswith("]"):
        state["response"] = message[1:-1]
        return state

    if state.get("response"):
        return state

    if error:
        state["response"] = resp.error_message(error)
        return state

    if intent == IntentType.REGISTER_EXPENSE.value or intent == IntentType.REGISTER_INCOME.value:
        extracted = state.get("extracted_data", {})
        tx_type = extracted.get("type", "EXPENSE")
        amount = extracted.get("amount", 0)
        category = state.get("category_name", extracted.get("category", "Outros"))
        desc = extracted.get("description", "")
        tx_date = state.get("transaction_date") or extracted.get("date") or extracted.get("transaction_date")

        state["response"] = resp.transaction_registered(tx_type, amount, category, desc, tx_date)

        alerts = state.get("alerts", [])
        if alerts:
            alert_texts = [a["message"] for a in alerts]
            state["response"] += "\n\n" + "\n".join(alert_texts)

        if tx_type == "INCOME":
            db = sync_session_maker()
            try:
                user = get_or_create_user(phone_number, db)
                from app.services.budget_service import get_goals

                goals = get_goals(phone_number)
                active_goals = [g for g in goals if g.get("status") == "active"]
                if active_goals:
                    goal_names = ", ".join([g["title"] for g in active_goals[:3]])
                    state["response"] += (
                        f"\n\nQuer direcionar parte para alguma meta? Você tem: {goal_names}"
                    )
            except Exception:
                pass
            finally:
                db.close()

    elif intent == IntentType.QUERY_DATA.value:
        query_result = state.get("query_result", {})
        if query_result and query_result.get("summary"):
            state["response"] = query_result["summary"]
        else:
            state["response"] = "Não encontrei dados para sua consulta."

    elif intent == IntentType.GENERATE_REPORT.value:
        summary = state.get("report_summary", "Relatório gerado com sucesso!")
        state["response"] = summary

    elif intent == IntentType.GREETING.value:
        db = sync_session_maker()
        try:
            user = get_or_create_user(phone_number, db)
            name = user.name if hasattr(user, "name") and user.name else None
        except Exception:
            name = None
        finally:
            db.close()
        hour = datetime.now(UTC).hour
        if hour < 12:
            greeting_time = "Bom dia"
        elif hour < 18:
            greeting_time = "Boa tarde"
        else:
            greeting_time = "Boa noite"
        state["response"] = resp.greeting(name=name, greeting_time=greeting_time)

    elif intent == IntentType.INTRODUCE.value:
        pass

    elif intent == IntentType.HELP.value:
        state["response"] = resp.help_menu()

    elif intent == IntentType.CREATE_BUDGET.value:
        if not state.get("response"):
            state["response"] = (
                "Para criar um orçamento, me diga algo como:\n"
                "• Orçamento de R$ 3000 para alimentação\n"
                "• Limite de R$ 800 para transporte"
            )

    elif intent == IntentType.CREATE_GOAL.value:
        if not state.get("response"):
            state["response"] = (
                "Para criar uma meta, me diga algo como:\n"
                "• Quero guardar R$ 5000 para viagem\n"
                "• Meta de reserva de emergência: R$ 10000"
            )

    elif intent == IntentType.IMPORT_STATEMENT.value:
        if state.get("import_summary"):
            state["response"] = state["import_summary"]
        else:
            state["response"] = (
                "Para importar seu extrato, envie o arquivo diretamente aqui:\n"
                "• PDF do banco\n"
                "• CSV (Excel)\n"
                "• Arquivo OFX\n\n"
                "Suporto extratos do Nubank, Itaú, Bradesco, Caixa e outros.\n"
                "Assim que enviar, mostro uma prévia e peço confirmação antes de importar."
            )

    elif state.get("import_summary"):
        state["response"] = state["import_summary"]

    else:
        # Fallback final — tenta usar LLM para responder
        from langchain_core.messages import HumanMessage, SystemMessage

        from app.services.llm_service import get_llm, timed_invoke

        llm = get_llm(temperature=0.7)
        if llm:
            try:
                msgs = [
                    SystemMessage(
                        content="Você é o BagCoin, assistente financeiro. Responda de forma breve e útil."
                    ),
                    HumanMessage(content=message),
                ]
                r, _ = timed_invoke(llm, msgs, operation="build_response")
                response_text = r.content[:500]

                # Filter: detect LLM-generated error/generic responses
                _bad_llm_patterns = [
                    "sorry, i couldn't", "i couldn't process",
                    "i'm sorry", "i am sorry", "sorry, i can't",
                    "i cannot", "i'm unable", "i am unable",
                    "as an ai", "as a language model",
                ]
                if any(p in response_text.lower() for p in _bad_llm_patterns):
                    logger.warning(
                        f"[build_response] LLM returned generic error: {response_text[:100]}"
                    )
                    state["response"] = resp.unknown_intent()
                else:
                    state["response"] = response_text
            except Exception:
                state["response"] = resp.unknown_intent()
        else:
            state["response"] = resp.unknown_intent()

    return state


def finalize_response_node(state: AgentState) -> AgentState:
    """Final response step: optional humanize, then persist final history once."""
    result = dict(state)
    response = result.get("response") or ""
    if should_humanize(result):
        result["response"] = humanize_safely(response, result)

    audio_text = (result.get("context") or {}).get("audio_transcription")
    if audio_text and settings.ECHO_AUDIO_TRANSCRIPTION and not result.get("error"):
        result["response"] = f'Ouvi: "{audio_text}". {result.get("response", "")}'

    _save_history(
        result.get("phone_number", ""),
        result.get("message", ""),
        result.get("response", ""),
    )
    return AgentState(**result)


def _save_history(phone_number: str, user_msg: str, bot_msg: str):
    """Salva par de mensagens no histórico."""
    try:
        save_message_to_history(phone_number, "user", user_msg)
        save_message_to_history(phone_number, "bot", bot_msg)
    except Exception:
        pass


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
    if settings.USE_TOOL_AGENTS and has_pending_confirmation_message(
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
    if settings.USE_TOOL_AGENTS and original_format in {"document", "image"}:
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
        if settings.USE_TOOL_AGENTS:
            return "register_agent"
        return "extract_data"

    if macro == "query":
        return "smart_query"  # novo: query com contexto

    if macro == "manage":
        return "smart_manage"  # novo: manage com LLM unificado

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
        IntentType.REGISTER_EXPENSE.value: "register_agent" if settings.USE_TOOL_AGENTS else "extract_data",
        IntentType.REGISTER_INCOME.value: "register_agent" if settings.USE_TOOL_AGENTS else "extract_data",
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
    return routing_map.get(intent, "chat")


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
    workflow.add_node("process_query", process_query_node)
    workflow.add_node("generate_report", generate_report_node)
    workflow.add_node("generate_recommendations", generate_recommendations_node)
    workflow.add_node("deep_research", deep_research_node)
    workflow.add_node("import_statement", import_statement_node)
    workflow.add_node("create_budget", budget_node)
    workflow.add_node("create_goal", goal_node)
    workflow.add_node("query_budgets", budgets_query_node)
    workflow.add_node("delete_budget", delete_budget_handler_node)
    workflow.add_node("update_budget", update_budget_handler_node)
    workflow.add_node("contribute_goal", contribute_goal_handler_node)
    workflow.add_node("delete_goal", delete_goal_handler_node)
    workflow.add_node("update_goal", update_goal_handler_node)
    workflow.add_node("delete_transaction", delete_transaction_handler_node)
    workflow.add_node("update_transaction", update_transaction_handler_node)
    workflow.add_node("introduce", intro_handler_node)
    workflow.add_node("correction", correction_handler_node)
    workflow.add_node("toggle_alerts", toggle_alerts_handler_node)
    workflow.add_node("wizard", wizard_handler_node)
    workflow.add_node("smart_query", smart_query_node)
    workflow.add_node("smart_manage", smart_manage_node)
    workflow.add_node("chat", chat_node)
    workflow.add_node("create_category", create_category_handler_node)
    workflow.add_node("delete_category", delete_category_handler_node)
    workflow.add_node("list_categories", list_categories_handler_node)
    workflow.add_node("update_category", update_category_handler_node)
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
            "process_query": "process_query",
            "generate_report": "generate_report",
            "generate_recommendations": "generate_recommendations",
            "deep_research": "deep_research",
            "create_budget": "create_budget",
            "create_goal": "create_goal",
            "query_budgets": "query_budgets",
            "delete_budget": "delete_budget",
            "update_budget": "update_budget",
            "contribute_goal": "contribute_goal",
            "delete_goal": "delete_goal",
            "update_goal": "update_goal",
            "delete_transaction": "delete_transaction",
            "update_transaction": "update_transaction",
            "introduce": "introduce",
            "correction": "correction",
            "toggle_alerts": "toggle_alerts",
            "wizard": "wizard",
            "chat": "chat",
            "create_category": "create_category",
            "delete_category": "delete_category",
            "list_categories": "list_categories",
            "update_category": "update_category",
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
    workflow.add_edge("process_query", "build_response")
    workflow.add_edge("generate_report", "build_response")
    workflow.add_edge("generate_recommendations", "build_response")
    workflow.add_edge("deep_research", "build_response")
    workflow.add_edge("import_statement", "build_response")
    workflow.add_edge("create_budget", "build_response")
    workflow.add_edge("create_goal", "build_response")
    workflow.add_edge("query_budgets", "build_response")
    workflow.add_edge("delete_budget", "build_response")
    workflow.add_edge("update_budget", "build_response")
    workflow.add_edge("contribute_goal", "build_response")
    workflow.add_edge("delete_goal", "build_response")
    workflow.add_edge("update_goal", "build_response")
    workflow.add_edge("delete_transaction", "build_response")
    workflow.add_edge("update_transaction", "build_response")
    workflow.add_edge("introduce", "build_response")
    workflow.add_edge("correction", "build_response")
    workflow.add_edge("toggle_alerts", "build_response")
    workflow.add_edge("wizard", "build_response")
    workflow.add_edge("chat", "build_response")
    workflow.add_edge("smart_query", "build_response")
    workflow.add_edge("smart_manage", "build_response")
    workflow.add_edge("create_category", "build_response")
    workflow.add_edge("delete_category", "build_response")
    workflow.add_edge("list_categories", "build_response")
    workflow.add_edge("update_category", "build_response")
    workflow.add_edge("build_response", "finalize_response")
    workflow.add_edge("finalize_response", END)

    return workflow.compile()


# Instância global do orquestrador
orchestrator = create_orchestrator()
