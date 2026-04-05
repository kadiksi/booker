"""Фрагменты текста с форматированием → Telegram HTML (parse_mode=HTML)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TextSpan:
    text: str
    bold: bool = False
    italic: bool = False
    strike: bool = False
    underline: bool = False
    code: bool = False
    link: str | None = None


def escape_telegram_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def escape_telegram_attr(text: str) -> str:
    return escape_telegram_html(text).replace('"', "&quot;")


def span_to_telegram_html(s: TextSpan) -> str:
    t = escape_telegram_html(s.text)
    if s.code:
        inner = f"<code>{t}</code>"
    elif s.bold and s.italic:
        inner = f"<b><i>{t}</i></b>"
    elif s.bold:
        inner = f"<b>{t}</b>"
    elif s.italic:
        inner = f"<i>{t}</i>"
    else:
        inner = t
    if s.strike and not s.code:
        inner = f"<s>{inner}</s>"
    if s.underline and not s.code:
        inner = f"<u>{inner}</u>"
    if s.link:
        inner = f'<a href="{escape_telegram_attr(s.link)}">{inner}</a>'
    return inner


def spans_to_telegram_html(spans: list[TextSpan]) -> str:
    return "".join(span_to_telegram_html(s) for s in spans)


def spans_plain_len(spans: list[TextSpan]) -> int:
    return sum(len(s.text) for s in spans)


def merge_adjacent_spans(spans: list[TextSpan]) -> list[TextSpan]:
    if not spans:
        return []
    out: list[TextSpan] = []
    for s in spans:
        if not s.text:
            continue
        if out and _span_style_key(out[-1]) == _span_style_key(s):
            prev = out[-1]
            out[-1] = TextSpan(
                prev.text + s.text,
                prev.bold,
                prev.italic,
                prev.strike,
                prev.underline,
                prev.code,
                prev.link,
            )
        else:
            out.append(
                TextSpan(
                    s.text,
                    s.bold,
                    s.italic,
                    s.strike,
                    s.underline,
                    s.code,
                    s.link,
                )
            )
    return out


def _span_style_key(s: TextSpan) -> tuple:
    return (s.bold, s.italic, s.strike, s.underline, s.code, s.link)


def trim_paragraph_spans(spans: list[TextSpan]) -> list[TextSpan]:
    if not spans:
        return []
    spans = list(spans)
    first = spans[0]
    spans[0] = TextSpan(
        first.text.lstrip(),
        first.bold,
        first.italic,
        first.strike,
        first.underline,
        first.code,
        first.link,
    )
    last = spans[-1]
    spans[-1] = TextSpan(
        last.text.rstrip(),
        last.bold,
        last.italic,
        last.strike,
        last.underline,
        last.code,
        last.link,
    )
    return merge_adjacent_spans([s for s in spans if s.text])


def concat_paragraph_spans(a: list[TextSpan], b: list[TextSpan]) -> list[TextSpan]:
    if not a:
        return b
    if not b:
        return a
    join = TextSpan("\n\n")
    return merge_adjacent_spans(a + [join] + b)


def split_spans_at_plain(spans: list[TextSpan], cut: int) -> tuple[list[TextSpan], list[TextSpan]]:
    if cut <= 0:
        return [], spans
    left: list[TextSpan] = []
    rem = cut
    for i, s in enumerate(spans):
        n = len(s.text)
        if n < rem:
            left.append(s)
            rem -= n
            continue
        if n == rem:
            left.append(s)
            return merge_adjacent_spans(left), merge_adjacent_spans(spans[i + 1 :])
        left.append(
            TextSpan(
                s.text[:rem],
                s.bold,
                s.italic,
                s.strike,
                s.underline,
                s.code,
                s.link,
            )
        )
        right_head = TextSpan(
            s.text[rem:],
            s.bold,
            s.italic,
            s.strike,
            s.underline,
            s.code,
            s.link,
        )
        return merge_adjacent_spans(left), merge_adjacent_spans([right_head] + list(spans[i + 1 :]))
    return merge_adjacent_spans(left), []
