"""Склеивание исходных абзацев в чанки для чтения по числу слов."""

from __future__ import annotations

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
    Объединяет абзацы так, чтобы в каждом чанке было не меньше min_words
    и не больше max_words слов.

    Очень короткая книга целиком попадает в один чанк (даже если слов < min_words).
    Последний чанк может быть короче min_words, если иначе нельзя уложиться в max_words.
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
