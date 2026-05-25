"""Pending action storage and execution for chat confirmations."""

from __future__ import annotations

import logging
import re
import unicodedata
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from sqlalchemy.orm.attributes import flag_modified

from app.agents import responses as resp
from app.agents.persistence import (
    create_category as persistence_create_category,
    delete_category as persistence_delete_category,
    delete_transaction_by_id,
    get_or_create_user,
    get_user_transactions,
    list_categories as persistence_list_categories,
    rename_category as persistence_rename_category,
    save_transaction,
    update_transaction as persistence_update_transaction,
)
from app.core.financial_categories import resolve_default_category_name
from app.db.models.phone_conversation import PhoneConversation
from app.db.session import sync_session_maker
from app.services.budget_service import (
    create_budget,
    create_goal,
    delete_budget_by_name,
    delete_goal,
    get_goals,
    update_budget_limit,
    update_goal,
    update_goal_progress,
)

logger = logging.getLogger(__name__)

PENDING_KEY = "pending_tool_action"
PENDING_TTL_MINUTES = 15


def _normalize_text(text: str) -> str:
    return unicodedata.normalize("NFKD", text.lower()).encode("ASCII", "ignore").decode("ASCII")


def _get_conversation(phone_number: str):
    db = sync_session_maker()
    user = get_or_create_user(phone_number, db)
    conv = (
        db.query(PhoneConversation)
        .filter(PhoneConversation.user_id == user.id)
        .order_by(PhoneConversation.updated_at.desc())
        .first()
    )
    if not conv:
        conv = PhoneConversation(user_id=user.id, channel="whatsapp", context_json={})
        db.add(conv)
        db.flush()
    return db, conv


def save_pending_action(
    phone_number: str,
    *,
    action: str,
    params: dict[str, Any],
    summary: str,
    channel: str = "whatsapp",
) -> str:
    """Store a pending action and return the confirmation text."""
    db, conv = _get_conversation(phone_number)
    try:
        effective_summary = summary
        if action == "register_transaction":
            effective_summary = _register_transaction_confirmation_text(params)
        if action == "create_budget":
            effective_summary = _create_budget_confirmation_text(params)
        if action == "create_goal":
            effective_summary = _create_goal_confirmation_text(params)
        if action == "contribute_goal":
            effective_summary = _contribute_goal_confirmation_text(params)
        if action == "update_goal":
            effective_summary = _update_goal_confirmation_text(params)
        if action == "delete_goal":
            effective_summary = _delete_goal_confirmation_text(params)
        context = dict(conv.context_json or {})
        context[PENDING_KEY] = {
            "action": action,
            "params": params,
            "summary": effective_summary,
            "channel": channel,
            "status": "pending",
            "created_at": datetime.now(UTC).isoformat(),
        }
        conv.context_json = context
        flag_modified(conv, "context_json")
        db.commit()
        logger.info("[pending_action] created action=%s phone=%s", action, phone_number)
        if action == "clarify_image_transaction_type":
            return effective_summary
        if action in {
            "register_transaction",
            "create_budget",
            "create_goal",
            "contribute_goal",
            "update_goal",
            "delete_goal",
        }:
            return effective_summary
        return f"{summary}\n\nConfirma?"
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def load_pending_action(phone_number: str) -> dict[str, Any] | None:
    db, conv = _get_conversation(phone_number)
    try:
        pending = (conv.context_json or {}).get(PENDING_KEY)
        if not pending or pending.get("status") != "pending":
            return None
        created_raw = pending.get("created_at")
        try:
            created_at = datetime.fromisoformat(str(created_raw).replace("Z", "+00:00"))
        except ValueError:
            created_at = datetime.now(UTC)
        if datetime.now(UTC) - created_at > timedelta(minutes=PENDING_TTL_MINUTES):
            clear_pending_action(phone_number)
            return None
        return dict(pending)
    finally:
        db.close()


def clear_pending_action(phone_number: str) -> None:
    db, conv = _get_conversation(phone_number)
    try:
        context = dict(conv.context_json or {})
        context.pop(PENDING_KEY, None)
        conv.context_json = context
        flag_modified(conv, "context_json")
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def pending_confirmation_decision(message: str) -> Literal["confirm", "cancel"] | None:
    """Interpret short confirmation/cancel messages only after a pending action exists."""
    msg = _normalize_text(message).strip(" .,!?\n\t")
    if msg.startswith(("sim ", "ok ", "pode ")):
        return "confirm"
    confirm_values = {
        "sim",
        "s",
        "ok",
        "pode",
        "confirmo",
        "confirmar",
        "isso",
        "isso mesmo",
        "correto",
        "ta certo",
        "esta certo",
        "manda",
        "sim registre",
        "sim importar",
        "sim importe",
        "registre",
        "importe",
    }
    cancel_values = {
        "nao",
        "n",
        "cancelar",
        "cancela",
        "cancele",
        "deixa",
        "deixa quieto",
        "esquece",
        "errado",
    }
    if msg in confirm_values:
        return "confirm"
    if msg in cancel_values:
        return "cancel"
    return None


def image_transaction_type_decision(message: str) -> Literal["INCOME", "EXPENSE"] | None:
    msg = _normalize_text(message).strip(" .,!?\n\t")
    income_markers = {
        "receita",
        "e receita",
        "entrada",
        "e entrada",
        "recebi",
        "eu recebi",
        "recebimento",
        "deposito",
        "deposito recebido",
        "pix recebido",
        "reembolso",
        "salario",
    }
    expense_markers = {
        "despesa",
        "e despesa",
        "gasto",
        "e gasto",
        "saida",
        "paguei",
        "eu paguei",
        "pagamento",
        "compra",
        "foi compra",
    }
    if msg in income_markers or any(marker in msg for marker in ("e receita", "entrada", "recebi")):
        return "INCOME"
    if msg in expense_markers or any(marker in msg for marker in ("e despesa", "gasto", "paguei")):
        return "EXPENSE"
    return None


def has_pending_confirmation_message(phone_number: str, message: str) -> bool:
    pending = load_pending_action(phone_number)
    if not pending:
        logger.debug("[pending] No pending action for phone=%s msg=%s", phone_number, message[:50])
        return False
    if pending.get("action") == "clarify_image_transaction_type":
        return (
            image_transaction_type_decision(message) is not None
            or pending_confirmation_decision(message) is not None
        )
    if pending.get("action") == "register_transaction":
        return (
            pending_confirmation_decision(message) is not None
            or _looks_like_register_transaction_correction(message)
        )
    result = pending_confirmation_decision(message) is not None
    if not result:
        logger.debug("[pending] Message not recognized as confirmation: phone=%s msg=%s", phone_number, message[:50])
    return result


def handle_pending_confirmation(phone_number: str, message: str) -> str | None:
    pending = load_pending_action(phone_number)
    if not pending:
        return None
    if pending.get("action") == "register_transaction" and pending_confirmation_decision(message) is None:
        correction_response = _apply_register_transaction_correction(phone_number, pending, message)
        if correction_response is not None:
            return correction_response
    if pending.get("action") == "clarify_image_transaction_type":
        type_decision = image_transaction_type_decision(message)
        cancel_decision = pending_confirmation_decision(message)
        if cancel_decision == "cancel":
            clear_pending_action(phone_number)
            return "Combinado, nao executei essa acao."
        if type_decision is None:
            return pending.get("summary") or "Isso é receita ou despesa?"
        params = dict(pending.get("params") or {})
        structured = dict(params.get("structured") or {})
        try:
            from app.agents.tools.documents import _build_receipt_transaction_confirmation

            tx, summary = _build_receipt_transaction_confirmation(structured, type_decision)
            return save_pending_action(
                phone_number,
                action="register_transaction",
                params={**tx, "source_format": "image"},
                summary=summary,
                channel=str(pending.get("channel") or "whatsapp"),
            )
        except Exception as exc:
            logger.exception("[pending_action] image type clarification failed")
            clear_pending_action(phone_number)
            return f"Nao consegui preparar a confirmacao dessa imagem: {exc}"
    decision = pending_confirmation_decision(message)
    logger.info("[pending] Confirmation decision=%s action=%s phone=%s msg=%s", decision, pending.get("action"), phone_number, message[:50])
    if decision == "cancel":
        clear_pending_action(phone_number)
        return "Combinado, nao executei essa acao."
    if decision != "confirm":
        return None
    try:
        response = execute_pending_action(phone_number, pending)
        clear_pending_action(phone_number)
        return response
    except Exception as exc:
        logger.exception("[pending_action] execution failed")
        clear_pending_action(phone_number)
        return f"Nao consegui executar essa acao: {exc}"


def _money(value: Any) -> str:
    try:
        return f"R$ {float(value):,.2f}"
    except (TypeError, ValueError):
        return "R$ 0,00"


def _normalize_amount_text(value: str) -> str:
    return value.replace(" ", "").replace(".", "").replace(",", ".")


def _parse_amount_from_message(message: str) -> float | None:
    patterns = (
        r"\bvalor(?:\s+(?:errado|era|para|de|correto|certo))?(?:\s+(?:e|eh|foi))?\s*(?:r\$)?\s*([0-9][0-9\.,]*)\b",
        r"\b(?:era|para|de)\s*(?:r\$)?\s*([0-9][0-9\.,]*)\b",
    )
    for pattern in patterns:
        match = re.search(pattern, message)
        if not match:
            continue
        raw = _normalize_amount_text(match.group(1))
        try:
            return float(raw)
        except ValueError:
            continue
    return None


def _parse_date_from_message(message: str):
    match = re.search(
        r"\bdata(?:\s+(?:errada|era|para|de))?\s*([0-3]?\d[/-][01]?\d[/-]\d{2,4}|\d{4}-\d{2}-\d{2})\b",
        message,
    )
    if not match:
        return None
    return _parse_date(match.group(1))


def _parse_text_after_keyword(message: str, keyword: str) -> str | None:
    match = re.search(rf"\b{keyword}\b(?:\s+(?:era|para|pra|de|do|da|o|a|um|uma))?\s*(.+)$", message)
    if not match:
        return None
    value = match.group(1).strip(" .,!?\n\t")
    value = re.sub(r"^(era|para|pra|de|do|da)\s+", "", value).strip(" .,!?\n\t")
    return value or None


def _parse_transaction_type_from_message(message: str) -> str | None:
    income_markers = (
        "era receita",
        "e receita",
        "é receita",
        "tipo receita",
        "na verdade receita",
    )
    expense_markers = (
        "era despesa",
        "e despesa",
        "é despesa",
        "tipo despesa",
        "na verdade despesa",
    )
    if any(marker in message for marker in income_markers) and not any(
        marker in message for marker in expense_markers
    ):
        return "INCOME"
    if any(marker in message for marker in expense_markers) and not any(
        marker in message for marker in income_markers
    ):
        return "EXPENSE"
    return None


def _register_transaction_confirmation_params(params: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": params.get("type") or params.get("transaction_type") or "EXPENSE",
        "amount": params.get("amount") or params.get("total_amount") or 0,
        "category": params.get("category") or params.get("category_name") or "Outros",
        "description": (
            params.get("description")
            or params.get("establishment")
            or params.get("name")
            or "Sem descrição"
        ),
        "transaction_date": params.get("date") or params.get("transaction_date"),
    }


def _register_transaction_confirmation_text(params: dict[str, Any]) -> str:
    confirm_params = _register_transaction_confirmation_params(params)
    return resp.transaction_confirmation(
        confirm_params["type"],
        confirm_params["amount"],
        confirm_params["category"],
        confirm_params["description"],
        confirm_params["transaction_date"],
    )


def _create_budget_confirmation_text(params: dict[str, Any]) -> str:
    return resp.budget_confirmation(
        params.get("name") or "Outros",
        float(params.get("total_limit") or 0),
        params.get("period") or "monthly",
    )


def _create_goal_confirmation_text(params: dict[str, Any]) -> str:
    return resp.goal_confirmation(
        params.get("title") or "Reserva",
        float(params.get("target_amount") or 0),
        params.get("deadline"),
    )


def _contribute_goal_confirmation_text(params: dict[str, Any]) -> str:
    return resp.goal_contribution_confirmation(
        params.get("goal_identifier") or "sua meta",
        float(params.get("amount") or 0),
    )


def _update_goal_confirmation_text(params: dict[str, Any]) -> str:
    target_amount = params.get("target_amount")
    return resp.goal_update_confirmation(
        params.get("goal_identifier") or "sua meta",
        title=params.get("title"),
        target_amount=float(target_amount) if target_amount is not None else None,
        deadline=params.get("deadline"),
    )


def _delete_goal_confirmation_text(params: dict[str, Any]) -> str:
    return resp.goal_delete_confirmation(params.get("goal_identifier") or "sua meta")


def _parse_date(value: Any):
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%Y"):
        try:
            parsed = datetime.strptime(str(value), fmt).date()
            if fmt == "%m/%Y":
                today = datetime.now(UTC).date()
                while parsed <= today:
                    parsed = parsed.replace(year=parsed.year + 1)
            return parsed
        except ValueError:
            continue
    return None


def _apply_register_transaction_correction(phone_number: str, pending: dict[str, Any], message: str) -> str | None:
    params = dict(pending.get("params") or {})
    normalized = _normalize_text(message)
    updated = False

    amount = _parse_amount_from_message(normalized)
    if amount is not None:
        params["amount"] = amount
        updated = True

    parsed_date = _parse_date_from_message(normalized)
    if parsed_date is not None:
        params["date"] = parsed_date.isoformat()
        params.pop("transaction_date", None)
        updated = True

    category_text = _parse_text_after_keyword(normalized, "categoria")
    if category_text:
        params["category"] = resolve_default_category_name(category_text)
        updated = True

    description_text = _parse_text_after_keyword(normalized, "descricao")
    if description_text:
        params["description"] = description_text
        updated = True

    tx_type = _parse_transaction_type_from_message(normalized)
    if tx_type:
        params["type"] = tx_type
        updated = True

    if not updated:
        return None

    return save_pending_action(
        phone_number,
        action="register_transaction",
        params=params,
        summary=_register_transaction_confirmation_text(params),
        channel=str(pending.get("channel") or "whatsapp"),
    )


def _looks_like_register_transaction_correction(message: str) -> bool:
    normalized = _normalize_text(message)
    return any(
        (
            _parse_amount_from_message(normalized) is not None,
            _parse_date_from_message(normalized) is not None,
            _parse_text_after_keyword(normalized, "categoria") is not None,
            _parse_text_after_keyword(normalized, "descricao") is not None,
            _parse_transaction_type_from_message(normalized) is not None,
        )
    )


def _find_transaction_id(phone_number: str, description: str | None = None) -> int | None:
    txs = get_user_transactions(phone_number, limit=10)
    if description:
        desc_norm = _normalize_text(description)
        for tx in txs:
            tx_desc = _normalize_text(getattr(tx, "description", "") or "")
            if desc_norm in tx_desc or tx_desc in desc_norm:
                return int(tx.id)
    return int(txs[0].id) if txs else None


def execute_pending_action(phone_number: str, pending: dict[str, Any]) -> str:
    action = pending.get("action")
    params = dict(pending.get("params") or {})
    logger.info("[pending] Executing action=%s phone=%s params_keys=%s", action, phone_number, list(params.keys()))

    if action == "register_transaction":
        state = {
            "phone_number": phone_number,
            "source_format": params.get("source_format", "text"),
            "intent": "register_income" if params.get("type") == "INCOME" else "register_expense",
            "extracted_data": params,
        }
        result = save_transaction(state)
        if result.get("error"):
            logger.error("[pending] Transaction save failed: %s", result["error"])
            return str(result["error"])
        if not result.get("transaction_id"):
            logger.error("[pending] Transaction save returned no transaction_id")
            return "Nao consegui confirmar a persistencia da transacao no banco. Tente novamente."
        logger.info("[pending] Transaction saved: id=%s", result["transaction_id"])
        message = resp.transaction_registered(
            params.get("type", "EXPENSE"),
            float(params.get("amount") or 0),
            result.get("category_name") or params.get("category") or "Outros",
            params.get("description") or "",
            result.get("transaction_date") or params.get("date") or params.get("transaction_date"),
        )
        if params.get("is_recurring"):
            if result.get("needs_pairing_for_recurring"):
                message += (
                    "\n\nA transacao foi salva, mas nao criei a recorrencia automatica "
                    "porque sua conta web ainda nao esta conectada a este chat."
                )
            elif result.get("recurring_transaction_id"):
                message += "\n\nRecorrencia automatica criada."
            else:
                message += "\n\nA transacao foi salva, mas nao consegui confirmar a recorrencia."
        return message

    if action == "import_document_transactions":
        from app.agents.import_statement import import_parsed_transactions

        transactions = params.get("transactions") or []
        if not transactions:
            return "Não encontrei transações para importar nesse documento."
        result = import_parsed_transactions(
            phone_number,
            transactions,
            source_format="document_import",
        )
        return resp.document_imported(
            result.get("imported_transactions", []),
            int(result.get("skipped_count") or 0),
            result.get("import_errors") or [],
            label="Documento",
        )

    if action == "create_budget":
        budget = create_budget(
            phone_number,
            params["name"],
            float(params["total_limit"]),
            "monthly",
            params.get("budget_type") or "category",
        )
        return resp.budget_saved_success()

    if action == "update_budget":
        result = update_budget_limit(phone_number, params["name"], float(params["total_limit"]))
        if not result:
            return f"Nao encontrei o orcamento '{params['name']}'."
        return resp.budget_created(result["name"], float(result["total_limit"]), result["period"], updated=True)

    if action == "delete_budget":
        count = delete_budget_by_name(phone_number, params["name"])
        return f"Orcamento '{params['name']}' removido." if count else f"Nao encontrei o orcamento '{params['name']}'."

    if action == "create_goal":
        goal = create_goal(
            phone_number,
            params["title"],
            float(params["target_amount"]),
            _parse_date(params.get("deadline")),
        )
        return resp.goal_saved_success()

    if action == "contribute_goal":
        goals = get_goals(phone_number)
        target = None
        identifier = _normalize_text(params.get("goal_identifier") or "")
        for goal in goals:
            if identifier and identifier in _normalize_text(goal["title"]):
                target = goal
                break
        if not target and len(goals) == 1:
            target = goals[0]
        if not target:
            return "Nao encontrei essa meta. Pode dizer o nome da meta?"
        result = update_goal_progress(phone_number, target["id"], float(params["amount"]))
        return resp.goal_contribution_success(
            result["title"],
            float(result["current_amount"]),
            float(result["target_amount"]),
            result["percentage"],
        )

    if action == "update_goal":
        result = update_goal(
            phone_number,
            params["goal_identifier"],
            new_target=float(params["target_amount"]) if params.get("target_amount") else None,
            new_title=params.get("title"),
            new_deadline=_parse_date(params.get("deadline")),
        )
        if not result:
            return "Nao encontrei essa meta."
        return resp.goal_update_success(
            result["title"],
            float(result["target_amount"]),
            result.get("deadline"),
        )

    if action == "delete_goal":
        ok = delete_goal(phone_number, params["goal_identifier"])
        return resp.goal_delete_success() if ok else "Nao encontrei essa meta."

    if action == "update_transaction":
        tx_id = params.get("transaction_id") or _find_transaction_id(phone_number, params.get("description"))
        if not tx_id:
            return "Nao encontrei uma transacao recente para atualizar."
        result = persistence_update_transaction(
            phone_number,
            int(tx_id),
            amount=float(params["amount"]) if params.get("amount") is not None else None,
            description=params.get("new_description"),
            category_name=params.get("category"),
        )
        if not result:
            return "Nao encontrei a transacao para atualizar."
        return f"Transacao atualizada: {_money(result['amount'])} - {result.get('description') or ''}."

    if action == "delete_transaction":
        tx_id = params.get("transaction_id") or _find_transaction_id(phone_number, params.get("description"))
        if not tx_id:
            return "Nao encontrei uma transacao recente para remover."
        return "Transacao removida." if delete_transaction_by_id(phone_number, int(tx_id)) else "Nao encontrei a transacao."

    if action == "create_category":
        created = persistence_create_category(phone_number, params["name"])
        return f"Categoria '{created['name']}' criada." if created else f"A categoria '{params['name']}' ja existe ou e padrao."

    if action == "rename_category":
        ok = persistence_rename_category(phone_number, params["old_name"], params["new_name"])
        return f"Categoria renomeada para '{params['new_name']}'." if ok else "Nao consegui renomear essa categoria."

    if action == "delete_category":
        ok = persistence_delete_category(phone_number, params["name"])
        return f"Categoria '{params['name']}' removida." if ok else "Nao encontrei essa categoria ou ela e padrao."

    if action == "list_categories":
        cats = persistence_list_categories(phone_number)
        names = ", ".join(c["name"] for c in cats)
        return f"Suas categorias: {names}" if names else "Voce ainda nao tem categorias."

    raise ValueError(f"Acao pendente desconhecida: {action}")
