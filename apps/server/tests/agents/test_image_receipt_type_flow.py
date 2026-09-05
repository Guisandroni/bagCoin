"""Image receipt transaction type handling."""

from __future__ import annotations

import base64

import pytest

from app.agents.document_understanding import analyze_document_media
from app.agents.pending_actions import handle_pending_confirmation
from app.agents.tools.documents import _handle_receipt_structured


def test_image_receipt_income_registers_single_income_transaction(monkeypatch):
    captured: dict = {}

    def fake_save_pending_action(phone_number, action, params, summary, channel):
        captured.update(
            {
                "phone_number": phone_number,
                "action": action,
                "params": params,
                "summary": summary,
                "channel": channel,
            }
        )
        return summary

    monkeypatch.setattr("app.agents.tools.documents.save_pending_action", fake_save_pending_action)

    _handle_receipt_structured(
        {
            "is_receipt": True,
            "tipo": "receita",
            "valor_total": 250.0,
            "data": "2026-05-24",
            "estabelecimento": "PIX recebido",
            "categoria": "Reembolso",
            "descricao": "Reembolso recebido",
            "itens": [{"descricao": "Reembolso", "valor_total": 250.0}],
            "confianca": 0.91,
            "precisa_confirmar_tipo": False,
        },
        "5511999999999",
        "whatsapp",
    )

    assert captured["action"] == "register_transaction"
    assert captured["params"]["type"] == "INCOME"
    assert captured["params"]["amount"] == pytest.approx(250.0)
    assert captured["params"]["category"] == "Reembolso"
    assert captured["params"]["source_format"] == "image"
    assert captured["summary"] == (
        "💰 Receita: R$ 250,00 em Reembolso (Reembolso recebido) no dia 24/05/2026.\n\n"
        "Confirma esta transação?\n"
        "Se algo estiver errado, me diga o ajuste. Ex: \"valor era 200\"."
    )


def test_image_receipt_ambiguous_type_creates_clarification_pending_action(monkeypatch):
    captured: dict = {}

    def fake_save_pending_action(phone_number, action, params, summary, channel):
        captured.update({"action": action, "params": params, "summary": summary, "channel": channel})
        return summary

    monkeypatch.setattr("app.agents.tools.documents.save_pending_action", fake_save_pending_action)

    response = _handle_receipt_structured(
        {
            "is_receipt": True,
            "tipo": None,
            "valor_total": 139.84,
            "estabelecimento": "Mercado Exemplo",
            "categoria": "Supermercado",
            "itens": [{"descricao": "Compras", "valor_total": 139.84}],
            "precisa_confirmar_tipo": True,
        },
        "5511999999999",
        "whatsapp",
    )

    assert captured["action"] == "clarify_image_transaction_type"
    assert captured["params"]["total_amount"] == pytest.approx(139.84)
    assert captured["params"]["suggested_category"] == "Supermercado"
    assert captured["params"]["source_format"] == "image"
    assert "receita ou despesa" in response.lower()


def test_ambiguous_image_payload_does_not_create_expense_transaction():
    result = analyze_document_media(
        {
            "data": base64.b64encode(b"fake").decode("ascii"),
            "mimetype": "image/jpeg",
            "filename": "comprovante.jpeg",
        },
        extracted_text=(
            '{"is_receipt": true, "tipo": null, "valor_total": 139.84, '
            '"estabelecimento": "Comprovante", "categoria": "Outros", '
            '"precisa_confirmar_tipo": true}'
        ),
    )

    assert result["is_financial"] is True
    assert result["transactions"] == []


def test_clarification_response_builds_final_income_confirmation(monkeypatch):
    captured: dict = {}
    pending = {
        "action": "clarify_image_transaction_type",
        "params": {
            "structured": {
                "is_receipt": True,
                "tipo": None,
                "valor_total": 500.0,
                "estabelecimento": "Deposito recebido",
                "categoria": "Renda Extra",
                "descricao": "Deposito recebido",
                "itens": [],
                "precisa_confirmar_tipo": True,
            },
            "source_format": "image",
        },
        "summary": "Isso é receita ou despesa?",
        "channel": "whatsapp",
        "status": "pending",
    }

    monkeypatch.setattr("app.agents.pending_actions.load_pending_action", lambda phone: pending)
    monkeypatch.setattr("app.agents.pending_actions.clear_pending_action", lambda phone: None)

    def fake_save_pending_action(phone_number, action, params, summary, channel):
        captured.update({"action": action, "params": params, "summary": summary, "channel": channel})
        return summary

    monkeypatch.setattr("app.agents.pending_actions.save_pending_action", fake_save_pending_action)

    response = handle_pending_confirmation("5511999999999", "é receita")

    assert captured["action"] == "register_transaction"
    assert captured["params"]["type"] == "INCOME"
    assert captured["params"]["source_format"] == "image"
    assert response == (
        "💰 Receita: R$ 500,00 em Renda Extra (Deposito recebido) no dia 24/05/2026.\n\n"
        "Confirma esta transação?\n"
        "Se algo estiver errado, me diga o ajuste. Ex: \"valor era 200\"."
    )
