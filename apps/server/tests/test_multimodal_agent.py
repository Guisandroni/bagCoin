"""Tests for multimodal agent media handling."""

import base64
import io
import json
import zipfile

from app.agents import document_understanding, multimodal
from app.agents.statement_parser import parse_ofx, parse_pdf_statement, parse_statement


def _docx_bytes(text: str) -> bytes:
    xml_text = "".join(
        f"<w:p><w:r><w:t>{line}</w:t></w:r></w:p>"
        for line in text.splitlines()
    )
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{xml_text}</w:body>"
        "</w:document>"
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("word/document.xml", document_xml)
    return buffer.getvalue()


def test_process_multimodal_accepts_audio_media(monkeypatch):
    monkeypatch.setattr(multimodal, "process_audio", lambda media: "Gastei R$ 42 no mercado")

    state = {
        "source_format": "ptt",
        "message": "",
        "context": {
            "media": {
                "mimetype": "audio/ogg",
                "data": "fake",
            }
        },
    }

    result = multimodal.process_multimodal(state)

    assert result["message"] == "Gastei R$ 42 no mercado"
    assert result["context"]["original_format"] == "audio"
    assert result["context"]["extracted_media_text"] == "Gastei R$ 42 no mercado"
    assert "error" not in result


def test_process_multimodal_accepts_image_media(monkeypatch):
    monkeypatch.setattr(
        multimodal,
        "process_image",
        lambda media: "Recibo do supermercado. Total R$ 99,90.",
    )

    state = {
        "source_format": "image",
        "message": "",
        "context": {
            "media": {
                "mimetype": "image/jpeg",
                "data": "fake",
            }
        },
    }

    result = multimodal.process_multimodal(state)

    assert result["message"] == "Recibo do supermercado. Total R$ 99,90."
    assert result["context"]["original_format"] == "image"
    assert "error" not in result


def test_process_multimodal_returns_actionable_error_when_audio_cannot_be_transcribed(monkeypatch):
    monkeypatch.setattr(
        multimodal,
        "process_audio",
        lambda media: "[Não consegui entender o áudio. Tente de novo ou envie como texto.]",
    )

    state = {
        "source_format": "audio",
        "message": "",
        "context": {
            "media": {
                "mimetype": "audio/ogg",
                "data": "fake",
            }
        },
    }

    result = multimodal.process_multimodal(state)

    assert "Não consegui entender o áudio" in result["error"]
    assert "Pode enviar novamente" in result["response"]


def test_process_multimodal_accepts_docx_document():
    data = base64.b64encode(_docx_bytes("Gastei R$ 42 no mercado")).decode()

    state = {
        "source_format": "document",
        "message": "",
        "context": {
            "media": {
                "mimetype": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "filename": "nota.docx",
                "data": data,
            }
        },
    }

    result = multimodal.process_multimodal(state)

    assert result["message"] == "Gastei R$ 42 no mercado"
    assert result["context"]["original_format"] == "document"
    assert result["context"]["media_provider"] == "docx"


def test_parse_statement_accepts_docx_statement():
    doc_text = "\n".join(
        [
            "01/05/2026 Mercado 42,10",
            "02/05/2026 Salario 2500,00",
            "03/05/2026 Uber 18,50",
        ]
    )
    media = {
        "mimetype": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "filename": "extrato.docx",
        "data": base64.b64encode(_docx_bytes(doc_text)).decode(),
    }

    transactions = parse_statement(media)

    assert len(transactions) == 3
    assert transactions[0]["description"] == "Mercado"
    assert transactions[0]["amount"] == 42.10


def test_parse_pdf_statement_handles_vertical_table_text():
    pdf_text = "\n".join(
        [
            "Data",
            "Histórico",
            "Docto.",
            "Crédito (R$)",
            "Débito (R$)",
            "Saldo (R$)",
            "01/02/2026",
            "TRANSFERENCIA PIX",
            "024639",
            "154,40",
            "4.627,83",
            "03/02/2026",
            "ESTORNO",
            "036335",
            "1.845,57",
            "6.473,40",
            "04/02/2026",
            "PGTO DARF",
            "995711",
            "1.792,49",
            "5.036,32",
            "Total Créditos",
            "1.845,57",
            "1.946,89",
            "5.036,32",
        ]
    )

    transactions = parse_pdf_statement(pdf_text)

    assert [tx["type"] for tx in transactions] == ["EXPENSE", "INCOME", "EXPENSE"]
    assert [tx["amount"] for tx in transactions] == [154.40, 1845.57, 1792.49]
    assert transactions[0]["description"] == "TRANSFERENCIA PIX"
    assert transactions[1]["description"] == "ESTORNO"
    assert all(tx["amount"] != 2026 for tx in transactions)


def test_parse_ofx_accepts_sgml_line_terminated_tags():
    ofx_text = """
<OFX>
<BANKTRANLIST>
<STMTTRN>
<TRNTYPE>DEBIT
<DTPOSTED>20260201
<TRNAMT>-154.40
<FITID>202602014639
<MEMO>TRANSFERENCIA PIX
</STMTTRN>
<STMTTRN>
<TRNTYPE>CREDIT
<DTPOSTED>20260203
<TRNAMT>1845.57
<FITID>202602036335
<MEMO>ESTORNO
</STMTTRN>
</BANKTRANLIST>
</OFX>
"""

    transactions = parse_ofx(ofx_text)

    assert len(transactions) == 2
    assert transactions[0]["type"] == "EXPENSE"
    assert transactions[0]["amount"] == 154.40
    assert transactions[1]["type"] == "INCOME"
    assert transactions[1]["amount"] == 1845.57


def test_document_understanding_uses_llm_for_arbitrary_docx(monkeypatch):
    data = base64.b64encode(
        _docx_bytes(
            "Movimentações da conta\n"
            "Primeiro de maio: compra no Mercado no valor de 42,10 reais\n"
            "Segundo de maio: salário recebido de 2500 reais"
        )
    ).decode()

    class FakeResponse:
        content = json.dumps({
            "document_type": "bank_statement",
            "is_financial": True,
            "period_start": "2026-05-01",
            "period_end": "2026-05-02",
            "currency": "BRL",
            "confidence": 0.82,
            "summary": "Movimentações da conta",
            "issues": [],
            "transactions": [
                {
                    "date": "2026-05-01",
                    "description": "Mercado",
                    "amount": 42.1,
                    "type": "EXPENSE",
                    "category": "Alimentação",
                    "confidence": 0.8,
                    "raw": "compra no Mercado no valor de 42,10 reais",
                },
                {
                    "date": "2026-05-02",
                    "description": "Salário",
                    "amount": 2500,
                    "type": "INCOME",
                    "category": "Receita",
                    "confidence": 0.85,
                    "raw": "salário recebido de 2500 reais",
                },
            ],
        })

    monkeypatch.setattr(document_understanding, "get_llm", lambda *_, **__: object())
    monkeypatch.setattr(document_understanding, "_parse_unstructured_financial_document", lambda *_: None)
    monkeypatch.setattr(
        document_understanding,
        "timed_invoke",
        lambda *_, **__: (FakeResponse(), 1),
    )

    result = document_understanding.analyze_document_media({
        "mimetype": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "filename": "movimentacoes.docx",
        "data": data,
    })

    assert result["document_type"] == "bank_statement"
    assert result["requires_confirmation"] is True
    assert result["extraction_method"] == "docx_text+llm"
    assert len(result["transactions"]) == 2


def test_document_understanding_parses_unstructured_financial_list():
    result = document_understanding.analyze_document_media(
        {
            "mimetype": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "filename": "test00010010111.docx",
            "data": "ignored",
        },
        extracted_text=(
            "Teste 001\n"
            "Mercado 240 reais\n"
            "Pao 120 reais\n"
            "Alsafrao 200\n"
            "Salario 2500 todo dia 5 do mes"
        ),
    )

    assert result["document_type"] == "unstructured_financial_list"
    assert result["extraction_method"] == "multimodal_preextract+unstructured"
    assert len(result["transactions"]) == 4
    salary = next(tx for tx in result["transactions"] if tx["description"] == "Salario")
    assert salary["type"] == "INCOME"
    assert salary["is_recurring"] is True
    assert salary["recurrence_day"] == 5


def test_document_understanding_does_not_parse_company_ids_as_money():
    result = document_understanding.analyze_document_media(
        {
            "mimetype": "image/jpeg",
            "filename": "comprovante.jpg",
            "data": "ignored",
        },
        extracted_text=(
            "R$ 185,77\n"
            "SUPERMERCADOS SAO ROQUE LTDA AV. CONSUMIDOR - ITAQUAQUE\n"
            "CNPJ 18.150.000/0001-77\n"
            "Padaria R$ 12,30"
        ),
    )

    assert result["document_type"] == "unstructured_financial_list"
    amounts = sorted(tx["amount"] for tx in result["transactions"])
    assert amounts == [12.3, 185.77]
    assert all(tx["amount"] < 1000 for tx in result["transactions"])


def test_document_tool_prepares_pending_import(monkeypatch):
    from app.agents.tools.documents import create_document_tools

    saved = {}
    monkeypatch.setattr(
        "app.agents.tools.documents.analyze_document_media",
        lambda *_args, **_kwargs: {
            "document_type": "receipt",
            "is_financial": True,
            "extraction_method": "vision_ocr+llm",
            "confidence": 0.9,
            "transactions": [
                {
                    "date": "2026-05-01",
                    "description": "Padaria",
                    "amount": 18.5,
                    "type": "EXPENSE",
                    "category": "Alimentação",
                    "confidence": 0.9,
                    "raw": "Padaria total 18,50",
                }
            ],
            "issues": [],
            "totals": {"transactions": 1, "income": 0, "expense": 18.5},
            "source": {"filename": "recibo.jpg", "mimetype": "image/jpeg"},
        },
    )

    def fake_save_pending_action(phone, **kwargs):
        saved["payload"] = {"phone": phone, **kwargs}
        return "Confirma?"

    monkeypatch.setattr(
        "app.agents.tools.documents.save_pending_action",
        fake_save_pending_action,
    )

    response = create_document_tools(
        "5511999999999",
        {"media": {"mimetype": "image/jpeg", "data": "x"}, "channel": "telegram"},
    )[0].invoke({})

    assert "Confirma?" in response
    assert "Identifiquei uma despesa" in saved["payload"]["summary"]
    assert "Valor total: R$ 18,50" in saved["payload"]["summary"]
    assert "Método" not in saved["payload"]["summary"]
    assert "Confiança" not in saved["payload"]["summary"]
    assert "multimodal" not in saved["payload"]["summary"]
    assert saved["payload"]["action"] == "import_document_transactions"
    assert saved["payload"]["channel"] == "telegram"
