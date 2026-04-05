"""Parse FB2 / EPUB into plain paragraphs (sync I/O — run via asyncio.to_thread in handlers)."""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET

import ebooklib
from ebooklib import epub
from lxml import html

logger = logging.getLogger(__name__)

# Не отбрасываем короткие строки — только пустые после нормализации пробелов.
MIN_PARAGRAPH_LEN = 1


class BookParseError(Exception):
    """User-visible parsing failures."""


class UnsupportedFormatError(BookParseError):
    """Format not supported (e.g. MOBI)."""


def _clean_paragraphs(raw: list[str], min_len: int = MIN_PARAGRAPH_LEN) -> list[str]:
    out: list[str] = []
    for text in raw:
        t = " ".join(str(text).split()).strip()
        if len(t) >= min_len:
            out.append(t)
    return out


def _strip_ns(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag


def parse_fb2(path: str) -> tuple[str | None, list[str]]:
    try:
        tree = ET.parse(path)
        root = tree.getroot()
    except ET.ParseError as e:
        raise BookParseError("Invalid FB2 XML.") from e

    titles: list[str] = []
    paragraphs: list[str] = []
    for el in root.iter():
        name = _strip_ns(el.tag)
        if name == "book-title" and el.text:
            titles.append(el.text.strip())
        elif name == "p":
            text = "".join(el.itertext()).strip()
            if text:
                paragraphs.append(text)

    if not paragraphs:
        blob = " ".join(t for t in root.itertext() if t and str(t).strip())
        blob = " ".join(blob.split()).strip()
        if blob:
            paragraphs.append(blob)
            logger.info("FB2: no <p> tags, using flat text fallback.")

    title = titles[0] if titles else None
    return title, _clean_paragraphs(paragraphs)


def parse_epub(path: str) -> tuple[str | None, list[str]]:
    try:
        book = epub.read_epub(path)
    except Exception as e:
        raise BookParseError("Could not read EPUB file.") from e

    title_meta = book.get_metadata("DC", "title")
    title: str | None = None
    if title_meta and title_meta[0] and title_meta[0][0]:
        title = str(title_meta[0][0]).strip() or None

    paragraphs: list[str] = []
    for spine_entry in book.spine:
        item_id = spine_entry[0] if isinstance(spine_entry, tuple) else spine_entry
        item = book.get_item_with_id(item_id)
        if not item or item.get_type() != ebooklib.ITEM_DOCUMENT:
            continue
        data = item.get_content()
        if not data:
            continue
        try:
            root = html.document_fromstring(data)
        except Exception:
            logger.debug("EPUB: skip HTML document (parse error), continue.")
            continue
        for p in root.xpath("//p"):
            text = " ".join(t.strip() for t in p.itertext() if t and t.strip())
            if text:
                paragraphs.append(text)

    if not paragraphs:
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            data = item.get_content()
            if not data:
                continue
            try:
                root = html.document_fromstring(data)
            except Exception:
                continue
            blob = " ".join(t for t in root.itertext() if t and str(t).strip())
            blob = " ".join(blob.split()).strip()
            if blob:
                paragraphs.append(blob)
        if paragraphs:
            logger.info("EPUB: no <p> tags, used full-text fallback from HTML items.")

    return title, _clean_paragraphs(paragraphs)


def parse_file(path: str, extension: str) -> tuple[str | None, list[str]]:
    ext = extension.lower().lstrip(".")
    if ext == "fb2":
        return parse_fb2(path)
    if ext == "epub":
        return parse_epub(path)
    if ext == "mobi":
        raise UnsupportedFormatError("MOBI is not supported yet. Please use FB2 or EPUB.")
    raise UnsupportedFormatError(f"Unsupported format: .{ext}")


class BookParserService:
    """Thin wrapper so callers can inject the same API as other services."""

    def parse_file(self, path: str, extension: str) -> tuple[str | None, list[str]]:
        return parse_file(path, extension)
