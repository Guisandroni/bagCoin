"""Real image extraction tests for receipt examples.

These tests use the JPEG files in ../../examples and call Gemini when running
the real-image marker. They are intentionally outside the default fast path.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

import pytest

from app.core.config import settings
from app.agents.document_understanding import analyze_document_media
from app.agents.multimodal import process_image
from app.agents.tools.documents import (
    _document_confirmation_summary,
    _handle_receipt_structured,
)

pytestmark = pytest.mark.real_image_extraction

EXAMPLES_DIR = Path(__file__).resolve().parents[4] / "examples"
FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "real_image_receipts"
ARTIFACTS_DIR = Path(__file__).resolve().parents[1] / "artifacts" / "real_image_receipts"
IMAGE_PATHS = sorted(EXAMPLES_DIR.glob("*.jpeg"))
HAS_GEMINI = bool(settings.GEMINI_API_KEY)
EXPECTED_TOTALS_BY_FILENAME = {
    "WhatsApp Image 2026-05-19 at 21.48.18.jpeg": 139.84,
    "WhatsApp Image 2026-05-19 at 21.48.19.jpeg": 5.99,
    "WhatsApp Image 2026-05-19 at 21.48.19 (1).jpeg": 185.77,
}


def _media_from_path(path: Path) -> dict[str, Any]:
    return {
        "data": base64.b64encode(path.read_bytes()).decode("ascii"),
        "mimetype": "image/jpeg",
        "filename": path.name,
    }


def _artifact_path(image_path: Path) -> Path:
    safe_name = "".join(
        char.lower() if char.isalnum() else "_"
        for char in image_path.stem
    ).strip("_")
    return ARTIFACTS_DIR / f"{safe_name}.json"


def _write_extraction_artifact(
    image_path: Path,
    image_structured: dict[str, Any],
    document_result: dict[str, Any],
    confirmation_summary: str,
) -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "source_image": str(image_path),
        "gemini_structured": image_structured,
        "bagcoin_document_analysis": document_result,
        "confirmation_summary": confirmation_summary,
        "single_transaction_to_import": (document_result.get("transactions") or [None])[0],
        "receipt_items": document_result.get("receipt_items") or [],
        "total_amount": document_result.get("total_amount"),
    }
    _artifact_path(image_path).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


@pytest.mark.skipif(not HAS_GEMINI, reason="GEMINI_API_KEY is required")
@pytest.mark.parametrize("image_path", IMAGE_PATHS, ids=lambda path: path.name)
def test_real_receipt_image_extracts_structured_total_and_items(image_path: Path):
    result = process_image(_media_from_path(image_path))

    assert not result.is_failure
    assert result.structured
    assert result.structured.get("is_receipt") is True
    assert float(result.structured.get("total_amount") or 0) > 0
    assert len(result.structured.get("items") or []) > 0


@pytest.mark.skipif(not HAS_GEMINI, reason="GEMINI_API_KEY is required")
@pytest.mark.parametrize("image_path", IMAGE_PATHS, ids=lambda path: path.name)
def test_real_receipt_image_document_analysis_imports_single_total_transaction(image_path: Path):
    media = _media_from_path(image_path)
    image_result = process_image(media)
    assert image_result.structured

    document_result = analyze_document_media(
        media,
        extracted_text=json.dumps(image_result.structured, ensure_ascii=False),
    )
    transactions = document_result.get("transactions") or []

    assert document_result["document_type"] in {"receipt", "invoice"}
    assert len(transactions) == 1
    assert transactions[0]["type"] == "EXPENSE"
    assert transactions[0]["amount"] == pytest.approx(
        float(document_result["total_amount"]), abs=0.01
    )
    assert transactions[0]["description"].lower() != "price"
    assert len(document_result.get("receipt_items") or []) > 0


@pytest.mark.skipif(not HAS_GEMINI, reason="GEMINI_API_KEY is required")
@pytest.mark.parametrize("image_path", IMAGE_PATHS, ids=lambda path: path.name)
def test_real_receipt_confirmation_message_uses_total_not_item_prices(image_path: Path):
    media = _media_from_path(image_path)
    image_result = process_image(media)
    document_result = analyze_document_media(
        media,
        extracted_text=json.dumps(image_result.structured, ensure_ascii=False),
    )
    summary = _document_confirmation_summary(
        document_result,
        document_result.get("transactions") or [],
    )
    _write_extraction_artifact(
        image_path,
        image_result.structured or {},
        document_result,
        summary,
    )

    assert "Aqui estão os itens encontrados" in summary
    assert "Valor total:" in summary
    assert "importar esta transação" in summary
    assert "Revise os principais lançamentos" not in summary
    assert '"price": R$' not in summary
    assert "importar essas transações" not in summary
    expected_total = EXPECTED_TOTALS_BY_FILENAME.get(image_path.name)
    if expected_total is not None:
        assert float(document_result["total_amount"]) == pytest.approx(expected_total, abs=0.01)


@pytest.mark.skipif(not HAS_GEMINI, reason="GEMINI_API_KEY is required")
@pytest.mark.parametrize("image_path", IMAGE_PATHS, ids=lambda path: path.name)
def test_real_receipt_pending_action_registers_only_one_transaction(monkeypatch, image_path: Path):
    image_result = process_image(_media_from_path(image_path))
    assert image_result.structured

    captured: dict[str, Any] = {}

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

    monkeypatch.setattr(
        "app.agents.tools.documents.save_pending_action",
        fake_save_pending_action,
    )

    _handle_receipt_structured(image_result.structured, "5511999999999", "whatsapp")

    assert captured["action"] == "register_transaction"
    assert captured["params"]["type"] == "EXPENSE"
    assert captured["params"]["source_format"] == "image"
    assert captured["params"]["amount"] == pytest.approx(
        float(image_result.structured["total_amount"]),
        abs=0.01,
    )
    assert captured["summary"].startswith("🧾 Despesa: R$")
    assert "Confirma esta transação?" in captured["summary"]
    assert "Método" not in captured["summary"]
    assert "Confiança" not in captured["summary"]


def test_broken_json_price_lines_are_not_imported_as_multiple_transactions():
    payload = """
    "is_receipt": true,
    "items": [
      {"desc": "carne bovina", "price": 10.90},
      {"desc": "peito de frango", "price": 9.85},
      {"desc": "arroz", "price": 9.85}
    ],
    "total_amount": 180.00
    """
    media = {
        "data": base64.b64encode(b"fake").decode("ascii"),
        "mimetype": "image/jpeg",
        "filename": "broken-json-receipt.jpeg",
    }

    result = analyze_document_media(media, extracted_text=payload)
    transactions = result.get("transactions") or []
    summary = _document_confirmation_summary(result, transactions)

    assert result["document_type"] == "receipt"
    assert len(transactions) == 1
    assert transactions[0]["amount"] == 180.0
    assert [item["description"] for item in result["receipt_items"]] == [
        "carne bovina",
        "peito de frango",
        "arroz",
    ]
    assert "Revise os principais lançamentos" not in summary
    assert '"price": R$' not in summary
    assert "Valor total: R$ 180,00" in summary


@pytest.mark.skipif(not HAS_GEMINI, reason="GEMINI_API_KEY is required")
def test_real_receipt_footer_total_is_used_instead_of_cash_payment(monkeypatch):
    image_path = EXAMPLES_DIR / "WhatsApp Image 2026-05-19 at 21.48.18.jpeg"
    media = _media_from_path(image_path)
    image_result = process_image(media)
    assert image_result.structured
    structured = image_result.structured
    captured: dict[str, Any] = {}

    def fake_save_pending_action(phone_number, action, params, summary, channel):
        captured.update({"action": action, "params": params, "summary": summary})
        return summary

    monkeypatch.setattr(
        "app.agents.tools.documents.save_pending_action",
        fake_save_pending_action,
    )

    result = analyze_document_media(media, extracted_text=json.dumps(structured, ensure_ascii=False))
    transactions = result.get("transactions") or []
    summary = _document_confirmation_summary(result, transactions)
    _handle_receipt_structured(structured, "5511999999999", "whatsapp")

    assert structured["labeled_total_amount"] == pytest.approx(139.84, abs=0.01)
    assert structured["payment_amount"] == pytest.approx(150.00, abs=0.01)
    assert structured["change_amount"] == pytest.approx(10.16, abs=0.01)
    assert "Valor Total" in str(structured.get("total_evidence") or "")
    assert "Dinheiro" in str(structured.get("total_evidence") or "")
    assert result["total_amount"] == pytest.approx(139.84)
    assert transactions[0]["amount"] == pytest.approx(139.84)
    assert summary.startswith("🧾 Despesa: R$ 139,84")
    assert "Confirma esta transação?" in summary
    assert captured["params"]["amount"] == pytest.approx(139.84)
    assert captured["summary"].startswith("🧾 Despesa: R$ 139,84")


def test_external_ocr_json_is_normalized_to_single_receipt_transaction():
    source = json.loads(
        (
            FIXTURES_DIR
            / "ocr_reference_resultado_nota_20260521_200428_20260521_200440.json"
        ).read_text(encoding="utf-8")
    )
    expected = json.loads(
        (
            FIXTURES_DIR
            / "expected_bagcoin_receipt_resultado_nota_20260521_200428_20260521_200440.json"
        ).read_text(encoding="utf-8")
    )
    media = {
        "data": base64.b64encode(b"fake").decode("ascii"),
        "mimetype": "image/jpeg",
        "filename": "nota_20260521_200428.jpeg",
    }

    result = analyze_document_media(
        media,
        extracted_text=json.dumps(source, ensure_ascii=False),
    )
    transactions = result.get("transactions") or []
    summary = _document_confirmation_summary(result, transactions)

    assert result["document_type"] == expected["document_type"]
    assert result["is_financial"] is expected["is_financial"]
    assert result["total_amount"] == pytest.approx(expected["total_amount"])
    assert result["establishment"] == expected["establishment"]
    assert len(transactions) == 1

    tx = transactions[0]
    expected_tx = expected["transaction"]
    assert tx["date"] == expected_tx["date"]
    assert tx["description"] == expected_tx["description"]
    assert tx["amount"] == pytest.approx(expected_tx["amount"])
    assert tx["type"] == expected_tx["type"]
    assert tx["category"] == expected_tx["category"]
    assert result["receipt_items"] == expected["items"]
    for text in expected["summary_must_contain"]:
        assert text in summary
    for text in expected["summary_must_not_contain"]:
        assert text not in summary


def test_external_ocr_json_pending_action_registers_only_total_transaction(monkeypatch):
    source = json.loads(
        (
            FIXTURES_DIR
            / "ocr_reference_resultado_nota_20260521_200428_20260521_200440.json"
        ).read_text(encoding="utf-8")
    )
    expected = json.loads(
        (
            FIXTURES_DIR
            / "expected_bagcoin_receipt_resultado_nota_20260521_200428_20260521_200440.json"
        ).read_text(encoding="utf-8")
    )
    captured: dict[str, Any] = {}

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

    monkeypatch.setattr(
        "app.agents.tools.documents.save_pending_action",
        fake_save_pending_action,
    )

    _handle_receipt_structured(source, "5511999999999", "whatsapp")

    assert captured["action"] == "register_transaction"
    assert captured["params"]["date"] == expected["transaction"]["date"]
    assert captured["params"]["description"] == expected["transaction"]["description"]
    assert captured["params"]["amount"] == pytest.approx(expected["transaction"]["amount"])
    assert captured["params"]["type"] == expected["transaction"]["type"]
    assert captured["params"]["category"] == expected["transaction"]["category"]
    assert captured["params"]["source_format"] == expected["transaction"]["source_format"]
    for text in expected["summary_must_contain"]:
        assert text in captured["summary"]
    for text in expected["summary_must_not_contain"]:
        assert text not in captured["summary"]
