"""Tests for report intent routing and report response text."""

from datetime import date, datetime
from unittest.mock import patch

import pytest

from app.agents.ingestion import _looks_like_budget_or_goal_request, _looks_like_report_summary_request
from app.agents.reports import _format_report_summary
from app.agents.text_to_sql import (
    FinancialQueryPeriod,
    _has_period_indicators,
    build_financial_transactions_query,
    resolve_financial_query_period,
    resolve_period_smart,
)


@pytest.mark.parametrize(
    "message",
    [
        "quanto ja gastei",
        "como estao minhas despesas",
        "como estao meus gastos",
        "como estao minhas receitas",
        "resumo das minhas financas",
        "qual meu saldo",
    ],
)
def test_summary_requests_generate_report(message):
    assert _looks_like_report_summary_request(message) is True


@pytest.mark.parametrize(
    "message",
    [
        "meus orcamentos",
        "minhas metas",
        "o que e orcamento",
        "mercado 120",
    ],
)
def test_specific_or_non_summary_requests_do_not_generate_report(message):
    assert _looks_like_report_summary_request(message) is False


def test_report_summary_mentions_pdf_but_not_csv():
    result = _format_report_summary(
        datetime(2026, 5, 1),
        datetime(2026, 5, 24),
        "este mês",
        total_income=0,
        total_expense=739.68,
    )

    assert "PDF gerado com sucesso!" in result
    assert "CSV" not in result
    assert "Receitas: R$ 0,00" in result
    assert "Despesas: R$ 739,68" in result
    assert "Saldo: R$ -739,68" in result


@pytest.mark.parametrize(
    ("message", "start", "end", "label"),
    [
        ("gere um relatorio de todo tempo", None, None, "todo histórico"),
        ("gere um relatorio de todas minhas financas", None, None, "todo histórico"),
        ("gere um realtorio de todo ano", date(2026, 1, 1), date(2026, 5, 25), "ano de 2026"),
        ("gere um relatorio de jan de 2026", date(2026, 1, 1), date(2026, 1, 31), "janeiro de 2026"),
        ("gere um relatorio de fevereiro de 2026", date(2026, 2, 1), date(2026, 2, 28), "fevereiro de 2026"),
        ("gere um relatorio deste ano", date(2026, 1, 1), date(2026, 5, 25), "ano de 2026"),
    ],
)
def test_financial_query_period_resolves_report_messages(message, start, end, label):
    period = resolve_financial_query_period(message, today=date(2026, 5, 25))

    assert period.start == start
    assert period.end == end
    assert period.label == label


def test_report_transaction_query_uses_text_to_sql_user_filter_and_period():
    sql, description, period = build_financial_transactions_query(
        "gere um relatorio de fevereiro de 2026"
    )

    assert "SELECT" in sql
    assert "FROM transactions t" in sql
    assert "t.user_id = (SELECT id FROM users WHERE phone_number = :phone_number)" in sql
    assert "DATE(transaction_date) BETWEEN '2026-02-01' AND '2026-02-28'" in sql
    assert description == "Transações financeiras - fevereiro de 2026"
    assert period.label == "fevereiro de 2026"


# ── Budget/Goal fast-path tests ──────────────────────────────────────


@pytest.mark.parametrize(
    "message",
    [
        "orcamento de 900 aluguel",
        "orçamento 4000 alimentação",
        "meta de 5000 viagem",
        "limite 2000 transporte",
        "orcamento 1500 supermercado",
    ],
)
def test_budget_goal_messages_detected(message):
    from app.agents.ingestion import _normalize

    assert _looks_like_budget_or_goal_request(_normalize(message)) is True


@pytest.mark.parametrize(
    "message",
    [
        "gastei 900 no aluguel",
        "mercado 240",
        "quanto gastei no orcamento",
        "resumo do orcamento 500",
        "uber 30",
    ],
)
def test_non_budget_messages_not_detected(message):
    from app.agents.ingestion import _normalize

    assert _looks_like_budget_or_goal_request(_normalize(message)) is False


# ── Period indicator detection ────────────────────────────────────────


@pytest.mark.parametrize(
    "msg",
    ["mes 2", "mes 02", "relatorio do mes 3", "ultimos 3 meses", "primeiro trimestre"],
)
def test_has_period_indicators_true(msg):
    from app.agents.text_to_sql import normalize_query_text

    assert _has_period_indicators(normalize_query_text(msg)) is True


@pytest.mark.parametrize(
    "msg",
    ["gastei 50 no mercado", "este mes", "quanto gastei", "relatorio de janeiro"],
)
def test_has_period_indicators_false(msg):
    from app.agents.text_to_sql import normalize_query_text

    assert _has_period_indicators(normalize_query_text(msg)) is False


# ── resolve_period_smart tests ────────────────────────────────────────


def test_resolve_period_smart_uses_parser_for_known_month():
    result = resolve_period_smart("gere um relatorio de fevereiro", today=date(2026, 5, 25))
    assert result.start == date(2026, 2, 1)
    assert result.end == date(2026, 2, 28)


def test_resolve_period_smart_calls_llm_for_mes_2():
    mock_result = FinancialQueryPeriod(
        start=date(2026, 2, 1), end=date(2026, 2, 28), label="fevereiro de 2026"
    )
    with patch("app.agents.text_to_sql.resolve_period_with_llm", return_value=mock_result):
        result = resolve_period_smart("gere um relatorio do mes 2", today=date(2026, 5, 25))
    assert result.start == date(2026, 2, 1)
    assert result.end == date(2026, 2, 28)
    assert result.label == "fevereiro de 2026"


def test_resolve_period_smart_fallback_when_llm_unavailable():
    with patch("app.agents.text_to_sql.resolve_period_with_llm", return_value=None):
        result = resolve_period_smart("gere um relatorio do mes 2", today=date(2026, 5, 25))
    # Falls back to "este mês" since parser can't handle it and LLM failed
    assert result.label == "este mês"


def test_resolve_period_smart_no_llm_for_normal_messages():
    """Messages without period indicators should NOT call LLM."""
    with patch("app.agents.text_to_sql.resolve_period_with_llm") as mock_llm:
        resolve_period_smart("gastei 50 no mercado", today=date(2026, 5, 25))
    mock_llm.assert_not_called()
