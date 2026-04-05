"""Фрагменты для чтения: 670–750 символов; абзацы через пустую строку; отступы и переносы строк сохраняются."""

from __future__ import annotations

from services.rich_text import (
    TextSpan,
    concat_paragraph_spans,
    merge_adjacent_spans,
    spans_plain_len,
    spans_to_telegram_html,
    split_spans_at_plain,
    trim_paragraph_spans,
)

# Минимум символов в сообщении (цель).
MIN_READING_CHARS = 670
# Верхняя граница длины chunk.
MAX_READING_CHARS = 750
# Если исходный абзац короче — к нему пристыковываем следующий(ие) целиком, пока не наберётся ≥ этого порога или не упремся в max.
SHORT_PARAGRAPH_CHARS = 200


def normalize_paragraph_text(text: str) -> str:
    """Убирает пустые строки по краям и хвостовые пробелы строк; красная строка и внутренние \\n сохраняются."""
    lines = [ln.rstrip() for ln in str(text).splitlines()]
    while lines and not lines[-1]:
        lines.pop()
    while lines and not lines[0]:
        lines.pop(0)
    return "\n".join(lines)


def _normalize_paragraph_list(paragraphs: list[str]) -> list[str]:
    out: list[str] = []
    for p in paragraphs:
        t = normalize_paragraph_text(p)
        if t:
            out.append(t)
    return out


def _bundle_short_paragraphs(paragraphs: list[str], short: int, max_len: int) -> list[str]:
    """
    Пока блок короче `short`, добавляет следующий абзац целиком через пустую строку (как в книге),
    но не больше max_len символов за раз.
    """
    out: list[str] = []
    i = 0
    while i < len(paragraphs):
        cur = paragraphs[i]
        i += 1
        while len(cur) < short and i < len(paragraphs):
            cand = cur + "\n\n" + paragraphs[i]
            if len(cand) > max_len:
                break
            cur = cand
            i += 1
        out.append(cur)
    return out


def _normalize_paragraph_spans(paragraphs: list[list[TextSpan]]) -> list[list[TextSpan]]:
    out: list[list[TextSpan]] = []
    for p in paragraphs:
        t = trim_paragraph_spans(merge_adjacent_spans(p))
        if spans_plain_len(t) > 0:
            out.append(t)
    return out


def _bundle_short_paragraphs_spans(
    paragraphs: list[list[TextSpan]],
    short: int,
    max_plain: int,
) -> list[list[TextSpan]]:
    out: list[list[TextSpan]] = []
    i = 0
    while i < len(paragraphs):
        cur = paragraphs[i]
        i += 1
        while spans_plain_len(cur) < short and i < len(paragraphs):
            cand = concat_paragraph_spans(cur, paragraphs[i])
            if spans_plain_len(cand) > max_plain:
                break
            cur = cand
            i += 1
        out.append(cur)
    return out


def _spans_to_plain(spans: list[TextSpan]) -> str:
    return "".join(s.text for s in spans)


def _lstrip_plain_newlines_spans(spans: list[TextSpan]) -> list[TextSpan]:
    if not spans:
        return []
    spans = list(spans)
    ft = spans[0].text.lstrip("\n")
    f0 = spans[0]
    spans[0] = TextSpan(
        ft,
        f0.bold,
        f0.italic,
        f0.strike,
        f0.underline,
        f0.code,
        f0.link,
    )
    return merge_adjacent_spans([s for s in spans if s.text])


def _split_long_paragraph_spans(
    spans: list[TextSpan],
    min_len: int,
    max_len: int,
) -> list[list[TextSpan]]:
    plain = _spans_to_plain(spans)
    t = plain.rstrip()
    if not t:
        return []
    if len(t) <= max_len:
        return [spans]

    out: list[list[TextSpan]] = []
    remaining = spans
    remaining_plain = plain
    while len(remaining_plain) > max_len:
        window = remaining_plain[:max_len]
        cut = _find_break_end(window, min_len, max_len)
        if cut <= 0:
            cut = min(max_len, len(remaining_plain))
        piece_spans, remaining = split_spans_at_plain(remaining, cut)
        piece_plain = _spans_to_plain(piece_spans).rstrip()
        if not piece_plain:
            cut = min(max_len, len(remaining_plain))
            piece_spans, remaining = split_spans_at_plain(remaining, cut)
        if not piece_spans:
            break
        out.append(piece_spans)
        remaining = _lstrip_plain_newlines_spans(remaining)
        remaining_plain = _spans_to_plain(remaining)
    if remaining_plain:
        out.append(remaining)
    return out


def _merge_whole_paragraphs_spans(
    segments: list[tuple[list[TextSpan], bool]],
    max_plain: int,
) -> list[tuple[list[TextSpan], bool]]:
    out: list[tuple[list[TextSpan], bool]] = []
    buf: list[TextSpan] | None = None

    for seg, whole in segments:
        if not whole:
            if buf is not None:
                out.append((buf, True))
                buf = None
            out.append((seg, False))
            continue
        if buf is None:
            buf = seg
        else:
            cand = concat_paragraph_spans(buf, seg)
            if spans_plain_len(cand) <= max_plain:
                buf = cand
            else:
                out.append((buf, True))
                buf = seg
    if buf is not None:
        out.append((buf, True))
    return out


def _fix_minimums_flagged_spans(
    chunks: list[tuple[list[TextSpan], bool]],
    min_len: int,
    max_plain: int,
) -> list[list[TextSpan]]:
    if not chunks:
        return []
    parts: list[dict[str, object]] = [{"t": c[0], "m": c[1]} for c in chunks]

    changed = True
    while changed:
        changed = False
        i = 0
        while i < len(parts):
            t = parts[i]["t"]
            spans_t = t if isinstance(t, list) else []
            pl = spans_plain_len(spans_t)
            if pl >= min_len:
                i += 1
                continue
            if i + 1 < len(parts) and not bool(parts[i]["m"]) and not bool(parts[i + 1]["m"]):
                nxt = parts[i + 1]["t"]
                if isinstance(nxt, list):
                    a: list[TextSpan] = list(spans_t)
                    b: list[TextSpan] = nxt
                    bridge = TextSpan("\n")
                    c = merge_adjacent_spans(a + [bridge] + b)
                    if spans_plain_len(c) <= max_plain:
                        parts[i : i + 2] = [{"t": c, "m": False}]
                        changed = True
                        continue
            if i + 1 < len(parts) and bool(parts[i]["m"]) and bool(parts[i + 1]["m"]):
                nxt = parts[i + 1]["t"]
                if isinstance(nxt, list):
                    c = concat_paragraph_spans(spans_t, nxt)
                    if spans_plain_len(c) <= max_plain:
                        parts[i : i + 2] = [{"t": c, "m": True}]
                        changed = True
                        continue
            if i > 0 and bool(parts[i - 1]["m"]) and bool(parts[i]["m"]):
                prev = parts[i - 1]["t"]
                if isinstance(prev, list):
                    c = concat_paragraph_spans(prev, spans_t)
                    if spans_plain_len(c) <= max_plain:
                        parts[i - 1 : i + 1] = [{"t": c, "m": True}]
                        changed = True
                        continue
            i += 1

    return [p["t"] for p in parts if isinstance(p["t"], list)]


def to_reading_chunks_from_spans(paragraphs: list[list[TextSpan]]) -> list[str]:
    """
    Как to_reading_chunks, но вход — абзацы из TextSpan; результат — строки Telegram HTML.
    Целевой размер видимого текста: **≥670**, максимум **750** символов.
    """
    normalized = _normalize_paragraph_spans(paragraphs)
    if not normalized:
        return []

    bundled = _bundle_short_paragraphs_spans(
        normalized,
        SHORT_PARAGRAPH_CHARS,
        MAX_READING_CHARS,
    )

    meta: list[tuple[list[TextSpan], bool]] = []
    for p in bundled:
        parts = _split_long_paragraph_spans(p, MIN_READING_CHARS, MAX_READING_CHARS)
        if len(parts) == 1:
            meta.append((parts[0], True))
        else:
            for seg in parts:
                meta.append((seg, False))

    merged_meta = _merge_whole_paragraphs_spans(meta, MAX_READING_CHARS)
    fixed = _fix_minimums_flagged_spans(
        merged_meta,
        MIN_READING_CHARS,
        MAX_READING_CHARS,
    )
    return [spans_to_telegram_html(s) for s in fixed]


def _find_break_end(window: str, min_len: int, max_len: int) -> int:
    """Exclusive end index первого куска; window уже не длиннее max_len."""
    hi = min(len(window), max_len)
    if hi <= 0:
        return 0
    if hi < min_len:
        return hi
    for sep in ("\n\n", "\n", " "):
        pos = hi
        while pos >= min_len:
            found = window.rfind(sep, 0, pos)
            if found < 0:
                break
            end = found + (1 if sep == " " else len(sep))
            if min_len <= end <= hi:
                return end
            pos = found
    return hi


def _split_long_paragraph(text: str, min_len: int, max_len: int) -> list[str]:
    """Один исходный абзац → несколько кусков ≤ max_len (разрывы по \\n\\n, \\n, пробелу)."""
    t = text.rstrip()
    if not t:
        return []
    if len(t) <= max_len:
        return [t]

    out: list[str] = []
    remaining = t
    while len(remaining) > max_len:
        window = remaining[:max_len]
        cut = _find_break_end(window, min_len, max_len)
        if cut <= 0:
            cut = min(max_len, len(remaining))
        piece = remaining[:cut].rstrip()
        if not piece:
            cut = min(max_len, len(remaining))
            piece = remaining[:cut].rstrip()
        if not piece:
            break
        out.append(piece)
        remaining = remaining[cut:].lstrip("\n")
    if remaining:
        out.append(remaining)
    return out


def _merge_whole_paragraphs(
    segments: list[tuple[str, bool]],
    max_len: int,
) -> list[tuple[str, bool]]:
    """
    Склеивает целые абзацы (True) через \\n\\n, пока длина ≤ max_len.
    Куски длинного абзаца (False) всегда отдельным сообщением.
    """
    out: list[tuple[str, bool]] = []
    buf: str | None = None

    for seg, whole in segments:
        if not whole:
            if buf is not None:
                out.append((buf, True))
                buf = None
            out.append((seg, False))
            continue
        if buf is None:
            buf = seg
        else:
            cand = buf + "\n\n" + seg
            if len(cand) <= max_len:
                buf = cand
            else:
                out.append((buf, True))
                buf = seg
    if buf is not None:
        out.append((buf, True))
    return out


def _fix_minimums_flagged(
    chunks: list[tuple[str, bool]],
    min_len: int,
    max_len: int,
) -> list[str]:
    """Подтягивает куски < min_len, склеивая соседей с тем же флагом (\\n между частями одного абзаца, \\n\\n между целыми)."""
    if not chunks:
        return []
    parts: list[dict[str, object]] = [{"t": c[0], "m": c[1]} for c in chunks]

    changed = True
    while changed:
        changed = False
        i = 0
        while i < len(parts):
            t = str(parts[i]["t"])
            if len(t) >= min_len:
                i += 1
                continue
            if i + 1 < len(parts) and not bool(parts[i]["m"]) and not bool(parts[i + 1]["m"]):
                nxt = str(parts[i + 1]["t"])
                c = t + "\n" + nxt
                if len(c) <= max_len:
                    parts[i : i + 2] = [{"t": c, "m": False}]
                    changed = True
                    continue
            if i + 1 < len(parts) and bool(parts[i]["m"]) and bool(parts[i + 1]["m"]):
                c = t + "\n\n" + str(parts[i + 1]["t"])
                if len(c) <= max_len:
                    parts[i : i + 2] = [{"t": c, "m": True}]
                    changed = True
                    continue
            if i > 0 and bool(parts[i - 1]["m"]) and bool(parts[i]["m"]):
                c = str(parts[i - 1]["t"]) + "\n\n" + t
                if len(c) <= max_len:
                    parts[i - 1 : i + 1] = [{"t": c, "m": True}]
                    changed = True
                    continue
            i += 1

    return [str(p["t"]) for p in parts]


def to_reading_chunks(paragraphs: list[str]) -> list[str]:
    """
    Каждый chunk — одно сообщение в боте, цель **≥670** и ≤750 символов.
    Абзац короче 200 символов стараемся дополнить следующим(и) через пустую строку (визуально разные абзацы).
    Части одного длинного абзаца — отдельные chunk'и; между ними перенос строки, не «простыня».
    """
    normalized = _normalize_paragraph_list(paragraphs)
    if not normalized:
        return []

    bundled = _bundle_short_paragraphs(
        normalized,
        SHORT_PARAGRAPH_CHARS,
        MAX_READING_CHARS,
    )

    meta: list[tuple[str, bool]] = []
    for p in bundled:
        parts = _split_long_paragraph(p, MIN_READING_CHARS, MAX_READING_CHARS)
        if len(parts) == 1:
            meta.append((parts[0], True))
        else:
            for seg in parts:
                meta.append((seg, False))

    merged_meta = _merge_whole_paragraphs(meta, MAX_READING_CHARS)
    return _fix_minimums_flagged(
        merged_meta,
        MIN_READING_CHARS,
        MAX_READING_CHARS,
    )
