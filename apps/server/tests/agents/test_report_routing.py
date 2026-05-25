"""Tests for report intent routing and report response text."""

from datetime import date, datetime

import pytest

from app.agents.ingestion import _looks_like_report_summary_request
from app.agents.reports import _format_report_summary
from app.agents.text_to_sql import (
    build_financial_transactions_query,
    resolve_financial_query_period,
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
