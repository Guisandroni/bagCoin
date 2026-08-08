"""Tool-agent node handler for Transação registration."""

import logging

from app.agents.nodes.tool_context import tool_history
from app.agents.state import AgentState

logger = logging.getLogger(__name__)


def register_agent_node(state: AgentState) -> AgentState:
    """Tool-based transaction registration agent with confirmation-first behavior."""
    from app.agents.tool_agent import run_tool_agent
    from app.agents.tools import create_financial_tools
    from app.services.llm_service import get_llm

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
            history=tool_history(phone_number, limit=4),
            max_iterations=3,
        )
    except Exception as exc:
        logger.warning("[register_agent] tool flow failed: %s", exc)
        state["response"] = (
            "Nao consegui preparar esse registro com seguranca agora. "
            "Pode tentar de novo com valor, descricao e se foi gasto ou receita?"
        )
    return state
