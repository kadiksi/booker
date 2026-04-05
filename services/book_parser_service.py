"""Parse FB2 / EPUB into paragraphs of TextSpan (Telegram HTML)."""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET

import ebooklib
from ebooklib import epub
from lxml import html

from services.rich_text import TextSpan, merge_adjacent_spans, spans_plain_len, trim_paragraph_spans
from services.word_chunks import normalize_paragraph_text

logger = logging.getLogger(__name__)

MIN_PARAGRAPH_LEN = 1

_DEFAULT_STYLE: dict = {
    "bold": False,
    "italic": False,
    "strike": False,
    "underline": False,
    "code": False,
    "link": None,
}


def _local_tag(tag: str | bytes) -> str:
    if not isinstance(tag, str):
        return ""
    if "}" in tag:
        tag = tag.rsplit("}", 1)[-1]
    return tag.lower()


def _strip_ns(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag


def _span_from(text: str, st: dict) -> TextSpan:
    return TextSpan(
        text,
        bold=bool(st.get("bold")),
        italic=bool(st.get("italic")),
        strike=bool(st.get("strike")),
        underline=bool(st.get("underline")),
        code=bool(st.get("code")),
        link=st.get("link"),
    )


def _fb2_push_style(tag: str, st: dict) -> dict:
    o = dict(st)
    if tag == "strong":
        o["bold"] = True
    elif tag == "emphasis":
        o["italic"] = True
    elif tag == "strikethrough":
        o["strike"] = True
    elif tag == "underline":
        o["underline"] = True
    elif tag == "code":
        o["code"] = True
    return o


def _fb2_href(el: ET.Element) -> str | None:
    for k, v in el.attrib.items():
        if not v:
            continue
        lk = k.lower()
        if lk.endswith("href") or lk.endswith(":href"):
            return str(v).strip() or None
    return None


def _fb2_collect_spans(el: ET.Element, st: dict) -> list[TextSpan]:
    out: list[TextSpan] = []
    if el.text:
        out.append(_span_from(el.text, st))
    for child in el:
        tag = _strip_ns(child.tag).lower()
        if tag == "empty-line":
            out.append(TextSpan("\n"))
            if child.tail:
                out.append(_span_from(child.tail, st))
            continue
        if tag in ("image", "binary"):
            if child.tail:
                out.append(_span_from(child.tail, st))
            continue
        if tag == "a":
            href = _fb2_href(child)
            cst = dict(st, link=href)
        elif tag in ("poem", "stanza", "section", "text-author"):
            cst = dict(st)
        else:
            cst = _fb2_push_style(tag, st)
        out.extend(_fb2_collect_spans(child, cst))
        if child.tail:
            out.append(_span_from(child.tail, st))
    return out


def _html_push_style(tag: str, st: dict) -> dict:
    o = dict(st)
    if tag in ("b", "strong"):
        o["bold"] = True
    elif tag in ("i", "em", "cite", "dfn"):
        o["italic"] = True
    elif tag in ("u", "ins"):
        o["underline"] = True
    elif tag in ("s", "strike", "del"):
        o["strike"] = True
    elif tag == "code":
        o["code"] = True
    return o


def _html_collect_spans(el: html.HtmlElement, st: dict) -> list[TextSpan]:
    out: list[TextSpan] = []
    if el.text:
        out.append(_span_from(el.text, st))
    for child in el:
        tag = _local_tag(child.tag)
        if tag == "br":
            out.append(TextSpan("\n"))
            if child.tail:
                out.append(_span_from(child.tail, st))
            continue
        if tag == "a":
            href = (child.get("href") or "").strip()
            cst = dict(st, link=href or None)
        else:
            cst = _html_push_style(tag, st) if tag else dict(st)
        out.extend(_html_collect_spans(child, cst))
        if child.tail:
            out.append(_span_from(child.tail, st))
    return out


def _p_element_to_spans(p: html.HtmlElement) -> list[TextSpan]:
    spans = _html_collect_spans(p, _DEFAULT_STYLE)
    return trim_paragraph_spans(merge_adjacent_spans(spans))


def _clean_paragraph_spans(raw: list[list[TextSpan]], min_len: int = MIN_PARAGRAPH_LEN) -> list[list[TextSpan]]:
    out: list[list[TextSpan]] = []
    for spans in raw:
        pl = spans_plain_len(spans)
        if pl >= min_len:
            out.append(spans)
    return out


def _plain_blob_to_spans(blob: str) -> list[TextSpan]:
    t = normalize_paragraph_text(blob.replace("\n", " "))
    if not t:
        return []
    return [TextSpan(t)]


class BookParseError(Exception):
    """User-visible parsing failures."""


class UnsupportedFormatError(BookParseError):
    """Format not supported (e.g. MOBI)."""


def parse_fb2(path: str) -> tuple[str | None, list[list[TextSpan]]]:
    try:
        tree = ET.parse(path)
        root = tree.getroot()
    except ET.ParseError as e:
        raise BookParseError("Invalid FB2 XML.") from e

    titles: list[str] = []
    paragraphs: list[list[TextSpan]] = []
    for el in root.iter():
        name = _strip_ns(el.tag)
        if name == "book-title" and el.text:
            titles.append(el.text.strip())
        elif name == "p":
            spans = trim_paragraph_spans(merge_adjacent_spans(_fb2_collect_spans(el, _DEFAULT_STYLE)))
            if spans_plain_len(spans) > 0:
                paragraphs.append(spans)

    if not paragraphs:
        blob = " ".join(t for t in root.itertext() if t and str(t).strip())
        spans = _plain_blob_to_spans(blob)
        if spans_plain_len(spans) > 0:
            paragraphs.append(spans)
            logger.info("FB2: no <p> tags, using flat text fallback.")

    title = titles[0] if titles else None
    return title, _clean_paragraph_spans(paragraphs)


def parse_epub(path: str) -> tuple[str | None, list[list[TextSpan]]]:
    try:
        book = epub.read_epub(path)
    except Exception as e:
        raise BookParseError("Could not read EPUB file.") from e

    title_meta = book.get_metadata("DC", "title")
    title: str | None = None
    if title_meta and title_meta[0] and title_meta[0][0]:
        title = str(title_meta[0][0]).strip() or None

    paragraphs: list[list[TextSpan]] = []
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
            spans = _p_element_to_spans(p)
            if spans_plain_len(spans) > 0:
                paragraphs.append(spans)

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
            spans = _plain_blob_to_spans(blob)
            if spans_plain_len(spans) > 0:
                paragraphs.append(spans)
        if paragraphs:
            logger.info("EPUB: no <p> tags, used full-text fallback from HTML items.")

    return title, _clean_paragraph_spans(paragraphs)


def parse_file(path: str, extension: str) -> tuple[str | None, list[list[TextSpan]]]:
    ext = extension.lower().lstrip(".")
    if ext == "fb2":
        return parse_fb2(path)
    if ext == "epub":
        return parse_epub(path)
    if ext == "mobi":
        raise UnsupportedFormatError("MOBI is not supported yet. Please use FB2 or EPUB.")
    raise UnsupportedFormatError(f"Unsupported format: .{ext}")


class BookParserService:
    def parse_file(self, path: str, extension: str) -> tuple[str | None, list[list[TextSpan]]]:
        return parse_file(path, extension)
