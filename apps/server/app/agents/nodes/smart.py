"""Smart query/manage node handlers (tool-agent + legacy paths)."""

import logging
import re
from datetime import UTC, datetime
from typing import Any

from app.agents import responses as resp
from app.agents.nodes.chat import wizard_handler_node
from app.agents.pending_actions import save_pending_action
from app.agents.routing import (
    _is_account_or_card_request,
    _is_budget_create_request,
    _msg_norm,
)
from app.agents.state import AgentState
from app.agents.text_to_sql import process_query
from app.core.config import settings
from app.db.session import sync_session_maker
from app.schemas.enums import IntentType
from app.services.llm_service import get_llm, timed_invoke

logger = logging.getLogger(__name__)


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
    # Categorias sao gerenciadas pelo caminho tool-agent (ADR-0001).

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

        # Budget/goal são tratados pelo caminho tool-agent (ADR-0001).
        # O legacy path só mantém transaction/category/toggle_alerts.
        if action in {
            "create_budget",
            "create_goal",
            "delete_budget",
            "delete_goal",
            "update_budget",
            "contribute_goal",
        }:
            state["response"] = (
                "Essa ação é gerenciada pelo assistente moderno. "
                "Me diga o que quer fazer e eu ajudo: criar orçamento, meta, "
                "ou ajustar transações."
            )
        elif action in {"delete_transaction", "update_transaction"}:
            state["response"] = (
                "Ajustes de transação são gerenciados pelo assistente moderno. "
                "Me diga o que quer corrigir e eu ajudo."
            )
        elif action == "toggle_alerts":
            state["response"] = (
                "Os alertas são gerenciados pelo assistente moderno. "
                "Pode me pedir para ativar ou desativar."
            )
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

    for deterministic_handler in (
        _prepare_budget_delete,
        _prepare_budget_update,
        _prepare_goal_delete,
        _prepare_goal_update,
    ):
        handled_state = deterministic_handler(state)
        if handled_state is not None:
            return handled_state

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


def _extract_money_amount(message: str) -> float | None:
    amount_match = re.search(
        r"(?:r\$?\s*)?(\d{1,3}(?:[.,]\d{3})*[.,]\d{1,2}|\d+(?:[.,]\d{1,2})?)",
        message,
        flags=re.IGNORECASE,
    )
    if not amount_match:
        return None
    try:
        return float(amount_match.group(1).replace(".", "").replace(",", "."))
    except ValueError:
        return None


def _strip_management_words(text: str, *, target: str) -> str:
    msg = _msg_norm(text)
    msg = re.sub(r"(?:r\$?\s*)?\d{1,3}(?:[.,]\d{3})*[.,]\d{1,2}|\d+(?:[.,]\d{1,2})?", " ", msg)
    words = [
        "quero",
        "queria",
        "pode",
        "por favor",
        "o",
        "a",
        "os",
        "as",
        "um",
        "uma",
        "de",
        "do",
        "da",
        "dos",
        "das",
        "para",
        "pra",
        "por",
        "em",
        "na",
        "no",
        "meu",
        "minha",
        "meus",
        "minhas",
        target,
        f"{target}s",
    ]
    action_words = [
        "excluir",
        "deletar",
        "apagar",
        "remover",
        "editar",
        "alterar",
        "atualizar",
        "mudar",
        "trocar",
        "aumentar",
        "diminuir",
        "novo",
        "nova",
        "limite",
        "valor",
        "reais",
        "real",
    ]
    pattern = r"\b(" + "|".join(re.escape(w) for w in words + action_words) + r")\b"
    msg = re.sub(pattern, " ", msg)
    return re.sub(r"\s+", " ", msg).strip(" .,!?\n\t")


def _prepare_budget_delete(state: AgentState) -> AgentState | None:
    msg_norm = _msg_norm(state.get("message", ""))
    if "orcamento" not in msg_norm or not any(w in msg_norm for w in ("excluir", "deletar", "apagar", "remover")):
        return None
    phone_number = state.get("phone_number", "")
    name = _strip_management_words(state.get("message", ""), target="orcamento")
    from app.core.financial_categories import resolve_default_category_name

    name = resolve_default_category_name(name) if name else ""
    if not name:
        from app.services.budget_service import get_budgets

        budgets = get_budgets(phone_number)
        state["response"] = (
            "Qual orçamento você quer excluir? " + ", ".join(b["name"] for b in budgets)
            if budgets
            else "Você não tem orçamentos para excluir."
        )
        return state
    state["response"] = save_pending_action(
        phone_number,
        action="delete_budget",
        params={"name": name},
        summary=f"Vou remover o orçamento {name}.",
        channel=str((state.get("context") or {}).get("channel") or "whatsapp"),
    )
    return state


def _prepare_budget_update(state: AgentState) -> AgentState | None:
    msg_norm = _msg_norm(state.get("message", ""))
    if "orcamento" not in msg_norm or not any(w in msg_norm for w in ("editar", "alterar", "atualizar", "mudar", "trocar", "aumentar", "diminuir")):
        return None
    phone_number = state.get("phone_number", "")
    amount = _extract_money_amount(state.get("message", ""))
    name = _strip_management_words(state.get("message", ""), target="orcamento")
    from app.agents.wizard import _save_wizard_state
    from app.core.financial_categories import resolve_default_category_name

    name = resolve_default_category_name(name) if name else ""
    if not name:
        from app.services.budget_service import get_budgets

        budgets = get_budgets(phone_number)
        if not budgets:
            state["response"] = "Você não tem orçamentos para atualizar."
            return state
        _save_wizard_state(
            phone_number,
            {
                "type": "update_budget",
                "status": "collecting",
                "collected": {},
                "missing": ["name", "total_limit"],
                "updated_at": datetime.now(UTC).isoformat(),
            },
        )
        state["response"] = "Qual orçamento você quer atualizar? " + ", ".join(
            b["name"] for b in budgets
        )
        return state
    if amount is None:
        _save_wizard_state(
            phone_number,
            {
                "type": "update_budget",
                "status": "collecting",
                "collected": {"name": name},
                "missing": ["total_limit"],
                "updated_at": datetime.now(UTC).isoformat(),
            },
        )
        state["response"] = f"Qual é o novo limite do orçamento {name}?"
        return state
    state["response"] = save_pending_action(
        phone_number,
        action="update_budget",
        params={"name": name, "total_limit": amount},
        summary=f"Vou atualizar o orçamento {name} para R$ {amount:,.2f}.",
        channel=str((state.get("context") or {}).get("channel") or "whatsapp"),
    )
    return state


def _prepare_goal_delete(state: AgentState) -> AgentState | None:
    msg_norm = _msg_norm(state.get("message", ""))
    if "meta" not in msg_norm or not any(w in msg_norm for w in ("excluir", "deletar", "apagar", "remover")):
        return None
    phone_number = state.get("phone_number", "")
    identifier = _strip_management_words(state.get("message", ""), target="meta")
    if not identifier:
        from app.services.budget_service import get_goals

        goals = get_goals(phone_number)
        state["response"] = (
            "Qual meta você quer excluir? " + ", ".join(g["title"] for g in goals)
            if goals
            else "Você não tem metas para excluir."
        )
        return state
    state["response"] = save_pending_action(
        phone_number,
        action="delete_goal",
        params={"goal_identifier": identifier},
        summary=resp.goal_delete_confirmation(identifier),
        channel=str((state.get("context") or {}).get("channel") or "whatsapp"),
    )
    return state


def _prepare_goal_update(state: AgentState) -> AgentState | None:
    msg_norm = _msg_norm(state.get("message", ""))
    if "meta" not in msg_norm or not any(w in msg_norm for w in ("editar", "alterar", "atualizar", "mudar", "trocar", "aumentar", "diminuir")):
        return None
    phone_number = state.get("phone_number", "")
    amount = _extract_money_amount(state.get("message", ""))
    identifier = _strip_management_words(state.get("message", ""), target="meta")
    if not identifier:
        from app.services.budget_service import get_goals

        goals = get_goals(phone_number)
        state["response"] = (
            "Qual meta você quer atualizar? " + ", ".join(g["title"] for g in goals)
            if goals
            else "Você não tem metas para atualizar."
        )
        return state
    if amount is None:
        state["response"] = f"O que você quer atualizar na meta {identifier}?"
        return state
    state["response"] = save_pending_action(
        phone_number,
        action="update_goal",
        params={"goal_identifier": identifier, "target_amount": amount},
        summary=resp.goal_update_confirmation(identifier, target_amount=amount),
        channel=str((state.get("context") or {}).get("channel") or "whatsapp"),
    )
    return state


