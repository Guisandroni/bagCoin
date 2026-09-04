"""Chat, wizard, response-building, and finalization node handlers."""

import logging
from datetime import UTC, datetime

from app.agents import responses as resp
from app.agents.builders import _BUILDERS, build_fallback_response
from app.agents.humanize import humanize_safely, should_humanize
from app.agents.persistence import save_message_to_history
from app.agents.state import AgentState
from app.agents.wizard import wizard_node
from app.core.config import settings
from app.schemas.enums import IntentType

logger = logging.getLogger(__name__)


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
    from langchain_core.messages import HumanMessage, SystemMessage

    from app.agents.persistence import get_conversation_history
    from app.services.integration_service import redact_message_for_log
    from app.services.llm_service import get_llm, timed_invoke

    phone_number = state.get("phone_number", "")
    message = state.get("message", "")
    intent = state.get("intent")

    # Se for HELP, tenta responder especificamente com LLM
    if intent == IntentType.HELP.value:
        from app.agents.prompts.chat import HELP_SPECIFIC_PROMPT

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


def build_response_node(state: AgentState) -> AgentState:
    """Nó de construção da resposta final — dispatcher para builders por intent."""
    message = state.get("message", "")
    intent = state.get("intent")
    error = state.get("error")

    # Edge-case: error bracket message
    if message.startswith("[") and message.endswith("]"):
        state["response"] = message[1:-1]
        return state

    # Already has a response — keep it
    if state.get("response"):
        return state

    # Error takes priority
    if error:
        state["response"] = resp.error_message(error)
        return state

    # import_summary wins for intents without a dedicated builder
    # (matches the old else-chain: import_summary beat the LLM fallback).
    if state.get("import_summary") and intent not in _BUILDERS:
        state["response"] = state["import_summary"]
        return state

    # Dispatch to intent-specific builder, or fallback
    builder = _BUILDERS.get(intent, build_fallback_response)
    state["response"] = builder(state)
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
