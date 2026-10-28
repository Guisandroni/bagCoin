"""Unit tests for app.agents.normalization.

Covers:
- Bug 1: Recurring transaction detection (regex)
- Bug 2: Clean description (no raw text, no verb, no amount)
- Bug 6: User-created categories take priority over defaults
- Amount parsing (Brazilian number formats)
- Type detection (EXPENSE / INCOME / TRANSFER)
"""

import pytest

from app.agents.normalization import _clean_description, extract_transaction


# =====================================================================
# Bug 2 — _clean_description: should strip amount, verb and period words
# =====================================================================


@pytest.mark.parametrize(
    "raw, expected_not_in",
    [
        ("Salario 500 reais mensalmente", ["500", "reais", "mensalmente"]),
        ("comprei remedio farmacia 500", ["500", "comprei"]),
        ("gastei 120 em alimentacao", ["120", "gastei"]),
        ("ganhei 200 de freela", ["200", "ganhei"]),
        ("paguei R$ 1.250,50 de aluguel", ["1", "250", "paguei", "reais"]),
    ],
)
def test_clean_description_removes_noise(raw, expected_not_in):
    result = _clean_description(raw)
    for token in expected_not_in:
        assert token.lower() not in result.lower(), f"'{token}' should not be in '{result}'"


def test_clean_description_returns_fallback_when_empty():
    assert _clean_description("500 reais mensalmente") == "Sem descrição"


# =====================================================================
# Bug 1 — Recurring detection (regex-based, no LLM)
# =====================================================================


@pytest.mark.parametrize(
    "message, expected_recurring, expected_freq",
    [
        ("salario 5000 mensalmente", True, "monthly"),
        ("aluguel 2000 todo mês", True, "monthly"),
        ("aluguel 2000 todo mes", True, "monthly"),
        ("netflix 40 fixo", True, "monthly"),
        ("pensao 300 recorrente", True, "monthly"),
        ("faxina 150 toda semana", True, "weekly"),
        ("faxina 150 semanalmente", True, "weekly"),
        ("iptu 1200 anualmente", True, "yearly"),
        ("iptu 1200 todo ano", True, "yearly"),
        # Non-recurring
        ("gastei 50 no mercado", False, None),
        ("uber 12", False, None),
        ("recebi 200 de freela", False, None),
    ],
)
def test_recurring_detection(
    mock_no_llm, mock_list_categories, base_state, message, expected_recurring, expected_freq
):
    mock_list_categories()
    base_state["message"] = message
    state = extract_transaction(base_state)
    data = state["extracted_data"]
    assert data["is_recurring"] == expected_recurring
    assert data["recurrence_frequency"] == expected_freq


# =====================================================================
# Bug 6 — User category priority (category-matching fast-path)
# =====================================================================


def test_user_category_takes_priority_over_defaults(
    mock_no_llm, mock_list_categories, base_state
):
    """User creates 'Acessorios para bike' — next tx must use it, not Vestuário."""
    mock_list_categories(extra=["Acessorios para bike"])
    base_state["message"] = "gasto de 50 em acessorios para bike"
    state = extract_transaction(base_state)
    assert state["extracted_data"]["category"] == "Acessorios para bike"


def test_default_category_still_used_when_no_custom_match(
    mock_no_llm, mock_list_categories, base_state
):
    mock_list_categories(extra=["Acessorios para bike"])
    base_state["message"] = "gastei 80 no mercado"
    state = extract_transaction(base_state)
    cat = state["extracted_data"]["category"]
    # Should match Supermercado or Alimentação via keyword, not "Outros"
    assert cat in ("Supermercado", "Alimentação", "Outros")


# =====================================================================
# Amount parsing (Brazilian number formats)
# =====================================================================


@pytest.mark.parametrize(
    "message, expected_amount",
    [
        ("gastei 50 no mercado", 50.0),
        ("uber 12", 12.0),
        ("recebi 5000 de salario", 5000.0),
        ("paguei R$ 1.250,50 de aluguel", 1250.50),
        ("gastei 3,40 no café", 3.40),
        ("comprei por 12,50", 12.50),
    ],
)
def test_amount_parsing(
    mock_no_llm, mock_list_categories, base_state, message, expected_amount
):
    mock_list_categories()
    base_state["message"] = message
    state = extract_transaction(base_state)
    assert state["extracted_data"]["amount"] == expected_amount


# =====================================================================
# Type detection
# =====================================================================


@pytest.mark.parametrize(
    "message, expected_type",
    [
        ("gastei 50 no mercado", "EXPENSE"),
        ("paguei 120 de luz", "EXPENSE"),
        ("comprei remedio farmacia 500", "EXPENSE"),
        ("recebi 5000 de salario", "INCOME"),
        ("ganhei 200 de freela", "INCOME"),
        ("meu pai me mandou 170", "INCOME"),
        ("transferi 300 para joao", "TRANSFER"),
    ],
)
def test_type_detection(
    mock_no_llm, mock_list_categories, base_state, message, expected_type
):
    mock_list_categories()
    base_state["message"] = message
    state = extract_transaction(base_state)
    assert state["extracted_data"]["type"] == expected_type


# =====================================================================
# Raw text preservation
# =====================================================================


def test_raw_text_always_preserved(mock_no_llm, mock_list_categories, base_state):
    msg = "salario 500 reais mensalmente"
    mock_list_categories()
    base_state["message"] = msg
    state = extract_transaction(base_state)
    assert state["extracted_data"]["raw_text"] == msg


# =====================================================================
# Hybrid extraction merge rules
# =====================================================================


def test_extract_hybrid_regex_wins_amount_conflict(
    monkeypatch, mock_llm_response, mock_list_categories, base_state
):
    monkeypatch.setattr("app.agents.normalization.get_llm", lambda **kw: object())
    mock_llm_response(
        '{"amount": 999, "type": "EXPENSE", "category": "Alimentação", "confidence": 0.9}'
    )
    mock_list_categories()
    base_state["message"] = "gastei 50 no mercado"

    state = extract_transaction(base_state)

    assert state["extracted_data"]["amount"] == 50


def test_extract_hybrid_phantom_category_falls_back(
    monkeypatch, mock_llm_response, mock_list_categories, base_state
):
    monkeypatch.setattr("app.agents.normalization.get_llm", lambda **kw: object())
    mock_llm_response(
        '{"amount": 50, "type": "EXPENSE", "category": "CategoriaInventada", "confidence": 0.9}'
    )
    mock_list_categories()
    base_state["message"] = "gastei 50 no mercado"

    state = extract_transaction(base_state)

    assert state["extracted_data"]["category"] != "CategoriaInventada"
    assert state["extracted_data"]["category"] in ("Supermercado", "Alimentação", "Outros")


def test_extract_hybrid_llm_timeout_uses_regex(monkeypatch, mock_list_categories, base_state):
    monkeypatch.setattr("app.agents.normalization.get_llm", lambda **kw: object())

    def timeout_invoke(*args, **kwargs):
        raise TimeoutError("simulated HTTP timeout")

    monkeypatch.setattr("app.agents.normalization.timed_invoke", timeout_invoke)
    mock_list_categories()
    base_state["message"] = "gastei 50 no mercado"

    state = extract_transaction(base_state)

    assert state["extracted_data"]["amount"] == 50


def test_extract_hybrid_llm_timeout_does_not_hang(monkeypatch, mock_list_categories, base_state):
    """Regression guard: even if LLM invoke sleeps, pipeline must return fast."""
    import time

    monkeypatch.setattr("app.agents.normalization.get_llm", lambda **kw: object())

    def slow_then_fail(*args, **kwargs):
        # Simulates slow HTTP client that eventually times out
        time.sleep(0.3)
        raise TimeoutError("simulated HTTP timeout")

    monkeypatch.setattr("app.agents.normalization.timed_invoke", slow_then_fail)
    mock_list_categories()
    base_state["message"] = "gastei 50 no mercado"

    start = time.time()
    state = extract_transaction(base_state)
    elapsed = time.time() - start

    # Pipeline must not hang: with a 0.3s sleep + future timeout, total < 2s
    assert elapsed < 2.0, f"pipeline hung for {elapsed:.2f}s"
    # Regex still wins when LLM fails
    assert state["extracted_data"]["amount"] == 50


# =====================================================================
# PR 2 — Short-circuit for structured image receipts
# =====================================================================


def test_extract_shortcircuits_on_structured_image_receipt(
    mock_no_llm, mock_list_categories, base_state
):
    """When context has a valid receipt JSON, skip LLM/regex cascade entirely."""
    mock_list_categories()
    base_state["message"] = ""  # Empty — image was the input
    base_state["context"] = {
        "image_structured": {
            "is_receipt": True,
            "establishment": "Mercado Extra",
            "total_amount": 87.43,
            "transaction_date": "2026-04-15",
            "confidence": 0.92,
            "raw_text": "NUBANK\nMercado Extra\n15/04/2026\nR$ 87,43",
        }
    }
    state = extract_transaction(base_state)
    data = state["extracted_data"]
    assert data["amount"] == 87.43
    assert data["description"] == "Mercado Extra"
    assert data["date"] == "2026-04-15"
    assert data["source_hint"] == "image_receipt"
    # Should have picked up Supermercado via establishment hints
    assert data["category"] == "Supermercado"


def test_extract_ignores_non_receipt_structured_image(
    mock_no_llm, mock_list_categories, base_state
):
    """If is_receipt=False, don't short-circuit — fall through to normal cascade."""
    mock_list_categories()
    base_state["message"] = "gastei 50 no mercado"
    base_state["context"] = {
        "image_structured": {"is_receipt": False, "raw_text": "selfie"}
    }
    state = extract_transaction(base_state)
    # Short-circuit skipped, regex cascade ran on message
    assert state["extracted_data"]["amount"] == 50
    assert state["extracted_data"].get("source_hint") != "image_receipt"


def test_extract_ignores_structured_image_without_amount(
    mock_no_llm, mock_list_categories, base_state
):
    """is_receipt=True but total_amount missing → skip short-circuit."""
    mock_list_categories()
    base_state["message"] = "gastei 50 no mercado"
    base_state["context"] = {
        "image_structured": {"is_receipt": True, "establishment": "X", "total_amount": None}
    }
    state = extract_transaction(base_state)
    assert state["extracted_data"]["amount"] == 50
