"""Normalization agent — extract structured transaction data from text.

Uses regex first, then LLM fallback for ambiguous cases.
"""

import concurrent.futures
import logging
import re
import time
import unicodedata
from datetime import date, datetime
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser

from app.core.config import settings
from app.core.financial_categories import (
    DEFAULT_FINANCIAL_CATEGORIES,
    normalize_category_key,
    resolve_default_category_name,
)
from app.services.llm_service import get_llm, timed_invoke

logger = logging.getLogger(__name__)

# Categories and descriptions
CATEGORIES = [category.name for category in DEFAULT_FINANCIAL_CATEGORIES]

CATEGORY_KEYWORDS = {
    "Alimentação": [
        "mercado",
        "supermercado",
        "padaria",
        "feira",
        "hortifruti",
        "lanches",
        "pao",
        "leite",
        "ovos",
        "arroz",
        "feijao",
    ],
    "Restaurante": [
        "restaurante",
        "bar",
        "cafeteria",
        "pastelaria",
        "lanchonete",
        "almoco",
        "jantar",
        "pizza",
        "hamburguer",
        "lanche",
    ],
    "Delivery": ["ifood", "uber eats", "rappi", "delivery"],
    "Transporte": [
        "uber",
        "99",
        "taxi",
        "gasolina",
        "combustivel",
        "onibus",
        "metro",
        "estacionamento",
        "pedagio",
        "passagem",
        "moto",
    ],
    "Moradia": ["aluguel", "condominio", "financiamento", "reforma", "manutencao"],
    "Luz": ["energia", "eletricidade", "conta de luz"],
    "Água": ["agua", "conta de agua", "esgoto"],
    "Internet": ["internet", "wifi", "banda larga", "provedor", "fibra"],
    "Telefone": ["celular", "plano movel", "recarga", "tim", "vivo", "claro", "oi"],
    "Saúde": [
        "farmacia",
        "remedio",
        "medico",
        "dentista",
        "plano de saude",
        "exame",
        "consulta",
        "hospital",
        "psicologo",
    ],
    "Educação": [
        "curso",
        "livro",
        "material escolar",
        "faculdade",
        "universidade",
        "mensalidade",
        "idioma",
    ],
    "Lazer": ["cinema", "teatro", "show", "festa", "bar", "hobby", "streaming", "musica", "jogo"],
    "Viagem": ["passagem", "hotel", "hospedagem", "passeio", "turismo"],
    "Vestuário": [
        "roupa",
        "calcado",
        "acessorio",
        "loja",
        "moda",
        "shopping",
        "camiseta",
        "calca",
        "sapato",
    ],
    "Beleza": ["salao", "barbearia", "manicure", "estetica", "cosmetico", "perfumaria"],
    "Tecnologia": ["eletronico", "computador", "tablet", "software", "app", "game", "console"],
    "Assinaturas": [
        "netflix",
        "spotify",
        "youtube premium",
        "gym",
        "clube",
        "revista",
        "jornal",
        "saas",
        "mensalidade",
    ],
    "Pet": ["racao", "veterinario", "petshop", "remedio pet", "banho e tosa"],
    "Doação": ["caridade", "igreja", "ong", "vaquinha", "doacao"],
    "Impostos": ["irpf", "iptu", "ipva", "darf", "gps", "taxas governo"],
    "Receita": [
        "salario",
        "freelance",
        "renda extra",
        "investimento",
        "bonus",
        "comissao",
        "aluguel recebido",
        "mesada",
        "presente",
        "pai",
        "mae",
        "pix",
        "transferencia",
        "deposito",
    ],
}

for category in DEFAULT_FINANCIAL_CATEGORIES:
    CATEGORY_KEYWORDS.setdefault(category.name, [])
    CATEGORY_KEYWORDS[category.name].extend(category.aliases)


def _parse_flexible_date(date_str: str) -> date | None:
    """Try to parse date in multiple formats."""
    if not date_str:
        return None
    formats = ["%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y", "%m/%d/%Y"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None


def _norm(s: str) -> str:
    return unicodedata.normalize("NFKD", s.lower()).encode("ASCII", "ignore").decode("ASCII")


def _suggest_category(text: str, user_cats: list[str] | None = None) -> str:
    """Suggest category based on user categories first, then default keywords."""
    text_norm = _norm(text)

    # 1. User-created categories take priority (substring match)
    for name in user_cats or []:
        if _norm(name) in text_norm or text_norm in _norm(name):
            return name

    # 2. Default keyword scoring
    scores: dict[str, int] = {}
    for cat, words in CATEGORY_KEYWORDS.items():
        scores[cat] = sum(1 for word in words if word in text_norm)

    best = max(scores, key=scores.get)
    return resolve_default_category_name(best) if scores[best] > 0 else "Outros"


# Words that must NOT appear in a clean description
_DESC_NOISE = re.compile(
    r"\b(gastei|paguei|comprei|recebi|ganhei|transferi|enviei|mandei|fiz|despesa|receita"
    r"|pix|boleto|salario|salário|mensalmente|semanalmente|anualmente|todo\s+m[eê]s"
    r"|todos?\s+os?\s+meses|fixo|recorrente|reais|real|pila|conto|pau)\b",
    re.IGNORECASE,
)


def _clean_description(raw: str) -> str:
    """Return a short label (2-4 words) stripped of amounts, verbs and period words."""
    txt = re.sub(r"R?\$?\s*\d{1,3}(?:[.,]\d{3})*[.,]\d{1,2}|\d+(?:[.,]\d{1,2})?", "", raw)
    txt = _DESC_NOISE.sub("", txt)
    txt = re.sub(r"\s+", " ", txt).strip(" ,.-")
    # Truncate to 60 chars and capitalise
    return txt[:60].capitalize() or "Sem descrição"


def _load_user_categories(phone_number: str) -> list[str]:
    try:
        from app.agents.persistence import list_categories

        return [c["name"] for c in list_categories(phone_number)]
    except Exception:
        return []


def _load_history(phone_number: str) -> str:
    try:
        from app.agents.persistence import get_conversation_history

        return get_conversation_history(phone_number, limit=6)
    except Exception:
        return ""


def _regex_extract(message: str, user_cats: list[str] | None = None) -> dict[str, Any]:
    """Extract transaction data using deterministic local rules only."""
    msg_lower = message.lower()

    extracted = {
        "type": "EXPENSE",
        "amount": None,
        "currency": "BRL",
        "category": None,
        "description": None,
        "date": None,
        "confidence": 0.5,
        "raw_text": message,
        "is_recurring": False,
        "recurrence_frequency": None,
    }

    # 1. Regex for amount
    amount_match = re.search(
        r"R?\$\s*(\d{1,3}(?:[.,]\d{3})*[.,]\d{1,2}|\d+(?:[.,]\d{1,2})?)", message
    )
    if not amount_match:
        amount_match = re.search(r"(?:^|\s)(\d+(?:[.,]\d{1,2})?)(?:\s|$)", message)

    if amount_match:
        try:
            amount_str = amount_match.group(1)
            has_dot = "." in amount_str
            has_comma = "," in amount_str

            if has_dot and has_comma:
                last_sep_pos = max(amount_str.rfind("."), amount_str.rfind(","))
                before = amount_str[:last_sep_pos].replace(".", "").replace(",", "")
                after = amount_str[last_sep_pos + 1 :]
                amount_str = before + "." + after
            elif has_dot:
                dot_pos = amount_str.rfind(".")
                if dot_pos == len(amount_str) - 3 and len(amount_str) <= 5:
                    pass  # already decimal
                else:
                    amount_str = amount_str.replace(".", "")
            elif has_comma:
                amount_str = amount_str.replace(",", ".")

            if amount_str.count(".") > 1:
                parts = amount_str.split(".")
                amount_str = "".join(parts[:-1]) + "." + parts[-1]
            extracted["amount"] = float(amount_str)
            extracted["confidence"] = 0.8
        except ValueError:
            pass

    # 2. Type detection
    income_signals = [
        "recebi",
        "ganhei",
        "salário",
        "salario",
        "renda",
        "entrada",
        "pagamento recebido",
        "me mandaram",
        "me mandou",
        "me enviaram",
        "depositaram",
        "caiu",
        "mesada",
        "aluguel recebido",
    ]
    transfer_signals = ["transferi", "enviei", "mandei", "fiz pix", "passei para", "transferência"]

    if any(w in msg_lower for w in income_signals):
        extracted["type"] = "INCOME"
    elif any(w in msg_lower for w in transfer_signals):
        extracted["type"] = "TRANSFER"
    elif "pix" in msg_lower:
        if any(w in msg_lower for w in ["recebi", "me mandaram", "chegou", "depositaram"]):
            extracted["type"] = "INCOME"

    # 3. Recurrence detection (Bug 1 fix) — fast regex, no LLM needed
    _RECURRING = re.compile(
        r"\b(mensalmente|todo\s+m[eê]s|todos?\s+os?\s+meses|fixo|recorrente"
        r"|semanalmente|toda\s+semana|anualmente|todo\s+ano)\b",
        re.IGNORECASE,
    )
    _FREQ_MAP = {
        "semanalmente": "weekly",
        "toda semana": "weekly",
        "anualmente": "yearly",
        "todo ano": "yearly",
    }
    rec_match = _RECURRING.search(msg_lower)
    if rec_match:
        extracted["is_recurring"] = True
        token = rec_match.group(1).lower()
        extracted["recurrence_frequency"] = _FREQ_MAP.get(token, "monthly")

    # 4. Extract description
    desc_patterns = [
        r"(?:gastei|paguei|comprei|gasto|despesa)\s+(?:R?\$\s*)?\d+(?:[.,]\d{1,2})?\s+(?:em|no|na|de)\s+(.+)$",
        r"(?:recebi|ganhei)\s+(?:R?\$\s*)?\d+(?:[.,]\d{1,2})?\s+(?:de|do|da)\s+(.+)$",
        r"^\d+(?:[.,]\d{1,2})?\s+(?:em|de|no|na)\s+(.+)$",
        r"^([a-zà-ú\s]+)\s+\d+(?:[.,]\d{1,2})?$",
    ]
    for pattern in desc_patterns:
        m = re.search(pattern, msg_lower, re.IGNORECASE)
        if m:
            extracted["description"] = _clean_description(m.group(1))
            break

    if not extracted["description"]:
        clean = re.sub(r"R?\$\s*\d+(?:[.,]\d{1,2})?", "", msg_lower)
        clean = _DESC_NOISE.sub("", clean).strip()
        if clean and len(clean) > 2:
            extracted["description"] = _clean_description(clean)

    # 5. Extract date
    date_match = re.search(r"\b(\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2}|\d{2}-\d{2}-\d{4})\b", message)
    if date_match:
        parsed = _parse_flexible_date(date_match.group(1))
        if parsed:
            extracted["date"] = parsed.strftime("%Y-%m-%d")

    # 6. Category by user cats + keywords (fast fallback)
    if not extracted["category"]:
        target_text = extracted["description"] or message
        extracted["category"] = _suggest_category(target_text, user_cats)
        if extracted["category"] and extracted["category"] != "Outros":
            extracted["confidence"] = max(extracted["confidence"], 0.75)

    return extracted


def _llm_extract_with_timeout(
    message: str,
    user_cats: list[str],
    history: str,
    timeout: float,
) -> dict[str, Any]:
    """Extract transaction data using LLM with an explicit client timeout."""
    try:
        llm = get_llm(temperature=0.1, request_timeout=timeout)
        if not llm:
            return {}

        from app.agents.prompts.extract_transaction import build_extract_transaction_prompt

        history_context = f"\n\nContexto da conversa recente:\n{history}" if history else ""
        all_cats = list(dict.fromkeys(user_cats + CATEGORIES))
        system_prompt = build_extract_transaction_prompt(
            categories=", ".join(all_cats),
            history=history_context,
        )
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Mensagem: {message}"),
        ]
        response, _ = timed_invoke(llm, messages, operation="extract_transaction")
        return JsonOutputParser().parse(response.content)
    except Exception as exc:
        logger.warning(f"[extract_hybrid] LLM failed: {exc}")
        return {}


def _valid_category(category: str | None, user_cats: list[str]) -> bool:
    if not category:
        return False
    valid = {normalize_category_key(cat) for cat in user_cats + CATEGORIES}
    return normalize_category_key(category) in valid


def _resolve_category(category: str | None, user_cats: list[str]) -> str:
    if not category:
        return "Outros"
    category_key = normalize_category_key(category)
    for user_cat in user_cats:
        if normalize_category_key(user_cat) == category_key:
            return user_cat
    return resolve_default_category_name(category)


def _merge_results(
    regex_result: dict[str, Any],
    llm_result: dict[str, Any],
    user_cats: list[str],
) -> dict[str, Any]:
    """Merge regex and LLM extraction results field by field."""
    merged = dict(regex_result)

    regex_amount = regex_result.get("amount")
    llm_amount = llm_result.get("amount")
    if regex_amount is None and llm_amount is not None:
        merged["amount"] = llm_amount
    elif regex_amount is not None and llm_amount is not None:
        try:
            if abs(float(regex_amount) - float(llm_amount)) > 1:
                logger.warning(
                    "[extract_hybrid] amount conflict regex=%s llm=%s, using regex",
                    regex_amount,
                    llm_amount,
                )
        except (TypeError, ValueError):
            pass

    if llm_result.get("type"):
        merged["type"] = llm_result["type"]

    llm_category = llm_result.get("category")
    regex_category = regex_result.get("category")
    if _valid_category(llm_category, user_cats):
        merged["category"] = _resolve_category(llm_category, user_cats)
    elif regex_category:
        merged["category"] = _resolve_category(regex_category, user_cats)
    else:
        merged["category"] = "Outros"

    if llm_result.get("description"):
        merged["description"] = _clean_description(str(llm_result["description"]))
    elif regex_result.get("description"):
        merged["description"] = _clean_description(str(regex_result["description"]))

    if not regex_result.get("date") and llm_result.get("date"):
        merged["date"] = llm_result["date"]

    merged["is_recurring"] = bool(
        regex_result.get("is_recurring") or llm_result.get("is_recurring")
    )
    if regex_result.get("recurrence_frequency"):
        merged["recurrence_frequency"] = regex_result["recurrence_frequency"]
    elif llm_result.get("recurrence_frequency"):
        merged["recurrence_frequency"] = llm_result["recurrence_frequency"]

    if llm_result.get("confidence") is not None:
        merged["confidence"] = llm_result["confidence"]

    return merged


ESTABLISHMENT_CATEGORY_HINTS: dict[str, tuple[str, ...]] = {
    "Supermercado": (
        "mercado",
        "supermercado",
        "extra",
        "carrefour",
        "dia",
        "atacadao",
        "assai",
        "hortifruti",
        "sams club",
        "makro",
    ),
    "Farmácia": (
        "farmacia",
        "drogaria",
        "drogasil",
        "raia",
        "pacheco",
        "ultrafarma",
        "araujo",
        "nissei",
    ),
    "Restaurantes": (
        "restaurante",
        "bar",
        "cafeteria",
        "cafe ",
        "pizzaria",
        "lanchonete",
        "cantina",
        "churrascaria",
        "hamburgueria",
    ),
    "Delivery": ("ifood", "rappi", "uber eats", "99food", "loggi"),
    "Transporte": ("uber", "99 pop", "99pop", "metro ", "cptm", "cet "),
    "Combustível": (
        "posto",
        "shell",
        "ipiranga",
        "petrobras",
        "br mania",
        "ale combustiveis",
        "raizen",
    ),
    "Vestuário": (
        "loja",
        "riachuelo",
        "renner",
        "c&a",
        "marisa",
        "zara",
        "lebes",
        "pernambucanas",
    ),
    "Saúde": (
        "clinica",
        "hospital",
        "laboratorio",
        "fleury",
        "sabin",
        "hapvida",
        "unimed",
        "amil",
    ),
    "Lazer": (
        "cinemark",
        "cinepolis",
        "kinoplex",
        "uci cinemas",
        "netflix",
        "spotify",
        "disney",
        "hbo",
    ),
    "Tecnologia": (
        "kabum",
        "magazine luiza",
        "americanas",
        "submarino",
        "fast shop",
        "casas bahia",
        "ponto frio",
    ),
}


def _category_from_establishment(name: str | None) -> str:
    """Guess a default category from an establishment name."""
    if not name:
        return "Outros"
    key = normalize_category_key(name)
    best_score = 0
    best_category = "Outros"
    for category, fragments in ESTABLISHMENT_CATEGORY_HINTS.items():
        score = sum(1 for fragment in fragments if fragment in key)
        if score > best_score:
            best_score = score
            best_category = category
    return best_category


def _extract_from_image_receipt(state: dict[str, Any]) -> dict[str, Any] | None:
    img = state.get("context", {}).get("image_structured")
    if not img or not img.get("is_receipt") or not img.get("total_amount"):
        return None
    try:
        from app.agents.document_understanding import _normalize_receipt_payload
        from app.agents.tools.documents import _receipt_category, _receipt_transaction_type

        img = _normalize_receipt_payload(img)
        tx_type = _receipt_transaction_type(img) or "EXPENSE"
        category = _receipt_category(img)
    except Exception:
        tx_type = "EXPENSE"
        category = _category_from_establishment(img.get("establishment"))
    establishment = img.get("establishment") or "Comprovante"
    try:
        amount = float(img["total_amount"])
    except (TypeError, ValueError):
        return None
    return {
        "type": tx_type,
        "amount": amount,
        "currency": "BRL",
        "category": category,
        "description": str(img.get("description") or establishment),
        "date": img.get("transaction_date"),
        "confidence": float(img.get("confidence", 0.85) or 0.85),
        "raw_text": img.get("raw_text", state.get("message", "")),
        "is_recurring": False,
        "recurrence_frequency": None,
        "source_hint": "image_receipt",
    }


def extract_transaction(state: dict[str, Any]) -> dict[str, Any]:
    """Extract financial information from user message using regex + LLM merge."""
    start_time = time.time()
    image_extracted = _extract_from_image_receipt(state)
    if image_extracted:
        state["extracted_data"] = image_extracted
        logger.info(
            "[image_receipt] extracted amount=%s category=%s",
            image_extracted["amount"],
            image_extracted["category"],
        )
        return state

    message = state.get("message", "")
    phone_number = state.get("phone_number", "")
    user_cats = _load_user_categories(phone_number)
    history = _load_history(phone_number)
    timeout = settings.LLM_EXTRACT_TIMEOUT

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        llm_future = executor.submit(
            _llm_extract_with_timeout,
            message,
            user_cats,
            history,
            timeout,
        )
        regex_result = _regex_extract(message, user_cats)
        try:
            llm_result = llm_future.result(timeout=timeout + 0.5)
        except concurrent.futures.TimeoutError:
            llm_result = {}
            logger.warning("[extract_hybrid] thread timeout, using regex only")

    extracted = _merge_results(regex_result, llm_result, user_cats)
    elapsed = (time.time() - start_time) * 1000
    logger.info(
        "[extract_hybrid] %.0fms | regex_amount=%s llm_amount=%s merged=%s | category=%s",
        elapsed,
        regex_result.get("amount"),
        llm_result.get("amount"),
        extracted.get("amount"),
        extracted.get("category"),
    )
    state["extracted_data"] = extracted
    return state
