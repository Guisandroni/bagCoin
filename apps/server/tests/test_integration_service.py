"""Unit tests for web↔bot integration pairing (tokens, redaction, parse)."""

from app.services.integration_service import (
    LINK_TOKEN_RE,
    parse_link_token_from_message,
    redact_message_for_log,
    try_consume_link_pairing_sync,
)


def test_parse_link_whatsapp_style():
    assert parse_link_token_from_message("#bagcoin link abcdefghijklmnop") == "abcdefghijklmnop"


def test_parse_link_whatsapp_style_with_authentication_text():
    assert (
        parse_link_token_from_message(
            "Enviando token para autenticacao. #bagcoin link abcdefghijklmnop"
        )
        == "abcdefghijklmnop"
    )


def test_parse_link_telegram_start():
    tok = "a" * 16
    assert parse_link_token_from_message(f"/start {tok}") == tok


def test_regex_minimum_length():
    m = LINK_TOKEN_RE.match("/start short")
    assert m is None


def test_redact_hides_whatsapp_token():
    tok = "x" * 22
    msg = f"Enviando token para autenticacao. #bagcoin link {tok} trailing"
    out = redact_message_for_log(msg)
    assert "[REDACTED]" in out
    assert tok not in out


def test_redact_hides_telegram_start_token():
    tok = "y" * 18
    msg = f"/start {tok} extra"
    out = redact_message_for_log(msg)
    assert "[REDACTED]" in out
    assert tok not in out


def test_redact_short_token_not_matched_by_redact_re():
    """Shorter than 16 chars: still logged (regex matches pairing tokens >=16 in consume path)."""
    msg = "#bagcoin link short"
    assert redact_message_for_log(msg) == msg


def test_try_consume_non_link_message_returns_none():
    assert (
        try_consume_link_pairing_sync(
            phone_number="5511999999999",
            message="gastei 10 no café",
            channel="whatsapp",
            source_format="text",
        )
        is None
    )


def test_try_consume_skipped_for_non_text_source():
    assert (
        try_consume_link_pairing_sync(
            phone_number="5511999999999",
            message="#bagcoin link abcdefghijklmnop",
            channel="whatsapp",
            source_format="audio",
        )
        is None
    )
