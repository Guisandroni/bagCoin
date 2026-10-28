"""Unit tests for app.agents.multimodal.

Covers Bug 8.1:
- Mimetype fallback via filename extension
- Large image resize
"""

import pytest

from app.agents.multimodal import (
    _configured_api_key,
    _maybe_resize_image,
    _source_format_from_media,
)


# =====================================================================
# _configured_api_key — rejects placeholder values
# =====================================================================


@pytest.mark.parametrize(
    "value, expected",
    [
        ("", None),
        (None, None),
        ("***", None),
        ("change-me", None),
        ("coloque_sua_chave", None),
        ("sua_chave", None),
        ("gsk_realkey_abc123", "gsk_realkey_abc123"),
        ("   gsk_abc   ", "gsk_abc"),
    ],
)
def test_configured_api_key_rejects_placeholders(value, expected):
    assert _configured_api_key(value) == expected


# =====================================================================
# _source_format_from_media — fallback by filename extension
# =====================================================================


@pytest.mark.parametrize(
    "media, expected",
    [
        ({"mimetype": "audio/ogg"}, "audio"),
        ({"mimetype": "image/jpeg"}, "image"),
        ({"mimetype": "application/pdf"}, "document"),
        ({"mimetype": "text/csv"}, "document"),
        # octet-stream + filename fallback
        ({"mimetype": "application/octet-stream", "filename": "voice.ogg"}, "audio"),
        ({"mimetype": "application/octet-stream", "filename": "photo.jpg"}, "image"),
        ({"mimetype": "application/octet-stream", "filename": "extrato.pdf"}, "document"),
        ({"mimetype": "", "filename": "nota.png"}, "image"),
        # Unknown → keep source_format
        ({"mimetype": "application/x-weird", "filename": "file.xyz"}, "text"),
        ({}, "text"),
    ],
)
def test_source_format_fallback(media, expected):
    assert _source_format_from_media("text", media) == expected


# =====================================================================
# _maybe_resize_image — only resizes large images
# =====================================================================


def test_small_image_not_resized():
    """Tiny payload stays the same bytes."""
    tiny = b"\x89PNG\r\n\x1a\n" + b"x" * 1000
    out_data, out_mime = _maybe_resize_image(tiny, "image/png")
    assert out_data == tiny
    assert out_mime == "image/png"


def test_large_image_resized_when_pillow_available():
    """Synthetic ~5MB payload: must be resized."""
    try:
        import os
        from io import BytesIO

        from PIL import Image
    except ImportError:
        pytest.skip("Pillow not installed in this environment")

    # Random noise doesn't compress well → forces a large JPEG
    size = 5000
    random_bytes = os.urandom(size * size * 3)
    img = Image.frombytes("RGB", (size, size), random_bytes)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=95)
    large = buf.getvalue()
    assert len(large) > 4_000_000, f"Setup failed: got {len(large)} bytes"

    out_data, out_mime = _maybe_resize_image(large, "image/jpeg")
    assert len(out_data) < len(large)
    assert out_mime == "image/jpeg"
