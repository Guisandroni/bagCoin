"""Unit tests for response humanization guards."""

from unittest.mock import MagicMock

from app.agents import humanize
from app.schemas.enums import IntentType


def test_should_humanize_is_off_by_default(monkeypatch):
    monkeypatch.setattr(humanize.settings, "HUMANIZE_RESPONSES", False)

    assert not humanize.should_humanize({"intent": IntentType.REGISTER_EXPENSE.value})


def test_should_humanize_allows_extra_intents(monkeypatch):
    monkeypatch.setattr(humanize.settings, "HUMANIZE_RESPONSES", True)
    monkeypatch.setattr(humanize.settings, "HUMANIZE_ALLOWED_INTENTS_EXTRA", ["CUSTOM_INTENT"])

    assert humanize.should_humanize({"intent": "CUSTOM_INTENT", "context": {}})


def test_should_humanize_blocks_disallowed_intent(monkeypatch):
    """Intents fora do whitelist não podem ser humanizadas mesmo com flag on."""
    monkeypatch.setattr(humanize.settings, "HUMANIZE_RESPONSES", True)
    monkeypatch.setattr(humanize.settings, "HUMANIZE_ALLOWED_INTENTS_EXTRA", [])

    # CHAT/GREETING/HELP não estão em HUMANIZE_ALLOWED_INTENTS
    assert not humanize.should_humanize({"intent": IntentType.CHAT.value, "context": {}})
    assert not humanize.should_humanize({"intent": IntentType.GREETING.value, "context": {}})
    assert not humanize.should_humanize({"intent": IntentType.HELP.value, "context": {}})
    assert not humanize.should_humanize({"intent": IntentType.QUERY_DATA.value, "context": {}})


def test_should_humanize_skips_on_error(monkeypatch):
    """Respostas de erro nunca são humanizadas."""
    monkeypatch.setattr(humanize.settings, "HUMANIZE_RESPONSES", True)

    assert not humanize.should_humanize({
        "intent": IntentType.REGISTER_EXPENSE.value,
        "error": "some error",
        "context": {},
    })


def test_should_humanize_skips_when_context_opts_out(monkeypatch):
    """Caminho de saída: context.skip_humanize=True bloqueia a humanização."""
    monkeypatch.setattr(humanize.settings, "HUMANIZE_RESPONSES", True)

    assert not humanize.should_humanize({
        "intent": IntentType.REGISTER_EXPENSE.value,
        "context": {"skip_humanize": True},
    })


def test_preserve_money_values_rejects_changed_value():
    raw = "Gasto de R$ 50,00 em Alimentação registrado."
    candidate = "Anotado. R$ 500,00 em Alimentação."

    assert not humanize._preserve_money_values(raw, candidate)


def test_preserve_category_names_normalizes_accents_and_case():
    raw = "Gasto de R$ 50,00 em Alimentação registrado."
    candidate = "Anotado. R$ 50,00 em alimentacao."
    state = {"category_name": "Alimentação"}

    assert humanize._preserve_category_names(raw, candidate, state)


def test_humanize_safely_keeps_raw_when_llm_fails(monkeypatch):
    monkeypatch.setattr(humanize, "get_llm", lambda **kw: None)
    raw = "Gasto de R$ 50,00 em Alimentação registrado."

    assert humanize.humanize_safely(raw, {"category_name": "Alimentação"}) == raw


def test_humanize_safely_applies_valid_candidate(monkeypatch):
    response = MagicMock()
    response.content = "Anotado. R$ 50,00 em Alimentação."
    monkeypatch.setattr(humanize, "get_llm", lambda **kw: object())
    monkeypatch.setattr(humanize, "timed_invoke", lambda *a, **kw: (response, 10))

    result = humanize.humanize_safely(
        "Gasto de R$ 50,00 em Alimentação registrado.",
        {"category_name": "Alimentação"},
    )

    assert result == "Anotado. R$ 50,00 em Alimentação."
