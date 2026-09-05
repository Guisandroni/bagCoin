"""Unit tests for app.agents.multimodal audio processing (PR 2)."""

from unittest.mock import MagicMock

import pytest

from app.agents.multimodal import (
    WHISPER_HALLUCINATIONS,
    _audio_confidence,
    process_multimodal,
)
from app.agents.multimodal_types import MultimodalResult


# =====================================================================
# _audio_confidence — deterministic guards
# =====================================================================


def test_audio_confidence_normal_for_real_phrase():
    conf, reason = _audio_confidence("gastei 50 no mercado", 2.5)
    assert conf == "normal"
    assert reason is None


def test_audio_confidence_low_when_empty():
    conf, reason = _audio_confidence("", 2.0)
    assert conf == "low"
    assert reason == "too_short"


def test_audio_confidence_low_when_very_short_text():
    conf, reason = _audio_confidence("ok", 1.0)
    assert conf == "low"
    assert reason == "too_short"


def test_audio_confidence_low_when_duration_tiny():
    conf, reason = _audio_confidence("teste ok bom", 0.2)
    assert conf == "low"
    assert reason == "audio_too_short"


@pytest.mark.parametrize(
    "hallucination",
    [
        "Obrigado por assistir",
        "obrigada por assistir",
        "Legendas pela comunidade Amara.org",
        "Inscreva-se no canal!",
    ],
)
def test_audio_confidence_detects_whisper_hallucinations(hallucination):
    conf, reason = _audio_confidence(hallucination, 5.0)
    assert conf == "low"
    assert reason == "whisper_hallucination"


def test_audio_confidence_handles_none_duration():
    """Missing duration should not crash; text alone must decide."""
    conf, reason = _audio_confidence("gastei 50 no mercado", None)
    assert conf == "normal"


# =====================================================================
# process_multimodal — adapter treats audio results correctly
# =====================================================================


def _state_with_audio(media=None):
    return {
        "phone_number": "5511999999999",
        "message": "",
        "source_format": "audio",
        "context": {"media": media or {"mimetype": "audio/ogg", "data": "aGVsbG8="}},
        "error": None,
        "response": None,
    }


def test_process_multimodal_audio_low_confidence_sets_response(monkeypatch):
    monkeypatch.setattr(
        "app.agents.multimodal.process_audio",
        lambda m: MultimodalResult(
            text="Obrigado por assistir",
            confidence="low",
            reason="whisper_hallucination",
            provider="groq_whisper",
        ),
    )
    state = _state_with_audio()
    result = process_multimodal(state)
    assert result["error"] == "media_low_confidence:whisper_hallucination"
    assert "não consegui entender" in result["response"].lower()


def test_process_multimodal_audio_normal_populates_transcription(monkeypatch):
    monkeypatch.setattr(
        "app.agents.multimodal.process_audio",
        lambda m: MultimodalResult(
            text="gastei 50 no mercado",
            confidence="normal",
            provider="groq_whisper",
        ),
    )
    state = _state_with_audio()
    result = process_multimodal(state)
    assert result["message"] == "gastei 50 no mercado"
    assert result["context"]["audio_transcription"] == "gastei 50 no mercado"
    assert result["context"]["media_provider"] == "groq_whisper"
    # No error/response shortcut — pipeline continues normally
    assert not result.get("error")
    assert not result.get("response")


def test_process_multimodal_audio_failure_sets_error(monkeypatch):
    monkeypatch.setattr(
        "app.agents.multimodal.process_audio",
        lambda m: MultimodalResult(
            text="",
            failure=True,
            reason="missing_groq_api_key",
            provider="groq_whisper",
        ),
    )
    state = _state_with_audio()
    result = process_multimodal(state)
    assert result["error"] == "media_failure:missing_groq_api_key"
    assert "áudio" in result["response"].lower() or "audio" in result["response"].lower()


# =====================================================================
# Default hallucinations list sanity
# =====================================================================


def test_default_hallucinations_contain_common_patterns():
    """Must include the known Whisper hallucination phrases."""
    assert "obrigado por assistir" in WHISPER_HALLUCINATIONS
    assert any("legendas" in p for p in WHISPER_HALLUCINATIONS)
