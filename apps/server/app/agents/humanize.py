"""Optional response humanization with safety guards."""

import logging
import re
import unicodedata
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.prompts.humanize import HUMANIZE_SYSTEM_PROMPT, build_humanize_prompt
from app.core.config import settings
from app.schemas.enums import IntentType
from app.services.llm_service import get_llm, timed_invoke

logger = logging.getLogger(__name__)

HUMANIZE_ALLOWED_INTENTS: frozenset[str] = frozenset({
    IntentType.REGISTER_EXPENSE.value,
    IntentType.REGISTER_INCOME.value,
    IntentType.CONTRIBUTE_GOAL.value,
    IntentType.CREATE_BUDGET.value,
    IntentType.CREATE_GOAL.value,
})

_MONEY_RE = re.compile(r"R\$\s*[\d.,]+")


def should_humanize(state: dict[str, Any]) -> bool:
    """Return whether this response is eligible for LLM humanization."""
    if not settings.HUMANIZE_RESPONSES:
        logger.info("[humanize] skipped (disabled)")
        return False
    if state.get("error"):
        logger.info("[humanize] skipped (error)")
        return False
    if state.get("context", {}).get("skip_humanize"):
        logger.info("[humanize] skipped (context)")
        return False

    allowed = HUMANIZE_ALLOWED_INTENTS | set(settings.HUMANIZE_ALLOWED_INTENTS_EXTRA)
    intent = state.get("intent")
    if intent not in allowed:
        logger.info("[humanize] skipped (intent not allowed)")
        return False
    return True


def humanize_safely(raw: str, state: dict[str, Any]) -> str:
    """Return humanized text only if all guards pass; otherwise return raw."""
    if not raw:
        return raw

    candidate = _call_llm(raw)
    if not candidate:
        return raw
    if not _preserve_money_values(raw, candidate):
        logger.warning("[humanize] money values changed, keeping raw")
        return raw
    if not _preserve_category_names(raw, candidate, state):
        logger.warning("[humanize] category names changed, keeping raw")
        return raw
    if not (10 <= len(candidate) <= settings.HUMANIZE_MAX_CHARS):
        logger.warning("[humanize] invalid length, keeping raw")
        return raw

    logger.info("[humanize] applied")
    return candidate


def _call_llm(raw: str) -> str:
    llm = get_llm(temperature=0.3)
    if not llm:
        return ""
    try:
        messages = [
            SystemMessage(content=HUMANIZE_SYSTEM_PROMPT),
            HumanMessage(content=build_humanize_prompt(raw)),
        ]
        response, _ = timed_invoke(llm, messages, operation="humanize_response")
        return str(response.content).strip()
    except Exception as exc:
        logger.warning(f"[humanize] LLM failed: {exc}")
        return ""


def _norm(s: str) -> str:
    """NFKD lowercase without accents for robust comparison."""
    return (
        unicodedata.normalize("NFKD", (s or "").lower())
        .encode("ASCII", "ignore")
        .decode("ASCII")
    )


def _preserve_money_values(raw: str, candidate: str) -> bool:
    """Every monetary value in raw must appear, normalized, in candidate."""
    def normalize_money(money: str) -> str:
        return re.sub(r"\s+", "", money.lower())

    raw_values = {normalize_money(m) for m in _MONEY_RE.findall(raw)}
    candidate_values = {normalize_money(m) for m in _MONEY_RE.findall(candidate)}
    return raw_values.issubset(candidate_values)


def _preserve_category_names(raw: str, candidate: str, state: dict[str, Any]) -> bool:
    """If state has a category in raw, it must be present in candidate."""
    category = state.get("category_name")
    if not category:
        extracted = state.get("extracted_data") or {}
        category = extracted.get("category")
    if not category:
        return True

    category_norm = _norm(str(category))
    if category_norm not in _norm(raw):
        return True
    return category_norm in _norm(candidate)
