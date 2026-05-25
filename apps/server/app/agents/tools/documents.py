"""Document tools for BagCoin chat agents."""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.tools import BaseTool, tool

from app.agents.document_understanding import (
    _normalize_receipt_items,
    _normalize_receipt_payload,
    _reconcile_receipt_total,
    analyze_document_media,
)
from app.agents import responses as resp
from app.agents.pending_actions import save_pending_action
from app.core.financial_categories import resolve_default_category_name
from app.services.agent_memory_service import record_memory_event_for_phone

logger = logging.getLogger(__name__)


def create_document_tools(phone_number: str, context: dict[str, Any] | None = None) -> list[BaseTool]:
    """Create document tools with media and tenant context captured in closures."""
    context = context or {}
    media = context.get("media") or {}
    channel = str(context.get("channel") or "whatsapp")
    if channel not in {"whatsapp", "telegram"}:
        channel = "whatsapp"

    @tool
    def analyze_uploaded_document() -> str:
        """Analyze the uploaded document/image and prepare financial import confirmation."""
        # Se já temos extração estruturada de imagem (nota/cupom), usar diretamente
        image_structured = context.get("image_structured")
        if isinstance(image_structured, dict):
            image_structured = _normalize_receipt_payload(image_structured)
        if image_structured:
            import json as _json
            logger.info("[document_tool] image_structured: %s", _json.dumps(image_structured, ensure_ascii=False, default=str)[:2000])
        if (
            image_structured
            and image_structured.get("is_receipt")
            and (image_structured.get("total_amount") or image_structured.get("items"))
        ):
            return _handle_receipt_structured(image_structured, phone_number, channel)

        result = analyze_document_media(
            media,
            extracted_text=context.get("extracted_media_text"),
        )
        logger.info(
            "[document_tool] analyzed %s (%s) -> type=%s txs=%s method=%s",
            (result.get("source") or {}).get("filename") or "sem_nome",
            (result.get("source") or {}).get("mimetype") or "desconhecido",
            result.get("document_type"),
            len(result.get("transactions") or []),
            result.get("extraction_method"),
        )
        transactions = result.get("transactions") or []
        if not result.get("is_financial"):
            source_format = "image" if str((result.get("source") or {}).get("mimetype") or "").startswith("image/") else "document"
            record_memory_event_for_phone(
                phone_number,
                event_type="non_financial_media_received",
                entity_type="media",
                source=source_format,
                summary="Mídia sem conteúdo financeiro aceita pelo BagCoin.",
                payload={"result": result},
            )
            return resp.non_financial_media(source_format)
        if not transactions:
            issues = result.get("issues") or []
            issue_text = f"\n\nPontos de atenção: {', '.join(issues)}" if issues else ""
            return (
                "Identifiquei um documento financeiro, mas não encontrei transações "
                f"seguras para importar.{issue_text}"
            )

        summary = _document_confirmation_summary(result, transactions)
        return save_pending_action(
            phone_number,
            action="import_document_transactions",
            params={
                "transactions": transactions,
                "document_type": result.get("document_type"),
                "extraction_method": result.get("extraction_method"),
                "confidence": result.get("confidence"),
                "source": result.get("source") or {},
            },
            summary=summary,
            channel=channel,
        )

    return [analyze_uploaded_document]


def _format_brl(value: Any) -> str:
    try:
        formatted = f"{float(value):,.2f}"
    except (TypeError, ValueError):
        formatted = "0.00"
    return f"R$ {formatted}".replace(",", "X").replace(".", ",").replace("X", ".")


def _document_confirmation_summary(result: dict[str, Any], transactions: list[dict[str, Any]]) -> str:
    document_type = str(result.get("document_type") or "")
    if document_type in {"receipt", "invoice"} and len(transactions) == 1:
        return _receipt_confirmation_summary(result, transactions[0])

    totals = result.get("totals") or {}
    issues = result.get("issues") or []
    issue_text = f"\n\nPontos de atenção: {', '.join(issues[:3])}" if issues else ""
    preview_lines = []
    for tx in transactions[:5]:
        preview_lines.append(
            f"- {tx['description']}: {_format_brl(tx['amount'])} "
            f"({'receita' if tx['type'] == 'INCOME' else 'despesa'})"
        )
    preview = "\n".join(preview_lines)
    tx_count = int(totals.get("transactions") or len(transactions))
    income_total = float(totals.get("income") or 0)
    expense_total = float(totals.get("expense") or 0)
    return (
        f"Encontrei {tx_count} transação{'ões' if tx_count != 1 else ''} neste documento.\n\n"
        f"- Receitas: {_format_brl(income_total)}\n"
        f"- Despesas: {_format_brl(expense_total)}"
        f"{issue_text}\n\n"
        f"Revise os principais lançamentos:\n{preview}\n\n"
        "Se estiver correto, posso importar essas transações."
    )


def _receipt_confirmation_summary(result: dict[str, Any], transaction: dict[str, Any]) -> str:
    items = result.get("receipt_items") or []
    total = float(transaction.get("amount") or result.get("total_amount") or 0)
    income_total = total if transaction.get("type") == "INCOME" else 0
    expense_total = total if transaction.get("type") != "INCOME" else 0
    type_label = "receita" if transaction.get("type") == "INCOME" else "despesa"
    item_count = len(items)
    item_lines = []
    for item in items[:12]:
        item_lines.append(f"- \"{item['description']}\": {_format_brl(item['amount'])}")
    if item_count > 12:
        item_lines.append(f"- ... e mais {item_count - 12} item(ns)")
    item_text = "\n".join(item_lines) if item_lines else "- Itens não detalhados com segurança."
    kind = "item" if item_count == 1 else "itens"
    return (
        f"Identifiquei uma {type_label} nesta imagem.\n\n"
        f"Encontrei {item_count or 1} {kind} neste documento.\n\n"
        f"Aqui estão os itens encontrados:\n{item_text}\n\n"
        f"Valor total: {_format_brl(total)}\n\n"
        f"Receitas: {_format_brl(income_total)}\n"
        f"Despesas: {_format_brl(expense_total)}\n\n"
        "Se estiver correto, posso importar esta transação."
    )


def _handle_receipt_structured(structured: dict[str, Any], phone_number: str, channel: str) -> str:
    """Handle a structured receipt extraction as a single transaction."""
    structured = _normalize_receipt_payload(structured)
    tx_type = _receipt_transaction_type(structured)
    if structured.get("needs_type_confirmation"):
        return _save_receipt_type_clarification(structured, phone_number, channel)
    tx_type = tx_type or "EXPENSE"

    tx, summary = _build_receipt_transaction_confirmation(structured, tx_type)
    return save_pending_action(
        phone_number,
        action="register_transaction",
        params={**tx, "source_format": "image"},
        summary=summary,
        channel=channel,
    )


def _receipt_transaction_type(structured: dict[str, Any]) -> str | None:
    structured = _normalize_receipt_payload(structured)
    tx_type = structured.get("transaction_type") or structured.get("type")
    if isinstance(tx_type, str):
        normalized = tx_type.strip().upper()
        if normalized in {"EXPENSE", "INCOME"}:
            return normalized
    raw_type = str(structured.get("tipo") or "").strip().lower()
    if raw_type in {"despesa", "gasto", "saida", "saída", "paguei", "pagamento"}:
        return "EXPENSE"
    if raw_type in {"receita", "entrada", "recebi", "recebimento", "deposito", "depósito"}:
        return "INCOME"
    return None


def _build_receipt_transaction_confirmation(
    structured: dict[str, Any],
    tx_type: str,
) -> tuple[dict[str, Any], str]:
    from datetime import datetime

    structured = _normalize_receipt_payload(structured)
    total = _receipt_total(structured)
    establishment = str(structured.get("establishment") or "").strip()
    date = structured.get("transaction_date") or datetime.now().strftime("%Y-%m-%d")
    description = str(structured.get("description") or "").strip()
    if not description:
        if tx_type == "EXPENSE":
            description = f"Nota fiscal {establishment}" if establishment else "Nota fiscal"
        else:
            description = f"Comprovante {establishment}" if establishment else "Comprovante"

    tx = {
        "date": date,
        "description": description,
        "amount": round(total, 2),
        "type": tx_type,
        "category": _receipt_category(structured),
        "confidence": float(structured.get("confidence") or 0.85),
        "raw": establishment or "imagem",
    }

    items = _normalize_receipt_items(structured.get("items") or [])
    summary = resp.transaction_confirmation(
        tx["type"],
        tx["amount"],
        tx["category"],
        tx["description"],
        tx["date"],
    )
    return tx, summary


def _save_receipt_type_clarification(
    structured: dict[str, Any],
    phone_number: str,
    channel: str,
) -> str:
    structured = _normalize_receipt_payload(structured)
    total = _receipt_total(structured)
    establishment = str(structured.get("establishment") or "comprovante").strip()
    category = _receipt_category(structured)
    items = _normalize_receipt_items(structured.get("items") or [])
    summary = (
        f"Identifiquei um comprovante de {_format_brl(total)} em {establishment}, "
        "mas não ficou claro se é uma receita ou uma despesa.\n\n"
        "Isso é receita ou despesa?"
    )
    return save_pending_action(
        phone_number,
        action="clarify_image_transaction_type",
        params={
            "structured": structured,
            "items": items,
            "total_amount": total,
            "establishment": establishment,
            "suggested_category": category,
            "question": "Isso é receita ou despesa?",
            "source_format": "image",
        },
        summary=summary,
        channel=channel,
    )


def _receipt_category(structured: dict[str, Any]) -> str:
    """Guess category from receipt type and establishment."""
    structured = _normalize_receipt_payload(structured)
    explicit_category = str(structured.get("category") or "").strip()
    if explicit_category:
        return resolve_default_category_name(explicit_category)
    receipt_type = str(structured.get("receipt_type") or "").lower()
    establishment = str(structured.get("establishment") or "").lower()

    food_keywords = ("mercado", "supermercado", "padaria", "restaurante", "lanchonete", "açougue", "hortifruti", "atacado")
    transport_keywords = ("uber", "99", "taxi", "posto", "combustível", "shell", "ipiranga")
    health_keywords = ("farmácia", "farmacia", "drogaria", "hospital", "clínica")

    if any(k in establishment for k in ("mercado", "supermercado", "hortifruti", "atacado")):
        return "Supermercado"
    if any(k in establishment for k in food_keywords) or receipt_type == "nfce":
        return "Alimentação"
    if any(k in establishment for k in transport_keywords):
        return "Transporte"
    if any(k in establishment for k in health_keywords):
        return "Saúde"
    return "Outros"


def _receipt_total(structured: dict[str, Any]) -> float:
    structured = _normalize_receipt_payload(structured)
    try:
        total = float(structured.get("labeled_total_amount") or structured.get("total_amount") or 0)
    except (TypeError, ValueError):
        total = 0.0
    reconciled = _reconcile_receipt_total(
        total if total > 0 else None,
        _normalize_receipt_items(structured.get("items") or []),
    )
    return round(float(reconciled or 0), 2)
