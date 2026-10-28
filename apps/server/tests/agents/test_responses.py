"""Unit tests for response formatting helpers."""

from datetime import date, datetime

from app.agents import responses as resp


def test_period_label_translates_known_periods():
    assert resp.period_label("daily") == "Diário"
    assert resp.period_label("weekly") == "Semanal"
    assert resp.period_label("monthly") == "Mensal"
    assert resp.period_label("yearly") == "Anual"


def test_period_label_keeps_unknown_period():
    assert resp.period_label("biweekly") == "biweekly"


def test_fmt_deadline_accepts_iso_with_timezone():
    assert resp._fmt_deadline("2025-10-01T00:00:00+00:00") == "outubro/2025"


def test_fmt_deadline_accepts_date_objects():
    assert resp._fmt_deadline(date(2026, 10, 1)) == "outubro/2026"
    assert resp._fmt_deadline(datetime(2026, 1, 15, 12, 0)) == "janeiro/2026"


def test_budget_list_uses_period_label():
    result = resp.budget_list([
        {
            "name": "Alimentação",
            "period": "monthly",
            "total_spent": 120,
            "total_limit": 500,
            "percentage": 24,
        }
    ])

    assert "(Mensal)" in result
    assert "monthly" not in result


def test_budget_confirmation_uses_fixed_message():
    result = resp.budget_confirmation("Alimentação", 4000, "monthly", "2026-05-24")

    assert result == (
        "📊 Orçamento de R$ 4.000,00 na categoria Alimentação a cada 30 dias no dia 24/05/2026.\n\n"
        "Confirma?"
    )


def test_budget_saved_success_returns_short_success():
    assert resp.budget_saved_success() == "✅ Orçamento criado com sucesso!"


def test_goal_created_uses_deadline_label():
    result = resp.goal_created("Viagem", 10_000, "2026-10-01T00:00:00+00:00")

    assert "outubro/2026" in result
    assert "2026-10-01T00:00:00+00:00" not in result


def test_goal_confirmation_uses_fixed_message():
    result = resp.goal_confirmation("Comprar notebook", 5000, "2026-10-01")

    assert result == "🎯 Meta de R$ 5.000,00 para Comprar notebook até outubro/2026.\n\nConfirma?"


def test_goal_success_messages_are_fixed():
    assert resp.goal_saved_success() == "✅ Meta criada com sucesso!"
    assert resp.goal_delete_success() == "✅ Meta removida com sucesso!"


def test_goal_contribution_messages_are_fixed():
    confirmation = resp.goal_contribution_confirmation("Viagem", 200)
    success = resp.goal_contribution_success("Viagem", 1200, 5000, 24)

    assert confirmation == "🎯 Adicionar R$ 200,00 na meta Viagem.\n\nConfirma?"
    assert success == "✅ Valor adicionado à meta!\n\nViagem: R$ 1.200,00 / R$ 5.000,00 (24%)."


def test_goal_update_and_delete_confirmations_are_fixed():
    update = resp.goal_update_confirmation("Viagem", target_amount=6000, deadline="2026-12-01")
    delete = resp.goal_delete_confirmation("Viagem")

    assert update == (
        "🎯 Atualizar meta Viagem.\n\n"
        "Alterações: valor para R$ 6.000,00, prazo para dezembro/2026.\n\n"
        "Confirma?"
    )
    assert delete == "🗑️ Remover meta Viagem.\n\nConfirma?"


def test_transaction_confirmation_includes_core_fields():
    result = resp.transaction_confirmation("EXPENSE", 50, "Alimentação", "Mercado", "2026-05-24")

    assert result == (
        "🧾 Despesa: R$ 50,00 em Alimentação (Mercado) no dia 24/05/2026.\n\n"
        "Confirma esta transação?\n"
        "Se algo estiver errado, me diga o ajuste. Ex: \"valor era 200\"."
    )


def test_transaction_registered_returns_short_success():
    result = resp.transaction_registered("EXPENSE", 50, "Alimentação", "Mercado", "2026-05-24")

    assert result == "✅ Transação registrada com sucesso!"


def test_income_transaction_confirmation_uses_income_prefix():
    result = resp.transaction_confirmation("INCOME", 500, "Receita", "Pix recebido", "2026-05-24")

    assert result == (
        "💰 Receita: R$ 500,00 em Receita (Pix recebido) no dia 24/05/2026.\n\n"
        "Confirma esta transação?\n"
        "Se algo estiver errado, me diga o ajuste. Ex: \"valor era 200\"."
    )


def test_income_transaction_registered_returns_short_success():
    result = resp.transaction_registered("INCOME", 500, "Receita", "Pix recebido", "2026-05-24")

    assert result == "✅ Transação registrada com sucesso!"


def test_document_imported_single_transaction_includes_core_fields():
    result = resp.document_imported([
        {
            "amount": 139.84,
            "category": "Mercado",
            "description": "Nota fiscal Sao Roque",
            "transaction_date": "2026-05-24",
        }
    ])

    assert result == (
        "Documento importado com sucesso! "
        "Valor: R$ 139,84 em Mercado (Nota fiscal Sao Roque) no dia 24/05/2026. ✅"
    )


def test_document_imported_multiple_transactions_lists_core_fields():
    result = resp.document_imported([
        {"amount": 10, "category": "Mercado", "description": "Padaria", "date": "2026-05-01"},
        {"amount": 20, "category": "Transporte", "description": "Uber", "date": "2026-05-02"},
    ])

    assert "Documento importado com sucesso! 2 transações importadas:" in result
    assert "1. Valor: R$ 10,00 em Mercado (Padaria) no dia 01/05/2026." in result
    assert "2. Valor: R$ 20,00 em Transporte (Uber) no dia 02/05/2026." in result


def test_document_imported_only_duplicates_has_clear_message():
    result = resp.document_imported([], skipped=2, label="Documento")

    assert result == (
        "📄 Documento processado.\n\n"
        "🔁 Nenhuma transação nova foi importada.\n"
        "As transações encontradas já estavam duplicadas e foram ignoradas."
    )


def test_statement_imported_only_duplicate_uses_label():
    result = resp.document_imported([], skipped=1, label="Extrato")

    assert result == (
        "📄 Extrato processado.\n\n"
        "🔁 Nenhuma transação nova foi importada.\n"
        "As transações encontradas já estavam duplicadas e foram ignoradas."
    )


def test_document_imported_no_new_transactions_without_duplicates_is_neutral():
    result = resp.document_imported([], skipped=0, label="Documento")

    assert result == "📄 Documento processado.\n\nNenhuma transação nova foi importada."
