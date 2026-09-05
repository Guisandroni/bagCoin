"""Minimal DOCX text extraction without external dependencies."""

from __future__ import annotations

import io
import zipfile
from xml.etree import ElementTree

WORD_TEXT_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"
WORD_TAB_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tab"
WORD_BREAK_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}br"
WORD_PARAGRAPH_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"
WORD_TABLE_ROW_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tr"
WORD_TABLE_CELL_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tc"


def extract_docx_text(data: bytes) -> str | None:
    """Extract plain text from a DOCX file.

    DOCX is a ZIP with XML parts. This intentionally extracts only text,
    tabs, paragraph breaks and basic table cell separation.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            names = archive.namelist()
            document_names = [
                "word/document.xml",
                *sorted(
                    name
                    for name in names
                    if name.startswith("word/header")
                    or name.startswith("word/footer")
                    or name.startswith("word/footnotes")
                    or name.startswith("word/endnotes")
                ),
            ]
            parts = [
                _xml_to_text(archive.read(name))
                for name in document_names
                if name in names
            ]
    except (zipfile.BadZipFile, KeyError, ElementTree.ParseError, ValueError):
        return None

    text = "\n".join(part for part in parts if part).strip()
    return text or None


def _xml_to_text(xml_data: bytes) -> str:
    root = ElementTree.fromstring(xml_data)
    lines: list[str] = []

    for paragraph in root.iter(WORD_PARAGRAPH_NS):
        line = _paragraph_to_text(paragraph)
        if line:
            lines.append(line)

    if lines:
        return "\n".join(lines)

    return _paragraph_to_text(root)


def _paragraph_to_text(node: ElementTree.Element) -> str:
    chunks: list[str] = []
    for child in node.iter():
        if child.tag == WORD_TEXT_NS and child.text:
            chunks.append(child.text)
        elif child.tag == WORD_TAB_NS:
            chunks.append("\t")
        elif child.tag == WORD_BREAK_NS:
            chunks.append("\n")
        elif child.tag in {WORD_TABLE_CELL_NS, WORD_TABLE_ROW_NS}:
            chunks.append("\t" if child.tag == WORD_TABLE_CELL_NS else "\n")
    return "".join(chunks).strip()
