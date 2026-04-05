"""Склеивание абзацев в чанки; при невозможности уложиться в лимиты слов — чанк на каждый абзац."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

MIN_CHUNK_WORDS = 300
MAX_CHUNK_WORDS = 550


def _flat_words(paragraphs: list[str]) -> list[str]:
    words: list[str] = []
    for p in paragraphs:
        p = (p or "").strip()
        if p:
            words.extend(p.split())
    return words


def merge_paragraphs_to_reading_chunks(
    paragraphs: list[str],
    min_words: int = MIN_CHUNK_WORDS,
    max_words: int = MAX_CHUNK_WORDS,
) -> list[str]:
    """
    Объединяет абзацы в чанки ~min_words..max_words слов.
    Короткая книга — один чанк; последний чанк может быть короче min_words.
    """
    if min_words > max_words or min_words < 1:
        raise ValueError("min_words must be >= 1 and <= max_words")

    words = _flat_words(paragraphs)
    if not words:
        return []

    if len(words) <= max_words:
        return [" ".join(words)]

    chunks: list[list[str]] = []
    i = 0
    n = len(words)

    while i < n:
        rem = n - i
        if rem <= max_words:
            tail = words[i:n]
            if len(tail) >= min_words or not chunks:
                chunks.append(tail)
            elif chunks and len(chunks[-1]) + len(tail) <= max_words:
                chunks[-1].extend(tail)
            else:
                chunks.append(tail)
            break

        take = min(max_words, rem - min_words)
        if take < min_words:
            take = min_words
        chunks.append(words[i : i + take])
        i += take

    return [" ".join(c) for c in chunks]


def _normalize_paragraph_list(paragraphs: list[str]) -> list[str]:
    out: list[str] = []
    for p in paragraphs:
        t = " ".join((p or "").split()).strip()
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

    word_total = len(_flat_words(normalized))
    if word_total < MIN_CHUNK_WORDS:
        return list(normalized)

    try:
        merged = merge_paragraphs_to_reading_chunks(normalized)
        if merged:
            return merged
    except ValueError as e:
        logger.warning("Word-chunk rules skipped, using raw paragraphs: %s", e)

    return list(normalized)
