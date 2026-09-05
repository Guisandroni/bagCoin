"""Unit tests for app.agents.multimodal image processing (PR 2)."""

import base64

import pytest

from app.agents.multimodal import (
    _parse_json_object,
    process_image,
    process_multimodal,
)
from app.agents.multimodal_types import MultimodalResult

# =====================================================================
# _parse_json_object — tolerates fenced / embedded JSON
# =====================================================================


def test_parse_json_object_direct():
    result = _parse_json_object('{"is_receipt": true, "total_amount": 50.0}')
    assert result == {"is_receipt": True, "total_amount": 50.0}


def test_parse_json_object_fenced():
    fenced = '```json\n{"is_receipt": false}\n```'
    assert _parse_json_object(fenced) == {"is_receipt": False}


def test_parse_json_object_embedded_in_text():
    content = 'Aqui está a análise: {"is_receipt": true, "establishment": "X"} fim.'
    assert _parse_json_object(content) == {
        "is_receipt": True,
        "establishment": "X",
    }


def test_parse_json_object_invalid_returns_none():
    assert _parse_json_object("not json at all") is None
    assert _parse_json_object("") is None


def test_parse_json_object_rejects_non_dict():
    """Arrays and primitives must not pass through."""
    assert _parse_json_object("[1, 2, 3]") is None
    assert _parse_json_object('"just a string"') is None


# =====================================================================
# process_image — returns MultimodalResult with structured when LLM parses
# =====================================================================


@pytest.fixture
def fake_image_media():
    tiny_png = b"\x89PNG\r\n\x1a\n" + b"x" * 100
    return {
        "mimetype": "image/jpeg",
        "data": base64.b64encode(tiny_png).decode("ascii"),
    }


def test_process_image_structured_when_json_valid(monkeypatch, fake_image_media):
    """Gemini returns JSON -> structured populated."""
    monkeypatch.setattr(
        "app.agents.multimodal._image_gemini",
        lambda m, b: '{"is_receipt": true, "establishment": "Mercado Extra", '
                     '"total_amount": 87.43, "transaction_date": "2026-04-15", '
                     '"confidence": 0.9, "raw_text": "NUBANK\\nMercado Extra"}',
    )
    result = process_image(fake_image_media)
    assert isinstance(result, MultimodalResult)
    assert result.structured is not None
    assert result.structured["is_receipt"] is True
    assert result.structured["total_amount"] == 87.43
    assert result.provider == "gemini"
    assert result.failure is False


def test_process_image_uses_gemini(monkeypatch, fake_image_media):
    """Image extraction uses Gemini directly."""
    monkeypatch.setattr(
        "app.agents.multimodal._image_gemini",
        lambda m, b: '{"is_receipt": true, "establishment": "Farmácia X", '
                     '"total_amount": 12.5, "confidence": 0.8, "raw_text": "..."}',
    )
    result = process_image(fake_image_media)
    assert result.provider == "gemini"
    assert result.structured["establishment"] == "Farmácia X"


def test_process_image_failure_when_gemini_fails(monkeypatch, fake_image_media):
    monkeypatch.setattr("app.agents.multimodal._image_gemini", lambda m, b: None)
    result = process_image(fake_image_media)
    assert result.is_failure
    assert result.reason == "vision_unavailable"


def test_process_image_plain_text_when_not_json(monkeypatch, fake_image_media):
    """If LLM returns prose without JSON, structured is None and text is preserved."""
    monkeypatch.setattr("app.agents.multimodal.settings.IMAGE_STRUCTURED_EXTRACT", True)
    monkeypatch.setattr(
        "app.agents.multimodal._image_gemini",
        lambda m, b: "Esta é uma imagem de um gato fofo",
    )
    result = process_image(fake_image_media)
    # When structured parsing fails, structured stays None but text is still there
    assert result.structured is None
    assert "gato fofo" in result.text


# =====================================================================
# process_multimodal adapter — treats image results correctly
# =====================================================================


def _state_with_image(media):
    return {
        "phone_number": "5511999999999",
        "message": "",
        "source_format": "image",
        "context": {"media": media},
        "error": None,
        "response": None,
    }


def test_process_multimodal_sets_image_structured_in_context(monkeypatch, fake_image_media):
    monkeypatch.setattr(
        "app.agents.multimodal.process_image",
        lambda m: MultimodalResult(
            text="Mercado Extra\nR$ 50.00",
            structured={"is_receipt": True, "total_amount": 50.0, "establishment": "Mercado Extra"},
            provider="groq_llama4",
        ),
    )
    state = _state_with_image(fake_image_media)
    result = process_multimodal(state)
    assert "error" not in result or result["error"] is None
    assert result["context"]["image_structured"]["total_amount"] == 50.0
    assert result["context"]["media_provider"] == "groq_llama4"


def test_process_multimodal_preserves_non_receipt_image_for_document_agent(monkeypatch, fake_image_media):
    """Non-receipt images continue through the tool-agent document path."""
    monkeypatch.setattr(
        "app.agents.multimodal.process_image",
        lambda m: MultimodalResult(
            text="isto é um meme",
            structured={"is_receipt": False, "raw_text": "isto é um meme"},
            provider="groq_llama4",
        ),
    )
    state = _state_with_image(fake_image_media)
    result = process_multimodal(state)
    assert result["context"]["image_structured"]["is_receipt"] is False
    assert result["context"]["original_format"] == "image"
    assert result["response"] is None


def test_process_multimodal_image_failure_sets_error(monkeypatch, fake_image_media):
    monkeypatch.setattr(
        "app.agents.multimodal.process_image",
        lambda m: MultimodalResult(
            text="",
            failure=True,
            reason="vision_unavailable",
            provider="image",
        ),
    )
    state = _state_with_image(fake_image_media)
    result = process_multimodal(state)
    assert result["error"] == "media_failure:vision_unavailable"
    assert "não consegui analisar" in result["response"].lower()
