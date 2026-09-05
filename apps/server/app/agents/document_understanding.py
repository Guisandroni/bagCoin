"""Universal financial document understanding for agent tools.

This module separates document/file understanding from persistence. It returns a
validated, normalized payload that the orchestrator can preview and confirm
before saving transactions.
"""

from __future__ import annotations

import base64
import io
import json
import logging
import re
from datetime import datetime
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.statement_parser import (
    _clean_transaction_description,
    _extract_money_candidate,
    parse_statement,
)
from app.core.config import settings
from app.services.docx_text import extract_docx_text
from app.services.llm_service import get_llm, timed_invoke

logger = logging.getLogger(__name__)

MAX_LLM_TEXT_CHARS = 14_000

FINANCIAL_DOCUMENT_TYPES = {
    "bank_statement",
    "credit_card_statement",
    "receipt",
    "invoice",
    "financial_spreadsheet",
    "payment_proof",
}


def analyze_document_media(
    media: dict[str, Any],
    *,
    extracted_text: str | None = None,
) -> dict[str, Any]:
    """Analyze uploaded media and return a normalized document result."""
    if not media or not media.get("data"):
        return _empty_result("missing_media", "Nenhum arquivo foi recebido para análise.")

    mimetype = str(media.get("mimetype") or "").lower()
    filename = str(media.get("filename") or "")

    deterministic = _deterministic_statement_result(media)
    if deterministic:
        return deterministic

    content = _extract_text_for_understanding(media, extracted_text=extracted_text)
    text = content.get("text", "")
    if not text:
        return _empty_result(
            content.get("method") or "text_extraction",
            "Não consegui extrair texto útil desse documento.",
        )

    structured_receipt = _structured_receipt_result_from_text(
        text,
        extraction_method=str(content.get("method") or "text_extraction"),
        source={"filename": filename, "mimetype": mimetype},
    )
    if structured_receipt:
        return structured_receipt

    unstructured = _parse_unstructured_financial_document(text)
    if unstructured:
        logger.info(
            "[document_understanding] unstructured financial document parsed: %s transactions",
            len(unstructured["transactions"]),
        )
        return _result_from_transactions(
            unstructured["transactions"],
            document_type="unstructured_financial_list",
            extraction_method=f"{content.get('method') or 'text_extraction'}+unstructured",
            confidence=unstructured["confidence"],
            issues=unstructured["issues"],
            source={"filename": filename, "mimetype": mimetype},
            summary=unstructured["summary"],
        )

    llm_result = _llm_understand_financial_document(
        text,
        filename=filename,
        mimetype=mimetype,
        extraction_method=str(content.get("method") or "text_extraction"),
    )
    if llm_result:
        return llm_result

    return {
        "document_type": "unknown",
        "is_financial": False,
        "extraction_method": content.get("method") or "text_extraction",
        "confidence": 0.2,
        "requires_confirmation": False,
        "transactions": [],
        "issues": ["Não consegui estruturar esse documento com segurança."],
        "summary": "Li o documento, mas não identifiquei dados financeiros importáveis com segurança.",
        "source": {"filename": filename, "mimetype": mimetype},
    }


def _structured_receipt_result_from_text(
    text: str,
    *,
    extraction_method: str,
    source: dict[str, Any],
) -> dict[str, Any] | None:
    """Use structured image receipt JSON before generic line parsers see item prices."""
    parsed = _parse_receipt_payload_from_text(text)
    if not parsed:
        return None
    parsed = _normalize_receipt_payload(parsed)

    is_receipt = _parse_bool(parsed.get("is_receipt"))
    document_type = str(parsed.get("document_type") or parsed.get("receipt_type") or "").lower()
    receipt_like = is_receipt or document_type in {"receipt", "invoice", "nfce", "cupom"}
    receipt_items = _normalize_receipt_items(parsed.get("items") or parsed.get("receipt_items") or [])
    total_amount = _parse_amount(
        parsed.get("labeled_total_amount")
        or parsed.get("total_amount")
        or parsed.get("valor_total")
        or parsed.get("total")
        or parsed.get("amount")
    )
    if not receipt_like and not (receipt_items and total_amount):
        return None
    total_amount = _reconcile_receipt_total(total_amount, receipt_items)
    if total_amount is None or total_amount <= 0:
        return None

    normalized_type = "invoice" if document_type == "invoice" else "receipt"
    transactions = _receipt_total_transaction(parsed, [], receipt_items, total_amount)
    return _result_from_transactions(
        transactions,
        document_type=normalized_type,
        extraction_method=f"{extraction_method}+structured_receipt",
        confidence=_clamp_float(parsed.get("confidence"), 0.0, 1.0, default=0.85),
        issues=[],
        source=source,
        is_financial=True,
        summary=str(parsed.get("summary") or ""),
        receipt_items=receipt_items,
        total_amount=total_amount,
        establishment=parsed.get("establishment"),
    )


def _deterministic_statement_result(media: dict[str, Any]) -> dict[str, Any] | None:
    """Use deterministic parsers when they can confidently parse structured files."""
    mimetype = str(media.get("mimetype") or "").lower()
    filename = str(media.get("filename") or "").lower()
    if not (
        mimetype in {"text/csv", "application/csv", "application/ofx", "text/ofx", "application/pdf"}
        or filename.endswith((".csv", ".ofx", ".qfx", ".pdf"))
    ):
        return None

    transactions = _normalize_transactions(parse_statement(media))
    if not transactions:
        return None

    return _result_from_transactions(
        transactions,
        document_type="bank_statement",
        extraction_method="deterministic_statement_parser",
        confidence=0.95,
        issues=[],
        source={
            "filename": media.get("filename"),
            "mimetype": media.get("mimetype"),
        },
    )


def _extract_text_for_understanding(
    media: dict[str, Any],
    *,
    extracted_text: str | None = None,
) -> dict[str, Any]:
    if extracted_text and not _is_truncated(extracted_text):
        return {"text": extracted_text, "method": "multimodal_preextract"}

    mimetype = str(media.get("mimetype") or "").lower()
    filename = str(media.get("filename") or "").lower()
    try:
        raw = base64.b64decode(media.get("data") or "")
    except Exception as exc:
        logger.warning("[document_understanding] decode failed: %s", exc)
        return {"text": "", "method": "decode_error"}

    if mimetype.startswith("image/"):
        return {
            "text": extracted_text or _vision_extract(media, prompt_kind="image_document"),
            "method": "vision_ocr",
        }

    if mimetype == "application/pdf" or filename.endswith(".pdf"):
        text = _extract_pdf_text(raw)
        if text:
            return {"text": text, "method": "pdf_text"}
        return {"text": _vision_extract(media, prompt_kind="scanned_pdf"), "method": "vision_ocr"}

    if _is_docx(mimetype, filename):
        return {"text": extract_docx_text(raw) or "", "method": "docx_text"}

    try:
        return {"text": raw.decode("utf-8", errors="replace").strip(), "method": "plain_text"}
    except Exception:
        return {"text": "", "method": "text_decode_error"}


def _extract_pdf_text(data: bytes) -> str:
    try:
        import PyPDF2

        reader = PyPDF2.PdfReader(io.BytesIO(data))
        parts = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(part for part in parts if part).strip()
    except Exception as exc:
        logger.warning("[document_understanding] pdf text extraction failed: %s", exc)
        return ""


def _parse_unstructured_financial_document(text: str) -> dict[str, Any] | None:
    """Parse loose financial lists such as 'Mercado 240 reais' line by line."""
    transactions: list[dict[str, Any]] = []
    issues: list[str] = []
    candidate_lines = [line.strip() for line in text.splitlines() if line.strip()]

    for index, line in enumerate(candidate_lines):
        parsed = _parse_unstructured_line(line)
        if not parsed and re.fullmatch(r"R\$\s*\d[\d.,]*", line, flags=re.IGNORECASE):
            next_line = candidate_lines[index + 1] if index + 1 < len(candidate_lines) else ""
            if next_line:
                parsed = _parse_unstructured_line(f"{next_line} {line}")
        if parsed:
            transactions.append(parsed)

    if len(transactions) < 2:
        return None

    recurring_count = sum(1 for tx in transactions if tx.get("is_recurring"))
    summary = (
        f"Encontrei {len(transactions)} itens financeiros nesse documento: "
        f"{sum(1 for tx in transactions if tx['type'] == 'INCOME')} receitas e "
        f"{sum(1 for tx in transactions if tx['type'] == 'EXPENSE')} despesas."
    )
    if recurring_count:
        issues.append(
            f"Detectei {recurring_count} item(ns) com indício de recorrência; "
            "vou registrar os lançamentos e marcar isso na prévia."
        )
    return {
        "transactions": transactions,
        "issues": issues,
        "summary": summary,
        "confidence": 0.82 if recurring_count else 0.78,
    }


def _parse_unstructured_line(line: str) -> dict[str, Any] | None:
    if _looks_like_json_kv_line(line):
        return None
    line_norm = _normalize_line(line)
    amount_candidate = _extract_money_candidate(line)
    if not amount_candidate and any(
        token in line_norm for token in ("salario", "recebi", "renda", "ganho", "entrada")
    ):
        income_match = re.search(r"\b(\d{2,6})(?:[.,]\d{1,2})?\b", line)
        if income_match:
            amount_candidate = (income_match.group(0), income_match.span(0))
    if not amount_candidate:
        return None

    amount_text, amount_span = amount_candidate
    amount = _parse_amount(amount_text)
    if amount is None or amount <= 0:
        return None

    raw_description = _clean_transaction_description(line, amount_span)
    raw_description = re.sub(
        r"\btodo\s+dia\s+\d{1,2}\s+(?:do\s+)?m[eê]s\b",
        "",
        raw_description,
        flags=re.IGNORECASE,
    )
    description = _normalize_description(raw_description)
    if (
        not description
        or description.lower().startswith("teste")
        or description == "Transação bancária"
        or _is_receipt_field_label(description)
    ):
        return None

    category = _guess_unstructured_category(description, line_norm)
    is_income = any(token in line_norm for token in ("salario", "recebi", "renda", "ganho", "entrada"))
    is_recurring = any(
        token in line_norm
        for token in ("todo dia", "todo mes", "mensal", "semanal", "anual", "todo ano")
    )
    recurrence_day = _extract_recurrence_day(line_norm) if is_recurring else None

    return {
        "date": datetime.now().date().isoformat(),
        "description": description,
        "amount": round(amount, 2),
        "type": "INCOME" if is_income else "EXPENSE",
        "category": category,
        "confidence": 0.8,
        "raw": line,
        "is_recurring": is_recurring,
        "recurrence_frequency": _infer_recurrence_frequency(line_norm) if is_recurring else None,
        "recurrence_day": recurrence_day,
    }


def _normalize_description(description: str) -> str:
    compact = " ".join(description.split()).strip()
    return compact[:255]


def _normalize_line(text: str) -> str:
    return (
        text.lower()
        .replace("á", "a")
        .replace("à", "a")
        .replace("â", "a")
        .replace("ã", "a")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ô", "o")
        .replace("õ", "o")
        .replace("ú", "u")
        .replace("ç", "c")
    )


def _looks_like_json_kv_line(line: str) -> bool:
    """Avoid treating structured receipt fields like '"price": 10.90' as transactions."""
    stripped = line.strip().strip(",")
    return bool(
        re.match(
            r"""^["']?(?:price|amount|valor|total|total_amount|valor_total|qty|quantity|quantidade|desc|description|name|items?)["']?\s*:""",
            stripped,
            flags=re.IGNORECASE,
        )
    )


def _is_receipt_field_label(description: str) -> bool:
    label = _normalize_line(description).strip(" \"':,.-_")
    return label in {
        "price",
        "amount",
        "valor",
        "total",
        "total amount",
        "valor total",
        "qty",
        "quantity",
        "quantidade",
        "desc",
        "description",
        "name",
        "item",
        "items",
    }


def _guess_unstructured_category(description: str, line_norm: str) -> str:
    if "salario" in line_norm or "recebi" in line_norm:
        return "Receita"
    if any(token in line_norm for token in ("mercado", "pao", "padaria", "acougue", "feira")):
        return "Alimentação"
    if any(token in line_norm for token in ("uber", "99", "taxi", "transporte")):
        return "Transporte"
    return "Outros"


def _infer_recurrence_frequency(line_norm: str) -> str:
    if "semanal" in line_norm:
        return "weekly"
    if "anual" in line_norm or "todo ano" in line_norm:
        return "yearly"
    return "monthly"


def _extract_recurrence_day(line_norm: str) -> int | None:
    match = re.search(r"todo dia\s+(\d{1,2})", line_norm)
    if not match:
        return None
    try:
        day = int(match.group(1))
    except ValueError:
        return None
    return max(1, min(day, 28))


def _vision_extract(media: dict[str, Any], *, prompt_kind: str) -> str:
    """OCR/vision fallback using Gemini (Google Gen AI SDK)."""
    if not settings.GEMINI_API_KEY:
        return ""
    mimetype = str(media.get("mimetype") or "application/octet-stream")
    b64_data = str(media.get("data") or "")
    prompt = (
        "Extraia todo o texto financeiro visível deste arquivo. "
        "Preserve tabelas, datas, descrições, valores, sinais de débito/crédito e totais. "
        "Não invente dados. Responda somente com o texto extraído."
    )
    if prompt_kind == "scanned_pdf":
        prompt += " O arquivo pode ser um PDF escaneado."
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        file_bytes = base64.b64decode(b64_data)

        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=[
                prompt,
                types.Part.from_bytes(data=file_bytes, mime_type=mimetype),
            ],
            config=types.GenerateContentConfig(
                temperature=0,
                max_output_tokens=2048,
            ),
        )
        return response.text.strip() if response.text else ""
    except Exception as exc:
        logger.warning("[document_understanding] vision OCR failed: %s", exc)
        return ""


def _llm_understand_financial_document(
    text: str,
    *,
    filename: str,
    mimetype: str,
    extraction_method: str,
) -> dict[str, Any] | None:
    llm = get_llm(temperature=0.0, request_timeout=20)
    if not llm:
        return None

    clipped = text[:MAX_LLM_TEXT_CHARS]
    messages = [
        SystemMessage(
            content=(
                "Você é um parser financeiro do BagCoin. Converta documentos financeiros "
                "em JSON estrito. Não use markdown. Não invente valores. Se o documento "
                "não for financeiro, retorne transactions vazio e is_financial=false."
            )
        ),
        HumanMessage(
            content=(
                "Analise este documento e responda somente com JSON neste formato:\n"
                "{"
                '"document_type":"bank_statement|credit_card_statement|receipt|invoice|financial_spreadsheet|payment_proof|other|unknown",'
                '"is_financial":true,'
                '"period_start":"YYYY-MM-DD|null",'
                '"period_end":"YYYY-MM-DD|null",'
                '"currency":"BRL",'
                '"confidence":0.0,'
                '"summary":"resumo curto",'
                '"issues":["problemas ou incertezas"],'
                '"establishment":"nome do estabelecimento|null",'
                '"total_amount":123.45,'
                '"transaction_date":"YYYY-MM-DD|null",'
                '"items":[{"desc":"produto","qty":1,"price":12.34}],'
                '"transactions":[{"date":"YYYY-MM-DD|null","description":"texto","amount":123.45,'
                '"type":"EXPENSE|INCOME","category":"categoria","confidence":0.0,"raw":"evidencia"}]'
                "}\n\n"
                "Para receipt/invoice/nota fiscal/cupom: NÃO transforme cada mercadoria em transação. "
                "Use transactions com apenas uma transação no valor total pago. Coloque mercadorias em items.\n\n"
                f"Arquivo: {filename or 'sem nome'}\n"
                f"MIME: {mimetype or 'desconhecido'}\n"
                f"Texto extraído:\n{clipped}"
            )
        ),
    ]
    try:
        response, _ = timed_invoke(llm, messages, operation="document_understanding")
    except Exception as exc:
        logger.warning("[document_understanding] llm failed: %s", exc)
        return None

    parsed = _parse_json_object(str(getattr(response, "content", "") or response))
    if not parsed:
        return None

    transactions = _normalize_transactions(parsed.get("transactions") or [])
    document_type = str(parsed.get("document_type") or "unknown")
    receipt_items = _normalize_receipt_items(parsed.get("items") or parsed.get("receipt_items") or [])
    total_amount = _parse_amount(
        parsed.get("labeled_total_amount")
        or parsed.get("total_amount")
        or parsed.get("valor_total")
    )
    total_amount = _reconcile_receipt_total(total_amount, receipt_items)
    if document_type in {"receipt", "invoice"} and (total_amount or receipt_items):
        transactions = _receipt_total_transaction(
            parsed,
            transactions,
            receipt_items,
            total_amount,
        )
    is_financial = _parse_bool(parsed.get("is_financial")) or bool(transactions)
    confidence = _clamp_float(parsed.get("confidence"), 0.0, 1.0, default=0.4)
    if transactions:
        confidence = max(confidence, min(tx.get("confidence", 0.4) for tx in transactions))
    issues = [str(item) for item in parsed.get("issues") or [] if str(item).strip()]
    if is_financial and not transactions:
        issues.append("Documento financeiro sem transações importáveis.")

    return _result_from_transactions(
        transactions,
        document_type=document_type,
        extraction_method=f"{extraction_method}+llm",
        confidence=confidence,
        issues=issues,
        source={"filename": filename, "mimetype": mimetype},
        is_financial=is_financial and document_type != "other",
        summary=str(parsed.get("summary") or ""),
        period_start=parsed.get("period_start"),
        period_end=parsed.get("period_end"),
        receipt_items=receipt_items,
        total_amount=total_amount,
        establishment=parsed.get("establishment"),
    )


def _result_from_transactions(
    transactions: list[dict[str, Any]],
    *,
    document_type: str,
    extraction_method: str,
    confidence: float,
    issues: list[str],
    source: dict[str, Any],
    is_financial: bool = True,
    summary: str = "",
    period_start: Any = None,
    period_end: Any = None,
    receipt_items: list[dict[str, Any]] | None = None,
    total_amount: float | None = None,
    establishment: Any = None,
) -> dict[str, Any]:
    incomes = [tx for tx in transactions if tx.get("type") == "INCOME"]
    expenses = [tx for tx in transactions if tx.get("type") == "EXPENSE"]
    total_income = sum(float(tx.get("amount") or 0) for tx in incomes)
    total_expense = sum(float(tx.get("amount") or 0) for tx in expenses)
    if not summary:
        summary = (
            f"{len(transactions)} transações encontradas: "
            f"{len(incomes)} receitas e {len(expenses)} despesas."
        )
    result = {
        "document_type": document_type,
        "is_financial": is_financial,
        "extraction_method": extraction_method,
        "confidence": _clamp_float(confidence, 0.0, 1.0, default=0.5),
        "requires_confirmation": bool(transactions),
        "transactions": transactions,
        "issues": issues,
        "summary": summary,
        "period_start": _normalize_date(period_start),
        "period_end": _normalize_date(period_end),
        "totals": {
            "income": round(total_income, 2),
            "expense": round(total_expense, 2),
            "transactions": len(transactions),
        },
        "source": source,
    }
    if receipt_items:
        result["receipt_items"] = receipt_items
    if total_amount:
        result["total_amount"] = round(float(total_amount), 2)
    if establishment:
        result["establishment"] = str(establishment).strip()
    return result


def _normalize_receipt_items(items: list[Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        description = str(
            item.get("desc")
            or item.get("description")
            or item.get("name")
            or item.get("produto")
            or item.get("nome")
            or ""
        ).strip()
        qty = _parse_amount(item.get("qty") or item.get("quantity") or item.get("quantidade")) or 1
        price = _parse_amount(
            item.get("price")
            or item.get("amount")
            or item.get("valor")
            or item.get("valor_total")
        )
        if price is None:
            unit_price = _parse_amount(item.get("valor_unitario"))
            if unit_price is not None:
                price = unit_price * qty
        if not description or price is None or price <= 0:
            continue
        normalized.append(
            {
                "description": description[:120],
                "quantity": round(float(qty), 3),
                "amount": round(float(price), 2),
            }
        )
    return normalized


def _receipt_total_transaction(
    parsed: dict[str, Any],
    transactions: list[dict[str, Any]],
    receipt_items: list[dict[str, Any]],
    total_amount: float | None,
) -> list[dict[str, Any]]:
    total_amount = _reconcile_receipt_total(total_amount, receipt_items)
    if total_amount is None and transactions:
        total_amount = sum(float(tx["amount"]) for tx in transactions if tx.get("type") == "EXPENSE")
    if total_amount is None or total_amount <= 0:
        return transactions

    establishment = str(parsed.get("establishment") or parsed.get("estabelecimento") or "").strip()
    tx_type = _receipt_transaction_type(parsed)
    if parsed.get("needs_type_confirmation") and tx_type is None:
        return transactions
    tx_type = tx_type or "EXPENSE"
    default_description = (
        f"Nota fiscal {establishment}"
        if tx_type == "EXPENSE" and establishment
        else f"Comprovante {establishment}"
        if establishment
        else "Comprovante"
    )
    description = str(parsed.get("description") or parsed.get("descricao") or default_description).strip()
    date = _normalize_date(parsed.get("transaction_date") or parsed.get("date") or parsed.get("data"))
    raw_items = "; ".join(
        f"{item['description']} R$ {float(item['amount']):.2f}" for item in receipt_items[:20]
    )
    category = str(parsed.get("category") or parsed.get("categoria") or "Outros").strip() or "Outros"
    try:
        from app.core.financial_categories import resolve_default_category_name

        category = resolve_default_category_name(category)
    except Exception:
        pass
    return [
        {
            "date": date or datetime.now().date().isoformat(),
            "description": description[:255],
            "amount": round(float(total_amount), 2),
            "type": tx_type,
            "category": category,
            "confidence": _clamp_float(parsed.get("confidence"), 0.0, 1.0, default=0.75),
            "raw": raw_items or str(parsed.get("raw_text") or description)[:1000],
        }
    ]


def _receipt_items_total(receipt_items: list[dict[str, Any]]) -> float | None:
    if not receipt_items:
        return None
    total = sum(float(item.get("amount") or 0) for item in receipt_items)
    return round(total, 2) if total > 0 else None


def _reconcile_receipt_total(
    total_amount: float | None,
    receipt_items: list[dict[str, Any]],
) -> float | None:
    """Prefer deterministic item-line totals when the model confuses payment amount with receipt total."""
    items_total = _receipt_items_total(receipt_items)
    if items_total is None:
        return total_amount
    if total_amount is None or total_amount <= 0:
        return items_total
    return round(float(total_amount), 2)


def _normalize_transactions(items: list[Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    seen: set[tuple[str, str, float]] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        amount = _parse_amount(item.get("amount"))
        if amount is None or amount == 0:
            continue
        tx_type = str(item.get("type") or "").upper()
        if tx_type not in {"EXPENSE", "INCOME"}:
            tx_type = "EXPENSE" if amount < 0 else "INCOME"
        amount = abs(amount)
        description = str(item.get("description") or "").strip()
        if not description:
            continue
        date = _normalize_date(item.get("date"))
        key = (date or "", description.lower(), round(amount, 2))
        if key in seen:
            continue
        seen.add(key)
        normalized.append(
            {
                "date": date or datetime.now().date().isoformat(),
                "description": description[:255],
                "amount": round(float(amount), 2),
                "type": tx_type,
                "category": str(item.get("category") or "Outros").strip() or "Outros",
                "confidence": _clamp_float(item.get("confidence"), 0.0, 1.0, default=0.6),
                "raw": str(item.get("raw") or item.get("raw_evidence") or description)[:1000],
            }
        )
    return normalized


def _parse_amount(value: Any) -> float | None:
    if isinstance(value, int | float):
        return float(value)
    text = str(value or "").strip()
    if not text:
        return None
    text = text.replace("R$", "").replace(" ", "")
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    else:
        text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def _normalize_date(value: Any) -> str | None:
    if not value:
        return None
    text = str(value).strip()
    if text.lower() in {"null", "none", "desconhecido"}:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _clamp_float(value: Any, minimum: float, maximum: float, *, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, parsed))


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "sim", "yes", "1"}
    return bool(value)


def _parse_json_object(text: str) -> dict[str, Any] | None:
    content = (text or "").strip()
    if "```json" in content:
        content = content.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in content:
        content = content.split("```", 1)[1].split("```", 1)[0].strip()
    if not content.startswith("{"):
        start = content.find("{")
        end = content.rfind("}")
        if start >= 0 and end > start:
            content = content[start : end + 1]
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _parse_receipt_payload_from_text(text: str) -> dict[str, Any] | None:
    """Parse structured or semi-structured receipt payloads from vision output."""
    parsed = _parse_json_object(text)
    if parsed:
        return _normalize_receipt_payload(parsed)

    items = _extract_receipt_items_from_loose_text(text)
    total = _extract_receipt_total_from_loose_text(text)
    text_norm = _normalize_line(text)
    receipt_markers = (
        "cupom",
        "nota fiscal",
        "nfce",
        "nfc-e",
        "recibo",
        "total_amount",
        "valor_total",
        '"price"',
        "'price'",
    )
    if not items or not any(marker in text_norm for marker in receipt_markers):
        return None

    return {
        "is_receipt": True,
        "document_type": "receipt",
        "items": items,
        "total_amount": total if total is not None else sum(float(item["price"]) for item in items),
    }


def _normalize_receipt_payload(parsed: dict[str, Any]) -> dict[str, Any]:
    """Accept BagCoin/Gemini and external OCR receipt schemas."""
    data = parsed.get("dados_extraidos")
    if isinstance(data, dict):
        confidence = data.get("confianca")
        normalized_type = _receipt_transaction_type(data)
        return {
            **parsed,
            "is_receipt": True,
            "document_type": "receipt",
            "receipt_type": parsed.get("receipt_type") or "nfce",
            "transaction_type": normalized_type,
            "needs_type_confirmation": bool(data.get("precisa_confirmar_tipo"))
            or ("tipo" in data and normalized_type is None),
            "establishment": data.get("estabelecimento"),
            "total_amount": data.get("valor_total"),
            "transaction_date": data.get("data"),
            "category": data.get("categoria"),
            "description": data.get("descricao"),
            "items": data.get("itens") or [],
            "confidence": _receipt_confidence_value(confidence),
            "raw_text": parsed.get("texto_ocr") or data.get("observacoes"),
        }
    if "itens" in parsed and "items" not in parsed:
        parsed = {**parsed, "items": parsed.get("itens")}
    if "valor_total" in parsed and "total_amount" not in parsed:
        parsed = {**parsed, "total_amount": parsed.get("valor_total")}
    if "estabelecimento" in parsed and "establishment" not in parsed:
        parsed = {**parsed, "establishment": parsed.get("estabelecimento")}
    if "data" in parsed and "transaction_date" not in parsed:
        parsed = {**parsed, "transaction_date": parsed.get("data")}
    if "categoria" in parsed and "category" not in parsed:
        parsed = {**parsed, "category": parsed.get("categoria")}
    if "descricao" in parsed and "description" not in parsed:
        parsed = {**parsed, "description": parsed.get("descricao")}
    normalized_type = _receipt_transaction_type(parsed)
    if normalized_type or "transaction_type" not in parsed:
        parsed = {**parsed, "transaction_type": normalized_type}
    if "precisa_confirmar_tipo" in parsed or "needs_type_confirmation" not in parsed:
        parsed = {
            **parsed,
            "needs_type_confirmation": bool(parsed.get("precisa_confirmar_tipo"))
            or ("tipo" in parsed and normalized_type is None),
        }
    return parsed


def _receipt_transaction_type(parsed: dict[str, Any]) -> str | None:
    raw_type = parsed.get("tipo") or parsed.get("transaction_type") or parsed.get("type")
    if raw_type is None:
        return None
    text = _normalize_line(str(raw_type))
    if text in {"despesa", "expense", "saida", "gasto", "pagamento", "paguei"}:
        return "EXPENSE"
    if text in {"receita", "income", "entrada", "recebimento", "recebi", "deposito"}:
        return "INCOME"
    return None


def _receipt_confidence_value(value: Any) -> float:
    if isinstance(value, int | float):
        return _clamp_float(value, 0.0, 1.0, default=0.85)
    normalized = _normalize_line(str(value or ""))
    if normalized in {"alta", "alto", "high"}:
        return 0.9
    if normalized in {"media", "medio", "medium"}:
        return 0.75
    if normalized in {"baixa", "baixo", "low"}:
        return 0.55
    return 0.85


def _extract_receipt_items_from_loose_text(text: str) -> list[dict[str, Any]]:
    """Recover item descriptions and prices from invalid/prettified JSON text."""
    items: list[dict[str, Any]] = []
    pattern = re.compile(
        r"""(?P<desc_key>["']?(?:desc|description|name|produto)["']?\s*:\s*["'](?P<desc>[^"']{2,120})["'])"""
        r""".{0,240}?["']?(?:price|amount|valor)["']?\s*:\s*["']?(?:R\$\s*)?(?P<price>\d{1,5}(?:[.,]\d{1,2})?)""",
        flags=re.IGNORECASE | re.DOTALL,
    )
    for match in pattern.finditer(text):
        desc = " ".join(match.group("desc").split()).strip()
        price = _parse_amount(match.group("price"))
        if desc and price and price > 0:
            items.append({"desc": desc, "price": round(float(price), 2)})

    if items:
        return items

    # Fallback for line pairs: product name on one line, price on the next.
    lines = [line.strip().strip(",") for line in text.splitlines() if line.strip()]
    pending_desc: str | None = None
    for line in lines:
        desc_match = re.search(
            r"""["']?(?:desc|description|name|produto)["']?\s*:\s*["'](?P<desc>[^"']{2,120})["']""",
            line,
            flags=re.IGNORECASE,
        )
        if desc_match:
            pending_desc = " ".join(desc_match.group("desc").split()).strip()
            continue
        price_match = re.search(
            r"""["']?(?:price|amount|valor)["']?\s*:\s*["']?(?:R\$\s*)?(?P<price>\d{1,5}(?:[.,]\d{1,2})?)""",
            line,
            flags=re.IGNORECASE,
        )
        if pending_desc and price_match:
            price = _parse_amount(price_match.group("price"))
            if price and price > 0:
                items.append({"desc": pending_desc, "price": round(float(price), 2)})
            pending_desc = None
    return items


def _extract_receipt_total_from_loose_text(text: str) -> float | None:
    total_patterns = (
        r"""["']?total_amount["']?\s*:\s*["']?(?:R\$\s*)?(?P<amount>\d{1,7}(?:[.,]\d{1,2})?)""",
        r"""["']?valor_total["']?\s*:\s*["']?(?:R\$\s*)?(?P<amount>\d{1,7}(?:[.,]\d{1,2})?)""",
        r"""\bvalor\s+total\b\s*:?\s*(?:R\$\s*)?(?P<amount>\d{1,7}(?:[.,]\d{1,2})?)""",
        r"""\btotal\b\s*:?\s*(?:R\$\s*)?(?P<amount>\d{1,7}(?:[.,]\d{1,2})?)""",
    )
    for pattern in total_patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue
        amount = _parse_amount(match.group("amount"))
        if amount and amount > 0:
            return round(float(amount), 2)
    return None


def _is_docx(mimetype: str, filename: str) -> bool:
    return (
        "wordprocessingml.document" in mimetype
        or mimetype == "application/msword"
        or filename.endswith(".docx")
    )


def _is_truncated(text: str) -> bool:
    return "...[texto truncado]" in text


def _empty_result(method: str, message: str) -> dict[str, Any]:
    return {
        "document_type": "unknown",
        "is_financial": False,
        "extraction_method": method,
        "confidence": 0.0,
        "requires_confirmation": False,
        "transactions": [],
        "issues": [message],
        "summary": message,
        "source": {},
    }
