"""Wizard agent — multi-turn interactive data collection for BagCoin.

Handles interactive dialogues for creating budgets, goals, etc.
Uses sync_session_maker for database access.
"""

import json
import logging
import re
from datetime import datetime, UTC
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents import responses as resp
from app.agents.persistence import get_or_create_user
from app.db.models.phone_conversation import PhoneConversation
from app.db.session import sync_session_maker
from app.services.llm_service import get_llm, timed_invoke

logger = logging.getLogger(__name__)

# Schemas de cada wizard (campos obrigatórios)
WIZARD_SCHEMAS = {
    "create_budget": {
        "fields": ["name", "total_limit"],
        "defaults": {"period": "monthly", "budget_type": "category"},
        "labels": {
            "name": "categoria do orçamento",
            "total_limit": "valor (em R$)",
        },
        "examples": [
            "Alimentação, 800",
            "Supermercado 500",
        ],
    },
    "create_goal": {
        "fields": ["title", "target_amount"],
        "optional": ["deadline"],
        "defaults": {},
        "labels": {
            "title": "objetivo da meta",
            "target_amount": "valor total (em R$)",
            "deadline": "prazo (opcional, ex: 12/2026)",
        },
        "examples": ["viagem, 10000, 12/2026", "bike 1200", "emergência R$ 5000 até 06/2027"],
    },
    "update_budget": {
        "fields": ["name", "total_limit"],
        "defaults": {},
        "labels": {
            "name": "qual orçamento",
            "total_limit": "novo limite (em R$)",
        },
        "examples": ["Combustível, 200", "Supermercado 800"],
    },
    "update_goal": {
        "fields": ["goal_identifier", "amount"],
        "defaults": {},
        "labels": {
            "goal_identifier": "qual meta (nome ou número)",
            "amount": "quanto quer adicionar (em R$)",
        },
        "examples": ["bike, 200", "viagem 500", "meta 1 R$ 300"],
    },
    "contribute_goal": {
        "fields": ["goal_identifier", "amount"],
        "defaults": {},
        "labels": {
            "goal_identifier": "qual meta (nome ou número)",
            "amount": "quanto quer adicionar (em R$)",
        },
        "examples": ["viagem, 200", "bike 500", "reserva R$ 300"],
    },
}


def _get_conversation(phone_number: str) -> PhoneConversation | None:
    """Busca a conversa mais recente do usuário."""
    db = sync_session_maker()
    try:
        user = get_or_create_user(phone_number, db)
        conv = (
            db.query(PhoneConversation)
            .filter(PhoneConversation.user_id == user.id)
            .order_by(PhoneConversation.updated_at.desc())
            .first()
        )
        return conv
    finally:
        db.close()


def _save_wizard_state(phone_number: str, wizard_state: dict[str, Any]):
    """Salva estado do wizard na conversa."""
    db = sync_session_maker()
    try:
        user = get_or_create_user(phone_number, db)
        conv = (
            db.query(PhoneConversation)
            .filter(PhoneConversation.user_id == user.id)
            .order_by(PhoneConversation.updated_at.desc())
            .first()
        )

        if not conv:
            conv = PhoneConversation(user_id=user.id, channel="whatsapp")
            db.add(conv)

        from sqlalchemy.orm.attributes import flag_modified

        context = dict(conv.context_json or {})
        context["wizard"] = wizard_state
        conv.context_json = context
        flag_modified(conv, "context_json")
        conv.updated_at = datetime.now(UTC)
        db.commit()
        logger.info(f"Wizard state salvo para {phone_number}: {wizard_state.get('status')}")
    except Exception as e:
        logger.error(f"Erro ao salvar wizard state: {e}")
        db.rollback()
    finally:
        db.close()


def _load_wizard_state(phone_number: str) -> dict[str, Any] | None:
    """Carrega estado do wizard da conversa."""
    conv = _get_conversation(phone_number)
    if conv and conv.context_json:
        wizard = conv.context_json.get("wizard")
        if wizard:
            # Verifica timeout (10 minutos)
            last_update = wizard.get("updated_at")
            if last_update:
                try:
                    last = datetime.fromisoformat(last_update)
                    if (datetime.now(UTC) - last).total_seconds() > 600:
                        logger.info(f"Wizard expirado para {phone_number}")
                        return None
                except Exception:
                    pass
            return wizard
    return None


def _clear_wizard_state(phone_number: str):
    """Limpa estado do wizard."""
    db = sync_session_maker()
    try:
        user = get_or_create_user(phone_number, db)
        conv = (
            db.query(PhoneConversation)
            .filter(PhoneConversation.user_id == user.id)
            .order_by(PhoneConversation.updated_at.desc())
            .first()
        )

        if conv and conv.context_json:
            from sqlalchemy.orm.attributes import flag_modified

            context = dict(conv.context_json)
            context.pop("wizard", None)
            conv.context_json = context
            flag_modified(conv, "context_json")
            db.commit()
            logger.info(f"Wizard state limpo para {phone_number}")
    except Exception as e:
        logger.error(f"Erro ao limpar wizard state: {e}")
        db.rollback()
    finally:
        db.close()


def _is_wizard_intent(intent: str) -> bool:
    """Verifica se a intenção é gerenciada pelo wizard."""
    return intent in ["create_budget", "create_goal", "update_budget", "update_goal", "contribute_goal"]


def _parse_value(value_str: str) -> float | None:
    """Extrai valor numérico de uma string."""
    if not value_str:
        return None
    # Remove R$, espaços
    original = re.sub(r"R?\$?\s*", "", str(value_str))

    has_dot = "." in original
    has_comma = "," in original

    if has_dot and has_comma:
        # Ambos: último separador é decimal (ex: "1.500,50" → 1500.50)
        cleaned = original.replace(".", "").replace(",", ".")
    elif has_dot:
        # Só ponto. Heurística: se estiver a 3 chars do final com ≤5 chars
        # totais, é decimal (ex: "50.40", "3.40"). Caso contrário, milhar.
        dot_pos = original.rfind(".")
        if dot_pos == len(original) - 3 and len(original) <= 6:
            cleaned = original.replace(".", ".")  # mantém como decimal
        else:
            cleaned = original.replace(".", "")  # remove milhar
    elif has_comma:
        cleaned = original.replace(",", ".")
    else:
        cleaned = original

    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_deadline(date_str: str) -> str | None:
    """Parseia data no formato MM/YYYY ou DD/MM/YYYY."""
    if not date_str:
        return None
    # MM/YYYY
    m = re.match(r"(\d{1,2})/(\d{4})", str(date_str))
    if m:
        return f"01/{m.group(1)}/{m.group(2)}"
    # DD/MM/YYYY
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", str(date_str))
    if m:
        return f"{m.group(1)}/{m.group(2)}/{m.group(3)}"
    return None


def wizard_node(state: dict[str, Any]) -> dict[str, Any]:
    """Nó de wizard multi-turno com LLM.

    Gerencia diálogos para criar orçamentos, metas, etc.
    - Se dados completos na primeira mensagem: executa direto (single-turn)
    - Se dados parciais: confirma antes de executar
    - Se sem dados: entra em modo de coleta multi-turno
    """
    import time

    start_time = time.time()

    message = state.get("message", "")
    phone_number = state.get("phone_number", "")
    intent = state.get("intent", "")
    llm = get_llm(temperature=0.2)
    llm_init_ms = (time.time() - start_time) * 1000

    # 1. Verifica se há wizard em andamento
    wizard_state = _load_wizard_state(phone_number)

    if wizard_state:
        # Continua wizard existente
        wizard_type = wizard_state.get("type", "")
        logger.info(f"Wizard em andamento para {phone_number}: {wizard_type}")
    elif _is_wizard_intent(intent):
        # Inicia novo wizard
        if hasattr(intent, "value"):
            wizard_type = intent.value
        else:
            wizard_type = str(intent)
        if wizard_type not in WIZARD_SCHEMAS:
            wizard_type = "create_goal"  # fallback
        wizard_state = {
            "type": wizard_type,
            "status": "collecting",
            "collected": {},
            "missing": WIZARD_SCHEMAS[wizard_type]["fields"].copy(),
            "updated_at": datetime.now(UTC).isoformat(),
        }
        # Aplica defaults
        for field, default in WIZARD_SCHEMAS[wizard_type].get("defaults", {}).items():
            if field in wizard_state["missing"]:
                wizard_state["collected"][field] = default
                wizard_state["missing"].remove(field)
        logger.info(f"Novo wizard iniciado para {phone_number}: {wizard_type}")

        # Tenta extrair dados da mensagem inicial
        msg_has_data = bool(re.search(r"\d", message)) or any(
            w in message.lower() for w in ["r$", "reais", "para", "de", "até", "ate"]
        )
        if llm and msg_has_data:
            extracted = _extract_fields_with_llm(
                llm,
                message,
                wizard_type,
                wizard_state["missing"],
                WIZARD_SCHEMAS[wizard_type]["labels"],
            )
        else:
            extracted = _extract_fields_simple(message, wizard_type, wizard_state["missing"])

        # Mescla dados extraídos
        for field, value in extracted.items():
            if field in wizard_state["missing"] and value is not None:
                wizard_state["collected"][field] = value
                wizard_state["missing"].remove(field)

        # Se conseguiu TODOS os dados na primeira mensagem, executa direto
        if not wizard_state["missing"]:
            logger.info(
                f"Wizard {wizard_type}: todos os dados coletados na primeira mensagem. Executando direto."
            )
            return _handle_executing(state, wizard_state, phone_number)

        # Se conseguiu ALGUNS dados, vai para confirmação/coleta
        if wizard_state["collected"]:
            wizard_state["status"] = "collecting"
            _save_wizard_state(phone_number, wizard_state)
            return _handle_collecting(state, wizard_state, message, phone_number, llm)

        # Se não conseguiu nenhum dado, inicia coleta
        _save_wizard_state(phone_number, wizard_state)
        return _handle_collecting(state, wizard_state, message, phone_number, llm)
    else:
        # Não é wizard, passa direto
        return state

    # 2. Se estamos coletando dados, usa LLM para interpretar a mensagem
    if wizard_state["status"] == "collecting":
        result = _handle_collecting(state, wizard_state, message, phone_number, llm)
        total_ms = (time.time() - start_time) * 1000
        logger.info(
            f"[wizard_node] collecting total: {total_ms:.0f}ms (llm_init={llm_init_ms:.0f}ms)"
        )
        return result

    # 3. Se estamos confirmando, verifica resposta do usuário
    if wizard_state["status"] == "confirming":
        result = _handle_confirming(state, wizard_state, message, phone_number, llm)
        total_ms = (time.time() - start_time) * 1000
        logger.info(
            f"[wizard_node] confirming total: {total_ms:.0f}ms (llm_init={llm_init_ms:.0f}ms)"
        )
        return result

    # 4. Se estamos executando, executa a ação
    if wizard_state["status"] == "executing":
        result = _handle_executing(state, wizard_state, phone_number)
        total_ms = (time.time() - start_time) * 1000
        logger.info(
            f"[wizard_node] executing total: {total_ms:.0f}ms (llm_init={llm_init_ms:.0f}ms)"
        )
        return result

    total_ms = (time.time() - start_time) * 1000
    logger.info(f"[wizard_node] no-op total: {total_ms:.0f}ms (llm_init={llm_init_ms:.0f}ms)")
    return state


def _parse_option_choice(message: str, valid_keys: list[str]) -> str | None:
    """Extrai escolha de opção da mensagem do usuário.

    Aceita:
    - Dígito: "1", "2"
    - Palavras: "primeira", "segunda", "um", "dois", "opção 1", "opcao 2"
    - Frases com número: "quero a 1", "a primeira"

    Returns: a chave da opção (ex: "1") ou None se inválido.
    """
    msg = message.lower().strip()
    # Mapeamento de palavras para números
    word_to_num = {
        "um": "1", "uma": "1", "primeira": "1", "primeiro": "1",
        "dois": "2", "duas": "2", "segunda": "2", "segundo": "2",
        "três": "3", "tres": "3", "terceira": "3", "terceiro": "3",
    }
    # Extrai número da mensagem
    num_match = re.search(r"\b([123])\b", msg)
    if num_match:
        key = num_match.group(1)
        if key in valid_keys:
            return key
    # Tenta palavras
    for word, num in word_to_num.items():
        if word in msg.split() or f" {word} " in f" {msg} ":
            if num in valid_keys:
                return num
    return None


def _build_option_prompt(field: str, opt_labels: dict[str, str], is_retry: bool = False) -> str:
    """Constrói prompt de opções para um campo do wizard.

    Args:
        field: Nome do campo
        opt_labels: Dict com labels das opções (ex: {"1": "descrição da opção 1"})
        is_retry: Se True, inclui mensagem de erro de validação

    Returns: string formatada com as opções.
    """
    prefix = (
        "Não entendi sua resposta. Poderia confirmar qual opção?\n\n"
        if is_retry
        else "Que tipo de orçamento você quer criar?\n\n"
    )
    lines = [prefix]
    for key in sorted(opt_labels.keys(), key=int):
        emoji = ["1️⃣", "2️⃣", "3️⃣"][int(key) - 1]
        lines.append(f"{emoji} {opt_labels[key]}")
    lines.append("\nResponda 1 ou 2.")
    return "\n".join(lines)


def _handle_collecting(
    state: dict[str, Any], wizard: dict[str, Any], message: str, phone_number: str, llm: Any
) -> dict[str, Any]:
    """Processa mensagem do usuário durante fase de coleta."""
    wizard_type = wizard["type"]
    schema = WIZARD_SCHEMAS[wizard_type]
    fields = schema["fields"]
    labels = schema["labels"]
    examples = schema["examples"]
    options = schema.get("options", {})
    option_labels = schema.get("option_labels", {})
    valid_fields = set(fields)
    wizard["missing"] = [field for field in wizard.get("missing", []) if field in valid_fields]
    for field, default in schema.get("defaults", {}).items():
        wizard.setdefault("collected", {}).setdefault(field, default)

    # Verifica cancelamento em qualquer fase
    # Só cancela se a mensagem é EXPLICITAMENTE de cancelamento
    # (palavra isolada ou comando curto, não frases como "não sei")
    msg_lower = message.lower().strip()
    msg_words_token = msg_lower.split()
    cancel_words = ["cancelar", "cancela", "esquece", "desistir", "desisto", "para", "pare"]
    is_cancel = any(w in msg_words_token for w in cancel_words)

    # "não" só cancela se for palavra única ou "não quero"
    if not is_cancel:
        if msg_words_token == ["não"] or msg_words_token == ["nao"] or (len(msg_words_token) == 2 and msg_words_token[0] in ["não", "nao"] and msg_words_token[1] in ["quero", "obrigado", "valeu"]) or (len(msg_words_token) <= 2 and any(w in ["errado", "desiste"] for w in msg_words_token)):
            is_cancel = True

    if is_cancel:
        _clear_wizard_state(phone_number)
        state["response"] = (
            "Cancelado. Se quiser tentar de novo, é só mandar 'criar orçamento' ou 'criar meta'."
        )
        return state

    # Detecta se a mensagem é apenas o comando (ex: "criar orçamento") sem dados
    msg_words = message.lower().split()
    is_just_command = len(msg_words) <= 3 and any(
        w in message.lower() for w in ["criar", "crie", "novo", "nova", "quero"]
    )

    # Se é a primeira interação e não há dados reais (só defaults), apresenta o wizard
    has_real_data = any(
        field not in schema.get("defaults", {}) for field in wizard.get("collected", {}).keys()
    )
    if not has_real_data and is_just_command:
        # Primeira mensagem só com "criar orçamento" - explica o que precisa
        first_missing = wizard["missing"][0] if wizard["missing"] else None
        if first_missing and first_missing in option_labels:
            state["response"] = _build_option_prompt(first_missing, option_labels[first_missing])
            wizard["updated_at"] = datetime.now(UTC).isoformat()
            _save_wizard_state(phone_number, wizard)
            return state

        missing_labels = [labels[f] for f in wizard["missing"]]
        type_name = {
            "create_budget": "orçamento",
            "update_budget": "atualização de orçamento",
            "create_goal": "meta",
            "update_goal": "atualização de meta",
            "contribute_goal": "contribuição para meta",
        }.get(wizard_type, wizard_type.replace("_", " "))
        if wizard_type == "create_budget":
            state["response"] = (
                "Para criar um orçamento, me envie a categoria e o valor.\n\n"
                'Ex: "alimentação 4000" ou "orçamento 4000 alimentação".'
            )
            wizard["updated_at"] = datetime.now(UTC).isoformat()
            _save_wizard_state(phone_number, wizard)
            return state

        response = f"Vamos criar seu {type_name}!\n\nPreciso das seguintes informações:\n"
        for i, label in enumerate(missing_labels, 1):
            response += f"{i}. {label}\n"
        response += f"\nExemplos de como responder:\n- {examples[0]}\n"
        if len(examples) > 1:
            response += f"- {examples[1]}\n"

        state["response"] = response
        wizard["updated_at"] = datetime.now(UTC).isoformat()
        _save_wizard_state(phone_number, wizard)
        return state

    # ── VALIDAÇÃO DE OPÇÕES (só quando wizard já está em andamento) ──
    # Se o primeiro campo pendente tem opções, valida a resposta do usuário
    if wizard["missing"] and wizard["missing"][0] in options:
        field = wizard["missing"][0]
        field_options = options[field]
        field_opt_labels = option_labels.get(field, {})
        # Tenta extrair opção da mensagem
        selected = _parse_option_choice(message, list(field_options.keys()))
        if selected:
            wizard["collected"][field] = field_options[selected]
            wizard["missing"].remove(field)
            logger.info(f"Wizard {wizard_type}: opção '{field}' = {selected} → {field_options[selected]}")
            # Se ainda faltam campos, mostra próximo prompt (não extrai dados da mesma msg)
            if wizard["missing"]:
                first_missing = wizard["missing"][0]
                if first_missing in option_labels:
                    state["response"] = _build_option_prompt(first_missing, option_labels[first_missing])
                else:
                    collected_summary = _format_collected(wizard["collected"], labels)
                    response = ""
                    if collected_summary:
                        response += f"Já tenho:\n{collected_summary}\n\n"
                    missing_labels = [labels[f] for f in wizard["missing"]]
                    response += "Ainda preciso de:\n"
                    for label in missing_labels:
                        response += f"- {label}\n"
                    state["response"] = response
                wizard["updated_at"] = datetime.now(UTC).isoformat()
                _save_wizard_state(phone_number, wizard)
                return state
            # Todos os campos coletados
            wizard["status"] = "confirming"
            return _prompt_for_confirmation(state, wizard, phone_number)
        else:
            # Resposta inválida — re-prompt com a pergunta de opções
            state["response"] = _build_option_prompt(field, field_opt_labels, is_retry=True)
            wizard["updated_at"] = datetime.now(UTC).isoformat()
            _save_wizard_state(phone_number, wizard)
            return state

    # ── EXTRAÇÃO DE DADOS ──
    # Primeiro tenta parse simples (rápido, deterministico)
    extracted = _extract_fields_simple(message, wizard_type, wizard["missing"])

    # Mescla dados extraídos
    for field, value in extracted.items():
        if field in wizard["missing"] and value is not None:
            wizard["collected"][field] = value
            wizard["missing"].remove(field)
            logger.info(f"Wizard {wizard_type}: campo '{field}' = {value}")

    # Se ainda faltam campos e a mensagem tem dados complexos, tenta LLM
    if wizard["missing"] and llm:
        msg_has_data = bool(re.search(r"\d", message)) or any(
            w in message.lower() for w in ["r$", "reais", "para", "de", "até", "ate"]
        )
        if msg_has_data:
            llm_extracted = _extract_fields_with_llm(
                llm, message, wizard_type, wizard["missing"], labels
            )
            for field, value in llm_extracted.items():
                if field in wizard["missing"] and value is not None:
                    wizard["collected"][field] = value
                    wizard["missing"].remove(field)
                    logger.info(f"Wizard {wizard_type}: campo '{field}' = {value} (via LLM)")

    # Verifica se ainda faltam campos
    if wizard["missing"]:
        missing_labels = [labels[f] for f in wizard["missing"]]
        collected_summary = _format_collected(wizard["collected"], labels)

        response = ""
        if collected_summary:
            response += f"Já tenho:\n{collected_summary}\n\n"

        # Se o próximo campo pendente tem opções, mostra menu de opções
        first_missing = wizard["missing"][0] if wizard["missing"] else None
        if first_missing and first_missing in option_labels:
            response += _build_option_prompt(first_missing, option_labels[first_missing])
        else:
            response += "Ainda preciso de:\n"
            for label in missing_labels:
                response += f"- {label}\n"

        state["response"] = response
        wizard["updated_at"] = datetime.now(UTC).isoformat()
        _save_wizard_state(phone_number, wizard)
        return state

    # Todos os campos coletados - vai para confirmação
    wizard["status"] = "confirming"
    return _prompt_for_confirmation(state, wizard, phone_number)


def _prompt_for_confirmation(
    state: dict[str, Any], wizard: dict[str, Any], phone_number: str
) -> dict[str, Any]:
    """Show confirmation without treating the current data message as approval."""
    summary = _format_confirmation(wizard)
    if wizard["type"] in {"create_budget", "create_goal", "update_budget", "update_goal", "contribute_goal"}:
        state["response"] = summary
    else:
        state["response"] = (
            f"{summary}\n\nConfirma?\nResponda 'sim' para criar ou me diga o que quer alterar."
        )
    wizard["updated_at"] = datetime.now(UTC).isoformat()
    _save_wizard_state(phone_number, wizard)
    return state


def _handle_confirming(
    state: dict[str, Any], wizard: dict[str, Any], message: str, phone_number: str, llm: Any
) -> dict[str, Any]:
    """Pede confirmação antes de executar."""
    wizard_type = wizard["type"]

    # Se o usuário confirmou
    msg_lower = message.lower().strip()
    confirm_words = [
        "sim",
        "yes",
        "confirmar",
        "ok",
        "tá bom",
        "pode criar",
        "pode",
        "criar",
        "confirmo",
    ]
    cancel_words = ["não", "nao", "no", "cancelar", "cancela", "esquece", "errado"]

    if any(w in msg_lower for w in confirm_words):
        wizard["status"] = "executing"
        return _handle_executing(state, wizard, phone_number)

    if any(w in msg_lower for w in cancel_words):
        _clear_wizard_state(phone_number)
        state["response"] = (
            "Cancelado. Se quiser tentar de novo, é só mandar 'criar orçamento' ou 'criar meta'."
        )
        return state

    # Se o usuário quer corrigir algum campo
    if any(w in msg_lower for w in ["mudar", "alterar", "trocar", "corrigir", "nao é", "não é"]):
        wizard["status"] = "collecting"
        # Tenta identificar qual campo corrigir
        if llm:
            correction = _extract_correction_with_llm(llm, message, wizard["collected"])
            if correction:
                for field, value in correction.items():
                    wizard["collected"][field] = value
                    if field in wizard["missing"]:
                        wizard["missing"].remove(field)
        return _handle_collecting(state, wizard, message, phone_number, llm)

    # Resumo para confirmação
    summary = _format_confirmation(wizard)
    if wizard_type in ("create_budget", "update_budget"):
        state["response"] = summary
    else:
        state["response"] = (
            f"{summary}\n\nConfirma?\nResponda 'sim' para criar ou me diga o que quer alterar."
        )
    wizard["updated_at"] = datetime.now(UTC).isoformat()
    _save_wizard_state(phone_number, wizard)
    return state


def _find_goal(goals: list, identifier: str) -> dict | None:
    """Encontra meta por nome ou índice."""
    if not identifier:
        return goals[0] if len(goals) == 1 else None
    for g in goals:
        if identifier.lower() in g["title"].lower():
            return g
    try:
        idx = int(identifier) - 1
        if 0 <= idx < len(goals):
            return goals[idx]
    except ValueError:
        pass
    return None


def _handle_executing(
    state: dict[str, Any], wizard: dict[str, Any], phone_number: str
) -> dict[str, Any]:
    """Executa a ação do wizard."""
    wizard_type = wizard["type"]
    collected = wizard["collected"]

    try:
        if wizard_type == "create_budget":
            from app.services.budget_service import create_budget

            from app.core.financial_categories import resolve_default_category_name

            total_limit_value = collected.get("total_limit", 0)
            if not isinstance(total_limit_value, (int, float)):
                total_limit_value = _parse_value(str(total_limit_value)) or 0
            budget = create_budget(
                phone_number=phone_number,
                name=resolve_default_category_name(collected.get("name", "Geral")),
                total_limit=float(total_limit_value),
                period=collected.get("period", "monthly"),
                budget_type="category",
            )
            state["budget_data"] = budget
            state["response"] = resp.budget_saved_success()

        elif wizard_type == "update_budget":
            from app.core.financial_categories import resolve_default_category_name
            from app.services.budget_service import update_budget_limit

            total_limit_value = collected.get("total_limit", 0)
            if not isinstance(total_limit_value, (int, float)):
                total_limit_value = _parse_value(str(total_limit_value)) or 0
            name = resolve_default_category_name(collected.get("name", ""))
            result = update_budget_limit(phone_number, name, float(total_limit_value))
            if result:
                state["budget_data"] = result
                state["response"] = resp.budget_created(
                    result["name"],
                    float(result["total_limit"]),
                    result["period"],
                    updated=True,
                )
            else:
                state["response"] = f"Não encontrei o orçamento '{name}'."

        elif wizard_type == "create_goal":
            from app.services.budget_service import create_goal

            deadline_str = collected.get("deadline")
            deadline = None
            if deadline_str:
                parsed = _parse_deadline(deadline_str)
                if parsed:
                    try:

                        deadline = datetime.strptime(parsed, "%d/%m/%Y").date()
                    except Exception:
                        pass
            goal = create_goal(
                phone_number=phone_number,
                title=collected.get("title", "Reserva"),
                target_amount=_parse_value(collected.get("target_amount", 0)) or 0,
                deadline=deadline,
            )
            state["goal_data"] = goal
            state["response"] = resp.goal_saved_success()

        elif wizard_type in ("update_goal", "contribute_goal"):
            from app.services.budget_service import get_goals, update_goal_progress

            goals = get_goals(phone_number)
            identifier = collected.get("goal_identifier", "")
            amount = _parse_value(collected.get("amount", 0))
            target_goal = _find_goal(goals, identifier)

            if target_goal and amount:
                result = update_goal_progress(phone_number, target_goal["id"], amount)
                state["response"] = resp.goal_contribution_success(
                    result["title"],
                    float(result["current_amount"]),
                    float(result["target_amount"]),
                    result["percentage"],
                )
            else:
                goals_list = "\n".join(
                    [
                        f"{i + 1}. {g['title']} (R$ {g['target_amount']:,.2f})"
                        for i, g in enumerate(goals)
                    ]
                )
                state["response"] = (
                    f"Não encontrei a meta '{identifier}'.\nSuas metas atuais:\n{goals_list}"
                    if goals
                    else "Você não tem metas ainda."
                )

        _clear_wizard_state(phone_number)
        logger.info(f"Wizard {wizard_type} executado com sucesso para {phone_number}")

    except Exception as e:
        logger.error(f"Erro ao executar wizard {wizard_type}: {e}")
        state["error"] = f"Erro ao executar: {e!s}"
        _clear_wizard_state(phone_number)

    return state


def _extract_fields_with_llm(
    llm: Any, message: str, wizard_type: str, missing_fields: list, labels: dict
) -> dict[str, Any]:
    """Usa LLM para extrair campos da mensagem do usuário."""
    schema = WIZARD_SCHEMAS[wizard_type]
    fields_str = ", ".join([labels[f] for f in missing_fields])

    # Mapeia nomes de campos para o LLM
    from app.agents.prompts.wizard import FIELD_EXAMPLES, build_wizard_extract_prompt

    system_prompt = build_wizard_extract_prompt(
        wizard_type=wizard_type,
        field_example=FIELD_EXAMPLES.get(wizard_type, "{}"),
    )

    try:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Mensagem: {message}"),
        ]
        response, latency_ms = timed_invoke(llm, messages, operation="wizard_extract_fields")
        content = response.content.strip()
        # Tenta extrair JSON
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        result = json.loads(content)
        logger.info(f"[wizard] LLM extraiu campos em {latency_ms:.0f}ms: {result}")
        return result
    except Exception as e:
        logger.warning(f"[wizard] LLM falhou ao extrair campos: {e}")
        return {}


def _extract_fields_simple(message: str, wizard_type: str, missing_fields: list) -> dict[str, Any]:
    """Fallback sem LLM para extração de campos."""
    result = {}
    msg_lower = message.lower()

    # Se a mensagem é apenas um comando, não extrai nada
    command_words = ["criar", "crie", "novo", "nova", "quero", "fazer", "definir"]
    msg_words = message.lower().split()
    is_just_command = len(msg_words) <= 3 and any(w in msg_words for w in command_words)
    if is_just_command:
        return result

    # Se a mensagem é só um número e o único campo pendente é numérico
    only_number = re.match(r"^\s*R?\$?\s*(\d+(?:[.,]\d{1,2})?)\s*$", message)
    if only_number and len(missing_fields) == 1:
        only_field = missing_fields[0]
        if only_field in ["total_limit", "target_amount", "amount"]:
            val = _parse_value(only_number.group(1))
            if val is not None:
                result[only_field] = val
                return result

    # Tenta extrair valor numérico
    if any(f in missing_fields for f in ["total_limit", "target_amount", "amount"]):
        value_match = re.search(
            r"R?\$?\s*(\d{1,3}(?:[.,]\d{3})*[.,]\d{1,2}|\d+(?:[.,]\d{1,2})?)", message
        )
        if value_match:
            val = _parse_value(value_match.group(1))
            if val is not None:
                for field in ["total_limit", "target_amount", "amount"]:
                    if field in missing_fields:
                        result[field] = val
                        break

    # Tenta extrair deadline
    if "deadline" in missing_fields:
        deadline = _parse_deadline(message)
        if deadline:
            result["deadline"] = deadline

    # Tenta extrair nome/título (texto restante sem números)
    if "name" in missing_fields or "title" in missing_fields:
        # Remove valores monetários e datas
        text_only = re.sub(r"R?\$?\s*\d{1,3}(?:[.,]\d{3})*[.,]?\d*", "", message)
        text_only = re.sub(r"\d{1,2}/\d{1,2}/\d{4}|\d{1,2}/\d{4}", "", text_only)
        text_only = re.sub(r"\b(mensal|semanal|anual|diario|diário)\b", "", text_only, flags=re.I)
        text_only = text_only.strip(" ,.;:-")
        if text_only and len(text_only) > 1:
            field = "name" if "name" in missing_fields else "title"
            value = text_only.strip()
            if field == "name" and wizard_type in {"create_budget", "update_budget"}:
                from app.core.financial_categories import resolve_default_category_name

                value = resolve_default_category_name(value)
            result[field] = value

    # Tenta extrair period
    if "period" in missing_fields:
        if any(w in msg_lower for w in ["semana", "semanal"]):
            result["period"] = "weekly"
        elif any(w in msg_lower for w in ["dia", "diario", "diário"]):
            result["period"] = "daily"
        elif any(w in msg_lower for w in ["ano", "anual"]):
            result["period"] = "yearly"

    return result


def _extract_correction_with_llm(llm: Any, message: str, collected: dict) -> dict[str, Any]:
    """Usa LLM para identificar correções em campos já coletados."""
    from app.agents.prompts.wizard import WIZARD_CORRECTION_PROMPT

    system_prompt = WIZARD_CORRECTION_PROMPT
    try:
        response = llm.invoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"Dados atuais: {json.dumps(collected)}\nMensagem: {message}"),
            ]
        )
        content = response.content.strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        return json.loads(content)
    except Exception:
        return {}


def _format_collected(collected: dict, labels: dict) -> str:
    """Formata dados já coletados para exibição."""
    lines = []
    for field, value in collected.items():
        label = labels.get(field, field)
        if field in ["total_limit", "target_amount", "amount"] and value:
            lines.append(f"- {label}: R$ {float(value):,.2f}")
        else:
            lines.append(f"- {label}: {value}")
    return "\n".join(lines)


def _format_confirmation(wizard: dict) -> str:
    """Formata resumo para confirmação."""
    wizard_type = wizard["type"]
    collected = wizard["collected"]

    if wizard_type == "create_budget":
        name = collected.get("name", "")
        limit = collected.get("total_limit", 0)
        period = collected.get("period", "monthly")
        return resp.budget_confirmation(str(name), float(limit), str(period or "monthly"))

    elif wizard_type == "update_budget":
        from app.core.financial_categories import resolve_default_category_name

        name = resolve_default_category_name(collected.get("name", ""))
        limit = collected.get("total_limit", 0)
        return f"Vou atualizar o orçamento {name} para R$ {float(limit):,.2f}.\n\nConfirma?"

    elif wizard_type == "create_goal":
        title = collected.get("title", "")
        target = collected.get("target_amount", 0)
        deadline = collected.get("deadline", "")
        return resp.goal_confirmation(str(title), float(target), deadline)

    elif wizard_type in ("update_goal", "contribute_goal"):
        identifier = collected.get("goal_identifier", "")
        amount = collected.get("amount", 0)
        return resp.goal_contribution_confirmation(str(identifier), float(amount))

    return ""


def _period_label(period: str) -> str:
    return {"daily": "Diário", "weekly": "Semanal", "monthly": "Mensal", "yearly": "Anual"}.get(
        period, "Mensal"
    )
