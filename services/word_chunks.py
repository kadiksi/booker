"""Склеивание абзацев в чанки; границы только между абзацами; в тексте сохраняются переносы и отступы."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

MIN_CHUNK_WORDS = 300
MAX_CHUNK_WORDS = 550

_PARA_BREAK = "\n\n"


def normalize_paragraph_text(text: str) -> str:
    """Убирает пустые строки по краям и хвостовые пробелы строк; красная строка и внутренние \\n сохраняются."""
    lines = [ln.rstrip() for ln in str(text).splitlines()]
    while lines and not lines[-1]:
        lines.pop()
    while lines and not lines[0]:
        lines.pop(0)
    return "\n".join(lines)


def _word_count(paragraph: str) -> int:
    return len((paragraph or "").split())


def merge_paragraphs_to_reading_chunks(
    paragraphs: list[str],
    min_words: int = MIN_CHUNK_WORDS,
    max_words: int = MAX_CHUNK_WORDS,
) -> list[str]:
    """
    Склеивает целые абзацы в чанки ~min_words..max_words (по числу слов).
    Абзацы в одном чанке разделяются пустой строкой, как в книге.
    """
    if min_words > max_words or min_words < 1:
        raise ValueError("min_words must be >= 1 and <= max_words")

    paras = _normalize_paragraph_list(paragraphs)
    if not paras:
        return []

    total_words = sum(_word_count(p) for p in paras)
    if total_words <= max_words:
        return [_PARA_BREAK.join(paras)]

    chunks: list[list[str]] = []
    i = 0
    n = len(paras)

    while i < n:
        rem_words = sum(_word_count(paras[j]) for j in range(i, n))
        if rem_words <= max_words:
            tail = paras[i:n]
            tw = sum(_word_count(p) for p in tail)
            if tw >= min_words or not chunks:
                chunks.append(tail)
            elif chunks and sum(_word_count(p) for p in chunks[-1]) + tw <= max_words:
                chunks[-1].extend(tail)
            else:
                chunks.append(tail)
            break

        block: list[str] = []
        bw = 0
        while i < n:
            p = paras[i]
            pw = _word_count(p)
            if pw > max_words:
                if block:
                    chunks.append(block)
                    block = []
                    bw = 0
                chunks.append([p])
                i += 1
                break
            if not block:
                block.append(p)
                bw = pw
                i += 1
                continue
            if bw >= min_words and bw + pw > max_words:
                break
            block.append(p)
            bw += pw
            i += 1
            if bw > max_words:
                break
        if block:
            chunks.append(block)

    return [_PARA_BREAK.join(c) for c in chunks]


def _normalize_paragraph_list(paragraphs: list[str]) -> list[str]:
    out: list[str] = []
    for p in paragraphs:
        t = normalize_paragraph_text(p)
        if t:
            out.append(t)
    return out


def to_reading_chunks(paragraphs: list[str]) -> list[str]:
    """
    Если всего слов меньше минимума для «больших» чанков — по одному чанку на абзац как из файла.
    Иначе склейка ~300–550 слов; при сбое алгоритма — снова по абзацам.
    """
    normalized = _normalize_paragraph_list(paragraphs)
    if not normalized:
        return []

    word_total = sum(_word_count(p) for p in normalized)
    if word_total < MIN_CHUNK_WORDS:
        return list(normalized)

    try:
        merged = merge_paragraphs_to_reading_chunks(normalized)
        if merged:
            return merged
    except ValueError as e:
        logger.warning("Word-chunk rules skipped, using raw paragraphs: %s", e)

    return list(normalized)
